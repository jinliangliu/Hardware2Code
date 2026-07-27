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
static uint32_t upgrade_attempts = 0;

/* ========== 区域级变量 ========== */

/* ========== 状态枚举 ========== */
#define STATE_IDLE 0
#define STATE_WAIT_PATCH 1
#define STATE_VERIFY 2
#define STATE_APPLY 3
#define STATE_RETRY 4
#define STATE_SUCCESS 5
#define STATE_ERROR 6

/* ========== 当前状态变量 ========== */
static uint32_t current_state;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */



/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */
static rtc_timer_handle_t WAIT_PATCH_timeout_handle = NULL;
static void WAIT_PATCH_timeout_cb(void *arg) {
    event_t evt = { .id = EVENT_TIMER_EXPIRED_WAIT_PATCH_timeout, .param = 0 };
    statemachine_process(&evt);
}
static rtc_timer_handle_t verify_timeout_handle = NULL;
static void verify_timeout_cb(void *arg) {
    event_t evt = { .id = EVENT_TIMER_EXPIRED_verify_timeout, .param = 0 };
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
    {
        event_t evt_pub = { .id = EVENT_FOTA_PATCH_COMPLETE, .param = 0 };
        statemachine_process(&evt_pub);
    }

}

/* ========== 初始化 ========== */
void statemachine_init(void) {
    current_state = STATE_IDLE;
    upgrade_attempts = 0;
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
            extern void led_task_notify(void);
            led_task_notify();
            {
                upgrade_attempts = 0;
            }

            current_state = STATE_WAIT_PATCH;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                uint32_t period = 200;
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
                uint32_t period = 500;
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
                uint32_t period = 30000;
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       WAIT_PATCH_timeout_cb, NULL);
                WAIT_PATCH_timeout_handle = h;
                RTC_TimerStart(h);
            }
        }
        break;
    case STATE_WAIT_PATCH:
        if (
            (evt->id == EVENT_FOTA_PATCH_COMPLETE)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            if (WAIT_PATCH_timeout_handle) {
                RTC_TimerStop(WAIT_PATCH_timeout_handle);
                RTC_TimerDelete(WAIT_PATCH_timeout_handle);
                WAIT_PATCH_timeout_handle = NULL;
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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_VERIFY;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                uint32_t period = 10000;
                if (verify_timeout_handle) {
                    RTC_TimerDelete(verify_timeout_handle);
                    verify_timeout_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       verify_timeout_cb, NULL);
                verify_timeout_handle = h;
                RTC_TimerStart(h);
            }

        }
        else if (
            (evt->id == EVENT_FOTA_ERROR)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            if (WAIT_PATCH_timeout_handle) {
                RTC_TimerStop(WAIT_PATCH_timeout_handle);
                RTC_TimerDelete(WAIT_PATCH_timeout_handle);
                WAIT_PATCH_timeout_handle = NULL;
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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_ERROR;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        else if (
            (evt->id == EVENT_TIMER_EXPIRED_WAIT_PATCH_timeout)
        ) {
            /* 停止并删除当前状态的超时定时器 */
            if (WAIT_PATCH_timeout_handle) {
                RTC_TimerStop(WAIT_PATCH_timeout_handle);
                RTC_TimerDelete(WAIT_PATCH_timeout_handle);
                WAIT_PATCH_timeout_handle = NULL;
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
    case STATE_VERIFY:
        if (
            (evt->id == EVENT_FOTA_VERIFY_OK)
        ) {
            {
                if (verify_timeout_handle) {
                    RTC_TimerStop(verify_timeout_handle);
                    RTC_TimerDelete(verify_timeout_handle);
                    verify_timeout_handle = NULL;
                }
            }

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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_APPLY;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        else if (
            (evt->id == EVENT_FOTA_VERIFY_FAIL)
        ) {
            {
                if (verify_timeout_handle) {
                    RTC_TimerStop(verify_timeout_handle);
                    RTC_TimerDelete(verify_timeout_handle);
                    verify_timeout_handle = NULL;
                }
            }

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
            {
                upgrade_attempts++;
            }
            {
                if (upgrade_attempts > 3 ) {
                    {
                event_t evt_pub = { .id = EVENT_FOTA_ERROR, .param = 0 };
                statemachine_process(&evt_pub);
            }

                }
            }

            current_state = STATE_RETRY;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                uint32_t period = 1000;
                if (defer_2_handle) {
                    RTC_TimerDelete(defer_2_handle);
                    defer_2_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       defer_2_cb, NULL);
                defer_2_handle = h;
                RTC_TimerStart(h);
            }

        }
        else if (
            (evt->id == EVENT_TIMER_EXPIRED_verify_timeout)
        ) {
            {
                if (verify_timeout_handle) {
                    RTC_TimerStop(verify_timeout_handle);
                    RTC_TimerDelete(verify_timeout_handle);
                    verify_timeout_handle = NULL;
                }
            }

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
            {
                upgrade_attempts++;
            }

            current_state = STATE_RETRY;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                uint32_t period = 1000;
                if (defer_2_handle) {
                    RTC_TimerDelete(defer_2_handle);
                    defer_2_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       defer_2_cb, NULL);
                defer_2_handle = h;
                RTC_TimerStart(h);
            }

        }
        break;
    case STATE_APPLY:
        if (
            (evt->id == EVENT_FOTA_APPLY_OK)
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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_SUCCESS;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        else if (
            (evt->id == EVENT_FOTA_ERROR)
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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_ERROR;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    case STATE_RETRY:
        if (
            (evt->id == EVENT_FOTA_PATCH_COMPLETE)
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
            
            current_state = STATE_VERIFY;
            /* 执行目标状态的进入动作并启动时间序列 */
            {
                uint32_t period = 10000;
                if (verify_timeout_handle) {
                    RTC_TimerDelete(verify_timeout_handle);
                    verify_timeout_handle = NULL;
                }
                rtc_timer_handle_t h = RTC_TimerCreate(period, RTC_TIMER_MODE_ONE_SHOT,
                                                       verify_timeout_cb, NULL);
                verify_timeout_handle = h;
                RTC_TimerStart(h);
            }

        }
        else if (
            (evt->id == EVENT_FOTA_ERROR)
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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_ERROR;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    case STATE_SUCCESS:
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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    case STATE_ERROR:
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
            extern void led_task_notify(void);
            led_task_notify();

            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    }
}