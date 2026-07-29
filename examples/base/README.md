# base — hw2c 最小系统单元

所有 hw2c 工程的最小可运行固件骨架。

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| LED | PC0 | 低电平点亮，启动心跳闪烁 |
| BUTTON | PC13 | 上拉输入，下降沿 EXTI13 中断 |
| USART2 | PA2/PA3 | CLI Shell + 日志输出（ST-Link VCP），波特率自动适配：正常115200 / STOP模式57600 |
| RTC | — | LSE 32.768 kHz，1 秒周期唤醒 |
| 温度传感器 | — | 片内 ADC1_CH16，0.1°C 精度 |

MCU: STM32G0B1RET6 @ 64 MHz，低功耗 STOP1。

## 软件任务

| 任务 | 优先级 | 栈 | 功能 |
|------|:-----:|:-------:|------|
| shell_task | 1 | 1024 B | hw2c_cli 交互终端 + 日志输出 |
| button_task | 2 | 128 B | 响应 PC13 按键中断（可通过 CLI 的 log 查看） |
| sensor_task | 3 | 512 B | 状态机：IDLE ↔ ACTIVE，RTC_TICK 驱动，计数器累加 |
| events_process_task | 3 | 512 B | 事件队列集中分发（16 深，RTC_TICK 由此产生） |

## CLI Shell

基于 **hw2c_cli** 引擎，支持 VT100 光标移动、退格删除、8 条命令历史、Tab 自动补全。

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

CLI 的数据流：`UART RX ISR → LwRB → shell_task → hw2c_cli_input()`，命令解析和派发由 hw2c_cli 内核完成。

## 文件结构

```
base/
├── hardware.yaml   # MCU、引脚、外设（USART2, RTC, LED, BUTTON, 温度传感器）
├── task.yaml       # FreeRTOS 任务定义 + sensor_task 状态机
└── bind.yaml       # 外设 → 任务绑定（usart2→shell, rtc→events, PC13→button）
```

## 使用

```bash
# 生成固件
hw2c gen -i hardware.yaml --task task.yaml --bind bind.yaml -o build/base

# 编译
cd build/base
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build

# 烧录（ST-Link）
cmake --build build --target flash

# 烧录（DAP-Link / CMSIS-DAP）
cmake --build build --target flash-daplink

# 串口连接 USART2 @ 115200（STOP模式为57600）
```
