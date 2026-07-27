"""
Abstract base class for MCU target backends.

Third-party packages can register new backends via
entry_points "hardware2code.backends" in their setup.cfg / pyproject.toml.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class TargetBackend(ABC):
    """Interface for chip-specific backend implementations.

    Each backend provides:
      - MCU family identification
      - Template directories (supporting multi-level override)
      - Pin/clock context builders
      - Default HAL source file lists
    """

    @abstractmethod
    def get_mcu_family(self) -> str:
        """Return the MCU family identifier, e.g. 'STM32G0'."""

    @abstractmethod
    def get_template_dirs(self) -> List[str]:
        """Return template search directories in priority order.

        The first directory has highest priority. Directories later in
        the list can override files from earlier directories.
        """

    @abstractmethod
    def build_pin_context(self, raw_pins: list) -> dict:
        """Process raw pin definitions into a template-ready context.

        Args:
            raw_pins: List of pin dicts from hardware.yaml.

        Returns:
            dict with processed pin information.
        """

    @abstractmethod
    def build_clock_context(self, raw_clock: dict) -> dict:
        """Build clock configuration context.

        Args:
            raw_clock: Clock section from hardware.yaml.

        Returns:
            dict with clock context (hclk, pclk, etc.).
        """

    @abstractmethod
    def get_default_hal_sources(self) -> List[str]:
        """Return list of default HAL source file paths.

        These are the core HAL files that every project needs.
        """

    def get_mcu_info(self) -> dict:
        """Return MCU metadata (optional override).

        Returns:
            dict with keys like 'core', 'flash_kb', 'ram_kb'.
        """
        return {}

    def validate_pin(self, pin_id: str) -> Optional[str]:
        """Validate a pin ID for this backend. Returns error message or None.

        Args:
            pin_id: Pin identifier string (e.g., 'PA2').

        Returns:
            Error message string or None if valid.
        """
        return None  # Default: no validation
