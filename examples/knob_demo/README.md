# knob_demo - TIM1 直驱 FOC 力矩反馈阻尼旋钮

演示 hw2c 的 **TIM1 直驱 FOC（磁场定向控制）** 与 **力觉旋钮**：

- **FOC 电流环**：TIM1 三相互补 PWM（8 kHz 中心对齐）+ ADC1 三路电流采样 +
  I2C 磁编码器（AS5600）电角度；Clarke → Park → PI → 逆 Park → SVPWM
- **力矩反馈阻尼**：目标力矩 = -阻尼×角速度 - 摩擦×方向，转动旋钮即有
  阻尼/摩擦手感（力觉）
- **模块化**：`foc_math`（纯 C 可测）→ `drv_foc_motor`（TIM1+ADC+编码器）
  → `foc_motor` 组件 → `knob` 应用组件

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| TIM1 三相 | PA8/PB13, PA9/PB14, PA10/PB15 | 互补 PWM（驱动级） |
| ADC1 电流 | PA0/PA1/PA4 | 三相电流采样 |
| 磁编码器 | I2C1 PB6/PB7 | AS5600 @ 0x36（12 位电角度） |
| LED / 按键 | PC0 / PC13 | 状态指示 / 手势 |
| USART2 | PA2/PA3 | CLI Shell + 日志（115200） |

MCU: STM32G0B1RET6 @ 16 MHz (HSI)

## 生成 / 编译 / 测试

```bash
python -m generator.generate -i examples/knob_demo/hardware.yaml -o output/knob_demo --force \
  --task examples/knob_demo/task.yaml --components examples/knob_demo/components.yaml \
  --bind examples/knob_demo/bind.yaml --params examples/knob_demo/params.yaml \
  --pubsub examples/knob_demo/pubsub.yaml
cd output/knob_demo
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake && cmake --build build
python test/run_tests.py        # 含 test_foc_math（Clarke/Park/SVPWM/PI）
```

## 设计要点

```
电流环（TIM1 更新中断, 10 kHz）
  ia/ib 采样 → Clarke → Park(θe)
  id 环(PI, ref=0)  iq 环(PI, ref=目标力矩/KT)
  → 逆 Park → SVPWM → TIM1 CCR1/2/3

knob 应用（10 ms）
  τ = -damping·ω - friction·sign(ω)
  转角超阈值 → KNOB_TURNED 事件
```

参数（CLI 运行时调）：`knob_damping` / `knob_friction` /
`knob_turn_threshold_deg`；电机参数（极对数/KT/母线电压/电流上限）在
`hardware.yaml` 的 `motor.extra`。
