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
 *
 * Clock strategy:
 *   - RTCCLK_DIV16 (2048 Hz) for sub-second resolution (max ~32s sleep)
 *   - CK_SPRE (1 Hz) fallback for very long sleeps (> 32s)
 */
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

#if ( configUSE_TICKLESS_IDLE == 1 )

/* RTC handle - must be initialized by main before scheduler starts */
extern RTC_HandleTypeDef hrtc;

/* Restore periodic wakeup configuration after tickless idle */
extern void RTC_RestoreTickConfig(void);

/* System clock re-configuration - defined in main.c */
extern void SystemClock_Config(void);

/* RTCCLK_DIV16 = 32768 / 16 = 2048 Hz */
#define TICKLESS_RTC_FREQ_HZ    2048
/* Max counter value for 16-bit auto-reload */
#define TICKLESS_MAX_COUNTER    0xFFFF

/*
 * vPortSuppressTicksAndSleep - FreeRTOS tickless idle hook.
 * Called by the idle task when configUSE_TICKLESS_IDLE = 1.
 *
 * Implementation:
 * 1. Calculate sleep duration in RTC counter ticks (RTCCLK_DIV16)
 * 2. Disable interrupts and check if a task was woken since we calculated
 * 3. Configure RTC WakeUp Timer for the sleep duration
 * 4. Enter STOP mode (HAL_PWR_EnterSTOPMode)
 * 5. On wake, reconfigure system clock (HSI)
 * 6. Inform FreeRTOS how many ticks elapsed
 * 7. Restore periodic RTC wakeup timer
 */
void vPortSuppressTicksAndSleep(TickType_t xExpectedIdleTime)
{
    if (xExpectedIdleTime <= 2) {
        /* Too short to justify sleep overhead - just do WFI */
        __WFI();
        return;
    }

    /* -------- Calculate sleep duration in RTC counter ticks -------- */
    /*
     * Use RTCCLK_DIV16 (2048 Hz) for sub-second resolution.
     * counter = xExpectedIdleTime * (2048 / configTICK_RATE_HZ)
     *
     * Example: tick_rate=1000 Hz, xExpectedIdleTime=100 (100 ms)
     *   counter = 100 * 2048 / 1000 = 204  → ~99.6 ms wakeup
     *
     * The minimum counter value is 1, giving ~0.5 ms resolution.
     * Max counter = 65535 / 2048 ≈ 32 seconds for RTCCLK_DIV16.
     *
     * For longer sleeps, fall back to CK_SPRE (1 Hz, max ~18 hours).
     */
    uint32_t wakeup_clock = RTC_WAKEUPCLOCK_RTCCLK_DIV16;
    uint32_t wakeup_counter = (uint32_t)xExpectedIdleTime * TICKLESS_RTC_FREQ_HZ
                              / configTICK_RATE_HZ;

    if (wakeup_counter > TICKLESS_MAX_COUNTER) {
        /* Sleep too long for RTCCLK_DIV16 — fall back to CK_SPRE (1 Hz) */
        wakeup_clock = RTC_WAKEUPCLOCK_CK_SPRE_16BITS;
        wakeup_counter = xExpectedIdleTime / configTICK_RATE_HZ;
        if (wakeup_counter == 0) {
            wakeup_counter = 1;
        }
        if (wakeup_counter > TICKLESS_MAX_COUNTER) {
            wakeup_counter = TICKLESS_MAX_COUNTER;
        }
    } else if (wakeup_counter == 0) {
        wakeup_counter = 1;
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

    /* Set wakeup period */
    HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, wakeup_counter, wakeup_clock);

    /* -------- Enter STOP mode -------- */
    /* Suspend SysTick so it doesn't wake us immediately */
    HAL_SuspendTick();

    /*
     * STOP0 mode: HSI off, HSE off, PLL off. Wake on RTC or EXTI.
     * STM32G0 STOP0 current ~3-5 uA (typ).
     * LSI/LSE keep running, so RTC wakeup timer continues counting.
     */
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);

    /* -------- Wakeup: reconfigure clocks -------- */
    /* System clock was stopped — reconfigure HSI.
     * RTC backup domain (LSI/LSE) survives STOP, but the APB interface
     * needs re-synchronization before accessing RTC registers. */
    SystemClock_Config();

    /* Resume SysTick */
    HAL_ResumeTick();

    /* Clear wakeup flag */
    __HAL_RTC_WAKEUPTIMER_CLEAR_FLAG(&hrtc, RTC_FLAG_WUTF);

    /* Re-enable interrupts */
    __enable_irq();

    /* Restore periodic RTC wakeup timer (100ms @ RTCCLK_DIV16).
     * vPortSuppressTicksAndSleep may have changed the clock source;
     * we must restore the original config so software timers resume firing. */
    RTC_RestoreTickConfig();

    /*
     * Tell FreeRTOS how many ticks elapsed.
     * Convert RTC counter ticks back to RTOS ticks.
     *
     * If using CK_SPRE (1 Hz): ticks = wakeup_counter * configTICK_RATE_HZ
     * If using RTCCLK_DIV16 (2048 Hz): ticks = wakeup_counter * configTICK_RATE_HZ / 2048
     */
    TickType_t ticks_elapsed;
    if (wakeup_clock == RTC_WAKEUPCLOCK_RTCCLK_DIV16) {
        ticks_elapsed = (TickType_t)(wakeup_counter * configTICK_RATE_HZ
                                     / TICKLESS_RTC_FREQ_HZ);
    } else {
        ticks_elapsed = (TickType_t)(wakeup_counter * configTICK_RATE_HZ);
    }

    /* Clamp to xExpectedIdleTime to prevent configASSERT in vTaskStepTick.
     * Rounding in integer division can cause ticks_elapsed to exceed
     * the expected value, which triggers assertion failure. */
    if (ticks_elapsed > xExpectedIdleTime) {
        ticks_elapsed = xExpectedIdleTime;
    }
    vTaskStepTick(ticks_elapsed);
}

#endif /* configUSE_TICKLESS_IDLE == 1 */
