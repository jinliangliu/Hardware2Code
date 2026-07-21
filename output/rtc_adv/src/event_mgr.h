#ifndef __EVENT_MGR_H
#define __EVENT_MGR_H

#include <stdint.h>

#ifdef TEST
#include "mock_hal.h"      // 提供 QueueHandle_t, TickType_t 等
#else
#include "FreeRTOS.h"
#include "queue.h"
#endif

typedef enum {
    EVENT_NONE = 0,
    EVENT_RTC_TICK,
    EVENT_MINUTE_TICK,
    EVENT_HOUR_TICK,
    EVENT_BUTTON_PRESS,
    EVENT_RTC_ALARM,
    EVENT_MAX
} event_id_t;

typedef struct {
    event_id_t id;
    uint32_t   param;
} event_t;

extern QueueHandle_t event_queue;

void EventMgr_Init(void);
void EventMgr_Task(void *pvParameters);


#endif