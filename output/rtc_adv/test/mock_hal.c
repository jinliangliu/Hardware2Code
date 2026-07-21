#include "mock_hal.h"
#include "unity.h"
#include <string.h>
#include <stdlib.h>

/* ======================================================================
 * External variables
 * ====================================================================== */
TaskHandle_t led_task_handle = NULL;
QueueHandle_t event_queue = NULL;

/* ======================================================================
 * GPIO mock state (history based)
 * ====================================================================== */
static GPIO_InitTypeDef gpio_history[MAX_GPIO_PINS];
static uint32_t gpio_call_count = 0;

void mock_HAL_GPIO_Init_reset(void) {
    gpio_call_count = 0;
    memset(gpio_history, 0, sizeof(gpio_history));
}

bool mock_HAL_GPIO_Init_called(void) {
    return gpio_call_count > 0;
}

uint32_t mock_HAL_GPIO_Init_get_count(void) {
    return gpio_call_count;
}

uint32_t mock_HAL_GPIO_Init_get_pin(uint32_t index) {
    if (index < gpio_call_count) {
        return gpio_history[index].Pin;
    }
    return 0;
}

uint32_t mock_HAL_GPIO_Init_get_mode(uint32_t index) {
    if (index < gpio_call_count) {
        return gpio_history[index].Mode;
    }
    return 0;
}

/* Called by the HAL_GPIO_Init stub */
static void record_gpio_init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *init) {
    (void)GPIOx;
    if (gpio_call_count < MAX_GPIO_PINS) {
        memcpy(&gpio_history[gpio_call_count], init, sizeof(GPIO_InitTypeDef));
        gpio_call_count++;
    }
}

/* ======================================================================
 * RTC mock state
 * ====================================================================== */
static bool rtc_init_called = false;

void mock_HAL_RTC_Init_reset(void) { rtc_init_called = false; }
bool mock_HAL_RTC_Init_called(void) { return rtc_init_called; }

/* ======================================================================
 * I2C mock state
 * ====================================================================== */
static bool i2c_init_called = false;

void mock_HAL_I2C_Init_reset(void) { i2c_init_called = false; }
bool mock_HAL_I2C_Init_called(void) { return i2c_init_called; }

/* ======================================================================
 * NVIC mock state
 * ====================================================================== */
static IRQn_Type last_irq = -1;
static bool nvic_called = false;

void mock_HAL_NVIC_EnableIRQ_reset(void) { last_irq = -1; nvic_called = false; }
bool mock_HAL_NVIC_EnableIRQ_called_with(IRQn_Type IRQn) {
    return nvic_called && (last_irq == IRQn);
}

static void record_nvic(IRQn_Type IRQn) {
    last_irq = IRQn;
    nvic_called = true;
}

/* ======================================================================
 * Real HAL function stubs (call the internal recorders)
 * ====================================================================== */
void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *init) {
    record_gpio_init(GPIOx, init);
}

void HAL_NVIC_EnableIRQ(IRQn_Type IRQn) {
    record_nvic(IRQn);
}

void HAL_NVIC_SetPriority(IRQn_Type IRQn, uint32_t prio, uint32_t subprio) {
    (void)IRQn; (void)prio; (void)subprio;
}

int HAL_RCC_OscConfig(RCC_OscInitTypeDef *osc) {
    (void)osc;
    return HAL_OK;
}

int HAL_RCC_ClockConfig(RCC_ClkInitTypeDef *clk, uint32_t FLatency) {
    (void)clk; (void)FLatency;
    return HAL_OK;
}

int HAL_RCCEx_PeriphCLKConfig(RCC_PeriphCLKInitTypeDef *pclk) {
    (void)pclk;
    return HAL_OK;
}

int HAL_RTC_Init(RTC_HandleTypeDef *hrtc) {
    rtc_init_called = true;
    (void)hrtc;
    return HAL_OK;
}

void HAL_I2C_Init(I2C_HandleTypeDef *hi2c) {
    i2c_init_called = true;
    (void)hi2c;
}

void HAL_PWR_EnableBkUpAccess(void) {}

void HAL_RTCEx_WakeUpTimerIRQHandler(RTC_HandleTypeDef *hrtc) { (void)hrtc; }
void HAL_RTCEx_DeactivateWakeUpTimer(RTC_HandleTypeDef *hrtc) { (void)hrtc; }
void HAL_RTCEx_SetWakeUpTimer_IT(RTC_HandleTypeDef *hrtc, uint32_t wakeup_counter, uint32_t clock) {
    (void)hrtc; (void)wakeup_counter; (void)clock;
}

void HAL_RTC_GetTime(RTC_HandleTypeDef *hrtc, RTC_TimeTypeDef *sTime, uint32_t format) {
    (void)hrtc; (void)format;
    if (sTime) memset(sTime, 0, sizeof(*sTime));
}

void HAL_RTC_SetTime(RTC_HandleTypeDef *hrtc, RTC_TimeTypeDef *sTime, uint32_t format) {
    (void)hrtc; (void)sTime; (void)format;
}

void HAL_RTC_GetDate(RTC_HandleTypeDef *hrtc, RTC_DateTypeDef *sDate, uint32_t format) {
    (void)hrtc; (void)format;
    if (sDate) memset(sDate, 0, sizeof(*sDate));
}

void HAL_RTC_SetDate(RTC_HandleTypeDef *hrtc, RTC_DateTypeDef *sDate, uint32_t format) {
    (void)hrtc; (void)sDate; (void)format;
}

void HAL_RTCEx_SetSmoothCalib(RTC_HandleTypeDef *hrtc, uint32_t period, uint32_t pulse, uint32_t ppm) {
    (void)hrtc; (void)period; (void)pulse; (void)ppm;
}

void HAL_SuspendTick(void) {}
void HAL_ResumeTick(void) {}
void vTaskStepTick(uint32_t ticks) { (void)ticks; }

/* ======================================================================
 * FreeRTOS stubs
 * ====================================================================== */
QueueHandle_t xQueueCreate(uint32_t length, uint32_t itemSize) {
    (void)length; (void)itemSize;
    return (QueueHandle_t)1;
}

BaseType_t xQueueReceive(QueueHandle_t queue, void *buffer, TickType_t wait) {
    (void)queue; (void)buffer; (void)wait;
    return pdFALSE;
}

BaseType_t xQueueSend(QueueHandle_t queue, const void *item, TickType_t wait) {
    (void)queue; (void)item; (void)wait;
    return pdPASS;
}

BaseType_t xQueueSendFromISR(QueueHandle_t queue, const void *item, BaseType_t *pxWoken) {
    (void)queue; (void)item;
    if (pxWoken) *pxWoken = pdFALSE;
    return pdPASS;
}

BaseType_t xTaskNotify(TaskHandle_t task, uint32_t value, eNotifyAction action) {
    (void)task; (void)value; (void)action;
    return pdPASS;
}

BaseType_t xTaskNotifyFromISR(TaskHandle_t task, uint32_t value, eNotifyAction action, BaseType_t *pxWoken) {
    (void)task; (void)value; (void)action;
    if (pxWoken) *pxWoken = pdFALSE;
    return pdPASS;
}

void portYIELD_FROM_ISR(BaseType_t xWoken) { (void)xWoken; }

void taskENTER_CRITICAL(void) {}
void taskEXIT_CRITICAL(void) {}

void *pvPortMalloc(size_t size) { return malloc(size); }
void vPortFree(void *ptr) { free(ptr); }
void vTaskDelay(TickType_t ticks) { (void)ticks; }

uint32_t HAL_GetTick(void) {
    return 0;   /* simple stub, not used in current tests */
}

void HAL_InitTick(uint32_t TickPriority) { (void)TickPriority; }
void HAL_TIM_Base_Start_IT(TIM_HandleTypeDef *htim) { (void)htim; }