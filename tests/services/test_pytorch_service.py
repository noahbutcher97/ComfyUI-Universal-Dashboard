"""
Tests for PyTorchService.

Per CUDA_PYTORCH_INSTALLATION.md spec:
- Automatic PyTorch/CUDA version selection based on compute capability
- Venv-only installation
- Verification and fallback chain
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Generator

import pytest

from src.services.pytorch_service import (
    PyTorchService,
    PyTorchConfig,
    VerificationResult,
    InstallationResult,
    PyTorchInstallError,
)


class TestPyTorchConfig:
    """Tests for PyTorchConfig dataclass."""

    def test_pytorch_config_fields(self) -> None:
        """PyTorchConfig should hold all configuration fields."""
        config = PyTorchConfig(
            cuda_version="cu130",
            pytorch_version="2.9.0",
            index_url="https://download.pytorch.org/whl/cu130",
            is_stable=True,
            notes=["Blackwell GPU"]
        )
        assert config.cuda_version == "cu130"
        assert config.pytorch_version == "2.9.0"
        assert config.is_stable is True
        assert "Blackwell GPU" in config.notes

    def test_pytorch_config_defaults(self) -> None:
        """PyTorchConfig should have sensible defaults."""
        config = PyTorchConfig(
            cuda_version="cpu",
            pytorch_version="2.5.1",
            index_url="https://download.pytorch.org/whl/cpu"
        )
        assert config.is_stable is True
        assert config.notes == []


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_verification_success(self) -> None:
        """VerificationResult captures successful verification."""
        result = VerificationResult(
            success=True,
            cuda_available=True,
            pytorch_version="2.9.0+cu130",
            cuda_version="13.0",
            gpu_name="NVIDIA GeForce RTX 5090",
            compute_capability="12.0"
        )
        assert result.success is True
        assert result.cuda_available is True
        assert result.gpu_name == "NVIDIA GeForce RTX 5090"

    def test_verification_cpu_only(self) -> None:
        """VerificationResult for CPU-only installation."""
        result = VerificationResult(
            success=True,
            cuda_available=False,
            pytorch_version="2.5.1"
        )
        assert result.success is True
        assert result.cuda_available is False

    def test_verification_failure(self) -> None:
        """VerificationResult captures failures."""
        result = VerificationResult(
            success=False,
            error="CUDA driver version insufficient"
        )
        assert result.success is False
        assert "driver" in result.error.lower()


class TestGetPyTorchConfig:
    """Tests for get_pytorch_config() version selection logic."""

    def test_blackwell_uses_cuda130(self) -> None:
        """Blackwell GPUs (CC 12.0+) should use CUDA 13.0."""
        config = PyTorchService.get_pytorch_config(12.0)

        assert config.cuda_version == "cu130"
        assert "13.0" in config.index_url or "cu130" in config.index_url
        assert any("Blackwell" in note for note in config.notes)

    def test_ada_lovelace_uses_cuda130(self) -> None:
        """Ada Lovelace GPUs (CC 8.9) should use CUDA 13.0."""
        config = PyTorchService.get_pytorch_config(8.9)

        assert config.cuda_version == "cu130"
        assert any("Ada" in note for note in config.notes)

    def test_ampere_uses_cuda130(self) -> None:
        """Ampere GPUs (CC 8.0-8.6) should use CUDA 13.0."""
        for cc in [8.0, 8.6]:
            config = PyTorchService.get_pytorch_config(cc)
            assert config.cuda_version == "cu130"
            assert any("Ampere" in note for note in config.notes)

    def test_turing_uses_cuda130(self) -> None:
        """Turing GPUs (CC 7.5) should use CUDA 13.0 (minimum supported)."""
        config = PyTorchService.get_pytorch_config(7.5)

        assert config.cuda_version == "cu130"
        assert any("Turing" in note for note in config.notes)

    def test_volta_uses_cuda121(self) -> None:
        """Volta GPUs (CC 7.0) should use CUDA 12.1 (13.0 dropped support)."""
        config = PyTorchService.get_pytorch_config(7.0)

        assert config.cuda_version == "cu121"
        assert any("Volta" in note or "12.1" in note for note in config.notes)

    def test_pascal_uses_cuda118(self) -> None:
        """Pascal GPUs (CC 6.x) should use CUDA 11.8."""
        for cc in [6.0, 6.1, 6.2]:
            config = PyTorchService.get_pytorch_config(cc)
            assert config.cuda_version == "cu118"

    def test_none_uses_cpu(self) -> None:
        """None compute capability should result in CPU-only installation."""
        config = PyTorchService.get_pytorch_config(None)

        assert config.cuda_version == "cpu"
        assert "cpu" in config.index_url
        assert any("CPU" in note for note in config.notes)


class TestGetExecutables:
    """Tests for executable path resolution."""

    def test_windows_pip_path(self) -> None:
        """Windows pip should be in Scripts directory."""
        with patch('sys.platform', 'win32'):
            venv = Path("C:/Users/test/.venv")
            pip = PyTorchService.get_pip_executable(venv)
            assert "Scripts" in str(pip)
            assert pip.name == "pip.exe"

    def test_unix_pip_path(self) -> None:
        """Unix pip should be in bin directory."""
        with patch('sys.platform', 'linux'):
            venv = Path("/home/user/.venv")
            pip = PyTorchService.get_pip_executable(venv)
            assert "bin" in str(pip)
            assert pip.name == "pip"

    def test_windows_python_path(self) -> None:
        """Windows python should be in Scripts directory."""
        with patch('sys.platform', 'win32'):
            venv = Path("C:/Users/test/.venv")
            python = PyTorchService.get_python_executable(venv)
            assert "Scripts" in str(python)
            assert python.name == "python.exe"

    def test_unix_python_path(self) -> None:
        """Unix python should be in bin directory."""
        with patch('sys.platform', 'darwin'):
            venv = Path("/Users/test/.venv")
            python = PyTorchService.get_python_executable(venv)
            assert "bin" in str(python)
            assert python.name == "python"


class TestInstallPyTorch:
    """Tests for install_pytorch() function."""

    def test_install_builds_correct_command(self) -> None:
        """install_pytorch should build correct pip command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)

            # Create mock pip
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            pip_path = scripts / "pip.exe"
            pip_path.touch()

            config = PyTorchConfig(
                cuda_version="cu130",
                pytorch_version="2.9.0",
                index_url="https://download.pytorch.org/whl/cu130"
            )

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.install_pytorch(venv_path, config)

                assert result is True

                # Verify command structure
                call_args = mock_run.call_args
                cmd = call_args[0][0]
                assert "pip" in cmd[0].lower()
                assert "install" in cmd
                assert "torch==2.9.0" in cmd
                assert "torchvision" in cmd
                assert "--index-url" in cmd
                assert "cu130" in str(cmd)

    def test_install_nightly_adds_pre_flag(self) -> None:
        """Nightly builds should include --pre flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()

            config = PyTorchConfig(
                cuda_version="cu130",
                pytorch_version="2.10.0.dev",
                index_url="https://download.pytorch.org/whl/nightly/cu130",
                is_stable=False
            )

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch('sys.platform', 'win32'):
                    PyTorchService.install_pytorch(venv_path, config)

                cmd = mock_run.call_args[0][0]
                assert "--pre" in cmd

    def test_install_without_vision(self) -> None:
        """Should exclude torchvision if not requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()

            config = PyTorchConfig(
                cuda_version="cpu",
                pytorch_version="2.5.1",
                index_url="https://download.pytorch.org/whl/cpu"
            )

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch('sys.platform', 'win32'):
                    PyTorchService.install_pytorch(
                        venv_path, config, include_vision=False
                    )

                cmd = mock_run.call_args[0][0]
                assert "torchvision" not in cmd

    def test_install_failure_returns_false(self) -> None:
        """Failed installation should return False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()

            config = PyTorchConfig(
                cuda_version="cu130",
                pytorch_version="2.9.0",
                index_url="https://download.pytorch.org/whl/cu130"
            )

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="Error")

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.install_pytorch(venv_path, config)

                assert result is False

    def test_install_pip_not_found_raises(self) -> None:
        """Missing pip should raise PyTorchInstallError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            # Don't create pip

            config = PyTorchConfig(
                cuda_version="cpu",
                pytorch_version="2.5.1",
                index_url="https://download.pytorch.org/whl/cpu"
            )

            with patch('sys.platform', 'win32'):
                with pytest.raises(PyTorchInstallError):
                    PyTorchService.install_pytorch(venv_path, config)


class TestVerifyPyTorchCuda:
    """Tests for verify_pytorch_cuda() function."""

    def test_verify_success_with_cuda(self) -> None:
        """Verification should return success with CUDA info."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "python.exe").touch()

            mock_output = json.dumps({
                "success": True,
                "cuda_available": True,
                "pytorch_version": "2.9.0+cu130",
                "cuda_version": "13.0",
                "gpu_name": "NVIDIA GeForce RTX 4090",
                "compute_capability": "8.9"
            })

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=mock_output,
                    stderr=""
                )

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.verify_pytorch_cuda(venv_path)

            assert result.success is True
            assert result.cuda_available is True
            assert result.pytorch_version == "2.9.0+cu130"
            assert result.gpu_name == "NVIDIA GeForce RTX 4090"

    def test_verify_cpu_only(self) -> None:
        """CPU-only installation should still verify successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "python.exe").touch()

            mock_output = json.dumps({
                "success": True,
                "cuda_available": False,
                "pytorch_version": "2.5.1",
                "cuda_version": None,
                "gpu_name": None,
                "compute_capability": None
            })

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=mock_output,
                    stderr=""
                )

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.verify_pytorch_cuda(venv_path)

            assert result.success is True
            assert result.cuda_available is False

    def test_verify_kernel_mismatch_error(self) -> None:
        """Should detect CUDA kernel mismatch errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "python.exe").touch()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="RuntimeError: no kernel image is available"
                )

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.verify_pytorch_cuda(venv_path)

            assert result.success is False
            assert "kernel" in result.error.lower()

    def test_verify_driver_version_error(self) -> None:
        """Should detect CUDA driver version errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "python.exe").touch()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="CUDA driver version is insufficient for CUDA runtime"
                )

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.verify_pytorch_cuda(venv_path)

            assert result.success is False
            assert "driver" in result.error.lower()


class TestInstallWithFallback:
    """Tests for install_with_fallback() function."""

    def test_optimal_install_succeeds(self) -> None:
        """Should succeed on first try with optimal config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()
            (scripts / "python.exe").touch()

            with patch.object(PyTorchService, 'install_pytorch', return_value=True):
                with patch.object(PyTorchService, 'verify_pytorch_cuda') as mock_verify:
                    mock_verify.return_value = VerificationResult(
                        success=True,
                        cuda_available=True,
                        pytorch_version="2.9.0+cu130"
                    )

                    result = PyTorchService.install_with_fallback(venv_path, 8.9)

            assert result.success is True
            assert result.fallback_used is False
            assert result.config.cuda_version == "cu130"

    def test_fallback_on_verification_failure(self) -> None:
        """Should try fallback if verification fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()
            (scripts / "python.exe").touch()

            call_count = [0]

            def mock_verify(venv):
                call_count[0] += 1
                if call_count[0] < 3:  # Fail first 2 attempts
                    return VerificationResult(success=False, error="Failed")
                return VerificationResult(success=True, cuda_available=True)

            with patch.object(PyTorchService, 'install_pytorch', return_value=True):
                with patch.object(PyTorchService, 'verify_pytorch_cuda', side_effect=mock_verify):
                    result = PyTorchService.install_with_fallback(venv_path, 8.0)

            assert result.success is True
            assert result.fallback_used is True

    def test_cpu_fallback_when_cuda_fails(self) -> None:
        """Should fall back to CPU if all CUDA attempts fail."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()
            (scripts / "python.exe").touch()

            def mock_verify(venv):
                # Only succeed for CPU
                return VerificationResult(success=True, cuda_available=False)

            with patch.object(PyTorchService, 'install_pytorch', return_value=True):
                with patch.object(PyTorchService, 'verify_pytorch_cuda', side_effect=mock_verify):
                    result = PyTorchService.install_with_fallback(venv_path, 8.0)

            assert result.success is True
            assert result.config.cuda_version == "cpu"

    def test_fail_when_requiring_cuda(self) -> None:
        """Should fail if requiring CUDA but only CPU works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()
            (scripts / "python.exe").touch()

            with patch.object(PyTorchService, 'install_pytorch', return_value=False):
                result = PyTorchService.install_with_fallback(
                    venv_path, 8.0, require_cuda=True
                )

            assert result.success is False


class TestInstallOnnxRuntime:
    """Tests for install_onnxruntime() function."""

    def test_install_gpu_version(self) -> None:
        """Should install onnxruntime-gpu when has_cuda=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.install_onnxruntime(venv_path, has_cuda=True)

                cmd = mock_run.call_args[0][0]
                assert "onnxruntime-gpu" in cmd

            assert result is True

    def test_install_cpu_version(self) -> None:
        """Should install onnxruntime when has_cuda=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.install_onnxruntime(venv_path, has_cuda=False)

                cmd = mock_run.call_args[0][0]
                assert "onnxruntime" in cmd
                assert "onnxruntime-gpu" not in cmd

            assert result is True


class TestUninstallPyTorch:
    """Tests for uninstall_pytorch() function."""

    def test_uninstall_all_packages(self) -> None:
        """Should uninstall torch, torchvision, and torchaudio."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "pip.exe").touch()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch('sys.platform', 'win32'):
                    result = PyTorchService.uninstall_pytorch(venv_path)

                cmd = mock_run.call_args[0][0]
                assert "uninstall" in cmd
                assert "-y" in cmd
                assert "torch" in cmd
                assert "torchvision" in cmd
                assert "torchaudio" in cmd

            assert result is True


class TestGetInstalledPyTorchInfo:
    """Tests for get_installed_pytorch_info() function."""

    def test_get_info_when_installed(self) -> None:
        """Should return info when PyTorch is installed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "python.exe").touch()

            mock_output = json.dumps({
                "installed": True,
                "version": "2.9.0+cu130",
                "cuda_available": True,
                "cuda_version": "13.0"
            })

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=mock_output
                )

                with patch('sys.platform', 'win32'):
                    info = PyTorchService.get_installed_pytorch_info(venv_path)

            assert info is not None
            assert info["installed"] is True
            assert info["version"] == "2.9.0+cu130"

    def test_get_info_when_not_installed(self) -> None:
        """Should return not installed when PyTorch is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir)
            scripts = venv_path / "Scripts"
            scripts.mkdir()
            (scripts / "python.exe").touch()

            mock_output = json.dumps({"installed": False})

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=mock_output
                )

                with patch('sys.platform', 'win32'):
                    info = PyTorchService.get_installed_pytorch_info(venv_path)

            assert info is not None
            assert info["installed"] is False


class TestArchitectureNotes:
    """Tests that architecture-specific notes are correct."""

    def test_blackwell_notes_mention_fp4_fp6(self) -> None:
        """Blackwell config should mention FP4/FP6 Tensor Cores."""
        config = PyTorchService.get_pytorch_config(12.0)
        notes_str = " ".join(config.notes)
        assert "FP4" in notes_str or "FP6" in notes_str

    def test_ada_notes_mention_fp8(self) -> None:
        """Ada Lovelace config should mention FP8."""
        config = PyTorchService.get_pytorch_config(8.9)
        notes_str = " ".join(config.notes)
        assert "FP8" in notes_str

    def test_ampere_notes_mention_bf16(self) -> None:
        """Ampere config should mention BF16."""
        config = PyTorchService.get_pytorch_config(8.0)
        notes_str = " ".join(config.notes)
        assert "BF16" in notes_str
