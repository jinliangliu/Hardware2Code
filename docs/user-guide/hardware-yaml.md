# hardware.yaml Reference

## Overview

`hardware.yaml` describes the **physical hardware capabilities** of the target board.
It is the output of netlist/BOM parsing and contains only hardware facts:
MCU model, pin assignments, peripherals, clock tree, and power configuration.

Software concerns (tasks, state machines, variables) are in [`task.yaml`](task-yaml.md).
The wiring between hardware and software is in [`bind.yaml`](bind-yaml.md).

---

## Schema Reference

### Top-Level Keys

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `mcu` | object | Yes | - | MCU configuration |
| `mcu.part` | string | Yes | - | MCU part number (e.g. `STM32G0B1RET6`) |
| `mcu.core` | string | No | `Cortex-M0+` | CPU core model (e.g. `Cortex-M0+`, `Cortex-M4`) |
| `mcu.core_clock_mhz` | int | No | 64 | Core clock frequency in MHz |
| `mcu.ram_kb` | int | No | 144 | On-chip SRAM in KB |
| `mcu.flash_kb` | int | No | 512 | On-chip Flash in KB |
| `mcu.dual_bank` | bool | No | true | Flash is dual-bank |
| `mcu.hse_freq` | int | No | 8000000 | HSE crystal frequency in Hz |
| `pins` | list | No | `[]` | Pin configuration list |
| `pins[].id` | string | Yes | - | Pin identifier (`PA0` – `PF15`) |
| `pins[].function` | string | Yes | - | Pin function (see [Pin Functions](#12-pin-configuration)) |
| `pins[].label` | string | No | `""` | Human-readable label |
| `pins[].active_level` | string | No | `high` | Active level: `high` / `low` |
| `pins[].pull` | string | No | `none` | Pull resistor: `up` / `down` |
| `pins[].af` | int | No | `0` | Alternate function number |
| `pins[].exti` | object | No | `{}` | EXTI interrupt configuration |
| `pins[].exti.enable` | bool | No | `false` | Enable EXTI interrupt |
| `pins[].exti.trigger` | string | No | `-` | Edge trigger: `rising` / `falling` / `both` |
| `peripherals` | list | No | `[]` | Peripheral configurations |
| `peripherals[].name` | string | Yes | - | Peripheral instance name |
| `peripherals[].type` | string | Yes | - | Peripheral type (see [Peripheral Types](#15-peripherals)) |
| `peripherals[].bus` | string | Varies | - | Bus instance (`I2C1`, `SPI1`, …) |
| `peripherals[].interface` | string | Varies | - | Interface type (`internal` for RTC, etc.) |
| `peripherals[].clock_source` | string | Varies | - | Clock source (for RTC: `LSE` / `LSI`) |
| `peripherals[].features` | list | Varies | `[]` | Feature flags (e.g. `[calendar]` for RTC) |
| `peripherals[].bearer` | string | Varies | - | Communication bearer name (protocols) |
| `peripherals[].broker` | string | Varies | - | MQTT broker URL |
| `peripherals[].extra` | object | Varies | `{}` | Type-specific extra parameters |
| `sleep` | object | No | `{}` | Low-power configuration |
| `sleep.mode` | string | No | `STOP0` | Sleep mode: `STOP0` / `STOP1` / `STOP2` / `STANDBY` / `SLEEP` |
| `clock` | object | No | `{}` | Clock tree configuration |
| `clock.hsi_hz` | int | No | `16000000` | HSI oscillator frequency |
| `clock.lsi_hz` | int | No | `32000` | LSI oscillator frequency |
| `clock.hse` | object | No | - | HSE configuration |
| `clock.hse.present` | bool | No | `false` | HSE crystal present |
| `clock.hse.frequency_hz` | int | No | `8000000` | HSE frequency in Hz |
| `clock.lse` | object | No | - | LSE configuration |
| `clock.lse.present` | bool | No | `false` | LSE crystal present |
| `clock.lse.frequency_hz` | int | No | `32768` | LSE frequency in Hz |
| `clock.pll` | object | No | - | PLL configuration |
| `clock.pll.source` | string | No | `HSI` | PLL source: `HSI` / `HSE` |
| `clock.pll.m` | int | No | `1` | PLL input divider |
| `clock.pll.n` | int | No | `8` | PLL multiplier |
| `clock.pll.r` | int | No | `2` | PLL output divider (SYSCLK) |
| `clock.sysclk` | object | No | - | System clock configuration |
| `clock.sysclk.source` | string | No | `PLL` | SYSCLK source: `HSI` / `HSE` / `PLL` |
| `clock.sysclk.frequency_hz` | int | No | `64000000` | SYSCLK frequency in Hz |
| `clock.apb` | object | No | - | APB bus prescaler |
| `clock.apb.prescaler` | int | No | `1` | APB prescaler value |
| `clock.freertos_tick` | object | No | - | FreeRTOS tick source |
| `clock.freertos_tick.source` | string | No | `SysTick` | Tick source |
| `clock.freertos_tick.frequency_hz` | int | No | `1000` | Tick frequency |
| `bootloader` | object | No | `{}` | Bootloader configuration |
| `bootloader.enabled` | bool | No | `false` | Enable dual-slot bootloader |
| `bootloader.size_kb` | int | No | `8` | Bootloader Flash size in KB (4–32) |
| `bootloader.app_a_offset` | int | No | `0x2000` | App Slot A start offset |
| `bootloader.app_b_offset` | int | No | `0x40000` | App Slot B start offset |
| `bootloader.wdg_timeout_ms` | int | No | `5000` | Watchdog timeout in ms |
| `bootloader.max_retries` | int | No | `3` | Max consecutive boot failures (1–10) |
| `hil` | object | No | `{}` | HIL test configuration |
| `hil.baudrate` | int | No | `115200` | HIL UART baudrate |
| `hil.uart` | string | No | `UART2` | HIL UART instance |
| `heap_size` | string | No | `0x200` | Heap size (hex literal) |
| `stack_size` | string | No | `0x400` | Stack size (hex literal) |

---

## 1. Hardware Configuration

### 1.1 MCU Configuration

```yaml
mcu:
  part: STM32G0B1RET6        # Required: MCU part number
  core: Cortex-M0+            # Optional: CPU core model (default: Cortex-M0+)
  core_clock_mhz: 64          # Optional: Core clock frequency (default: 64)
  ram_kb: 144                 # Optional: On-chip SRAM (default: 144)
  flash_kb: 512               # Optional: On-chip Flash (default: 512)
  dual_bank: true             # Optional: Flash dual-bank (default: true)
  hse_freq: 8000000           # Optional: HSE crystal frequency (default: 8000000)
```

**Valid MCU parts**: STM32G0B1RET6 (currently only STM32G0 series supported)

### 1.2 Pin Configuration

```yaml
pins:
  - id: PC0                    # Required: Pin identifier (format: P[A-F][0-9][0-9]?)
    function: GPIO_Output      # Required: Pin function
    label: "LED"               # Optional: Human-readable label
    active_level: low          # Optional: Active level for output pins (low/high, default: high)
    pull: up                   # Optional: Pull resistor for input pins (up/down)
    af: 0                      # Optional: Alternate function number (default: 0)
    exti:                      # Optional: EXTI interrupt configuration
      enable: true
      trigger: falling         # rising/falling/both
```

> **Note**: `notify_task` has been removed. Pin-to-task interrupt binding is now defined in [`bind.yaml`](bind-yaml.md).

**Valid functions** — all supported `pins[].function` values:

| Function | Description |
|----------|-------------|
| `GPIO_Output` | General-purpose output (push-pull) |
| `GPIO_Input` | General-purpose input (floating) |
| `I2C_SCL` | I2C clock line (any I2C bus) |
| `I2C_SDA` | I2C data line (any I2C bus) |
| `I2C1_SCL` | I2C1 clock line |
| `I2C1_SDA` | I2C1 data line |
| `I2C2_SCL` | I2C2 clock line |
| `I2C2_SDA` | I2C2 data line |
| `SPI_SCK` | SPI clock (any SPI bus) |
| `SPI_MISO` | SPI master-in slave-out (any SPI bus) |
| `SPI_MOSI` | SPI master-out slave-in (any SPI bus) |
| `SPI_NSS` | SPI chip select (any SPI bus) |
| `SPI1_SCK` | SPI1 clock |
| `SPI1_MISO` | SPI1 MISO |
| `SPI1_MOSI` | SPI1 MOSI |
| `SPI1_NSS` | SPI1 NSS |
| `SPI2_SCK` | SPI2 clock |
| `SPI2_MISO` | SPI2 MISO |
| `SPI2_MOSI` | SPI2 MOSI |
| `SPI2_NSS` | SPI2 NSS |
| `UART_TX` | UART transmit (any UART) |
| `UART_RX` | UART receive (any UART) |
| `USART_TX` | USART transmit (any USART) |
| `USART_RX` | USART receive (any USART) |
| `USART1_TX` | USART1 transmit |
| `USART1_RX` | USART1 receive |
| `USART2_TX` | USART2 transmit |
| `USART2_RX` | USART2 receive |
| `LPUART_TX` | Low-power UART transmit |
| `LPUART_RX` | Low-power UART receive |
| `RS485_DE` | RS485 direction-control (DE/RE) |
| `ADC_IN` | Analog-to-digital input (general) |
| `ADC_IN1` – `ADC_IN16` | ADC input channels 1–16 |
| `IR_OUT` | Infrared transmitter output |
| `IR_IN` | Infrared receiver input |
| `CELL_PWR` | Cellular modem power key |
| `CELL_RST` | Cellular modem reset |

### 1.3 Sleep Mode Configuration

```yaml
sleep:
  mode: STOP1                  # STOP0/STOP1/STOP2/STANDBY/SLEEP
```

### 1.4 Clock Tree Configuration

```yaml
clock:
  hsi_hz: 16000000            # HSI oscillator (default: 16000000)
  lsi_hz: 32000               # LSI oscillator (default: 32000)
  hse:
    present: true             # HSE crystal detected from BOM
    frequency_hz: 8000000     # HSE frequency in Hz
  lse:
    present: true             # LSE crystal detected from BOM
    frequency_hz: 32768       # LSE frequency (default: 32768)
  pll:
    source: HSE               # PLL clock source (HSE / HSI)
    m: 1                      # Input divider
    n: 8                      # Multiplier
    r: 2                      # Output divider (SYSCLK)
  sysclk:
    source: PLL               # System clock source (HSI / HSE / PLL)
    frequency_hz: 64000000    # SYSCLK frequency
  apb:
    prescaler: 1              # APB prescaler (1, 2, 4, 8, 16)
  freertos_tick:
    source: SysTick           # FreeRTOS tick timer source
    frequency_hz: 1000        # Tick rate (default: 1000)
```

### 1.5 Peripherals

```yaml
peripherals:
  - name: "rtc"                # Required: Peripheral name
    type: "Internal_RTC"       # Required: Peripheral type
    interface: "internal"      # Required: Interface type
    clock_source: "LSE"        # Optional: Clock source (for RTC)
    features:                  # Optional: Feature list
      - calendar
    bus: "I2C1"                # Required for I2C/SPI peripherals
    extra:                     # Optional: Extra configuration
      baudrate: 115200         # For UART
      update_interval_ms: 1000 # For sensors
```

**Supported peripheral types**:

| Type | Required Bus | `extra` Parameters | Description |
|------|-------------|--------------------|-------------|
| `Internal_RTC` | - | - | Internal real-time clock (LSE) |
| `Internal_PWM` | - | `timer`, `channel`, `freq`, `duty` | Internal PWM output |
| `Internal_ADC` | - | `channel`, `resolution` | Internal analog-to-digital converter |
| `Internal_CLI` | - | `uart` (carrier name) | UART-based debug command shell |
| `Internal_IR` | - | `carrier_freq` | Infrared NEC/SIR communication |
| `Internal_IWDG` | - | `wdg_timeout_ms` | Independent watchdog timer |
| `UART_Serial` | - | `baudrate` | UART serial communication |
| `I2C_Sensor_MPU6050` | I2C bus | `update_interval_ms` | MPU6050 accelerometer via I2C |
| `SPI_Flash_W25Q32` | SPI bus | `chip_select_pin` | W25Q32 SPI NOR Flash |
| `SPI_Flash_Generic` | SPI bus | `chip_select_pin`, `total_size` | Generic SPI NOR Flash |
| `I2C_EEPROM` | I2C bus | `i2c_addr`, `page_size`, `total_size` | I2C EEPROM storage |
| `RS485` | - | `uart`, `de_pin`, `baudrate` | RS485 half-duplex transceiver |
| `Cellular_4G` | - | `uart`, `apn`, `baudrate` | 4G Cat.1 cellular module |
| `Protocol_Modbus` | - | `bearer`, `role` (master/slave), `slave_id` | Modbus RTU protocol |
| `Protocol_MQTT` | - | `bearer`, `broker`, `client_id`, `topic` | MQTT 3.1.1 client |

### 1.6 Communication Peripherals

```yaml
peripherals:
  # RS485 example
  - name: "rs485_1"
    type: "RS485"
    uart: "uart2"          # Reference to UART_Serial peripheral name
    de_pin: "PA1"          # RS485 direction control pin (RE/DE)
    extra:
      baudrate: 9600

  # Cellular 4G Cat.1 example
  - name: "cellular"
    type: "Cellular_4G"
    uart: "uart2"
    power_pin: "PC4"       # Optional: power control
    reset_pin: "PC5"       # Optional: reset control
    extra:
      apn: "ctnet"         # APN for PDP activation

  # IR NEC example
  - name: "ir"
    type: "Internal_IR"
    mode: "nec"            # nec | sir (default: nec)
    tx_pin: "PB0"
    rx_pin: "PB1"

  # Modbus RTU slave example
  - name: "modbus"
    type: "Protocol_Modbus"
    bearer: "rs485_1"      # Reference to RS485 or UART peripheral
    role: "slave"
    slave_id: 1

  # MQTT client example
  - name: "mqtt"
    type: "Protocol_MQTT"
    bearer: "cellular"     # Reference to Cellular_4G peripheral
    broker: "iot.telecom.com"
    port: 1883
    client_id: "device001"
    extra:
      username: "optional_user"
      password: "optional_pass"
      keep_alive_s: 60

  # CLI debug shell example
  - name: "cli"
    type: "Internal_CLI"
    uart: "uart_debug"     # Reference to UART_Serial peripheral
    extra:
      prompt: "h2c> "      # Optional: shell prompt, default "> "
      stack_size: 512       # Optional: CLI task stack, default 512
      priority: 4           # Optional: CLI task priority, default 4
      max_cmd_len: 64       # Optional: max command length, default 64
```

### 1.7 Bootloader Configuration

```yaml
bootloader:
  enabled: true               # Required: Enable dual-slot bootloader
  size_kb: 8                  # Optional: Bootloader Flash size (default: 8)
  max_retries: 3              # Optional: Max consecutive boot failures before slot swap (default: 3)
  app_a_offset: 0x2000        # Optional: App Slot A start offset (default: 0x2000)
  app_b_offset: 0x40000       # Optional: App Slot B start offset (default: 0x40000)
  crc_method: crc32_hw        # Optional: CRC method (default: crc32_hw)
  boot_flag_src: tamp_bkp     # Optional: Boot flag storage (default: tamp_bkp)
  wdg_timeout_ms: 5000        # Optional: Watchdog timeout (default: 5000)
```

When enabled, the bootloader occupies the first `size_kb` KB of Flash and manages two App slots:

- **App Slot A**: `app_a_offset` → `app_b_offset` (Bank 1 remainder)
- **App Slot B**: `app_b_offset` → flash end (Bank 2)

The bootloader flow:
1. Read TAMP backup registers for boot state
2. If previous boot was OK → clear counter → CRC check → jump to App
3. If previous boot failed → increment counter → CRC check → jump to App
4. If counter exceeds `max_retries` → swap to other slot → soft reset
5. If CRC fails → swap slot → soft reset (indicates corrupted firmware)
6. If both slots fail → LED SOS pattern (recovery mode)

Supported CRC methods:
- `crc32_hw`: STM32G0 hardware CRC unit (fast, low code size)

---

## 2. Example: Complete hardware.yaml

```yaml
mcu:
  part: STM32G0B1RET6
  core: Cortex-M0+
  core_clock_mhz: 64
  ram_kb: 144
  flash_kb: 512
  dual_bank: true

pins:
  - id: PC0
    function: GPIO_Output
    label: "LED"
    active_level: low
  - id: PC13
    function: GPIO_Input
    label: "BUTTON"
    pull: up
    exti:
      enable: true
      trigger: falling

sleep:
  mode: STOP1

clock:
  hsi_hz: 16000000
  lsi_hz: 32000
  hse:
    present: true
    frequency_hz: 8000000
  lse:
    present: true
    frequency_hz: 32768
  pll:
    source: HSE
    m: 1
    n: 8
    r: 2
  sysclk:
    source: PLL
    frequency_hz: 64000000
  apb:
    prescaler: 1
  freertos_tick:
    source: SysTick
    frequency_hz: 1000

peripherals:
  - name: "rtc"
    type: "Internal_RTC"
    interface: "internal"
    clock_source: "LSE"
    features:
      - calendar
```

---

## 3. Validation Rules

The generator validates the following hardware constraints:

### Critical Errors (Cannot continue)
- Missing `mcu.part`
- YAML parsing errors

### Errors (Recommended to fix)
- Missing required fields (pin id, function)
- Invalid formats (pin ID regex `^P[A-F][0-9]{1,2}$`, MCU part number)
- Invalid pin functions (must be one of supported functions)
- Invalid EXTI trigger values (must be `rising`/`falling`/`both`)
- Invalid `sleep.mode` (valid: `STOP0`/`STOP1`/`STOP2`/`STANDBY`/`SLEEP`)
- Duplicate pin IDs
- Missing `bus` field for I2C and SPI peripherals
- Invalid clock source values (`HSI`/`HSE`/`PLL`)
- Clock frequencies inconsistent with selected dividers/multipliers

### Warnings (May cause unexpected behavior)
- No pins defined
- Invalid pull values (only `up`/`down` valid)
- Missing model files for peripheral types
- HSE/LSE declared present but no crystal detected from BOM
- APB prescaler results in APB clock exceeding max rated frequency
