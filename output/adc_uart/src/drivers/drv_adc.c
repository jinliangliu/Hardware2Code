#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif
#include "drv_adc.h"

#ifndef TEST
static ADC_HandleTypeDef hadc;
#endif

void ADC_Init(void) {
#ifndef TEST
    __HAL_RCC_ADC_CLK_ENABLE();
    hadc.Instance = ADC1;
    hadc.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV2;
    hadc.Init.Resolution = ADC_RESOLUTION_12B;
    hadc.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc.Init.LowPowerAutoWait = DISABLE;
    hadc.Init.LowPowerAutoPowerOff = DISABLE;
    hadc.Init.ContinuousConvMode = DISABLE;
    hadc.Init.NbrOfConversion = 1;
    hadc.Init.DiscontinuousConvMode = DISABLE;
    hadc.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc.Init.DMAContinuousRequests = DISABLE;
    hadc.Init.Overrun = ADC_OVR_DATA_PRESERVED;
    if (HAL_ADC_Init(&hadc) != HAL_OK) while(1);
#else
    HAL_ADC_Init(NULL);   /* 测试环境：调用 mock 函数 */
#endif
}

uint32_t ADC_ReadChannel(uint32_t channel) {
#ifndef TEST
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = channel;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_39CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc, &sConfig);
    HAL_ADC_Start(&hadc);
    HAL_ADC_PollForConversion(&hadc, 100);
    return HAL_ADC_GetValue(&hadc);
#else
    (void)channel;
    return 0;
#endif
}