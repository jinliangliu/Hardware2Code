#ifndef __DRV_RTC_H
#define __DRV_RTC_H

#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif
#include "event_mgr.h"

/* Wall clock time structure */
typedef struct {
    uint8_t hour;
    uint8_t min;
    uint8_t sec;
    uint8_t day;
    uint8_t month;
    uint8_t year;
} rtc_time_t;

/* Software timer modes */
#define RTC_TIMER_MODE_ONE_SHOT     0
#define RTC_TIMER_MODE_PERIODIC     1

/* Timer callback type */
typedef void (*rtc_timer_cb_t)(void *arg);

/* Timer handle (opaque) */
typedef struct rtc_timer *rtc_timer_handle_t;

/* ---------- RTC basic functions ---------- */
void RTC_Init(void);
void RTC_Start(void);
void RTC_GetTime(rtc_time_t *time);
void RTC_SetTime(rtc_time_t *time);
void RTC_AdjustDrift(int16_t ppm);           // fine tune RTC clock

/* ---------- Software timer management ---------- */
rtc_timer_handle_t RTC_TimerCreate( uint32_t period_ms,
                                    uint8_t  mode,
                                    rtc_timer_cb_t callback,
                                    void     *arg );
void RTC_TimerStart(rtc_timer_handle_t handle);
void RTC_TimerStop(rtc_timer_handle_t handle);
void RTC_TimerDelete(rtc_timer_handle_t handle);
void RTC_SetWakeUpCounter(uint32_t wake_up_counter);
void RTC_ProcessTimers(void);
#endif