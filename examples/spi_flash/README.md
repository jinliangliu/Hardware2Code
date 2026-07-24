# spi_flash — SPI Flash W25Q32

演示 `SPI_Flash_W25Q32` 外设驱动生成。

## 硬件

- **PA5**: SPI1 SCK（AF0）
- **PA6**: SPI1 MISO（AF0）
- **PA7**: SPI1 MOSI（AF0）
- **PC4**: SPI1 片选（GPIO 输出，软件控制）
- **PC0**: LED（低电平点亮）

## 行为

- SPI1 外设自动配置驱动 W25Q32 Flash
- Flash 测试任务自动生成

## 测试特性

| 特性 | 说明 |
|------|------|
| `SPI_Flash_W25Q32` | SPI Flash HAL 驱动自动生成 |
| `bus` 字段 | 指定 SPI 总线（SPI1） |
| `cs_pin` | 软件片选引脚配置 |
| 外设模型 | 通过 `models/SPI_Flash_W25Q32.yaml` 管理 HAL 依赖 |

## 生成

```bash
python generator/generate.py -i examples/spi_flash/hardware.yaml -o output/spi_flash
```
