# Installation

## Prerequisites

- Python 3.10 or later
- Git (with submodule support)
- GNU Arm Embedded Toolchain (`arm-none-eabi-gcc`) for firmware compilation
- OpenOCD (optional, for flashing via DAP-Link)

## Clone the Repository

```bash
git clone --recurse-submodules https://github.com/jinliangliu/hw2c.git
cd hw2c
```

The `--recurse-submodules` flag is required to pull in:
- `static/stm32g0/` — HAL, CMSIS, and FreeRTOS-Kernel
- `static/unity/` — Unity test framework

## Install Python Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:

| Package | Version | Purpose |
|---------|---------|---------|
| PyYAML | >= 6.0 | Hardware YAML parsing |
| Jinja2 | >= 3.1 | C code template rendering |
| Pydantic | >= 2.0 | Type-safe data models and validation |
| libcst | >= 1.0.0 | C source code parsing and merging |
| Click | >= 8.1.0 | CLI interface |

### Development Dependencies (Optional)

```bash
pip install -r requirements.txt
pip install pytest pytest-cov flake8 black
```

Or using pyproject.toml:

```bash
pip install -e ".[dev]"
```

## Verify Installation

```bash
hw2c gen -i examples/blinky_g0/hardware.yaml -o output/blinky_g0 --task examples/blinky_g0/task.yaml --bind examples/blinky_g0/bind.yaml
```

If successful, you should see output confirming the project generation, followed by:

```bash
cd output/blinky_g0
cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
```

## Toolchain Setup

### Arm GNU Toolchain

- Download from [Arm Developer](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain)
- Add to `PATH` — verify with `arm-none-eabi-gcc --version`

### OpenOCD (for flashing)

- Download from [OpenOCD](https://openocd.org/)
- Or use your IDE's built-in debug probe support (e.g., STM32CubeIDE, VS Code + Cortex-Debug)

## Building Documentation (MkDocs)

```bash
pip install mkdocs-material
mkdocs serve
```

Then open `http://localhost:8000` in your browser.
