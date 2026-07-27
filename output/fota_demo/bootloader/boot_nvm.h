/**
 * @file    boot_nvm.h
 * @brief   Bootloader 非易失标志存储接口
 *          使用 TAMP 备份寄存器在复位间持久化启动状态。
 *          备份寄存器在 VBAT 供电时掉电不丢失。
 *          函数入参均需非空校验。
 */

#ifndef __BOOT_NVM_H
#define __BOOT_NVM_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========== 启动标志位定义 ========== */

/* TAMP 备份寄存器分配（通过 TAMP->BKPxR 直接访问）:
 *   BKP0R = 启动失败计数器
 *   BKP1R = 当前活动槽位 (0=A, 1=B)
 *   BKP2R = App 启动成功标志
 */

/* 启动成功魔数 */
#define BOOT_OK_MAGIC            0xB007C0DEUL

/* 最大连续启动重试次数 */
#define BOOT_MAX_RETRIES         3

/* 槽位定义 */
#define BOOT_SLOT_A              0U
#define BOOT_SLOT_B              1U

/* ========== API ========== */

/**
 * @brief 初始化 TAMP 备份域时钟
 * @note  必须在访问任何 TAMP 寄存器之前调用
 */
void boot_nvm_init(void);

/**
 * @brief 重置所有启动标志为默认值
 *        计数器清零，槽位重置为 Slot A
 */
void boot_nvm_reset(void);

/**
 * @brief 获取当前启动尝试计数
 * @return 0 ~ BOOT_MAX_RETRIES
 */
uint32_t boot_nvm_get_attempt_count(void);

/**
 * @brief 递增启动尝试计数（+1）
 * @note  调用者负责在上电时判断是否超限
 */
void boot_nvm_inc_attempt_count(void);

/**
 * @brief 清除启动尝试计数（归零）
 * @note  App 启动成功后调用
 */
void boot_nvm_clear_attempt_count(void);

/**
 * @brief 获取当前活动槽位
 * @return BOOT_SLOT_A (0) 或 BOOT_SLOT_B (1)
 */
uint32_t boot_nvm_get_active_slot(void);

/**
 * @brief 切换活动槽位 (A→B 或 B→A)
 * @note  切换后计数器自动清零
 */
void boot_nvm_swap_active_slot(void);

/**
 * @brief 检查 App 是否已成功启动（boot_ok 标志）
 * @return true 已启动成功, false 未写入
 */
bool boot_nvm_is_boot_ok(void);

/**
 * @brief 写入启动成功魔数
 * @note  App 初始化完成后调用
 */
void boot_nvm_set_boot_ok(void);

/**
 * @brief 清除启动成功标志
 * @note  Bootloader 启动时调用，为新一轮验证做准备
 */
void boot_nvm_clear_boot_ok(void);

#ifdef __cplusplus
}
#endif

#endif /* __BOOT_NVM_H */