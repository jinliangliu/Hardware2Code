/**
 * @file    drv_log.c
 * @brief   Lightweight logging implementation for STM32G0B1
 *
 *          Architecture:
 *          1. Ring buffer (power-of-2, lock-free single-producer single-consumer)
 *          2. USART2 TXE interrupt drains ring buffer byte-by-byte
 *          3. log_output() formats message into ring buffer (ISR-safe)
 *          4. Output format: "[LEVEL] file:line | message\r\n"
 *
 *          Reference: https://github.com/rxi/log.c (MIT License)
 */

#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "stm32g0xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "drv_log.h"

/* ================================================================
 * Local Constants
 * ================================================================ */
#define USART2_BAUDRATE          115200
#define LOG_MSG_BUF_SIZE         128     /* max formatted message length */
#define LOG_LINE_END             "\r\n"

/* USART2 pins: PA2=TX(AF1), PA3=RX(AF1) on STM32G0 */
#define LOG_USART                USART2
#define LOG_USART_IRQn           USART2_LPUART2_IRQn
#define LOG_GPIO_PORT            GPIOA
#define LOG_GPIO_TX_PIN          GPIO_PIN_2
#define LOG_GPIO_RX_PIN          GPIO_PIN_3
#define LOG_GPIO_AF              GPIO_AF1_USART2

/* ================================================================
 * Level string table
 * ================================================================ */
static const char *level_strings[] = {
    "TRC", "DBG", "INF", "WRN", "ERR", "FTL"
};

/* ================================================================
 * Ring Buffer (single-producer, single-consumer, lock-free)
 * ================================================================ */
static volatile uint8_t  ring_buf[LOG_RING_BUF_SIZE];
static volatile uint32_t ring_head;   /* ISR consumes from here */
static volatile uint32_t ring_tail;   /* producer writes to here */

static inline uint32_t ring_mask(uint32_t val)
{
    return val & (LOG_RING_BUF_SIZE - 1);
}

/* Returns 1 if ring is empty */
static inline int ring_empty(void)
{
    return ring_head == ring_tail;
}

/* Returns number of free bytes in ring buffer */
static inline uint32_t ring_free(void)
{
    return LOG_RING_BUF_SIZE - (ring_tail - ring_head);
}

/* Push one byte into ring buffer. Returns 0 if full. */
/* Called from both task context and ISR — must be lock-free */
static int ring_put(uint8_t byte)
{
    if (ring_free() == 0) {
        return 0;   /* full */
    }
    ring_buf[ring_mask(ring_tail)] = byte;
    ring_tail++;
    return 1;
}

/* Pop one byte from ring buffer. Returns 0 if empty. */
/* Called only from ISR context */
static int ring_get(uint8_t *byte)
{
    if (ring_empty()) {
        return 0;   /* empty */
    }
    *byte = ring_buf[ring_mask(ring_head)];
    ring_head++;
    return 1;
}

/* ================================================================
 * USART2 handle — shared between init and ISR
 * ================================================================ */
static UART_HandleTypeDef log_huart;

/* ================================================================
 * USART2 Initialization
 * ================================================================ */
static void log_uart_init(void)
{
    GPIO_InitTypeDef gpio_init = {0};

    /* Enable clocks */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_USART2_CLK_ENABLE();

    /* PA2 = TX (Alternate Function, Push-Pull) */
    gpio_init.Pin       = LOG_GPIO_TX_PIN;
    gpio_init.Mode      = GPIO_MODE_AF_PP;
    gpio_init.Pull      = GPIO_PULLUP;
    gpio_init.Speed     = GPIO_SPEED_FREQ_LOW;
    gpio_init.Alternate = LOG_GPIO_AF;
    HAL_GPIO_Init(LOG_GPIO_PORT, &gpio_init);

    /* PA3 = RX (Alternate Function, Push-Pull) */
    gpio_init.Pin       = LOG_GPIO_RX_PIN;
    gpio_init.Mode      = GPIO_MODE_AF_PP;
    gpio_init.Pull      = GPIO_PULLUP;
    gpio_init.Speed     = GPIO_SPEED_FREQ_LOW;
    gpio_init.Alternate = LOG_GPIO_AF;
    HAL_GPIO_Init(LOG_GPIO_PORT, &gpio_init);

    /* Configure USART2 */
    log_huart.Instance          = LOG_USART;
    log_huart.Init.BaudRate     = USART2_BAUDRATE;
    log_huart.Init.WordLength   = UART_WORDLENGTH_8B;
    log_huart.Init.StopBits     = UART_STOPBITS_1;
    log_huart.Init.Parity       = UART_PARITY_NONE;
    log_huart.Init.Mode         = UART_MODE_TX_RX;
    log_huart.Init.HwFlowCtl    = UART_HWCONTROL_NONE;
    log_huart.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&log_huart);

    /* Enable TXE interrupt (transmit data register empty) */
    __HAL_UART_ENABLE_IT(&log_huart, UART_IT_TXE);

    /* Enable USART2 IRQ in NVIC */
    HAL_NVIC_SetPriority(LOG_USART_IRQn, 7, 0);
    HAL_NVIC_EnableIRQ(LOG_USART_IRQn);
}

/* ================================================================
 * USART2 Interrupt Handler
 *
 * TXE interrupt: pop byte from ring buffer → push to USART DR.
 * When ring buffer is empty, disable TXE interrupt to stop IRQ storm.
 * ================================================================ */
void log_uart_irq_handler(void)
{
    uint8_t byte;

    /* Check if TXE (Transmit Data Register Empty) interrupt */
    if (__HAL_UART_GET_FLAG(&log_huart, UART_FLAG_TXE) != RESET) {
        if (ring_get(&byte)) {
            LOG_USART->TDR = byte;
        } else {
            /* Ring empty — disable TXE interrupt until next log_output() */
            __HAL_UART_DISABLE_IT(&log_huart, UART_IT_TXE);
        }
    }
}

/* ================================================================
 * Runtime log level
 * ================================================================ */
static int current_log_level = LOG_LEVEL;

void log_set_level(int level)
{
    current_log_level = level;
}

/* ================================================================
 * Core log_output
 * ================================================================ */
void log_output(int level, const char *file, int line, const char *fmt, ...)
{
    /* Compile-time + runtime level filter */
    if (level < current_log_level) {
        return;
    }

    char msg_buf[LOG_MSG_BUF_SIZE];
    int  msg_len;

    /* Format: "[INF] file:line | " prefix */
    msg_len = snprintf(msg_buf, sizeof(msg_buf),
                       "[%s] %s:%d | ",
                       level_strings[level], file, line);

    if (msg_len < 0 || (size_t)msg_len >= sizeof(msg_buf)) {
        return;   /* overflow, safe to drop */
    }

    /* Append user message */
    va_list args;
    va_start(args, fmt);
    int user_len = vsnprintf(msg_buf + msg_len,
                             sizeof(msg_buf) - msg_len - 2,  /* reserve for \r\n */
                             fmt, args);
    va_end(args);

    if (user_len < 0) {
        return;
    }
    msg_len += user_len;
    if ((size_t)msg_len >= sizeof(msg_buf) - 2) {
        msg_len = (int)sizeof(msg_buf) - 3;   /* truncate, leave room for \r\n */
    }

    /* Append line ending */
    msg_buf[msg_len++] = '\r';
    msg_buf[msg_len++] = '\n';

    /* Push entire message to ring buffer */
    int pushed = 0;
    for (int i = 0; i < msg_len; i++) {
        if (!ring_put((uint8_t)msg_buf[i])) {
            break;   /* ring full, drop remaining bytes */
        }
        pushed++;
    }

    /* Re-enable TXE interrupt to kick off transmission */
    if (pushed > 0) {
        __HAL_UART_ENABLE_IT(&log_huart, UART_IT_TXE);
    }
}

/* ================================================================
 * System Info Banner
 * ================================================================ */
void log_system_info(void)
{
    extern uint32_t SystemCoreClock;

    log_info("========================================");
    log_info("  Hardware2Code Firmware");
    log_info("  MCU:    STM32G0B1RE (Cortex-M0+)");
    log_info("  HCLK:   %lu MHz", (unsigned long)(SystemCoreClock / 1000000));
    log_info("  Flash:  512 KB (dual-bank)");
    log_info("  SRAM:   144 KB");
    log_info("  RTOS:   FreeRTOS %s", tskKERNEL_VERSION_NUMBER);
    log_info("  Log:    USART2 @ %d baud", USART2_BAUDRATE);
    log_info("========================================");
}

/* ================================================================
 * Flush — block until ring buffer is drained
 * ================================================================ */
void log_flush(void)
{
    /* Poll until ring empty and USART TX complete */
    uint32_t timeout = 100000;
    while (!ring_empty() && timeout > 0) {
        timeout--;
    }
    /* Wait for last byte to finish shifting out */
    timeout = 100000;
    while (!(LOG_USART->ISR & USART_ISR_TC) && timeout > 0) {
        timeout--;
    }
}

/* ================================================================
 * Initialize
 * ================================================================ */
void log_init(void)
{
    ring_head = 0;
    ring_tail = 0;

    log_uart_init();

    /* Print banner — flush to ensure it's fully transmitted before
       any potential crash during subsequent init steps */
    log_system_info();
    log_flush();
}
