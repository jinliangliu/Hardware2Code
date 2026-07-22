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
#define STATE_PROCESS 1
#define STATE_PROCESS_STEP1 0
#define STATE_PROCESS_STEP2 1

/* ========== 当前状态变量 ========== */
static uint32_t current_state;
static uint32_t current_state_PROCESS;

/* ========== 历史状态变量 ========== */

/* ========== 动作实现宏 ========== */

/* ========== 动作列表处理宏 ========== */


/* ========== 定时器收集宏（排除 defer 生成的定时器） ========== */

        


/* ========== 用户定时器 + 状态超时定时器的句柄与回调 ========== */

/* ========== 延迟动作定时器回调 ========== */
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
    current_state_PROCESS = STATE_PROCESS_STEP1;
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
            /* 停止当前状态的时间序列定时器 */
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


            current_state = STATE_PROCESS;
            /* 执行目标状态的进入动作并启动时间序列 */
        }
        break;
    case STATE_PROCESS:
        {
            int handled = 0;
            switch (current_state_PROCESS) {
            case STATE_PROCESS_STEP1:
                if (evt->id == EVENT_RTC_TICK) {
                    
                    current_state_PROCESS = STATE_PROCESS_STEP2;
                    handled = 1;
                    break;
                }
                break;
            case STATE_PROCESS_STEP2:
                if (evt->id == EVENT_RTC_TICK) {
                        

                    current_state_PROCESS = STATE_PROCESS_;
                    handled = 1;
                    break;
                }
                break;
            }
            if (handled) break;
        }
        if (
            (evt->id == EVENT_RETURN)
        ) {
            /* 停止当前状态的时间序列定时器 */
                #ifndef TEST
    led_task_notify();
#else
    extern void led_task_notify(void);
    led_task_notify();
#endif


            current_state = STATE_IDLE;
            /* 执行目标状态的进入动作并启动时间序列 */
            /* 若目标也是复合状态，初始化子状态（考虑历史） */
        }
        break;
    }
}