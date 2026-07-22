#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif
#include "drv_uart_debug.h"

#ifndef TEST
static UART_HandleTypeDef *huart_ptr;
#endif

void UART_Init(UART_HandleTypeDef *huart) {
#ifndef TEST
    huart_ptr = huart;
#else
    (void)huart;
    HAL_UART_Init(NULL);   /* 测试环境：调用 mock 函数 */
#endif
}

void UART_SendByte(uint8_t byte) {
#ifndef TEST
    HAL_UART_Transmit(huart_ptr, &byte, 1, 100);
#else
    (void)byte;
#endif
}

void UART_SendString(const char *str) {
#ifndef TEST
    HAL_UART_Transmit(huart_ptr, (uint8_t *)str, strlen(str), 100);
#else
    (void)str;
#endif
}

uint8_t UART_ReceiveByte(void) {
#ifndef TEST
    uint8_t byte;
    HAL_UART_Receive(huart_ptr, &byte, 1, 100);
    return byte;
#else
    return 0;
#endif
}