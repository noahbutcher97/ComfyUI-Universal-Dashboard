"""
Hardware detection base class per SPEC_v3 Section 4.1.

Provides abstract interface for platform-specific detection strategies.

NEW in Phase 1 - does not replace existing code.
See: docs/MIGRATION_PROTOCOL.md Section 3
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.schemas.hardware import HardwareProfile


class HardwareDetector(ABC):
    """
    Abstract base class for platform-specific hardware detection.

    Each platform (Apple Silicon, NVIDIA, AMD ROCm) has unique APIs
    and constraints, so detection is implemented separately per platform.
    """

    @abstractmethod
    def detect(self) -> HardwareProfile:
        """
        Detect hardware and return a HardwareProfile.

        Implementations should:
        1. Use platform-specific APIs to gather hardware info
        2. Apply platform-specific constraints (e.g., 75% memory ceiling for Apple)
        3. Return a fully populated HardwareProfile

        Raises:
            DetectionFailedError: If detection fails and no fallback is possible
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this detector is applicable for the current system.

        Returns:
            True if this detector should be used on the current platform
        """
        pass

    def get_thermal_state(self) -> Optional[str]:
        """
        Get current GPU thermal state.

        Override in subclasses that support thermal monitoring.

        Returns:
            "normal", "warning", "critical", or None if unsupported
        """
        return None


class DetectionFailedError(Exception):
    """
    Raised when hardware detection fails and no fallback is available.

    Per SPEC_v3: We must fail explicitly rather than use dangerous fallbacks
    (e.g., assuming 16GB RAM which could cause wrong recommendations).
    """

    def __init__(self, component: str, message: str, details: Optional[str] = None):
        self.component = component
        self.message = message
        self.details = details
        super().__init__(f"Failed to detect {component}: {message}")


class NoCUDAError(DetectionFailedError):
    """Raised when CUDA is expected but not available."""

    def __init__(self):
        super().__init__(
            component="CUDA",
            message="CUDA not available",
            details="PyTorch CUDA support not detected. Install CUDA-enabled PyTorch."
        )


class NoROCmError(DetectionFailedError):
    """Raised when ROCm is expected but not available."""

    def __init__(self):
        super().__init__(
            component="ROCm",
            message="ROCm not available",
            details="AMD ROCm not detected. Install ROCm and ROCm-enabled PyTorch."
        )
