#ifdef TEST
#include "mock_hal.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#endif

#include "statemachine.h"



/* ========== 全局变量 ========== */
static uint32_t button_count = 0;
static uint32_t stored = 0;

/* ========== 区域级变量 ========== */

/* ========== 状态枚举 ========== */
#define STATE_idle 0
#define STATE_reading 1
#define STATE_storing 2

/* ========== 当前状态变量 ========== */
static uint32_t current_state;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */



/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */

/* ========== 延迟动作定时器回调 ========== */

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state = STATE_idle;
    button_count = 0;
    stored = 0;
    /* 执行初始状态的进入动作并启动时间序列 */
    extern void led_task_notify(void);
    led_task_notify();

}

/* ========== 事件处理 ========== */
void statemachine_process(event_t *evt) {
    /* 单区域状态机（传统模式） */
    switch (current_state) {
    case STATE_idle:
        if (
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            
            current_state = STATE_reading;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                button_count++;
            }

        }
        break;
    case STATE_reading:
        if (
            (evt->id == EVENT_SENSOR_READY)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            
            current_state = STATE_storing;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                stored = button_count * 2;
            }

        }
        else if (
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            
            current_state = STATE_idle;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();

        }
        break;
    case STATE_storing:
        if (
            (evt->id == EVENT_STORE_DONE)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            
            current_state = STATE_idle;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();

        }
        break;
    }
}