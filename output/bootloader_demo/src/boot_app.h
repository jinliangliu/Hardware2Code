/**
 * @file    boot_app.h
 * @brief   App 端 Bootloader 协作接口
 *          应用程序调用此接口告知 Bootloader "启动成功"。
 */

#ifndef __BOOT_APP_H
#define __BOOT_APP_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief  标记应用启动成功
 * @note   必须在 main() 中尽早调用（FreeRTOS 初始化完成后即可调用）。
 *         写入 TAMP_BKP2R = BOOT_OK_MAGIC，Bootloader 在下次上电时识别。
 *         如果 App 卡死 → WDG 复位 → Bootloader 检测 BOOT_OK 未写入 → 计为失败。
 */
void boot_app_mark_ok(void);

#ifdef __cplusplus
}
#endif

#endif /* __BOOT_APP_H */