
#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#endif

#include "drv_onboard_rtc.h"
#include "event_mgr.h"

/* Private handle */
RTC_HandleTypeDef hrtc;

/* RTC tick 间隔 (毫秒) - 必须与 RTC_WakeUp_Config 配置的唤醒周期一致 */
#define RTC_TICK_INTERVAL_MS    100

/* 软件定时器链表 */
typedef struct rtc_timer {
    uint32_t            period_ms;
    uint32_t            remaining_ms;
    uint8_t             mode;
    rtc_timer_cb_t      callback;
    void                *arg;
    struct rtc_timer    *next;
} rtc_timer_t;

static rtc_timer_t *timer_head = NULL;
extern QueueHandle_t event_queue;

/* 分钟/小时定时器回调 */
static void minute_timer_cb(void *arg) {
    event_t evt = { .id = EVENT_MINUTE_TICK, .param = 0 };
    xQueueSend(event_queue, &evt, 0);
}
static void hour_timer_cb(void *arg) {
    event_t evt = { .id = EVENT_HOUR_TICK, .param = 0 };
    xQueueSend(event_queue, &evt, 0);
}

#ifndef TEST
/* ========== 硬件实现区域 ========== */

/**
 * @brief  系统错误处理（灯闪烁 + 死循环）
 *         替代 STM32Cube main.c 中的 Error_Handler，避免跨文件 extern 依赖
 */
static void Error_Handler(void)
{
    __disable_irq();
    while (1) {}
}

/**
 * @brief  RTC 外设 MSP 初始化（由 HAL_RTC_Init 自动调用）
 *         参考 STM32Cube 官方模板，使用 HAL_RCCEx_PeriphCLKConfig 配置 RTC 时钟源
 * @param  hrtc: RTC 句柄指针
 * @note   时钟源选择由 hardware.yaml 中的 clock_source 决定（LSI / LSE）
 */
void HAL_RTC_MspInit(RTC_HandleTypeDef* hrtc)
{
    if (hrtc->Instance == RTC) {
        /* 使能 PWR 时钟并解锁备份域（RTC 寄存器处于备份域） */
        __HAL_RCC_PWR_CLK_ENABLE();
        HAL_PWR_EnableBkUpAccess();

        /* 配置 RTC 时钟源 */
        RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};
        PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_RTC;

        /* 使用内部低速振荡器 LSI (32kHz) */
        __HAL_RCC_LSI_ENABLE();
        while (!__HAL_RCC_GET_FLAG(RCC_FLAG_LSIRDY));
        PeriphClkInit.RTCClockSelection = RCC_RTCCLKSOURCE_LSI;

        if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK) {
            Error_Handler();
        }

        /* 使能 RTC 外设时钟 */
        __HAL_RCC_RTC_ENABLE();
        __HAL_RCC_RTCAPB_CLK_ENABLE();
    }
}

static void RTC_WakeUp_Config(void)
{
    /* RTC_CLK = 32768 Hz, DIV16 = 2048 Hz, (204+1) = 10 Hz = 100ms */
    uint32_t wake_up_counter = (32768 / 16 / 1000 * RTC_TICK_INTERVAL_MS) - 1;
    HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, wake_up_counter, RTC_WAKEUPCLOCK_RTCCLK_DIV16);
}

/**
 * @brief  RTC 初始化（参考 STM32Cube 官方 MX_RTC_Init 模板）
 *         使用 HAL_RTC_Init 替代直接寄存器操作，内部自动调用 HAL_RTC_MspInit
 */
void RTC_Init(void)
{
    hrtc.Instance = RTC;
    hrtc.Init.HourFormat = RTC_HOURFORMAT_24;
    hrtc.Init.AsynchPrediv = 127;
    hrtc.Init.SynchPrediv = 255;
    hrtc.Init.OutPut = RTC_OUTPUT_DISABLE;
    hrtc.Init.OutPutRemap = RTC_OUTPUT_REMAP_NONE;
    hrtc.Init.OutPutPolarity = RTC_OUTPUT_POLARITY_HIGH;
    hrtc.Init.OutPutType = RTC_OUTPUT_TYPE_OPENDRAIN;
    hrtc.Init.OutPutPullUp = RTC_OUTPUT_PULLUP_NONE;

    if (HAL_RTC_Init(&hrtc) != HAL_OK) {
        Error_Handler();
    }

    /* 配置唤醒定时器 (100ms 周期) */
    RTC_WakeUp_Config();

    /* 使能 RTC 中断（优先级 1：FreeRTOS ISR 安全范围内） */
    HAL_NVIC_SetPriority(RTC_TAMP_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(RTC_TAMP_IRQn);

    /* 启动分钟/小时软件定时器 */
    rtc_timer_handle_t t_min = RTC_TimerCreate(60000, RTC_TIMER_MODE_PERIODIC, minute_timer_cb, NULL);
    rtc_timer_handle_t t_hour = RTC_TimerCreate(3600000, RTC_TIMER_MODE_PERIODIC, hour_timer_cb, NULL);
    RTC_TimerStart(t_min);
    RTC_TimerStart(t_hour);
}

void RTC_Start(void)
{
    /* 唤醒中断已在 RTC_Init 中使能，此处保留空实现以兼容历史接口 */
}

/**
 * @brief  RTC 唤醒定时器中断回调（由 HAL_RTCEx_WakeUpTimerIRQHandler 自动调用）
 *         发送 RTC_TICK 事件到事件队列，触发软件定时器处理
 */
void HAL_RTCEx_WakeUpTimerEventCallback(RTC_HandleTypeDef *hrtc)
{
    (void)hrtc;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    event_t evt = { .id = EVENT_RTC_TICK, .param = 0 };
    xQueueSendFromISR(event_queue, &evt, &xHigherPriorityTaskWoken);
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

void RTC_TAMP_IRQHandler(void)
{
    HAL_RTCEx_WakeUpTimerIRQHandler(&hrtc);
}

void RTC_SetWakeUpCounter(uint32_t wake_up_counter)
{
    /* 先禁用唤醒定时器，更新计数值后重新使能 */
    CLEAR_BIT(RTC->CR, RTC_CR_WUTE);
    WRITE_REG(RTC->WUTR, wake_up_counter);
    SET_BIT(RTC->CR, RTC_CR_WUTE);
}

#else
/* ========== 测试环境空桩 ========== */
void RTC_Init(void)
{
    hrtc.Instance = (RTC_TypeDef *)0;
    HAL_RTC_Init(&hrtc);
}
void RTC_Start(void) {}
void RTC_TAMP_IRQHandler(void) {}
void RTC_SetWakeUpCounter(uint32_t wake_up_counter) { (void)wake_up_counter; }

#endif

/* ========== 软件定时器 API（测试和非测试共享）========== */
#ifndef TEST
rtc_timer_handle_t RTC_TimerCreate(uint32_t period_ms, uint8_t mode,
                                    rtc_timer_cb_t callback, void *arg)
{
    rtc_timer_t *t = pvPortMalloc(sizeof(rtc_timer_t));
    if (!t) return NULL;
    t->period_ms = period_ms;
    t->remaining_ms = period_ms;
    t->mode = mode;
    t->callback = callback;
    t->arg = arg;
    t->next = NULL;

    taskENTER_CRITICAL();
    if (!timer_head) {
        timer_head = t;
    } else {
        rtc_timer_t *p = timer_head;
        while (p->next) p = p->next;
        p->next = t;
    }
    taskEXIT_CRITICAL();
    return (rtc_timer_handle_t)t;
}

void RTC_TimerStart(rtc_timer_handle_t handle)
{
    rtc_timer_t *t = (rtc_timer_t *)handle;
    taskENTER_CRITICAL();
    t->remaining_ms = t->period_ms;
    taskEXIT_CRITICAL();
}

void RTC_TimerStop(rtc_timer_handle_t handle)
{
    rtc_timer_t *t = (rtc_timer_handle_t)handle;
    taskENTER_CRITICAL();
    t->remaining_ms = 0;
    taskEXIT_CRITICAL();
}

void RTC_TimerDelete(rtc_timer_handle_t handle)
{
    rtc_timer_t *t = (rtc_timer_handle_t)handle;
    taskENTER_CRITICAL();
    if (timer_head == t) {
        timer_head = t->next;
    } else {
        rtc_timer_t *p = timer_head;
        while (p && p->next != t) p = p->next;
        if (p) p->next = t->next;
    }
    taskEXIT_CRITICAL();
    vPortFree(t);
}
#else
static rtc_timer_t timer_pool[8];
static int timer_pool_idx = 0;

rtc_timer_handle_t RTC_TimerCreate(uint32_t period_ms, uint8_t mode,
                                    rtc_timer_cb_t callback, void *arg) {
    if (timer_pool_idx >= 8) return NULL;
    rtc_timer_t *t = &timer_pool[timer_pool_idx++];
    t->period_ms = period_ms;
    t->remaining_ms = period_ms;
    t->mode = mode;
    t->callback = callback;
    t->arg = arg;
    t->next = NULL;
    
    if (!timer_head) {
        timer_head = t;
    } else {
        rtc_timer_t *p = timer_head;
        while (p->next) p = p->next;
        p->next = t;
    }
    return (rtc_timer_handle_t)t;
}

void RTC_TimerStart(rtc_timer_handle_t handle) {
    rtc_timer_t *t = (rtc_timer_t *)handle;
    t->remaining_ms = t->period_ms;
}

void RTC_TimerStop(rtc_timer_handle_t handle) {
    rtc_timer_t *t = (rtc_timer_handle_t)handle;
    t->remaining_ms = 0;
}

void RTC_TimerDelete(rtc_timer_handle_t handle) {
    rtc_timer_t *t = (rtc_timer_handle_t)handle;
    if (timer_head == t) {
        timer_head = t->next;
    } else {
        rtc_timer_t *p = timer_head;
        while (p && p->next != t) p = p->next;
        if (p) p->next = t->next;
    }
}
#endif

void RTC_ProcessTimers(void)
{
    rtc_timer_t *t = timer_head;
    while (t) {
        /* 提前保存下一个节点，防止回调中删除当前定时器导致 use-after-free */
        rtc_timer_t *next = t->next;
        if (t->remaining_ms > 0) {
            if (t->remaining_ms <= RTC_TICK_INTERVAL_MS) {
                t->remaining_ms = 0;
                if (t->callback) t->callback(t->arg);
                if (t->mode == RTC_TIMER_MODE_PERIODIC)
                    t->remaining_ms = t->period_ms;
            } else {
                t->remaining_ms -= RTC_TICK_INTERVAL_MS;
            }
        }
        t = next;
    }
}

/* ---------- 时间读写（使用 HAL 安全函数） ---------- */
void RTC_GetTime(rtc_time_t *time)
{
    RTC_TimeTypeDef sTime = {0};
    RTC_DateTypeDef sDate = {0};
    HAL_RTC_GetTime(&hrtc, &sTime, RTC_FORMAT_BIN);
    HAL_RTC_GetDate(&hrtc, &sDate, RTC_FORMAT_BIN);
    time->sec   = sTime.Seconds;
    time->min   = sTime.Minutes;
    time->hour  = sTime.Hours;
    time->day   = sDate.Date;
    time->month = sDate.Month;
    time->year  = sDate.Year;
}

void RTC_SetTime(rtc_time_t *time)
{
    RTC_TimeTypeDef sTime = {0};
    RTC_DateTypeDef sDate = {0};
    sTime.Seconds = time->sec;
    sTime.Minutes = time->min;
    sTime.Hours   = time->hour;
    sDate.Date    = time->day;
    sDate.Month   = time->month;
    sDate.Year    = time->year;
    HAL_RTC_SetTime(&hrtc, &sTime, RTC_FORMAT_BIN);
    HAL_RTC_SetDate(&hrtc, &sDate, RTC_FORMAT_BIN);
}

void RTC_AdjustDrift(int16_t ppm)
{
    HAL_RTCEx_SetSmoothCalib(&hrtc,
                            RTC_SMOOTHCALIB_PERIOD_32SEC,
                            RTC_SMOOTHCALIB_PLUSPULSES_RESET,
                            (uint32_t)ppm);
}