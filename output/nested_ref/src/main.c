#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"

/* Include driver headers for each peripheral */
#include "drv_rtc.h"

/* Include event manager header (always present) */
#include "event_mgr.h"

#include "statemachine.h"

/* GPIO initialization function */
void MX_GPIO_Init(void);

/* ------- Auto-generated pin definitions ------- */
#define LED_GPIO_Port  GPIOC
#define LED_GPIO_Pin   GPIO_PIN_0

/* ------- I2C Handles (if I2C peripherals are used) ------- */

/* ------- SPI Handles (if SPI peripherals are used) ------- */

/* ------- UART Handles (if UART peripherals are used) ------- */

/* ------- Task handles ------- */
TaskHandle_t led_task_handle = NULL;
TaskHandle_t rtc_demo_task_handle = NULL;

/* ------- Task prototypes ------- */
void led_task(void *pvParameters);
void rtc_demo_task(void *pvParameters);

/* ------- System clock configuration (HSI 16MHz default) ------- */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) while(1);

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK) while(1);

//    HAL_SYSTICK_Config(HAL_RCC_GetHCLKFreq() / 1000);
//    HAL_SYSTICK_CLKSourceConfig(SYSTICK_CLKSOURCE_HCLK);
//    HAL_NVIC_SetPriority(SysTick_IRQn, 0, 0);
}

/* ------- I2C initialization (if peripherals with I2C are present) ------- */

/* ------- SPI initialization (if peripherals with SPI are present) ------- */

/* ------- UART initialization (if UART peripherals are present) ------- */

/* ------- Main ------- */
int main(void)
{
    HAL_Init();

    /* 使能调试模块在 STOP 模式下的时钟，保持 SWD 连接 */
    DBG->CR |= DBG_CR_DBG_STOP;

    HAL_InitTick(TICK_INT_PRIORITY);
    
    SystemClock_Config();

    /* USER CODE BEGIN SysInit */
    SystemCoreClockUpdate();
    /* USER CODE END SysInit */

    /* Initialize all configured peripherals */
    MX_GPIO_Init();

    /* Initialize the event manager */
    EventMgr_Init();

    statemachine_init();
    
    /* Initialize I2C and internal peripherals */
    RTC_Init();
    RTC_Start();

    /* Create application tasks (user-defined) */
    xTaskCreate( led_task, "led_task", 128, NULL, 2, &led_task_handle );
    xTaskCreate( rtc_demo_task, "rtc_demo_task", 512, NULL, 3, &rtc_demo_task_handle );



    /* Create the central event manager task (highest priority) */
    xTaskCreate(EventMgr_Task, "event_mgr", 512, NULL, configMAX_PRIORITIES - 1, NULL);

    vTaskStartScheduler();
    while(1);
}

/* ------- Task implementations ------- */
void led_task(void *pvParameters)
{
    uint32_t ulNotifiedValue;
    while(1) {
        xTaskNotifyWait( 0x00, 0xFFFFFFFF, &ulNotifiedValue, portMAX_DELAY );
        HAL_GPIO_TogglePin( LED_GPIO_Port, LED_GPIO_Pin );
    }
}
void rtc_demo_task(void *pvParameters)
{
    rtc_time_t time;
    while(1) {
        RTC_GetTime(&time);
        event_t evt = { .id = EVENT_RTC_TICK, .param = 0 };
        xQueueSend(event_queue, &evt, 0);
        RTC_ProcessTimers();
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void led_task_notify(void) {
    if (led_task_handle) {
        xTaskNotify(led_task_handle, 0, eSetBits);
    }
}
