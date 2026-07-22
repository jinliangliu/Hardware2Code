# 示例工程

## 1. blinky_g0
- **功能**：LED 翻转，按键中断。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`python generator/generate.py -i examples/blinky_g0/hardware.yaml -o output/blinky_g0`

## 2. mpu6050
- **功能**：读取加速度，检测倾斜报警，通过事件管理器控制 LED。
- **硬件连接**：I2C1 → PB6(SCL)/PB7(SDA)；LED → PC0；按键 → PC13。
- **生成命令**：`python generator/generate.py -i examples/mpu6050/hardware.yaml -o output/mpu6050`

## 3. rtc_adv
- **功能**：RTC 日历、WakeUp 定时器、软件定时器、Tickless 低功耗、业务状态机（按键→LED 翻转，RTC 超时回退）。
- **硬件连接**：LED → PC0，按键 → PC13。
- **生成命令**：`python generator/generate.py -i examples/rtc_advanced/hardware.yaml -o output/rtc_adv`
- **调试**：Debug 版本（`make debug`）使用 SLEEP 模式，保持调试连接。

## 4. spi_flash
- **功能**：SPI Flash ID 读取、扇区擦除、数据写入。
- **硬件连接**：SPI1 → PA5(SCK)/PA6(MISO)/PA7(MOSI)/PC4(NSS)；LED → PC0。
- **生成命令**：`python generator/generate.py -i examples/spi_flash/hardware.yaml -o output/spi_flash`

## 5. pwm
- **功能**：PWM 输出，可调频率和占空比。
- **硬件连接**：PWM → PA8 (TIM1_CH1)；LED → PC0。
- **生成命令**：`python generator/generate.py -i examples/pwm/hardware.yaml -o output/pwm`