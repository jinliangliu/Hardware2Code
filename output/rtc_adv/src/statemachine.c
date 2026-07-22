#ifdef TEST
#include "mock_hal.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#endif

#include "statemachine.h"

#define STATE_IDLE 0
#define STATE_ACTIVE 1

static uint32_t current_state;

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
                /* 测试环境：调用本地桩函数 */
                extern void led_task_notify(void);
                led_task_notify();
#endif
                current_state = STATE_ACTIVE;
            }
            break;
        case STATE_ACTIVE:
            if (evt->id == EVENT_RTC_TICK) {
                current_state = STATE_IDLE;
            }
            break;
    }
}