#!/usr/bin/env python3
"""
hw2c CLI: unified command-line entry point.

Usage:
    hw2c parse <netlist> [--bom <bom.csv>] [--yaml <user.yaml>] [-o <output.yaml>] [--summary]
    hw2c gen   <hardware.yaml> -o <output_dir> [--hil] [--dry-run]
    hw2c --version
"""

import argparse
import sys
from pathlib import Path


def _cmd_parse(args: argparse.Namespace) -> int:
    """Run the netlist/BOM parsing pipeline."""
    from parser.pipeline import run_pipeline

    netlist_path = args.netlist
    bom_path = args.bom
    yaml_path = args.yaml
    output_path = args.output

    # Read netlist file
    netlist_text = Path(netlist_path).read_text(encoding="utf-8")

    # Read optional files
    bom_text = None
    if bom_path:
        bom_text = Path(bom_path).read_text(encoding="utf-8")

    yaml_text = None
    if yaml_path:
        yaml_text = Path(yaml_path).read_text(encoding="utf-8")

    result = run_pipeline(
        netlist_text=netlist_text,
        bom_text=bom_text,
        yaml_text=yaml_text,
    )

    if result.warnings:
        for w in result.warnings:
            print(f"WARNING: {w}", file=sys.stderr)

    if args.summary:
        print(f"=== Hardware Pipeline Summary ===")
        print(f"  Warnings: {len(result.warnings)}")
        print(f"  Bus hints: {len(result.annotations.bus_hints)}")
        print(f"  Peripheral hints: {len(result.annotations.peripheral_hints)}")
        print(f"  Power hints: {len(result.annotations.power_hints)}")
        print(f"  Signal role hints: {len(result.annotations.signal_role_hints)}")
        if result.passive_constraints:
            print(result.passive_constraints.summary())
        if result.report.issues:
            print(f"  Cross-validation: {len(result.report.issues)} issue(s)")
        else:
            print(f"  Cross-validation: no user YAML to compare")

    if output_path:
        Path(output_path).write_text(result.hardware_yaml or result.yaml, encoding="utf-8")
        print(f"Hardware YAML written to {output_path}")
    else:
        # stdout: print monolithic yaml for backward compat
        print(result.yaml)

    # Write task.yaml if --task specified
    task_path = getattr(args, 'task', None)
    if task_path and result.task_yaml:
        Path(task_path).write_text(result.task_yaml, encoding="utf-8")
        print(f"Task YAML written to {task_path}")

    return 0


def _cmd_gen(args: argparse.Namespace) -> int:
    """Run the code generator."""
    from generator.generate import main as gen_main

    # Simulate command-line arguments for generate.main()
    sys.argv = [
        "hw2c-gen",
        "-i", args.input,
        "-o", args.output,
    ]
    if args.hil:
        sys.argv.append("--hil")
    if args.dry_run:
        sys.argv.append("--dry-run")
    if args.diff:
        sys.argv.append("--diff")
    if args.force:
        sys.argv.append("--force")
    if args.target:
        sys.argv.extend(["--target", args.target])
    if args.no_validate_pins:
        sys.argv.append("--no-validate-pins")
    if args.no_allocate_pins:
        sys.argv.append("--no-allocate-pins")
    if args.task:
        sys.argv.extend(["--task", args.task])
    if args.bind:
        sys.argv.extend(["--bind", args.bind])

    gen_main()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hw2c",
        description="Hardware2Code: parse EDA netlist/BOM, generate embedded firmware",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Show version and exit",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ---- parse ----
    p_parse = sub.add_parser("parse", help="Parse netlist/BOM → hardware YAML")
    p_parse.add_argument(
        "netlist",
        help="Path to netlist file (.enet / .net)",
    )
    p_parse.add_argument(
        "--bom", default=None,
        help="Path to BOM CSV file (optional)",
    )
    p_parse.add_argument(
        "--yaml", default=None,
        help="Path to user hardware YAML for cross-validation (optional)",
    )
    p_parse.add_argument(
        "-o", "--output", default=None,
        help="Output hardware YAML file path (default: stdout)",
    )
    p_parse.add_argument(
        "--task", default=None,
        help="Output task YAML file path (default: none)",
    )
    p_parse.add_argument(
        "--summary", action="store_true",
        help="Print summary before YAML output",
    )

    # ---- gen ----
    p_gen = sub.add_parser("gen", help="Generate embedded firmware from hardware YAML")
    p_gen.add_argument(
        "-i", "--input", required=True,
        help="Path to hardware YAML file",
    )
    p_gen.add_argument(
        "-o", "--output", required=True,
        help="Output directory for generated project",
    )
    p_gen.add_argument(
        "--hil", action="store_true",
        help="Generate HIL test firmware",
    )
    p_gen.add_argument(
        "--target", default="stm32",
        help="Target platform (default: stm32)",
    )
    p_gen.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be generated without writing files",
    )
    p_gen.add_argument(
        "--diff", action="store_true",
        help="Show diff against existing files",
    )
    p_gen.add_argument(
        "--force", action="store_true",
        help="Overwrite existing files without confirmation",
    )
    p_gen.add_argument(
        "--no-validate-pins", action="store_true",
        help="Skip pin validation",
    )
    p_gen.add_argument(
        "--no-allocate-pins", action="store_true",
        help="Skip auto pin allocation",
    )
    p_gen.add_argument(
        "--task", default=None,
        help="Path to task YAML file (task.yaml)",
    )
    p_gen.add_argument(
        "--bind", default=None,
        help="Path to bind YAML file (bind.yaml)",
    )

    args = parser.parse_args()

    if args.version:
        import importlib.metadata
        try:
            version = importlib.metadata.version("hw2c")
        except importlib.metadata.PackageNotFoundError:
            version = "0.4.0 (dev)"
        print(f"hw2c {version}")
        return

    if args.command == "parse":
        sys.exit(_cmd_parse(args))
    elif args.command == "gen":
        sys.exit(_cmd_gen(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
