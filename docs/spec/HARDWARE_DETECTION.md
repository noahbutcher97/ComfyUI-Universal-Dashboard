# Hardware Detection Specification

**Purpose**: Comprehensive hardware detection for AI workstation configuration
**Scope**: GPU, CPU, Storage, RAM - detection methods, classification, and recommendation impact

---

## Overview

AI Universal Suite detects hardware to:
1. **Determine viability** - Can this model run at all?
2. **Predict usability** - How fast/smooth will the experience be?
3. **Constrain recommendations** - What fits in available space/memory?
4. **Communicate tradeoffs** - Help users understand speed vs quality choices

Detection happens once at startup, cached for session. Users can manually override if needed.

---

## 1. GPU Detection

### 1.1 Platform-Specific Detection

#### NVIDIA (Windows/Linux)

```python
def detect_nvidia() -> GPUProfile:
    """Detect NVIDIA GPU via nvidia-smi and torch."""
    # Basic info
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,compute_cap,power.limit",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    name, vram_mb, compute_cap, power_limit = result.stdout.strip().split(", ")
    
    # Parse compute capability
    major, minor = compute_cap.split(".")
    cc = float(compute_cap)
    
    return GPUProfile(
        vendor="nvidia",
        name=name,
        vram_gb=float(vram_mb) / 1024,
        compute_capability=cc,
        power_limit_watts=float(power_limit),
        supports_fp8=(cc >= 8.9),
        supports_fp4=(cc >= 12.0),
        supports_bf16=(cc >= 8.0),
    )
```

#### Apple Silicon (macOS)

```python
def detect_apple_silicon() -> GPUProfile:
    """Detect Apple Silicon via sysctl and system_profiler."""
    import subprocess
    
    # RAM (shared with GPU)
    result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
    total_ram_bytes = int(result.stdout.strip())
    total_ram_gb = total_ram_bytes / (1024**3)
    
    # Apply 75% ceiling for effective VRAM
    effective_vram_gb = total_ram_gb * 0.75
    
    # Chip variant from system_profiler
    result = subprocess.run(
        ["system_profiler", "SPHardwareDataType"],
        capture_output=True, text=True
    )
    # Parse "Chip: Apple M3 Max" etc.
    chip_variant = parse_chip_from_profiler(result.stdout)
    
    # Memory bandwidth lookup
    bandwidth = APPLE_SILICON_BANDWIDTH.get(chip_variant, 200)  # GB/s
    
    return GPUProfile(
        vendor="apple",
        name=f"Apple {chip_variant}",
        vram_gb=effective_vram_gb,
        unified_memory=True,
        chip_variant=chip_variant,
        memory_bandwidth_gbps=bandwidth,
        mps_available=True,
    )

# Memory bandwidth by chip (GB/s)
APPLE_SILICON_BANDWIDTH = {
    "M1": 68, "M1 Pro": 200, "M1 Max": 400, "M1 Ultra": 800,
    "M2": 100, "M2 Pro": 200, "M2 Max": 400, "M2 Ultra": 800,
    "M3": 100, "M3 Pro": 150, "M3 Max": 400,
    "M4": 120, "M4 Pro": 273, "M4 Max": 546,
}
```

#### AMD ROCm (Linux)

```python
def detect_amd_rocm() -> GPUProfile:
    """Detect AMD GPU via rocm-smi."""
    result = subprocess.run(
        ["rocm-smi", "--showmeminfo", "vram", "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    vram_bytes = data["card0"]["VRAM Total Memory (B)"]
    
    # Get GFX version for compatibility
    result = subprocess.run(["rocminfo"], capture_output=True, text=True)
    gfx_version = parse_gfx_version(result.stdout)  # e.g., "gfx1100"
    
    # Check if officially supported
    officially_supported = gfx_version in SUPPORTED_GFX_VERSIONS
    hsa_override = None
    if not officially_supported and gfx_version.startswith("gfx103"):
        # RDNA2 workaround
        hsa_override = "HSA_OVERRIDE_GFX_VERSION=10.3.0"
    
    return GPUProfile(
        vendor="amd",
        name=get_amd_gpu_name(),
        vram_gb=vram_bytes / (1024**3),
        gfx_version=gfx_version,
        officially_supported=officially_supported,
        hsa_override_required=hsa_override,
        rocm_version=get_rocm_version(),
    )
```

### 1.2 GPU Compute Capabilities

| Architecture | Compute Capability | Key Features |
|--------------|-------------------|--------------|
| Blackwell | 12.0 (sm_120) | FP4, FP6, FP8 Gen2, BF16 |
| Ada Lovelace | 8.9 (sm_89) | FP8, BF16, Flash Attention |
| Hopper | 9.0 (sm_90) | FP8, BF16, Transformer Engine |
| Ampere | 8.0-8.6 (sm_80/86) | BF16, TF32 |
| Turing | 7.5 (sm_75) | FP16 Tensor Cores |
| Volta | 7.0 (sm_70) | FP16 Tensor Cores |

### 1.3 Platform Constraints

#### Apple Silicon Constraints
```python
APPLE_SILICON_CONSTRAINTS = {
    "gguf_allowed": ["Q4_0", "Q5_0", "Q8_0"],  # K-quants crash MPS
    "memory_ceiling": 0.75,  # 75% of unified memory
    "excluded_models": ["HunyuanVideo"],  # ~16 min/clip impractical
    "fp8_available": False,
    "flash_attention": False,
}
```

#### NVIDIA Constraints by Compute Capability
```python
def get_nvidia_constraints(compute_capability: float) -> dict:
    return {
        "fp8_available": compute_capability >= 8.9,
        "fp4_available": compute_capability >= 12.0,
        "bf16_available": compute_capability >= 8.0,
        "flash_attention": compute_capability >= 8.0,
        "gguf_allowed": ["Q4_0", "Q4_K_M", "Q5_0", "Q5_K_M", "Q6_K", "Q8_0"],
    }
```

---

## 2. GPU Power & Form Factor

### 2.1 Problem

Mobile GPUs share names with desktop variants but have significantly lower sustained performance due to thermal and power constraints.

| GPU | Desktop TDP | Mobile TDP | Sustained Performance |
|-----|-------------|------------|----------------------|
| RTX 5090 | 575W | 175W | ~55% of desktop |
| RTX 4090 | 450W | 175W | ~62% of desktop |
| RTX 4080 | 320W | 175W | ~74% of desktop |
| RTX 4070 | 200W | 140W | ~84% of desktop |

### 2.2 Detection

```python
def detect_power_limit() -> Optional[float]:
    """Get actual enforced power limit from nvidia-smi."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=power.limit", "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return float(result.stdout.strip().split("\n")[0])
    return None

def detect_is_mobile(gpu_name: str) -> bool:
    """Check if GPU name indicates mobile variant."""
    mobile_indicators = ["laptop", "mobile", "max-q", "notebook"]
    return any(ind in gpu_name.lower() for ind in mobile_indicators)
```

### 2.3 Reference TDP Lookup

```python
GPU_REFERENCE_TDP = {
    # Blackwell
    "rtx 5090": 575, "rtx 5080": 360, "rtx 5070 ti": 300, "rtx 5070": 250,
    # Ada Lovelace
    "rtx 4090": 450, "rtx 4080 super": 320, "rtx 4080": 320,
    "rtx 4070 ti super": 285, "rtx 4070 ti": 285, 
    "rtx 4070 super": 220, "rtx 4070": 200,
    "rtx 4060 ti": 165, "rtx 4060": 115,
    # Ampere
    "rtx 3090 ti": 450, "rtx 3090": 350, "rtx 3080 ti": 350, "rtx 3080": 320,
    "rtx 3070 ti": 290, "rtx 3070": 220, "rtx 3060 ti": 200, "rtx 3060": 170,
    # Turing
    "rtx 2080 ti": 250, "rtx 2080 super": 250, "rtx 2080": 215,
    "rtx 2070 super": 215, "rtx 2070": 175, "rtx 2060 super": 175, "rtx 2060": 160,
}
```

### 2.4 Performance Ratio Calculation

```python
import math

def get_sustained_performance_ratio(gpu_name: str, actual_power_limit: float) -> float:
    """
    Calculate sustained performance ratio for mobile/throttled GPUs.
    
    Physics basis: GPU performance scales approximately with sqrt(power) 
    in thermal-limited regime. Well-established in GPU benchmarking.
    
    Returns:
        1.0 for desktop at full power
        <1.0 for power-limited configurations
    """
    reference_tdp = lookup_reference_tdp(gpu_name)
    
    if reference_tdp is None:
        return 1.0  # Unknown GPU, assume full performance
    
    if actual_power_limit >= reference_tdp * 0.95:
        return 1.0  # At or near full power
    
    power_ratio = actual_power_limit / reference_tdp
    performance_ratio = math.sqrt(power_ratio)
    
    # Clamp to reasonable range (0.5 - 1.0)
    return max(0.5, min(1.0, performance_ratio))
```

### 2.5 Laptop Warning UI

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Laptop GPU Detected                                     │
│                                                             │
│  GPU: NVIDIA GeForce RTX 4090 Laptop GPU                    │
│  Power Limit: 175W (Desktop reference: 450W)                │
│  Estimated Sustained Performance: ~62%                      │
│                                                             │
│  For best AI performance:                                   │
│  • Keep laptop plugged in (battery limits GPU power)        │
│  • Ensure good ventilation (avoid soft surfaces)            │
│  • Long generation tasks may cause thermal throttling       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. CPU Detection

### 3.1 Why CPU Matters

1. **CPU fallback/offload** - When VRAM insufficient, layers offload to RAM via CPU
2. **Preprocessing** - Tokenization, image resizing, audio processing
3. **GGUF inference** - llama.cpp runs well on high-core-count CPUs
4. **Hybrid workflows** - Some operations stay on CPU

### 3.2 Key Metrics

| Metric | Why It Matters | Detection |
|--------|----------------|-----------|
| Physical cores | Actual parallel capacity | `psutil.cpu_count(logical=False)` |
| Logical cores | Thread count with SMT | `psutil.cpu_count(logical=True)` |
| Model name | Performance class indicator | Platform-specific |
| Architecture | x86_64 vs ARM64 compatibility | `platform.machine()` |
| AVX support | SIMD for CPU inference | CPUID flags |

### 3.3 Detection Implementation

```python
import platform
import psutil
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class CPUTier(Enum):
    HIGH = "high"         # 16+ physical cores - viable GGUF, fast preprocessing
    MEDIUM = "medium"     # 8-15 cores - adequate preprocessing, slow GGUF
    LOW = "low"           # 4-7 cores - preprocessing only
    MINIMAL = "minimal"   # <4 cores - bottleneck warning

@dataclass
class CPUProfile:
    model: str                              # "AMD Ryzen 9 7950X"
    architecture: str                       # "x86_64", "arm64"
    physical_cores: int
    logical_cores: int
    
    # Instruction support (x86 only)
    supports_avx: bool = False
    supports_avx2: bool = False
    supports_avx512: bool = False
    
    # Derived
    tier: CPUTier = CPUTier.MINIMAL
    
    def __post_init__(self):
        self.tier = self._calculate_tier()
    
    def _calculate_tier(self) -> CPUTier:
        cores = self.physical_cores
        if cores >= 16:
            return CPUTier.HIGH
        elif cores >= 8:
            return CPUTier.MEDIUM
        elif cores >= 4:
            return CPUTier.LOW
        else:
            return CPUTier.MINIMAL

def detect_cpu() -> CPUProfile:
    """Detect CPU specifications."""
    physical = psutil.cpu_count(logical=False) or 1
    logical = psutil.cpu_count(logical=True) or 1
    
    # Model name detection
    model = get_cpu_model_name()
    
    # AVX detection (x86 only)
    avx, avx2, avx512 = False, False, False
    if platform.machine() in ("x86_64", "AMD64"):
        avx, avx2, avx512 = detect_avx_support()
    
    return CPUProfile(
        model=model,
        architecture=platform.machine(),
        physical_cores=physical,
        logical_cores=logical,
        supports_avx=avx,
        supports_avx2=avx2,
        supports_avx512=avx512,
    )

def get_cpu_model_name() -> str:
    """Get CPU model name (platform-specific)."""
    system = platform.system()
    
    if system == "Windows":
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    
    elif system == "Darwin":  # macOS
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    
    elif system == "Linux":
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":")[1].strip()
    
    return "Unknown CPU"

def detect_avx_support() -> tuple[bool, bool, bool]:
    """Detect AVX, AVX2, AVX-512 support on x86."""
    # Use cpuinfo library or parse /proc/cpuinfo on Linux
    # Windows: Use __cpuid intrinsic or registry
    # This is simplified - real implementation needs platform-specific code
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        flags = info.get("flags", [])
        return ("avx" in flags, "avx2" in flags, "avx512f" in flags)
    except ImportError:
        return (False, False, False)
```

### 3.4 CPU Tier Impact on Recommendations

| Tier | GGUF Viability | Preprocessing | Offload Capacity |
|------|----------------|---------------|------------------|
| HIGH (16+) | Good - usable for 7B-13B models | Excellent | Full layer offload viable |
| MEDIUM (8-15) | Slow but works for 7B | Good | Partial offload viable |
| LOW (4-7) | Impractical | Adequate | Minimal offload |
| MINIMAL (<4) | Not viable | Bottleneck | Not recommended |

---

## 4. Storage Detection

### 4.1 Why Storage Matters

1. **Model loading speed** - 10GB model: 1 sec (NVMe) vs 67 sec (HDD)
2. **Workflow friction** - Frequent model swapping amplifies speed differences
3. **Capacity constraints** - Can't install models that don't fit
4. **Speed preference** - Users prioritizing speed need fast storage warnings

### 4.2 Storage Types and Speeds

| Type | Sequential Read | 10GB Load | 50GB Load |
|------|-----------------|-----------|-----------|
| NVMe Gen5 | ~10,000 MB/s | ~1 sec | ~5 sec |
| NVMe Gen4 | ~5,000 MB/s | ~2 sec | ~10 sec |
| NVMe Gen3 | ~3,500 MB/s | ~3 sec | ~15 sec |
| SATA SSD | ~550 MB/s | ~18 sec | ~90 sec |
| HDD | ~150 MB/s | ~67 sec | ~5.5 min |

### 4.3 Detection Implementation

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import shutil

class StorageType(Enum):
    NVME_GEN5 = "nvme_gen5"
    NVME_GEN4 = "nvme_gen4"
    NVME_GEN3 = "nvme_gen3"
    SATA_SSD = "sata_ssd"
    HDD = "hdd"
    UNKNOWN = "unknown"

class StorageTier(Enum):
    FAST = "fast"         # NVMe Gen3+ - frequent model swapping OK
    MODERATE = "moderate" # SATA SSD - occasional swapping
    SLOW = "slow"         # HDD - minimize swapping

# Estimated speeds in MB/s for load time calculations
STORAGE_SPEEDS = {
    StorageType.NVME_GEN5: 10000,
    StorageType.NVME_GEN4: 5000,
    StorageType.NVME_GEN3: 3500,
    StorageType.SATA_SSD: 550,
    StorageType.HDD: 150,
    StorageType.UNKNOWN: 500,  # Conservative assumption
}

@dataclass
class StorageProfile:
    path: Path                    # Installation path
    total_gb: float
    free_gb: float
    storage_type: StorageType
    estimated_read_mbps: int
    tier: StorageTier
    
    def can_fit(self, size_gb: float, buffer_gb: float = 10) -> bool:
        """Check if size fits with buffer for workspace."""
        return self.free_gb >= (size_gb + buffer_gb)
    
    def estimate_load_time(self, size_gb: float) -> float:
        """Estimate model load time in seconds."""
        size_mb = size_gb * 1024
        return size_mb / self.estimated_read_mbps

def detect_storage(path: Path) -> StorageProfile:
    """Detect storage characteristics for given path."""
    # Get capacity
    total, used, free = shutil.disk_usage(path)
    total_gb = total / (1024**3)
    free_gb = free / (1024**3)
    
    # Detect type (platform-specific)
    storage_type = detect_storage_type(path)
    
    # Get speed estimate
    speed = STORAGE_SPEEDS[storage_type]
    
    # Classify tier
    if storage_type in (StorageType.NVME_GEN5, StorageType.NVME_GEN4, StorageType.NVME_GEN3):
        tier = StorageTier.FAST
    elif storage_type == StorageType.SATA_SSD:
        tier = StorageTier.MODERATE
    else:
        tier = StorageTier.SLOW
    
    return StorageProfile(
        path=path,
        total_gb=total_gb,
        free_gb=free_gb,
        storage_type=storage_type,
        estimated_read_mbps=speed,
        tier=tier,
    )

def detect_storage_type(path: Path) -> StorageType:
    """Detect storage type (platform-specific)."""
    system = platform.system()
    
    if system == "Windows":
        return _detect_storage_type_windows(path)
    elif system == "Linux":
        return _detect_storage_type_linux(path)
    elif system == "Darwin":
        return _detect_storage_type_macos(path)
    
    return StorageType.UNKNOWN

def _detect_storage_type_windows(path: Path) -> StorageType:
    """Windows storage detection via PowerShell."""
    try:
        # Get drive letter
        drive = path.drive or "C:"
        
        # Query physical disk info
        cmd = f'''
        $partition = Get-Partition -DriveLetter '{drive[0]}'
        $disk = Get-PhysicalDisk -DeviceNumber $partition.DiskNumber
        $disk | Select-Object MediaType, BusType | ConvertTo-Json
        '''
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            media_type = data.get("MediaType", "").lower()
            bus_type = data.get("BusType", "").lower()
            
            if "nvme" in bus_type:
                # Could further detect Gen3/4/5 via PCIe link speed
                return StorageType.NVME_GEN4  # Default assumption
            elif media_type == "ssd" or "ssd" in bus_type:
                return StorageType.SATA_SSD
            elif media_type == "hdd":
                return StorageType.HDD
    except Exception:
        pass
    
    return StorageType.UNKNOWN

def _detect_storage_type_linux(path: Path) -> StorageType:
    """Linux storage detection via sysfs."""
    try:
        # Resolve to mount point and find device
        import os
        device = os.path.realpath(path)
        
        # Check for NVMe
        if Path("/sys/block").glob("nvme*"):
            # Check if path is on NVMe
            # ... device mapping logic
            return StorageType.NVME_GEN4  # Default assumption
        
        # Check rotational flag
        # rotational = 0 means SSD, 1 means HDD
        for block_dev in Path("/sys/block").iterdir():
            rot_file = block_dev / "queue" / "rotational"
            if rot_file.exists():
                rotational = int(rot_file.read_text().strip())
                if rotational == 0:
                    return StorageType.SATA_SSD
                else:
                    return StorageType.HDD
    except Exception:
        pass
    
    return StorageType.UNKNOWN

def _detect_storage_type_macos(path: Path) -> StorageType:
    """macOS storage detection - all modern Macs use NVMe."""
    # All Apple Silicon Macs have internal NVMe
    # External drives could be different but we assume internal
    return StorageType.NVME_GEN4
```

### 4.4 Space-Constrained Recommendations

When `free_gb < recommended_total_gb`:

```python
@dataclass
class SpaceConstrainedRecommendation:
    fits: bool
    adjusted_models: List[Model]
    removed_models: List[Model]
    cloud_fallback_models: List[Model]
    space_needed_gb: float
    space_available_gb: float
    suggestions: List[str]

def adjust_for_space(
    recommendations: List[Model],
    storage: StorageProfile,
    priorities: Dict[str, int]  # Use case -> priority (1=highest)
) -> SpaceConstrainedRecommendation:
    """Adjust recommendations to fit available space."""
    
    total_size = sum(m.size_gb for m in recommendations)
    buffer_gb = 10
    
    if storage.free_gb >= total_size + buffer_gb:
        return SpaceConstrainedRecommendation(
            fits=True,
            adjusted_models=recommendations,
            removed_models=[],
            cloud_fallback_models=[],
            space_needed_gb=total_size,
            space_available_gb=storage.free_gb,
            suggestions=[],
        )
    
    # Sort by priority (lower = more important)
    sorted_models = sorted(recommendations, 
        key=lambda m: priorities.get(m.use_case, 99))
    
    # Greedily fit models by priority
    fitted = []
    removed = []
    cloud_fallback = []
    current_size = 0
    
    for model in sorted_models:
        if current_size + model.size_gb + buffer_gb <= storage.free_gb:
            fitted.append(model)
            current_size += model.size_gb
        else:
            removed.append(model)
            if model.has_cloud_alternative:
                cloud_fallback.append(model)
    
    # Generate suggestions
    suggestions = []
    if removed:
        space_short = total_size - storage.free_gb + buffer_gb
        suggestions.append(f"Free up {space_short:.0f} GB to install all models")
        suggestions.append("Or use cloud APIs for removed models")
    
    return SpaceConstrainedRecommendation(
        fits=False,
        adjusted_models=fitted,
        removed_models=removed,
        cloud_fallback_models=cloud_fallback,
        space_needed_gb=total_size,
        space_available_gb=storage.free_gb,
        suggestions=suggestions,
    )
```

### 4.5 Speed Preference Warning

```python
def get_storage_warning(
    storage: StorageProfile,
    speed_preference: str,  # "speed", "balanced", "quality"
    largest_model_gb: float
) -> Optional[str]:
    """Generate warning for speed-focused users on slow storage."""
    
    if speed_preference != "speed":
        return None
    
    if storage.tier == StorageTier.FAST:
        return None
    
    load_time = storage.estimate_load_time(largest_model_gb)
    
    if storage.tier == StorageTier.SLOW:
        return f"""⚠️ Storage Speed Notice

Your models are stored on an HDD (~{storage.estimated_read_mbps} MB/s).
With your speed preference, this may cause friction:

• Largest model ({largest_model_gb:.1f} GB): ~{load_time:.0f} sec to load
• Switching models: {load_time/2:.0f}-{load_time:.0f} seconds each time

Recommendations:
• Install key models on an SSD if available
• Use quantized variants (smaller, faster to load)
• Keep your most-used model loaded, minimize switching"""
    
    elif storage.tier == StorageTier.MODERATE:
        return f"""💡 Storage Note

Your models are on a SATA SSD (~{storage.estimated_read_mbps} MB/s).
Model loading is moderate - largest model loads in ~{load_time:.0f} sec.

For even faster iteration, consider NVMe storage."""
    
    return None
```

---

## 5. RAM & Offload Capacity

### 5.1 Why RAM Matters for AI

When GPU VRAM is insufficient:
1. **Layer offloading** - Model layers can run on CPU using system RAM
2. **GGUF models** - Designed for CPU/RAM inference
3. **Hybrid execution** - llama.cpp can split layers between GPU and CPU

### 5.2 Offload Performance Reality

| Execution Location | Relative Speed | Use Case |
|-------------------|----------------|----------|
| Full GPU (VRAM) | 1.0x (baseline) | Ideal |
| GPU + CPU offload | 0.1-0.5x | Enables larger models |
| Full CPU (RAM) | 0.02-0.1x | Fallback only |

**Key insight**: Offload is 10-50x slower but **enables models that otherwise couldn't run**.

### 5.3 Detection Implementation

```python
import psutil
from dataclasses import dataclass

@dataclass
class RAMProfile:
    total_gb: float
    available_gb: float           # Not used by OS/apps
    usable_for_offload_gb: float  # Conservative estimate for AI use
    
    def can_offload_model(self, model_ram_requirement_gb: float) -> bool:
        """Check if model can be offloaded to RAM."""
        return self.usable_for_offload_gb >= model_ram_requirement_gb

def detect_ram() -> RAMProfile:
    """Detect RAM capacity and availability."""
    mem = psutil.virtual_memory()
    
    total_gb = mem.total / (1024**3)
    available_gb = mem.available / (1024**3)
    
    # Conservative estimate: leave space for OS, use safety factor for remainder
    # OS_RESERVED_RAM_GB = 4.0
    # OFFLOAD_SAFETY_FACTOR = 0.8
    usable = max(0, (available_gb - OS_RESERVED_RAM_GB) * OFFLOAD_SAFETY_FACTOR)
    
    return RAMProfile(
        total_gb=total_gb,
        available_gb=available_gb,
        usable_for_offload_gb=usable,
    )
```

### 5.4 Effective Capacity Calculation

```python
def calculate_effective_capacity(
    gpu: GPUProfile,
    ram: RAMProfile,
    cpu: CPUProfile
) -> dict:
    """Calculate what models can run with offloading."""
    
    # Pure GPU capacity
    gpu_only = gpu.vram_gb
    
    # With offload (if CPU is capable)
    if cpu.tier in (CPUTier.HIGH, CPUTier.MEDIUM):
        # Can offload to RAM, but with performance penalty
        with_offload = gpu.vram_gb + ram.usable_for_offload_gb
        offload_viable = True
    else:
        with_offload = gpu.vram_gb
        offload_viable = False
    
    return {
        "gpu_only_gb": gpu_only,
        "with_offload_gb": with_offload,
        "offload_viable": offload_viable,
        "offload_speed_factor": 0.2 if offload_viable else 0,  # ~5x slower
    }
```

### 5.5 Recommendation Integration

```python
def can_run_model(
    model: Model,
    gpu: GPUProfile,
    ram: RAMProfile,
    cpu: CPUProfile,
    accept_slow: bool = False
) -> tuple[bool, str]:
    """
    Determine if model can run and how.
    
    Returns:
        (can_run, execution_mode)
        execution_mode: "gpu", "gpu_offload", "cpu_only", "cannot_run"
    """
    capacity = calculate_effective_capacity(gpu, ram, cpu)
    
    # Fits in VRAM - ideal
    if model.vram_required_gb <= capacity["gpu_only_gb"]:
        return (True, "gpu")
    
    # Fits with offload
    if model.vram_required_gb <= capacity["with_offload_gb"]:
        if accept_slow or capacity["offload_viable"]:
            return (True, "gpu_offload")
    
    # CPU only (GGUF models)
    if model.supports_cpu_inference and cpu.tier != CPUTier.MINIMAL:
        if model.ram_required_gb <= ram.usable_for_offload_gb:
            return (True, "cpu_only")
    
    return (False, "cannot_run")
```

---

## 6. Composite HardwareProfile

### 6.1 Complete Profile

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class HardwareProfile:
    """Complete hardware profile for recommendation engine."""
    
    # GPU
    gpu: GPUProfile
    
    # CPU
    cpu: CPUProfile
    
    # Storage (for installation path)
    storage: StorageProfile
    
    # RAM
    ram: RAMProfile
    
    # Form factor
    is_laptop: bool = False
    sustained_performance_ratio: float = 1.0
    
    # Platform
    platform: PlatformType = PlatformType.UNKNOWN
    
    # Derived tier (based on effective GPU capacity)
    tier: HardwareTier = HardwareTier.MINIMAL
    
    # Warnings for UI display
    warnings: List[str] = field(default_factory=list)
    
    # Effective capacities
    effective_vram_gb: float = 0
    effective_capacity_with_offload_gb: float = 0
    
    def __post_init__(self):
        self._calculate_derived_fields()
    
    def _calculate_derived_fields(self):
        # Apply platform-specific adjustments
        if self.gpu.unified_memory:
            # Apple Silicon: already has 75% ceiling applied
            self.effective_vram_gb = self.gpu.vram_gb
        else:
            self.effective_vram_gb = self.gpu.vram_gb
        
        # Apply laptop performance ratio
        if self.is_laptop and self.sustained_performance_ratio < 1.0:
            # Don't reduce VRAM, but note for throughput expectations
            self.warnings.append(
                f"Laptop GPU detected - ~{self.sustained_performance_ratio*100:.0f}% "
                "sustained performance vs desktop"
            )
        
        # Calculate offload capacity
        capacity = calculate_effective_capacity(self.gpu, self.ram, self.cpu)
        self.effective_capacity_with_offload_gb = capacity["with_offload_gb"]
        
        # Determine tier
        self.tier = self._calculate_tier()
    
    def _calculate_tier(self) -> HardwareTier:
        """
        Calculate tier based on EFFECTIVE capacity (VRAM + viable offload).

        This reflects actual runnable model sizes, not just native GPU VRAM.
        A machine with 24GB VRAM + 64GB fast RAM can run larger models via
        offloading than one with 24GB VRAM + 8GB slow RAM.

        Decision: PLAN_v3.md 2026-01-03
        """
        # Use effective capacity (includes offload if viable)
        capacity = self.effective_capacity_with_offload_gb

        # Fall back to VRAM if offload calculation not available
        if capacity <= 0:
            capacity = self.effective_vram_gb

        if capacity >= 48:
            return HardwareTier.WORKSTATION
        elif capacity >= 16:
            return HardwareTier.PROFESSIONAL
        elif capacity >= 12:
            return HardwareTier.PROSUMER
        elif capacity >= 8:
            return HardwareTier.CONSUMER
        elif capacity >= 4:
            return HardwareTier.ENTRY
        else:
            return HardwareTier.MINIMAL
```

### 6.2 Detection Orchestration

```python
def detect_hardware(installation_path: Path = None) -> HardwareProfile:
    """
    Comprehensive hardware detection.
    
    Args:
        installation_path: Where models will be installed (for storage detection)
    
    Returns:
        Complete HardwareProfile for recommendation engine
    """
    if installation_path is None:
        installation_path = Path.cwd()
    
    # Detect GPU
    gpu = detect_gpu()  # Platform-specific dispatcher
    
    # Detect CPU
    cpu = detect_cpu()
    
    # Detect storage
    storage = detect_storage(installation_path)
    
    # Detect RAM
    ram = detect_ram()
    
    # Detect form factor (for NVIDIA)
    is_laptop = False
    perf_ratio = 1.0
    if gpu.vendor == "nvidia":
        is_laptop = detect_is_mobile(gpu.name)
        power_limit = detect_power_limit()
        if power_limit:
            perf_ratio = get_sustained_performance_ratio(gpu.name, power_limit)
    
    # Determine platform type
    platform = determine_platform_type(gpu)
    
    return HardwareProfile(
        gpu=gpu,
        cpu=cpu,
        storage=storage,
        ram=ram,
        is_laptop=is_laptop,
        sustained_performance_ratio=perf_ratio,
        platform=platform,
    )
```

---

## 7. UI Summary Display

```
┌─────────────────────────────────────────────────────────────┐
│  Hardware Profile                                           │
├─────────────────────────────────────────────────────────────┤
│  GPU: NVIDIA GeForce RTX 4090 Laptop GPU                    │
│       VRAM: 24 GB │ Compute: 8.9 │ FP8: ✓                   │
│       ⚠️ Laptop - ~62% sustained performance                │
│                                                             │
│  CPU: AMD Ryzen 9 7945HX (16 cores / 32 threads)           │
│       Tier: HIGH │ AVX2: ✓ │ Offload: Viable                │
│                                                             │
│  RAM: 64 GB total │ ~48 GB available for AI                │
│       Combined capacity with offload: ~72 GB                │
│                                                             │
│  Storage: NVMe Gen4 │ 1.8 TB free of 2 TB                  │
│           Tier: FAST │ Load speed: ~5,000 MB/s             │
│                                                             │
│  Overall Tier: PROFESSIONAL                                 │
│  Platform: Windows + NVIDIA                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Integration Points

**See `AI_UNIVERSAL_SUITE_SPEC_v3.md` Section 6 for complete recommendation engine integration.**

### 8.1 Recommendation Engine (Layer 1 - CSP)

Hardware profile feeds into constraint satisfaction:
- `effective_vram_gb` → VRAM constraints
- `storage.free_gb` → Space constraints
- `cpu.tier` → Offload viability
- `gpu.compute_capability` → Precision support (FP8, etc.)
- `platform_constraints` → Model exclusions

### 8.2 Recommendation Engine (Layer 3 - TOPSIS)

Hardware affects scoring criteria:
- `hardware_fit` → VRAM headroom + platform penalties + form factor
- `speed_fit` → Storage speed + model load time
- `sustained_performance_ratio` → Intensity-based penalty

### 8.3 Resolution Cascade

Hardware enables fallback options:
- CPU offload requires: `cpu.tier` HIGH/MEDIUM + `ram.usable_for_offload_gb` + AVX2
- Space adjustment requires: `storage.free_gb` < total model size

### 8.4 Onboarding UI

- Display detected hardware for confirmation
- Allow manual override if detection fails
- Show tier classification with explanation

### 8.5 Warning System

Hardware triggers user-facing warnings:
- `is_laptop` + `sustained_performance_ratio < 0.8` → Laptop warning
- `storage.tier == SLOW` + speed priority → Storage warning
- `execution_mode == gpu_offload` → Offload notification
- `ram.usable_for_offload_gb < 16` → Low RAM warning
- `!supports_avx2` + GGUF models → Performance warning

---

## References

- NVIDIA nvidia-smi documentation
- Apple Silicon memory bandwidth specifications
- AMD ROCm documentation
- psutil library documentation
