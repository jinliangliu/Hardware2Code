#ifdef TEST
#include "mock_hal.h"
#include "drv_rtc.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#include "drv_rtc.h"
#endif

#include "statemachine.h"



/* ========== 全局变量 ========== */

/* ========== 区域级变量 ========== */

/* ========== 状态枚举 ========== */
#define STATE_DISCONNECTED 0
#define STATE_CONNECTING 1
#define STATE_CONNECTED 2

/* ========== 当前状态变量 ========== */
static uint32_t current_state;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */



/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */
static rtc_timer_handle_t CONNECTING_timeout_handle = NULL;
static void CONNECTING_timeout_cb(void *arg) {
    event_t evt = { .id = EVENT_TIMER_EXPIRED_CONNECTING_timeout, .param = 0 };
    statemachine_process(&evt);
}

/* ========== 延迟动作定时器回调 ========== */

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state = STATE_DISCONNECTED;
    /* 执行初始状态的进入动作并启动时间序列 */
    extern void led_task_notify(void);
    led_task_notify();

}

/* ========== 事件处理 ========== */
void statemachine_process(event_t *evt) {
    /* 单区域状态机（传统模式） */
    switch (current_state) {
    case STATE_DISCONNECTED:
        if (
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_CONNECTING;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                uint32_t period = 10000;
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       CONNECTING_timeout_cb, NULL);
                CONNECTING_timeout_handle = h;
                RTC_TimerStart(h);
            }
        }
        break;
    case STATE_CONNECTING:
        if (
            (evt->id == EVENT_TIMER_EXPIRED_CONNECTING_timeout)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            if (CONNECTING_timeout_handle) {
                RTC_TimerStop(CONNECTING_timeout_handle);
                RTC_TimerDelete(CONNECTING_timeout_handle);
                CONNECTING_timeout_handle = NULL;
            }
            /* 停止并删除所有 defer 定时器 */
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_CONNECTED;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    case STATE_CONNECTED:
        if (
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_DISCONNECTED;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();

        }
        break;
    }
}