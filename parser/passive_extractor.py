"""
passive_extractor.py
Extract passive component constraints from BOM data.

Passive components (resistors, capacitors, inductors, connectors, crystals,
regulators) do not map to software peripherals directly, but they inform
hardware constraints that affect code generation:

  - Decoupling capacitors → power domain validation
  - Pull-up/down resistors → GPIO default state hints
  - Crystal/oscillator → clock configuration
  - Connectors → pin group allocation
  - Voltage regulators → power sequencing requirements

Usage:
    from parser.passive_extractor import PassiveExtractor
    ext = PassiveExtractor()
    constraints = ext.extract(bom_rows)
    print(constraints)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hw2c.passive_extractor")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PassiveComponent:
    """A single passive component from the BOM."""
    designator: str
    value: str
    footprint: str = ""
    component_type: str = "unknown"  # resistor, capacitor, inductor, etc.

    # Resistor-specific
    resistance_ohms: Optional[float] = None
    tolerance_pct: Optional[float] = None

    # Capacitor-specific
    capacitance_farad: Optional[float] = None
    voltage_rating: Optional[float] = None
    capacitor_type: Optional[str] = None  # ceramic, electrolytic, tantalum

    # Crystal/oscillator-specific
    frequency_hz: Optional[float] = None

    # Connector-specific
    pin_count: Optional[int] = None
    connector_type: Optional[str] = None

    # Regulator-specific
    output_voltage: Optional[float] = None
    output_current: Optional[float] = None


@dataclass
class PassiveConstraints:
    """Aggregated constraints extracted from passive components."""
    power_regulators: List[PassiveComponent] = field(default_factory=list)
    decoupling_caps: List[PassiveComponent] = field(default_factory=list)
    crystals: List[PassiveComponent] = field(default_factory=list)
    connectors: List[PassiveComponent] = field(default_factory=list)
    pull_resistors: List[PassiveComponent] = field(default_factory=list)
    unknown_passives: List[PassiveComponent] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable summary of constraints."""
        lines = ["Passive Component Constraints", "=" * 28]
        if self.power_regulators:
            lines.append(f"  Regulators: {len(self.power_regulators)}")
        if self.decoupling_caps:
            lines.append(f"  Decoupling caps: {len(self.decoupling_caps)}")
        if self.crystals:
            lines.append(f"  Crystals/Oscillators: {len(self.crystals)}")
        if self.connectors:
            lines.append(f"  Connectors: {len(self.connectors)}")
        if self.pull_resistors:
            lines.append(f"  Pull resistors: {len(self.pull_resistors)}")
        if self.unknown_passives:
            lines.append(f"  Unknown: {len(self.unknown_passives)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Regex patterns for value parsing
# ---------------------------------------------------------------------------

# Resistance: "10k", "4.7k", "100R", "1M", "0.1R", "330"
_RESISTANCE_RE = re.compile(
    r"^\s*([\d.]+)\s*(R|K|M|m)?\s*(ohms?|Ω)?\s*$",
    re.IGNORECASE,
)

# Capacitance: "100nF", "10uF", "22pF", "0.1u", "1mF"
_CAPACITANCE_RE = re.compile(
    r"^\s*([\d.]+)\s*(pF|pf|nF|nf|uF|uf|µF|mF|mf|F)\s*$",
    re.IGNORECASE,
)

# Frequency: "8MHz", "32.768kHz", "25M"
_FREQUENCY_RE = re.compile(
    r"^\s*([\d.]+)\s*(Hz|kHz|MHz|KHz|MHZ)\s*$",
    re.IGNORECASE,
)

# Voltage: "3.3V", "5V", "1.2V", "12V"
_VOLTAGE_RE = re.compile(
    r"^\s*([\d.]+)\s*(V|mV)\s*$",
    re.IGNORECASE,
)

# Tolerance: "±1%", "5%", "±0.5%", "10%"
_TOLERANCE_RE = re.compile(
    r"^\s*[±]?\s*([\d.]+)\s*%\s*$",
)

# Connector pin count: "1x4", "2x10", "4pin", "20P"
_CONNECTOR_RE = re.compile(
    r"(?:(\d+)\s*x\s*(\d+))|(\d+)\s*(?:pin|P|POS)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Component type classification table
# ---------------------------------------------------------------------------

# Footprint patterns → component type
_FOOTPRINT_TO_TYPE: List[Tuple[str, str]] = [
    ("Crystal", "crystal"),
    ("XTAL", "crystal"),
    ("Oscillator", "crystal"),
    ("OSC", "crystal"),
    ("USB", "connector"),
    ("Header", "connector"),
    ("Connector", "connector"),
    ("CONN", "connector"),
    ("PinHeader", "connector"),
    ("Terminal", "connector"),
    ("Battery", "connector"),
    ("SD_Card", "connector"),
    ("microSD", "connector"),
    ("SWD", "connector"),
    ("JTAG", "connector"),
    ("DC_Jack", "connector"),
    ("Barrel", "connector"),
    ("REG", "regulator"),
    ("LDO", "regulator"),
    ("Regulator", "regulator"),
    ("DC-DC", "regulator"),
    ("Buck", "regulator"),
    ("Boost", "regulator"),
    ("AMS1117", "regulator"),
    ("Switch", "switch"),
    ("SW_", "switch"),
    ("Relay", "relay"),
    ("Diode", "diode"),
    ("TVS", "diode"),
    ("Fuse", "fuse"),
    ("PTC", "fuse"),
    ("Inductor", "inductor"),
    ("Ferrite", "inductor"),
    ("Transformer", "inductor"),
]

# Value patterns for component type classification (when footprint is ambiguous)
_VALUE_TO_TYPE: List[Tuple[str, str]] = [
    (r"^\d+[\d.]*\s*[KMRkmr]?$", "resistor"),       # "10k", "100R", "4.7K"
    (r"^(Pt|NTC|PTC)\d+", "thermistor"),
    (r"^\d+[\d.]*\s*(pF|nF|uF|µF|mF|F)", "capacitor"),  # "100nF", "10uF"
    (r"^\d+[\d.]*\s*(Hz|kHz|MHz)", "crystal"),         # "8MHz"
    (r"^\d+[\d.]*\s*[xX]\s*\d+", "connector"),          # "2x5"
    (r"^\d+[\d.]*\s*(V|mV)", "regulator"),              # "3.3V"
    (r"^[\d.]+[mM]?\s*[Hh]$", "inductor"),              # "10uH"
]


def _classify_component(value: str, footprint: str, designator: str) -> str:
    """Classify a passive component by its footprint and value.

    Args:
        value: Component value string (e.g. '10k', '100nF').
        footprint: Footprint string from BOM.
        designator: Reference designator (e.g. 'R1', 'C3').

    Returns:
        Component type string: 'resistor', 'capacitor', 'crystal',
        'connector', 'regulator', 'switch', 'diode', 'fuse',
        'inductor', 'thermistor', 'relay', or 'unknown'.
    """
    # 1. Try by footprint
    for pattern, ctype in _FOOTPRINT_TO_TYPE:
        if pattern.lower() in footprint.lower():
            return ctype

    # 2. Try by value pattern (more reliable than designator prefix)
    for pattern, ctype in _VALUE_TO_TYPE:
        if re.match(pattern, value, re.IGNORECASE):
            return ctype

    # 3. Infer from designator prefix (fallback)
    if designator.upper().startswith("R"):
        return "resistor"
    if designator.upper().startswith("C"):
        return "capacitor"
    if designator.upper().startswith("L"):
        return "inductor"
    if designator.upper().startswith("J") or designator.upper().startswith("P"):
        return "connector"
    if designator.upper().startswith("Y"):
        return "crystal"
    if designator.upper().startswith("D"):
        return "diode"
    if designator.upper().startswith("F"):
        return "fuse"
    if designator.upper().startswith("U") or designator.upper().startswith("VR"):
        # Could be regulator IC — check value for voltage pattern
        if _VOLTAGE_RE.match(value):
            return "regulator"

    return "unknown"


# ---------------------------------------------------------------------------
# Value parsers
# ---------------------------------------------------------------------------

_RESISTANCE_MULTIPLIERS = {
    "R": 1.0, "": 1.0,
    "K": 1e3, "M": 1e6, "m": 1e-3,
}

_CAPACITANCE_MULTIPLIERS = {
    "PF": 1e-12, "NF": 1e-9, "UF": 1e-6, "µF": 1e-6,
    "MF": 1e-3, "F": 1.0,
}

_FREQUENCY_MULTIPLIERS = {
    "HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6,
}


def _parse_resistance(value: str) -> Optional[Tuple[float, Optional[float]]]:
    """Parse resistance value and tolerance.

    Returns:
        (ohms, tolerance_pct) or None if parsing fails.
    """
    m = _RESISTANCE_RE.match(value.strip())
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").upper()
    mult = _RESISTANCE_MULTIPLIERS.get(unit)
    if mult is None:
        return None
    return num * mult, None


def _parse_capacitance(value: str) -> Optional[Tuple[float, Optional[float]]]:
    """Parse capacitance value and optional voltage rating.

    Returns:
        (farads, voltage) or None if parsing fails.
    """
    # Try "100nF 16V" format
    parts = value.strip().split()
    cap_part = parts[0]
    volt_part = parts[1] if len(parts) > 1 else ""

    m = _CAPACITANCE_RE.match(cap_part)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2).upper()
    mult = _CAPACITANCE_MULTIPLIERS.get(unit)
    if mult is None:
        return None

    voltage: Optional[float] = None
    if volt_part:
        vm = _VOLTAGE_RE.match(volt_part)
        if vm:
            voltage = float(vm.group(1))
            if (vm.group(2) or "").upper() == "MV":
                voltage *= 1e-3

    return num * mult, voltage


def _parse_frequency(value: str) -> Optional[float]:
    """Parse frequency value in Hz."""
    m = _FREQUENCY_RE.match(value.strip())
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2).upper()
    mult = _FREQUENCY_MULTIPLIERS.get(unit)
    if mult is None:
        return None
    return num * mult


def _parse_voltage(value: str) -> Optional[float]:
    """Parse voltage value in volts."""
    m = _VOLTAGE_RE.match(value.strip())
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").upper()
    if unit == "MV":
        num *= 1e-3
    return num


def _parse_connector_pins(value: str, footprint: str) -> Optional[int]:
    """Estimate connector pin count from value or footprint."""
    m = _CONNECTOR_RE.search(value)
    if m:
        if m.group(1) and m.group(2):
            return int(m.group(1)) * int(m.group(2))
        if m.group(3):
            return int(m.group(3))

    # Try from footprint
    m = _CONNECTOR_RE.search(footprint)
    if m:
        if m.group(1) and m.group(2):
            return int(m.group(1)) * int(m.group(2))
        if m.group(3):
            return int(m.group(3))

    return None


# ---------------------------------------------------------------------------
# PassiveExtractor
# ---------------------------------------------------------------------------


class PassiveExtractor:
    """Extract passive component constraints from BOM rows.

    Usage:
        ext = PassiveExtractor()
        rows = [
            {"Designator": "C1", "Value": "100nF", "Footprint": "C_0805"},
            {"Designator": "R1", "Value": "10k", "Footprint": "R_0805"},
            {"Designator": "Y1", "Value": "8MHz", "Footprint": "Crystal_HC49"},
        ]
        constraints = ext.extract(rows)
        print(constraints.summary())
    """

    # Thresholds for classifying resistors as pull-up/down
    PULL_UP_MIN_OHMS = 1000     # 1kΩ
    PULL_UP_MAX_OHMS = 100000   # 100kΩ — typical range for pull resistors

    # Decoupling capacitor range
    DECOUPLING_MIN_FARAD = 10e-9   # 10nF
    DECOUPLING_MAX_FARAD = 100e-6  # 100µF

    def extract(self, bom_rows: List[Dict[str, str]]) -> PassiveConstraints:
        """Extract passive component constraints from BOM rows.

        Args:
            bom_rows: List of dicts with keys Designator, Value, Footprint.

        Returns:
            PassiveConstraints with classified components.
        """
        constraints = PassiveConstraints()

        for row in bom_rows:
            designator = row.get("Designator", "").strip().strip('"')
            value = row.get("Value", "").strip().strip('"')
            footprint = row.get("Footprint", "").strip().strip('"')

            if not value or not designator:
                continue

            ctype = _classify_component(value, footprint, designator)

            comp = PassiveComponent(
                designator=designator,
                value=value,
                footprint=footprint,
                component_type=ctype,
            )

            # Parse value details based on type
            if ctype == "resistor":
                res = _parse_resistance(value)
                if res:
                    comp.resistance_ohms = res[0]
                    comp.tolerance_pct = res[1]

                    # Classify as pull resistor if in typical range
                    if (self.PULL_UP_MIN_OHMS <= comp.resistance_ohms <=
                            self.PULL_UP_MAX_OHMS):
                        constraints.pull_resistors.append(comp)
                        continue

            elif ctype == "capacitor":
                cap = _parse_capacitance(value)
                if cap:
                    comp.capacitance_farad = cap[0]
                    comp.voltage_rating = cap[1]

                    # Classify as decoupling if in typical range
                    if (self.DECOUPLING_MIN_FARAD <= comp.capacitance_farad <=
                            self.DECOUPLING_MAX_FARAD):
                        constraints.decoupling_caps.append(comp)
                        continue

            elif ctype == "crystal":
                freq = _parse_frequency(value)
                if freq:
                    comp.frequency_hz = freq
                constraints.crystals.append(comp)
                continue

            elif ctype == "connector":
                comp.pin_count = _parse_connector_pins(value, footprint)
                constraints.connectors.append(comp)
                continue

            elif ctype == "regulator":
                vout = _parse_voltage(value)
                if vout:
                    comp.output_voltage = vout
                constraints.power_regulators.append(comp)
                continue

            # Uncategorized
            constraints.unknown_passives.append(comp)

        logger.info("Passive extraction: %d regulators, %d decoupling, "
                    "%d crystals, %d connectors, %d pull, %d unknown",
                    len(constraints.power_regulators),
                    len(constraints.decoupling_caps),
                    len(constraints.crystals),
                    len(constraints.connectors),
                    len(constraints.pull_resistors),
                    len(constraints.unknown_passives))

        return constraints


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import csv
    import io

    if len(sys.argv) < 2:
        print("Usage: python passive_extractor.py <bom.csv>")
        sys.exit(1)

    try:
        text = open(sys.argv[1], encoding="utf-8").read()
    except (FileNotFoundError, csv.Error, ValueError, OSError) as e:
        print(f"Error reading BOM: {e}", file=sys.stderr)
        sys.exit(2)

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    ext = PassiveExtractor()
    constraints = ext.extract(rows)

    print(constraints.summary())
    print()

    # Print detail
    detail_groups = [
        ("Power Regulators", constraints.power_regulators),
        ("Decoupling Capacitors", constraints.decoupling_caps),
        ("Crystals & Oscillators", constraints.crystals),
        ("Connectors", constraints.connectors),
        ("Pull Resistors", constraints.pull_resistors),
        ("Unknown Passives", constraints.unknown_passives),
    ]

    for group_name, items in detail_groups:
        if not items:
            continue
        print(f"\n-- {group_name} --")
        for item in items:
            details = [item.designator, item.value]
            if item.resistance_ohms:
                details.append(f"{item.resistance_ohms:.0f}Ω")
            if item.capacitance_farad:
                if item.capacitance_farad >= 1e-6:
                    details.append(f"{item.capacitance_farad*1e6:.1f}µF")
                elif item.capacitance_farad >= 1e-9:
                    details.append(f"{item.capacitance_farad*1e9:.1f}nF")
                else:
                    details.append(f"{item.capacitance_farad*1e12:.1f}pF")
            if item.frequency_hz:
                if item.frequency_hz >= 1e6:
                    details.append(f"{item.frequency_hz/1e6:.3f}MHz")
                elif item.frequency_hz >= 1e3:
                    details.append(f"{item.frequency_hz/1e3:.1f}kHz")
            if item.pin_count:
                details.append(f"{item.pin_count}pins")
            if item.output_voltage:
                details.append(f"{item.output_voltage}V")
            print(f"  {', '.join(details)}")
