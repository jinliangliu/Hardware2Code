/**
 * sleep.c.j2 - Low power management
 * 如果使用了 RTC，则进入 STOP1 模式并依赖 RTC 唤醒；
 * 否则仅使用简单的 WFI（Sleep 模式）。
 */
#include "stm32g0xx_hal.h"
#include "stm32g0xx_hal_pwr_ex.h"
#include "FreeRTOS.h"
#include "task.h"

#include "drv_rtc.h"

extern void SystemClock_Config(void);

void vPortSuppressTicksAndSleep( TickType_t xExpectedIdleTime )
{
    if( xExpectedIdleTime > 0 )
    {
        HAL_SuspendTick();

        /* 使用 RTC 作为唤醒源 */
        const uint32_t counts_per_tick = 2;
        uint32_t req_counts = xExpectedIdleTime * counts_per_tick;
        if( req_counts > 0xFFFF ) req_counts = 0xFFFF;
        RTC_SetWakeUpCounter( req_counts );

        __disable_irq();
#ifdef DEBUG
        HAL_PWR_EnterSLEEPMode( PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI );
#else
        HAL_PWREx_EnterSTOP1Mode( PWR_MAINREGULATOR_ON, PWR_STOPENTRY_WFI );
#endif
        __enable_irq();

        SystemClock_Config();
        HAL_ResumeTick();
        vTaskStepTick( xExpectedIdleTime );
    }
}