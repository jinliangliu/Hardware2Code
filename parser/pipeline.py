"""
pipeline.py
Unified hardware analysis pipeline for Phase 4: Netlist/BOM 驱动.

Takes KiCad design files (netlist + optional BOM) and user hardware YAML,
runs all Phase 4 parsers, and produces an enriched, cross-validated
hardware YAML with annotations.

Usage:
    from parser.pipeline import HardwarePipeline

    pipe = HardwarePipeline()
    result = pipe.run(
        netlist_path="hardware.net",
        bom_path="hardware.csv",
        hw_yaml_path="hardware.yaml",
    )
    print(result.report)
    with open("hardware_enriched.yaml", "w") as f:
        f.write(result.yaml)

CLI:
    python -m parser.pipeline hardware.net --bom hardware.csv \\
        --yaml hardware.yaml --output hardware_enriched.yaml
"""

from __future__ import annotations

import csv
import io
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

from .netlist_parser import parse_netlist, parse_netlist_string
from .bom_parser import parse_bom, parse_bom_string
from .passive_extractor import PassiveExtractor, PassiveConstraints
from .schematic_annotator import SchematicAnnotator, AnnotationHints
from .cross_validator import CrossValidator, CrossReport

logger = logging.getLogger("hw2c.pipeline")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """Aggregated output of the full hardware analysis pipeline."""

    yaml: str = ""
    """Enriched hardware YAML merging netlist, BOM, and annotations."""

    report: CrossReport = field(default_factory=CrossReport)
    """Cross-validation report (empty if no user YAML provided)."""

    annotations: AnnotationHints = field(default_factory=AnnotationHints)
    """Schematic annotation hints extracted from net names."""

    passive_constraints: PassiveConstraints = field(
        default_factory=PassiveConstraints
    )
    """Passive component constraints from BOM."""

    warnings: List[str] = field(default_factory=list)
    """Non-fatal warnings from the pipeline run."""

    def summary(self) -> str:
        lines = ["=== Hardware Pipeline Summary ==="]
        lines.append(f"  Warnings: {len(self.warnings)}")
        lines.append(f"  Bus hints: {len(self.annotations.bus_hints)}")
        lines.append(f"  Peripheral hints: {len(self.annotations.peripheral_hints)}")
        lines.append(f"  Power hints: {len(self.annotations.power_hints)}")
        lines.append(f"  Signal role hints: {len(self.annotations.signal_role_hints)}")
        if self.passive_constraints:
            lines.append(self.passive_constraints.summary())
        if self.report.issues:
            lines.append(str(self.report))
        else:
            lines.append("  Cross-validation: no user YAML to compare")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class HardwarePipeline:
    """Orchestrates all Phase 4 parsers into a single workflow.

    Input:
        - Netlist file (KiCad XML or S-Expr) — required
        - BOM file (CSV) — optional
        - User hardware YAML — optional

    Output:
        - PipelineResult with enriched YAML, validation report,
          annotations, and passive constraints.

    Usage:
        pipe = HardwarePipeline()
        result = pipe.run(
            netlist_path="hardware.net",
            bom_path="hardware.csv",
            hw_yaml_path="hardware.yaml",
        )
        print(result.summary())
    """

    _CFG_DEFAULTS: dict = {
        "validate_mcu_match": True,
        "validate_pin_conflicts": True,
        "validate_periph_mismatches": True,
        "annotate_buses": True,
        "annotate_peripherals": True,
        "annotate_power": True,
        "annotate_signal_roles": True,
        "extract_passives": True,
    }

    def __init__(self, **cfg) -> None:
        """Initialise with optional feature flags.

        Keyword Args:
            validate_mcu_match: Check MCU type matches netlist (default True).
            validate_pin_conflicts: Detect pin function conflicts (default True).
            validate_periph_mismatches: Detect peripheral type mismatches (default True).
            annotate_buses: Extract bus hints from net names (default True).
            annotate_peripherals: Group nets by peripheral prefix (default True).
            annotate_power: Detect power domains from net names (default True).
            annotate_signal_roles: Detect signal roles from net names (default True).
            extract_passives: Extract passive constraints from BOM (default True).
        """
        self.cfg = dict(self._CFG_DEFAULTS)
        self.cfg.update(cfg)

        self._netlist_parser = None  # set during run
        self._bom_parser = None
        self._passive_extractor = PassiveExtractor()
        self._annotator = SchematicAnnotator()
        self._validator = CrossValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        netlist_path: Optional[str] = None,
        netlist_text: Optional[str] = None,
        bom_path: Optional[str] = None,
        bom_text: Optional[str] = None,
        hw_yaml_path: Optional[str] = None,
        hw_yaml_text: Optional[str] = None,
    ) -> PipelineResult:
        """Run the full hardware analysis pipeline.

        At minimum, a netlist (file path or text) is required.
        BOM and user hardware YAML are optional.

        Args:
            netlist_path: Path to KiCad netlist file.
            netlist_text: Raw netlist content (alternative to path).
            bom_path: Path to CSV BOM file.
            bom_text: Raw BOM CSV content (alternative to path).
            hw_yaml_path: Path to user-authored hardware YAML.
            hw_yaml_text: Raw hardware YAML content (alternative to path).

        Returns:
            PipelineResult with enriched YAML, reports, and hints.
        """
        result = PipelineResult()

        # ---- 1. Parse netlist (required) ----
        nl_yaml = self._parse_netlist(netlist_path, netlist_text)
        if not nl_yaml:
            result.warnings.append("No netlist data provided; pipeline aborted.")
            return result

        result.yaml = nl_yaml

        # ---- 2. Extract net names for annotation ----
        net_names = self._extract_net_names(netlist_path, netlist_text)
        if net_names and self.cfg.get("annotate_buses"):
            result.annotations = self._annotator.extract(net_names)

        # ---- 3. Parse BOM (optional) ----
        bom_rows: List[dict] = []
        bom_yaml: Optional[str] = None

        if bom_path or bom_text:
            bom_yaml = self._parse_bom(bom_path, bom_text)
            bom_rows = self._parse_bom_rows(bom_path, bom_text)

        # ---- 4. Extract passive constraints ----
        if bom_rows and self.cfg.get("extract_passives"):
            result.passive_constraints = self._passive_extractor.extract(bom_rows)

        # ---- 5. Merge BOM YAML into netlist YAML if both exist ----
        if bom_yaml:
            result.yaml = self._merge_yamls(nl_yaml, bom_yaml)

        # ---- 5b. Build and inject clock configuration ----
        clock_config = self._build_clock_config(
            result.passive_constraints.crystals,
            mcu_clock_mhz=64,
        )
        # Inject clock section into YAML
        merged_doc = yaml.safe_load(result.yaml) or {}
        merged_doc["clock"] = clock_config
        result.yaml = yaml.dump(merged_doc, default_flow_style=False,
                                sort_keys=False, allow_unicode=True)

        # ---- 6. Cross-validate with user YAML ----
        user_yaml = self._resolve_user_yaml(hw_yaml_path, hw_yaml_text)
        if user_yaml and self.cfg.get("validate_pin_conflicts"):
            result.report = self._validator.validate(result.yaml, user_yaml)

        # ---- 7. Embed annotations as YAML comments ----
        result.yaml = self._embed_annotations(result.yaml, result.annotations,
                                               result.passive_constraints)

        return result

    # ------------------------------------------------------------------
    # Input helpers
    # ------------------------------------------------------------------

    def _parse_netlist(self, path: Optional[str],
                       text: Optional[str]) -> str:
        """Parse netlist and return H2C YAML string."""
        if path:
            logger.info("Parsing netlist from file: %s", path)
            try:
                return parse_netlist(path)
            except (ValueError, FileNotFoundError) as exc:
                logger.warning("Netlist parse error: %s", exc)
                return ""
        if text:
            logger.info("Parsing netlist from string (%d chars)", len(text))
            try:
                return parse_netlist_string(text)
            except ValueError as exc:
                logger.warning("Netlist parse error: %s", exc)
                return ""
        return ""

    def _parse_bom(self, path: Optional[str],
                   text: Optional[str]) -> Optional[str]:
        """Parse BOM and return H2C YAML string."""
        if path:
            logger.info("Parsing BOM from file: %s", path)
            return parse_bom(path)
        if text:
            logger.info("Parsing BOM from string (%d chars)", len(text))
            return parse_bom_string(text)
        return None

    def _parse_bom_rows(self, path: Optional[str],
                        text: Optional[str]) -> List[dict]:
        """Parse BOM and return raw rows for passive extraction."""
        if text:
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)
        if path:
            raw = Path(path).read_text(encoding="utf-8")
            reader = csv.DictReader(io.StringIO(raw))
            return list(reader)
        return []

    def _resolve_user_yaml(self, path: Optional[str],
                           text: Optional[str]) -> Optional[str]:
        """Read user hardware YAML from file or string."""
        if text:
            return text
        if path:
            try:
                return Path(path).read_text(encoding="utf-8")
            except (FileNotFoundError, OSError) as exc:
                logger.warning("Cannot read user YAML: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Net name extraction
    # ------------------------------------------------------------------

    def _extract_net_names(
        self,
        netlist_path: Optional[str],
        netlist_text: Optional[str],
    ) -> List[str]:
        """Extract net names from the raw netlist content.

        Works for EasyEDA .enet JSON, KiCad XML, and S-Expression formats.
        """
        raw = ""
        if netlist_text:
            raw = netlist_text
        elif netlist_path:
            try:
                raw = Path(netlist_path).read_text(encoding="utf-8")
            except (FileNotFoundError, OSError) as exc:
                logger.warning("Cannot read netlist for annotations: %s", exc)
                return []
        else:
            return []

        if not raw:
            return []

        stripped = raw.strip()
        if stripped.startswith("{"):
            return self._extract_net_names_enet(raw)
        if stripped.startswith("("):
            return self._extract_net_names_sexpr(raw)
        return self._extract_net_names_xml(raw)

    @staticmethod
    def _extract_net_names_xml(xml_text: str) -> List[str]:
        """Extract net names from KiCad XML netlist."""
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        nets = root.find("nets")
        if nets is None:
            return []
        names: List[str] = []
        for net in nets.findall("net"):
            name = net.get("name", "")
            if name:
                names.append(name)
        return names

    @staticmethod
    def _extract_net_names_sexpr(sexpr_text: str) -> List[str]:
        """Extract net names from KiCad S-Expression netlist."""
        import re
        # Match (name "...") within (net ...) blocks
        pattern = re.compile(r'\(name\s+"([^"]*)"\)')
        return pattern.findall(sexpr_text)

    @staticmethod
    def _extract_net_names_enet(enet_text: str) -> List[str]:
        """Extract net names from EasyEDA Pro .enet JSON netlist.

        Net names are embedded in pinInfoMap[pin].net fields.
        """
        import json
        try:
            enet = json.loads(enet_text)
        except json.JSONDecodeError:
            return []
        names: set = set()
        for comp in enet.get("components", {}).values():
            for pin_info in comp.get("pinInfoMap", {}).values():
                net = pin_info.get("net", "")
                if net and not net.startswith("$"):
                    names.add(net)
        return sorted(names)

    # ------------------------------------------------------------------
    # YAML merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_yamls(netlist_yaml: str, bom_yaml: str) -> str:
        """Merge BOM-derived YAML into netlist-derived YAML.

        Strategy:
        - MCU: netlist takes precedence (it has actual connections).
        - Pins: netlist takes precedence (pin assignments from nets).
        - Peripherals: union — BOM may list peripherals not yet wired.
        - App tasks: union with priority rebalancing.
        """
        nl = yaml.safe_load(netlist_yaml) or {}
        bm = yaml.safe_load(bom_yaml) or {}

        merged: dict = {}

        # MCU — prefer netlist
        merged["mcu"] = nl.get("mcu", bm.get("mcu", {}))

        # Pins — union, netlist pins take priority
        nl_pins = {p.get("id", "").upper(): p for p in nl.get("pins", [])}
        bm_pins = {p.get("id", "").upper(): p for p in bm.get("pins", [])}
        for pid, pin in bm_pins.items():
            if pid not in nl_pins:
                nl_pins[pid] = pin
        merged["pins"] = list(nl_pins.values())

        # Peripherals — union by name, BOM enriches
        nl_peri = {p.get("name", "").lower(): p for p in nl.get("peripherals", [])}
        bm_peri = {p.get("name", "").lower(): p for p in bm.get("peripherals", [])}
        for name, peri in nl_peri.items():
            if name in bm_peri:
                # Merge: BOM may have address/bus info netlist lacks
                bm_entry = bm_peri[name]
                for key in ("address", "bus", "uart", "cs_pin"):
                    if key in bm_entry and key not in peri:
                        peri[key] = bm_entry[key]
            else:
                bm_peri[name] = peri
        merged["peripherals"] = list(bm_peri.values())

        # App tasks — union
        nl_tasks = {t.get("name", ""): t for t in nl.get("app_tasks", [])}
        bm_tasks = {t.get("name", ""): t for t in bm.get("app_tasks", [])}
        for tn, task in nl_tasks.items():
            if tn not in bm_tasks:
                bm_tasks[tn] = task
        merged["app_tasks"] = list(bm_tasks.values())

        return yaml.dump(merged, default_flow_style=False,
                         sort_keys=False, allow_unicode=True)

    @staticmethod
    def _build_clock_config(
        crystals: list,
        mcu_clock_mhz: int = 64,
    ) -> dict:
        """Build a clock configuration section from detected crystals.

        Detects HSE (MHz-range) and LSE (kHz-range) crystals from BOM,
        and builds a complete clock tree with sensible defaults.
        Falls back to HSI/LSI if external crystals are not found.
        """
        hse_hz: int | None = None
        lse_hz: int | None = None

        for xtal in crystals:
            if xtal.frequency_hz is None:
                continue
            if xtal.frequency_hz >= 1e6:  # MHz range → HSE
                if hse_hz is None or xtal.frequency_hz > hse_hz:
                    hse_hz = int(xtal.frequency_hz)
            elif xtal.frequency_hz < 1e6:  # kHz range → LSE
                if lse_hz is None:
                    lse_hz = int(xtal.frequency_hz)

        # HSE section
        hse = {
            "present": hse_hz is not None,
            "frequency_hz": hse_hz or 8000000,
        }

        # LSE section
        lse = {
            "present": lse_hz is not None,
            "frequency_hz": lse_hz or 32768,
        }

        # HSI = 16 MHz, LSI = ~32 kHz (fixed on STM32G0)
        hsi_hz = 16_000_000
        lsi_hz = 32_000

        # PLL calculation: target SYSCLK = mcu_clock_mhz MHz
        target_sysclk = mcu_clock_mhz * 1_000_000

        # Prefer HSE for PLL if available, else HSI
        if hse["present"] and hse_hz:
            pll_source = "HSE"
            pll_in = hse_hz
        else:
            pll_source = "HSI"
            pll_in = hsi_hz

        # Compute PLL M/N/R to hit target
        # PLLVCO = pll_in / M * N  (must be 64-344 MHz on G0)
        # SYSCLK = PLLVCO / R
        # Try M=1, find N and R
        m = 1
        best_n = 8
        best_r = 2
        best_err = abs(target_sysclk - (pll_in // m * best_n // best_r))

        for n in range(8, 86, 2):  # N = 8..86 (even only on G0)
            for r in (2, 4, 6, 8):  # R = 2,4,6,8
                vco = pll_in // m * n
                if vco < 64_000_000 or vco > 344_000_000:
                    continue
                sysclk = vco // r
                err = abs(target_sysclk - sysclk)
                if err < best_err:
                    best_err = err
                    best_n = n
                    best_r = r

        pll = {
            "source": pll_source,
            "m": m,
            "n": best_n,
            "r": best_r,
        }

        # Clock source selection for SYSCLK
        sysclk_source = "PLL" if not (best_n == 1 and best_r == 1) else pll_source

        clock = {
            "hsi_hz": hsi_hz,
            "lsi_hz": lsi_hz,
            "hse": hse,
            "lse": lse,
            "pll": pll,
            "sysclk": {
                "source": sysclk_source,
                "frequency_hz": pll_in // m * best_n // best_r,
            },
            "apb": {
                "prescaler": 1,
            },
            "freertos_tick": {
                "source": "SysTick",
                "frequency_hz": 1000,
            },
        }

        return clock

    # ------------------------------------------------------------------
    # Annotation embedding
    # ------------------------------------------------------------------

    @staticmethod
    def _embed_annotations(
        yaml_str: str,
        hints: AnnotationHints,
        constraints: PassiveConstraints,
    ) -> str:
        """Embed annotation hints and passive constraints as YAML comments.

        Comments are prefixed with '# hw2c-annot:' so tools can locate them.
        """
        lines = yaml_str.splitlines()
        result_lines: List[str] = []

        # ---- Bus hints ----
        if hints.bus_hints:
            result_lines.append("# hw2c-annot: Detected bus assignments from net names")
            for bh in hints.bus_hints:
                sigs = ",".join(sorted(bh.signals))
                result_lines.append(
                    f"# hw2c-annot:   {bh.bus_name} ({bh.bus_type}): {sigs}"
                )
            result_lines.append("")

        # ---- Peripheral hints ----
        if hints.peripheral_hints:
            result_lines.append(
                "# hw2c-annot: Detected peripheral groupings from net names"
            )
            for ph in hints.peripheral_hints:
                result_lines.append(
                    f"# hw2c-annot:   {ph.name} [{ph.interface}]"
                )
            result_lines.append("")

        # ---- Power hints ----
        if hints.power_hints:
            result_lines.append(
                "# hw2c-annot: Detected power domains from net names"
            )
            for ph in hints.power_hints:
                detail = f"{ph.net_name} → {ph.domain}"
                if ph.voltage is not None:
                    detail += f" ({ph.voltage}V)"
                result_lines.append(f"# hw2c-annot:   {detail}")
            result_lines.append("")

        # ---- Signal roles ----
        if hints.signal_role_hints:
            result_lines.append(
                "# hw2c-annot: Detected signal roles from net names"
            )
            for net, role in sorted(hints.signal_role_hints.items()):
                result_lines.append(f"# hw2c-annot:   {net} → {role}")
            result_lines.append("")

        # ---- Passive constraints ----
        if (constraints.power_regulators or constraints.crystals or
                constraints.connectors or constraints.decoupling_caps):
            result_lines.append(
                "# hw2c-annot: Passive component constraints from BOM"
            )
            for reg in constraints.power_regulators:
                detail = f"{reg.designator} ({reg.value})"
                if reg.output_voltage:
                    detail += f" Vout={reg.output_voltage}V"
                result_lines.append(f"# hw2c-annot:   REG: {detail}")
            for xtal in constraints.crystals:
                detail = f"{xtal.designator} ({xtal.value})"
                if xtal.frequency_hz:
                    if xtal.frequency_hz >= 1e6:
                        detail += f" {xtal.frequency_hz/1e6:.3f}MHz"
                    else:
                        detail += f" {xtal.frequency_hz/1e3:.1f}kHz"
                result_lines.append(f"# hw2c-annot:   XTAL: {detail}")
            for conn in constraints.connectors:
                detail = f"{conn.designator} ({conn.value})"
                if conn.pin_count:
                    detail += f" {conn.pin_count}p"
                result_lines.append(f"# hw2c-annot:   CONN: {detail}")
            for cap in constraints.decoupling_caps[:6]:
                detail = f"{cap.designator} ({cap.value})"
                if cap.capacitance_farad:
                    if cap.capacitance_farad >= 1e-6:
                        detail += f" {cap.capacitance_farad*1e6:.1f}µF"
                    else:
                        detail += f" {cap.capacitance_farad*1e9:.1f}nF"
                result_lines.append(f"# hw2c-annot:   CAP: {detail}")
            result_lines.append("")

        result_lines.extend(lines)
        return "\n".join(result_lines) + "\n"


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def run_pipeline(
    netlist_path: Optional[str] = None,
    netlist_text: Optional[str] = None,
    bom_path: Optional[str] = None,
    bom_text: Optional[str] = None,
    hw_yaml_path: Optional[str] = None,
    hw_yaml_text: Optional[str] = None,
    **cfg,
) -> PipelineResult:
    """Convenience wrapper: run the full pipeline in one call.

    Args:
        netlist_path, netlist_text, bom_path, bom_text,
        hw_yaml_path, hw_yaml_text: Input sources (netlist required).
        **cfg: Feature flags passed to HardwarePipeline.__init__.

    Returns:
        PipelineResult with enriched YAML, reports, and hints.
    """
    pipe = HardwarePipeline(**cfg)
    return pipe.run(
        netlist_path=netlist_path,
        netlist_text=netlist_text,
        bom_path=bom_path,
        bom_text=bom_text,
        hw_yaml_path=hw_yaml_path,
        hw_yaml_text=hw_yaml_text,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="hw2c Hardware Analysis Pipeline — Phase 4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m parser.pipeline hardware.net
  python -m parser.pipeline hardware.net --bom hardware.csv
  python -m parser.pipeline hardware.net --bom hardware.csv --yaml hardware.yaml
  python -m parser.pipeline hardware.net -o enriched.yaml
        """,
    )
    ap.add_argument("netlist", help="Path to KiCad netlist file (.net/.xml)")
    ap.add_argument("--bom", "-b", help="Path to CSV BOM file")
    ap.add_argument("--yaml", "-y", help="Path to user hardware.yaml for "
                    "cross-validation")
    ap.add_argument("--output", "-o", help="Output path for enriched YAML "
                    "(default: stdout)")
    ap.add_argument("--no-validate", action="store_true",
                    help="Skip cross-validation even if --yaml is given")
    ap.add_argument("--summary", "-s", action="store_true",
                    help="Print pipeline summary to stderr")
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s:%(name)s:%(message)s")

    pipe = HardwarePipeline(
        validate_pin_conflicts=not args.no_validate,
        validate_periph_mismatches=not args.no_validate,
    )

    try:
        result = pipe.run(
            netlist_path=args.netlist,
            bom_path=args.bom,
            hw_yaml_path=args.yaml,
        )
    except (ValueError, FileNotFoundError, yaml.YAMLError, OSError) as exc:
        print(f"Pipeline error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.summary:
        print(result.summary(), file=sys.stderr)

    if result.warnings:
        for w in result.warnings:
            print(f"Warning: {w}", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(result.yaml, encoding="utf-8")
        print(f"Enriched YAML written to {args.output}")
    else:
        print(result.yaml)

    # Exit with error if validation fails
    if result.report.has_errors:
        sys.exit(1)
