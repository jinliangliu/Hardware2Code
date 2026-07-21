
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

void vApplicationIdleHook( void )
{
    /* MVP: enter sleep mode using WFI (works on all Cortex-M, no HAL dependency) */
    __WFI();
}