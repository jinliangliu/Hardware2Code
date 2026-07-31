"""
driver_api.py - Standardized POSIX-style driver interface signatures.

Each entry defines the public API surface for a driver type.
Templates use these signatures to generate thin HAL wrappers.
Component code calls only these interfaces — never HAL directly.

Interface contract:
  - open:  acquire the peripheral, return opaque handle
  - read:  blocking/non-blocking read from the peripheral
  - write: blocking/non-blocking write to the peripheral
  - ioctl: device-specific control operations
  - close: release the peripheral

Return values:
  - handle:  non-NULL on success, NULL on failure
  - read/write: bytes transferred, or negative error code
  - ioctl: 0 on success, negative error code on failure
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# API table — maps interface type string to function signatures
# ---------------------------------------------------------------------------

DRIVER_POSIX_API = {
    "uart": {
        "open":  "uart_handle_t uart_open(const char *name, const uart_cfg_t *cfg);",
        "read":  "int32_t uart_read(uart_handle_t h, uint8_t *buf, uint32_t len, uint32_t timeout_ms);",
        "write": "int32_t uart_write(uart_handle_t h, const uint8_t *buf, uint32_t len);",
        "ioctl": "int32_t uart_ioctl(uart_handle_t h, uint32_t cmd, void *arg);",
        "close": "void uart_close(uart_handle_t h);",
    },
    "gpio": {
        "open":  "gpio_handle_t gpio_open(const char *name, const gpio_cfg_t *cfg);",
        "read":  "int32_t gpio_read(gpio_handle_t h);",
        "write": "int32_t gpio_write(gpio_handle_t h, int32_t value);",
        "ioctl": "int32_t gpio_ioctl(gpio_handle_t h, uint32_t cmd, void *arg);",
        "close": "void gpio_close(gpio_handle_t h);",
    },
    "adc": {
        "open":  "adc_handle_t adc_open(const char *name, const adc_cfg_t *cfg);",
        "read":  "int32_t adc_read(adc_handle_t h, uint32_t channel, uint32_t *value_mv);",
        "ioctl": "int32_t adc_ioctl(adc_handle_t h, uint32_t cmd, void *arg);",
        "close": "void adc_close(adc_handle_t h);",
    },
    "i2c": {
        "open":  "i2c_handle_t i2c_open(const char *name, const i2c_cfg_t *cfg);",
        "read":  "int32_t i2c_read(i2c_handle_t h, uint16_t dev_addr, uint8_t *buf, uint32_t len);",
        "write": "int32_t i2c_write(i2c_handle_t h, uint16_t dev_addr, const uint8_t *buf, uint32_t len);",
        "ioctl": "int32_t i2c_ioctl(i2c_handle_t h, uint32_t cmd, void *arg);",
        "close": "void i2c_close(i2c_handle_t h);",
    },
    "pwm": {
        "open":  "pwm_handle_t pwm_open(const char *name, const pwm_cfg_t *cfg);",
        "write": "int32_t pwm_set_duty(pwm_handle_t h, uint32_t duty_percent);",
        "ioctl": "int32_t pwm_ioctl(pwm_handle_t h, uint32_t cmd, void *arg);",
        "close": "void pwm_close(pwm_handle_t h);",
    },
    "rtc": {
        "open":  "rtc_handle_t rtc_open(const char *name);",
        "read":  "int32_t rtc_get_time(rtc_handle_t h, rtc_time_t *t);",
        "write": "int32_t rtc_set_time(rtc_handle_t h, const rtc_time_t *t);",
        "ioctl": "int32_t rtc_ioctl(rtc_handle_t h, uint32_t cmd, void *arg);",
    },
}


# ---------------------------------------------------------------------------
# IOCTL command constants — per-driver command sets
# ---------------------------------------------------------------------------

UART_IOCTL = {
    "SET_BAUD":    "0x01",   # arg: uint32_t *baud
    "GET_BAUD":    "0x02",   # arg: uint32_t *baud
    "FLUSH_RX":    "0x03",   # arg: NULL, discard rx buffer
    "FLUSH_TX":    "0x04",   # arg: NULL, wait tx complete
    "SET_TIMEOUT": "0x05",   # arg: uint32_t *timeout_ms
}

GPIO_IOCTL = {
    "SET_MODE":    "0x01",   # arg: uint32_t *mode (0=input,1=output,2=af)
    "SET_PULL":    "0x02",   # arg: uint32_t *pull (0=none,1=up,2=down)
    "TOGGLE":      "0x03",   # arg: NULL
}

ADC_IOCTL = {
    "START_CONV":  "0x01",   # arg: NULL, start conversion
    "STOP_CONV":   "0x02",   # arg: NULL, stop conversion
    "GET_RAW":     "0x03",   # arg: uint32_t *raw_value
}

RTC_IOCTL = {
    "GET_TICK":    "0x01",   # arg: uint64_t *tick_count
    "SET_ALARM":   "0x02",   # arg: rtc_alarm_t *alarm
    "CLEAR_ALARM": "0x03",   # arg: uint32_t alarm_id
}


# ---------------------------------------------------------------------------
# Opaque handle type definitions
# ---------------------------------------------------------------------------

HANDLE_TYPES = {
    "uart": "typedef struct uart_dev *uart_handle_t;",
    "gpio": "typedef struct gpio_dev *gpio_handle_t;",
    "adc":  "typedef struct adc_dev  *adc_handle_t;",
    "i2c":  "typedef struct i2c_dev  *i2c_handle_t;",
    "pwm":  "typedef struct pwm_dev  *pwm_handle_t;",
    "rtc":  "typedef struct rtc_dev  *rtc_handle_t;",
}
