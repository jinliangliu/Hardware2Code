# pwm_demo - 多路 Timer PWM（逐路占空比可调）

演示 hw2c 的 **多通道 PWM 驱动**：

- **一个定时器多路输出**：TIM2 同时驱动 CH1（PA0）与 CH2（PA1），
  每路占空比独立可调（0..100%）
- **频率可调**：`pwm freq <hz>`（100 Hz..100 kHz），改频时各通道
  占空比百分比自动保持
- **CLI**：`pwm list` / `pwm set <ch> <0-100>` / `pwm freq <hz>`

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| TIM2 CH1 | PA0 | PWM 输出，默认 50% @ 1 kHz |
| TIM2 CH2 | PA1 | PWM 输出，默认 25% @ 1 kHz |
| LED | PC0 | 低电平点亮 |
| BUTTON | PC13 | EXTI 双沿 → 手势检测 |
| USART2 | PA2/PA3 | CLI Shell + 日志（115200） |

MCU: STM32G0B1RET6 @ 16 MHz (HSI)

## 生成固件（六层完整配置）

```bash
python -m generator.generate -i examples/pwm_demo/hardware.yaml -o output/pwm_demo --force \
  --task examples/pwm_demo/task.yaml \
  --components examples/pwm_demo/components.yaml \
  --bind examples/pwm_demo/bind.yaml \
  --params examples/pwm_demo/params.yaml \
  --pubsub examples/pwm_demo/pubsub.yaml
```

## 编译 / 测试 / 烧录

```bash
cd output/pwm_demo
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
python test/run_tests.py
cmake --build build --target flash-daplink
```

## CLI 用法

```text
hw2c> pwm list
CH1: 50%
CH2: 25%

hw2c> pwm set 1 80
CH1 duty -> 80%

hw2c> pwm freq 500
PWM frequency -> 500 Hz (duty preserved)
```

## 设计要点

```
TIM2（16 MHz → 1 MHz 计数）
  ├─ CH1 (PA0)  占空比 0..100% 独立可调
  └─ CH2 (PA1)  占空比 0..100% 独立可调

ARR = 1e6 / freq - 1
pulse(ch) = (ARR + 1) * duty(ch) / 100
```

驱动 `drv_pwm` 按 `hardware.yaml` 的 `channels` 列表生成通道表，
`pwm set <ch> <pct>` 只更新目标通道的 CCR，互不影响；`pwm freq`
重算 ARR 后按已保存的百分比重写所有 CCR。
