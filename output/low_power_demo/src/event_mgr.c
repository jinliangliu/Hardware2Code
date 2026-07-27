
#ifdef TEST
#include "mock_hal.h"
#else
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#endif

#include "event_mgr.h"



#include "drv_onboard_rtc.h"

extern TaskHandle_t led_task_handle;

/* event_queue 在真实环境和测试环境中都由此定义 */
QueueHandle_t event_queue = NULL;

/* 内部处理器（无业务流时使用） */
static void handle_minute_tick(void);
static void handle_hour_tick(void);
static void handle_button_press(void);

void EventMgr_Init(void)
{
    /* 测试模式和真实模式都创建队列（mock 的 xQueueCreate 会返回非空） */
    event_queue = xQueueCreate(100, sizeof(event_t));
}

void EventMgr_Task(void *pvParameters)
{
    event_t evt;
    while(1) {
        if( xQueueReceive(event_queue, &evt, portMAX_DELAY) == pdTRUE ) {
#ifndef TEST
            switch(evt.id) {
                case EVENT_MINUTE_TICK:
                    handle_minute_tick();
                    break;
                case EVENT_HOUR_TICK:
                    handle_hour_tick();
                    break;
                case EVENT_BUTTON_PRESS:
                    handle_button_press();
                    break;
                case EVENT_RTC_TICK:
                    RTC_ProcessTimers();
                    break;
                default:
                    break;
            }
#else
            /* 测试模式：仅标记事件已处理 */
            (void)evt;
#endif
        }
    }
}

/* 经典事件处理器（测试环境不参与） */
#ifndef TEST
static void handle_minute_tick(void) {
    static uint32_t min_count = 0;
    if (++min_count >= 30) {
        min_count = 0;
        if (led_task_handle) xTaskNotify(led_task_handle, 0, eSetBits);
    }
}
static void handle_hour_tick(void) {}
static void handle_button_press(void) {
    if (led_task_handle) xTaskNotify(led_task_handle, 0, eSetBits);
}
#endif /* !TEST */
