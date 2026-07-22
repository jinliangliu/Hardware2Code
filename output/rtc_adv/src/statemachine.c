#ifdef TEST
#include "mock_hal.h"
#include "drv_rtc.h"          /* 为了 rtc_timer_handle_t 等类型 */
#else
#include "FreeRTOS.h"
#include "task.h"
#include "drv_rtc.h"
#endif

#include "statemachine.h"

#define STATE_IDLE 0
#define STATE_ACTIVE 1

static uint32_t current_state;

/* 定时器句柄 */
static rtc_timer_handle_t delay_timer_handle = NULL;

/* 定时器回调 */
static void delay_timer_cb(void *arg) {
    event_t evt = { .id = EVENT_TIMER_EXPIRED_delay_timer, .param = 0 };
    statemachine_process(&evt);
}

void statemachine_init(void) {
    current_state = STATE_IDLE;
}

void statemachine_process(event_t *evt) {
    switch (current_state) {
        case STATE_IDLE:
            if (evt->id == EVENT_BUTTON_PRESS) {
#ifndef TEST
                led_task_notify();
#else
                extern void led_task_notify(void);
                led_task_notify();
#endif
                {
                    uint32_t period = 5000;
                    rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                           delay_timer_cb, NULL);
                    delay_timer_handle = h;
                    RTC_TimerStart(h);
                }
                current_state = STATE_ACTIVE;
            }
            break;
        case STATE_ACTIVE:
            if (evt->id == EVENT_TIMER_EXPIRED_delay_timer) {
#ifndef TEST
                led_task_notify();
#else
                extern void led_task_notify(void);
                led_task_notify();
#endif
                current_state = STATE_IDLE;
            }
            break;
    }
}