# spi_flash_demo - SPI NOR Flash (W25Q32) 示例

演示 **SPI 外设 + NOR Flash 存储驱动** 在六层 YAML 架构下的完整用法：

- **SPI1**：PA5(SCK)/PA6(MISO)/PA7(MOSI)，CS=PC4（软件控制 GPIO）
- **W25Q32**：读 ID / 读数据 / 页写 / 扇区擦除 / 整片擦除
- **CLI**：USART2（PA2/PA3）115200
- **组件框架**：shell / led / btn（短按/双击/长按 → LED 模式）

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| SPI1 SCK/MISO/MOSI | PA5/PA6/PA7 | SPI 总线 |
| SPI CS | PC4 | 软件控制（低有效） |
| LED | PC0 | 低电平点亮 |
| BUTTON | PC13 | EXTI 双沿 → 手势检测 |
| USART2 | PA2/PA3 | CLI Shell + 日志（115200） |

MCU: STM32G0B1RET6 @ 16 MHz (HSI)

## 生成固件（六层完整配置）

```bash
python -m generator.generate -i examples/spi_flash_demo/hardware.yaml -o output/spi_flash_demo --force \
  --task examples/spi_flash_demo/task.yaml \
  --components examples/spi_flash_demo/components.yaml \
  --bind examples/spi_flash_demo/bind.yaml \
  --params examples/spi_flash_demo/params.yaml \
  --pubsub examples/spi_flash_demo/pubsub.yaml
```

## 编译 / 测试 / 烧录

```bash
cd output/spi_flash_demo
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
cd test && python run_tests.py    # 7 个套件（含 test_spi_flash 4/4）

openocd -f interface/cmsis-dap.cfg -f target/stm32g0x.cfg \
  -c "program build/spi_flash_demo.elf verify reset exit"
```
