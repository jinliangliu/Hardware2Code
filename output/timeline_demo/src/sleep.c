/**
 * sleep.c.j2 - Low power management
 *
 * When has_tickless is True: full tickless idle with RTC wakeup + STOP mode.
 * When has_tickless is False: debug stub that never enters sleep.
 */
/**
 * tickless_idle.c.j2 - FreeRTOS Tickless Idle implementation for STM32G0
 * Uses RTC WakeUp Timer + STOP mode for low power.
 *
 * Generated when: has_tickless is True (FreeRTOS enabled + RTC present)
 */
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

/* RTC handle - must be initialized by main before scheduler starts */
extern RTC_HandleTypeDef hrtc;

/* System clock re-configuration - defined in main.c */
extern void SystemClock_Config(void);

/*
 * vPortSuppressTicksAndSleep - FreeRTOS tickless idle hook.
 * Called by the idle task when configUSE_TICKLESS_IDLE = 1.
 *
 * Implementation:
 * 1. Calculate how many ticks we can sleep
 * 2. Disable interrupts and check if a task was woken since we calculated
 * 3. Configure RTC WakeUp Timer for the sleep duration
 * 4. Enter STOP mode (HAL_PWR_EnterSTOPMode)
 * 5. On wake, reconfigure system clock (HSI)
 * 6. Inform FreeRTOS how many ticks elapsed
 */
void vPortSuppressTicksAndSleep(TickType_t xExpectedIdleTime)
{
    if (xExpectedIdleTime <= 2) {
        /* Too short to justify sleep overhead - just do WFI */
        __WFI();
        return;
    }

    /* Cap at maximum RTC WakeUp timer period (~36 hours with 1Hz) */
    if (xExpectedIdleTime > 0xFFFF) {
        xExpectedIdleTime = 0xFFFF;
    }

    /* Disable interrupts for atomic sleep preparation */
    __disable_irq();

    /* Re-check: did an ISR wake a task since we computed xExpectedIdleTime? */
    if (eTaskConfirmSleepModeStatus() == eAbortSleep) {
        __enable_irq();
        return;
    }

    /* -------- Configure RTC WakeUp Timer -------- */
    /* Clear pending wakeup flag */
    __HAL_RTC_WAKEUPTIMER_CLEAR_FLAG(&hrtc, RTC_FLAG_WUTF);

    /* Set wakeup period in seconds (RTC runs at 1 Hz) */
    /* Convert RTOS ticks to seconds - assumes configTICK_RATE_HZ = 1000 */
    uint32_t sleep_seconds = xExpectedIdleTime / (configTICK_RATE_HZ / 1000);
    if (sleep_seconds == 0) {
        sleep_seconds = 1;
    }
    if (sleep_seconds > 0xFFFF) {
        sleep_seconds = 0xFFFF;
    }

    HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, sleep_seconds,
                                RTC_WAKEUPCLOCK_CK_SPRE_16BITS);

    /* -------- Enter STOP mode -------- */
    /* Suspend SysTick so it doesn't wake us immediately */
    HAL_SuspendTick();

    /*
     * STOP0 mode: HSI off, HSE off, PLL off. Wake on RTC or EXTI.
     * STM32G0 STOP0 current ~3-5 uA (typ).
     */
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);

    /* -------- Wakeup: reconfigure clocks -------- */
    /* System clock was stopped - reconfigure HSI */
    SystemClock_Config();

    /* Resume SysTick */
    HAL_ResumeTick();

    /* Clear wakeup flag */
    __HAL_RTC_WAKEUPTIMER_CLEAR_FLAG(&hrtc, RTC_FLAG_WUTF);

    /* Re-enable interrupts */
    __enable_irq();

    /*
     * Tell FreeRTOS how many ticks elapsed.
     * Since we slept for sleep_seconds seconds and tick rate is 1000 Hz:
     */
    vTaskStepTick(sleep_seconds * (configTICK_RATE_HZ / 1000));
}