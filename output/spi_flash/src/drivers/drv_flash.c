#include "drv_flash.h"

static SPI_HandleTypeDef *spi_handle;
static uint8_t tx_buf[4], rx_buf[4];

void flash_init(SPI_HandleTypeDef *hspi) {
    spi_handle = hspi;
}

void flash_read_id(uint8_t *id) {
    tx_buf[0] = 159;
    HAL_SPI_TransmitReceive(spi_handle, tx_buf, id, 3, 100);
}

void flash_read_data(uint32_t addr, uint8_t *buf, uint32_t len) {
    tx_buf[0] = 3;
    tx_buf[1] = (addr >> 16) & 0xFF;
    tx_buf[2] = (addr >> 8) & 0xFF;
    tx_buf[3] = addr & 0xFF;
    HAL_SPI_Transmit(spi_handle, tx_buf, 4, 100);
    HAL_SPI_Receive(spi_handle, buf, len, 1000);
}

void flash_sector_erase(uint32_t addr) {
    tx_buf[0] = 6;
    HAL_SPI_Transmit(spi_handle, tx_buf, 1, 100);
    tx_buf[0] = 32;
    tx_buf[1] = (addr >> 16) & 0xFF;
    tx_buf[2] = (addr >> 8) & 0xFF;
    tx_buf[3] = addr & 0xFF;
    HAL_SPI_Transmit(spi_handle, tx_buf, 4, 200);
    HAL_Delay(100);
}

void flash_write_data(uint32_t addr, const uint8_t *buf, uint32_t len) {
    tx_buf[0] = 6;
    HAL_SPI_Transmit(spi_handle, tx_buf, 1, 100);
    tx_buf[0] = 0x02;  // Page Program command (not in model, common)
    tx_buf[1] = (addr >> 16) & 0xFF;
    tx_buf[2] = (addr >> 8) & 0xFF;
    tx_buf[3] = addr & 0xFF;
    HAL_SPI_Transmit(spi_handle, tx_buf, 4, 100);
    HAL_SPI_Transmit(spi_handle, (uint8_t *)buf, len, 2000);
    HAL_Delay(10);
}