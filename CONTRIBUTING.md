# Contributing to Hardware2Code

## 1. Project Architecture

```
Hardware2Code
├── models/          # Peripheral model YAML definitions
├── templates/       # Jinja2 templates (C source, tests, config)
├── generator/       # Python code generation engine
│   ├── generate.py  # Main generator entry point
│   ├── validator.py # YAML validation
│   ├── context_builder.py  # Template rendering context
│   └── paths.py     # Path constants
├── examples/        # Example hardware.yaml projects
├── static/          # Static vendor files (HAL, Unity)
├── parser/          # Netlist/BOM parsers
└── docs/            # Documentation
```

## 2. Local Development Setup

- Python 3.10+
- Install dependencies: `pip install pyyaml jinja2`
- Run generator: `python generator/generate.py -i examples/cli_demo/hardware.yaml -o output/cli_demo`
- Run tests: `cd output/cli_demo/test ; python run_tests.py`

## 3. Adding a New Peripheral Model

1. Create `models/New_Peripheral.yaml` with required fields:
   `model`, `type`, `interface`, `driver_template`, `header_template`,
   `capabilities`, `default_params`, `extra_schema`
2. Create driver templates:
   - `templates/drivers/drv_new_peripheral.c.j2`
   - `templates/drivers/drv_new_peripheral.h.j2`
3. Create test template: `templates/test/test_new_peripheral.c.j2`
4. Register the type in `validator.py` — append to `valid_types` list
5. Add detection logic in `context_builder.py` — set `has_xxx = True`
6. Wire the test template in `generate.py` under the `test_templates` section

## 4. DSL Syntax Reference

### Guard Expressions

```yaml
guard:
  foo:
    oneof: [0, 1]           # value must be one of listed
    range: [0, 65535]       # value must be within range
    depends: [bar, baz]     # value requires these fields present
    unless:                 # conditional requirement
      field: mode
      oneof: [disable]
```

### Action Syntax

```yaml
action:
  type: write | read | poll | sequence  # action kind
  target: DEVICE_ADDR                   # I2C/UART/SPI address
  channel: 0                            # peripheral instance index
  payload: [0x01, 0x02, 0x03]          # byte sequence
  delay_ms: 10                          # post-action delay
```

### Variable Declaration

```yaml
var:
  name: pulse_count
  type: uint16_t | int32_t | float
  default: 0
  persist: false          # retain across power cycles
```

## 5. Pull Request Guidelines

- Run the reference project before submitting:
  `python generator/generate.py -i examples/cli_demo/hardware.yaml -o output/cli_demo`
- Ensure all tests pass
- Keep modules under ~100 lines (single responsibility principle)
- Use `paths.py` for all filesystem path constants — never hardcode paths
- Use `TypedDict` for context structures passed to templates
- **Do not modify auto-generated output files directly** — change the Jinja2 templates instead
