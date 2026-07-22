#include "unity.h"
#include "mock_hal.h"
#include <string.h>

#include "../src/drivers/drv_pwm.c"

static bool pwm_init_called = false;
void HAL_TIM_PWM_Init(TIM_HandleTypeDef *htim) { (void)htim; pwm_init_called = true; }

void setUp(void) { pwm_init_called = false; }
void tearDown(void) {}

void test_PWM_Init_calls_HAL_TIM_PWM_Init(void) {
    PWM_Init();
    TEST_ASSERT_TRUE(pwm_init_called);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_PWM_Init_calls_HAL_TIM_PWM_Init);
    return UNITY_END();
}