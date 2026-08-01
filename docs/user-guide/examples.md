# 示例工程

## base — 最小系统

- **功能**：HSI 16MHz 最小系统，含 CLI 交互终端、RTC（每秒 WAKEUP 内核 + 10 路定时器）、内部温度传感器（VREFINT 补偿）、STOP1 低功耗 USART 唤醒。所有 GPIO/AF/IRQ 从 `hardware.yaml` pins 派生，无硬编码。
- **硬件连接**：USART2 → PA2(TX)/PA3(RX) (115200bps)；LED → PC0（低电平有效）；按键 → PC13。
- **生成命令**（六层完整配置）：

```bash
python -m generator.generate -i examples/base/hardware.yaml -o output/my_project \
  --task examples/base/task.yaml \
  --components examples/base/components.yaml \
  --bind examples/base/bind.yaml \
  --params examples/base/params.yaml \
  --pubsub examples/base/pubsub.yaml
```

### hardware.yaml 关键配置

```yaml
mcu:
  part: STM32G0B1RET6
  clock_source: HSI             # HSI 或 HSE
  clock_freq_hz: 16000000       # 振荡器频率 (Hz)
  core_clock_mhz: 16            # SYSCLK = clock_freq / 1e6

peripherals:
  - name: usart2
    type: UART_Serial
    extra:
      baudrate: 115200          # CLI 串口波特率

  - name: temp_sensor
    type: Internal_TempSensor

sleep:
  mode: STOP1                   # SLEEP / STOP0 / STOP1
```

### RTC 定时器（10 路）

RTC 以 LSE 32.768 kHz 为时钟源，WakeUp 定时器每秒唤醒内核一次，作为 1 Hz 心跳驱动全部定时器；RTC 中断为最高优先级（NVIC 0），确保可从 STOP 模式唤醒内核。定时器类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| `periodic_sec` | 秒级周期闹钟 | 1s / 15s / 30s / 2min / 5min |
| `periodic_minute` | 分钟边界（每分 :00，内建） | `MINUTE_TICK` |
| `periodic_hour` | 小时边界（每小时 :00:00，内建） | `HOUR_TICK` |
| `one_shot` | 单次（秒级） | 5s 后触发一次 |
| `one_shot_ms` | 毫秒单次（RTC SSR + Alarm B） | 500ms / 2s 后触发一次 |

`hardware.yaml` 中 alarms 配置示例：

```yaml
alarms:
  - type: periodic_sec
    period_s: 1               # 每秒心跳
    event: TICK_1S
  - type: one_shot_ms
    delay_ms: 500             # 500ms 单次（毫秒级）
    event: ONE_SHOT_500MS
```

`rtc set <HH:MM:SS>` 会通过 `RTC_SetTime()` 统一重排所有定时器（含毫秒定时器），时钟调整后闹钟仍按新时刻触发。

### CLI 命令列表

| 命令 | 功能 |
|------|------|
| `help` | 显示可用命令 |
| `version` | 显示固件版本 |
| `uptime` | 显示系统运行时间 |
| `free` | 显示空闲堆内存 |
| `tasks` | 列出 FreeRTOS 任务 |
| `sysinfo` | 系统信息（温度/堆/Flash） |
| `reset` | 软件复位 MCU |
| `gpio` | 读写 GPIO 引脚 |
| `led on/off/toggle` | LED 控制 |
| `rtc` | RTC 时间操作 |
| `param get/set` | 运行时参数读写 |

> 更多外设示例正在重构适配六层 YAML 架构，后续逐步恢复。当前示例工程为 `examples/base`。

## modbus_demo — RS485 + Modbus RTU 从站

- **功能**：RS485 半双工（USART1 + DE 方向控制）+ Modbus RTU 从站协议（FC03/06/16、CRC16、异常码），
  CLI 交互终端 + LED/按键组件 + RTC 定时事件。
- **硬件连接**：RS485 → PA9(TX)/PA10(RX)/PA1(DE)；CLI → USART2 PA2/PA3 (115200)。
- **测试**：10 个单元测试套件全过（含 `test_modbus` 12/12、`test_rs485` 5/5）。
- **位置**：`examples/modbus_demo/`

## spi_flash_demo — SPI NOR Flash

- **功能**：SPI1（PA5/PA6/PA7 + PC4 CS）驱动 W25Q32 NOR Flash，
  读 ID / 读写 / 扇区擦除，CLI + LED/按键组件。
- **测试**：7 个单元测试套件全过（含 `test_spi_flash` 4/4）。
- **位置**：`examples/spi_flash_demo/`
