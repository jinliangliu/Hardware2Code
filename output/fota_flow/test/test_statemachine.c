#include "unity.h"
#include "mock_hal.h"
#include <string.h>

/* Test stubs */
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

void test_initial_state_actions(void) {
    TEST_ASSERT_EQUAL(0, led_notify_count);
}

void test_IDLE_to_WAIT_PATCH_on_BUTTON_PRESS(void) {
    event_t evt = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt);
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

void test_WAIT_PATCH_to_IDLE_on_TIMER_EXPIRED_WAIT_PATCH_timeout(void) {
    event_t evt_fwd = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt_fwd);
    led_notify_count = 0;
    event_t evt_back = { .id = EVENT_TIMER_EXPIRED_WAIT_PATCH_timeout };
    statemachine_process(&evt_back);
    TEST_ASSERT_EQUAL(0, led_notify_count);
}
void test_ERROR_to_IDLE_on_BUTTON_PRESS(void) {
    event_t evt_fwd = { .id = EVENT_FOTA_ERROR };
    statemachine_process(&evt_fwd);
    led_notify_count = 0;
    event_t evt_back = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt_back);
    TEST_ASSERT_EQUAL(1, led_notify_count);
}
void test_SUCCESS_to_IDLE_on_BUTTON_PRESS(void) {
    event_t evt_fwd = { .id = EVENT_FOTA_APPLY_OK };
    statemachine_process(&evt_fwd);
    led_notify_count = 0;
    event_t evt_back = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt_back);
    TEST_ASSERT_EQUAL(1, led_notify_count);
}
void test_ERROR_to_IDLE_on_BUTTON_PRESS(void) {
    event_t evt_fwd = { .id = EVENT_FOTA_ERROR };
    statemachine_process(&evt_fwd);
    led_notify_count = 0;
    event_t evt_back = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt_back);
    TEST_ASSERT_EQUAL(1, led_notify_count);
}
void test_ERROR_to_IDLE_on_BUTTON_PRESS(void) {
    event_t evt_fwd = { .id = EVENT_FOTA_ERROR };
    statemachine_process(&evt_fwd);
    led_notify_count = 0;
    event_t evt_back = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt_back);
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

void test_roundtrip_cycle(void) {
    for (int i = 0; i < 4; i++) {
        event_t evt_fwd = { .id = EVENT_BUTTON_PRESS };
        statemachine_process(&evt_fwd);
        event_t evt_back = { .id = EVENT_TIMER_EXPIRED_WAIT_PATCH_timeout };
        statemachine_process(&evt_back);
    }
    TEST_ASSERT_EQUAL(4, led_notify_count);
}
void test_roundtrip_cycle(void) {
    for (int i = 0; i < 4; i++) {
        event_t evt_fwd = { .id = EVENT_FOTA_ERROR };
        statemachine_process(&evt_fwd);
        event_t evt_back = { .id = EVENT_BUTTON_PRESS };
        statemachine_process(&evt_back);
    }
    TEST_ASSERT_EQUAL(8, led_notify_count);
}
void test_roundtrip_cycle(void) {
    for (int i = 0; i < 4; i++) {
        event_t evt_fwd = { .id = EVENT_FOTA_APPLY_OK };
        statemachine_process(&evt_fwd);
        event_t evt_back = { .id = EVENT_BUTTON_PRESS };
        statemachine_process(&evt_back);
    }
    TEST_ASSERT_EQUAL(8, led_notify_count);
}
void test_roundtrip_cycle(void) {
    for (int i = 0; i < 4; i++) {
        event_t evt_fwd = { .id = EVENT_FOTA_ERROR };
        statemachine_process(&evt_fwd);
        event_t evt_back = { .id = EVENT_BUTTON_PRESS };
        statemachine_process(&evt_back);
    }
    TEST_ASSERT_EQUAL(8, led_notify_count);
}
void test_roundtrip_cycle(void) {
    for (int i = 0; i < 4; i++) {
        event_t evt_fwd = { .id = EVENT_FOTA_ERROR };
        statemachine_process(&evt_fwd);
        event_t evt_back = { .id = EVENT_BUTTON_PRESS };
        statemachine_process(&evt_back);
    }
    TEST_ASSERT_EQUAL(8, led_notify_count);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_initial_state_actions);
    RUN_TEST(test_IDLE_to_WAIT_PATCH_on_BUTTON_PRESS);
    RUN_TEST(test_WAIT_PATCH_to_VERIFY_on_FOTA_PATCH_COMPLETE);
    RUN_TEST(test_WAIT_PATCH_to_ERROR_on_FOTA_ERROR);
    RUN_TEST(test_WAIT_PATCH_to_IDLE_on_TIMER_EXPIRED_WAIT_PATCH_timeout);
    RUN_TEST(test_VERIFY_to_APPLY_on_FOTA_VERIFY_OK);
    RUN_TEST(test_VERIFY_to_RETRY_on_FOTA_VERIFY_FAIL);
    RUN_TEST(test_VERIFY_to_RETRY_on_TIMER_EXPIRED_verify_timeout);
    RUN_TEST(test_APPLY_to_SUCCESS_on_FOTA_APPLY_OK);
    RUN_TEST(test_APPLY_to_ERROR_on_FOTA_ERROR);
    RUN_TEST(test_RETRY_to_VERIFY_on_FOTA_PATCH_COMPLETE);
    RUN_TEST(test_RETRY_to_ERROR_on_FOTA_ERROR);
    RUN_TEST(test_SUCCESS_to_IDLE_on_BUTTON_PRESS);
    RUN_TEST(test_ERROR_to_IDLE_on_BUTTON_PRESS);
    RUN_TEST(test_WAIT_PATCH_to_IDLE_on_TIMER_EXPIRED_WAIT_PATCH_timeout);
    RUN_TEST(test_ERROR_to_IDLE_on_BUTTON_PRESS);
    RUN_TEST(test_SUCCESS_to_IDLE_on_BUTTON_PRESS);
    RUN_TEST(test_ERROR_to_IDLE_on_BUTTON_PRESS);
    RUN_TEST(test_ERROR_to_IDLE_on_BUTTON_PRESS);
    RUN_TEST(test_roundtrip_cycle);
    return UNITY_END();
}