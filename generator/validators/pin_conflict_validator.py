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
        alternatives: Optional[List[str]] = None,
    ):
        self.pin = pin
        self.func_a = func_a
        self.func_b = func_b
        self.label_a = label_a
        self.label_b = label_b
        self.alternatives = alternatives or []

    def __str__(self) -> str:
        detail = f"Pin {self.pin} conflict: '{self.func_a}'"
        if self.label_a:
            detail += f" [{self.label_a}]"
        detail += f" vs '{self.func_b}'"
        if self.label_b:
            detail += f" [{self.label_b}]"
        if self.alternatives:
            detail += (
                f". Alternative free pins for '{self.func_b}': "
                + ", ".join(self.alternatives[:5])
            )
            if len(self.alternatives) > 5:
                detail += f" ... and {len(self.alternatives) - 5} more"
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


class PeripheralPinRefError:
    """Error raised when a peripheral references a pin that is not declared
    in the hardware YAML `pins` list (no GPIO/AF configuration would be
    generated for it)."""

    def __init__(self, peripheral: str, field: str, pin: str):
        self.peripheral = peripheral
        self.field = field
        self.pin = pin

    def __str__(self) -> str:
        return (
            f"Peripheral '{self.peripheral}' references pin '{self.pin}' "
            f"({self.field}) which is not declared in the pins list — "
            f"no GPIO configuration would be generated for it."
        )


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

# Peripheral fields that reference physical pins (validated against the
# pins list and across peripherals).
_PERIPHERAL_PIN_FIELDS = (
    "cs_pin",
    "chip_select_pin",
    "tx_pin",
    "rx_pin",
    "de_pin",
    "rs485_de_pin",
)


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


def _find_alternative_pins(
    mcu_db: Any,
    peripheral: str,
    signal: str,
    used_pins: Dict[str, Any],
) -> List[str]:
    """Find free pins that support the given peripheral+signal combination.

    Args:
        mcu_db: MCUDatabase instance.
        peripheral: Peripheral name (e.g. 'I2C1').
        signal: Signal name (e.g. 'SCL').
        used_pins: Currently occupied pins dict.

    Returns:
        List of free pin names that support the function.
    """
    all_pins = mcu_db.get_peripheral_signals(peripheral)
    free: List[str] = []
    for entry in all_pins:
        pin = entry["pin"]
        sig = entry["signal"]
        if sig == signal and pin.upper() not in used_pins:
            free.append(pin)
    # Sort by port letter then pin number (e.g., PA0 < PA1 < PB0)
    return sorted(free, key=lambda p: (p[1], int(p[2:])))


def _collect_peripheral_pin_refs(hw_config: Any) -> List[Tuple[str, str, str, str, str]]:
    """Collect (pin, peripheral_name, field, type, uart_ref) references.

    Looks at both top-level peripheral fields and the `extra` dict
    (cs_pin / de_pin / rs485_de_pin / tx_pin / rx_pin / chip_select_pin).
    """
    refs: List[Tuple[str, str, str, str, str]] = []
    periphs = getattr(hw_config, "peripherals", None)
    if not isinstance(periphs, (list, tuple)):
        return refs

    for peri in periphs:
        name = str(getattr(peri, "name", "?") or "?")
        ptype = str(getattr(peri, "type", "") or "")
        uart_ref = str(getattr(peri, "uart", None) or "") or str(
            (getattr(peri, "extra", None) or {}).get("uart", "")
        )
        for field in _PERIPHERAL_PIN_FIELDS:
            value = getattr(peri, field, None)
            if value:
                refs.append((str(value).upper(), name, field, ptype, uart_ref))
        extra = getattr(peri, "extra", None)
        if isinstance(extra, dict):
            for field in _PERIPHERAL_PIN_FIELDS:
                value = extra.get(field)
                if value:
                    refs.append((str(value).upper(), name, field, ptype, uart_ref))
    return refs


def _pin_shared_legally(owners: List[Tuple[str, str, str, str]]) -> bool:
    """Whether multiple peripheral pin references on one pin are allowed.

    The single allowed case is the RS485 half-duplex pattern: one
    UART_Serial (extra.rs485_de_pin) plus its paired RS485 peripheral
    (de_pin, uart=<that UART>) sharing the same DE pin.
    """
    if len(owners) != 2:
        return False
    uarts = [o for o in owners if o[1] == "UART_Serial"]
    rs485s = [o for o in owners if o[1] == "RS485"]
    if len(uarts) != 1 or len(rs485s) != 1:
        return False
    uart_name, rs485_uart_ref = uarts[0][0], rs485s[0][2]
    return rs485_uart_ref.upper() == uart_name.upper()


def _validate_peripheral_pin_refs(hw_config: Any, errors: List[Any]) -> None:
    """Cross-check peripheral pin references (cs_pin, de_pin, ...).

    Checks:
      1. Referenced pins must be declared in the pins list, otherwise no
         GPIO configuration is generated (silent missing config).
      2. A physical pin may be referenced by at most ONE peripheral
         (two devices sharing one CS/DE pin would fight on the bus).
      3. A referenced pin must not be assigned an AF function in pins
         (CS/DE are GPIO outputs; AF would own the pin).
    """
    refs = _collect_peripheral_pin_refs(hw_config)
    if not refs:
        return

    declared = {p.id.upper() for p in hw_config.pins}
    pin_function = {p.id.upper(): p.function for p in hw_config.pins}

    # 1) every referenced pin must be declared
    for pin, periph, field, _pt, _ur in refs:
        if pin not in declared:
            errors.append(PeripheralPinRefError(periph, field, pin))

    # 2) no pin may be referenced by more than one peripheral
    by_pin: Dict[str, List[Tuple[str, str, str, str]]] = {}
    for pin, periph, field, ptype, uart_ref in refs:
        by_pin.setdefault(pin, []).append((periph, ptype, uart_ref, field))
    for pin, owners in by_pin.items():
        if len(owners) > 1 and not _pin_shared_legally(owners):
            a, b = owners[0], owners[1]
            errors.append(PinConflictError(
                pin,
                f"{a[0]}.{a[3]}",
                f"{b[0]}.{b[3]}",
            ))

    # 3) referenced pins must be GPIO (CS/DE), not an AF function
    for pin, periph, field, _pt, _ur in refs:
        fn = pin_function.get(pin)
        if fn and _parse_function(fn) is not None:
            errors.append(PinConflictError(
                pin, fn, f"{periph}.{field}",
            ))


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
            # GPIO function - conflicts with an existing AF assignment
            if pin_id in used_pins and not used_pins[pin_id].get("is_gpio"):
                existing = used_pins[pin_id]
                errors.append(PinConflictError(
                    pin_id,
                    existing["function"],
                    function,
                    existing.get("label"),
                    label,
                ))
            elif pin_id not in used_pins:
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
                # A physical pin can only serve one function: GPIO and an
                # AF function cannot share it.
                errors.append(PinConflictError(
                    pin_id,
                    existing["function"],
                    function,
                    existing.get("label"),
                    label,
                ))
            elif existing["function"] != function:
                # Two different AF functions on same pin = conflict
                # Query MCU database for alternative free pins
                alt_pins: List[str] = _find_alternative_pins(
                    mcu_db, periph, signal, used_pins
                )
                errors.append(PinConflictError(
                    pin_id,
                    existing["function"],
                    function,
                    existing.get("label"),
                    label,
                    alternatives=alt_pins,
                ))
            else:
                # Same function reused on same pin = duplicate assignment
                # (could be benign, but worth warning)
                pass
        else:
            used_pins[pin_id] = {
                "function": function, "label": label, "is_gpio": False,
            }

    # Peripheral pin references (cs_pin / de_pin / ...)
    _validate_peripheral_pin_refs(hw_config, errors)

    if errors:
        logger.warning("Pin conflict validation found %d error(s)", len(errors))
    else:
        logger.info("Pin conflict validation passed (%d pins allocated)", len(used_pins))

    return errors
