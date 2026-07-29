# base — hw2c Minimal System Unit

The smallest runnable firmware skeleton for all hw2c projects.

## Hardware

| Component | Pin | Description |
|-----------|-----|-------------|
| LED | PC0 | Active-low, startup heartbeat |
| BUTTON | PC13 | Pull-up input, falling-edge EXTI13 interrupt |
| USART2 | PA2/PA3 | CLI Shell + log output (ST-Link VCP). 115200 baud (57600 in STOP mode) |
| RTC | — | LSE 32.768 kHz, 1 s periodic wakeup |
| Temp Sensor | — | On-chip ADC1_CH16, 0.1 °C resolution |

MCU: STM32G0B1RET6 @ 64 MHz, low-power STOP1 mode.

## Software Tasks

| Task | Priority | Stack | Role |
|------|:--------:|:-----:|------|
| shell_task | 1 | 1024 B | hw2c_cli interactive terminal + log output |
| button_task | 2 | 128 B | PC13 button interrupt handler |
| sensor_task | 3 | 512 B | State machine: IDLE ↔ ACTIVE, driven by RTC_TICK |
| events_process_task | 3 | 512 B | Event queue dispatch (depth 16, produces RTC_TICK) |

## CLI Shell

Powered by the **hw2c_cli** engine. Supports VT100 cursor movement, backspace,
8-entry command history, and Tab auto-completion.

```
hw2c> help
help       Show available commands
version    Show firmware version
uptime     Show system uptime
free       Show free heap memory
tasks      List FreeRTOS tasks
reset      Software reset MCU
gpio       Read/write GPIO pins
led        Control LED (on/off/toggle)
rtc        RTC time operations
sysinfo    System info (temperature, RAM/Flash usage)

hw2c> sysinfo
Temperature : 34.2 C
Heap        : 4832 / 16384 bytes (used / total)
Flash       : 45632 / 524288 bytes (used / total)
```

Data flow: `UART RX ISR → LwRB → shell_task → hw2c_cli_input()`. Command parsing
and dispatch are handled by the hw2c_cli kernel.

## File Layout

```
base/
├── hardware.yaml   # MCU, pins, peripherals (USART2, RTC, LED, BUTTON, temp)
├── task.yaml       # FreeRTOS tasks + sensor_task state machine
└── bind.yaml       # Peripheral-to-task bindings
```

## Usage

```bash
# Generate firmware
hw2c gen -i hardware.yaml --task task.yaml --bind bind.yaml -o build/base

# Build
cd build/base
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build

# Flash (ST-Link)
cmake --build build --target flash

# Flash (DAP-Link / CMSIS-DAP)
cmake --build build --target flash-daplink

# Connect serial console — USART2 @ 115200 (57600 in STOP mode)
```
