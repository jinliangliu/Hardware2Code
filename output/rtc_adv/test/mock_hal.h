#ifndef MOCK_HAL_H
#define MOCK_HAL_H

#include <stdint.h>
#include <stdbool.h>

/* ======================================================================
 * CMSIS‑like definitions
 * ====================================================================== */
#define __IO       volatile
#define __I        volatile const
#define __O        volatile
#define __WEAK     __attribute__((weak))
#define STM32G0B1xx

/* ======================================================================
 * GPIO stubs
 * ====================================================================== */
typedef uint32_t GPIO_TypeDef;

#define GPIOA  ((GPIO_TypeDef *)0)
#define GPIOB  ((GPIO_TypeDef *)0)
#define GPIOC  ((GPIO_TypeDef *)0)
#define GPIOD  ((GPIO_TypeDef *)0)
#define GPIOE  ((GPIO_TypeDef *)0)
#define GPIOF  ((GPIO_TypeDef *)0)

#define GPIO_PIN_0   ((uint16_t)0x0001)
#define GPIO_PIN_1   ((uint16_t)0x0002)
#define GPIO_PIN_2   ((uint16_t)0x0004)
#define GPIO_PIN_3   ((uint16_t)0x0008)
#define GPIO_PIN_4   ((uint16_t)0x0010)
#define GPIO_PIN_5   ((uint16_t)0x0020)
#define GPIO_PIN_6   ((uint16_t)0x0040)
#define GPIO_PIN_7   ((uint16_t)0x0080)
#define GPIO_PIN_8   ((uint16_t)0x0100)
#define GPIO_PIN_9   ((uint16_t)0x0200)
#define GPIO_PIN_10  ((uint16_t)0x0400)
#define GPIO_PIN_11  ((uint16_t)0x0800)
#define GPIO_PIN_12  ((uint16_t)0x1000)
#define GPIO_PIN_13  ((uint16_t)0x2000)
#define GPIO_PIN_14  ((uint16_t)0x4000)
#define GPIO_PIN_15  ((uint16_t)0x8000)

typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
    uint32_t Alternate;
} GPIO_InitTypeDef;

#define GPIO_MODE_OUTPUT_PP     1
#define GPIO_MODE_IT_FALLING    2
#define GPIO_MODE_AF_OD         3
#define GPIO_NOPULL             0
#define GPIO_PULLUP             1
#define GPIO_SPEED_FREQ_LOW     2
#define GPIO_SPEED_FREQ_HIGH    3

#define __HAL_RCC_GPIOA_CLK_ENABLE()
#define __HAL_RCC_GPIOB_CLK_ENABLE()
#define __HAL_RCC_GPIOC_CLK_ENABLE()
#define __HAL_RCC_GPIOD_CLK_ENABLE()
#define __HAL_RCC_GPIOE_CLK_ENABLE()
#define __HAL_RCC_GPIOF_CLK_ENABLE()
#define __HAL_RCC_RTC_ENABLE()

/* ======================================================================
 * NVIC stubs
 * ====================================================================== */
typedef int32_t IRQn_Type;

#define EXTI0_1_IRQn    0
#define EXTI2_3_IRQn    1
#define EXTI4_15_IRQn   2
#define RTC_TAMP_IRQn   3

/* ======================================================================
 * RCC stubs
 * ====================================================================== */
 /* HAL status type (used by RTC init) */
typedef uint32_t HAL_StatusTypeDef;
/* For test builds, provide a stub HAL_GetTick */
uint32_t HAL_GetTick(void);

#define RCC_RTCCLKSOURCE_LSI     1   /* or actual value from HAL, not critical */
#define RTC_OUTPUT_POLARITY_HIGH 0   /* dummy */
#define RTC_OUTPUT_TYPE_OPENDRAIN 0  /* dummy */

typedef struct {
    uint32_t OscillatorType;
    uint32_t HSIState;
    uint32_t HSICalibrationValue;
    uint32_t LSEState;
    uint32_t LSIState;
    struct {
        uint32_t PLLState;
    } PLL;
} RCC_OscInitTypeDef;

typedef struct {
    uint32_t ClockType;
    uint32_t SYSCLKSource;
    uint32_t AHBCLKDivider;
    uint32_t APB1CLKDivider;
} RCC_ClkInitTypeDef;

typedef struct {
    uint32_t PeriphClockSelection;
    uint32_t RTCClockSelection;
} RCC_PeriphCLKInitTypeDef;

#define RCC_OSCILLATORTYPE_HSI   0
#define RCC_HSI_ON               1
#define RCC_HSICALIBRATION_DEFAULT 0x10
#define RCC_PLL_NONE             0
#define RCC_CLOCKTYPE_HCLK       1
#define RCC_CLOCKTYPE_SYSCLK     2
#define RCC_CLOCKTYPE_PCLK1      4
#define RCC_SYSCLKSOURCE_HSI     0
#define RCC_SYSCLK_DIV1          0
#define RCC_HCLK_DIV1            0

#define RCC_OSCILLATORTYPE_LSE   1
#define RCC_OSCILLATORTYPE_LSI   2
#define RCC_LSE_ON               1
#define RCC_LSE_OFF              0
#define RCC_LSI_ON               1
#define RCC_RTCCLKSOURCE_LSE     1
#define RCC_PERIPHCLK_RTC        1

/* ======================================================================
 * RTC stubs
 * ====================================================================== */
typedef void RTC_TypeDef;
#define RTC  ((RTC_TypeDef *)0)

typedef struct {
    uint32_t HourFormat;
    uint32_t AsynchPrediv;
    uint32_t SynchPrediv;
    uint32_t OutPut;
} RTC_InitTypeDef;

typedef struct {
    RTC_TypeDef    *Instance;
    RTC_InitTypeDef Init;
} RTC_HandleTypeDef;

typedef struct {
    uint32_t Seconds;
    uint32_t Minutes;
    uint32_t Hours;
} RTC_TimeTypeDef;

typedef struct {
    uint32_t Date;
    uint32_t Month;
    uint32_t Year;
} RTC_DateTypeDef;

#define RTC_HOURFORMAT_24           0
#define RTC_OUTPUT_DISABLE          0
#define RTC_FORMAT_BIN              0
#define RTC_WAKEUPCLOCK_RTCCLK_DIV16 0
#define RTC_SMOOTHCALIB_PERIOD_32SEC 0
#define RTC_SMOOTHCALIB_PLUSPULSES_RESET 0

/* ======================================================================
 * I2C stubs
 * ====================================================================== */
typedef void I2C_TypeDef;
typedef struct {
    I2C_TypeDef    *Instance;
} I2C_HandleTypeDef;

/* ======================================================================
 * Common HAL constants
 * ====================================================================== */
#define HAL_OK      0
#define HAL_ERROR   1
#define HAL_TIMEOUT 2

/* ======================================================================
 * FreeRTOS stubs
 * ====================================================================== */
typedef void * QueueHandle_t;
typedef uint32_t TickType_t;
typedef void * TaskHandle_t;
typedef uint32_t BaseType_t;

#define pdFALSE        0
#define pdTRUE         1
#define pdPASS         1
#define portMAX_DELAY  0xFFFFFFFF

typedef enum {
    eNoAction,
    eSetBits
} eNotifyAction;

/* FreeRTOS functions */
QueueHandle_t xQueueCreate(uint32_t length, uint32_t itemSize);
BaseType_t xQueueReceive(QueueHandle_t queue, void *buffer, TickType_t wait);
BaseType_t xQueueSend(QueueHandle_t queue, const void *item, TickType_t wait);
BaseType_t xQueueSendFromISR(QueueHandle_t queue, const void *item, BaseType_t *pxWoken);
BaseType_t xTaskNotify(TaskHandle_t task, uint32_t value, eNotifyAction action);
BaseType_t xTaskNotifyFromISR(TaskHandle_t task, uint32_t value, eNotifyAction action, BaseType_t *pxWoken);
void portYIELD_FROM_ISR(BaseType_t xWoken);
void taskENTER_CRITICAL(void);
void taskEXIT_CRITICAL(void);
void *pvPortMalloc(size_t size);
void vPortFree(void *ptr);
void vTaskDelay(TickType_t ticks);

/* ======================================================================
 * Mock verification helpers
 * ====================================================================== */
#define MAX_GPIO_PINS  16

void mock_HAL_GPIO_Init_reset(void);
bool mock_HAL_GPIO_Init_called(void);
uint32_t mock_HAL_GPIO_Init_get_count(void);
uint32_t mock_HAL_GPIO_Init_get_pin(uint32_t index);
uint32_t mock_HAL_GPIO_Init_get_mode(uint32_t index);

void mock_HAL_RTC_Init_reset(void);
bool mock_HAL_RTC_Init_called(void);

void mock_HAL_I2C_Init_reset(void);
bool mock_HAL_I2C_Init_called(void);

void mock_HAL_NVIC_EnableIRQ_reset(void);
bool mock_HAL_NVIC_EnableIRQ_called_with(IRQn_Type IRQn);

/* ======================================================================
 * HAL function prototypes (stubs)
 * ====================================================================== */
void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *init);
void HAL_NVIC_EnableIRQ(IRQn_Type IRQn);
void HAL_NVIC_SetPriority(IRQn_Type IRQn, uint32_t prio, uint32_t subprio);
void HAL_I2C_Init(I2C_HandleTypeDef *hi2c);

int  HAL_RCC_OscConfig(RCC_OscInitTypeDef *osc);
int  HAL_RCC_ClockConfig(RCC_ClkInitTypeDef *clk, uint32_t FLatency);
int  HAL_RCCEx_PeriphCLKConfig(RCC_PeriphCLKInitTypeDef *pclk);
int  HAL_RTC_Init(RTC_HandleTypeDef *hrtc);

void HAL_PWR_EnableBkUpAccess(void);
void HAL_RTCEx_WakeUpTimerIRQHandler(RTC_HandleTypeDef *hrtc);
void HAL_RTCEx_DeactivateWakeUpTimer(RTC_HandleTypeDef *hrtc);
void HAL_RTCEx_SetWakeUpTimer_IT(RTC_HandleTypeDef *hrtc, uint32_t wakeup_counter, uint32_t clock);
void HAL_RTC_GetTime(RTC_HandleTypeDef *hrtc, RTC_TimeTypeDef *sTime, uint32_t format);
void HAL_RTC_SetTime(RTC_HandleTypeDef *hrtc, RTC_TimeTypeDef *sTime, uint32_t format);
void HAL_RTC_GetDate(RTC_HandleTypeDef *hrtc, RTC_DateTypeDef *sDate, uint32_t format);
void HAL_RTC_SetDate(RTC_HandleTypeDef *hrtc, RTC_DateTypeDef *sDate, uint32_t format);
void HAL_RTCEx_SetSmoothCalib(RTC_HandleTypeDef *hrtc, uint32_t period, uint32_t pulse, uint32_t ppm);
void HAL_SuspendTick(void);
void HAL_ResumeTick(void);
void vTaskStepTick(uint32_t ticks);


typedef void TIM_HandleTypeDef;
void HAL_InitTick(uint32_t TickPriority);
void HAL_TIM_Base_Start_IT(TIM_HandleTypeDef *htim);

#endif /* MOCK_HAL_H */