#ifndef __DRV_FLASH_H
#define __DRV_FLASH_H

#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif

#include <stdint.h>

/* Command constants */
#define SPI_FLASH_CMD_READ_ID        ((uint8_t)159)
#define SPI_FLASH_CMD_READ_DATA      ((uint8_t)3)
#define SPI_FLASH_CMD_WRITE_ENABLE   ((uint8_t)6)
#define SPI_FLASH_CMD_SECTOR_ERASE   ((uint8_t)32)
#define SPI_FLASH_CMD_CHIP_ERASE     ((uint8_t)199)
#define SPI_FLASH_CMD_PAGE_PROGRAM   ((uint8_t)0x02)

/* Flash geometry */
#define SPI_FLASH_SECTOR_SIZE        4096U
#define SPI_FLASH_PAGE_SIZE          256U
#define SPI_FLASH_TOTAL_SIZE         4194304U

/* SPI Flash API */
int spi_flash_init(SPI_HandleTypeDef *hspi);
int spi_flash_read(uint32_t addr, uint8_t *buf, uint32_t len);
int spi_flash_write(uint32_t addr, const uint8_t *buf, uint32_t len);
int spi_flash_erase_sector(uint32_t addr);
int spi_flash_get_id(uint8_t *id);

#endif /* __DRV_FLASH_H */