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
    /* 初始化过程会执行 IDLE 的 on_entry，导致一次 LED 通知 */
}

void tearDown(void) {}

/* 初始状态 IDLE，初始化时已执行 on_entry，LED 计数应为 1 */
void test_initial_state_is_IDLE(void) {
    TEST_ASSERT_EQUAL(1, led_notify_count);
}

/* IDLE -> ACTIVE: 离开 IDLE 触发 on_exit (toggle_led) 一次，ACTIVE on_entry 无 toggle_led，所以额外加 1 */
void test_IDLE_plus_BUTTON_PRESS_transitions_to_ACTIVE_and_toggles_led(void) {
    event_t evt = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt);
    TEST_ASSERT_EQUAL(2, led_notify_count);  // 初始 1 + 离开 IDLE on_exit 1 = 2
}

/* ACTIVE -> IDLE: ACTIVE on_exit (stop_timer, 不影响), IDLE on_entry (toggle_led) 一次，所以 LED 再加 1 */
void test_ACTIVE_plus_RTC_TICK_transitions_to_IDLE(void) {
    event_t evt1 = { .id = EVENT_BUTTON_PRESS };
    statemachine_process(&evt1);  // 进入 ACTIVE，LED 变为 2
    led_notify_count = 0;   /* 清零 */
    event_t evt2 = { .id = EVENT_RTC_TICK };
    statemachine_process(&evt2);  // 返回 IDLE，IDLE on_entry 触发一次 toggle_led
    TEST_ASSERT_EQUAL(1, led_notify_count);  // 只有一次 on_entry
}

/* 四次按键循环，每次循环：进入 ACTIVE (IDLE on_exit 1) + 返回 IDLE (IDLE on_entry 1) = 2 次 LED。
   四次循环共 8 次，加上初始化 on_entry 1 次，总共 9 次？但注意每次循环结束后状态回到 IDLE，
   下次循环开始时已经在 IDLE，不会再执行 on_entry。实际上测试循环中：
   for i=0..3:
     statemachine_process(&press)  // 离开 IDLE -> on_exit 1 次
     statemachine_process(&tick)   // 回到 IDLE -> on_entry 1 次
   所以每次循环 2 次，4 次循环 8 次。加上初始化 on_entry 1 次，共计 9 次。
   第四次按键后（i=3），press 进入 RESET，RESET 没有 on_exit/on_entry 的 LED 动作，但 press 事件本身不产生 LED，而 tick 回到 IDLE 触发 on_entry 1 次。所以 9 次。 */
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