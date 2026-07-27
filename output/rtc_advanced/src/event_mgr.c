
#ifdef TEST
#include "mock_hal.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#endif

#include "event_mgr.h"

#ifndef TEST
#include "drv_log.h"
#endif

#ifndef TEST
#include "statemachine.h"
#endif

#include "drv_rtc.h"
#include "drv_uart_debug.h"

extern TaskHandle_t led_task_handle;

/* event_queue 在真实环境和测试环境中都由此定义 */
QueueHandle_t event_queue = NULL;

/* 内部处理器（无业务流时使用） */

void EventMgr_Init(void)
{
    /* 测试模式和真实模式都创建队列（mock 的 xQueueCreate 会返回非空） */
    event_queue = xQueueCreate(100, sizeof(event_t));
}

void EventMgr_Task(void *pvParameters)
{
#ifndef TEST
    log_info("EventMgr: task started, waiting for events...");
#endif
    event_t evt;
    while(1) {
        if( xQueueReceive(event_queue, &evt, portMAX_DELAY) == pdTRUE ) {
#ifndef TEST
            log_info("EventMgr: dispatching event #%d", (int)evt.id);
            if (evt.id == EVENT_RTC_TICK) {
                RTC_ProcessTimers();
            }
            statemachine_process(&evt);
#else
            /* 测试模式：仅标记事件已处理 */
            (void)evt;
#endif
        }
    }
}

