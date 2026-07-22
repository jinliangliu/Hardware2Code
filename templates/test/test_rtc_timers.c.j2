#include "unity.h"
#include "mock_hal.h"
#include <string.h>

QueueHandle_t event_queue = NULL; /* 与 test_rtc 相同 */
#include "../src/drivers/drv_rtc.c"

static int callback_count = 0;
void test_timer_cb(void *arg) {
    callback_count++;
}

void setUp(void) {
    callback_count = 0;
    /* 初始化 RTC（使用 mock） */
    RTC_Init();
}

void tearDown(void) {}

void test_CreateMultipleTimers(void) {
    rtc_timer_handle_t t1 = RTC_TimerCreate(1000, RTC_TIMER_MODE_ONE_SHOT, NULL, NULL);
    rtc_timer_handle_t t2 = RTC_TimerCreate(2000, RTC_TIMER_MODE_PERIODIC, test_timer_cb, NULL);
    TEST_ASSERT_NOT_NULL(t1);
    TEST_ASSERT_NOT_NULL(t2);
    RTC_TimerDelete(t2);
    RTC_TimerDelete(t1);
}

void test_PeriodicTimerTriggersMultipleTimes(void) {
    rtc_timer_handle_t t = RTC_TimerCreate(100, RTC_TIMER_MODE_PERIODIC, test_timer_cb, NULL);
    RTC_TimerStart(t);
    /* 模拟多次 RTC tick 处理（直接调用 RTC_ProcessTimers 多次） */
    for (int i = 0; i < 15; i++) { /* 15 * 100ms = 1500ms，应触发 ~10 次 */
        RTC_ProcessTimers();
    }
    RTC_TimerStop(t);
    TEST_ASSERT_GREATER_THAN(5, callback_count); /* 至少触发 5 次 */
    RTC_TimerDelete(t);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_CreateMultipleTimers);
    RUN_TEST(test_PeriodicTimerTriggersMultipleTimes);
    return UNITY_END();
}   