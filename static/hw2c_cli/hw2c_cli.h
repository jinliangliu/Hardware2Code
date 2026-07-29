/**
 * @file    hw2c_cli.h
 * @brief   hw2c CLI Shell — lightweight interactive command-line interface
 *
 *          Part of Hardware2Code (hw2c) project.
 *          Designed for Cortex-M embedded MCUs (STM32 / ESP32),
 *          supports bare-metal and FreeRTOS.
 *
 *          Design references: lwshell (MaJerle), microsh, rxi/linedit
 *
 *          Key features:
 *          - Zero dynamic allocation — all buffers user-provided
 *          - Hardware-independent — IO via user callback
 *          - VT100 interactive terminal: cursor move, backspace, history, tab
 *          - In-place tokenizer with quoted-string support
 *          - Static command table (Flash-resident) + optional dynamic registration
 *          - Multi-instance safe — all state in hw2c_cli_t
 *          - Compile-time feature toggles strip unused code
 */

#ifndef HW2C_CLI_H
#define HW2C_CLI_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ==================================================================
 *  Compile-time configuration
 *
 *  Override any macro before including this header, e.g.:
 *    #define HW2C_CLI_CFG_HISTORY  0
 *    #include "hw2c_cli.h"
 * ================================================================== */

/** Maximum number of parsed arguments (argv size) */
#ifndef HW2C_CLI_CFG_MAX_ARGS
#define HW2C_CLI_CFG_MAX_ARGS         8
#endif

/** Maximum command-line length (including '\0') */
#ifndef HW2C_CLI_CFG_MAX_CMD_LEN
#define HW2C_CLI_CFG_MAX_CMD_LEN     128
#endif

/** Enable command history (up/down arrow navigation).
 *  When 0, hist_buf is not needed and history code is stripped. */
#ifndef HW2C_CLI_CFG_HISTORY
#define HW2C_CLI_CFG_HISTORY          1
#endif

/** Number of history slots. Each slot = HW2C_CLI_CFG_MAX_CMD_LEN bytes. */
#ifndef HW2C_CLI_CFG_HISTORY_DEPTH
#define HW2C_CLI_CFG_HISTORY_DEPTH    8
#endif

/** Enable Tab auto-completion. When 0, completion code is stripped. */
#ifndef HW2C_CLI_CFG_TAB_COMPLETION
#define HW2C_CLI_CFG_TAB_COMPLETION   1
#endif

/** Enable runtime (dynamic) command registration.
 *  When 0, only static command table is supported. */
#ifndef HW2C_CLI_CFG_DYN_CMD
#define HW2C_CLI_CFG_DYN_CMD          0
#endif

/** Enable thread-safety via lock/unlock callbacks.
 *  When 1, user must provide lock() / unlock() before calling init. */
#ifndef HW2C_CLI_CFG_THREAD_SAFE
#define HW2C_CLI_CFG_THREAD_SAFE      0
#endif

/** Disable VT100 escape sequences (CSI D, CSI C, CSI K).
 *  When 1, uses plain \b and space-overwrite for line editing.
 *  Use for terminals that do not support ANSI escape codes. */
#ifndef HW2C_CLI_CFG_NO_ESCAPE
#define HW2C_CLI_CFG_NO_ESCAPE        0
#endif

/* ==================================================================
 *  Forward declaration
 * ================================================================== */
typedef struct hw2c_cli hw2c_cli_t;

/* ==================================================================
 *  Type definitions
 * ================================================================== */

/**
 * @brief  Command handler callback.
 * @param  argc  Argument count (argv[0] is the command name)
 * @param  argv  Parsed token array, null-terminated.
 *               Strings point into the line buffer (in-place tokenization).
 * @param  cli   Pointer to the CLI instance (for hw2c_cli_puts / _printf)
 */
typedef void (*hw2c_cli_handler_t)(int argc, char *argv[],
                                   hw2c_cli_t *cli);

/**
 * @brief  Static command descriptor — stored in Flash (const).
 */
typedef struct {
    const char           *name;    /**< Command name (case-sensitive)       */
    const char           *help;    /**< One-line help text                  */
    hw2c_cli_handler_t    handler; /**< Handler function                    */
} hw2c_cli_cmd_t;

/**
 * @brief  CLI instance — all state encapsulated, supports multiple shells.
 *
 *          Usage:
 *            1. Populate mandatory fields: line_buf, line_size, putc
 *            2. Optionally set: prompt, hist_buf/hist_size
 *            3. Call hw2c_cli_init()
 *            4. Register commands: hw2c_cli_register_static()
 *            5. Feed bytes: hw2c_cli_input(&cli, ch)
 */
struct hw2c_cli {
    /* ---------- Mandatory: user-provided before init ---------- */

    char            *line_buf;        /**< Line-editing buffer (user alloc) */
    uint16_t         line_size;       /**< Size of line_buf                */
    void           (*putc)(char c);   /**< Single-char output callback     */

    /* ---------- Optional: user sets before init ---------- */

    const char      *prompt;          /**< Prompt string, default "> "     */

#if HW2C_CLI_CFG_HISTORY
    char            *hist_buf;        /**< History buffer (user alloc).
                                           Must be at least
                                           HW2C_CLI_CFG_HISTORY_DEPTH *
                                           HW2C_CLI_CFG_MAX_CMD_LEN bytes. */
#endif

#if HW2C_CLI_CFG_DYN_CMD
    hw2c_cli_cmd_t  *dyn_cmds;       /**< Dynamic command table buffer    */
    uint16_t         dyn_cmd_max;     /**< Max entries in dyn_cmds         */
#endif

#if HW2C_CLI_CFG_THREAD_SAFE
    void           (*lock)(void);     /**< Acquire mutex callback          */
    void           (*unlock)(void);   /**< Release mutex callback          */
#endif

    /* ---------- Internal state (do not modify) ---------- */

    /* line editor */
    uint16_t         line_len;        /**< Current line length             */
    uint16_t         cursor_pos;      /**< Cursor position in line         */

    /* VT100 escape parser */
    uint8_t          esc_state;       /**< 0=idle, 1=saw-ESC, 2=saw-ESC[  */

    /* command tables */
    const hw2c_cli_cmd_t  *static_cmds;      /**< Static command table    */
    uint16_t                static_cmd_count;

#if HW2C_CLI_CFG_DYN_CMD
    uint16_t         dyn_cmd_count;   /**< Current dynamic command count   */
#endif

    /* prompt backing storage */
    char             prompt_default[4];  /**< "> " + \0                    */

#if HW2C_CLI_CFG_HISTORY
    uint8_t          hist_count;      /**< Entries currently stored         */
    uint8_t          hist_head;       /**< Index of oldest entry            */
    int8_t           hist_pos;        /**< Current browsing pos, -1 = live  */
    char             saved_line[HW2C_CLI_CFG_MAX_CMD_LEN];  /**< Saved
                                            current line during browsing   */
    uint16_t         saved_len;       /**< Length of saved_line             */
#endif
};

/* ==================================================================
 *  Public API
 * ================================================================== */

/**
 * @brief  Initialise a CLI instance.
 * @param  cli   Pointer to user-allocated hw2c_cli_t.
 * @note   Before calling, the user MUST set:
 *           - cli->line_buf  (editing buffer)
 *           - cli->line_size
 *           - cli->putc      (output callback)
 *         Optional:
 *           - cli->prompt
 *           - cli->hist_buf  (if HW2C_CLI_CFG_HISTORY = 1)
 *           - cli->lock / unlock (if HW2C_CLI_CFG_THREAD_SAFE = 1)
 */
void hw2c_cli_init(hw2c_cli_t *cli);

/**
 * @brief  Feed one byte into the CLI shell (call from UART RX ISR or task).
 *
 *          Process flow:
 *            Printable char  → insert into line buffer, echo
 *            Backspace (0x08/0x7F) → delete left, VT100 erase
 *            Tab (0x09)      → auto-complete (if enabled)
 *            CR / LF (0x0D/0x0A) → execute command
 *            ESC (0x1B)      → enter VT100 escape parser
 *
 * @param  cli  Initialised CLI instance
 * @param  ch   Single byte received
 */
void hw2c_cli_input(hw2c_cli_t *cli, uint8_t ch);

/**
 * @brief  Register a table of static (const, Flash-resident) commands.
 * @param  cli    CLI instance
 * @param  cmds   Pointer to const command array
 * @param  count  Number of entries in the array
 */
void hw2c_cli_register_static(hw2c_cli_t *cli,
                              const hw2c_cli_cmd_t *cmds,
                              uint16_t count);

#if HW2C_CLI_CFG_DYN_CMD
/**
 * @brief  Register a single command at runtime (dynamic).
 * @param  cli  CLI instance
 * @param  cmd  Pointer to command descriptor (copied into dyn_cmds buffer)
 * @return 0 on success, -1 if table full
 */
int hw2c_cli_register_command(hw2c_cli_t *cli, const hw2c_cli_cmd_t *cmd);
#endif

/**
 * @brief  Output a null-terminated string through the CLI putc callback.
 *          Convenience wrapper — safe to use from command handlers.
 * @param  cli  CLI instance
 * @param  str  Null-terminated C string
 */
void hw2c_cli_puts(hw2c_cli_t *cli, const char *str);

/**
 * @brief  Output a formatted string (snprintf into stack buffer).
 *          Use sparingly — stack buffer is 128 bytes.
 * @param  cli  CLI instance
 * @param  fmt  printf format string
 * @param  ...  Format arguments
 */
void hw2c_cli_printf(hw2c_cli_t *cli, const char *fmt, ...);

/**
 * @brief  Set the CLI prompt at runtime.
 * @param  cli     CLI instance
 * @param  prompt  New prompt string (must remain valid / static)
 */
void hw2c_cli_set_prompt(hw2c_cli_t *cli, const char *prompt);

/**
 * @brief  Print all registered commands as a help listing.
 *          Can be called from a "help" command handler.
 * @param  cli  CLI instance
 */
void hw2c_cli_print_help(hw2c_cli_t *cli);

#ifdef __cplusplus
}
#endif

#endif /* HW2C_CLI_H */
