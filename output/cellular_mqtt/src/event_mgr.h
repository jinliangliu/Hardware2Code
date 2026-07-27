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

/* ========== 动态定时器事件（由 context builder 预计算） ========== */
    EVENT_TIMER_EXPIRED_CONNECTING_timeout,

/* ========== 动态发布事件（由 context builder 预计算） ========== */

/* ========== 业务流转换事件（来自 YAML transitions 的 event 字段） ========== */

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