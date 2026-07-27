#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "event_mgr.h"

/* External task handles for notifications */

void NMI_Handler(void) { while(1); }
void HardFault_Handler(void) {
    uint32_t sp;
    __asm__("mov %0, sp" : "=r"(sp));
    // 断点打在这里，查看sp指向的栈内存
    while(1);
}

/* EXTI interrupt handlers */



