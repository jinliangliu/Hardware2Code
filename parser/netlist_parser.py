"""
netlist_parser.py
Parse KiCad XML netlist format and convert to H2C hardware YAML.
"""

import xml.etree.ElementTree as ET
from typing import Optional, Tuple, Dict, List
from pathlib import Path


# ---------------------------------------------------------------------------
# Heuristic mapping: component value substring → H2C peripheral type
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

# Signal suffixes that indicate SPI pins on peripheral components
SPI_SIGNALS = {"SCK", "CLK", "MISO", "MOSI", "SI", "SO", "CS", "NSS", "SS"}
# Signal suffixes that indicate I2C pins on peripheral components
I2C_SIGNALS = {"SCL", "SDA"}
# Signal suffixes that indicate UART pins on peripheral components
UART_SIGNALS = {"TX", "RX", "TXD", "RXD", "TX1", "RX1", "TX2", "RX2"}
# LED/button value patterns
LED_PATTERNS = {"LED", "LED_RED", "LED_GREEN", "LED_BLUE", "LED_YELLOW"}
BUTTON_PATTERNS = {"BUTTON", "SW", "SWITCH", "KEY"}

# Pin-to-bus mapping for STM32G0B1 (AF assignments)
# Maps a pin id → (default_af_function, af_number, bus_name)
_STM32G0_PIN_BUS: Dict[str, Tuple[str, int, str]] = {
    # USART1
    "PA9":  ("USART1_TX", 1, "USART1"),
    "PA10": ("USART1_RX", 1, "USART1"),
    "PB6":  ("USART1_TX", 0, "USART1"),
    "PB7":  ("USART1_RX", 0, "USART1"),
    # USART2
    "PA2":  ("USART2_TX", 1, "USART2"),
    "PA3":  ("USART2_RX", 1, "USART2"),
    # I2C1
    "PB6":  ("I2C1_SCL", 1, "I2C1"),
    "PB7":  ("I2C1_SDA", 1, "I2C1"),
    "PB8":  ("I2C1_SCL", 1, "I2C1"),
    "PB9":  ("I2C1_SDA", 1, "I2C1"),
    # I2C2
    "PA11": ("I2C2_SCL", 6, "I2C2"),
    "PA12": ("I2C2_SDA", 6, "I2C2"),
    # SPI1
    "PA5":  ("SPI1_SCK",  0, "SPI1"),
    "PA6":  ("SPI1_MISO", 0, "SPI1"),
    "PA7":  ("SPI1_MOSI", 0, "SPI1"),
    "PB3":  ("SPI1_SCK",  0, "SPI1"),
    "PB4":  ("SPI1_MISO", 0, "SPI1"),
    "PB5":  ("SPI1_MOSI", 0, "SPI1"),
    # SPI2
    "PB13": ("SPI2_SCK",  0, "SPI2"),
    "PB14": ("SPI2_MISO", 0, "SPI2"),
    "PB15": ("SPI2_MOSI", 0, "SPI2"),
}

# Override: for PB6/PB7, prefer I2C1_SCL/I2C1_SDA → AF1
# This handles the PB6/PB7 conflict between USART1 and I2C1.
_STM32G0_PIN_BUS_I2C_OVERRIDE = {
    "PB6": ("I2C1_SCL", 1, "I2C1"),
    "PB7": ("I2C1_SDA", 1, "I2C1"),
}


def _normalize_pin(pin_str: str) -> str:
    """Normalize pin string like 'PA5' or '1' to uppercase PA5."""
    pin_str = pin_str.strip().upper()
    # Handle bare pin numbers: if it's just digits, return as-is
    return pin_str


def _is_mcu(value: str) -> bool:
    """Check if a component value looks like an MCU."""
    v = value.upper().strip()
    return v.startswith("STM32") or v.startswith("AT32") or v.startswith("GD32")


def _match_peripheral(value: str) -> Optional[Tuple[str, str]]:
    """
    Match a component value against the heuristic table.

    Returns:
        (peripheral_type, interface) or None if no match.
        interface is one of: 'I2C', 'SPI', 'UART', 'GPIO', or '' for internal.
    """
    v = value.strip()
    for key, (ptype, bus) in VALUE_TO_PERIPHERAL.items():
        if key.upper() in v.upper():
            return (ptype, bus)
    # Check LED patterns
    for pat in LED_PATTERNS:
        if pat in v.upper():
            return ("GPIO", "GPIO")
    # Check button patterns
    for pat in BUTTON_PATTERNS:
        if pat in v.upper():
            return ("GPIO", "GPIO")
    return None


def _pin_to_bus_info(pin_id: str, interface: str) -> Tuple[str, int, str]:
    """
    Determine the function, AF, and bus for an MCU pin based on the interface.

    Args:
        pin_id: e.g. 'PA5'
        interface: 'I2C', 'SPI', 'UART', or 'GPIO'

    Returns:
        (function_name, af_number, bus_name)
    """
    if interface == "GPIO":
        return ("GPIO_Output", 0, "")

    if interface == "I2C":
        entry = _STM32G0_PIN_BUS_I2C_OVERRIDE.get(pin_id) or _STM32G0_PIN_BUS.get(pin_id)
    else:
        entry = _STM32G0_PIN_BUS.get(pin_id)

    if entry:
        return entry

    # Fallback: guess from interface + pin
    return (f"{interface}_{pin_id}", 0, f"{interface}1")


def _parse_components(xml_root: ET.Element) -> Tuple[Dict[str, dict], Optional[str]]:
    """
    Parse <components> section.

    Returns:
        (components_dict, mcu_ref)
        components_dict: ref → {value, footprint, type}
        mcu_ref: the ref of the MCU component, or None
    """
    components: Dict[str, dict] = {}
    mcu_ref: Optional[str] = None

    comps_elem = xml_root.find("components")
    if comps_elem is None:
        return components, mcu_ref

    for comp in comps_elem.findall("comp"):
        ref = comp.get("ref", "")
        value_elem = comp.find("value")
        value = value_elem.text if value_elem is not None else ""
        fp_elem = comp.find("footprint")
        footprint = fp_elem.text if fp_elem is not None else ""

        components[ref] = {
            "value": value.strip(),
            "footprint": footprint.strip(),
        }

        if _is_mcu(value):
            mcu_ref = ref

    return components, mcu_ref


def _parse_nets(xml_root: ET.Element) -> List[dict]:
    """
    Parse <nets> section.

    Returns:
        list of net dicts: {name, code, nodes: [{ref, pin}]}
    """
    nets: List[dict] = []

    nets_elem = xml_root.find("nets")
    if nets_elem is None:
        return nets

    for net in nets_elem.findall("net"):
        net_info = {
            "code": net.get("code", ""),
            "name": net.get("name", ""),
            "nodes": []
        }
        for node in net.findall("node"):
            net_info["nodes"].append({
                "ref": node.get("ref", ""),
                "pin": node.get("pin", ""),
            })
        nets.append(net_info)

    return nets


def _build_yaml(
    mcu_ref: str,
    mcu_value: str,
    components: Dict[str, dict],
    nets: List[dict],
) -> str:
    """
    Build the H2C hardware YAML from parsed netlist data.
    """
    import yaml

    # Determine which refs are peripherals (not MCU)
    mcu_pin_connections: Dict[str, List[dict]] = {}  # mcu_pin → [node_info, ...]
    peripheral_connections: Dict[str, Dict[str, List[str]]] = {}  # peri_ref → {interface: [mcu_pins]}

    for net in nets:
        mcu_nodes = [n for n in net["nodes"] if n["ref"] == mcu_ref]
        other_nodes = [n for n in net["nodes"] if n["ref"] != mcu_ref]

        for mcu_node in mcu_nodes:
            mcu_pin = _normalize_pin(mcu_node["pin"])
            if mcu_pin not in mcu_pin_connections:
                mcu_pin_connections[mcu_pin] = []
            for other in other_nodes:
                mcu_pin_connections[mcu_pin].append(other)

    # Build peripheral list and pin assignments
    pins: List[dict] = []
    peripherals: List[dict] = []
    seen_peripherals: Dict[str, dict] = {}  # peri_ref → {name, type, bus, extra}
    used_buses: Dict[str, int] = {}  # bus_name → next instance number
    peri_task_counter: int = 0

    # First pass: collect all peripherals and their interface types
    for ref, comp in components.items():
        if ref == mcu_ref:
            continue
        match = _match_peripheral(comp["value"])
        if match:
            peri_type, interface = match

            if interface == "GPIO":
                # Determine if it's LED or button
                v = comp["value"].upper()
                if any(p in v for p in LED_PATTERNS):
                    comp["_role"] = "LED"
                elif any(p in v for p in BUTTON_PATTERNS):
                    comp["_role"] = "BUTTON"
                else:
                    comp["_role"] = "GPIO"
            else:
                comp["_role"] = interface

            comp["_type"] = peri_type
            comp["_interface"] = interface
        else:
            comp["_type"] = "unknown"
            comp["_interface"] = ""
            comp["_role"] = "unknown"

    # Second pass: for each MCU pin, determine its function from connected peripherals
    connected_pins: Dict[str, dict] = {}  # pin_id → pin_config

    for mcu_pin, others in mcu_pin_connections.items():
        pin_config = {"id": mcu_pin}

        # Find the primary connected component
        if not others:
            continue

        primary = others[0]
        peri_ref = primary["ref"]
        peri_pin = _normalize_pin(primary["pin"])
        comp_info = components.get(peri_ref, {})

        if comp_info.get("_role") == "LED":
            pin_config["function"] = "GPIO_Output"
            pin_config["label"] = f"LED_{peri_ref}"
            pin_config["active_level"] = "low"
            pin_config["af"] = 0
        elif comp_info.get("_role") == "BUTTON":
            pin_config["function"] = "GPIO_Input"
            pin_config["label"] = f"BUTTON_{peri_ref}"
            pin_config["pull"] = "up"
            pin_config["exti"] = {"enable": True, "trigger": "falling"}
            pin_config["af"] = 0
        elif comp_info.get("_interface") == "I2C":
            func, af, bus = _pin_to_bus_info(mcu_pin, "I2C")
            pin_config["function"] = func
            pin_config["label"] = func
            pin_config["af"] = af
            connected_pins[mcu_pin] = pin_config

            # Register peripheral
            if peri_ref not in seen_peripherals:
                peri_name = comp_info["value"].lower().replace(" ", "_")
                seen_peripherals[peri_ref] = {
                    "name": peri_name,
                    "type": comp_info["_type"],
                    "bus": bus,
                }
                if comp_info["_type"] == "I2C_Sensor_MPU6050":
                    seen_peripherals[peri_ref]["address"] = 0x68
                elif comp_info["_type"] == "I2C_EEPROM":
                    seen_peripherals[peri_ref]["address"] = 0x50
            continue

        elif comp_info.get("_interface") == "SPI":
            func, af, bus = _pin_to_bus_info(mcu_pin, "SPI")
            # Determine role: SCK/MISO/MOSI/CS
            if any(s in peri_pin.upper() for s in ["CS", "NSS", "SS"]):
                pin_config["function"] = "GPIO_Output"
                pin_config["label"] = f"{bus}_NSS"
                pin_config["active_level"] = "low"
                pin_config["af"] = 0
            else:
                pin_config["function"] = func
                pin_config["label"] = func
                pin_config["af"] = af

            connected_pins[mcu_pin] = pin_config

            # Register peripheral
            if peri_ref not in seen_peripherals:
                peri_name = comp_info["value"].lower().replace(" ", "_")
                seen_peripherals[peri_ref] = {
                    "name": peri_name,
                    "type": comp_info["_type"],
                    "bus": bus,
                }
            continue

        elif comp_info.get("_interface") == "UART":
            func, af, bus = _pin_to_bus_info(mcu_pin, "UART")
            pin_config["function"] = func
            pin_config["label"] = func
            pin_config["af"] = af
            connected_pins[mcu_pin] = pin_config

            # Register peripheral
            if peri_ref not in seen_peripherals:
                peri_name = comp_info["value"].lower().replace(" ", "_")
                seen_peripherals[peri_ref] = {
                    "name": peri_name,
                    "type": comp_info["_type"],
                    "uart": bus,
                }
            continue

        else:
            # Unknown — mark as GPIO
            pin_config["function"] = "GPIO_Output"
            pin_config["label"] = f"NET_{mcu_pin}"
            pin_config["af"] = 0

        connected_pins[mcu_pin] = pin_config

    # Assemble pins list (sorted for deterministic output)
    pins = [connected_pins[p] for p in sorted(connected_pins.keys())]

    # Add cs_pin for SPI peripherals
    for peri_ref, peri_cfg in seen_peripherals.items():
        if peri_cfg["type"] in ("SPI_Flash_W25Q32", "SPI_Flash_Generic"):
            # Find the NSS/CS pin for this bus
            bus_name = peri_cfg["bus"]
            for pin in pins:
                if pin.get("label") == f"{bus_name}_NSS":
                    peri_cfg["cs_pin"] = pin["id"]
                    break

    # Build sorted peripheral list
    peripherals = [seen_peripherals[r] for r in sorted(seen_peripherals.keys())]

    # Generate app_tasks
    task_priority = 2
    app_tasks = []
    for peri in peripherals:
        task_priority += 1
        app_tasks.append({
            "name": f"{peri['name']}_task",
            "priority": task_priority,
            "stack_size": 512,
        })

    # Check if there are button pins that need notify_task
    for pin in pins:
        if pin.get("exti") and not pin.get("notify_task"):
            # Assign to first task or create a default
            if app_tasks:
                pin["notify_task"] = app_tasks[0]["name"]

    # Assemble the full YAML structure
    doc = {
        "mcu": {
            "part": mcu_value,
            "core_clock_mhz": 64,
        },
        "pins": pins,
        "peripherals": peripherals,
    }
    if app_tasks:
        doc["app_tasks"] = app_tasks

    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)


def parse_netlist_string(xml_string: str) -> str:
    """
    Parse a KiCad netlist XML string and return H2C YAML.

    Args:
        xml_string: Raw netlist XML string.

    Returns:
        H2C hardware YAML string.
    """
    root = ET.fromstring(xml_string)
    components, mcu_ref = _parse_components(root)

    if mcu_ref is None:
        raise ValueError("No MCU component found in netlist. "
                         "Expected a component with STM32/GD32/AT32 value.")

    mcu_value = components[mcu_ref]["value"]
    nets = _parse_nets(root)

    return _build_yaml(mcu_ref, mcu_value, components, nets)


def parse_netlist(file_path: str) -> str:
    """
    Parse a KiCad netlist XML file and return H2C YAML.

    Args:
        file_path: Path to the .net XML file.

    Returns:
        H2C hardware YAML string.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Netlist file not found: '{file_path}'")

    xml_text = path.read_text(encoding="utf-8")
    return parse_netlist_string(xml_text)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import yaml

    if len(sys.argv) < 2:
        print("Usage: python netlist_parser.py <kicad_netlist.net> [output.yaml]")
        sys.exit(1)

    try:
        yaml_content = parse_netlist(sys.argv[1])
    except (FileNotFoundError, ET.ParseError, yaml.YAMLError,
            ValueError, KeyError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"YAML written to {sys.argv[2]}")
    else:
        print(yaml_content)
