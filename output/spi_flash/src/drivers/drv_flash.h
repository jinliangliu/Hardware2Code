#ifndef __DRV_FLASH_H
#define __DRV_FLASH_H

#include "stm32g0xx_hal.h"

void flash_init(SPI_HandleTypeDef *hspi);
void flash_read_id(uint8_t *id);
void flash_read_data(uint32_t addr, uint8_t *buf, uint32_t len);
void flash_sector_erase(uint32_t addr);
void flash_write_data(uint32_t addr, const uint8_t *buf, uint32_t len);

#endif