
#ifdef TEST
#include "mock_hal.h"
extern QueueHandle_t event_queue;   /* defined in mock_hal.c */
#else
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "event_mgr.h"
QueueHandle_t event_queue = NULL;
#endif

/* Include any driver headers needed by handlers */
#include "drv_rtc.h"

/* External LED task handle */
extern TaskHandle_t led_task_handle;

/* Forward declarations of internal handlers */
static void handle_minute_tick(void);
static void handle_hour_tick(void);
static void handle_button_press(void);

void EventMgr_Init(void)
{
    event_queue = xQueueCreate(100, sizeof(event_t));
}

void EventMgr_Task(void *pvParameters)
{
    event_t evt;
    while(1) {
        if( xQueueReceive(event_queue, &evt, portMAX_DELAY) == pdTRUE ) {

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
#ifndef TEST
                case EVENT_RTC_TICK:
                    RTC_ProcessTimers();
                    break;
#endif
                default:
                    break;
            }
        }
    }
}

/* ---------- Handler implementations ---------- */
static void handle_minute_tick(void)
{
    static uint32_t min_count = 0;
    if (++min_count >= 30) {
        min_count = 0;
        if (led_task_handle) {
            xTaskNotify(led_task_handle, 0, eSetBits);
        }
    }
}

static void handle_hour_tick(void)
{
    /* Hourly tasks */
}

static void handle_button_press(void)
{
    if (led_task_handle) {
        xTaskNotify(led_task_handle, 0, eSetBits);
    }
}

