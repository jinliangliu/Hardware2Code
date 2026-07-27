"""
bootloader_context.py
Bootloader / FOTA / IWDG configuration helpers.
"""


def build_boot_config(bootloader_raw: dict) -> tuple:
    """
    Parse bootloader raw config and set defaults.

    Args:
        bootloader_raw: raw bootloader dict from hardware YAML.

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
