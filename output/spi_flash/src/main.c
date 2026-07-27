#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"

/* Include driver headers for each peripheral */
#include "drv_flash.h"

/* Include event manager header (always present) */
#include "event_mgr.h"




/* GPIO initialization function */
void MX_GPIO_Init(void);

/* ------- Auto-generated pin definitions ------- */
#define LED_GPIO_Port  GPIOC
#define LED_GPIO_Pin   GPIO_PIN_0

/* ------- I2C Handles (if I2C peripherals are used) ------- */

/* ------- SPI Handles (if SPI peripherals are used) ------- */
SPI_HandleTypeDef hspi1;

/* ------- UART Handles (if UART peripherals are used) ------- */

/* ------- Task handles ------- */
TaskHandle_t flash_test_task_handle = NULL;
TaskHandle_t led_task_handle = NULL;

/* ------- Task prototypes ------- */
void flash_test_task(void *pvParameters);
void led_task(void *pvParameters);



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
}

/* ------- I2C initialization (if peripherals with I2C are present) ------- */

/* ------- SPI initialization (if peripherals with SPI are present) ------- */
static void MX_SPI1_Init(void)
{
    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi1.Init.NSS = SPI_NSS_SOFT;
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    if (HAL_SPI_Init(&hspi1) != HAL_OK) while(1);
}

/* ------- UART initialization (if UART peripherals are present) ------- */

/* ------- Main ------- */
int main(void)
{
    HAL_Init();

    /* 使能调试模块在 STOP 模式下的时钟，保持 SWD 连接 */
    DBG->CR |= DBG_CR_DBG_STOP;

    SystemClock_Config();

    /* 系统时钟配置完成后，重新初始化 HAL 时基（TIM14），
       确保 HAL_GetTick() 使用正确的时钟频率。
       RTC_WakeUp_Config 内部调用 HAL_RTCEx_SetWakeUpTimer_IT 会用到 HAL_GetTick */
    HAL_InitTick(TICK_INT_PRIORITY);


    /* Initialize all configured peripherals */
    MX_GPIO_Init();


    /* Initialize the event manager */
    EventMgr_Init();

    
    /* Initialize I2C and internal peripherals */
    MX_SPI1_Init();
    spi_flash_init(&hspi1);



    /* Create application tasks (user-defined) */
    xTaskCreate( flash_test_task, "flash_test_task", 512, NULL, 2, &flash_test_task_handle );
    xTaskCreate( led_task, "led_task", 128, NULL, 2, &led_task_handle );





    /* Create the central event manager task (highest priority) */
    xTaskCreate(EventMgr_Task, "event_mgr", 512, NULL, configMAX_PRIORITIES - 1, NULL);




    vTaskStartScheduler();
    while(1);
}

/* ------- Task implementations ------- */
void flash_test_task(void *pvParameters)
{
    while(1) {
        vTaskDelay(1000);
    }
}
void led_task(void *pvParameters)
{
    while(1) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        HAL_GPIO_TogglePin( LED_GPIO_Port, LED_GPIO_Pin );
    }
}

void led_task_notify(void) {
    if (led_task_handle) {
        xTaskNotifyGive(led_task_handle);
    }
}

