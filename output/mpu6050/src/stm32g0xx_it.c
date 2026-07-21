
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

/* External task handles for notifications */
extern TaskHandle_t mpu6050_alert_task_handle;

void NMI_Handler(void) { while(1); }
void HardFault_Handler(void) { while(1); }

/* EXTI interrupt handlers (auto-generated) */

void EXTI4_15_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler( GPIO_PIN_13 );
    if (xTaskGetSchedulerState() != taskSCHEDULER_NOT_STARTED)
    {
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        xTaskNotifyFromISR( mpu6050_alert_task_handle, 0, eSetBits, &xHigherPriorityTaskWoken );
        portYIELD_FROM_ISR( xHigherPriorityTaskWoken );
    }
}
