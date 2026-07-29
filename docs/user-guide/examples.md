# 示例工程

## base — 最小系统

- **功能**：HSI 16MHz 最小系统，含 CLI 交互终端、RTC、内部温度传感器（VREFINT 补偿）、STOP1 低功耗 USART 唤醒。所有 GPIO/AF/IRQ 从 `hardware.yaml` pins 派生，无硬编码。
- **硬件连接**：USART2 → PA2(TX)/PA3(RX) (115200bps)；LED → PC0（低电平有效）；按键 → PC13。
- **生成命令**：`python -m generator.generate -i examples/base/hardware.yaml -o output/my_project`

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
    extra:
      temp_offset: 25.0         # 手动校准偏移 (°C)

sleep:
  mode: STOP1                   # SLEEP / STOP0 / STOP1
```

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

> 更多外设示例（I2C、SPI、PWM、状态机、FOTA 等）正在重构适配三层 YAML 架构，后续逐步恢复。
