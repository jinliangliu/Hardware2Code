"""
jinja_filters.py
Custom Jinja2 filters for Hardware2Code templates.
Consolidates pin-to-register conversion, EXTI mapping, and other
STM32-specific logic that was previously computed inside templates.

Usage in generate.py:
    from jinja_filters import register_filters
    env = Environment(loader=...)
    register_filters(env)
"""


def pin_port(pin_id: str) -> str:
    """Extract GPIO port letter from pin ID.
    'PA5' -> 'A', 'PC13' -> 'C'
    """
    return pin_id[1]


def pin_number(pin_id: str) -> str:
    """Extract pin number as string from pin ID.
    'PA5' -> '5', 'PC13' -> '13'
    """
    return pin_id[2:]


def pin_num_int(pin_id: str) -> int:
    """Extract pin number as integer from pin ID.
    'PA5' -> 5, 'PC13' -> 13
    """
    return int(pin_id[2:])


def hal_pin(pin_id: str) -> str:
    """Convert pin ID to HAL GPIO_PIN macro.
    'PA5' -> 'GPIO_PIN_5', 'PC13' -> 'GPIO_PIN_13'
    """
    return f"GPIO_PIN_{pin_id[2:]}"


def hal_port(pin_id: str) -> str:
    """Convert pin ID to HAL GPIO port macro.
    'PA5' -> 'GPIOA', 'PC13' -> 'GPIOC'
    """
    return f"GPIO{pin_id[1]}"


def exti_irq_name(pin_id: str) -> str:
    """Map pin ID to EXTI IRQ number.
    'PA0' -> 'EXTI0_1_IRQn'
    'PA2' -> 'EXTI2_3_IRQn'
    'PC13' -> 'EXTI4_15_IRQn'
    """
    num = int(pin_id[2:]) if len(pin_id) > 2 else 0
    if num <= 1:
        return "EXTI0_1_IRQn"
    elif num <= 3:
        return "EXTI2_3_IRQn"
    else:
        return "EXTI4_15_IRQn"


def exti_handler_name(pin_id: str) -> str:
    """Map pin ID to EXTI IRQ handler function name.
    'PA0' -> 'EXTI0_1_IRQHandler'
    'PC13' -> 'EXTI4_15_IRQHandler'
    """
    num = int(pin_id[2:]) if len(pin_id) > 2 else 0
    if num <= 1:
        return "EXTI0_1_IRQHandler"
    elif num <= 3:
        return "EXTI2_3_IRQHandler"
    else:
        return "EXTI4_15_IRQHandler"


def event_name(name: str) -> str:
    """Convert event name to underscore form (replaces spaces), without EVENT_ prefix.
    'MINUTE TICK' -> 'MINUTE_TICK'
    Use 'EVENT_' + name|event_name in templates when the enum prefix is needed.
    """
    return name.replace(' ', '_')


def event_enum(name: str) -> str:
    """Convert event name to full EVENT_ enum form.
    'MINUTE TICK' -> 'EVENT_MINUTE_TICK'
    """
    return f"EVENT_{name.replace(' ', '_')}"


def to_binary(value: int, bits: int = 8) -> str:
    """Convert integer to binary string literal.
    0x55, 8 -> '0b01010101'
    Used for register value documentation in templates.
    """
    return f"0b{value:0{bits}b}"


def i2c_timing_hex(value: int) -> str:
    """Format I2C TIMINGR value as hex for template use.
    If value is from a pre-calculated I2CConfig, use it; otherwise default.
    """
    if isinstance(value, int):
        return f"0x{value:08X}"
    return "0x00000F13"


def spi_prescaler_code(value: int) -> str:
    """Map SPI prescaler divisor to HAL prescaler macro.
    8 -> 'SPI_BAUDRATEPRESCALER_8'
    """
    return f"SPI_BAUDRATEPRESCALER_{value}"


def register_filters(env) -> None:
    """Register all custom Jinja2 filters on the given Environment."""
    env.filters['pin_port'] = pin_port
    env.filters['pin_number'] = pin_number
    env.filters['pin_num_int'] = pin_num_int
    env.filters['hal_pin'] = hal_pin
    env.filters['hal_port'] = hal_port
    env.filters['exti_irq_name'] = exti_irq_name
    env.filters['exti_handler_name'] = exti_handler_name
    env.filters['event_name'] = event_name
    env.filters['event_enum'] = event_enum
    env.filters['to_binary'] = to_binary
    env.filters['i2c_timing_hex'] = i2c_timing_hex
    env.filters['spi_prescaler_code'] = spi_prescaler_code
