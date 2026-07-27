#include "unity.h"
#include "mock_hal.h"
#include <string.h>

/* Provide stubs for RTC timer subsystem (defer timers won't fire in test) */
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

/* 提供 event_queue 供 defer 使用 */
QueueHandle_t event_queue = NULL;
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


/* Test: BUTTON_PRESS enters DEEP substate, auto-enters first sub-state */
void test_enter_substate_initial_step(void) {
    event_t evt = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt);
    /* IDLE→DEEP transition: toggle_led fired once */
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

/* Test: First sub-state transitions via defer event */
void test_substate_step1_to_step2(void) {
    /* Enter DEEP / step 1 */
    event_t press = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&press);
    /* Send RTC_TICK (what defer would publish after 1000ms) */
    event_t step_evt = { .id = EVENT_RTC_TICK };
    statemachine_process(&step_evt);
    /* No toggle_led on step 1→step 2 transition */
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

/* Test: return action from last sub-state triggers parent exit transition */
void test_substate_return_to_idle(void) {
    /* Navigate: IDLE → DEEP → step 1 → step 2 */
    event_t press = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&press);
    event_t evt1 = { .id = EVENT_RTC_TICK };
    statemachine_process(&evt1);
    /* Send RTC_TICK → return → DEEP transition → IDLE */
    event_t evt2 = { .id = EVENT_RTC_TICK };
    statemachine_process(&evt2);
    /* return → pop substate → parent RETURN→IDLE transition → toggle_led */
    TEST_ASSERT_EQUAL(2, led_notify_count);
}

/* Test: After return to IDLE, further events have no effect */
void test_idle_after_return_is_stable(void) {
    /* Navigate to IDLE via substate chain */
    event_t press = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&press);
    event_t evt1 = { .id = EVENT_RTC_TICK };
    statemachine_process(&evt1);
    event_t evt2 = { .id = EVENT_RTC_TICK };
    statemachine_process(&evt2);
    led_notify_count = 0;
    /* RTC_TICK should have no effect in IDLE */
    event_t tick = { .id = EVENT_RTC_TICK };
    statemachine_process(&tick);
    TEST_ASSERT_EQUAL(0, led_notify_count);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_enter_substate_initial_step);
    RUN_TEST(test_substate_step1_to_step2);
    RUN_TEST(test_substate_return_to_idle);
    RUN_TEST(test_idle_after_return_is_stable);
    return UNITY_END();
}