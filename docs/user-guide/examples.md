# 示例工程索引

| 工程名 | 功能 | 主要外设 |
|--------|------|----------|
| `blinky_g0` | 按键控制 LED 翻转 | GPIO 输入/输出 |
| `mpu6050` | 加速度传感器报警 | I2C (MPU6050), GPIO |
| `spi_flash` | SPI Flash 读写 | SPI (W25Q32), GPIO |
| `pwm` | PWM 输出控制 | 内部定时器 PWM, GPIO |
| `rtc_advanced` | RTC 日历、低功耗、状态机全特性 | 内部 RTC, GPIO |
| `substate_demo` | 复合子状态演示 | GPIO, RTC |
| `parallel_states` | 并行区域演示 | GPIO, RTC |
| `parallel_comm` | 并行区域跨区域通信 | GPIO, RTC |
| `nested_ref` | ref 引用 + namespace 命名空间 | GPIO, RTC |
| `ref_demo` | ref 基础用法演示 | GPIO, RTC |
| `timeline_demo` | timeline 时间序列动作 | GPIO |
| `bootloader_demo` | 双槽位 Bootloader | Bootloader, GPIO |
| `cli_demo` | CLI 调试终端 | USART2, CLI, GPIO |
| `modbus_demo` | Modbus RTU 从机通信 | RS485, Modbus RTU, GPIO |
| `cellular_mqtt` | 4G Cat.1 + MQTT 上云 | Cellular_4G, MQTT, GPIO |
| `cellular_test` | 4G Cat.1 基础测试 | Cellular_4G, MQTT, GPIO |
| `fota_demo` | BSDIFF 差分升级 | Bootloader, CLI, RTC, GPIO |
| `fota_flow` | FOTA 完整状态机流程 | Bootloader, RTC, GPIO |
| `i2c_spi_demo` | I2C EEPROM + SPI 综合 | I2C, SPI, GPIO |
| `low_power_demo` | STOP0 低功耗管理 | RTC, GPIO (EXTI 唤醒) |

**通用硬件连接：**
- LED：PC0 或 PA0/PA5（低电平有效）
- 按键：PC13（上拉，下降沿触发）

各工程的详细 YAML 文件位于 `examples/<工程名>/` 目录。
生成命令均为：

```
hw2c gen -i examples/<工程名>/hardware.yaml -o output/<工程名>
```

对于支持三层格式的工程（`blinky_g0`、`rtc_advanced`），还需指定 `--task` 和 `--bind`：

```
hw2c gen -i examples/<工程名>/hardware.yaml -o output/<工程名> --task examples/<工程名>/task.yaml --bind examples/<工程名>/bind.yaml
```

---

## 基础外设类

### 1. blinky_g0
- **功能**：LED 翻转，按键中断。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/blinky_g0/hardware.yaml -o output/blinky_g0 --task examples/blinky_g0/task.yaml --bind examples/blinky_g0/bind.yaml`

### 2. mpu6050
- **功能**：读取加速度，检测倾斜报警，通过事件管理器控制 LED。
- **硬件连接**：I2C1 → PB6(SCL)/PB7(SDA)；LED → PC0；按键 → PC13。
- **生成命令**：`hw2c gen -i examples/mpu6050/hardware.yaml -o output/mpu6050`

### 3. spi_flash
- **功能**：SPI Flash ID 读取、扇区擦除、数据写入。
- **硬件连接**：SPI1 → PA5(SCK)/PA6(MISO)/PA7(MOSI)/PC4(NSS)；LED → PC0。
- **生成命令**：`hw2c gen -i examples/spi_flash/hardware.yaml -o output/spi_flash`

### 4. pwm
- **功能**：PWM 输出，可调频率和占空比。
- **硬件连接**：PWM → PA8 (TIM1_CH1)；LED → PC0。
- **生成命令**：`hw2c gen -i examples/pwm/hardware.yaml -o output/pwm`

### 5. rtc_advanced
- **功能**：RTC 日历、WakeUp 定时器、软件定时器、Tickless 低功耗、业务状态机（按键→LED 翻转，RTC 超时回退）。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/rtc_advanced/hardware.yaml -o output/rtc_advanced --task examples/rtc_advanced/task.yaml --bind examples/rtc_advanced/bind.yaml`

### 6. i2c_spi_demo
- **功能**：I2C 传感器 (MPU6050) + SPI Flash 综合读写，按键触发传感器数据采集和存储。
- **硬件连接**：I2C1 → PB6(SCL)/PB7(SDA)；SPI1 → PA5(SCK)/PA6(MISO)/PA7(MOSI)/PC4(NSS)；LED → PA0；按键 → PC13。
- **生成命令**：`hw2c gen -i examples/i2c_spi_demo/hardware.yaml -o output/i2c_spi_demo`

### 7. low_power_demo
- **功能**：STOP0 低功耗模式演示，通过 RTC 和按键 EXTI 唤醒。
- **硬件连接**：LED → PA5，按键 → PC13（EXTI 下降沿唤醒）。
- **生成命令**：`hw2c gen -i examples/low_power_demo/hardware.yaml -o output/low_power_demo`

---

## 状态机类

### 8. substate_demo
- **功能**：复合子状态（compound/substate）演示，支持状态层级和入口/出口动作。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/substate_demo/hardware.yaml -o output/substate_demo`

### 9. parallel_states
- **功能**：并行区域（parallel regions）演示，多个独立状态机同时运行。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/parallel_states/hardware.yaml -o output/parallel_states`

### 10. parallel_comm
- **功能**：并行区域之间的跨区域通信（send_to）。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/parallel_comm/hardware.yaml -o output/parallel_comm`

### 11. ref_demo
- **功能**：状态机 ref 引用基础用法，复用子状态机定义。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/ref_demo/hardware.yaml -o output/ref_demo`

### 12. nested_ref
- **功能**：ref 引用 + namespace 命名空间隔离，支持多层嵌套状态机复用。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/nested_ref/hardware.yaml -o output/nested_ref`

### 13. timeline_demo
- **功能**：timeline 时间序列动作，按时间轴依次执行多个延迟动作。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/timeline_demo/hardware.yaml -o output/timeline_demo`

---

## Bootloader 与 FOTA

### 14. bootloader_demo
- **功能**：双槽位 (A/B) Bootloader，硬件 CRC32 校验，TAMP 备份寄存器持久化，启动失败自动回退。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/bootloader_demo/hardware.yaml -o output/bootloader_demo`

### 15. fota_demo
- **功能**：BSDIFF 差分固件升级基础框架，含 Bootloader + CLI 触发 + 双分区 A/B 镜像管理。
- **硬件连接**：LED → PA5；USART2 → PA2(TX)/PA3(RX)。
- **生成命令**：`hw2c gen -i examples/fota_demo/hardware.yaml -o output/fota_demo`

### 16. fota_flow
- **功能**：FOTA 升级完整状态机（空闲/等待补丁/校验/应用/重试/成功/错误 7 状态），含补丁超时和校验失败重试。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`hw2c gen -i examples/fota_flow/hardware.yaml -o output/fota_flow`

---

## 通信协议类

### 17. cli_demo
- **功能**：UART 命令行调试终端，支持 help/version/uptime/free/tasks/reset/gpio/led/rtc 等调试命令。
- **硬件连接**：USART2 → PA2(TX)/PA3(RX) (115200bps)；LED → PC0；按键 → PC13。
- **生成命令**：`hw2c gen -i examples/cli_demo/hardware.yaml -o output/cli_demo`

### 18. modbus_demo
- **功能**：Modbus RTU 从机通信，基于 RS485 物理层。
- **硬件连接**：USART1 → PB6(TX)/PB7(RX) (9600bps)；RS485 DE → PA1；LED → PC0；按键 → PC13。
- **生成命令**：`hw2c gen -i examples/modbus_demo/hardware.yaml -o output/modbus_demo`

### 19. cellular_mqtt
- **功能**：4G Cat.1 蜂窝网络拨号 + MQTT 上云，含三态业务状态机（断连/连接中/已连接）。
- **硬件连接**：USART2 → PA2(TX)/PA3(RX) (115200bps)；LED → PC0；按键 → PC13。
- **生成命令**：`hw2c gen -i examples/cellular_mqtt/hardware.yaml -o output/cellular_mqtt`

### 20. cellular_test
- **功能**：最精简的 4G Cat.1 通信基础测试，仅验证 AT 指令交互和 MQTT 连接能力。
- **硬件连接**：USART2 → PA2(TX)/PA3(RX) (115200bps)；LED → PC0。
- **生成命令**：`hw2c gen -i examples/cellular_test/hardware.yaml -o output/cellular_test`
