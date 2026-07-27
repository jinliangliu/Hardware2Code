/**
 * @file    boot_app.c
 * @brief   App 端 Bootloader 协作实现
 *          直接操作 TAMP 备份寄存器（CMSIS 寄存器操作，不依赖 HAL）。
 */

#include "boot_app.h"
#include "stm32g0xx.h"

/* 启动成功魔数（与 boot_nvm.h 保持一致） */
#define BOOT_OK_MAGIC  0xB007C0DEUL

/**
 * @brief  标记应用启动成功
 *         写入 TAMP 备份寄存器 2，Bootloader 在上电时读取此寄存器。
 *         若此寄存器非 BOOT_OK_MAGIC，Bootloader 认为上次启动失败。
 */
void boot_app_mark_ok(void)
{
    /* 确保 PWR 时钟已启用（用于备份域解锁） */
    RCC->APBENR1 |= RCC_APBENR1_PWREN;

    /* 确保 RTC/TAMP 时钟已启用 */
    RCC->APBENR1 |= RCC_APBENR1_RTCAPBEN;

    /* 解锁备份域写保护 */
    PWR->CR1 |= PWR_CR1_DBP;

    /* 等待 DBP 位同步完成 — 备份域由低速时钟驱动，写操作需同步延迟 */
    while ((PWR->CR1 & PWR_CR1_DBP) == 0U) { }

    /* 写入启动成功魔数 */
    TAMP->BKP2R = BOOT_OK_MAGIC;
}