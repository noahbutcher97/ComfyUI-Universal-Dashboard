# Architecture Principles

**Purpose**: Core architectural principles for AI Universal Suite development
**Audience**: Human developers and AI agents working on this codebase
**Last Updated**: January 2026

---

## Overview

This document captures architectural principles discovered during development. These principles are **mandatory requirements** for all new code and refactoring efforts.

**If code violates these principles, the code is wrong.**

---

## 1. I/O Data Normalization Standard

### Principle

**All external I/O data must be normalized before use. Never trust raw output from shells, files, APIs, or user input.**

### Rationale

External data sources are inherently unreliable:
- **Shell profiles** can inject unexpected text (PowerShell profiles, bash aliases)
- **File encodings** vary across platforms (UTF-8 with BOM, UTF-16, Latin-1)
- **API responses** may include non-JSON text (error messages, redirects)
- **User input** may contain path traversal, injection, or invalid characters

### Implementation

Create `src/utils/io_utils.py` with utilities for each I/O type:

#### Shell Output Utilities

```python
def run_powershell(command: str, timeout: int = 30) -> str:
    """
    Run PowerShell with -NoProfile to prevent profile injection.

    Returns cleaned output with whitespace stripped.
    Raises CalledProcessError on non-zero exit.
    """
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW  # Windows only
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, command, result.stdout, result.stderr
        )
    return result.stdout.strip()


def run_shell(command: list[str], timeout: int = 30) -> str:
    """
    Run shell command without inheriting user environment.

    Use for: macOS sysctl, Linux /proc reads, etc.
    """
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}  # Minimal PATH
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env
    )
    return result.stdout.strip()


def extract_number(text: str) -> Optional[float]:
    """
    Extract first numeric value from potentially noisy output.

    Handles: "Loading profile...\n16384\n", "Value: 16.5 GB"
    """
    for line in text.splitlines():
        line = line.strip()
        # Try whole line as number
        try:
            return float(line.replace(",", ""))
        except ValueError:
            pass
        # Try extracting number from line
        match = re.search(r"[-+]?\d*\.?\d+", line)
        if match:
            return float(match.group())
    return None


def extract_json(text: str) -> Optional[dict]:
    """
    Extract JSON object from mixed text output.

    Handles: "Profile loaded\n{\"key\": \"value\"}\nDone"
    """
    # Find JSON boundaries
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None

    json_str = text[start:end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
```

#### File I/O Utilities

```python
def read_text_normalized(path: Path, encoding: str = "utf-8") -> str:
    """
    Read text file with encoding normalization.

    - Removes BOM if present
    - Normalizes line endings to \n
    - Falls back to latin-1 if UTF-8 fails
    """
    try:
        content = path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")

    # Remove UTF-8 BOM if present
    if content.startswith("\ufeff"):
        content = content[1:]

    # Normalize line endings
    return content.replace("\r\n", "\n").replace("\r", "\n")


def read_json_safe(path: Path) -> Optional[dict]:
    """
    Read JSON file with error handling and normalization.

    Returns None on any error (file not found, parse error, etc.)
    """
    try:
        text = read_text_normalized(path)
        return json.loads(text)
    except (OSError, json.JSONDecodeError):
        return None
```

### Current Implementation Status

| File | Current State | Action Needed |
|------|---------------|---------------|
| `services/hardware/ram.py` | Uses utilities | Done ✓ |
| `services/hardware/storage.py` | Uses utilities | Done ✓ |
| `services/hardware/nvidia.py` | Uses utilities | Done ✓ |
| `services/hardware/cpu.py` | Windows registry (safe) | N/A |
| `services/comfy_service.py` | Direct subprocess | Audit and update |

**Shared utilities**: `src/utils/subprocess_utils.py` provides:
- `run_powershell()` - PowerShell with `-NoProfile` isolation
- `run_command()` - General command execution
- `extract_number()` - Extract numbers from noisy output
- `extract_json()` - Extract JSON from mixed text

### Anti-Patterns (Do NOT Do This)

```python
# BAD: Trusting raw PowerShell output
result = subprocess.run(["powershell", command], capture_output=True, text=True)
value = int(result.stdout)  # Will crash on profile injection

# BAD: Assuming UTF-8 without fallback
content = path.read_text()  # Crashes on non-UTF-8 files

# BAD: Parsing API response without validation
data = response.json()
return data["result"]["value"]  # KeyError if structure changes
```

---

## 2. No Magic Numbers Principle

### Principle

**Never use arbitrary estimates or magic numbers for calculations. Use real algorithmic/formulaic protocols based on actual data.**

### Rationale

Magic numbers:
- Are impossible to validate or debug
- Cannot adapt to different hardware configurations
- Make code behavior opaque to reviewers
- Often become incorrect as hardware evolves

### Examples

#### Bad: Magic Number

```python
# BAD: Where does 0.2 come from? Why not 0.15 or 0.25?
def estimate_offload_speed(gpu_speed: float) -> float:
    return gpu_speed * 0.2  # "CPU is about 5x slower than GPU"
```

#### Good: Formula-Based

```python
# GOOD: Physics-grounded calculation with real data
def estimate_offload_speed_ratio(ram_bandwidth_gbps: float, gpu_bandwidth_gbps: float) -> float:
    """
    Calculate CPU offload speed relative to GPU execution.

    Formula: speed_ratio = ram_bandwidth / gpu_bandwidth

    Example:
        DDR5-4800 (38.4 GB/s) vs RTX 4090 (1008 GB/s)
        speed_ratio = 38.4 / 1008 = 0.038 (~26x slower)

    Sources:
        - DDR specifications: JEDEC standards
        - GPU bandwidth: Vendor published specs
    """
    if gpu_bandwidth_gbps <= 0:
        return 0.0
    return ram_bandwidth_gbps / gpu_bandwidth_gbps
```

### When Numbers Are Acceptable

Some constants are not "magic" because they have clear definitions:

```python
# OK: Physical/standard constants
BYTES_PER_GB = 1024 ** 3  # Definition of GB
APPLE_SILICON_MEMORY_CEILING = 0.75  # Published Apple recommendation

# OK: Tier boundaries (policy decisions, documented)
CPU_TIER_HIGH_CORES = 16  # Defined in SPEC_v3 Section 4.5
CPU_TIER_MEDIUM_CORES = 8
```

The difference: **documented policy decisions** vs **arbitrary guesses**.

---

## 3. Lookup Table Approach for Hardware Specs

### Principle

**When no reliable cross-platform API exists for hardware specifications, use static lookup tables based on published specifications.**

### Rationale

- Many hardware characteristics (memory bandwidth, TDP) have no reliable runtime API
- Published specifications are authoritative
- Lookup tables are auditable and updatable
- Better than guessing or using inaccurate heuristics

### Implementation Pattern

```python
# 1. Define the lookup table with clear source documentation
GPU_BANDWIDTH_GBPS = {
    # Source: NVIDIA official specifications
    # Blackwell
    "rtx 5090": 1792,
    "rtx 5080": 960,
    "rtx 5070 ti": 896,
    "rtx 5070": 672,
    # Ada Lovelace
    "rtx 4090": 1008,
    "rtx 4080 super": 736,
    "rtx 4080": 716,
    # ... etc
}

# 2. Normalize input before lookup
def lookup_gpu_bandwidth(gpu_name: str) -> Optional[float]:
    """
    Look up GPU memory bandwidth from published specifications.

    Args:
        gpu_name: GPU name from nvidia-smi (e.g., "NVIDIA GeForce RTX 4090")

    Returns:
        Memory bandwidth in GB/s, or None if not found
    """
    # Normalize: lowercase, remove vendor prefix
    normalized = gpu_name.lower()
    normalized = normalized.replace("nvidia", "").replace("geforce", "").strip()

    # Try exact match first
    if normalized in GPU_BANDWIDTH_GBPS:
        return GPU_BANDWIDTH_GBPS[normalized]

    # Try partial match for variants
    for key, value in GPU_BANDWIDTH_GBPS.items():
        if key in normalized:
            return value

    return None
```

### Current Lookup Tables

| Table | Location | Data Source |
|-------|----------|-------------|
| GPU memory bandwidth | `nvidia.py`, `amd_rocm.py` | Vendor specs |
| GPU reference TDP | `form_factor.py` | Vendor specs |
| Apple Silicon bandwidth | `apple_silicon.py` | Apple specs |
| DDR bandwidth by type | `ram.py` | JEDEC standards |

### Maintenance

- Update tables when new hardware releases
- Document the source of each entry
- Use consistent units (GB/s for bandwidth, Watts for TDP)

### Encapsulated Lookup Pattern

**When a function needs data from a lookup table, it should accept an identifier (e.g., `gpu_name`) and perform the lookup internally, rather than requiring the caller to pass the looked-up value.**

#### Rationale

- **Reduces duplication**: Callers don't need to know about lookup tables
- **Ensures consistency**: Lookup logic is in one place
- **Enables caching**: Function can cache lookup results
- **Simplifies API**: Fewer parameters, clearer intent

#### Bad Pattern (Leaky Abstraction)

```python
# BAD: Caller must know about and perform lookup
def calculate_speed_ratio(gpu_bandwidth_gbps: float, ram_bandwidth_gbps: float) -> float:
    """Caller is responsible for looking up both values."""
    return ram_bandwidth_gbps / gpu_bandwidth_gbps

# Usage requires caller to do lookups:
gpu_bw = GPU_BANDWIDTH_GBPS.get(gpu_name, 0)  # Caller knows about lookup table
ram_bw = RAM_BANDWIDTH_GBPS.get(ram_type, 0)  # Caller knows about lookup table
ratio = calculate_speed_ratio(gpu_bw, ram_bw)
```

#### Good Pattern (Encapsulated)

```python
# GOOD: Function takes identifier and does lookup internally
def calculate_sustained_performance_ratio(
    gpu_name: str,
    actual_power_limit: float,
) -> Tuple[bool, float, Optional[int]]:
    """
    Takes GPU name and does TDP lookup internally.

    Returns:
        (is_laptop, performance_ratio, reference_tdp)
    """
    # Internal lookup - caller doesn't need to know about GPU_REFERENCE_TDP
    ref_tdp = _lookup_reference_tdp(gpu_name)
    if ref_tdp is None:
        return (False, 1.0, None)

    # Laptop detection and ratio calculation
    is_laptop = actual_power_limit < ref_tdp * 0.7
    ratio = math.sqrt(actual_power_limit / ref_tdp)
    return (is_laptop, ratio, ref_tdp)

# Usage is simple - caller just passes identifiers:
is_laptop, ratio, ref_tdp = calculate_sustained_performance_ratio(
    gpu_name="NVIDIA GeForce RTX 4090",
    actual_power_limit=175.0
)
```

#### Hybrid Pattern (Profile-Based)

When a dataclass already contains the looked-up value (from detection), use it directly:

```python
# RAMProfile already contains bandwidth_gbps from detection
def calculate_offload_viability(
    vram_gb: float,
    ram_profile: RAMProfile,  # Contains bandwidth_gbps
    cpu_can_offload: bool,
    gpu_bandwidth_gbps: Optional[float] = None,  # From HardwareProfile
) -> dict:
    """
    RAM bandwidth is read from ram_profile.bandwidth_gbps (encapsulated).
    GPU bandwidth comes from HardwareProfile.gpu_bandwidth_gbps.
    """
    ram_bandwidth = ram_profile.bandwidth_gbps or 0.0  # Encapsulated in profile

    if gpu_bandwidth_gbps and ram_bandwidth > 0:
        speed_ratio = ram_bandwidth / gpu_bandwidth_gbps
    else:
        speed_ratio = None
    # ...
```

#### Summary

| Pattern | When to Use |
|---------|-------------|
| **Encapsulated function** | Function needs lookup for calculation |
| **Profile-based** | Detection already performed lookup, stored in profile |
| **Direct lookup export** | Caller explicitly needs raw data (rare) |

---

## 4. Nested Profile Pattern

### Principle

**Complex hardware detection uses nested dataclass profiles. Each profile has its own tier classification and helper methods.**

### Rationale

- **Separation of concerns**: GPU, CPU, RAM, Storage each have distinct characteristics
- **Type safety**: Each profile validates its own fields
- **Testability**: Test each profile independently
- **Extensibility**: Add new profiles without bloating parent class

### Implementation

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class CPUTier(Enum):
    HIGH = "high"      # 16+ cores
    MEDIUM = "medium"  # 8-15 cores
    LOW = "low"        # 4-7 cores
    MINIMAL = "minimal"  # <4 cores

@dataclass
class CPUProfile:
    """CPU detection results with tier classification."""
    model: str
    architecture: str  # "x86_64", "arm64"
    physical_cores: int
    logical_cores: int
    supports_avx2: bool = False

    # Derived field, calculated in __post_init__
    tier: CPUTier = field(init=False)

    def __post_init__(self):
        self.tier = self._calculate_tier()

    def _calculate_tier(self) -> CPUTier:
        if self.physical_cores >= 16:
            return CPUTier.HIGH
        elif self.physical_cores >= 8:
            return CPUTier.MEDIUM
        elif self.physical_cores >= 4:
            return CPUTier.LOW
        return CPUTier.MINIMAL

    def can_offload_gguf(self) -> bool:
        """Check if CPU can handle GGUF offload."""
        if self.architecture == "arm64":
            return True  # ARM doesn't need AVX
        return self.supports_avx2


@dataclass
class RAMProfile:
    """RAM detection results with offload capacity."""
    total_gb: float
    available_gb: float
    memory_type: str  # "DDR4", "DDR5"
    bandwidth_gbps: float

    @property
    def usable_for_offload_gb(self) -> float:
        """Conservative estimate of RAM available for AI workloads."""
        return max(0, (self.available_gb - 4) * 0.8)


@dataclass
class HardwareProfile:
    """Complete hardware profile combining all components."""
    # Primary detection
    gpu_vendor: str
    gpu_name: str
    vram_gb: float

    # Nested profiles
    cpu: Optional[CPUProfile] = None
    ram: Optional[RAMProfile] = None
    storage: Optional[StorageProfile] = None
    form_factor: Optional[FormFactorProfile] = None

    # Derived fields
    tier: HardwareTier = field(init=False)
    warnings: list[str] = field(default_factory=list)
```

### Benefits

1. **Clear ownership**: `CPUProfile.can_offload_gguf()` belongs with CPU logic
2. **Incremental detection**: Can build profile piece by piece
3. **Optional components**: Not all hardware has all features
4. **Easy serialization**: Each profile can be serialized/deserialized independently

---

## 5. Explicit Failure Over Silent Defaults

### Principle

**When detection fails, fail explicitly with a clear error. Never silently fall back to arbitrary defaults.**

### Rationale

Silent defaults cause worse problems than explicit failures:
- Wrong recommendations (e.g., 16GB default when user has 8GB)
- Difficult debugging ("why did it think I have 16GB?")
- False confidence in incorrect data

### Implementation

```python
# BAD: Silent fallback to arbitrary value
def detect_ram_gb() -> float:
    try:
        # Detection logic
        return detected_value
    except Exception:
        return 16.0  # "Reasonable default"

# GOOD: Explicit failure with clear error
class HardwareDetectionError(Exception):
    """Raised when hardware detection fails."""
    pass

def detect_ram_gb() -> float:
    try:
        # Primary detection
        return primary_method()
    except Exception as e:
        logger.warning(f"Primary RAM detection failed: {e}")

    try:
        # Fallback to alternative method
        return alternative_method()
    except Exception as e:
        logger.warning(f"Alternative RAM detection failed: {e}")

    # All methods failed - raise, don't guess
    raise HardwareDetectionError(
        "Could not detect RAM. Please enter RAM size manually in settings."
    )
```

### When Defaults Are Acceptable

Defaults are OK when:
1. They are **safe minimums** (e.g., assuming no FP8 support if unknown)
2. They are **explicitly documented** as conservative
3. The user is **informed** that detection failed

```python
# OK: Safe minimum with user notification
def detect_gpu_features() -> GPUFeatures:
    try:
        return full_detection()
    except Exception:
        logger.warning("GPU feature detection failed, using safe defaults")
        return GPUFeatures(
            supports_fp8=False,  # Safe: won't recommend unsupported models
            supports_bf16=False,  # Safe: falls back to FP16
            note="Feature detection failed - using conservative defaults"
        )
```

---

## Summary Checklist

Before submitting code, verify:

- [ ] **I/O Normalization**: All shell output parsed with extraction utilities
- [ ] **No Magic Numbers**: All calculations use formulas or documented constants
- [ ] **Lookup Tables**: Hardware specs from published sources, not guesses
- [ ] **Encapsulated Lookups**: Functions accept identifiers, not raw looked-up values
- [ ] **Nested Profiles**: Complex data uses dataclasses with helper methods
- [ ] **Explicit Failure**: Detection failures raise errors, not silent defaults

For business/architectural decisions (e.g., tier calculation rules), see `docs/plan/PLAN_v3.md` Section 1 Decision Log.

---

## References

- **HARDWARE_DETECTION.md**: Technical specification for detection
- **MIGRATION_PROTOCOL.md**: How to update existing code
- **CLAUDE.md**: Quick reference for AI agents
- **PLAN_v3.md Section 1**: Decision log with architectural decisions

---

*This document is normative. Code that violates these principles should be fixed.*
