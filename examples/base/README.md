# base — hw2c 最小系统单元

所有 hw2c 工程的最小可运行固件骨架，展示完整六层 YAML 架构、组件框架、RTC
定时器系统与低功耗（SLEEP / STOP0 / STOP1）能力。全部代码由生成器产出，
无手写业务代码。

## 1. 硬件配置

| 组件 | 引脚 | 功能 |
|------|------|------|
| LED | PC0 | 低电平点亮，组件模式驱动（OFF / 快闪 / 慢闪 / fault / 常亮） |
| BUTTON | PC13 | 上拉输入，EXTI 双沿中断 → 手势检测（短按 / 双击 / 长按） |
| USART2 | PA2/PA3 | CLI Shell + 日志输出（USB-TTL），115200 8N1 |
| RTC | — | LSE 32.768 kHz，1 Hz 唤醒心跳 + 10 路定时器 |
| 温度传感器 | — | 片内 ADC VIN12 + VREFINT(VIN13) 补偿，0.1°C 分辨率 |

MCU：STM32G0B1RET6 @ 16 MHz（HSI，无 PLL），Cortex-M0+，512 KB Flash / 144 KB RAM。
调试：CMSIS-DAP（SWD）+ OpenOCD。

## 2. 架构层面

### 2.1 六层 YAML 配置（模型驱动）

```
examples/base/
├── hardware.yaml    # 硬件物理事实 — MCU / 引脚 / 外设 / 时钟 / 休眠
├── task.yaml        # 任务与行为 — 事件任务 / 状态机 / 定时事件
├── components.yaml  # 组件注册 — shell / led / btn（周期 / 配置 / sleep_compat）
├── bind.yaml        # 软硬件绑定 — 外设→任务、EXTI 中断→组件
├── params.yaml      # 运行时参数 — 组件参数（default/min/max），CLI 动态调参
└── pubsub.yaml      # 发布/订阅 — 跨组件解耦事件通信主题
```

生成命令（从仓库根执行）：

```bash
python -m generator.generate -i examples/base/hardware.yaml -o output/base \
  --task examples/base/task.yaml \
  --components examples/base/components.yaml \
  --bind examples/base/bind.yaml \
  --params examples/base/params.yaml \
  --pubsub examples/base/pubsub.yaml
```

### 2.2 运行时架构（分层）

```
┌─ 应用层 ────────────────────────────────────────────────┐
│  CLI 命令         状态机行为        定时事件动作          │
├─ 组件层 ────────────────────────────────────────────────┤
│  component_registry / component_bus / param_registry    │
│  shell · led · btn（init/step/terminate 生命周期）        │
├─ 事件层 ────────────────────────────────────────────────┤
│  event_queue（100 深）← EXTI / RTC 定时器 / 组件          │
│  EventMgr_Task（最高优先级）→ statemachine_process        │
├─ 任务层 ────────────────────────────────────────────────┤
│  event_mgr / cli / comp_step（FreeRTOS 8 级优先级）       │
├─ 驱动层 ────────────────────────────────────────────────┤
│  drv_rtc · drv_log · drv_shell(CLI) · drv_temp_sensor    │
│  gpio · uart_api · LwRB 环形缓冲 · hw2c_cli 引擎          │
└─ 硬件层 ────────────────────────────────────────────────┘
   STM32G0B1RET6 · HAL + CMSIS · USART2/EXTI/RTC(LSE)/ADC
```

### 2.3 关键数据流

- **按键**：`PC13 EXTI 中断 → btn_queue → btn_component 手势检测 → event_queue
  → statemachine 动作 → led_component 模式驱动`
- **串口输入**：`USART2 RXNE 中断 → LwRB 环形缓冲 → 信号量 → cli_task →
  hw2c_cli_input() 行编辑/解析 → cmd_xxx(argc, argv)`
- **串口输出**：`log/CLI → 共享 LwRB 环形缓冲 → TXE 中断逐字节 → USART2 TDR`
  （单写者设计，日志与 CLI 回显不抢 TDR）
- **RTC 定时**：`LSE 1 Hz 唤醒中断 → rtc_uptime_sec++ → rtc_fire_expired →
  event_queue → EventMgr 分发`

## 3. 软件任务

| 任务 | 优先级 | 栈 | 功能 |
|------|:-----:|:-------:|------|
| event_mgr | configMAX-1(7) | 512 B | 事件队列集中分发（100 深） |
| cli | 4 | 512 B | CLI 交互（RX 中断 → 引擎 → 命令分发） |
| comp_step | 2 | 512 B | 组件调度器 — 每 10ms 执行所有组件 step() |
| IDLE / Tmr Svc | — | — | FreeRTOS 内建 |

堆：`configTOTAL_HEAP_SIZE = 11264 B`，由生成器按任务栈自动估算（KiB 对齐）。

## 4. 组件框架

`component_init_all() → 3/3 OK`，由 `component_registry` 统一管理生命周期：

```
├── shell (shell_cli)  CLI 交互，周期 50ms，sleep_compat: STOP1
├── led   (led)        LED 模式驱动，周期 50ms，sleep_compat: STOP1
│                      off / fast_blink / slow_blink / fault / on
└── btn   (btn)        按键手势检测，周期 10ms，sleep_compat: STOP1
                       SHORT_PRESS / DOUBLE_PRESS / LONG_PRESS
```

组件间通过 `component_bus`（4 个主题）与 `param_registry`（7 个参数）解耦通信。

## 5. 状态机行为

`task.yaml` 定义的按键手势 → LED 模式映射：

```
IDLE
  ├─ BUTTON_SHORT_PRESS  → fast_blink + log + 读取温度
  ├─ BUTTON_DOUBLE_PRESS → slow_blink + log + 读取温度
  └─ BUTTON_LONG_PRESS   → fault      + log + 读取温度
```

## 6. RTC 定时器系统

- **时钟**：LSE 32.768 kHz，预分频 A=0 / S=32767 → SSR 以 **1 kHz** 计数（1 ms 分辨率）。
- **1 Hz 唤醒心跳**：WakeUp 定时器（`WUCKSEL=100`，CK_SPRE 16-bit）每秒唤醒内核，
  驱动 `rtc_uptime_sec` 与全部定时器；RTC 中断为 **NVIC 最高优先级 0**（可从 STOP 唤醒）。
- **10 路定时器**：

| 类型 | 说明 | base 示例 |
|------|------|----------|
| periodic_sec | 秒级周期闹钟 | 15s / 30s / 2min / 5min |
| periodic_minute | 分钟边界（每分 :00，内建） | MINUTE_TICK |
| periodic_hour | 小时边界（每小时 :00:00，内建） | HOUR_TICK |
| one_shot | 单次（秒级） | 5s 后触发一次 |
| one_shot_ms | 毫秒单次（SSR + Alarm B） | 500ms / 2s，实测误差 ~4ms |

- **校时**：CLI `rtc set HH:MM:SS` 走 `RTC_SetTime()`，重建排序链表并重算毫秒定时器，
  改时后闹钟按新时刻触发（已用 `rtc set 22:59:50 → 23:00:00` 验证小时闹钟）。

## 7. 低功耗（RUN / SLEEP / STOP0 / STOP1）

- **Tickless idle**：`configUSE_TICKLESS_IDLE=2`，`sleep.c` 提供
  `vPortSuppressTicksAndSleep()`，按 `power_mgr` 允许深度自动进低功耗。
- **三种模式**：SLEEP（CPU 停，外设全跑）/ STOP0（主稳压器）/ STOP1（低功耗稳压器，默认）。
- **唤醒源**：
  - RTC 1 Hz（LSE 独立供电，始终有效）
  - USART2 起始位唤醒（UESM + HSI16 保持），实测 ~110 ms 唤醒并完成 Shell 交互
  - EXTI 按键（PC13）
- **保持性**：RTC（日历 + SSR）与 RAM 全部保持；唤醒后系统时间零偏差
  （休眠时长由 RTC 实测，补偿 HAL tick；tickless 路径同时补偿 FreeRTOS tick）。
- **调试命令**：`power info` / `power mode <SLEEP|STOP0|STOP1>` / `power sleep`。

> 注意：base 组件步进任务为 10ms 轮询，空闲窗口通常 < 1s，而 RTC 唤醒粒度为 1s，
> 因此自动 tickless 默认不频繁触发；显式 `power sleep` 用于逐模式验证。

## 8. CLI Shell

基于 **hw2c_cli** 引擎（VT100 光标移动、退格删除、8 条历史、Tab 补全），
接收走 RXNE 中断 → LwRB → cli_task，输出与日志共享 TXE 中断环形缓冲。

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
sysinfo    System info (temp/RAM/flash)
power      Power modes (sleep/stop)

hw2c> sysinfo
Temperature : 36.0 C
Heap        : 7236 / 11264 bytes (used / total)
Flash       : 59656 / 524288 bytes (used / total)
```

常用组合：`led on/off/toggle`（组件 pattern 驱动，状态保持）、`rtc time` / `rtc set`、
`power mode STOP1` + `power sleep`（进低功耗，串口发任意字符立即唤醒）。

## 9. 日志系统

- LwRB 环形缓冲（1024 B）+ USART2 TXE 中断逐字节发送。
- 时间戳来自 RTC（1 kHz SSR，毫秒级），`[YYYY-MM-DD HH:MM:SS.mmm] [LEVEL]`。
- CLI 回显与日志共用同一环形缓冲（单写者），无字节竞争。
- 每秒心跳不打印日志（事件照发，仅静默丢弃），避免刷屏。

## 10. 使用

```bash
# 生成（见 2.1）→ 编译
cd output/base
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build

# 烧录（CMSIS-DAP）
openocd -f interface/cmsis-dap.cfg -f target/stm32g0x.cfg \
  -c "program output/base/build/base.bin 0x08000000 verify reset exit"

# 串口连接 USART2 @ 115200（USB-TTL → PA2/PA3），回车激活 CLI
```

## 11. 单元测试

生成工程自带主机侧测试（mock HAL + Unity），编译运行：

```bash
cd output/base/test
python run_tests.py
```

9 套件 46 用例：btn / cli / event_mgr / gpio / led / rtc / rtc_timers /
statemachine / uart，全部通过。
