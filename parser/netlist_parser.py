"""
netlist_parser.py
Parse EDA netlist formats and convert to H2C hardware YAML.

Supports:
  - EasyEDA Pro .enet JSON netlist (primary target)
  - KiCad legacy XML netlist (<export version="D">)
  - KiCad 6+ S-Expression netlist ((kicad_netlist ...))

Format is auto-detected from content.
"""

import re
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, Dict, List, Any
from pathlib import Path


# ---------------------------------------------------------------------------
# Heuristic mapping: component value substring → H2C peripheral type
# ---------------------------------------------------------------------------
VALUE_TO_PERIPHERAL: Dict[str, Tuple[str, str]] = {
    # I2C sensors
    "MPU6050":        ("I2C_Sensor_MPU6050", "I2C"),
    "MPU9250":        ("I2C_Sensor_MPU9250", "I2C"),
    "BMP280":         ("I2C_Sensor_BMP280", "I2C"),
    "BME280":         ("I2C_Sensor_BME280", "I2C"),
    "SHT30":          ("I2C_Sensor_SHT30", "I2C"),
    "SHT31":          ("I2C_Sensor_SHT31", "I2C"),
    "AHT20":          ("I2C_Sensor_AHT20", "I2C"),
    "BH1750":         ("I2C_Sensor_BH1750", "I2C"),
    "VL53L0X":        ("I2C_Sensor_VL53L0X", "I2C"),
    "SSD1306":        ("I2C_Display_SSD1306", "I2C"),
    "SH1106":         ("I2C_Display_SH1106", "I2C"),
    "PCF8563":        ("I2C_RTC_PCF8563", "I2C"),
    "DS3231":         ("I2C_RTC_DS3231", "I2C"),
    # SPI Flash
    "W25Q32":         ("SPI_Flash_W25Q32", "SPI"),
    "W25Q64":         ("SPI_Flash_W25Q32", "SPI"),
    "W25Q128":        ("SPI_Flash_W25Q32", "SPI"),
    "W25Q256":        ("SPI_Flash_W25Q32", "SPI"),
    "GD25Q32":        ("SPI_Flash_W25Q32", "SPI"),
    "GD25Q64":        ("SPI_Flash_W25Q32", "SPI"),
    "GD25Q128":        ("SPI_Flash_W25Q32", "SPI"),
    "MX25L6433":      ("SPI_Flash_W25Q32", "SPI"),
    "SST26VF":        ("SPI_Flash_W25Q32", "SPI"),
    # SPI displays
    "ILI9341":        ("SPI_Display_ILI9341", "SPI"),
    "ST7789":         ("SPI_Display_ST7789", "SPI"),
    "ST7735":         ("SPI_Display_ST7735", "SPI"),
    # SPI sensors
    "NRF24L01":       ("SPI_Radio_NRF24L01", "SPI"),
    "CC1101":         ("SPI_Radio_CC1101", "SPI"),
    # I2C EEPROM
    "AT24C02":        ("I2C_EEPROM", "I2C"),
    "AT24C08":        ("I2C_EEPROM", "I2C"),
    "AT24C16":        ("I2C_EEPROM", "I2C"),
    "AT24C32":        ("I2C_EEPROM", "I2C"),
    "AT24C64":        ("I2C_EEPROM", "I2C"),
    "AT24C128":        ("I2C_EEPROM", "I2C"),
    "AT24C256":       ("I2C_EEPROM", "I2C"),
    "AT24C512":       ("I2C_EEPROM", "I2C"),
    # RS485 transceivers
    "MAX485":         ("RS485", "UART"),
    "SP3485":         ("RS485", "UART"),
    "MAX3485":        ("RS485", "UART"),
    "SN65HVD72":      ("RS485", "UART"),
    "ISL83485":       ("RS485", "UART"),
    # RS232 transceivers
    "MAX3232":        ("UART_Serial", "UART"),
    "MAX232":         ("UART_Serial", "UART"),
    "SP3232":         ("UART_Serial", "UART"),
    # Cellular modules
    "SIM800":         ("Cellular_4G", "UART"),
    "SIM7020":        ("Cellular_4G", "UART"),
    "SIM7600":        ("Cellular_4G", "UART"),
    "AIR780":         ("Cellular_4G", "UART"),
    "AIR724":         ("Cellular_4G", "UART"),
    "EC200":          ("Cellular_4G", "UART"),
    "BC26":           ("Cellular_4G", "UART"),
    "M5311":          ("Cellular_4G", "UART"),
    # Wi-Fi
    "ESP8266":        ("UART_WiFi_ESP8266", "UART"),
    "ESP32":          ("UART_WiFi_ESP32", "UART"),
    "ESP32C3":        ("UART_WiFi_ESP32C3", "UART"),
    # Bluetooth
    "HC05":           ("UART_BT_HC05", "UART"),
    "HC06":           ("UART_BT_HC06", "UART"),
    "JDY31":          ("UART_BT_JDY31", "UART"),
    # GPS/GNSS
    "ATGM336H":       ("UART_GNSS_ATGM336H", "UART"),
    "NEO6M":          ("UART_GNSS_NEO6M", "UART"),
    "NEO8M":          ("UART_GNSS_NEO8M", "UART"),
    # CAN transceivers
    "TJA1050":        ("CAN_Transceiver", "FDCAN"),
    "SN65HVD230":     ("CAN_Transceiver", "FDCAN"),
    "MCP2551":        ("CAN_Transceiver", "FDCAN"),
    # USB
    "CH340":          ("UART_USB_CH340", "UART"),
    "CP2102":         ("UART_USB_CP2102", "UART"),
    "FT232":          ("UART_USB_FT232", "UART"),
    # Ethernet
    "W5500":          ("SPI_Ethernet_W5500", "SPI"),
    "ENC28J60":       ("SPI_Ethernet_ENC28J60", "SPI"),
    # LoRa
    "SX1276":         ("SPI_LoRa_SX1276", "SPI"),
    "SX1278":         ("SPI_LoRa_SX1276", "SPI"),
    "E220":           ("UART_LoRa_E220", "UART"),
    # Motor drivers
    "A4988":          ("Internal_Stepper", "GPIO"),
    "DRV8825":        ("Internal_Stepper", "GPIO"),
    "TMC2208":        ("UART_Stepper_TMC2208", "UART"),
    "TMC2209":        ("UART_Stepper_TMC2209", "UART"),
    "L298N":          ("Internal_MotorDC", "Internal"),
    "TB6612":         ("Internal_MotorDC", "Internal"),
    # Servo
    "SG90":           ("Internal_Servo", "Internal"),
    "MG996R":         ("Internal_Servo", "Internal"),
    # ADC sensors
    "ACS712":         ("Internal_ADC_Current", "ADC"),
    "MAX6675":        ("SPI_Thermocouple_MAX6675", "SPI"),
    "MAX31855":       ("SPI_Thermocouple_MAX31855", "SPI"),
    "DS18B20":        ("OneWire_Temp_DS18B20", "GPIO"),
    "DHT11":          ("OneWire_DHT11", "GPIO"),
    "DHT22":          ("OneWire_DHT22", "GPIO"),
    # Buzzer
    "BUZZER":         ("Internal_Buzzer", "Internal"),
    "BZ1":            ("Internal_Buzzer", "Internal"),
    # Relay
    "RELAY":           ("Internal_Relay", "Internal"),
    "SRD05":          ("Internal_Relay", "Internal"),
    # RGB LED
    "WS2812":         ("Internal_Neopixel", "Internal"),
    "SK6812":         ("Internal_Neopixel", "Internal"),
    # Card readers
    "RC522":          ("SPI_RFID_RC522", "SPI"),
    "PN532":          ("I2C_NFC_PN532", "I2C"),
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
                pin_config["function"] = f"{bus}_NSS"
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
                    "bus": bus,
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
            "run_mode": "loop",
            "triggers": [],
            "signals": [],
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
            "ram_kb": 144,
            "flash_kb": 512,
            "dual_bank": True,
        },
        "pins": pins,
        "peripherals": peripherals,
    }
    if app_tasks:
        doc["app_tasks"] = app_tasks

    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _detect_format(text: str) -> str:
    """Detect netlist format from content.

    Returns:
        'enet' for EasyEDA Pro .enet JSON,
        'xml' for KiCad XML format,
        'sexpr' for KiCad S-Expression format.
    """
    stripped = text.strip()
    if stripped.startswith("{"):
        # JSON format (EasyEDA Pro .enet)
        return "enet"
    if stripped.startswith("<?xml") or stripped.startswith("<export"):
        return "xml"
    if stripped.startswith("(kicad_netlist"):
        return "sexpr"
    if "<export" in stripped:
        return "xml"
    return "sexpr"


# ---------------------------------------------------------------------------
# S-Expression parser for KiCad 6+ netlist format
# ---------------------------------------------------------------------------

_SEXPR_STRING_RE = re.compile(r'"([^"]*)"')


def _tokenize_sexpr(text: str) -> List[str]:
    """Tokenize an S-Expression string into tokens.

    Splits on whitespace, parentheses, and preserves quoted strings.

    Args:
        text: Raw S-Expression text.

    Returns:
        List of tokens: '(', ')', or string values (unquoted).
    """
    tokens: List[str] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Whitespace
        if ch in (' ', '\t', '\n', '\r'):
            i += 1
            continue

        # Parentheses
        if ch in ('(', ')'):
            tokens.append(ch)
            i += 1
            continue

        # Quoted string
        if ch == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == '\\' and j + 1 < n:
                    j += 1  # skip escaped char
                j += 1
            value = text[i+1:j]
            tokens.append(value)
            i = j + 1  # skip closing quote
            continue

        # Unquoted atom
        j = i
        while j < n and text[j] not in (' ', '\t', '\n', '\r', '(', ')', '"'):
            j += 1
        tokens.append(text[i:j])
        i = j

    return tokens


def _parse_sexpr_tokens(tokens: List[str], pos: int = 0) -> Tuple[Any, int]:
    """Recursively parse S-Expression tokens into nested lists.

    Args:
        tokens: Tokenized S-Expression.
        pos: Current position in the token list.

    Returns:
        (parsed_value, next_position)
    """
    if pos >= len(tokens):
        return None, pos

    token = tokens[pos]

    if token == '(':
        pos += 1
        lst: List[Any] = []
        while pos < len(tokens) and tokens[pos] != ')':
            value, pos = _parse_sexpr_tokens(tokens, pos)
            lst.append(value)
        if pos < len(tokens) and tokens[pos] == ')':
            pos += 1
        return lst, pos
    elif token == ')':
        return None, pos
    else:
        return token, pos + 1


def _sexpr_val(items: List[Any]) -> Any:
    """Convert the contents of a list (after the tag) to a value.

    - Single string atom → return the string
    - Single sublist → recursively parse
    - Multiple items → treat as alternating (key value) pairs → dict
    """
    if len(items) == 0:
        return None
    if len(items) == 1:
        val = items[0]
        if isinstance(val, list):
            return _sexpr_to_dict(val)  # returns {tag: value}
        return val

    # Multiple items: alternating key value or tagged sublists
    result: Dict[str, Any] = {}
    j = 0
    while j < len(items):
        item = items[j]
        if isinstance(item, list):
            # Tagged sublist: (tag ...)  → {tag: value}
            s = _sexpr_to_dict(item)
            for sk, sv in s.items():
                if sk not in result:
                    result[sk] = sv
                elif isinstance(result[sk], list):
                    result[sk].append(sv)
                else:
                    result[sk] = [result[sk], sv]
            j += 1
        elif isinstance(item, str):
            key = item
            if j + 1 < len(items):
                nxt = items[j + 1]
                if isinstance(nxt, list):
                    value = _sexpr_val(nxt)
                else:
                    value = nxt
                j += 1
            else:
                value = None
            if key not in result:
                result[key] = value
            elif isinstance(result[key], list):
                result[key].append(value)
            else:
                result[key] = [result[key], value]
            j += 1
        else:
            j += 1
    return result


def _sexpr_to_dict(sexpr: List[Any]) -> Dict[str, Any]:
    """Convert a parsed S-Expression list into {tag: value}.

    Examples:
        (ref "U1")  →  {"ref": "U1"}
        (comp (ref "U1") (value "STM32"))  →  {"comp": {"ref": "U1", "value": "STM32"}}
        (nets (net ...) (net ...))  →  {"nets": {"net": [{...}, {...}]}}
    """
    if not isinstance(sexpr, list) or len(sexpr) == 0:
        return {}

    tag = sexpr[0]
    if not isinstance(tag, str):
        return {}

    value = _sexpr_val(sexpr[1:])
    return {tag: value}


def _parse_components_sexpr(root_data: Dict[str, Any]) -> Tuple[Dict[str, dict], Optional[str]]:
    """Parse components from S-Expr data.

    Returns:
        (components_dict, mcu_ref)
    """
    components: Dict[str, dict] = {}
    mcu_ref: Optional[str] = None

    comps = root_data.get("components") or {}
    comp_list = comps.get("comp", [])
    if not isinstance(comp_list, list):
        comp_list = [comp_list]

    for comp in comp_list:
        if not isinstance(comp, dict):
            continue
        ref = comp.get("ref", "")
        value = comp.get("value", "")
        footprint = comp.get("footprint", "")

        if isinstance(ref, dict):
            ref = ref.get("ref", "") if hasattr(ref, 'get') else ""
        if isinstance(value, dict):
            value = value.get("value", "") if hasattr(value, 'get') else ""

        components[ref] = {
            "value": value.strip() if isinstance(value, str) else "",
            "footprint": footprint.strip() if isinstance(footprint, str) else "",
        }

        if _is_mcu(value if isinstance(value, str) else ""):
            mcu_ref = ref

    return components, mcu_ref


def _parse_nets_sexpr(root_data: Dict[str, Any]) -> List[dict]:
    """Parse nets from S-Expr data."""
    nets: List[dict] = []

    nets_data = root_data.get("nets") or {}
    net_list = nets_data.get("net", [])
    if not isinstance(net_list, list):
        net_list = [net_list]

    for net in net_list:
        if not isinstance(net, dict):
            continue
        net_info = {
            "code": str(net.get("code", "")),
            "name": str(net.get("name", "")),
            "nodes": [],
        }

        nodes = net.get("node", [])
        if not isinstance(nodes, list):
            nodes = [nodes]

        for node in nodes:
            if isinstance(node, dict):
                net_info["nodes"].append({
                    "ref": str(node.get("ref", "")),
                    "pin": str(node.get("pin", "")),
                })

        nets.append(net_info)

    return nets


def parse_netlist_sexpr(sexpr_text: str) -> str:
    """Parse a KiCad S-Expression netlist and return H2C YAML.

    Args:
        sexpr_text: Raw S-Expression netlist text.

    Returns:
        H2C hardware YAML string.

    Raises:
        ValueError: If no MCU component is found or format is invalid.
    """
    import yaml

    # Remove comments (lines starting with ;)
    lines = [l for l in sexpr_text.split('\n') if not l.strip().startswith(';')]
    clean_text = '\n'.join(lines)

    tokens = _tokenize_sexpr(clean_text)
    parsed, _ = _parse_sexpr_tokens(tokens)
    if not isinstance(parsed, list) or len(parsed) == 0:
        raise ValueError("Invalid S-Expression netlist: could not parse")

    root_data = _sexpr_to_dict(parsed)

    # Unwrap top-level kicad_netlist wrapper
    if "kicad_netlist" in root_data:
        root_data = root_data["kicad_netlist"]

    components, mcu_ref = _parse_components_sexpr(root_data)

    if mcu_ref is None:
        raise ValueError("No MCU component found in netlist. "
                         "Expected a component with STM32/GD32/AT32 value.")

    mcu_value = components[mcu_ref]["value"]
    nets = _parse_nets_sexpr(root_data)

    # Reuse the existing _build_yaml which takes the same intermediate format
    return _build_yaml(mcu_ref, mcu_value, components, nets)


# ---------------------------------------------------------------------------
# Unified parse entry points
# ---------------------------------------------------------------------------

def parse_netlist_string(text: str) -> str:
    """
    Parse an EDA netlist string and return H2C YAML.

    Supports EasyEDA Pro .enet JSON, KiCad XML, and KiCad S-Expression.
    Format is auto-detected from content.

    Args:
        text: Raw netlist string.

    Returns:
        H2C hardware YAML string.
    """
    fmt = _detect_format(text)

    if fmt == "enet":
        from .netlist_parser_enet import parse_netlist_enet
        return parse_netlist_enet(text)

    if fmt == "xml":
        root = ET.fromstring(text)
        components, mcu_ref = _parse_components(root)

        if mcu_ref is None:
            raise ValueError("No MCU component found in netlist. "
                             "Expected a component with STM32/GD32/AT32 value.")

        mcu_value = components[mcu_ref]["value"]
        nets = _parse_nets(root)
        return _build_yaml(mcu_ref, mcu_value, components, nets)
    else:
        return parse_netlist_sexpr(text)


def parse_netlist(file_path: str) -> str:
    """
    Parse an EDA netlist file and return H2C YAML.

    Supports EasyEDA Pro .enet, KiCad legacy XML (.net), and
    KiCad 6+ S-Expression formats. Format is auto-detected from file content.

    Args:
        file_path: Path to the netlist file.

    Returns:
        H2C hardware YAML string.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Netlist file not found: '{file_path}'")

    text = path.read_text(encoding="utf-8")
    return parse_netlist_string(text)


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
