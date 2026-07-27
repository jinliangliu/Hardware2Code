#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"

/* Include driver headers for each peripheral */
#include "drv_rtc.h"
#include "drv_uart2.h"
#include "drv_iwdg.h"
#include "drv_fota.h"
#include "drv_fota_bspatch.h"

/* Include event manager header (always present) */
#include "event_mgr.h"

#include "statemachine.h"

#include "boot_app.h"


/* GPIO initialization function */
void MX_GPIO_Init(void);

/* ------- Auto-generated pin definitions ------- */
#define LED_GPIO_Port  GPIOC
#define LED_GPIO_Pin   GPIO_PIN_0

/* ------- I2C Handles (if I2C peripherals are used) ------- */

/* ------- SPI Handles (if SPI peripherals are used) ------- */

/* ------- UART Handles (if UART peripherals are used) ------- */
UART_HandleTypeDef huart_uart2;

/* ------- Task handles ------- */
TaskHandle_t led_task_handle = NULL;

/* ------- Task prototypes ------- */
void led_task(void *pvParameters);


void fota_task(void *arg);

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

/* ------- UART initialization (if UART peripherals are present) ------- */
static void MX_USART2_UART_Init(void)
{
    __HAL_RCC_USART2_CLK_ENABLE();
    huart_uart2.Instance = USART2;
    huart_uart2.Init.BaudRate = 115200;
    huart_uart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart_uart2.Init.StopBits = UART_STOPBITS_1;
    huart_uart2.Init.Parity = UART_PARITY_NONE;
    huart_uart2.Init.Mode = UART_MODE_TX_RX;
    huart_uart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart_uart2.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart_uart2) != HAL_OK) while(1);
}

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

    /*
     * App alive heartbeat: 2 quick blinks (100ms on/off each) to confirm App startup.
     * Distinct from Bootloader's 3 slow blinks (200ms). If you see 2 quick blinks after
     * the Bootloader's pattern, the App has started successfully.
     */
    HAL_GPIO_WritePin(LED_GPIO_Port, LED_GPIO_Pin, GPIO_PIN_RESET); /* LED on */
    HAL_Delay(100);
    HAL_GPIO_WritePin(LED_GPIO_Port, LED_GPIO_Pin, GPIO_PIN_SET);   /* LED off */
    HAL_Delay(100);
    HAL_GPIO_WritePin(LED_GPIO_Port, LED_GPIO_Pin, GPIO_PIN_RESET); /* LED on */
    HAL_Delay(100);
    HAL_GPIO_WritePin(LED_GPIO_Port, LED_GPIO_Pin, GPIO_PIN_SET);   /* LED off */
    HAL_Delay(100);

    /* Initialize the event manager */
    EventMgr_Init();

    statemachine_init();
    
    /* Initialize I2C and internal peripherals */
    RTC_Init();
    MX_USART2_UART_Init();


    RTC_Start();

    /* Create application tasks (user-defined) */
    xTaskCreate( led_task, "led_task", 128, NULL, 2, &led_task_handle );





    /* Create the central event manager task (highest priority) */
    xTaskCreate(EventMgr_Task, "event_mgr", 512, NULL, configMAX_PRIORITIES - 1, NULL);

    /* Initialize FOTA subsystem (protocol state machine + bspatch engine) */
    fota_init();
    xTaskCreate(fota_task, "fota", 512, NULL, 1, NULL);

    /* 初始化 IWDG 看门狗 — App 挂死后硬件复位，Bootloader 检测 boot_ok 缺失 */
    IWDG_Init();

    /* 标记启动成功 — Bootloader 在下次上电时检测此标志 */
    boot_app_mark_ok();

    /* Enable DBGMCU clock and keep debug interface active during STOP mode */
    __HAL_RCC_DBGMCU_CLK_ENABLE();
    HAL_DBGMCU_EnableDBGStopMode();

    vTaskStartScheduler();
    while(1);
}

/* ------- Task implementations ------- */
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

/*
 * FOTA task: polls the protocol state machine.
 * When a FOTA START command is received via UART interrupt,
 * the state machine transitions IDLE → RECEIVING and processes
 * incoming chunks automatically.
 */
void fota_task(void *arg) {
    (void)arg;
    for (;;) {
        fota_process();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
