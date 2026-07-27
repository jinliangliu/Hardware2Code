
#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif

#include "drv_cli0.h"
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

#ifndef TEST
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"
#endif

#include "drv_onboard_rtc.h"
#include "drv_fota.h"

/* ==================================================================
 *  Static module state
 * ================================================================== */

static UART_HandleTypeDef *cli_huart;
static SemaphoreHandle_t   cli_rx_sem = NULL;
static uint8_t             cli_rx_byte;

/* Ring buffer */
static volatile uint8_t  cli_ringbuf[CLI_RINGBUF_SIZE];
static volatile uint16_t cli_ringbuf_head = 0;
static volatile uint16_t cli_ringbuf_tail = 0;

/* Command table */
static cli_command_t  cli_commands[CLI_MAX_COMMANDS];
static int            cli_cmd_count = 0;
static const char    *cli_prompt = CLI_PROMPT_DEFAULT;

/* ==================================================================
 *  Ring buffer helpers (ISR-safe single producer, single consumer)
 * ================================================================== */

static bool ringbuf_put(uint8_t c)
{
    uint16_t next = (cli_ringbuf_head + 1) % CLI_RINGBUF_SIZE;
    if (next == cli_ringbuf_tail) return false; /* full */
    cli_ringbuf[cli_ringbuf_head] = c;
    cli_ringbuf_head = next;
    return true;
}

static int ringbuf_get(void)
{
    if (cli_ringbuf_head == cli_ringbuf_tail) return -1; /* empty */
    uint8_t c = cli_ringbuf[cli_ringbuf_tail];
    cli_ringbuf_tail = (cli_ringbuf_tail + 1) % CLI_RINGBUF_SIZE;
    return c;
}

/* ==================================================================
 *  UART output helpers
 * ================================================================== */

static void cli_uart_putc(char c)
{
    HAL_UART_Transmit((UART_HandleTypeDef *)cli_huart, (uint8_t *)&c, 1, 100);
}

void cli_output(const char *fmt, ...)
{
    char buf[128];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    for (char *p = buf; *p; p++) {
        cli_uart_putc(*p);
    }
}

/* ==================================================================
 *  Tokenizer  (destructive: inserts '\0' terminators into line_buf)
 * ================================================================== */

static int cli_tokenize(char *line, char *argv[], int max_args)
{
    int argc = 0;
    char *p = line;
    while (*p && argc < max_args) {
        /* skip leading whitespace */
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        argv[argc++] = p;
        /* find end of token */
        while (*p && *p != ' ' && *p != '\t') p++;
        if (*p) { *p = '\0'; p++; }
    }
    argv[argc] = NULL;
    return argc;
}

/* ==================================================================
 *  Command table management
 * ================================================================== */

void cli_register_command(const char *name, const char *help,
                          cli_cmd_handler_t handler)
{
    if (cli_cmd_count >= CLI_MAX_COMMANDS) return;
    cli_commands[cli_cmd_count].name    = name;
    cli_commands[cli_cmd_count].help    = help;
    cli_commands[cli_cmd_count].handler = handler;
    cli_cmd_count++;
}

static cli_command_t *cli_find_command(const char *name)
{
    for (int i = 0; i < cli_cmd_count; i++) {
        if (strcmp(cli_commands[i].name, name) == 0) {
            return &cli_commands[i];
        }
    }
    return NULL;
}

/* ==================================================================
 *  Built-in command handlers
 * ================================================================== */

static void cmd_help(int argc, char *argv[], cli_output_fn out)
{
    (void)argc; (void)argv;
    out("Available commands:\r\n");
    for (int i = 0; i < cli_cmd_count; i++) {
        out("  %-16s - %s\r\n", cli_commands[i].name, cli_commands[i].help);
    }
}

static void cmd_version(int argc, char *argv[], cli_output_fn out)
{
    (void)argc; (void)argv;
    out("Firmware version: 1.0.0\r\n");
    out("Build: %s %s\r\n", __DATE__, __TIME__);
}

static void cmd_uptime(int argc, char *argv[], cli_output_fn out)
{
    (void)argc; (void)argv;
    TickType_t ticks = xTaskGetTickCount();
    uint32_t seconds = ticks / 1000;
    uint32_t hours = seconds / 3600;
    uint32_t minutes = (seconds % 3600) / 60;
    uint32_t secs = seconds % 60;
    out("Uptime: %lu:%02lu:%02lu\r\n", hours, minutes, secs);
}

static void cmd_free(int argc, char *argv[], cli_output_fn out)
{
    (void)argc; (void)argv;
    out("Free heap: %lu bytes\r\n", xPortGetFreeHeapSize());
}

static void cmd_tasks(int argc, char *argv[], cli_output_fn out)
{
    (void)argc; (void)argv;
    static char task_buf[512];
    vTaskList(task_buf);
    out("%s", task_buf);
}

static void cmd_reset(int argc, char *argv[], cli_output_fn out)
{
    (void)argc; (void)argv;
    out("Resetting...\r\n");
    vTaskDelay(100);
    NVIC_SystemReset();
}

/* ==================================================================
 *  Conditional command: GPIO  (available when any pin is defined)
 * ================================================================== */

/* Named cli_strcasecmp to avoid conflict with libc strcasecmp on host */
static int cli_strcasecmp(const char *a, const char *b)
{
    while (*a && *b) {
        char ca = (*a >= 'A' && *a <= 'Z') ? *a + 32 : *a;
        char cb = (*b >= 'A' && *b <= 'Z') ? *b + 32 : *b;
        if (ca != cb) return ca - cb;
        a++; b++;
    }
    return *a - *b;
}

static int cli_pin_lookup(const char *name, GPIO_TypeDef **port,
                          uint16_t *pin_num)
{
    if (cli_strcasecmp(name, "PA2") == 0) {
        *port = GPIOA;
        *pin_num = GPIO_PIN_2;
        return 0;
    }
    if (cli_strcasecmp(name, "PA3") == 0) {
        *port = GPIOA;
        *pin_num = GPIO_PIN_3;
        return 0;
    }
    if (cli_strcasecmp(name, "PA5") == 0) {
        *port = GPIOA;
        *pin_num = GPIO_PIN_5;
        return 0;
    }
    if (cli_strcasecmp(name, "PC14") == 0) {
        *port = GPIOC;
        *pin_num = GPIO_PIN_14;
        return 0;
    }
    if (cli_strcasecmp(name, "PC15") == 0) {
        *port = GPIOC;
        *pin_num = GPIO_PIN_15;
        return 0;
    }
    return -1;
}

static void cmd_gpio(int argc, char *argv[], cli_output_fn out)
{
    if (argc < 2) {
        out("Usage: gpio read <pin> | gpio write <pin> <0|1>\r\n");
        out("Available pins: PA2 PA3 PA5 PC14 PC15 \r\n");
        return;
    }
    if (strcmp(argv[1], "read") == 0) {
        if (argc < 3) { out("Usage: gpio read <pin>\r\n"); return; }
        GPIO_TypeDef *port; uint16_t pn;
        if (cli_pin_lookup(argv[2], &port, &pn) != 0) {
            out("Unknown pin: %s\r\n", argv[2]);
            return;
        }
        GPIO_PinState state = HAL_GPIO_ReadPin(port, pn);
        out("%s: %d\r\n", argv[2], state);
    } else if (strcmp(argv[1], "write") == 0) {
        if (argc < 4) { out("Usage: gpio write <pin> <0|1>\r\n"); return; }
        GPIO_TypeDef *port; uint16_t pn;
        if (cli_pin_lookup(argv[2], &port, &pn) != 0) {
            out("Unknown pin: %s\r\n", argv[2]);
            return;
        }
        GPIO_PinState val = (argv[3][0] == '1') ? GPIO_PIN_SET : GPIO_PIN_RESET;
        HAL_GPIO_WritePin(port, pn, val);
        out("%s -> %d\r\n", argv[2], val);
    } else {
        out("Unknown gpio subcommand: %s\r\n", argv[1]);
    }
}

/* ==================================================================
 *  Conditional command: LED
 * ================================================================== */

static void cmd_led(int argc, char *argv[], cli_output_fn out)
{
    if (argc < 2) { out("Usage: led on|off|toggle\r\n"); return; }
    GPIO_TypeDef *port;
    uint16_t pn;
    port = GPIOA;
    pn = GPIO_PIN_5;
    if (strcmp(argv[1], "on") == 0) {
        HAL_GPIO_WritePin(port, pn,
GPIO_PIN_SET);
        out("LED ON\r\n");
    } else if (strcmp(argv[1], "off") == 0) {
        HAL_GPIO_WritePin(port, pn,
GPIO_PIN_RESET);
        out("LED OFF\r\n");
    } else if (strcmp(argv[1], "toggle") == 0) {
        HAL_GPIO_TogglePin(port, pn);
        out("LED TOGGLED\r\n");
    } else {
        out("Usage: led on|off|toggle\r\n");
    }
}

/* ==================================================================
 *  Conditional command: RTC
 * ================================================================== */

static void cmd_rtc(int argc, char *argv[], cli_output_fn out)
{
    if (argc < 2) {
        out("Usage: rtc time | rtc set <HH:MM:SS>\r\n");
        return;
    }
    if (strcmp(argv[1], "time") == 0) {
        RTC_TimeTypeDef t;
        RTC_DateTypeDef d;
        HAL_RTC_GetTime(&hrtc, &t, RTC_FORMAT_BIN);
        HAL_RTC_GetDate(&hrtc, &d, RTC_FORMAT_BIN);
        out("RTC Time: %02d:%02d:%02d  Date: %02d/%02d/%02d\r\n",
            t.Hours, t.Minutes, t.Seconds,
            d.Date, d.Month, (uint8_t)(d.Year + 2000));
    } else if (strcmp(argv[1], "set") == 0) {
        if (argc < 3) { out("Usage: rtc set <HH:MM:SS>\r\n"); return; }
        int hh, mm, ss;
        if (sscanf(argv[2], "%d:%d:%d", &hh, &mm, &ss) != 3) {
            out("Invalid time format. Use HH:MM:SS\r\n");
            return;
        }
        RTC_TimeTypeDef t = {0};
        t.Hours   = hh;
        t.Minutes = mm;
        t.Seconds = ss;
        HAL_RTC_SetTime(&hrtc, &t, RTC_FORMAT_BIN);
        out("RTC time set to %02d:%02d:%02d\r\n", hh, mm, ss);
    } else {
        out("Unknown rtc subcommand: %s\r\n", argv[1]);
    }
}

/* ==================================================================
 *  Conditional command: Modbus
 * ================================================================== */


/* ==================================================================
 *  Conditional command: Cellular
 * ================================================================== */


/* ==================================================================
 *  Conditional command: MQTT
 * ================================================================== */


/* ==================================================================
 *  Conditional command: FOTA
 * ================================================================== */

static void cmd_fota(int argc, char *argv[], cli_output_fn out)
{
    if (argc < 2) {
        out("Usage: fota status | fota progress\r\n");
        return;
    }
    if (strcmp(argv[1], "status") == 0) {
        fota_state_t state = fota_get_state();
        static const char *state_names[] = {
            "IDLE", "RECEIVING", "APPLYING", "VERIFYING", "COMPLETE", "ERROR"
        };
        out("FOTA state: %s\r\n",
            (state <= FOTA_STATE_ERROR) ? state_names[state] : "UNKNOWN");
    } else if (strcmp(argv[1], "progress") == 0) {
        uint32_t progress = fota_get_progress();
        out("FOTA progress: %lu%%\r\n", progress);
    } else {
        out("Unknown fota subcommand: %s\r\n", argv[1]);
    }
}

/* ==================================================================
 *  Register all commands (called once from cli_task before the loop)
 * ================================================================== */

static void cli_register_builtin_commands(void)
{
    cli_register_command("help",    "Show available commands",      cmd_help);
    cli_register_command("version", "Show firmware version",        cmd_version);
    cli_register_command("uptime",  "Show system uptime",           cmd_uptime);
    cli_register_command("free",    "Show free heap memory",        cmd_free);
    cli_register_command("tasks",   "List FreeRTOS tasks",          cmd_tasks);
    cli_register_command("reset",   "Software reset MCU",           cmd_reset);
    cli_register_command("gpio",    "Read/write GPIO pins",         cmd_gpio);
    cli_register_command("led",     "Control LED (on/off/toggle)",  cmd_led);
    cli_register_command("rtc",     "RTC time operations",          cmd_rtc);
    cli_register_command("fota",    "FOTA firmware update",         cmd_fota);
}

/* ==================================================================
 *  cli_init  —  set up NVIC and start interrupt-driven RX
 * ================================================================== */

void cli_init(void *huart)
{
    cli_huart = (UART_HandleTypeDef *)huart;
    cli_rx_sem = xSemaphoreCreateBinary();

    /* Start one-byte interrupt receive */
    HAL_UART_Receive_IT(cli_huart, &cli_rx_byte, 1);
}

/* ==================================================================
 *  HAL_UART_RxCpltCallback  —  override the __weak HAL default
 * ================================================================== */

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == (UART_HandleTypeDef *)cli_huart) {
        ringbuf_put(cli_rx_byte);
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        xSemaphoreGiveFromISR(cli_rx_sem, &xHigherPriorityTaskWoken);
        HAL_UART_Receive_IT((UART_HandleTypeDef *)cli_huart, &cli_rx_byte, 1);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

/* ==================================================================
 *  cli_task  —  FreeRTOS task: read ring buffer, edit, dispatch
 * ================================================================== */

void cli_task(void *arg)
{
    (void)arg;
    char   line_buf[CLI_MAX_CMD_LEN + 1];
    uint16_t line_pos = 0;
    char  *argv[CLI_MAX_ARGS + 1];

    cli_register_builtin_commands();

    cli_output("\r\n%s", cli_prompt);

    for (;;) {
        /* Wait for at least one character with a timeout */
        if (xSemaphoreTake(cli_rx_sem, pdMS_TO_TICKS(100)) == pdTRUE) {
            int c;
            while ((c = ringbuf_get()) >= 0) {
                if (c == '\r' || c == '\n') {
                    cli_output("\r\n");
                    line_buf[line_pos] = '\0';

                    if (line_pos > 0) {
                        int argc = cli_tokenize(line_buf, argv, CLI_MAX_ARGS);
                        if (argc > 0) {
                            cli_command_t *cmd = cli_find_command(argv[0]);
                            if (cmd) {
                                cmd->handler(argc, argv, cli_output);
                            } else {
                                cli_output("Unknown command: %s. "
                                           "Type 'help' for available commands.\r\n",
                                           argv[0]);
                            }
                        }
                    }

                    line_pos = 0;
                    cli_output("%s", cli_prompt);
                } else if (c == 0x08 || c == 0x7F) {
                    /* Backspace / DEL */
                    if (line_pos > 0) {
                        line_pos--;
                        cli_output("\b \b");
                    }
                } else if (c >= 0x20 && c <= 0x7E) {
                    /* Printable ASCII */
                    if (line_pos < CLI_MAX_CMD_LEN) {
                        line_buf[line_pos++] = (char)c;
                        cli_uart_putc((char)c);
                    }
                }
            }
        }
    }
}