/**
 * @file    boot_jump.h
 * @brief   Bootloader 应用跳转接口
 */

#ifndef __BOOT_JUMP_H
#define __BOOT_JUMP_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief  安全跳转到应用程序
 * @param  app_addr : App 向量表起始地址（Flash 地址）
 * @note   调用后不返回。跳转前会执行:
 *         1. 关闭全局中断
 *         2. 复位 SysTick
 *         3. 清除所有 NVIC 中断挂起和使能位
 *         4. 设置 VTOR 到 App 地址
 *         5. 加载 MSP 并跳转到 Reset_Handler
 */
void boot_jump_to_app(uint32_t app_addr);

#ifdef __cplusplus
}
#endif

#endif /* __BOOT_JUMP_H */