#ifdef TEST
#include "mock_hal.h"
#include "drv_rtc.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#include "drv_rtc.h"
#endif

#include "statemachine.h"



/* ========== 自定义类型定义 / Custom Type Definitions ========== */
/* ========== 全局变量 ========== */
static uint32_t press_count = 0;

/* ========== 区域级变量 ========== */

/* ========== 状态枚举 ========== */
#define STATE_IDLE 2089173635
#define STATE_ACTIVE 610930977
#define STATE_RESET 233970152
#define STATE_TIMEOUT 1975300844

/* ========== 当前状态变量 ========== */
static uint32_t current_state;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */
static rtc_timer_handle_t IDLE_timeout_handle = NULL;
static void IDLE_timeout_cb(void *arg) {
    event_t evt = { .id = EVENT_TIMER_EXPIRED_IDLE_timeout, .param = 0 };
    statemachine_process(&evt);
}
static rtc_timer_handle_t exit_timer_handle = NULL;
static void exit_timer_cb(void *arg) {
    event_t evt = { .id = EVENT_TIMER_EXPIRED_exit_timer, .param = 0 };
    statemachine_process(&evt);
}

/* ========== 延迟动作定时器回调 ========== */
static rtc_timer_handle_t defer_0_handle = NULL;
static void defer_0_cb(void *arg) {
    extern void led_task_notify(void);
    led_task_notify();

}

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state = STATE_IDLE;
    press_count = 0;
    /* 执行初始状态的进入动作并启动时间序列 */
    extern void led_task_notify(void);
    led_task_notify();

    {
        uint32_t period = 5000;
        rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                               IDLE_timeout_cb, NULL);
        IDLE_timeout_handle = h;
        RTC_TimerStart(h);
    }
}

/* ========== 事件处理 ========== */
void statemachine_process(event_t *evt) {
    /* 单区域状态机（传统模式） */
    switch (current_state) {
    case STATE_IDLE:
        if (
            (press_count < 3) &&
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
            extern void led_task_notify(void);
            led_task_notify();

            /* 停止并删除当前状态的超时定时器 */
            if (IDLE_timeout_handle) {
                RTC_TimerStop(IDLE_timeout_handle);
                RTC_TimerDelete(IDLE_timeout_handle);
                IDLE_timeout_handle = NULL;
            }
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            {
                uint32_t period = 3000;
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
                press_count++;
            }

            current_state = STATE_ACTIVE;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                uint32_t period = 3000;
                if (exit_timer_handle) {
                    RTC_TimerDelete(exit_timer_handle);
                    exit_timer_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       exit_timer_cb, NULL);
                exit_timer_handle = h;
                RTC_TimerStart(h);
            }

        }
        else if (
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
            extern void led_task_notify(void);
            led_task_notify();

            /* 停止并删除当前状态的超时定时器 */
            if (IDLE_timeout_handle) {
                RTC_TimerStop(IDLE_timeout_handle);
                RTC_TimerDelete(IDLE_timeout_handle);
                IDLE_timeout_handle = NULL;
            }
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            {
                press_count = 0;
            }

            current_state = STATE_RESET;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        else if (
            (evt->id == EVENT_TIMER_EXPIRED_IDLE_timeout)
        ) {
            extern void led_task_notify(void);
            led_task_notify();

            /* 停止并删除当前状态的超时定时器 */
            if (IDLE_timeout_handle) {
                RTC_TimerStop(IDLE_timeout_handle);
                RTC_TimerDelete(IDLE_timeout_handle);
                IDLE_timeout_handle = NULL;
            }
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            
            current_state = STATE_TIMEOUT;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    case STATE_ACTIVE:
        if (
            (evt->id == EVENT_RTC_TICK)
        ) {
            {
                if (exit_timer_handle) {
                    RTC_TimerStop(exit_timer_handle);
                    RTC_TimerDelete(exit_timer_handle);
                    exit_timer_handle = NULL;
                }
            }

            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();

            {
                uint32_t period = 5000;
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       IDLE_timeout_cb, NULL);
                IDLE_timeout_handle = h;
                RTC_TimerStart(h);
            }
        }
        else if (
            (evt->id == EVENT_TIMER_EXPIRED_exit_timer)
        ) {
            {
                if (exit_timer_handle) {
                    RTC_TimerStop(exit_timer_handle);
                    RTC_TimerDelete(exit_timer_handle);
                    exit_timer_handle = NULL;
                }
            }

            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();

            {
                uint32_t period = 5000;
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       IDLE_timeout_cb, NULL);
                IDLE_timeout_handle = h;
                RTC_TimerStart(h);
            }
        }
        break;
    case STATE_RESET:
        if (
            (evt->id == EVENT_RTC_TICK)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();

            {
                uint32_t period = 5000;
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       IDLE_timeout_cb, NULL);
                IDLE_timeout_handle = h;
                RTC_TimerStart(h);
            }
        }
        break;
    case STATE_TIMEOUT:
        if (
            (evt->id == EVENT_RTC_TICK)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            /* 停止并删除所有 defer 定时器 */
            if (defer_0_handle) {
                RTC_TimerStop(defer_0_handle);
                RTC_TimerDelete(defer_0_handle);
                defer_0_handle = NULL;
            }
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
            extern void led_task_notify(void);
            led_task_notify();

            {
                uint32_t period = 5000;
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       IDLE_timeout_cb, NULL);
                IDLE_timeout_handle = h;
                RTC_TimerStart(h);
            }
        }
        break;
    }
}