"""
schematic_annotator.py
Extract bus intent, peripheral grouping, and power domain hints
from net naming conventions in schematics.

Many EDA tools allow the designer to label nets with meaningful names.
These conventions carry design intent that the raw netlist topology alone
cannot express:

  - Bus allocation: "SPI1_SCK", "I2C2_SDA" → which hardware bus instance
  - Peripheral grouping: "MPU6050_SCL", "MPU6050_SDA" → same device
  - Power domains: "3V3", "VDD_MCU", "VBAT" → voltage rail assignment
  - Signal roles: "nCS_FLASH", "INT_ACCEL" → active-low / interrupt hints

Usage:
    from parser.schematic_annotator import SchematicAnnotator
    ann = SchematicAnnotator()
    hints = ann.extract(net_names)
    print(hints.summary())
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("hw2c.schematic_annotator")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BusHint:
    """Inferred bus assignment from net naming."""
    bus_name: str       # e.g. "I2C1", "SPI2", "USART1"
    bus_type: str       # e.g. "I2C", "SPI", "UART"
    signals: Set[str]   # e.g. {"SCL", "SDA"}
    nets: List[str]     # original net names that contributed


@dataclass
class PeripheralHint:
    """Inferred peripheral grouping from net naming."""
    name: str           # e.g. "MPU6050"
    interface: str      # e.g. "I2C", "SPI", "UART", "GPIO"
    nets: List[str]


@dataclass
class PowerHint:
    """Power domain hint from net names."""
    net_name: str
    voltage: Optional[float] = None
    domain: str = "unknown"  # "3V3", "5V", "VBAT", "VDD_MCU", etc.


@dataclass
class AnnotationHints:
    """Aggregated schematic annotation hints."""
    bus_hints: List[BusHint] = field(default_factory=list)
    peripheral_hints: List[PeripheralHint] = field(default_factory=list)
    power_hints: List[PowerHint] = field(default_factory=list)
    signal_role_hints: Dict[str, str] = field(default_factory=dict)
    # net_name → inferred role (e.g. "nCS", "INT", "RESET")

    def summary(self) -> str:
        lines = ["Schematic Annotation Hints", "=" * 24]
        if self.bus_hints:
            lines.append(f"  Bus hints: {len(self.bus_hints)}")
            for hint in self.bus_hints:
                lines.append(f"    {hint.bus_name} ({hint.bus_type}): "
                             f"{sorted(hint.signals)}")
        if self.peripheral_hints:
            lines.append(f"  Peripheral groupings: {len(self.peripheral_hints)}")
            for hint in self.peripheral_hints:
                lines.append(f"    {hint.name} [{hint.interface}]")
        if self.power_hints:
            lines.append(f"  Power domains: {len(self.power_hints)}")
            for hint in self.power_hints:
                detail = f"    {hint.net_name} → {hint.domain}"
                if hint.voltage is not None:
                    detail += f" ({hint.voltage}V)"
                lines.append(detail)
        if self.signal_role_hints:
            lines.append(f"  Signal roles: {len(self.signal_role_hints)}")
            for net, role in sorted(self.signal_role_hints.items()):
                lines.append(f"    {net} → {role}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bus type detection patterns
# ---------------------------------------------------------------------------

# Regex patterns for bus type inference from net names
_BUS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # I2C: "I2C1_SCL", "PB6_SCL", "I2C_SCL", "SENSOR_SCL"
    (re.compile(r"(?:I2C|IIC)(\d*)\s*[_-]\s*(SCL|SDA)", re.IGNORECASE), "I2C"),
    # SPI: "SPI1_SCK", "SPI2_MISO", "FLASH_CS"
    (re.compile(r"SPI(\d*)\s*[_-]\s*(SCK|CLK|MISO|MOSI|NSS|CS\b)", re.IGNORECASE), "SPI"),
    # UART: "USART1_TX", "UART2_RX", "DEBUG_TXD"
    (re.compile(r"(?:USART|UART|LPUART)(\d*)\s*[_-]\s*(TX|RX|TXD|RXD)", re.IGNORECASE), "UART"),
    # CAN: "CAN1_TX", "FDCAN1_RX"
    (re.compile(r"(?:CAN|FDCAN)(\d*)\s*[_-]\s*(TX|RX|H|L)", re.IGNORECASE), "CAN"),
    # USB: "USB_DM", "USB_DP"
    (re.compile(r"USB\s*[_-]\s*(DM|DP|VBUS|ID)", re.IGNORECASE), "USB"),
    # SWD: "SWDIO", "SWCLK"
    (re.compile(r"SW(?:D)?\s*[_-]?\s*(IO|CLK|DIO)", re.IGNORECASE), "SWD"),
]

# Default bus numbers for common peripheral types
_DEFAULT_BUS_NUMBER: Dict[str, int] = {
    "I2C": 1, "SPI": 1, "UART": 2, "CAN": 1, "USB": 0, "SWD": 0,
}


# ---------------------------------------------------------------------------
# Peripheral prefix detection
# ---------------------------------------------------------------------------

# Common peripheral prefixes that indicate device-level grouping
# Format: (prefix_regex, interface_type)
_PERIPHERAL_PREFIXES: List[Tuple[str, str]] = [
    # I2C sensors
    ("MPU6050", "I2C"), ("MPU9250", "I2C"), ("BMP280", "I2C"), ("BME280", "I2C"),
    ("SHT30", "I2C"), ("SHT31", "I2C"), ("AHT20", "I2C"),
    ("BH1750", "I2C"), ("VL53L0X", "I2C"),
    ("SSD1306", "I2C"), ("SH1106", "I2C"),
    ("PCF8563", "I2C"), ("DS3231", "I2C"),
    # EEPROM
    ("AT24C", "I2C"), ("EEPROM", "I2C"),
    # SPI devices
    ("W25Q", "SPI"), ("GD25Q", "SPI"), ("SST26", "SPI"),
    ("ILI9341", "SPI"), ("ST7789", "SPI"), ("ST7735", "SPI"),
    ("NRF24", "SPI"), ("CC1101", "SPI"),
    ("W5500", "SPI"), ("ENC28", "SPI"),
    ("SX127", "SPI"),
    # UART devices
    ("ESP", "UART"), ("HC0", "UART"), ("JDY", "UART"),
    ("SIM", "UART"), ("AIR", "UART"), ("EC200", "UART"), ("BC26", "UART"),
    ("ATGM", "UART"), ("NEO", "UART"),
    ("MAX3232", "UART"), ("MAX232", "UART"),
    # RS485
    ("MAX485", "UART"), ("SP3485", "UART"),
    # CAN
    ("TJA1050", "CAN"), ("SN65HVD230", "CAN"),
    # Motor
    ("TMC220", "UART"), ("A4988", "GPIO"), ("DRV8825", "GPIO"),
    # OneWire
    ("DS18B20", "GPIO"), ("DHT", "GPIO"),
    # Servo
    ("SG90", "GPIO"), ("MG996R", "GPIO"),
    # LED / button
    ("LED", "GPIO"), ("BUTTON", "GPIO"), ("SW_", "GPIO"), ("SWITCH", "GPIO"),
]


# ---------------------------------------------------------------------------
# Power domain patterns
# ---------------------------------------------------------------------------

_POWER_PATTERNS: List[Tuple[re.Pattern, str, Optional[float]]] = [
    (re.compile(r"^3V3", re.IGNORECASE), "3V3", 3.3),
    (re.compile(r"^5V\b", re.IGNORECASE), "5V", 5.0),
    (re.compile(r"^1V8", re.IGNORECASE), "1V8", 1.8),
    (re.compile(r"^1V2", re.IGNORECASE), "1V2", 1.2),
    (re.compile(r"^VDD_MCU", re.IGNORECASE), "VDD_MCU", 3.3),
    (re.compile(r"^VDD\b", re.IGNORECASE), "VDD", None),
    (re.compile(r"^VBAT", re.IGNORECASE), "VBAT", None),
    (re.compile(r"^GND\b", re.IGNORECASE), "GND", 0.0),
    (re.compile(r"^VCC\b", re.IGNORECASE), "VCC", None),
    (re.compile(r"^VIN\b", re.IGNORECASE), "VIN", None),
    (re.compile(r"^VDDA", re.IGNORECASE), "VDDA", 3.3),
    (re.compile(r"^VREF", re.IGNORECASE), "VREF", None),
]

# Signal role prefixes
_SIGNAL_ROLE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Active-low signals (prefix n, /, or #, anywhere in net name)
    (re.compile(r"(?:^|[_-])(?:n|/|#)\s*(CS|SS|RST|RESET|INT|EN|OE|WE)\b", re.IGNORECASE), "active_low"),
    # Reset
    (re.compile(r"RST|RESET|NRST|MR", re.IGNORECASE), "reset"),
    # Interrupt
    (re.compile(r"INT|IRQ", re.IGNORECASE), "interrupt"),
    # Chip select
    (re.compile(r"\b(CS|NSS|SS)\b", re.IGNORECASE), "chip_select"),
    # Enable
    (re.compile(r"\bEN\b", re.IGNORECASE), "enable"),
    # Clock
    (re.compile(r"\bCLK\b", re.IGNORECASE), "clock"),
    # Data ready
    (re.compile(r"DRDY|READY", re.IGNORECASE), "data_ready"),
    # Power enable / control
    (re.compile(r"PWR_EN|POWER_EN|EN_PWR", re.IGNORECASE), "power_enable"),
    # Wake
    (re.compile(r"WAKE|WKUP", re.IGNORECASE), "wakeup"),
    # Boot
    (re.compile(r"BOOT\d*", re.IGNORECASE), "boot"),
]


# ---------------------------------------------------------------------------
# SchematicAnnotator
# ---------------------------------------------------------------------------


class SchematicAnnotator:
    """Extract design intent hints from schematic net naming conventions.

    Usage:
        ann = SchematicAnnotator()
        hints = ann.extract(["MPU6050_SCL", "MPU6050_SDA",
                              "W25Q32_CS", "W25Q32_CLK",
                              "nRST", "3V3", "GND"])
        print(hints.summary())
    """

    def extract(self, net_names: List[str]) -> AnnotationHints:
        """Analyze net names and extract design intent hints.

        Args:
            net_names: List of net name strings from the schematic.

        Returns:
            AnnotationHints with bus, peripheral, power, and signal role info.
        """
        hints = AnnotationHints()

        if not net_names:
            return hints

        # 1. Bus hints
        hints.bus_hints = self._extract_bus_hints(net_names)

        # 2. Peripheral grouping
        hints.peripheral_hints = self._extract_peripheral_hints(net_names)

        # 3. Power domains
        hints.power_hints = self._extract_power_hints(net_names)

        # 4. Signal role hints
        hints.signal_role_hints = self._extract_signal_roles(net_names)

        logger.info("Schematic annotation: %d bus hints, %d peripherals, "
                    "%d power domains, %d signal roles",
                    len(hints.bus_hints), len(hints.peripheral_hints),
                    len(hints.power_hints), len(hints.signal_role_hints))

        return hints

    # ------------------------------------------------------------------
    # Bus hints
    # ------------------------------------------------------------------

    def _extract_bus_hints(self, net_names: List[str]) -> List[BusHint]:
        """Detect bus allocation from net names like 'I2C1_SCL', 'SPI2_MOSI'."""
        bus_groups: Dict[str, BusHint] = {}

        for net in net_names:
            for pattern, bus_type in _BUS_PATTERNS:
                m = pattern.search(net)
                if m:
                    # Extract number and signal from groups
                    groups = m.groups()
                    if len(groups) >= 2:
                        num_str = groups[0] or ""
                        signal = (groups[1] or "").upper()
                    else:
                        num_str = ""
                        signal = (groups[0] or "").upper()

                    if num_str.isdigit():
                        bus_num = num_str
                    else:
                        bus_num = str(_DEFAULT_BUS_NUMBER.get(bus_type, 1))
                    bus_name = f"{bus_type}{bus_num}" if bus_num != "0" else bus_type

                    if bus_name not in bus_groups:
                        bus_groups[bus_name] = BusHint(
                            bus_name=bus_name,
                            bus_type=bus_type,
                            signals=set(),
                            nets=[],
                        )
                    bus_groups[bus_name].signals.add(signal)
                    bus_groups[bus_name].nets.append(net)
                    break

        return list(bus_groups.values())

    # ------------------------------------------------------------------
    # Peripheral hints
    # ------------------------------------------------------------------

    def _extract_peripheral_hints(self, net_names: List[str]) -> List[PeripheralHint]:
        """Group nets by peripheral device prefix.

        E.g. 'MPU6050_SCL' and 'MPU6050_SDA' → PeripheralHint('mpu6050', 'I2C')
        """
        groups: Dict[str, PeripheralHint] = {}

        for net in net_names:
            for prefix, interface in _PERIPHERAL_PREFIXES:
                if net.upper().startswith(prefix.upper()):
                    name = prefix.lower()
                    if name not in groups:
                        groups[name] = PeripheralHint(
                            name=name,
                            interface=interface,
                            nets=[],
                        )
                    groups[name].nets.append(net)
                    break

        return list(groups.values())

    # ------------------------------------------------------------------
    # Power domain hints
    # ------------------------------------------------------------------

    def _extract_power_hints(self, net_names: List[str]) -> List[PowerHint]:
        """Detect power domain hints from net names like '3V3', 'VDD_MCU'."""
        power_hints: List[PowerHint] = []

        for net in net_names:
            for pattern, domain, voltage in _POWER_PATTERNS:
                if pattern.match(net.strip()):
                    power_hints.append(PowerHint(
                        net_name=net,
                        voltage=voltage,
                        domain=domain,
                    ))
                    break

        return power_hints

    # ------------------------------------------------------------------
    # Signal role hints
    # ------------------------------------------------------------------

    def _extract_signal_roles(self, net_names: List[str]) -> Dict[str, str]:
        """Detect signal roles from net naming conventions.

        E.g. 'nCS_FLASH' → chip_select, active_low
             'INT_ACCEL' → interrupt
        """
        roles: Dict[str, str] = {}

        for net in net_names:
            for pattern, role in _SIGNAL_ROLE_PATTERNS:
                if pattern.search(net):
                    roles[net] = role
                    break

        return roles


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python schematic_annotator.py <net_names.txt>")
        print("  Each line in the file is a net name from the schematic.")
        sys.exit(1)

    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            net_names = [line.strip() for line in f if line.strip()]
    except (FileNotFoundError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    ann = SchematicAnnotator()
    hints = ann.extract(net_names)
    print(hints.summary())
