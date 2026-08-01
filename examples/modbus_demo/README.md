# modbus_demo - RS485 + Modbus RTU 从站示例

演示 **Modbus RTU 从站协议** 在六层 YAML 架构下的完整用法：

- **USB-TTL 直连**（默认）：USART1（PA9=TX / PA10=RX）@ 9600，无需 DE 方向控制；
  也支持 **RS485**（配置 `transport: rs485`，PA1 作 DE）
- **Modbus RTU 从站**：功能码 03/06/16，CRC16-Modbus，异常码响应，广播地址抑制
- **CLI**：USART2（PA2/PA3）115200，`modbus` 命令显示从站状态
- **组件框架**：shell / led / btn / **modbus_slave**（短按/双击/长按 → LED 模式）
- **RTC**：LSE 1 秒心跳 + 30 秒定时事件

## Modbus 组件化架构

Modbus RTU 从站以 **框架组件** 形式接入（`components.yaml` 注册 `modbus_slave`），
由 `component_registry` 统一调度，软硬件分层清晰：

```
component_step_task (10ms)
  └─ modbus_slave.step()  →  modbus_process()   （从环形缓冲读帧）
  └─ modbus_slave.init()  →  uart_open("usart1")      （POSIX UART API）
                          →  USART1 RXNE 中断 → 环形缓冲（不丢字节）
                          →  modbus_init(1, tx/rx/read/write 回调)

数据映射：
  pub/sub topic "temperature"  ──订阅──►  保持寄存器 addr=1 (temperature_x10)
  主站 FC03 读寄存器            ◄──read_cb──  g_modbus_regs[]
  主站 FC06/FC16 写寄存器       ──write_cb──►  g_modbus_regs[]
```

`transport: uart` 时组件直接走 `uart_api`（USB-TTL 直连，无 DE 引脚依赖）；
`transport: rs485` 时经 `drv_rs485` 半双工控制 DE。两种模式均通过函数指针
回调与协议层（`drv_modbus`）解耦。

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
当 `pubsub.yaml` 定义 `temperature` 主题时，组件自动订阅并把读数镜像到
名称含 `temperature` 的寄存器（本例为 addr=1）。

## USB-TTL 直连测试（modbus_tool）

接线（CP210x 等 USB-TTL，非 RS485）：

```
USB-TTL TX  ──►  PA10 (USART1_RX)
USB-TTL RX  ◄──  PA9  (USART1_TX)
USB-TTL GND ──   板子 GND
```

```powershell
# 读保持寄存器（reg0=status, reg1=temperature_x10）
python modbus_tool.py --port COM4 read 0 2

# 写单个寄存器（FC06）
python modbus_tool.py --port COM4 write 0 42

# 写多个寄存器（FC16）
python modbus_tool.py --port COM4 write_multi 0 7 250

# 轮询温度寄存器（每秒）
python modbus_tool.py --port COM4 monitor 1 1 1.0
```
