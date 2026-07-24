/**
 * @file    drv_log.h
 * @brief   Lightweight logging interface for STM32G0B1
 *
 *          Based on rxi/log.c design principles:
 *          - Callback-driven output (decoupled from UART)
 *          - Compile-time level filtering
 *          - ISR-safe via ring buffer + interrupt-driven TX
 *          - Zero dynamic allocation, C99 compatible
 *
 *          Output: USART2 (PA2 TX, PA3 RX) @ 115200-8-N-1
 *          Protocol: printf-style via ring buffer + TXE interrupt
 *
 *          Reference: https://github.com/rxi/log.c (MIT License)
 */

#ifndef DRV_LOG_H
#define DRV_LOG_H

#include <stdint.h>

/* ================================================================
 * Log Level Definitions
 * ================================================================ */
#define LOG_LEVEL_TRACE  0
#define LOG_LEVEL_DEBUG  1
#define LOG_LEVEL_INFO   2
#define LOG_LEVEL_WARN   3
#define LOG_LEVEL_ERROR  4
#define LOG_LEVEL_FATAL  5
#define LOG_LEVEL_NONE   6

/* Compile-time log level threshold — set via build flag or define here */
#ifndef LOG_LEVEL
#define LOG_LEVEL  LOG_LEVEL_INFO
#endif

/* ================================================================
 * Ring Buffer Configuration
 * ================================================================ */
#define LOG_RING_BUF_SIZE  1024  /* must be power of 2 for efficient masking */

/* ================================================================
 * Public API
 * ================================================================ */

/**
 * @brief  Initialize the log subsystem
 * @note   Configures USART2 (PA2/PA3), ring buffer, and TXE interrupt.
 *         Must be called after HAL_Init() and GPIO clock enable.
 */
void log_init(void);

/**
 * @brief  Set runtime log level threshold
 * @param  level : minimum level to output (LOG_TRACE .. LOG_NONE)
 */
void log_set_level(int level);

/**
 * @brief  Core log output function (printf-style)
 * @param  level : log level of this message
 * @param  file  : source file name (use __FILE__)
 * @param  line  : source line number (use __LINE__)
 * @param  fmt   : printf format string
 * @param  ...   : format arguments
 * @note   ISR-safe: writes to ring buffer, actual TX happens in USART2 IRQ.
 *         Messages exceeding ring buffer space are silently dropped.
 */
void log_output(int level, const char *file, int line, const char *fmt, ...);

/**
 * @brief  Print system information banner
 * @note   Outputs MCU type, clock freq, firmware version, FreeRTOS config.
 *         Call once after log_init() and SystemClock_Config().
 */
void log_system_info(void);

/**
 * @brief  Flush ring buffer (blocking, for critical shutdown)
 */
void log_flush(void);

/* ================================================================
 * Convenience Macros
 * ================================================================ */

#if LOG_LEVEL <= LOG_LEVEL_TRACE
#define log_trace(...) log_output(LOG_LEVEL_TRACE, __FILE__, __LINE__, __VA_ARGS__)
#else
#define log_trace(...) ((void)0)
#endif

#if LOG_LEVEL <= LOG_LEVEL_DEBUG
#define log_debug(...) log_output(LOG_LEVEL_DEBUG, __FILE__, __LINE__, __VA_ARGS__)
#else
#define log_debug(...) ((void)0)
#endif

#if LOG_LEVEL <= LOG_LEVEL_INFO
#define log_info(...)  log_output(LOG_LEVEL_INFO,  __FILE__, __LINE__, __VA_ARGS__)
#else
#define log_info(...)  ((void)0)
#endif

#if LOG_LEVEL <= LOG_LEVEL_WARN
#define log_warn(...)  log_output(LOG_LEVEL_WARN,  __FILE__, __LINE__, __VA_ARGS__)
#else
#define log_warn(...)  ((void)0)
#endif

#if LOG_LEVEL <= LOG_LEVEL_ERROR
#define log_error(...) log_output(LOG_LEVEL_ERROR, __FILE__, __LINE__, __VA_ARGS__)
#else
#define log_error(...) ((void)0)
#endif

#if LOG_LEVEL <= LOG_LEVEL_FATAL
#define log_fatal(...) log_output(LOG_LEVEL_FATAL, __FILE__, __LINE__, __VA_ARGS__)
#else
#define log_fatal(...) ((void)0)
#endif

#endif /* DRV_LOG_H */
