/**
 * @file    boot_crc.c
 * @brief   STM32G0 硬件 CRC32 固件完整性校验实现
 *          镜像头部（向量表后 0xC0 偏移处）包含 image_size 和 CRC32。
 *          依赖 stm32g0xx.h (CMSIS)，不依赖 HAL。
 */

#include "boot_crc.h"
#include "stm32g0xx.h"

/* 镜像头部定义 */
#define APP_HEADER_MAGIC    0x4841436BUL   /* "H2Ck" */
#define HEADER_SEARCH_MAX   0x200U         /* 在前 512 字节搜索 magic */

/**
 * @brief  硬件 CRC32 固件完整性校验
 * @param  flash_start  固件槽位 Flash 起始地址
 * @param  slot_size    槽位总大小（未使用，保留兼容）
 * @return true 固件完整，false 校验失败或参数非法
 * @note   搜索 magic "H2Ck" 定位 Header，格式:
 *         [image_size(4B) | CRC32(4B) | magic(4B)] | payload...
 *         CRC 覆盖 payload 区域（magic 之后 image_size 字节）。
 */
bool boot_crc_verify(uint32_t flash_start, uint32_t slot_size)
{
    (void)slot_size;    /* 槽位大小在新方案中不使用 */

    if (flash_start == 0) {
        return false;
    }

    /* 在向量表后的 Flash 区域搜索 magic "H2Ck" 定位头部 */
    uint32_t magic_offset = 0;
    bool found = false;

    for (uint32_t off = 0x40; off < HEADER_SEARCH_MAX; off += 4) {
        if (((volatile uint32_t *)(flash_start + off))[0] == APP_HEADER_MAGIC) {
            magic_offset = off;
            found = true;
            break;
        }
    }

    if (!found) {
        return false;             /* 未找到有效头部魔数 */
    }

    /* 头部位于 magic 之前 8 字节: image_size(4B) + CRC32(4B) */
    uint32_t header_addr = flash_start + magic_offset - 8;

    uint32_t image_size = ((volatile uint32_t *)header_addr)[0];
    uint32_t stored_crc = ((volatile uint32_t *)header_addr)[1];

    /* 校验 image_size 合法性（必须足够大，且不超过整个 Bank） */
    uint32_t max_size = 0x00040000;   /* Bank 大小 256KB */
    if (image_size == 0 || image_size == 0xFFFFFFFF || image_size > max_size) {
        return false;
    }
    if ((image_size & 0x3) != 0) {
        return false;                 /* 非字对齐 */
    }

    /* 有效载荷起始地址: magic 之后（flash_start + magic_offset + 4） */
    uint32_t payload_addr = flash_start + magic_offset + 4;

    /* 使能 CRC 时钟 */
    RCC->AHBENR |= RCC_AHBENR_CRCEN;

    /* 配置 CRC 为 CRC-32/MPEG-2 模式（与 patch_crc.py 一致）：
     *   REV_IN=01 : 字内字节反转（输入位反转）
     *   REV_OUT=1 : 输出位反转
     *   多项式和初值使用默认值（0x04C11DB7 / 0xFFFFFFFF） */
    CRC->CR |= CRC_CR_REV_IN_0 | CRC_CR_REV_OUT;

    /* 复位 CRC 模块 */
    CRC->CR |= CRC_CR_RESET;
    CRC->CR &= ~CRC_CR_RESET;

    /* 按 32-bit 字逐字计算 CRC */
    uint32_t word_count = image_size / 4;
    uint32_t *pdata = (uint32_t *)payload_addr;

    for (uint32_t i = 0; i < word_count; i++) {
        CRC->DR = pdata[i];
    }

    uint32_t calculated_crc = CRC->DR;

    return (calculated_crc == stored_crc);
}

/**
 * @brief   从固件头部读取版本号
 * @param   flash_start  固件 Flash 起始地址
 * @return  版本号 (0x00000001~0x00FFFFFF)，0 表示未找到
 * @note    格式: [image_size(4B)] [CRC32(4B)] [magic"H2Ck"(4B)] [fw_version(4B)] [payload...]
 *          fw_version 位于 magic 之后的 4 字节，是 payload 的一部分
 */
uint32_t boot_read_fw_version(uint32_t flash_start)
{
    for (uint32_t off = 0x40; off < HEADER_SEARCH_MAX; off += 4) {
        if (((volatile uint32_t *)(flash_start + off))[0] == APP_HEADER_MAGIC) {
            /* fw_version 紧接在 magic 之后 */
            return ((volatile uint32_t *)(flash_start + off))[1];
        }
    }
    return 0;
}