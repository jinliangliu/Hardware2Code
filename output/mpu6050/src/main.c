#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

/* Include driver headers for each peripheral */
#include "drv_mpu6050.h"

/* GPIO initialization function */
void MX_GPIO_Init(void);

/* ------- Auto-generated pin definitions ------- */
#define LED_GPIO_Port  GPIOC
#define LED_GPIO_Pin   GPIO_PIN_0

/* ------- I2C Handles (if I2C peripherals are used) ------- */
I2C_HandleTypeDef hi2c1;

/* ------- Task handles ------- */
TaskHandle_t mpu6050_alert_task_handle = NULL;
TaskHandle_t led_task_handle = NULL;

/* ------- Task prototypes ------- */
void mpu6050_alert_task(void *pvParameters);
void led_task(void *pvParameters);

/* ------- System clock configuration (HSI 16MHz) ------- */
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

    HAL_SYSTICK_Config(HAL_RCC_GetHCLKFreq() / 1000);
    HAL_SYSTICK_CLKSourceConfig(SYSTICK_CLKSOURCE_HCLK);
    HAL_NVIC_SetPriority(SysTick_IRQn, 0, 0);
}

/* ------- I2C initialization (if peripherals with I2C are present) ------- */
static void MX_I2C1_Init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x2000090E;
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    if (HAL_I2C_Init(&hi2c1) != HAL_OK) while(1);
    /* Analog filter is enabled by default; no explicit call needed */
}

{% for p in peripherals %}
{% if p.type == 'Internal_RTC' %}
#include "drv_{{ p.name }}.h"
{% endif %}
{% endfor %}

/* ------- Main ------- */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    /* Initialize I2C and peripherals */
    MX_I2C1_Init();
    mpu6050_init(&hi2c1);

    /* Initialize internal peripherals */
    {% for p in peripherals %}
    {% if p.type == 'Internal_RTC' %}
    RTC_Init();
    {% endif %}
    {% endfor %}

    /* Create application tasks */
    xTaskCreate( mpu6050_alert_task, "mpu6050_alert_task", 512, NULL, 3, &mpu6050_alert_task_handle );
    xTaskCreate( led_task, "led_task", 128, NULL, 2, &led_task_handle );

    /* Create application tasks */
    {% for task in app_tasks %}
    xTaskCreate( {{ task.name }}, "{{ task.name }}", {{ task.stack_size | default(128) }}, NULL, {{ task.priority }}, &{{ task.name }}_handle );
    {% endfor %}

    /* Create RTC timer service task (if RTC used) */
    {% set has_rtc = peripherals | selectattr('type', 'equalto', 'Internal_RTC') | list %}
    {% if has_rtc %}
    TaskHandle_t rtc_svc_handle;
    xTaskCreate(RTC_TimerServiceTask, "rtc_timer_svc", 256, NULL, 4, &rtc_svc_handle);
    {% endif %}

    vTaskStartScheduler();
    while(1);
}

/* ------- Task implementations (auto-generated from app_tasks) ------- */
/* Task implementations ... */
/* Add a sample task using RTC timer:
void rtc_led_task(void *pvParameters)
{
    while(1) {
        HAL_GPIO_TogglePin(LED_GPIO_Port, LED_GPIO_Pin);
        vTaskDelay(1000);
    }
}
*/

void mpu6050_alert_task(void *pvParameters)
{
    /* Example: read accelerometer and toggle LED if X axis exceeds threshold */
    mpu6050_data_t sensor_data;
    while(1) {
        mpu6050_read(&sensor_data);
        if (sensor_data.accel_x > 1.0f || sensor_data.accel_x < -1.0f) {
            xTaskNotify( led_task_handle, 0, eSetBits );
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
void led_task(void *pvParameters)
{
    uint32_t ulNotifiedValue;
    while(1) {
        xTaskNotifyWait( 0x00, 0xFFFFFFFF, &ulNotifiedValue, portMAX_DELAY );
        HAL_GPIO_TogglePin( LED_GPIO_Port, LED_GPIO_Pin );
    }
}
