/**
 * sleep.c.j2 - Low power management
 *
 * When has_tickless is True: full tickless idle with RTC wakeup + STOP mode.
 * When has_tickless is False: debug stub that never enters sleep.
 */
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

void vPortSuppressTicksAndSleep( TickType_t xExpectedIdleTime )
{
    /* DEBUG mode: never enter low power, keep debugger and peripherals running */
    (void)xExpectedIdleTime;
    return;
}
