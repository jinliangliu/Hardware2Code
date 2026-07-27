#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "event_mgr.h"

/* External task handles for notifications */
extern TaskHandle_t fota_task_handle;

void NMI_Handler(void) { while(1); }
void HardFault_Handler(void) {
    uint32_t sp;
    __asm__("mov %0, sp" : "=r"(sp));
    // 断点打在这里，查看sp指向的栈内存
    while(1);
}

/* EXTI interrupt handlers */

void EXTI4_15_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler( GPIO_PIN_13 );
    if (xTaskGetSchedulerState() != taskSCHEDULER_NOT_STARTED)
    {
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        event_t evt = { .id = EVENT_BUTTON_PRESS, .param = 0 };
        xQueueSendFromISR(event_queue, &evt, &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

/* TIM14 用作 HAL 时基，中断内调用 HAL_TIM_IRQHandler，
   最终触发 HAL_TIM_PeriodElapsedCallback → HAL_IncTick() */
extern TIM_HandleTypeDef TimHandle;

void TIM14_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&TimHandle);
}

