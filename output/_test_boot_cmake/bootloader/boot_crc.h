/**
 * @file    boot_crc.h
 * @brief   CRC32 固件完整性校验接口
 */

#ifndef __BOOT_CRC_H
#define __BOOT_CRC_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief   CRC32 硬件校验固件镜像完整性
 * @param   flash_start : 固件镜像起始 Flash 地址
 * @param   slot_size   : 槽位总大小（字节），元数据位于末尾 8 字节
 * @return  true = CRC 匹配，固件完整; false = 校验失败
 * @note    镜像格式: [固件数据 ...] [4B image_size] [4B CRC32]
 */
bool boot_crc_verify(uint32_t flash_start, uint32_t slot_size);

/**
 * @brief   读取固件映像的版本号
 * @param   flash_start : 固件 Flash 起始地址
 * @return  版本号 (1~0xFFFFFF)，0 表示未找到有效头部
 */
uint32_t boot_read_fw_version(uint32_t flash_start);

#ifdef __cplusplus
}
#endif

#endif /* __BOOT_CRC_H */