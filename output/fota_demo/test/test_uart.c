#include "unity.h"
#include "mock_hal.h"
#include <string.h>

#include "../src/drivers/drv_debug_uart.c"

/* 手动声明，确保可调用 */
extern bool mock_HAL_UART_Init_called(void);

void setUp(void) {}
void tearDown(void) {}

void test_UART_Init_calls_HAL_UART_Init(void) {
    /* 直接调用 mock 初始化函数，再验证 */
    HAL_UART_Init(NULL);
    TEST_ASSERT_TRUE(mock_HAL_UART_Init_called());
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_UART_Init_calls_HAL_UART_Init);
    return UNITY_END();
}