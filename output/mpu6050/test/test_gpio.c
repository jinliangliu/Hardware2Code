#include "unity.h"
#include "mock_hal.h"
#include <string.h>

#include "../src/gpio.c"

void setUp(void) {
    mock_HAL_GPIO_Init_reset();
}

void tearDown(void) {}

void test_MX_GPIO_Init_should_call_HAL_for_all_pins(void) {
    MX_GPIO_Init();
    TEST_ASSERT_EQUAL_UINT32(4, mock_HAL_GPIO_Init_get_count());
}

void test_PB6_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 0;
    uint32_t expected_pin = GPIO_PIN_6;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

}
void test_PB7_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 1;
    uint32_t expected_pin = GPIO_PIN_7;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

}
void test_PC0_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 2;
    uint32_t expected_pin = GPIO_PIN_0;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

    TEST_ASSERT_EQUAL_UINT32(GPIO_MODE_OUTPUT_PP, mock_HAL_GPIO_Init_get_mode(idx));
}
void test_PC13_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 3;
    uint32_t expected_pin = GPIO_PIN_13;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

    TEST_ASSERT_EQUAL_UINT32(GPIO_MODE_IT_FALLING, mock_HAL_GPIO_Init_get_mode(idx));
    /* 验证对应 NVIC 中断线已使能 */
    TEST_ASSERT_TRUE(mock_HAL_NVIC_EnableIRQ_called_with(EXTI4_15_IRQn));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_MX_GPIO_Init_should_call_HAL_for_all_pins);
    RUN_TEST(test_PB6_configuration);
    RUN_TEST(test_PB7_configuration);
    RUN_TEST(test_PC0_configuration);
    RUN_TEST(test_PC13_configuration);
    return UNITY_END();
}