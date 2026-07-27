#ifdef TEST
#include "mock_hal.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#endif

#include "statemachine.h"



/* ========== 全局变量 ========== */

/* ========== 区域级变量 ========== */

/* ========== 状态枚举 ========== */
#define STATE_button_region_UP 0
#define STATE_button_region_DOWN 1
#define STATE_led_region_OFF 0
#define STATE_led_region_ON 1

/* ========== 当前状态变量 ========== */
static uint32_t current_state_button_region;
static uint32_t current_state_led_region;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */




/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */

/* ========== 延迟动作定时器回调 ========== */

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state_button_region = STATE_button_region_UP;
    /* 执行初始状态的进入动作并启动时间序列 */
    current_state_led_region = STATE_led_region_OFF;
    /* 执行初始状态的进入动作并启动时间序列 */
}

/* ========== 事件处理 ========== */
void statemachine_process(event_t *evt) {
    /* 并行区域：每个区域独立处理事件 */
    {
        uint32_t *p_curr = &current_state_button_region;
        switch (*p_curr) {
        case STATE_button_region_UP:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_BUTTON_PRESS)
            ) {
                /* 停止并删除当前状态的超时定时器 */
                /* 停止并删除所有 defer 定时器 */
                {
                    event_t evt_pub = { .id = EVENT_LED_ON, .param = 0 };
                    xQueueSend(event_queue, &evt_pub, 0);
                }

                *p_curr = STATE_button_region_DOWN;
                /* 执行目标状态的进入动作并启动时间序列 */
            }
            break;
        case STATE_button_region_DOWN:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_BUTTON_PRESS)
            ) {
                /* 停止并删除当前状态的超时定时器 */
                /* 停止并删除所有 defer 定时器 */
                {
                    event_t evt_pub = { .id = EVENT_LED_OFF, .param = 0 };
                    xQueueSend(event_queue, &evt_pub, 0);
                }

                *p_curr = STATE_button_region_UP;
                /* 执行目标状态的进入动作并启动时间序列 */
            }
            break;
        }
    }
    {
        uint32_t *p_curr = &current_state_led_region;
        switch (*p_curr) {
        case STATE_led_region_OFF:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_LED_ON)
            ) {
                /* 停止并删除当前状态的超时定时器 */
                /* 停止并删除所有 defer 定时器 */
                extern void led_task_notify(void);
                led_task_notify();

                *p_curr = STATE_led_region_ON;
                /* 执行目标状态的进入动作并启动时间序列 */
            }
            break;
        case STATE_led_region_ON:
            /* 父状态转换 */
            if (
                (evt->id == EVENT_LED_OFF)
            ) {
                /* 停止并删除当前状态的超时定时器 */
                /* 停止并删除所有 defer 定时器 */
                extern void led_task_notify(void);
                led_task_notify();

                *p_curr = STATE_led_region_OFF;
                /* 执行目标状态的进入动作并启动时间序列 */
            }
            break;
        }
    }
}