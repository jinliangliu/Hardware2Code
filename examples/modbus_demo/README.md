# modbus_demo - RS485 + Modbus RTU 从站示例

演示 **RS485 半双工 + Modbus RTU 从站协议** 在六层 YAML 架构下的完整用法：

- **RS485**：USART1（PA9/PA10）+ DE 方向控制（PA1），半双工收发
- **Modbus RTU 从站**：功能码 03/06/16，CRC16-Modbus，异常码响应，广播地址抑制
- **CLI**：USART2（PA2/PA3）115200，`modbus` 命令显示从站状态
- **组件框架**：shell / led / btn（短按/双击/长按 → LED 模式）
- **RTC**：LSE 1 秒心跳 + 30 秒定时事件

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| LED | PC0 | 低电平点亮 |
| BUTTON | PC13 | EXTI 双沿 → 手势检测 |
| USART2 | PA2/PA3 | CLI Shell + 日志（115200） |
| RS485 TX/RX | PA9/PA10 | USART1 半双工 |
| RS485 DE | PA1 | 方向控制（高=发送） |

MCU: STM32G0B1RET6 @ 16 MHz (HSI)

## 生成固件（六层完整配置）

```bash
python -m generator.generate -i examples/modbus_demo/hardware.yaml -o output/modbus_demo --force \
  --task examples/modbus_demo/task.yaml \
  --components examples/modbus_demo/components.yaml \
  --bind examples/modbus_demo/bind.yaml \
  --params examples/modbus_demo/params.yaml \
  --pubsub examples/modbus_demo/pubsub.yaml
```

## 编译 / 测试 / 烧录

```bash
cd output/modbus_demo
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
cd test && python run_tests.py    # 10 个套件（含 modbus/rs485）

# 烧录（CMSIS-DAP）
openocd -f interface/cmsis-dap.cfg -f target/stm32g0x.cfg \
  -c "program build/modbus_demo.elf verify reset exit"
```

## Modbus 从站寄存器

`hardware.yaml` 中 `modbus.extra.registers` 定义保持寄存器表：

```yaml
registers:
  - { addr: 0, name: "status", default: 0 }
  - { addr: 1, name: "temperature_x10", default: 300 }
```

外部主站可通过 RS485 总线读取（FC03）或写入（FC06/FC16）。
