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
#define STATE_IDLE 0
#define STATE_PLAYING 1

/* ========== 当前状态变量 ========== */
static uint32_t current_state;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */



/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */
static rtc_timer_handle_t PLAYING_timeout_handle = NULL;
static void PLAYING_timeout_cb(void *arg) {
    event_t evt = { .id = EVENT_TIMER_EXPIRED_PLAYING_timeout, .param = 0 };
    statemachine_process(&evt);
}

/* ========== 延迟动作定时器回调 ========== */
static rtc_timer_handle_t defer_0_handle = NULL;
static void defer_0_cb(void *arg) {
    extern void led_task_notify(void);
    led_task_notify();

}
static rtc_timer_handle_t defer_1_handle = NULL;
static void defer_1_cb(void *arg) {
    extern void led_task_notify(void);
    led_task_notify();

}
static rtc_timer_handle_t defer_2_handle = NULL;
static void defer_2_cb(void *arg) {
    extern void led_task_notify(void);
    led_task_notify();

}

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state = STATE_IDLE;
    /* 执行初始状态的进入动作并启动时间序列 */
}

/* ========== 事件处理 ========== */
void statemachine_process(event_t *evt) {
    /* 单区域状态机（传统模式） */
    switch (current_state) {
    case STATE_IDLE:
        if (
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            if (defer_1_handle) {
                RTC_TimerStop(defer_1_handle);
                RTC_TimerDelete(defer_1_handle);
                defer_1_handle = NULL;
            }
            if (defer_2_handle) {
                RTC_TimerStop(defer_2_handle);
                RTC_TimerDelete(defer_2_handle);
                defer_2_handle = NULL;
            }
            
            current_state = STATE_PLAYING;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();
            {
                uint32_t period = 1000;
                if (defer_0_handle) {
                    RTC_TimerDelete(defer_0_handle);
                    defer_0_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       defer_0_cb, NULL);
                defer_0_handle = h;
                RTC_TimerStart(h);
            }
            {
                uint32_t period = 2000;
                if (defer_1_handle) {
                    RTC_TimerDelete(defer_1_handle);
                    defer_1_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       defer_1_cb, NULL);
                defer_1_handle = h;
                RTC_TimerStart(h);
            }
            {
                uint32_t period = 3000;
                if (defer_2_handle) {
                    RTC_TimerDelete(defer_2_handle);
                    defer_2_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       defer_2_cb, NULL);
                defer_2_handle = h;
                RTC_TimerStart(h);
            }

            {
                uint32_t period = 5000;
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       PLAYING_timeout_cb, NULL);
                PLAYING_timeout_handle = h;
                RTC_TimerStart(h);
            }
        }
        break;
    case STATE_PLAYING:
        if (
            (evt->id == EVENT_TIMER_EXPIRED_PLAYING_timeout)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            if (PLAYING_timeout_handle) {
                RTC_TimerStop(PLAYING_timeout_handle);
                RTC_TimerDelete(PLAYING_timeout_handle);
                PLAYING_timeout_handle = NULL;
            }
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            if (defer_1_handle) {
                RTC_TimerStop(defer_1_handle);
                RTC_TimerDelete(defer_1_handle);
                defer_1_handle = NULL;
            }
            if (defer_2_handle) {
                RTC_TimerStop(defer_2_handle);
                RTC_TimerDelete(defer_2_handle);
                defer_2_handle = NULL;
            }
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    }
}