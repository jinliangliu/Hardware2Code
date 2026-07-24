   
   #ifdef TEST
   #include "mock_hal.h"
   #else
   #include "stm32g0xx_hal.h"
   #include "FreeRTOS.h"
   #include "task.h"
   #include "queue.h"
   #endif
   
   #include "drv_rtc.h"
   #include "event_mgr.h"
   
   /* Private handle */
   static RTC_HandleTypeDef hrtc;
   
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
   
   static void RTC_WakeUp_Config(void)
   {
       /* LSI = 32768 Hz, DIV16 = 2048 Hz, (204+1) = 10 Hz = 100ms */
       /* 计算: (LSI / 16) / (wake_up_counter + 1) = 1 / RTC_TICK_INTERVAL_MS */
       uint32_t wake_up_counter = (32768 / 16 / 1000 * RTC_TICK_INTERVAL_MS) - 1;
       HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, wake_up_counter, RTC_WAKEUPCLOCK_RTCCLK_DIV16);
   }
   
   void RTC_Init(void)
   {
       /* 1. 强制使能 PWR 时钟并解锁备份域 */
       __HAL_RCC_PWR_CLK_ENABLE();
       HAL_PWR_EnableBkUpAccess();
       SET_BIT(PWR->CR1, PWR_CR1_DBP);
   
       /* 2. 启动 LSI 并等待就绪 */
       RCC->CSR |= RCC_CSR_LSION;
       while ((RCC->CSR & RCC_CSR_LSIRDY) == 0U);
   
       /* 3. 选择 LSI 作为 RTC 时钟源 (0x02) 并使能 RTC 时钟 */
       MODIFY_REG(RCC->BDCR, RCC_BDCR_RTCSEL, (0x02UL << RCC_BDCR_RTCSEL_Pos));
       SET_BIT(RCC->BDCR, RCC_BDCR_RTCEN);
       while ((RCC->BDCR & RCC_BDCR_RTCEN) == 0U);
   
       /* 4. 如果 RTC 已处于初始化模式，先退出 */
       if (RTC->ICSR & RTC_ICSR_INITF) {
           RTC->ICSR &= ~RTC_ICSR_INIT;
           volatile uint32_t delay = 10000;
           while (delay--);
       }
   
       /* 5. 进入初始化模式 */
       SET_BIT(RTC->ICSR, RTC_ICSR_INIT);
       uint32_t timeout = 1000000;
       while (!(RTC->ICSR & RTC_ICSR_INITF)) {
           if (--timeout == 0) break;
       }
   
       /* 6. 配置预分频器 (1Hz) */
       RTC->PRER = (127U << 16) | (255U);
       RTC->CR = (RTC->CR & ~(RTC_CR_FMT | RTC_CR_OSEL)) | RTC_HOURFORMAT_24;
       RTC->SCR = 0x00;
   
       /* 退出初始化模式 */
       RTC->ICSR &= ~RTC_ICSR_INIT;
       timeout = 1000000;
       while (RTC->ICSR & RTC_ICSR_INITF) {
           if (--timeout == 0) break;
       }
   
       /* 等待同步 RSF */
       timeout = 1000000;
       while (!(RTC->ICSR & RTC_ICSR_RSF)) {
           if (--timeout == 0) break;
       }
   
       /* 配置唤醒定时器 (100ms) */
       RTC_WakeUp_Config();
   
       /* 使能 RTC 中断 */
       HAL_NVIC_SetPriority(RTC_TAMP_IRQn, 5, 0);
       HAL_NVIC_EnableIRQ(RTC_TAMP_IRQn);
   
       /* 给 hrtc 赋值 Instance 以兼容 HAL 时间读写 */
       hrtc.Instance = RTC;

       /* 启动分钟/小时定时器 */
       rtc_timer_handle_t t_min = RTC_TimerCreate(60000, RTC_TIMER_MODE_PERIODIC, minute_timer_cb, NULL);
       rtc_timer_handle_t t_hour = RTC_TimerCreate(3600000, RTC_TIMER_MODE_PERIODIC, hour_timer_cb, NULL);
       RTC_TimerStart(t_min);
       RTC_TimerStart(t_hour);
   }
   
   void RTC_Start(void)
   {
       /* 仅使能唤醒中断（已在 Init 中完成） */
   }
   
   void RTC_TAMP_IRQHandler(void)
   {
       if (RTC->SR & RTC_SR_WUTF) {
           RTC->SCR = RTC_SCR_CWUTF;
           BaseType_t xHigherPriorityTaskWoken = pdFALSE;
           event_t evt = { .id = EVENT_RTC_TICK, .param = 0 };
           xQueueSendFromISR(event_queue, &evt, &xHigherPriorityTaskWoken);
           portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
       }
   }
   
   void RTC_SetWakeUpCounter(uint32_t wake_up_counter)
   {
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
           t = t->next;
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