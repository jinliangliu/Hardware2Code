#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif

#include "drv_flash.h"

/* CS pin: PA4 */
#define SPI_FLASH_CS_PORT                GPIOA
#define SPI_FLASH_CS_PIN                 GPIO_PIN_4

/* Private variables */
static SPI_HandleTypeDef *flash_spi;
static uint8_t tx_buf[8];

/* Internal helper: select CS (active low) */
static void spi_flash_cs_low(void) {
    HAL_GPIO_WritePin(SPI_FLASH_CS_PORT, SPI_FLASH_CS_PIN, GPIO_PIN_RESET);
}

/* Internal helper: deselect CS (active high) */
static void spi_flash_cs_high(void) {
    HAL_GPIO_WritePin(SPI_FLASH_CS_PORT, SPI_FLASH_CS_PIN, GPIO_PIN_SET);
}

/**
 * @brief   Initialize the SPI Flash driver
 * @param   hspi: pointer to the SPI handle (already configured by HAL)
 * @return  0 on success, -1 on error
 */
int spi_flash_init(SPI_HandleTypeDef *hspi)
{
    if (hspi == NULL) {
        return -1;
    }
    flash_spi = hspi;
    spi_flash_cs_high();
    return 0;
}

/**
 * @brief   Read the JEDEC manufacturer/device ID (3 bytes)
 * @param   id: output buffer (must be at least 3 bytes)
 * @return  0 on success, -1 on error
 */
int spi_flash_get_id(uint8_t *id)
{
    if (id == NULL || flash_spi == NULL) {
        return -1;
    }

    spi_flash_cs_low();
    tx_buf[0] = SPI_FLASH_CMD_READ_ID;
    HAL_SPI_Transmit(flash_spi, tx_buf, 1, 100);
    HAL_SPI_Receive(flash_spi, id, 3, 100);
    spi_flash_cs_high();
    return 0;
}

/**
 * @brief   Read data from flash memory
 * @param   addr: start address (24-bit)
 * @param   buf: output buffer
 * @param   len: number of bytes to read
 * @return  0 on success, -1 on error
 */
int spi_flash_read(uint32_t addr, uint8_t *buf, uint32_t len)
{
    if (buf == NULL || flash_spi == NULL) {
        return -1;
    }

    spi_flash_cs_low();
    tx_buf[0] = SPI_FLASH_CMD_READ_DATA;
    tx_buf[1] = (uint8_t)((addr >> 16) & 0xFF);
    tx_buf[2] = (uint8_t)((addr >> 8) & 0xFF);
    tx_buf[3] = (uint8_t)(addr & 0xFF);
    HAL_SPI_Transmit(flash_spi, tx_buf, 4, 100);
    HAL_SPI_Receive(flash_spi, buf, (uint16_t)len, 1000);
    spi_flash_cs_high();
    return 0;
}

/**
 * @brief   Write data to flash memory (page program)
 * @param   addr: start address (24-bit)
 * @param   buf: data buffer
 * @param   len: number of bytes to write (must fit within one page)
 * @return  0 on success, -1 on error
 */
int spi_flash_write(uint32_t addr, const uint8_t *buf, uint32_t len)
{
    if (buf == NULL || flash_spi == NULL) {
        return -1;
    }

    /* Write Enable */
    spi_flash_cs_low();
    tx_buf[0] = SPI_FLASH_CMD_WRITE_ENABLE;
    HAL_SPI_Transmit(flash_spi, tx_buf, 1, 100);
    spi_flash_cs_high();

    /* Page Program */
    spi_flash_cs_low();
    tx_buf[0] = SPI_FLASH_CMD_PAGE_PROGRAM;
    tx_buf[1] = (uint8_t)((addr >> 16) & 0xFF);
    tx_buf[2] = (uint8_t)((addr >> 8) & 0xFF);
    tx_buf[3] = (uint8_t)(addr & 0xFF);
    HAL_SPI_Transmit(flash_spi, tx_buf, 4, 100);
    HAL_SPI_Transmit(flash_spi, (uint8_t *)buf, (uint16_t)len, 2000);
    spi_flash_cs_high();

#ifdef TEST
    /* No delay in test mode */
#else
    HAL_Delay(10);
#endif
    return 0;
}

/**
 * @brief   Erase a 4KB sector
 * @param   addr: any address within the sector to erase
 * @return  0 on success, -1 on error
 */
int spi_flash_erase_sector(uint32_t addr)
{
    if (flash_spi == NULL) {
        return -1;
    }

    /* Write Enable */
    spi_flash_cs_low();
    tx_buf[0] = SPI_FLASH_CMD_WRITE_ENABLE;
    HAL_SPI_Transmit(flash_spi, tx_buf, 1, 100);
    spi_flash_cs_high();

    /* Sector Erase */
    spi_flash_cs_low();
    tx_buf[0] = SPI_FLASH_CMD_SECTOR_ERASE;
    tx_buf[1] = (uint8_t)((addr >> 16) & 0xFF);
    tx_buf[2] = (uint8_t)((addr >> 8) & 0xFF);
    tx_buf[3] = (uint8_t)(addr & 0xFF);
    HAL_SPI_Transmit(flash_spi, tx_buf, 4, 200);
    spi_flash_cs_high();

#ifdef TEST
    /* No delay in test mode */
#else
    HAL_Delay(100);
#endif
    return 0;
}