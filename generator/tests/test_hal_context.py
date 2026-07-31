"""Tests for generator/context/hal_context.py"""

from generator.context.hal_context import BASE_HAL_SOURCES, compute_hal_sources


def test_base_hal_sources_not_empty():
    """BASE_HAL_SOURCES should contain core HAL files"""
    assert len(BASE_HAL_SOURCES) > 0
    assert 'stm32g0xx_hal.c' in BASE_HAL_SOURCES
    assert 'stm32g0xx_hal_gpio.c' in BASE_HAL_SOURCES


def test_compute_hal_sources_basic():
    """No peripherals should return base sources only"""
    flags = {"has_i2c": False, "has_rtc": False, "has_spi": False, "has_pwm": False,
             "has_adc": False, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags, hil_mode=False)
    assert 'stm32g0xx_hal.c' in result
    assert 'stm32g0xx_hal_i2c.c' not in result


def test_compute_hal_sources_with_i2c():
    """I2C enabled should add i2c HAL source"""
    flags = {"has_i2c": True, "has_rtc": False, "has_spi": False, "has_pwm": False,
             "has_adc": False, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags)
    assert 'stm32g0xx_hal_i2c.c' in result


def test_compute_hal_sources_with_rtc():
    """RTC enabled should add RTC and TIM HAL sources"""
    flags = {"has_i2c": False, "has_rtc": True, "has_spi": False, "has_pwm": False,
             "has_adc": False, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags)
    assert 'stm32g0xx_hal_rtc.c' in result
    assert 'stm32g0xx_hal_tim.c' in result


def test_compute_hal_sources_with_spi():
    """SPI enabled should add spi HAL source"""
    flags = {"has_i2c": False, "has_rtc": False, "has_spi": True, "has_pwm": False,
             "has_adc": False, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags)
    assert 'stm32g0xx_hal_spi.c' in result


def test_compute_hal_sources_with_pwm():
    """PWM enabled should add tim HAL sources"""
    flags = {"has_i2c": False, "has_rtc": False, "has_spi": False, "has_pwm": True,
             "has_adc": False, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags)
    assert 'stm32g0xx_hal_tim.c' in result


def test_compute_hal_sources_with_bootloader():
    """Bootloader enabled should add iwdg HAL source"""
    flags = {"has_i2c": False, "has_rtc": False, "has_spi": False, "has_pwm": False,
             "has_adc": False, "has_uart": False, "has_bootloader": True}
    result = compute_hal_sources(flags)
    assert 'stm32g0xx_hal_iwdg.c' in result


def test_compute_hal_sources_deduplication():
    """Multiple flags requiring same HAL file should not duplicate"""
    flags = {"has_i2c": False, "has_rtc": True, "has_spi": False, "has_pwm": True,
             "has_adc": False, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags)
    # Both RTC and PWM add stm32g0xx_hal_tim.c — should only appear once
    assert result.count('stm32g0xx_hal_tim.c') == 1


def test_compute_hal_sources_hil_mode():
    """HIL mode should add uart HAL source"""
    flags = {"has_i2c": False, "has_rtc": False, "has_spi": False, "has_pwm": False,
             "has_adc": False, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags, hil_mode=True)
    assert 'stm32g0xx_hal_uart.c' in result


def test_compute_hal_sources_with_adc():
    """ADC enabled should add adc HAL source"""
    flags = {"has_i2c": False, "has_rtc": False, "has_spi": False, "has_pwm": False,
             "has_adc": True, "has_uart": False, "has_bootloader": False}
    result = compute_hal_sources(flags)
    assert 'stm32g0xx_hal_adc.c' in result


def test_compute_hal_sources_no_flags_uses_defaults():
    """Missing flags should not cause errors (uses .get defaults)"""
    result = compute_hal_sources({}, hil_mode=False)
    assert 'stm32g0xx_hal.c' in result


if __name__ == "__main__":
    test_base_hal_sources_not_empty()
    test_compute_hal_sources_basic()
    test_compute_hal_sources_with_i2c()
    test_compute_hal_sources_with_rtc()
    test_compute_hal_sources_with_spi()
    test_compute_hal_sources_with_pwm()
    test_compute_hal_sources_with_bootloader()
    test_compute_hal_sources_deduplication()
    test_compute_hal_sources_hil_mode()
    print("All hal_context tests passed.")
