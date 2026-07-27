"""
bootloader_context.py
Bootloader / FOTA / IWDG / LED pin configuration helpers.
"""


def get_boot_led_pin(pins: list) -> dict:
    """
    Extract LED pin info from YAML pins list.

    Searches for pin with label == "LED".  Falls back to GPIOC / pin 0 if
    no LED pin is declared in the hardware YAML.

    Args:
        pins: list of pin dicts, each with 'id', 'label', 'function'.

    Returns:
        dict with keys: boot_led_port, boot_led_pin_num, boot_led_rcc_enable.
    """
    led_pin = None
    for p in pins:
        if p.get('label') == 'LED':
            led_pin = p
            break

    if led_pin:
        pin_id = led_pin['id']          # e.g. "PA5"
        port_letter = pin_id[1]          # 'A'
        pin_num = int(pin_id[2:])        # 5
    else:
        port_letter = 'C'
        pin_num = 0

    return {
        'boot_led_port': f'GPIO{port_letter}',
        'boot_led_pin_num': pin_num,
        'boot_led_rcc_enable': f'RCC_IOPENR_GPIO{port_letter}EN',
    }


def build_boot_config(bootloader_raw: dict,
                      mcu_flash_kb: int = 512) -> tuple:
    """
    Parse bootloader raw config, set defaults, and compute linker-level
    slot addresses.

    Args:
        bootloader_raw: raw bootloader dict from hardware YAML.
        mcu_flash_kb:  total on-chip Flash size in KiB (default 512 for
                       STM32G0B1RE).

    Returns:
        (boot_config, has_bootloader) tuple.
    """
    has_bootloader = bootloader_raw.get('enabled', False)
    boot_config = dict(bootloader_raw) if has_bootloader else {}
    if has_bootloader:
        boot_config.setdefault('size_kb', 8)
        boot_config.setdefault('app_a_offset', 0x2000)
        boot_config.setdefault('app_b_offset', 0x40000)
        boot_config.setdefault('crc_method', 'crc32_hw')
        boot_config.setdefault('boot_flag_src', 'tamp_bkp')
        boot_config.setdefault('max_retries', 3)
        boot_config.setdefault('wdg_timeout_ms', 5000)

        # Compute IWDG reload value: prescaler /256, LSI ~32kHz → 8ms per tick
        # Clamp to 12-bit range [1, 0xFFF]
        wdg_timeout_ms = boot_config['wdg_timeout_ms']
        boot_config['iwdg_reload_value'] = max(1, min(int(wdg_timeout_ms / 8), 0xFFF))

        # ---- Compute linker-script slot addresses (all derived from config) ----
        flash_base = 0x08000000
        ao = boot_config['app_a_offset']
        bo = boot_config['app_b_offset']
        flash_bytes = mcu_flash_kb * 1024

        boot_config['_app_a_start'] = flash_base + ao
        boot_config['_app_a_end']   = flash_base + bo
        boot_config['_app_b_start'] = flash_base + bo
        boot_config['_app_b_end']   = flash_base + flash_bytes

        # Convenience: slot sizes for C code
        boot_config['_app_a_size'] = bo - ao
        boot_config['_app_b_size'] = flash_bytes - bo

    return (boot_config, has_bootloader)


def inject_bootloader_drivers(has_bootloader: bool, has_uart: bool,
                               boot_config: dict, uart_name: str) -> dict:
    """
    Auto-inject IWDG driver (bootloader) and FOTA drivers (bootloader + UART).

    Args:
        has_bootloader: whether bootloader is enabled.
        has_uart: whether any UART peripheral is present.
        boot_config: bootloader config dict with defaults already applied.
        uart_name: name of the primary UART peripheral for FOTA.

    Returns:
        dict with drivers_additions (list), has_fota (bool), hal_additions (list).
    """
    drivers_additions = []
    has_fota = False
    hal_additions = []

    # IWDG driver is auto-injected when bootloader is enabled
    if has_bootloader:
        drivers_additions.append({
            'name': 'iwdg',
            'template': 'drivers/drv_iwdg.c.j2',
            'header_template': 'drivers/drv_iwdg.h.j2',
            'model': {'type': 'Internal_IWDG'},
            'peripheral': {
                'name': 'iwdg',
                'wdg_timeout_ms': boot_config.get('wdg_timeout_ms', 5000)
            }
        })

    # FOTA modules are auto-injected when bootloader + UART are both enabled
    has_fota = has_bootloader and has_uart
    if has_fota:
        drivers_additions.append({
            'name': 'fota',
            'template': 'drivers/drv_fota.c.j2',
            'header_template': 'drivers/drv_fota.h.j2',
            'model': {'type': 'Internal_FOTA'},
            'peripheral': {
                'name': 'fota',
                'uart_name': uart_name
            }
        })
        drivers_additions.append({
            'name': 'fota_bspatch',
            'template': 'drivers/fota_bspatch.c.j2',
            'header_template': 'drivers/fota_bspatch.h.j2',
            'model': {'type': 'Internal_FOTA'},
            'peripheral': {'name': 'fota_bspatch'}
        })
        hal_additions.extend(['stm32g0xx_hal_flash.c', 'stm32g0xx_hal_flash_ex.c'])

    return {
        'drivers_additions': drivers_additions,
        'has_fota': has_fota,
        'hal_additions': hal_additions
    }
