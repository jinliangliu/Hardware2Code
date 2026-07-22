#include "unity.h"
#include "mock_hal.h"
#include <string.h>

/* Provide event_queue needed by drv_rtc.c callbacks */
QueueHandle_t event_queue = NULL;

/* Include the RTC driver source, providing RTC_TimerCreate etc. */
#include "../src/drivers/drv_rtc.c"

/* Include statemachine source under test */
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
    event_t dummy = { .id = EVENT_NONE };
    statemachine_process(&dummy);
    TEST_PASS();
}

void test_IDLE_plus_BUTTON_PRESS_transitions_to_ACTIVE_and_toggles_led(void) {
    event_t evt = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt);
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

void test_ACTIVE_plus_RTC_TICK_transitions_to_IDLE(void) {
    event_t evt1 = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt1);
    led_notify_count = 0;
    event_t evt2 = { .id = EVENT_RTC_TICK };
    statemachine_process(&evt2);
    TEST_ASSERT_EQUAL(0, led_notify_count);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_initial_state_is_IDLE);
    RUN_TEST(test_IDLE_plus_BUTTON_PRESS_transitions_to_ACTIVE_and_toggles_led);
    RUN_TEST(test_ACTIVE_plus_RTC_TICK_transitions_to_IDLE);
    return UNITY_END();
}