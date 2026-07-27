#include "unity.h"
#include "mock_hal.h"
#include <string.h>

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

void test_led_toggle_on_button_press(void) {
    event_t evt = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt);
    TEST_ASSERT_EQUAL(1, led_notify_count);
    statemachine_process(&evt);
    TEST_ASSERT_EQUAL(2, led_notify_count);
}

void test_counter_increments_on_rtc_tick(void) {
    for (int i = 0; i < 10; i++) {
        event_t evt = { .id = EVENT_RTC_TICK };
        statemachine_process(&evt);
    }
    TEST_PASS();
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_led_toggle_on_button_press);
    RUN_TEST(test_counter_increments_on_rtc_tick);
    return UNITY_END();
}