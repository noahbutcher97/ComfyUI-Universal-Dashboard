"""
PyTorch/CUDA Dynamic Installation Service.

Per CUDA_PYTORCH_INSTALLATION.md spec:
- Automatically installs optimal PyTorch/CUDA version based on detected GPU
- Installs into venv only (not system Python)
- Supports Blackwell (RTX 50 series) through Pascal GPUs
- Fallback chain: optimal → stable older → CPU

This implements the core "zero terminal interaction" principle.
"""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Callable

from src.utils.logger import log


class PyTorchInstallError(Exception):
    """Base exception for PyTorch installation failures."""
    pass


class CUDANotAvailableError(PyTorchInstallError):
    """Raised when CUDA is not available after installation."""
    pass


class DriverVersionError(PyTorchInstallError):
    """Raised when CUDA driver version is insufficient."""
    pass


@dataclass
class PyTorchConfig:
    """
    Recommended PyTorch installation configuration.

    Per CUDA_PYTORCH_INSTALLATION.md Section 2.
    """
    cuda_version: str           # "cu130", "cu121", "cu118", "cpu"
    pytorch_version: str        # "2.9.0", "2.5.1", etc.
    index_url: str              # PyPI index URL
    is_stable: bool = True      # False if nightly required
    notes: List[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Result of PyTorch CUDA verification."""
    success: bool
    cuda_available: bool = False
    pytorch_version: Optional[str] = None
    cuda_version: Optional[str] = None
    gpu_name: Optional[str] = None
    compute_capability: Optional[str] = None
    error: Optional[str] = None


@dataclass
class InstallationResult:
    """Result of PyTorch installation attempt."""
    success: bool
    config: Optional[PyTorchConfig] = None
    verification: Optional[VerificationResult] = None
    fallback_used: bool = False
    error: Optional[str] = None


class PyTorchService:
    """
    Service for installing and managing PyTorch/CUDA.

    Per CUDA_PYTORCH_INSTALLATION.md:
    - Determines optimal CUDA version based on compute capability
    - Installs into venv only
    - Verifies installation with torch.cuda.is_available()
    - Implements fallback chain for robustness
    """

    # Fallback CUDA versions (oldest compatible with each GPU generation)
    FALLBACK_CONFIGS: List[Tuple[str, str]] = [
        ("cu128", "2.7.0"),   # CUDA 12.8
        ("cu124", "2.5.1"),   # CUDA 12.4
        ("cu121", "2.5.1"),   # CUDA 12.1
        ("cu118", "2.5.1"),   # CUDA 11.8
    ]

    # Default packages to install
    DEFAULT_PACKAGES = ["torch", "torchvision"]

    @staticmethod
    def get_pytorch_config(compute_capability: Optional[float]) -> PyTorchConfig:
        """
        Determine optimal PyTorch config based on GPU compute capability.

        Per CUDA_PYTORCH_INSTALLATION.md Section 2.

        Args:
            compute_capability: GPU compute capability (e.g., 12.0, 8.9)
                               None for CPU-only installation

        Returns:
            PyTorchConfig with installation parameters
        """
        if compute_capability is None:
            return PyTorchConfig(
                cuda_version="cpu",
                pytorch_version="2.5.1",
                index_url="https://download.pytorch.org/whl/cpu",
                is_stable=True,
                notes=["No NVIDIA GPU detected - CPU-only installation"]
            )

        cc = compute_capability

        # Blackwell (12.0+) - RTX 5090, 5080, etc.
        if cc >= 12.0:
            return PyTorchConfig(
                cuda_version="cu130",
                pytorch_version="2.9.0",
                index_url="https://download.pytorch.org/whl/cu130",
                is_stable=True,
                notes=[
                    "Blackwell architecture - using CUDA 13.0",
                    "FP4/FP6 Tensor Cores available",
                ]
            )

        # Ada Lovelace (8.9) - RTX 4090, 4080, etc.
        if cc >= 8.9:
            return PyTorchConfig(
                cuda_version="cu130",
                pytorch_version="2.9.0",
                index_url="https://download.pytorch.org/whl/cu130",
                is_stable=True,
                notes=["Ada Lovelace - using CUDA 13.0", "FP8 available"]
            )

        # Ampere (8.0-8.6) - RTX 3090, 3080, A100, etc.
        if cc >= 8.0:
            return PyTorchConfig(
                cuda_version="cu130",
                pytorch_version="2.9.0",
                index_url="https://download.pytorch.org/whl/cu130",
                is_stable=True,
                notes=["Ampere - using CUDA 13.0", "BF16 available"]
            )

        # Turing (7.5) - RTX 2080, 2070, etc.
        if cc >= 7.5:
            return PyTorchConfig(
                cuda_version="cu130",
                pytorch_version="2.9.0",
                index_url="https://download.pytorch.org/whl/cu130",
                is_stable=True,
                notes=["Turing - minimum architecture for CUDA 13.0"]
            )

        # Volta (7.0) - V100, Titan V - CUDA 13.0 dropped support
        if cc >= 7.0:
            return PyTorchConfig(
                cuda_version="cu121",
                pytorch_version="2.5.1",
                index_url="https://download.pytorch.org/whl/cu121",
                is_stable=True,
                notes=["Volta - CUDA 13.0 dropped support, using 12.1"]
            )

        # Pascal (6.x) - GTX 1080, 1070, P100, etc.
        return PyTorchConfig(
            cuda_version="cu118",
            pytorch_version="2.5.1",
            index_url="https://download.pytorch.org/whl/cu118",
            is_stable=True,
            notes=["Legacy GPU (Pascal) - using CUDA 11.8"]
        )

    @staticmethod
    def get_pip_executable(venv_path: Path) -> Path:
        """Get path to pip executable in venv."""
        if sys.platform == "win32":
            return venv_path / "Scripts" / "pip.exe"
        return venv_path / "bin" / "pip"

    @staticmethod
    def get_python_executable(venv_path: Path) -> Path:
        """Get path to Python executable in venv."""
        if sys.platform == "win32":
            return venv_path / "Scripts" / "python.exe"
        return venv_path / "bin" / "python"

    @staticmethod
    def install_pytorch(
        venv_path: Path,
        config: PyTorchConfig,
        include_vision: bool = True,
        include_audio: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        timeout: int = 600
    ) -> bool:
        """
        Install PyTorch into specified venv.

        Per CUDA_PYTORCH_INSTALLATION.md Section 3.1.

        Args:
            venv_path: Path to virtual environment
            config: PyTorchConfig from get_pytorch_config()
            include_vision: Install torchvision (default True)
            include_audio: Install torchaudio (default False)
            progress_callback: Called with (message, progress_fraction)
            timeout: Installation timeout in seconds

        Returns:
            True if installation succeeded

        Raises:
            PyTorchInstallError: If installation fails
        """
        pip = PyTorchService.get_pip_executable(venv_path)

        if not pip.exists():
            raise PyTorchInstallError(f"Pip not found at {pip}")

        # Build package list with versions
        packages = [f"torch=={config.pytorch_version}"]
        if include_vision:
            packages.append("torchvision")
        if include_audio:
            packages.append("torchaudio")

        # Build command
        cmd = [str(pip), "install", *packages, "--index-url", config.index_url]

        # Add --pre for nightly builds
        if not config.is_stable:
            cmd.insert(2, "--pre")

        if progress_callback:
            progress_callback(f"Installing PyTorch ({config.cuda_version})...", 0.1)

        log.info(f"Installing PyTorch: {' '.join(packages)} from {config.index_url}")
        log.debug(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                log.error(f"PyTorch installation failed: {result.stderr}")
                return False

            if progress_callback:
                progress_callback("PyTorch installation complete", 0.9)

            log.info("PyTorch installation succeeded")
            return True

        except subprocess.TimeoutExpired:
            log.error(f"PyTorch installation timed out after {timeout}s")
            return False
        except Exception as e:
            log.error(f"PyTorch installation error: {e}")
            return False

    @staticmethod
    def verify_pytorch_cuda(
        venv_path: Path,
        timeout: int = 30
    ) -> VerificationResult:
        """
        Verify PyTorch CUDA installation.

        Per CUDA_PYTORCH_INSTALLATION.md Section 4.

        Args:
            venv_path: Path to virtual environment
            timeout: Verification timeout in seconds

        Returns:
            VerificationResult with installation status
        """
        python = PyTorchService.get_python_executable(venv_path)

        if not python.exists():
            return VerificationResult(
                success=False,
                error=f"Python not found at {python}"
            )

        verify_script = '''
import torch
import json

result = {
    "success": True,
    "cuda_available": torch.cuda.is_available(),
    "pytorch_version": torch.__version__,
}

if torch.cuda.is_available():
    result["cuda_version"] = torch.version.cuda
    result["gpu_name"] = torch.cuda.get_device_name(0)
    cc = torch.cuda.get_device_capability(0)
    result["compute_capability"] = f"{cc[0]}.{cc[1]}"
else:
    # CPU-only is still a valid installation
    result["cuda_version"] = None
    result["gpu_name"] = None
    result["compute_capability"] = None

print(json.dumps(result))
'''

        try:
            result = subprocess.run(
                [str(python), "-c", verify_script],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return VerificationResult(
                    success=True,
                    cuda_available=data.get("cuda_available", False),
                    pytorch_version=data.get("pytorch_version"),
                    cuda_version=data.get("cuda_version"),
                    gpu_name=data.get("gpu_name"),
                    compute_capability=data.get("compute_capability"),
                )
            else:
                # Check for common errors
                stderr = result.stderr
                if "no kernel image" in stderr.lower():
                    return VerificationResult(
                        success=False,
                        error="CUDA kernel mismatch - wrong PyTorch version for GPU"
                    )
                elif "cuda driver version" in stderr.lower():
                    return VerificationResult(
                        success=False,
                        error="CUDA driver version insufficient - please update GPU drivers"
                    )
                else:
                    return VerificationResult(
                        success=False,
                        error=f"Verification failed: {stderr[:200]}"
                    )

        except subprocess.TimeoutExpired:
            return VerificationResult(
                success=False,
                error="Verification timed out"
            )
        except json.JSONDecodeError as e:
            return VerificationResult(
                success=False,
                error=f"Failed to parse verification output: {e}"
            )
        except Exception as e:
            return VerificationResult(
                success=False,
                error=str(e)
            )

    @staticmethod
    def install_with_fallback(
        venv_path: Path,
        compute_capability: Optional[float],
        progress_callback: Optional[Callable[[str, float], None]] = None,
        require_cuda: bool = False
    ) -> InstallationResult:
        """
        Install PyTorch with fallback chain.

        Per CUDA_PYTORCH_INSTALLATION.md Section 5.2.

        Tries optimal config first, then falls back through compatible versions.

        Args:
            venv_path: Path to virtual environment
            compute_capability: GPU compute capability (None for CPU)
            progress_callback: Called with (message, progress_fraction)
            require_cuda: If True, fail if CUDA not available

        Returns:
            InstallationResult with status and configuration used
        """
        # Try 1: Optimal config
        if progress_callback:
            progress_callback("Determining optimal PyTorch configuration...", 0.05)

        config = PyTorchService.get_pytorch_config(compute_capability)
        log.info(f"Optimal config: {config.cuda_version} for CC {compute_capability}")

        if PyTorchService.install_pytorch(venv_path, config, progress_callback=progress_callback):
            verification = PyTorchService.verify_pytorch_cuda(venv_path)

            if verification.success:
                # For CPU-only config, CUDA not being available is expected
                if config.cuda_version == "cpu" or verification.cuda_available:
                    log.info(f"Installation verified: {verification}")
                    return InstallationResult(
                        success=True,
                        config=config,
                        verification=verification,
                        fallback_used=False
                    )

        # Try 2: Fallback through older CUDA versions
        if compute_capability is not None and compute_capability >= 7.0:
            for cuda_ver, torch_ver in PyTorchService.FALLBACK_CONFIGS:
                if progress_callback:
                    progress_callback(f"Trying fallback: CUDA {cuda_ver}...", 0.3)

                log.info(f"Attempting fallback: {cuda_ver}")

                fallback_config = PyTorchConfig(
                    cuda_version=cuda_ver,
                    pytorch_version=torch_ver,
                    index_url=f"https://download.pytorch.org/whl/{cuda_ver}",
                    is_stable=True,
                    notes=["Fallback installation"]
                )

                if PyTorchService.install_pytorch(venv_path, fallback_config):
                    verification = PyTorchService.verify_pytorch_cuda(venv_path)
                    if verification.success and verification.cuda_available:
                        log.info(f"Fallback succeeded: {cuda_ver}")
                        return InstallationResult(
                            success=True,
                            config=fallback_config,
                            verification=verification,
                            fallback_used=True
                        )

        # Try 3: CPU only (if not requiring CUDA)
        if not require_cuda:
            if progress_callback:
                progress_callback("Installing CPU-only PyTorch...", 0.7)

            cpu_config = PyTorchConfig(
                cuda_version="cpu",
                pytorch_version="2.5.1",
                index_url="https://download.pytorch.org/whl/cpu",
                is_stable=True,
                notes=["CPU-only fallback - GPU acceleration unavailable"]
            )

            if PyTorchService.install_pytorch(venv_path, cpu_config):
                verification = PyTorchService.verify_pytorch_cuda(venv_path)
                if verification.success:
                    log.warning("Installed CPU-only PyTorch (GPU not available)")
                    return InstallationResult(
                        success=True,
                        config=cpu_config,
                        verification=verification,
                        fallback_used=True
                    )

        # All attempts failed
        return InstallationResult(
            success=False,
            error="All installation attempts failed"
        )

    @staticmethod
    def install_onnxruntime(
        venv_path: Path,
        has_cuda: bool,
        timeout: int = 300
    ) -> bool:
        """
        Install ONNX Runtime with appropriate backend.

        Per CUDA_PYTORCH_INSTALLATION.md Section 3.2.

        Args:
            venv_path: Path to virtual environment
            has_cuda: Whether to install GPU version
            timeout: Installation timeout in seconds

        Returns:
            True if installation succeeded
        """
        pip = PyTorchService.get_pip_executable(venv_path)

        if not pip.exists():
            log.error(f"Pip not found at {pip}")
            return False

        package = "onnxruntime-gpu" if has_cuda else "onnxruntime"

        log.info(f"Installing {package}")

        try:
            result = subprocess.run(
                [str(pip), "install", package],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                log.info(f"{package} installed successfully")
                return True
            else:
                log.error(f"ONNX Runtime installation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            log.error(f"ONNX Runtime installation timed out")
            return False
        except Exception as e:
            log.error(f"ONNX Runtime installation error: {e}")
            return False

    @staticmethod
    def uninstall_pytorch(venv_path: Path, timeout: int = 120) -> bool:
        """
        Uninstall PyTorch from venv.

        Useful for reinstallation or switching CUDA versions.

        Args:
            venv_path: Path to virtual environment
            timeout: Uninstallation timeout in seconds

        Returns:
            True if uninstallation succeeded
        """
        pip = PyTorchService.get_pip_executable(venv_path)

        if not pip.exists():
            return False

        packages = ["torch", "torchvision", "torchaudio"]

        log.info("Uninstalling PyTorch packages")

        try:
            result = subprocess.run(
                [str(pip), "uninstall", "-y", *packages],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Uninstall returns 0 even if package wasn't installed
            return True

        except subprocess.TimeoutExpired:
            log.error("PyTorch uninstallation timed out")
            return False
        except Exception as e:
            log.error(f"PyTorch uninstallation error: {e}")
            return False

    @staticmethod
    def get_installed_pytorch_info(venv_path: Path) -> Optional[dict]:
        """
        Get information about installed PyTorch.

        Args:
            venv_path: Path to virtual environment

        Returns:
            Dict with version info, or None if not installed
        """
        python = PyTorchService.get_python_executable(venv_path)

        if not python.exists():
            return None

        check_script = '''
import json
try:
    import torch
    result = {
        "installed": True,
        "version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
    }
except ImportError:
    result = {"installed": False}
print(json.dumps(result))
'''

        try:
            result = subprocess.run(
                [str(python), "-c", check_script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            return None

        except Exception:
            return None
