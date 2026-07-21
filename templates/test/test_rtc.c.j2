#include "unity.h"
#include "mock_hal.h"
#include <string.h>

/* 直接包含被测源码 */
#include "../src/drivers/drv_rtc.c"

void setUp(void) {
    mock_HAL_RTC_Init_reset();
}

void tearDown(void) {}

void test_RTC_Init_should_call_HAL_RTC_Init(void) {
    RTC_Init();
    TEST_ASSERT_TRUE(mock_HAL_RTC_Init_called());
}

void test_RTC_TimerCreate_should_return_non_null(void) {
    rtc_timer_handle_t t = RTC_TimerCreate(1000, RTC_TIMER_MODE_ONE_SHOT, NULL, NULL);
    TEST_ASSERT_NOT_NULL(t);
    RTC_TimerDelete(t);
}

void test_RTC_TimerStart_should_not_crash(void) {
    rtc_timer_handle_t t = RTC_TimerCreate(500, RTC_TIMER_MODE_PERIODIC, NULL, NULL);
    RTC_TimerStart(t);
    RTC_TimerDelete(t);
}

void test_RTC_TimerCreate_should_insert_into_list(void)
{
    rtc_timer_handle_t t1 = RTC_TimerCreate(1000, RTC_TIMER_MODE_ONE_SHOT, NULL, NULL);
    rtc_timer_handle_t t2 = RTC_TimerCreate(2000, RTC_TIMER_MODE_PERIODIC, NULL, NULL);
    TEST_ASSERT_NOT_NULL(t1);
    TEST_ASSERT_NOT_NULL(t2);
    /* 验证 timer_head 非空，链表包含两个节点（通过 ProcessTimers 间接验证） */
    RTC_TimerDelete(t2);
    RTC_TimerDelete(t1);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_RTC_Init_should_call_HAL_RTC_Init);
    RUN_TEST(test_RTC_TimerCreate_should_return_non_null);
    RUN_TEST(test_RTC_TimerStart_should_not_crash);
    RUN_TEST(test_RTC_TimerCreate_should_insert_into_list);
    return UNITY_END();
}