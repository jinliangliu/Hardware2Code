
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

/* GPIO initialization function */
void MX_GPIO_Init(void);

/* ------- Auto-generated pin definitions ------- */
#define LED_GPIO_Port  GPIOC
#define LED_GPIO_Pin   GPIO_PIN_0

/* ------- Task handles ------- */
TaskHandle_t button_led_task_handle = NULL;

/* ------- Task prototypes ------- */
void button_led_task(void *pvParameters);

/* ------- Basic system clock configuration (to be customized) ------- */
void SystemClock_Config(void)
{
    /* Default: HSI 16MHz, no PLL. Configure PLL if required. */
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* Enable HSI and wait for it to be ready */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        while(1);
    }

    /* Configure system clocks (HSI as SYSCLK, AHB/APB prescalers) */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
    {
        while(1);
    }

    /* Optional: configure SysTick to generate 1ms interrupt */
    HAL_SYSTICK_Config(HAL_RCC_GetHCLKFreq() / 1000);
    HAL_SYSTICK_CLKSourceConfig(SYSTICK_CLKSOURCE_HCLK);
    HAL_NVIC_SetPriority(SysTick_IRQn, 0, 0);
}

/* ------- Main ------- */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    xTaskCreate( button_led_task, "button_led_task", 128, NULL, 2, &button_led_task_handle );

    vTaskStartScheduler();

    while(1);
}

/* ------- LED toggle task (waits for button notification) ------- */
void button_led_task(void *pvParameters)
{
    uint32_t ulNotifiedValue;
    while(1)
    {
        xTaskNotifyWait( 0x00, 0xFFFFFFFF, &ulNotifiedValue, portMAX_DELAY );
        HAL_GPIO_TogglePin( LED_GPIO_Port, LED_GPIO_Pin );
    }
}