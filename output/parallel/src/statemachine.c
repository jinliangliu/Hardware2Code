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

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */




/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */

/* ========== 延迟动作定时器回调 ========== */

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state_led_control = STATE_led_control_OFF;
    /* 执行初始状态的进入动作并启动时间序列 */
    current_state_counter = STATE_counter_COUNTING;
    counter_count = 0;
    /* 执行初始状态的进入动作并启动时间序列 */
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
                /* 停止当前状态的时间序列定时器 */
                /* 停止所有 defer 定时器 */
                        extern void led_task_notify(void);
    led_task_notify();


                *p_curr = STATE_led_control_ON;
                /* 执行目标状态的进入动作并启动时间序列 */
            }
            break;
        case STATE_led_control_ON:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_BUTTON_PRESS)
            ) {
                /* 停止当前状态的时间序列定时器 */
                /* 停止所有 defer 定时器 */
                        extern void led_task_notify(void);
    led_task_notify();


                *p_curr = STATE_led_control_OFF;
                /* 执行目标状态的进入动作并启动时间序列 */
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
                /* 停止当前状态的时间序列定时器 */
                /* 停止所有 defer 定时器 */
                        {
        counter_count++;
    }


                *p_curr = STATE_counter_COUNTING;
                /* 执行目标状态的进入动作并启动时间序列 */
            }
            break;
        }
    }
}