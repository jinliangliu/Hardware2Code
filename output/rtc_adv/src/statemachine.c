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
static uint32_t press_count = 0;

/* ========== 区域级变量 ========== */

/* ========== 状态枚举 ========== */
#define STATE_IDLE 0
#define STATE_ACTIVE 1
#define STATE_RESET 2
#define STATE_TIMEOUT 3

/* ========== 当前状态变量 ========== */
static uint32_t current_state;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */



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

/* ========== 延迟动作定时器回调（单独生成句柄和回调） ========== */
static rtc_timer_handle_t defer_0_handle = NULL;
static void defer_0_cb(void *arg) {
    #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif

}

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state = STATE_IDLE;
    press_count = 0;
    /* 执行初始状态的进入动作并启动时间序列 */
        #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


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
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


            /* 停止当前状态的时间序列定时器 */
            RTC_TimerStop(IDLE_timeout_handle);
                    {
        uint32_t period = 3000;
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
        rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                               exit_timer_cb, NULL);
        exit_timer_handle = h;
        RTC_TimerStart(h);
    }


        }
        else if (
            (evt->id == EVENT_BUTTON_PRESS)
        ) {
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


            /* 停止当前状态的时间序列定时器 */
            RTC_TimerStop(IDLE_timeout_handle);
                    {
        press_count = 0;
    }


            current_state = STATE_RESET;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        else if (
            (evt->id == EVENT_TIMER_EXPIRED_IDLE_timeout)
        ) {
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


            /* 停止当前状态的时间序列定时器 */
            RTC_TimerStop(IDLE_timeout_handle);
            
            current_state = STATE_TIMEOUT;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    case STATE_ACTIVE:
        if (
            (evt->id == EVENT_RTC_TICK)
        ) {
                    RTC_TimerStop(exit_timer_handle);


            /* 停止当前状态的时间序列定时器 */
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


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
                    RTC_TimerStop(exit_timer_handle);


            /* 停止当前状态的时间序列定时器 */
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


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
            /* 停止当前状态的时间序列定时器 */
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


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
            /* 停止当前状态的时间序列定时器 */
            
            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


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