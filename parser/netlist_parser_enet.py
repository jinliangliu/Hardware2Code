"""
netlist_parser_enet.py
Parse EasyEDA Pro .enet JSON netlist and convert to H2C hardware YAML.

EasyEDA Pro exports schematic netlists as `.enet` files in JSON format:
  - version: format version (currently "2.0.0")
  - components: keyed by unique ID, each with props and pinInfoMap
  - designRule, differentialPair, netClass, equalLengthNetGroup

The parser reconstructs nets by grouping pin connections that share
the same net name, then delegates to the shared _build_yaml() function.

Usage:
    from parser.netlist_parser_enet import parse_netlist_enet
    yaml_str = parse_netlist_enet(json_text)
"""

import json
import itertools
from typing import Dict, List, Optional, Tuple, Any

from .netlist_parser import _build_yaml, _is_mcu


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_netlist_enet(enet_text: str) -> str:
    """Parse an EasyEDA Pro .enet JSON netlist and return H2C YAML.

    Args:
        enet_text: Raw .enet JSON string.

    Returns:
        H2C hardware YAML string.

    Raises:
        ValueError: If no MCU component is found or JSON is invalid.
    """
    try:
        enet = json.loads(enet_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in .enet netlist: {e}") from e

    components_raw = enet.get("components", {})
    if not components_raw:
        raise ValueError("No components found in .enet netlist")

    # ---- Step 1: Convert EasyEDA components to intermediate format ----
    components: Dict[str, dict] = {}
    mcu_ref: Optional[str] = None

    for uid, comp_data in components_raw.items():
        props = comp_data.get("props", {})
        designator = props.get("Designator", "").strip()
        value = props.get("Value", "").strip()
        footprint = props.get("FootprintName", "").strip()

        if not designator:
            continue

        components[designator] = {
            "value": value,
            "footprint": footprint,
            "_uid": uid,
            "_raw": comp_data,  # preserve for reference
        }

        if _is_mcu(value):
            mcu_ref = designator

    if mcu_ref is None:
        raise ValueError(
            "No MCU component found in .enet netlist. "
            "Expected a component with STM32/GD32/AT32 value."
        )

    mcu_value = components[mcu_ref]["value"]

    # ---- Step 2: Reconstruct nets from pinInfoMap ----
    nets = _reconstruct_nets(components_raw, components, mcu_ref)

    # ---- Step 3: Build YAML using shared logic ----
    return _build_yaml(mcu_ref, mcu_value, components, nets)


# ---------------------------------------------------------------------------
# Net reconstruction
# ---------------------------------------------------------------------------

def _reconstruct_nets(
    components_raw: Dict[str, dict],
    components: Dict[str, dict],
    mcu_ref: str,
) -> List[dict]:
    """Reconstruct net list from pinInfoMap connections.

    In EasyEDA .enet, each pin has a 'net' field. Pins sharing the same
    net name are electrically connected. We group them to form nets.

    Args:
        components_raw: Raw EasyEDA components dict (keyed by uid).
        components: Converted components dict (keyed by designator).
        mcu_ref: Designator of the MCU component.

    Returns:
        List of net dicts: [{code, name, nodes: [{ref, pin}]}]
    """
    # Build designator → uid lookup
    uid_to_ref: Dict[str, str] = {}
    for ref, comp in components.items():
        uid = comp.get("_uid", "")
        if uid:
            uid_to_ref[uid] = ref

    # Group pin connections by net name
    # net_name → [(designator, pin_number)]
    net_groups: Dict[str, List[Tuple[str, str]]] = {}

    for uid, comp_data in components_raw.items():
        designator = uid_to_ref.get(uid, uid)
        pin_map = comp_data.get("pinInfoMap", {})

        for pin_key, pin_info in pin_map.items():
            if not isinstance(pin_info, dict):
                continue
            net_name = pin_info.get("net", "")
            if not net_name:  # NC pin
                continue
            pin_number = str(pin_info.get("number", pin_key))

            if net_name not in net_groups:
                net_groups[net_name] = []
            net_groups[net_name].append((designator, pin_number))

    # Convert to net list format compatible with _build_yaml
    nets: List[dict] = []
    code_counter = itertools.count(1)

    for net_name, nodes in sorted(net_groups.items()):
        # Filter: keep nets that connect to at least 2 different components
        # (single-component nets are usually NC or internal pins)
        refs_in_net = set(ref for ref, _ in nodes)
        if len(refs_in_net) < 2:
            continue

        # Skip pure power nets that don't connect to MCU
        # (e.g., GND/GND connections between passives only)
        if mcu_ref not in refs_in_net:
            # Still include if it connects a known peripheral to something
            has_peripheral = any(
                ref != mcu_ref for ref in refs_in_net
            )
            if not has_peripheral:
                continue

        net_code = str(next(code_counter))
        net_nodes = [
            {"ref": ref, "pin": pin} for ref, pin in nodes
        ]

        nets.append({
            "code": net_code,
            "name": net_name,
            "nodes": net_nodes,
        })

    return nets


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import yaml

    if len(sys.argv) < 2:
        print("Usage: python netlist_parser_enet.py <netlist.enet> [output.yaml]")
        sys.exit(1)

    try:
        text = open(sys.argv[1], encoding="utf-8").read()
        yaml_content = parse_netlist_enet(text)
    except (FileNotFoundError, json.JSONDecodeError, yaml.YAMLError,
            ValueError, KeyError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"YAML written to {sys.argv[2]}")
    else:
        print(yaml_content)
