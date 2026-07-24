#ifndef __EVENT_MGR_H
#define __EVENT_MGR_H

#ifdef TEST
#include "mock_hal.h"
#else
#include "FreeRTOS.h"
#include "queue.h"
#endif

/* ========== 事件枚举 ========== */
typedef enum {
    EVENT_NONE = 0,
    EVENT_MINUTE_TICK,
    EVENT_HOUR_TICK,
    EVENT_BUTTON_PRESS,
    EVENT_RTC_ALARM,
    EVENT_RTC_TICK,
    EVENT_RETURN,   /* 子状态返回事件 */

/* ========== 动态定时器事件（由模板自动收集） ========== */



    EVENT_TIMER_EXPIRED_defer_0,
    EVENT_TIMER_EXPIRED_defer_1,
    EVENT_TIMER_EXPIRED_defer_2,
    EVENT_TIMER_EXPIRED_PLAYING_timeout,

/* ========== 动态发布事件（由生成器提供） ========== */

    EVENT_MAX
} event_id_t;

/* ========== 事件结构体 ========== */
typedef struct {
    event_id_t id;
    uint32_t   param;
} event_t;

extern QueueHandle_t event_queue;

void EventMgr_Init(void);
void EventMgr_Task(void *pvParameters);

#endif /* __EVENT_MGR_H */