#include "unity.h"
#include "mock_hal.h"
#include <string.h>

#include "../src/drivers/drv_rs485_1.c"

extern void mock_HAL_GPIO_WritePin_reset(void);
extern uint32_t mock_HAL_GPIO_WritePin_get_last_state(void);
extern bool mock_HAL_UART_Transmit_called(void);
extern void mock_HAL_UART_Transmit_reset(void);
extern bool mock_HAL_UART_Receive_called(void);
extern void mock_HAL_UART_Receive_reset(void);

void setUp(void)
{
    mock_HAL_GPIO_WritePin_reset();
    mock_HAL_UART_Transmit_reset();
    mock_HAL_UART_Receive_reset();
}

void tearDown(void) {}

void test_rs485_init_sets_rx_mode(void)
{
    rs485_init(NULL, (GPIO_TypeDef *)0, GPIO_PIN_5);
    TEST_ASSERT_EQUAL(GPIO_PIN_RESET, mock_HAL_GPIO_WritePin_get_last_state());
}

void test_rs485_set_tx_pulls_de_high(void)
{
    rs485_set_tx();
    TEST_ASSERT_EQUAL(GPIO_PIN_SET, mock_HAL_GPIO_WritePin_get_last_state());
}

void test_rs485_set_rx_pulls_de_low(void)
{
    rs485_set_rx();
    TEST_ASSERT_EQUAL(GPIO_PIN_RESET, mock_HAL_GPIO_WritePin_get_last_state());
}

void test_rs485_send_calls_uart_transmit(void)
{
    uint8_t data[] = {0x01, 0x02};
    rs485_send(data, 2);
    TEST_ASSERT_TRUE(mock_HAL_UART_Transmit_called());
}

void test_rs485_recv_calls_uart_receive(void)
{
    uint8_t data[8];
    rs485_recv(data, 8, 100);
    TEST_ASSERT_TRUE(mock_HAL_UART_Receive_called());
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_rs485_init_sets_rx_mode);
    RUN_TEST(test_rs485_set_tx_pulls_de_high);
    RUN_TEST(test_rs485_set_rx_pulls_de_low);
    RUN_TEST(test_rs485_send_calls_uart_transmit);
    RUN_TEST(test_rs485_recv_calls_uart_receive);
    return UNITY_END();
}