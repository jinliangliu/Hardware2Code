/**
 * sleep.c.j2 - Low power management
 * 使用 CMSIS 寄存器进入 STOP1 模式（无需 HAL_PWREx 头文件）
 */
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

#include "drv_rtc.h"

extern void SystemClock_Config(void);

/**
 * @brief 使用 CMSIS 寄存器进入 STOP1 模式
 */
static void EnterStop1Mode(void)
{
    /* 设置 SLEEPDEEP 位 */
    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;

    /* 选择 STOP1 模式 (LPMS = 1) */
    MODIFY_REG(PWR->CR1, PWR_CR1_LPMS, (1UL << PWR_CR1_LPMS_Pos));

    /* 执行 WFI 进入 STOP */
    __WFI();
}

void vPortSuppressTicksAndSleep( TickType_t xExpectedIdleTime )
{
    if( xExpectedIdleTime > 0 )
    {
        HAL_SuspendTick();

        const uint32_t counts_per_tick = 2;
        uint32_t req_counts = xExpectedIdleTime * counts_per_tick;
        if( req_counts > 0xFFFF ) req_counts = 0xFFFF;
        RTC_SetWakeUpCounter( req_counts );

        __disable_irq();
#ifdef DEBUG
        HAL_PWR_EnterSLEEPMode( PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI );
#else
        EnterStop1Mode();
#endif
        __enable_irq();

        SystemClock_Config();
        HAL_ResumeTick();
        vTaskStepTick( xExpectedIdleTime );
    }
}