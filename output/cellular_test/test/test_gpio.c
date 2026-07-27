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
    TEST_ASSERT_EQUAL_UINT32(5, mock_HAL_GPIO_Init_get_count());
}

void test_PA2_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 0;
    uint32_t expected_pin = GPIO_PIN_2;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

}
void test_PA3_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 1;
    uint32_t expected_pin = GPIO_PIN_3;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

}
void test_PC6_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 2;
    uint32_t expected_pin = GPIO_PIN_6;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

}
void test_PC7_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 3;
    uint32_t expected_pin = GPIO_PIN_7;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

}
void test_PC0_configuration(void) {
    MX_GPIO_Init();
    /* 获取该引脚对应索引的配置（按YAML顺序） */
    uint32_t idx = 4;
    uint32_t expected_pin = GPIO_PIN_0;
    uint32_t actual_pin = mock_HAL_GPIO_Init_get_pin(idx);
    TEST_ASSERT_EQUAL_HEX32(expected_pin, actual_pin);

    TEST_ASSERT_EQUAL_UINT32(GPIO_MODE_OUTPUT_PP, mock_HAL_GPIO_Init_get_mode(idx));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_MX_GPIO_Init_should_call_HAL_for_all_pins);
    RUN_TEST(test_PA2_configuration);
    RUN_TEST(test_PA3_configuration);
    RUN_TEST(test_PC6_configuration);
    RUN_TEST(test_PC7_configuration);
    RUN_TEST(test_PC0_configuration);
    return UNITY_END();
}