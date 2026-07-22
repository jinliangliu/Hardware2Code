#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "stm32g0xx_hal_tim.h"

/* Include driver headers for each peripheral */
#include "drv_adc.h"
#include "drv_uart_debug.h"

/* Include event manager header (always present) */
#include "event_mgr.h"

/* GPIO initialization function */
void MX_GPIO_Init(void);

/* ------- Auto-generated pin definitions ------- */
#define LED_GPIO_Port  GPIOC
#define LED_GPIO_Pin   GPIO_PIN_0

/* ------- I2C Handles (if I2C peripherals are used) ------- */

/* ------- SPI Handles (if SPI peripherals are used) ------- */

/* ------- UART Handles (if UART peripherals are used) ------- */
UART_HandleTypeDef huart_uart_debug;

/* ------- Task handles ------- */
TaskHandle_t led_task_handle = NULL;

/* ------- Task prototypes ------- */
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

//    HAL_SYSTICK_Config(HAL_RCC_GetHCLKFreq() / 1000);
//    HAL_SYSTICK_CLKSourceConfig(SYSTICK_CLKSOURCE_HCLK);
//    HAL_NVIC_SetPriority(SysTick_IRQn, 0, 0);
}

/* ------- I2C initialization (if peripherals with I2C are present) ------- */

/* ------- SPI initialization (if peripherals with SPI are present) ------- */

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

    
    /* Initialize I2C and internal peripherals */
static void MX_USART2_UART_Init(void) {
    /* 引脚已由 MX_GPIO_Init 配置 */
    __HAL_RCC_USART2_CLK_ENABLE();
    huart_uart_debug.Instance = USART2;
    huart_uart_debug.Init.BaudRate = 115200;
    huart_uart_debug.Init.WordLength = UART_WORDLENGTH_8B;
    huart_uart_debug.Init.StopBits = UART_STOPBITS_1;
    huart_uart_debug.Init.Parity = UART_PARITY_NONE;
    huart_uart_debug.Init.Mode = UART_MODE_TX_RX;
    huart_uart_debug.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart_uart_debug.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart_uart_debug) != HAL_OK) while(1);
}

    

    /* Create application tasks (user-defined) */
    xTaskCreate( led_task, "led_task", 128, NULL, 2, &led_task_handle );

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

void led_task_notify(void) {
    if (led_task_handle) {
        xTaskNotify(led_task_handle, 0, eSetBits);
    }
}
