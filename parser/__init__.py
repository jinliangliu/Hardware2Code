"""
Hardware2Code input parsers.
Convert various hardware description formats into H2C YAML.

Modules:
  - netlist_parser:      Parse EDA netlists (EasyEDA .enet / KiCad XML / S-Expr) → H2C YAML
  - netlist_parser_enet: EasyEDA Pro .enet JSON parser (primary target)
  - bom_parser:          Parse CSV BOM → H2C YAML peripherals list
  - passive_extractor:   Extract passive component constraints from BOM
  - cross_validator:     Cross-validate netlist/BOM YAML vs user hardware YAML
  - schematic_annotator: Extract design intent from net naming conventions
  - pipeline:            Unified pipeline orchestrating all parsers
"""

from .netlist_parser import parse_netlist, parse_netlist_string
from .netlist_parser_enet import parse_netlist_enet
from .bom_parser import parse_bom, parse_bom_string
from .passive_extractor import PassiveExtractor, PassiveConstraints, PassiveComponent
from .cross_validator import CrossValidator, CrossReport, CrossIssue
from .schematic_annotator import (
    SchematicAnnotator, AnnotationHints, BusHint,
    PeripheralHint, PowerHint,
)
from .pipeline import HardwarePipeline, PipelineResult, run_pipeline

__all__ = [
    # netlist_parser
    "parse_netlist",
    "parse_netlist_string",
    "parse_netlist_enet",
    # bom_parser
    "parse_bom",
    "parse_bom_string",
    # passive_extractor
    "PassiveExtractor",
    "PassiveConstraints",
    "PassiveComponent",
    # cross_validator
    "CrossValidator",
    "CrossReport",
    "CrossIssue",
    # schematic_annotator
    "SchematicAnnotator",
    "AnnotationHints",
    "BusHint",
    "PeripheralHint",
    "PowerHint",
    # pipeline
    "HardwarePipeline",
    "PipelineResult",
    "run_pipeline",
]
