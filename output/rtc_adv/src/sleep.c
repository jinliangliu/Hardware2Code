/**
 * sleep.c.j2 - Low power management
 * Debug: SLEEP mode (debugger stays connected)
 * Release: STOP1 mode (deep low power)
 */
#include "stm32g0xx_hal.h"
#include "stm32g0xx_hal_pwr_ex.h"
#include "FreeRTOS.h"
#include "task.h"
#include "drv_rtc.h"

extern void SystemClock_Config(void);

void vPortSuppressTicksAndSleep( TickType_t xExpectedIdleTime )
{
        #if 0
    if( xExpectedIdleTime > 0 )
    {
        const uint32_t counts_per_tick = 2;
        uint32_t req_counts = xExpectedIdleTime * counts_per_tick;
        if( req_counts > 0xFFFF ) req_counts = 0xFFFF;

        HAL_SuspendTick();
        RTC_SetWakeUpCounter( req_counts );

        __disable_irq();
#ifdef DEBUG
        /* Debug 模式：仅 SLEEP，调试器可保持连接 */
        HAL_PWR_EnterSLEEPMode( PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI );
#else
        /* Release 模式：进入 STOP1，功耗极低 */
        HAL_PWREx_EnterSTOP1Mode( PWR_MAINREGULATOR_ON, PWR_STOPENTRY_WFI );
#endif
        __enable_irq();

        SystemClock_Config();
        HAL_ResumeTick();
        vTaskStepTick( xExpectedIdleTime );

    }
    #endif
}