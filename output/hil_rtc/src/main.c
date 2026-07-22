/* HIL Test Firmware for STM32G0B1RET6 */
#include "stm32g0xx_hal.h"
#include "stm32g0xx_hal_rtc.h"
#include <string.h>
#include <stdio.h>

/* ----- UART handle ----- */
UART_HandleTypeDef huart2;

/* ----- LED pin (hardcoded for PC0) ----- */
#define LED_GPIO_Port  GPIOC
#define LED_GPIO_Pin   GPIO_PIN_0

/* ----- Lightweight test framework ----- */
static int tests_passed = 0;
static int tests_failed = 0;

#define STRINGIFY(x) #x

#define TEST_PASS() do { tests_passed++; return; } while(0)

#define TEST_FAIL(msg) do { \
    char buf[100]; \
    int len = snprintf(buf, sizeof(buf), "FAIL: %s\r\n", msg); \
    HAL_UART_Transmit(&huart2, (uint8_t *)buf, len, 100); \
    tests_failed++; \
    return; \
} while(0)

#define TEST_ASSERT(cond) do { \
    if (!(cond)) { TEST_FAIL(__FILE__ ":" STRINGIFY(__LINE__) " assert failed"); } \
} while(0)

#define TEST_ASSERT_EQUAL(expected, actual) do { \
    if ((expected) != (actual)) { \
        char buf[80]; \
        int len = snprintf(buf, sizeof(buf), "FAIL: expected %d, was %d\r\n", (int)(expected), (int)(actual)); \
        HAL_UART_Transmit(&huart2, (uint8_t *)buf, len, 100); \
        tests_failed++; \
        return; \
    } \
} while(0)

void run_test(void (*test)(void), const char *name) {
    char buf[60];
    int len = snprintf(buf, sizeof(buf), "Running %s...\r\n", name);
    HAL_UART_Transmit(&huart2, (uint8_t *)buf, len, 100);
    test();
}

/* ----- System Clock Configuration (HSI 16MHz, no SysTick config) ----- */
void SystemClock_Config(void) {
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

/* ----- GPIO Initialization (LED) ----- */
void MX_GPIO_Init(void) {
    __HAL_RCC_GPIOC_CLK_ENABLE();
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = LED_GPIO_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LED_GPIO_Port, &GPIO_InitStruct);
}

/* ----- UART2 Initialization (HAL) ----- */
static void MX_USART2_UART_Init(void) {
    __HAL_RCC_GPIOA_CLK_ENABLE();
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF1_USART2;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    __HAL_RCC_USART2_CLK_ENABLE();
    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart2) != HAL_OK) while(1);
}

/* ----- Test Cases (auto-generated) ----- */
void test_RTC_Init(void) {

            RTC_HandleTypeDef hrtc;
            __HAL_RCC_RTC_ENABLE();
            HAL_PWR_EnableBkUpAccess();

            /* 配置 LSE 和 LSI，优先使用 LSE，若失败则回退至 LSI */
            RCC_OscInitTypeDef RCC_OscInitStruct = {0};
            RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_LSE | RCC_OSCILLATORTYPE_LSI;
            RCC_OscInitStruct.LSEState = RCC_LSE_ON;
            RCC_OscInitStruct.LSIState = RCC_LSI_ON;
            RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;

            if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
                /* 如果 LSE 立即返回错误（例如无外部晶振），强制回退至 LSI */
                RCC_OscInitStruct.LSEState = RCC_LSE_OFF;
                HAL_RCC_OscConfig(&RCC_OscInitStruct);
            }

            /* 等待所选时钟源就绪 */
            if (RCC_OscInitStruct.LSEState == RCC_LSE_ON) {
                uint32_t tickstart = HAL_GetTick();
                while ((RCC->BDCR & RCC_BDCR_LSERDY) == 0U) {
                    if ((HAL_GetTick() - tickstart) > 500U) {
                        RCC_OscInitStruct.LSEState = RCC_LSE_OFF;
                        HAL_RCC_OscConfig(&RCC_OscInitStruct);
                        break;
                    }
                }
            } else {
                uint32_t tickstart = HAL_GetTick();
                while ((RCC->CSR & RCC_CSR_LSIRDY) == 0U) {
                    if ((HAL_GetTick() - tickstart) > 500U) break;
                }
            }

            RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};
            PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_RTC;
            PeriphClkInit.RTCClockSelection = (RCC_OscInitStruct.LSEState == RCC_LSE_ON) ?
                                            RCC_RTCCLKSOURCE_LSE : RCC_RTCCLKSOURCE_LSI;
            if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK) {
                PeriphClkInit.RTCClockSelection = RCC_RTCCLKSOURCE_LSI;
                HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit);
            }

            __HAL_RCC_RTC_ENABLE();
            HAL_Delay(1);   /* 确保时钟稳定 */

            hrtc.Instance = RTC;
            hrtc.Init.HourFormat = RTC_HOURFORMAT_24;
            hrtc.Init.AsynchPrediv = 127;
            hrtc.Init.SynchPrediv = 255;
            hrtc.Init.OutPut = RTC_OUTPUT_DISABLE;
            if (HAL_RTC_Init(&hrtc) != HAL_OK) {
                TEST_FAIL("HAL_RTC_Init failed");
            } else {
                TEST_PASS();
            }
        
}

int main(void) {
    HAL_Init();
    HAL_InitTick(TICK_INT_PRIORITY);    /* 使用 TIM14 作为 HAL 时基，与 rtc_adv 一致 */
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART2_UART_Init();

    /* Startup blink */
    for (int i = 0; i < 6; i++) {
        HAL_GPIO_TogglePin(LED_GPIO_Port, LED_GPIO_Pin);
        HAL_Delay(100);
    }

    char *start_msg = "START\r\n";
    HAL_UART_Transmit(&huart2, (uint8_t *)start_msg, strlen(start_msg), 100);

    run_test(test_RTC_Init, "test_RTC_Init");
    if (tests_failed == 0) {
        char *pass = "PASS\r\n";
        HAL_UART_Transmit(&huart2, (uint8_t *)pass, strlen(pass), 100);
    } else {
        tests_failed = 0;
    }

    char buf[80];
    int len = snprintf(buf, sizeof(buf), "\r\n%d Tests %d Failures\r\n", tests_passed, tests_failed);
    HAL_UART_Transmit(&huart2, (uint8_t *)buf, len, 100);

    char *end_msg = "END\r\n";
    HAL_UART_Transmit(&huart2, (uint8_t *)end_msg, strlen(end_msg), 100);

    HAL_GPIO_WritePin(LED_GPIO_Port, LED_GPIO_Pin, GPIO_PIN_SET);
    while (1);
}