
#ifdef TEST
#include "mock_hal.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#endif

#include "statemachine.h"

/* ========== 全局变量 ========== */

/* ========== 区域级变量 ========== */
static uint32_t counter_count = 0;

/* ========== 状态枚举 ========== */
#define STATE_led_control_OFF 0
#define STATE_led_control_ON 1
#define STATE_counter_COUNTING 0

/* ========== 当前状态变量 ========== */
static uint32_t current_state_led_control;
static uint32_t current_state_counter;

/* ========== 历史状态变量 ========== */

/* ========== 定时器句柄与回调 ========== */


/* ========== 动作处理宏（单区域） ========== */

/* ========== 动作处理宏（并行区域，自动添加区域前缀） ========== */

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state_led_control = STATE_led_control_OFF;
    /* 执行初始状态的进入动作 */
    current_state_counter = STATE_counter_COUNTING;
    counter_count = 0;
    /* 执行初始状态的进入动作 */
}

/* ========== 事件处理 ========== */
void statemachine_process(event_t *evt) {
    /* 并行区域：每个区域独立处理事件 */
    {
        uint32_t *p_curr = &current_state_led_control;
        switch (*p_curr) {
        case STATE_led_control_OFF:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_BUTTON_PRESS)
            ) {
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif

                *p_curr = STATE_led_control_ON;
            }
            break;
        case STATE_led_control_ON:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_BUTTON_PRESS)
            ) {
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif

                *p_curr = STATE_led_control_OFF;
            }
            break;
        }
    }
    {
        uint32_t *p_curr = &current_state_counter;
        switch (*p_curr) {
        case STATE_counter_COUNTING:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_RTC_TICK)
            ) {
                    {
        counter_count++;
    }

                *p_curr = STATE_counter_COUNTING;
            }
            break;
        }
    }
}