#ifndef __DRV_RTC_H
#define __DRV_RTC_H

/* 定时器句柄和回调类型 - 在所有编译模式下均需定义 */
typedef void * rtc_timer_handle_t;
typedef void (*rtc_timer_cb_t)(void *arg);
#define RTC_TIMER_MODE_ONE_SHOT     0
#define RTC_TIMER_MODE_PERIODIC     1

#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif

typedef struct {
    uint8_t hour;
    uint8_t min;
    uint8_t sec;
    uint8_t day;
    uint8_t month;
    uint8_t year;
} rtc_time_t;

void RTC_Init(void);
void RTC_Start(void);
void RTC_GetTime(rtc_time_t *time);
void RTC_SetTime(rtc_time_t *time);
void RTC_AdjustDrift(int16_t ppm);

rtc_timer_handle_t RTC_TimerCreate(uint32_t period_ms, uint8_t mode, rtc_timer_cb_t callback, void *arg);
void RTC_TimerStart(rtc_timer_handle_t handle);
void RTC_TimerStop(rtc_timer_handle_t handle);
void RTC_TimerDelete(rtc_timer_handle_t handle);
void RTC_ProcessTimers(void);
void RTC_SetWakeUpCounter(uint32_t wake_up_counter);

#endif /* __DRV_RTC_H */