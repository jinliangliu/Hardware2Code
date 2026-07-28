# Adding New MCU Support

This guide explains how to add support for a new microcontroller.

## Prerequisites

- A working knowledge of your target MCU's HAL/CMSIS libraries
- Pinout and peripheral mapping documentation
- Arm GCC toolchain for the target architecture

## Step 1: Create MCU Data File

Create `generator/data/mcu/<PART>.json`:

```json
{
    "part": "STM32F407VGTx",
    "core": "cortex-m4",
    "flash_kb": 1024,
    "sram_kb": 192,
    "max_freq_mhz": 168,
    "pins": [
        {
            "name": "PA0",
            "functions": [
                {"function": "GPIO_Input", "af": 0},
                {"function": "GPIO_Output", "af": 0},
                {"function": "ADC_IN0", "af": 0},
                {"function": "TIM2_CH1", "af": 1},
                {"function": "USART2_CTS", "af": 7}
            ]
        }
    ],
    "peripherals": {
        "USART1": {"bus": "APB2", "base_addr": "0x40011000"},
        "USART2": {"bus": "APB1", "base_addr": "0x40004400"},
        "SPI1": {"bus": "APB2", "base_addr": "0x40013000"}
    }
}
```

## Step 2: Implement MCU Backend

Create `generator/backends/<vendor>/backend.py`:

```python
from generator.backends.base import BackendBase

class F4Backend(BackendBase):
    """STM32F4 series backend."""

    @property
    def core(self) -> str:
        return "cortex-m4"

    def get_hal_include_path(self) -> str:
        return "static/stm32f4/HAL/Inc"

    def get_startup_file(self) -> str:
        return "static/stm32f4/CMSIS/startup_stm32f407xx.s"

    def get_linker_script(self, flash_kb: int) -> str:
        return f"generator/data/linker/STM32F407VG_FLASH.ld"

    # ... additional methods
```

## Step 3: Register the Backend

In `generator/registry.py`:

```python
BACKEND_REGISTRY = {
    "STM32G0B1RET6": "generator.backends.stm32.backend:STM32Backend",
    "STM32F407VGTx": "generator.backends.stmicro.f4:STM32F4Backend",
}
```

## Step 4: Update Validation

In `generator/schemas/hardware.py`, add new MCU part numbers to the allowed list.

## Step 5: Create Linker Script

Add the MCU-specific linker script in `templates/linker/`. Follow the Jinja2 template pattern used by existing scripts.

## Step 6: Add Unit Tests

Add tests in `generator/tests/` to verify:
- MCU data file is valid JSON
- Backend returns correct paths
- Pin function mapping is correct
