/**
 * sleep.c.j2 - Low power management (DEBUG mode: no sleep)
 */
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

extern void SystemClock_Config(void);

void vPortSuppressTicksAndSleep( TickType_t xExpectedIdleTime )
{
    /* 调试期间：完全不进入低功耗，确保调试器和外设持续运行 */
    (void)xExpectedIdleTime;
    return;
}