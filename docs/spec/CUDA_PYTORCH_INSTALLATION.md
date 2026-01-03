# CUDA & PyTorch Dynamic Installation

**Purpose**: Install optimal PyTorch/CUDA configuration into application venv
**Scope**: Venv-only - does not modify system Python or CUDA toolkit
**Depends on**: `HARDWARE_DETECTION.md` for GPU detection

---

## Overview

AI Universal Suite automatically installs the correct PyTorch/CUDA version based on detected GPU. This eliminates the most common setup failure: mismatched CUDA/PyTorch versions.

---

## 1. CUDA Version Selection

### 1.1 CUDA 13.x vs 12.x

**CUDA 13.0** (released August 2025) is preferred for Turing (sm_75) and newer:

| Benefit | Details |
|---------|---------|
| Smaller binaries | ~33% smaller wheel (2.18GB vs 3.28GB) |
| Better compression | ~71% reduction for CUDA Math APIs |
| Blackwell optimized | Full sm_120 support |
| Unified Arm | Single install for server + embedded |

**Important**: CUDA 13.0 dropped Maxwell, Pascal, and Volta support.

### 1.2 Version Matrix

| GPU Architecture | Compute Capability | Recommended CUDA | PyTorch Index |
|------------------|-------------------|------------------|---------------|
| Blackwell | 12.0 (sm_120) | 13.x | `cu130` |
| Ada Lovelace | 8.9 (sm_89) | 13.x | `cu130` |
| Ampere | 8.0-8.6 | 13.x | `cu130` |
| Turing | 7.5 (sm_75) | 13.x | `cu130` |
| Volta | 7.0 (sm_70) | 12.1 | `cu121` |
| Pascal | 6.x | 11.8 | `cu118` |

---

## 2. Configuration Logic

```python
from dataclasses import dataclass
from typing import List

@dataclass
class PyTorchConfig:
    """Recommended PyTorch installation configuration."""
    cuda_version: str           # "cu130", "cu121", "cu118"
    pytorch_version: str        # "2.9.0", etc.
    index_url: str              # PyPI index URL
    is_stable: bool             # False if nightly required
    notes: List[str]

def get_pytorch_config(compute_capability: float) -> PyTorchConfig:
    """
    Determine optimal PyTorch config based on GPU compute capability.
    
    Args:
        compute_capability: GPU compute capability (e.g., 12.0, 8.9)
    
    Returns:
        PyTorchConfig with installation parameters
    """
    cc = compute_capability
    
    # Blackwell (12.0+)
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
    
    # Ada Lovelace (8.9)
    elif cc >= 8.9:
        return PyTorchConfig(
            cuda_version="cu130",
            pytorch_version="2.9.0",
            index_url="https://download.pytorch.org/whl/cu130",
            is_stable=True,
            notes=["Ada Lovelace - using CUDA 13.0", "FP8 available"]
        )
    
    # Ampere (8.0-8.6)
    elif cc >= 8.0:
        return PyTorchConfig(
            cuda_version="cu130",
            pytorch_version="2.9.0",
            index_url="https://download.pytorch.org/whl/cu130",
            is_stable=True,
            notes=["Ampere - using CUDA 13.0", "BF16 available"]
        )
    
    # Turing (7.5)
    elif cc >= 7.5:
        return PyTorchConfig(
            cuda_version="cu130",
            pytorch_version="2.9.0",
            index_url="https://download.pytorch.org/whl/cu130",
            is_stable=True,
            notes=["Turing - minimum architecture for CUDA 13.0"]
        )
    
    # Volta (7.0) - Must use CUDA 12.x
    elif cc >= 7.0:
        return PyTorchConfig(
            cuda_version="cu121",
            pytorch_version="2.5.1",
            index_url="https://download.pytorch.org/whl/cu121",
            is_stable=True,
            notes=["Volta - CUDA 13.0 dropped support, using 12.1"]
        )
    
    # Pascal and older
    else:
        return PyTorchConfig(
            cuda_version="cu118",
            pytorch_version="2.5.1",
            index_url="https://download.pytorch.org/whl/cu118",
            is_stable=True,
            notes=["Legacy GPU - using CUDA 11.8"]
        )
```

---

## 3. Installation

### 3.1 Venv Installation

```python
import subprocess
import sys
from pathlib import Path

def install_pytorch(
    venv_path: Path,
    config: PyTorchConfig,
    include_vision: bool = True,
    include_audio: bool = False
) -> bool:
    """
    Install PyTorch into specified venv.
    
    Args:
        venv_path: Path to virtual environment
        config: PyTorchConfig from get_pytorch_config()
        include_vision: Install torchvision
        include_audio: Install torchaudio
    
    Returns:
        True if successful
    """
    # Get pip executable
    if sys.platform == "win32":
        pip = venv_path / "Scripts" / "pip.exe"
    else:
        pip = venv_path / "bin" / "pip"
    
    # Build package list
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
    
    # Execute
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
```

### 3.2 ONNX Runtime Installation

```python
def install_onnxruntime(venv_path: Path, has_cuda: bool) -> bool:
    """Install ONNX Runtime with appropriate backend."""
    if sys.platform == "win32":
        pip = venv_path / "Scripts" / "pip.exe"
    else:
        pip = venv_path / "bin" / "pip"
    
    package = "onnxruntime-gpu" if has_cuda else "onnxruntime"
    
    result = subprocess.run(
        [str(pip), "install", package],
        capture_output=True, text=True
    )
    return result.returncode == 0
```

---

## 4. Verification

```python
import json
import subprocess
from pathlib import Path

def verify_pytorch_cuda(venv_path: Path) -> dict:
    """
    Verify PyTorch CUDA installation.
    
    Returns:
        {
            "success": bool,
            "cuda_available": bool,
            "pytorch_version": str,
            "cuda_version": str,
            "gpu_name": str,
            "compute_capability": str,
            "error": Optional[str]
        }
    """
    if sys.platform == "win32":
        python = venv_path / "Scripts" / "python.exe"
    else:
        python = venv_path / "bin" / "python"
    
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
    result["success"] = False
    result["error"] = "CUDA not available"

print(json.dumps(result))
'''
    
    try:
        result = subprocess.run(
            [str(python), "-c", verify_script],
            capture_output=True, text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 5. Error Handling

### 5.1 Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `sm_120 not compatible` | PyTorch too old | Install cu130 build |
| `CUDA driver version insufficient` | Driver outdated | Prompt driver update |
| `no kernel image available` | Wrong CUDA version | Reinstall correct version |
| `CUDA out of memory` | VRAM exhausted | Use quantization |

### 5.2 Fallback Chain

```python
def install_with_fallback(venv_path: Path, compute_capability: float) -> bool:
    """Install PyTorch with fallback chain."""
    
    # Try 1: Optimal config
    config = get_pytorch_config(compute_capability)
    if install_pytorch(venv_path, config):
        if verify_pytorch_cuda(venv_path)["success"]:
            return True
    
    # Try 2: Stable with older CUDA
    fallback_configs = [
        ("cu128", "2.7.0"),
        ("cu124", "2.5.1"),
        ("cu121", "2.5.1"),
        ("cu118", "2.5.1"),
    ]
    
    for cuda_ver, torch_ver in fallback_configs:
        config = PyTorchConfig(
            cuda_version=cuda_ver,
            pytorch_version=torch_ver,
            index_url=f"https://download.pytorch.org/whl/{cuda_ver}",
            is_stable=True,
            notes=["Fallback installation"]
        )
        if install_pytorch(venv_path, config):
            if verify_pytorch_cuda(venv_path)["success"]:
                return True
    
    # Try 3: CPU only
    config = PyTorchConfig(
        cuda_version="cpu",
        pytorch_version="2.5.1",
        index_url="https://download.pytorch.org/whl/cpu",
        is_stable=True,
        notes=["CPU-only fallback - GPU acceleration unavailable"]
    )
    return install_pytorch(venv_path, config)
```

---

## 6. UI Integration

### 6.1 Installation Progress

```
Installing PyTorch for Blackwell GPU...

[████████████░░░░░░░░] 60%

├─ torch-2.9.0+cu130 (2.1 GB) ✓
├─ torchvision-0.24.0+cu130 (12 MB) ...
└─ Verifying CUDA support...
```

### 6.2 Verification Display

```
┌─────────────────────────────────────────────────────────────┐
│  PyTorch Installation Verified                              │
│                                                             │
│  PyTorch: 2.9.0+cu130                                       │
│  CUDA: 13.0                                                 │
│  GPU: NVIDIA GeForce RTX 5090                               │
│  Compute Capability: 12.0                                   │
│                                                             │
│  ✓ CUDA acceleration available                              │
│  ✓ FP4/FP6 Tensor Cores enabled                            │
│  ✓ FP8 Transformer Engine enabled                          │
└─────────────────────────────────────────────────────────────┘
```

---

## References

- [PyTorch Installation Matrix](https://pytorch.org/get-started/locally/)
- [PyTorch Previous Versions](https://pytorch.org/get-started/previous-versions/)
- [CUDA Toolkit Release Notes](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/)
- [NVIDIA CUDA Compute Capability](https://developer.nvidia.com/cuda/gpus)
