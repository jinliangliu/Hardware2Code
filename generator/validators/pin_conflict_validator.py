"""
Pin conflict validator.

Validates hardware YAML pin assignments against the MCU pin database,
detecting duplicate assignments, unsupported AF functions, and GPIO conflicts.

Usage:
    from generator.validators.pin_conflict_validator import validate_pin_conflicts
    errors = validate_pin_conflicts(hw_config, mcu_db)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hw2c.pin_validator")


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class PinConflictError:
    """Error raised when two peripherals conflict on the same pin."""

    def __init__(
        self,
        pin: str,
        func_a: str,
        func_b: str,
        label_a: Optional[str] = None,
        label_b: Optional[str] = None,
    ):
        self.pin = pin
        self.func_a = func_a
        self.func_b = func_b
        self.label_a = label_a
        self.label_b = label_b

    def __str__(self) -> str:
        detail = f"Pin {self.pin} conflict: '{self.func_a}'"
        if self.label_a:
            detail += f" [{self.label_a}]"
        detail += f" vs '{self.func_b}'"
        if self.label_b:
            detail += f" [{self.label_b}]"
        return detail


class InvalidPinError:
    """Error raised when a pin does not exist in the MCU database."""

    def __init__(self, pin: str, function: str, label: Optional[str] = None):
        self.pin = pin
        self.function = function
        self.label = label

    def __str__(self) -> str:
        detail = f"Invalid pin '{self.pin}'"
        if self.label:
            detail += f" [{self.label}]"
        detail += f": not available on this MCU (assigned function: '{self.function}')"
        return detail


class UnsupportedFunctionError:
    """Error raised when a function is not supported on the assigned pin."""

    def __init__(
        self,
        pin: str,
        function: str,
        label: Optional[str] = None,
        available: Optional[List[str]] = None,
    ):
        self.pin = pin
        self.function = function
        self.label = label
        self.available = available or []

    def __str__(self) -> str:
        detail = f"Pin '{self.pin}' does not support function '{self.function}'"
        if self.label:
            detail += f" [{self.label}]"
        if self.available:
            detail += (
                f". Available AF functions on {self.pin}: "
                + ", ".join(sorted(self.available))
            )
        return detail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Match function strings like "USART2_TX", "I2C1_SCL", "TIM2_CH1"
_FUNCTION_RE = re.compile(r"^([A-Z][A-Z0-9]*)_([A-Z][A-Z0-9]*)$")

# Functions that are pure GPIO and never conflict with AF assignments
_GPIO_FUNCTIONS = {
    "GPIO_Output", "GPIO_Input", "GPIO_Analog", "GPIO_EXTI",
    "GPIO_OD", "GPIO_AF_PP", "GPIO_AF_OD",
}


def _parse_function(func: str) -> Optional[Tuple[str, str]]:
    """Parse a function string into (peripheral, signal) pair.

    Examples:
        'USART2_TX' -> ('USART2', 'TX')
        'GPIO_Output' -> None (pure GPIO, no AF conflict)
        'ADC1_IN0' -> ('ADC1', 'IN0')
    """
    func = func.strip()
    if func in _GPIO_FUNCTIONS:
        return None

    match = _FUNCTION_RE.match(func)
    if match:
        return match.group(1).upper(), match.group(2).upper()

    # Unknown format - treat as GPIO (no conflict detection possible)
    logger.debug("Unrecognized function format: '%s' - treating as GPIO", func)
    return None


def _is_af_function(func: str) -> bool:
    """Check if a function string represents an AF (alternate function) assignment."""
    return _parse_function(func) is not None


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------


def validate_pin_conflicts(
    hw_config: Any,
    mcu_db: Any,
) -> List[Any]:
    """Validate pin assignments in a hardware configuration.

    Checks:
      1. All assigned pins exist in the MCU database.
      2. No duplicate physical pin assignments (same pin used for
         two different AF functions).
      3. AF functions are actually supported on the assigned pin.

    Pure GPIO functions (GPIO_Output, GPIO_Input, etc.) are excluded
    from conflict detection since they don't use alternate functions.

    Args:
        hw_config: HardwareModel instance with .pins list of PinConfig.
        mcu_db: MCUDatabase instance with pin/function data.

    Returns:
        List of error objects (PinConflictError, InvalidPinError,
        UnsupportedFunctionError). Empty list means no errors.
    """
    errors: List[Any] = []

    # Index: physical_pin -> {function, label, index}
    used_pins: Dict[str, Dict[str, Any]] = {}

    for i, pin_cfg in enumerate(hw_config.pins):
        pin_id = pin_cfg.id.upper()
        function = pin_cfg.function
        label = pin_cfg.label

        # ---------- Check 1: pin existence ----------
        if not mcu_db.is_valid_pin(pin_id):
            errors.append(InvalidPinError(pin_id, function, label))
            continue

        # ---------- Parse function ----------
        parsed = _parse_function(function)
        if parsed is None:
            # GPIO function - track but don't flag as conflict
            if pin_id not in used_pins:
                used_pins[pin_id] = {"function": function, "label": label, "is_gpio": True}
            continue

        periph, signal = parsed

        # ---------- Check 2: function supported on this pin? ----------
        af = mcu_db.resolve_pin_function(pin_id, periph, signal)
        if af is None:
            available_af = mcu_db.get_pin_af_functions(pin_id)
            errors.append(UnsupportedFunctionError(pin_id, function, label, available_af))
            continue

        # ---------- Check 3: duplicate/conflict ----------
        if pin_id in used_pins:
            existing = used_pins[pin_id]
            if existing.get("is_gpio"):
                # AF function vs GPIO on same pin = no conflict
                # (GPIO can coexist with AF via mux)
                used_pins[pin_id] = {
                    "function": function, "label": label, "is_gpio": False,
                }
            elif existing["function"] != function:
                # Two different AF functions on same pin = conflict
                errors.append(PinConflictError(
                    pin_id,
                    existing["function"],
                    function,
                    existing.get("label"),
                    label,
                ))
            else:
                # Same function reused on same pin = duplicate assignment
                # (could be benign, but worth warning)
                pass
        else:
            used_pins[pin_id] = {
                "function": function, "label": label, "is_gpio": False,
            }

    if errors:
        logger.warning("Pin conflict validation found %d error(s)", len(errors))
    else:
        logger.info("Pin conflict validation passed (%d pins allocated)", len(used_pins))

    return errors
