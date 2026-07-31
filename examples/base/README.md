# base — hw2c 最小系统单元

所有 hw2c 工程的最小可运行固件骨架，展示完整六层 YAML 架构和组件框架。

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| LED | PC0 | 低电平点亮，启动心跳 + 按键响应模式驱动 |
| BUTTON | PC13 | 上拉输入，EXTI 双边沿中断 → 手势检测（短按/双击/长按） |
| USART2 | PA2/PA3 | CLI Shell + 日志输出（CP210x USB-UART），115200 baud |
| RTC | — | LSE 32.768 kHz，1 秒周期唤醒 + 30 秒/5 分钟定时事件 |
| 温度传感器 | — | 片内 ADC1_CH16，ADC 自校准 + VREFINT 实时 VDDA 补偿，0.1°C 精度 |

MCU: STM32G0B1RET6 @ 16 MHz (HSI)，无 PLL。

## YAML 配置层（六层解耦）

```
examples/base/
├── hardware.yaml    # 硬件物理事实 — MCU / 引脚 / 外设 / 时钟 / 休眠
├── task.yaml        # 任务与行为 — FreeRTOS 任务 / 层级状态机 / 定时事件
├── components.yaml  # 组件注册 — shell / led / btn 组件实例（周期/配置/休眠兼容）
├── bind.yaml        # 硬-软件绑定 — EXTI中断 → 组件路由
├── params.yaml      # 运行时参数 — 组件参数 (default/min/max)，CLI 动态调参
└── pubsub.yaml      # 发布/订阅 — 跨组件解耦事件通信主题
```

## 软件任务

| 任务 | 优先级 | 栈 | 功能 |
|------|:-----:|:-------:|------|
| event_mgr | configMAX-1 | 512 B | 事件队列集中分发（100 深） |
| cli | 4 | 512 B | CLI 交互终端 + 日志输出 |
| shell_task | 1 | 1024 B | hw2c_cli 任务（Shell 组件） |
| comp_step | 2 | 512 B | 组件调度器 — 每 10ms 执行所有组件的 step() |

## 组件框架

生成固件内置三个应用层组件，由 `component_registry` 统一管理生命周期：

```
component_init_all() → 3/3 OK
├── shell (shell_cli)    CLI 交互，周期 50ms，STOP1 兼容
├── led  (led)           LED 模式驱动，周期 50ms
│                          off / fast_blink / slow_blink / fault
└── btn  (btn)           按键手势检测，周期 10ms
                           SHORT_PRESS / DOUBLE_PRESS / LONG_PRESS
```

组件间通过 `component_bus`（4 个主题）和 `param_registry`（7 个参数）解耦通信。

## 状态机行为

`task.yaml` 定义的按钮手势 → LED 模式映射：

```
IDLE
  ├── BUTTON_SHORT_PRESS  → fast_blink  + log + 读取温度
  ├── BUTTON_DOUBLE_PRESS → slow_blink  + log + 读取温度
  └── BUTTON_LONG_PRESS   → fault       + log + 读取温度
```

按键手势检测流程：`PC13 EXTI → event_queue → btn_component 手势检测 → statemachine 动作分发 → led_component 模式驱动`。

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
led        Control LED (on/off/toggle/pattern)
rtc        RTC time operations
param      Get/set runtime parameters
sysinfo    System info (temperature, RAM/Flash usage)

hw2c> sysinfo
Temperature : 36.0 C
Heap        : 13992 / 15360 bytes (used / total)
Flash       : 52152 / 524288 bytes (used / total)
```

## 使用

```bash
# 生成固件（六层完整配置）
python -m generator.generate -i hardware.yaml -o build/base --force \
  --task task.yaml \
  --components components.yaml \
  --bind bind.yaml \
  --params params.yaml \
  --pubsub pubsub.yaml

# 编译
cd build/base
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build

# 烧录（CMSIS-DAP）
openocd -f interface/cmsis-dap.cfg -f target/stm32g0x.cfg \
  -c "program build/base.elf verify reset exit"

# 串口连接 USART2 @ 115200（CP210x USB-UART）
```
