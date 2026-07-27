"""
bom_parser.py
Parse CSV BOM (Bill of Materials) and map components to H2C peripheral types.
"""

import csv
import io
from typing import Dict, List, Optional, Tuple
from pathlib import Path


# ---------------------------------------------------------------------------
# Heuristic mapping: component value substring → H2C peripheral type
# Same table as netlist_parser for consistency.
# ---------------------------------------------------------------------------
VALUE_TO_PERIPHERAL: Dict[str, Tuple[str, str]] = {
    "MPU6050":        ("I2C_Sensor_MPU6050", "I2C"),
    "W25Q32":         ("SPI_Flash_W25Q32", "SPI"),
    "W25Q64":         ("SPI_Flash_W25Q32", "SPI"),
    "W25Q128":        ("SPI_Flash_W25Q32", "SPI"),
    "AT24C32":        ("I2C_EEPROM", "I2C"),
    "AT24C256":       ("I2C_EEPROM", "I2C"),
    "MAX485":         ("RS485", "UART"),
    "SP3485":         ("RS485", "UART"),
    "MAX3232":        ("UART_Serial", "UART"),
    "SIM800":         ("Cellular_4G", "UART"),
    "SIM7020":        ("Cellular_4G", "UART"),
    "AIR780":         ("Cellular_4G", "UART"),
    "ESP8266":        ("UART_Serial", "UART"),
}

LED_PATTERNS = {"LED", "LED_RED", "LED_GREEN", "LED_BLUE", "LED_YELLOW"}
BUTTON_PATTERNS = {"BUTTON", "SW", "SWITCH", "KEY"}


def _is_mcu(value: str) -> bool:
    """Check if a component value looks like an MCU."""
    v = value.upper().strip()
    return v.startswith("STM32") or v.startswith("AT32") or v.startswith("GD32")


def _match_peripheral(value: str) -> Optional[Tuple[str, str]]:
    """
    Match a component value against the heuristic table.

    Returns:
        (peripheral_type, interface) or None if no match.
    """
    v = value.strip()
    for key, (ptype, bus) in VALUE_TO_PERIPHERAL.items():
        if key.upper() in v.upper():
            return (ptype, bus)
    for pat in LED_PATTERNS:
        if pat in v.upper():
            return ("GPIO", "GPIO")
    for pat in BUTTON_PATTERNS:
        if pat in v.upper():
            return ("GPIO", "GPIO")
    return None


def _parse_designators(designator: str) -> List[str]:
    """
    Split a designator string like 'R1,R2,R3' into individual refs.
    """
    if not designator:
        return []
    return [d.strip() for d in designator.split(",") if d.strip()]


def parse_bom_string(csv_text: str) -> str:
    """
    Parse a CSV BOM string and return H2C YAML with peripherals section.

    Args:
        csv_text: Raw CSV BOM text.

    Returns:
        H2C hardware YAML string with mcu and peripherals sections.
    """
    import yaml

    reader = csv.DictReader(io.StringIO(csv_text))

    mcu_part: Optional[str] = None
    peripherals: List[dict] = []
    gpio_leds: List[str] = []
    gpio_buttons: List[str] = []
    passive_refs: List[str] = []

    for row in reader:
        value = row.get("Value", "").strip().strip('"')
        designator = row.get("Designator", "").strip().strip('"')
        footprint = row.get("Footprint", "").strip().strip('"')

        if not value:
            continue

        # Check if this is the MCU
        if _is_mcu(value):
            mcu_part = value
            continue

        # Try to match as a known peripheral
        match = _match_peripheral(value)
        if match:
            peri_type, interface = match

            if interface == "GPIO":
                v = value.upper()
                if any(p in v for p in LED_PATTERNS):
                    for d in _parse_designators(designator):
                        gpio_leds.append(d)
                elif any(p in v for p in BUTTON_PATTERNS):
                    for d in _parse_designators(designator):
                        gpio_buttons.append(d)
            else:
                # Build peripheral entry
                refs = _parse_designators(designator)
                peri_name = value.lower().replace(" ", "_").replace("-", "_")
                entry: dict = {
                    "name": peri_name,
                    "type": peri_type,
                }
                if interface == "I2C":
                    entry["bus"] = "I2C1"
                    if peri_type == "I2C_Sensor_MPU6050":
                        entry["address"] = 0x68
                    elif peri_type == "I2C_EEPROM":
                        entry["address"] = 0x50
                elif interface == "SPI":
                    entry["bus"] = "SPI1"
                elif interface == "UART":
                    entry["uart"] = "USART1"

                peripherals.append(entry)
        else:
            # Passive components (R, C, etc.) — skip for YAML
            for d in _parse_designators(designator):
                passive_refs.append(d)

    # Build YAML document
    doc: dict = {}

    if mcu_part:
        doc["mcu"] = {"part": mcu_part, "core_clock_mhz": 64}
    else:
        doc["mcu"] = {"part": "STM32G0B1RET6", "core_clock_mhz": 64}

    # Add pins section for LEDs and buttons (without specific MCU pin assignments)
    pins: List[dict] = []
    for led_ref in gpio_leds:
        pins.append({
            "id": "PC0",
            "function": "GPIO_Output",
            "label": f"LED_{led_ref}",
            "active_level": "low",
            "af": 0,
        })
    for btn_ref in gpio_buttons:
        pins.append({
            "id": "PC13",
            "function": "GPIO_Input",
            "label": f"BUTTON_{btn_ref}",
            "pull": "up",
            "exti": {"enable": True, "trigger": "falling"},
            "af": 0,
        })

    if pins:
        doc["pins"] = pins

    if peripherals:
        doc["peripherals"] = peripherals

    # Generate app_tasks
    app_tasks = []
    task_priority = 2
    for peri in peripherals:
        task_priority += 1
        app_tasks.append({
            "name": f"{peri['name']}_task",
            "priority": task_priority,
            "stack_size": 512,
        })

    if app_tasks:
        doc["app_tasks"] = app_tasks

    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)


def parse_bom(file_path: str) -> str:
    """
    Parse a CSV BOM file and return H2C YAML.

    Args:
        file_path: Path to the CSV BOM file.

    Returns:
        H2C hardware YAML string.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"BOM file not found: '{file_path}'")

    csv_text = path.read_text(encoding="utf-8")
    return parse_bom_string(csv_text)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import yaml

    if len(sys.argv) < 2:
        print("Usage: python bom_parser.py <bom.csv> [output.yaml]")
        sys.exit(1)

    try:
        yaml_content = parse_bom(sys.argv[1])
    except (FileNotFoundError, yaml.YAMLError, csv.Error,
            ValueError, KeyError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"YAML written to {sys.argv[2]}")
    else:
        print(yaml_content)
