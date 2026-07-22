#include "unity.h"
#include "mock_hal.h"
#include <string.h>

/* 测试桩 */
typedef void * rtc_timer_handle_t;
typedef void (*rtc_timer_cb_t)(void *arg);
#define RTC_TIMER_MODE_ONE_SHOT     0
#define RTC_TIMER_MODE_PERIODIC     1

rtc_timer_handle_t RTC_TimerCreate(uint32_t period_ms, uint8_t mode, rtc_timer_cb_t callback, void *arg) {
    (void)period_ms; (void)mode; (void)callback; (void)arg;
    return (rtc_timer_handle_t)1;
}
void RTC_TimerStart(rtc_timer_handle_t handle) { (void)handle; }
void RTC_TimerStop(rtc_timer_handle_t handle) { (void)handle; }
void RTC_TimerDelete(rtc_timer_handle_t handle) { (void)handle; }
void RTC_ProcessTimers(void) {}

#include "../src/statemachine.c"

static int led_notify_count = 0;
void led_task_notify(void) {
    led_notify_count++;
}

void setUp(void) {
    led_notify_count = 0;
    statemachine_init();
}

void tearDown(void) {}

void test_initial_state_is_IDLE(void) {
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

void test_IDLE_plus_BUTTON_PRESS_transitions_to_ACTIVE_and_toggles_led(void) {
    event_t evt = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt);
    TEST_ASSERT_EQUAL(2, led_notify_count);
}

void test_ACTIVE_plus_RTC_TICK_transitions_to_IDLE(void) {
    event_t evt1 = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt1);
    led_notify_count = 0;
    event_t evt2 = { .id = EVENT_RTC_TICK };
    statemachine_process(&evt2);
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

void test_press_count_initial_zero(void) {
    event_t press = { .id = EVENT_BUTTON_PRESS };
    for (int i = 0; i < 4; i++) {
        press.id = EVENT_BUTTON_PRESS;
        statemachine_process(&press);
        event_t tick = { .id = EVENT_RTC_TICK };
        statemachine_process(&tick);
    }
    TEST_ASSERT_EQUAL(9, led_notify_count);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_initial_state_is_IDLE);
    RUN_TEST(test_IDLE_plus_BUTTON_PRESS_transitions_to_ACTIVE_and_toggles_led);
    RUN_TEST(test_ACTIVE_plus_RTC_TICK_transitions_to_IDLE);
    RUN_TEST(test_press_count_initial_zero);
    return UNITY_END();
}