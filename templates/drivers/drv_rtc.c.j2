#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#endif

#include "drv_rtc.h"
#include "event_mgr.h"

static RTC_HandleTypeDef hrtc;

/* ========== 软件定时器（公共部分，测试和硬件均可用） ========== */
typedef struct rtc_timer {
    uint32_t            period_ms;
    uint32_t            remaining_ms;
    uint8_t             mode;
    rtc_timer_cb_t      callback;
    void                *arg;
    struct rtc_timer    *next;
} rtc_timer_t;

static rtc_timer_t *timer_head = NULL;
static QueueHandle_t timer_queue = NULL;
extern QueueHandle_t event_queue;

static void minute_timer_cb(void *arg) {
    event_t evt = { .id = EVENT_MINUTE_TICK, .param = 0 };
    xQueueSend(event_queue, &evt, 0);
}
static void hour_timer_cb(void *arg) {
    event_t evt = { .id = EVENT_HOUR_TICK, .param = 0 };
    xQueueSend(event_queue, &evt, 0);
}

rtc_timer_handle_t RTC_TimerCreate(uint32_t period_ms, uint8_t mode,
                                   rtc_timer_cb_t callback, void *arg)
{
    rtc_timer_t *t = pvPortMalloc(sizeof(rtc_timer_t));
    if (!t) return NULL;
    t->period_ms = period_ms;
    t->remaining_ms = period_ms;
    t->mode = mode;
    t->callback = callback;
    t->arg = arg;
    t->next = NULL;

    taskENTER_CRITICAL();
    if (!timer_head) {
        timer_head = t;
    } else {
        rtc_timer_t *p = timer_head;
        while (p->next) p = p->next;
        p->next = t;
    }
    taskEXIT_CRITICAL();
    return (rtc_timer_handle_t)t;
}

void RTC_TimerStart(rtc_timer_handle_t handle) {
    rtc_timer_t *t = (rtc_timer_t *)handle;
    taskENTER_CRITICAL();
    t->remaining_ms = t->period_ms;
    taskEXIT_CRITICAL();
}

void RTC_TimerStop(rtc_timer_handle_t handle) {
    rtc_timer_t *t = (rtc_timer_handle_t)handle;
    taskENTER_CRITICAL();
    t->remaining_ms = 0;
    taskEXIT_CRITICAL();
}

void RTC_TimerDelete(rtc_timer_handle_t handle) {
    rtc_timer_t *t = (rtc_timer_handle_t)handle;
    taskENTER_CRITICAL();
    if (timer_head == t) {
        timer_head = t->next;
    } else {
        rtc_timer_t *p = timer_head;
        while (p && p->next != t) p = p->next;
        if (p) p->next = t->next;
    }
    taskEXIT_CRITICAL();
    vPortFree(t);
}

void RTC_ProcessTimers(void) {
    rtc_timer_t *t = timer_head;
    while (t) {
        if (t->remaining_ms > 0) {
            if (t->remaining_ms <= 100) {
                t->remaining_ms = 0;
                if (t->callback) t->callback(t->arg);
                if (t->mode == RTC_TIMER_MODE_PERIODIC)
                    t->remaining_ms = t->period_ms;
            } else {
                t->remaining_ms -= 100;
            }
        }
        t = t->next;
    }
}

/* ========== 硬件初始化（TEST 环境下提供空桩） ========== */
#ifndef TEST
void RTC_Init(void) {
    /* 硬件实现，保持不变 */
    __disable_irq();
    RCC->APBENR1 |= RCC_APBENR1_PWREN;
    PWR->CR1 |= PWR_CR1_DBP;
    RCC->CSR |= RCC_CSR_LSION;
    while ((RCC->CSR & RCC_CSR_LSIRDY) == 0);
    RCC->BDCR = (0x02UL << RCC_BDCR_RTCSEL_Pos) | RCC_BDCR_RTCEN;
    while (!(RCC->BDCR & RCC_BDCR_RTCEN));
    /* ... 其余初始化步骤 ... */
    hrtc.Instance = RTC;
}

void RTC_Start(void) {
    SET_BIT(RTC->CR, RTC_CR_WUTIE);
    HAL_NVIC_SetPriority(RTC_TAMP_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(RTC_TAMP_IRQn);
    timer_queue = xQueueCreate(10, sizeof(rtc_timer_cb_t));
    rtc_timer_handle_t t_min = RTC_TimerCreate(60000, RTC_TIMER_MODE_PERIODIC, minute_timer_cb, NULL);
    rtc_timer_handle_t t_hour = RTC_TimerCreate(3600000, RTC_TIMER_MODE_PERIODIC, hour_timer_cb, NULL);
    RTC_TimerStart(t_min);
    RTC_TimerStart(t_hour);
}

void RTC_TAMP_IRQHandler(void) { /* ... */ }
void RTC_SetWakeUpCounter(uint32_t wake_up_counter) { /* ... */ }
void RTC_GetTime(rtc_time_t *time) { /* ... */ }
void RTC_SetTime(rtc_time_t *time) { /* ... */ }
void RTC_AdjustDrift(int16_t ppm) { /* ... */ }

#else
/* TEST 空桩 */
void RTC_Init(void) { hrtc.Instance = RTC; HAL_RTC_Init(&hrtc); }
void RTC_Start(void) {}
void RTC_TAMP_IRQHandler(void) {}
void RTC_SetWakeUpCounter(uint32_t wake_up_counter) { (void)wake_up_counter; }
void RTC_GetTime(rtc_time_t *time) { memset(time, 0, sizeof(*time)); }
void RTC_SetTime(rtc_time_t *time) {}
void RTC_AdjustDrift(int16_t ppm) {}
#endif