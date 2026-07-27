#ifndef __DRV_DEBUG_UART_H
#define __DRV_DEBUG_UART_H

#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#include <stdbool.h>
#endif

void UART_Init(UART_HandleTypeDef *huart);
void UART_SendByte(uint8_t byte);
void UART_SendString(const char *str);
uint8_t UART_ReceiveByte(void);

/* ---- Interrupt-based receive API (used by FOTA) ---- */

/**
 * @brief   Start interrupt-based receive into buffer
 * @param   buf   Receive buffer (must remain valid until callback)
 * @param   size  Buffer size in bytes
 */
void UART_StartRx_IT(uint8_t *buf, uint16_t size);

/**
 * @brief   Get number of bytes received in current Rx buffer
 */
uint16_t UART_GetRxCount(void);

/**
 * @brief   Check if current interrupt receive is complete
 */
bool UART_IsRxComplete(void);

#ifndef TEST
/**
 * @brief   HAL UART Rx complete callback (weak, user overrideable)
 * @note    Called from USARTx_IRQHandler via HAL_UART_IRQHandler
 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart);
#endif

#endif