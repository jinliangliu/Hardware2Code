"""
cross_validator.py
Cross-validate netlist/BOM-derived pin assignments against hardware YAML.

Reports discrepancies between what the schematic says (netlist) and what
the user has declared in hardware.yaml, helping catch wiring errors and
incomplete configuration before code generation.

Usage:
    from parser.cross_validator import CrossValidator
    v = CrossValidator()
    report = v.validate(netlist_yaml_str, hw_yaml_str)
    print(report)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

logger = logging.getLogger("hw2c.cross_validator")


# ---------------------------------------------------------------------------
# Report data classes
# ---------------------------------------------------------------------------

@dataclass
class CrossIssue:
    """A single discrepancy between netlist and YAML."""

    severity: str  # "error", "warning", "info"
    code: str      # e.g. "PIN_CONFLICT", "PERIPH_MISMATCH"
    message: str
    pin: Optional[str] = None
    netlist_value: Optional[str] = None
    yaml_value: Optional[str] = None


@dataclass
class CrossReport:
    """Aggregated cross-validation results."""

    netlist_mcu: Optional[str] = None
    yaml_mcu: Optional[str] = None
    issues: List[CrossIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[CrossIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[CrossIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def __str__(self) -> str:
        lines = ["Cross-Validation Report", "=" * 24]
        if self.netlist_mcu and self.yaml_mcu:
            match = "OK" if self.netlist_mcu == self.yaml_mcu else "MISMATCH"
            lines.append(f"  MCU: netlist={self.netlist_mcu} "
                         f"YAML={self.yaml_mcu} [{match}]")
        lines.append(f"  Issues: {len(self.errors)} error(s), "
                     f"{len(self.warnings)} warning(s)")
        lines.append("")
        severity_order = {"error": 0, "warning": 1, "info": 2}
        for issue in sorted(self.issues,
                            key=lambda x: severity_order.get(x.severity, 99)):
            prefix = {"error": "E", "warning": "W", "info": "I"}.get(issue.severity, "?")
            lines.append(f"  [{prefix}] {issue.message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pin extraction helpers
# ---------------------------------------------------------------------------

def _extract_pins_from_yaml(hw_doc: dict) -> Dict[str, dict]:
    """Extract pin->function mapping from a parsed hardware.yaml doc.

    Returns:
        {pin_id: {function, label, af}} for each pin in the YAML.
    """
    pins: Dict[str, dict] = {}
    for pin_cfg in hw_doc.get("pins", []):
        pin_id = pin_cfg.get("id", "").upper()
        if not pin_id:
            continue
        pins[pin_id] = {
            "function": pin_cfg.get("function", ""),
            "label": pin_cfg.get("label", ""),
            "af": pin_cfg.get("af", 0),
        }
    return pins


def _extract_peripherals_from_yaml(hw_doc: dict) -> Dict[str, dict]:
    """Extract peripheral name->type mapping from hardware.yaml.

    Returns:
        {peripheral_name: {type, bus/uart/cs_pin}} for each peripheral.
    """
    peris: Dict[str, dict] = {}
    for peri_cfg in hw_doc.get("peripherals", []):
        name = peri_cfg.get("name", "")
        if not name:
            continue
        info: dict = {"type": peri_cfg.get("type", "")}
        for opt_key in ("bus", "uart", "cs_pin", "address"):
            if opt_key in peri_cfg:
                info[opt_key] = peri_cfg[opt_key]
        peris[name] = info
    return peris


def _extract_pins_from_netlist_yaml(nl_doc: dict) -> Dict[str, dict]:
    """Extract pin->function mapping from netlist/BOM-parser output.

    This is the intermediate YAML produced by netlist_parser or bom_parser,
    which uses the same structure as hardware.yaml.

    Returns:
        {pin_id: {function, label}} for each pin.
    """
    return _extract_pins_from_yaml(nl_doc)


def _extract_peripherals_from_netlist_yaml(nl_doc: dict) -> Dict[str, dict]:
    """Extract peripheral mapping from netlist/BOM-parser output."""
    return _extract_peripherals_from_yaml(nl_doc)


# ---------------------------------------------------------------------------
# Function comparison helpers
# ---------------------------------------------------------------------------

# Families of functions that are equivalent but may be named differently
# between netlist-parser auto-guess and user-authored YAML.
_FUNCTION_EQUIVALENCE: Dict[str, Set[str]] = {
    "SPI1_MISO": {"SPI1_MISO", "MISO", "SPI_MISO"},
    "SPI1_MOSI": {"SPI1_MOSI", "MOSI", "SPI_MOSI"},
    "SPI1_SCK":  {"SPI1_SCK", "SCK", "SPI_SCK"},
    "I2C1_SCL":  {"I2C1_SCL", "SCL", "I2C_SCL"},
    "I2C1_SDA":  {"I2C1_SDA", "SDA", "I2C_SDA"},
    "USART1_TX": {"USART1_TX", "TX", "UART_TX"},
    "USART1_RX": {"USART1_RX", "RX", "UART_RX"},
    "USART2_TX": {"USART2_TX", "TX", "UART_TX"},
    "USART2_RX": {"USART2_RX", "RX", "UART_RX"},
}


def _functions_equivalent(func_a: str, func_b: str) -> bool:
    """Check if two function strings represent the same logical assignment."""
    if func_a.upper() == func_b.upper():
        return True
    for _base, aliases in _FUNCTION_EQUIVALENCE.items():
        if func_a.upper() in aliases and func_b.upper() in aliases:
            return True
    return False


def _is_gpio_function(func: str) -> bool:
    """Check if a function string represents a pure GPIO assignment."""
    return func.upper().startswith("GPIO_")


# ---------------------------------------------------------------------------
# CrossValidator
# ---------------------------------------------------------------------------


class CrossValidator:
    """Cross-validate netlist-derived YAML against user-authored hardware YAML.

    Usage:
        v = CrossValidator()
        report = v.validate(netlist_yaml, hw_yaml)
        if report.has_errors:
            raise SystemExit(str(report))
    """

    def validate(self, netlist_yaml: str, hw_yaml: str) -> CrossReport:
        """Perform full cross-validation.

        Args:
            netlist_yaml: YAML string from netlist_parser or bom_parser.
            hw_yaml: YAML string from user-authored hardware.yaml.

        Returns:
            CrossReport with all discrepancies found.
        """
        nl_doc = yaml.safe_load(netlist_yaml) or {}
        hw_doc = yaml.safe_load(hw_yaml) or {}

        report = CrossReport()

        # ---- MCU match ----
        nl_mcu = (nl_doc.get("mcu", {}) or {}).get("part", "")
        hw_mcu = (hw_doc.get("mcu", {}) or {}).get("part", "")
        report.netlist_mcu = nl_mcu or None
        report.yaml_mcu = hw_mcu or None

        if nl_mcu and hw_mcu and nl_mcu.upper() != hw_mcu.upper():
            report.issues.append(CrossIssue(
                severity="error",
                code="MCU_MISMATCH",
                message=f"MCU mismatch: netlist '{nl_mcu}' vs YAML '{hw_mcu}'",
                netlist_value=nl_mcu,
                yaml_value=hw_mcu,
            ))

        # ---- Pin-level cross-check ----
        nl_pins = _extract_pins_from_netlist_yaml(nl_doc)
        hw_pins = _extract_pins_from_yaml(hw_doc)

        report.issues.extend(
            self._check_pin_conflicts(nl_pins, hw_pins))

        report.issues.extend(
            self._check_missing_pins(nl_pins, hw_pins))

        report.issues.extend(
            self._check_extra_pins(nl_pins, hw_pins))

        # ---- Peripheral-level cross-check ----
        nl_peris = _extract_peripherals_from_netlist_yaml(nl_doc)
        hw_peris = _extract_peripherals_from_yaml(hw_doc)

        report.issues.extend(
            self._check_peripheral_mismatches(nl_peris, hw_peris))

        # Log summary
        if report.issues:
            logger.warning("Cross-validation: %d error(s), %d warning(s)",
                           len(report.errors), len(report.warnings))
        else:
            logger.info("Cross-validation passed: netlist matches YAML")

        return report

    # ------------------------------------------------------------------
    # Pin checks
    # ------------------------------------------------------------------

    def _check_pin_conflicts(
        self,
        nl_pins: Dict[str, dict],
        hw_pins: Dict[str, dict],
    ) -> List[CrossIssue]:
        """Detect pins assigned to different functions in netlist vs YAML."""
        issues: List[CrossIssue] = []
        common_pins = set(nl_pins.keys()) & set(hw_pins.keys())

        for pin in sorted(common_pins):
            nl_func = nl_pins[pin]["function"]
            hw_func = hw_pins[pin]["function"]

            if _functions_equivalent(nl_func, hw_func):
                continue

            # GPIO in one, AF in the other — not necessarily a conflict
            # (user may have refined GPIO→specific AF)
            nl_is_gpio = _is_gpio_function(nl_func)
            hw_is_gpio = _is_gpio_function(hw_func)

            if nl_is_gpio and not hw_is_gpio:
                # User refined a generic GPIO to a specific AF — info only
                issues.append(CrossIssue(
                    severity="info",
                    code="PIN_REFINED",
                    message=f"Pin {pin}: netlist says '{nl_func}', "
                            f"YAML refines to '{hw_func}'",
                    pin=pin,
                    netlist_value=nl_func,
                    yaml_value=hw_func,
                ))
            elif hw_is_gpio and not nl_is_gpio:
                # Netlist inferred AF, but YAML only has GPIO — warning
                issues.append(CrossIssue(
                    severity="warning",
                    code="PIN_DOWNGRADED",
                    message=f"Pin {pin}: netlist infers '{nl_func}', "
                            f"but YAML only has '{hw_func}'",
                    pin=pin,
                    netlist_value=nl_func,
                    yaml_value=hw_func,
                ))
            else:
                # Two different non-GPIO functions — genuine conflict
                issues.append(CrossIssue(
                    severity="error",
                    code="PIN_CONFLICT",
                    message=f"Pin {pin} conflict: netlist='{nl_func}' "
                            f"vs YAML='{hw_func}'",
                    pin=pin,
                    netlist_value=nl_func,
                    yaml_value=hw_func,
                ))

        return issues

    def _check_missing_pins(
        self,
        nl_pins: Dict[str, dict],
        hw_pins: Dict[str, dict],
    ) -> List[CrossIssue]:
        """Detect pins present in netlist but missing from YAML."""
        issues: List[CrossIssue] = []
        missing = set(nl_pins.keys()) - set(hw_pins.keys())

        for pin in sorted(missing):
            nl_info = nl_pins[pin]
            if _is_gpio_function(nl_info["function"]):
                sev = "info"
                code = "PIN_UNCONFIGURED_GPIO"
            else:
                sev = "warning"
                code = "PIN_MISSING"
            issues.append(CrossIssue(
                severity=sev,
                code=code,
                message=f"Pin {pin} ('{nl_info['function']}') is in netlist "
                        f"but missing from YAML",
                pin=pin,
                netlist_value=nl_info["function"],
            ))

        return issues

    def _check_extra_pins(
        self,
        nl_pins: Dict[str, dict],
        hw_pins: Dict[str, dict],
    ) -> List[CrossIssue]:
        """Detect pins present in YAML but not connected in netlist."""
        issues: List[CrossIssue] = []
        extra = set(hw_pins.keys()) - set(nl_pins.keys())

        for pin in sorted(extra):
            hw_info = hw_pins[pin]
            if _is_gpio_function(hw_info["function"]):
                # Extra GPIO pins are often intentional (debug LEDs, etc.)
                continue
            issues.append(CrossIssue(
                severity="warning",
                code="PIN_EXTRA",
                message=f"Pin {pin} ('{hw_info['function']}') is in YAML "
                        f"but not found in netlist",
                pin=pin,
                yaml_value=hw_info["function"],
            ))

        return issues

    # ------------------------------------------------------------------
    # Peripheral checks
    # ------------------------------------------------------------------

    def _check_peripheral_mismatches(
        self,
        nl_peris: Dict[str, dict],
        hw_peris: Dict[str, dict],
    ) -> List[CrossIssue]:
        """Detect peripheral type mismatches between netlist and YAML."""

        # Build a fuzzy search: netlist-derived names may differ in suffix
        # (e.g., "mpu6050" vs "mpu6050_task")
        def _normalize(name: str) -> str:
            return name.lower().replace(" ", "_").rstrip("_")

        nl_names = {_normalize(n): n for n in nl_peris}
        hw_names = {_normalize(n): n for n in hw_peris}
        issues: List[CrossIssue] = []

        for nl_norm, nl_orig in sorted(nl_names.items()):
            if nl_norm in hw_names:
                # Same peripheral exists in both
                nl_type = nl_peris[nl_orig].get("type", "")
                hw_orig = hw_names[nl_norm]
                hw_type = hw_peris[hw_orig].get("type", "")
                if nl_type and hw_type and nl_type != hw_type:
                    issues.append(CrossIssue(
                        severity="error",
                        code="PERIPH_MISMATCH",
                        message=f"Peripheral '{nl_orig}': netlist type "
                                f"'{nl_type}' vs YAML type '{hw_type}'",
                        netlist_value=nl_type,
                        yaml_value=hw_type,
                    ))
            else:
                # Peripheral in netlist but not in YAML
                issues.append(CrossIssue(
                    severity="warning",
                    code="PERIPH_MISSING",
                    message=f"Peripheral '{nl_orig}' "
                            f"({nl_peris[nl_orig].get('type', 'unknown')}) "
                            f"found in netlist but missing from YAML",
                    netlist_value=nl_peris[nl_orig].get("type", ""),
                ))

        # Peripherals in YAML but not in netlist
        for hw_norm, hw_orig in sorted(hw_names.items()):
            if hw_norm not in nl_names:
                issues.append(CrossIssue(
                    severity="info",
                    code="PERIPH_EXTRA",
                    message=f"Peripheral '{hw_orig}' "
                            f"({hw_peris[hw_orig].get('type', 'unknown')}) "
                            f"in YAML but not in netlist "
                            f"(may be virtual/internal peripheral)",
                    yaml_value=hw_peris[hw_orig].get("type", ""),
                ))

        return issues


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python cross_validator.py "
              "<netlist_output.yaml> <hardware.yaml>")
        sys.exit(1)

    netlist_path = sys.argv[1]
    hw_path = sys.argv[2]

    try:
        nl_text = open(netlist_path, encoding="utf-8").read()
        hw_text = open(hw_path, encoding="utf-8").read()
    except (FileNotFoundError, yaml.YAMLError, ValueError, OSError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(2)

    v = CrossValidator()
    report = v.validate(nl_text, hw_text)
    print(report)

    sys.exit(1 if report.has_errors else 0)
