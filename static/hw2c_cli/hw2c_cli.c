/**
 * @file    hw2c_cli.c
 * @brief   hw2c CLI Shell — implementation
 *
 *          Architecture:
 *          ┌─────────────────────────────────────┐
 *          │  hw2c_cli_input(ch)                 │  ← UART ISR / task
 *          │    ├─ VT100 escape parser           │
 *          │    ├─ Line editor (insert/delete/   │
 *          │    │   cursor) + VT100 redraw       │
 *          │    ├─ History (up/down navigation)  │
 *          │    ├─ Tab completion                │
 *          │    └─ On CR: tokenize → dispatch    │
 *          └─────────────────────────────────────┘
 */

#include "hw2c_cli.h"
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

/* ==================================================================
 *  Internal helpers — forward declarations
 * ================================================================== */

static void cli_redraw_line(hw2c_cli_t *cli);
static void cli_erase_line(hw2c_cli_t *cli);
static void cli_execute(hw2c_cli_t *cli);
static void cli_parse_and_dispatch(hw2c_cli_t *cli);
static int  cli_tokenize(char *line, char *argv[], int max_args);
static void cli_history_save(hw2c_cli_t *cli);
static void cli_history_restore_entry(hw2c_cli_t *cli);
static void cli_tab_complete(hw2c_cli_t *cli);
static int  cli_find_common_prefix(const char *a, const char *b,
                                   int max_len);

/* ==================================================================
 *  Thread-safety helpers (no-op when HW2C_CLI_CFG_THREAD_SAFE = 0)
 * ================================================================== */

#if HW2C_CLI_CFG_THREAD_SAFE
#define CLI_LOCK(cli)   do { if ((cli)->lock) (cli)->lock(); } while (0)
#define CLI_UNLOCK(cli) do { if ((cli)->unlock) (cli)->unlock(); } while (0)
#else
#define CLI_LOCK(cli)   (void)(cli)
#define CLI_UNLOCK(cli) (void)(cli)
#endif

/* ==================================================================
 *  Public: hw2c_cli_init
 * ================================================================== */

void hw2c_cli_init(hw2c_cli_t *cli)
{
    /* The user must have populated mandatory fields before calling init.
     * We only reset internal state and set defaults. */
    if (cli == NULL) {
        return;
    }

    cli->line_len   = 0;
    cli->cursor_pos = 0;
    cli->esc_state  = 0;
    cli->static_cmds       = NULL;
    cli->static_cmd_count  = 0;

    /* Default prompt */
    cli->prompt_default[0] = '>';
    cli->prompt_default[1] = ' ';
    cli->prompt_default[2] = '\0';
    cli->prompt = cli->prompt_default;

#if HW2C_CLI_CFG_DYN_CMD
    cli->dyn_cmd_count = 0;
#endif

#if HW2C_CLI_CFG_HISTORY
    cli->hist_count = 0;
    cli->hist_head  = 0;
    cli->hist_pos   = -1;
    cli->saved_len  = 0;
    if (cli->hist_buf != NULL) {
        (void)memset(cli->hist_buf, 0,
                     (size_t)HW2C_CLI_CFG_HISTORY_DEPTH
                           * (size_t)HW2C_CLI_CFG_MAX_CMD_LEN);
    }
#endif

    /* Print initial prompt */
    if (cli->putc != NULL && cli->prompt != NULL) {
        const char *p = cli->prompt;
        while (*p) {
            cli->putc(*p);
            p++;
        }
    }
}

/* ==================================================================
 *  Public: hw2c_cli_register_static
 * ================================================================== */

void hw2c_cli_register_static(hw2c_cli_t *cli,
                              const hw2c_cli_cmd_t *cmds,
                              uint16_t count)
{
    if (cli == NULL || cmds == NULL) {
        return;
    }
    cli->static_cmds      = cmds;
    cli->static_cmd_count = count;
}

/* ==================================================================
 *  Public: hw2c_cli_register_command (dynamic)
 * ================================================================== */

#if HW2C_CLI_CFG_DYN_CMD
int hw2c_cli_register_command(hw2c_cli_t *cli, const hw2c_cli_cmd_t *cmd)
{
    if (cli == NULL || cmd == NULL) {
        return -1;
    }
    if (cli->dyn_cmd_count >= cli->dyn_cmd_max) {
        return -1;   /* table full */
    }
    cli->dyn_cmds[cli->dyn_cmd_count] = *cmd;
    cli->dyn_cmd_count++;
    return 0;
}
#endif /* HW2C_CLI_CFG_DYN_CMD */

/* ==================================================================
 *  Public: hw2c_cli_puts / hw2c_cli_printf
 * ================================================================== */

void hw2c_cli_puts(hw2c_cli_t *cli, const char *str)
{
    if (cli == NULL || cli->putc == NULL || str == NULL) {
        return;
    }
    while (*str) {
        cli->putc(*str);
        str++;
    }
}

void hw2c_cli_printf(hw2c_cli_t *cli, const char *fmt, ...)
{
    if (cli == NULL || cli->putc == NULL || fmt == NULL) {
        return;
    }
    char buf[128];
    va_list args;
    va_start(args, fmt);
    (void)vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    buf[sizeof(buf) - 1] = '\0';
    hw2c_cli_puts(cli, buf);
}

/* ==================================================================
 *  Public: hw2c_cli_set_prompt
 * ================================================================== */

void hw2c_cli_set_prompt(hw2c_cli_t *cli, const char *prompt)
{
    if (cli != NULL && prompt != NULL) {
        cli->prompt = prompt;
    }
}

/* ==================================================================
 *  Public: hw2c_cli_print_help
 * ================================================================== */

void hw2c_cli_print_help(hw2c_cli_t *cli)
{
    uint16_t i;

    if (cli == NULL) {
        return;
    }

    hw2c_cli_puts(cli, "Available commands:\r\n");

    /* Static commands */
    for (i = 0; i < cli->static_cmd_count; i++) {
        if (cli->static_cmds[i].name == NULL) {
            continue;
        }
        hw2c_cli_printf(cli, "  %-16s - %s\r\n",
                        cli->static_cmds[i].name,
                        cli->static_cmds[i].help
                            ? cli->static_cmds[i].help : "");
    }

#if HW2C_CLI_CFG_DYN_CMD
    /* Dynamic commands */
    for (i = 0; i < cli->dyn_cmd_count; i++) {
        if (cli->dyn_cmds[i].name == NULL) {
            continue;
        }
        hw2c_cli_printf(cli, "  %-16s - %s\r\n",
                        cli->dyn_cmds[i].name,
                        cli->dyn_cmds[i].help
                            ? cli->dyn_cmds[i].help : "");
    }
#endif
}

/* ==================================================================
 *  Command lookup (internal) — searches both tables
 * ================================================================== */

static const hw2c_cli_cmd_t *cli_find_command(hw2c_cli_t *cli,
                                               const char *name)
{
    uint16_t i;

    /* Search static commands first */
    for (i = 0; i < cli->static_cmd_count; i++) {
        if (cli->static_cmds[i].name != NULL
            && strcmp(cli->static_cmds[i].name, name) == 0) {
            return &cli->static_cmds[i];
        }
    }

#if HW2C_CLI_CFG_DYN_CMD
    /* Search dynamic commands */
    for (i = 0; i < cli->dyn_cmd_count; i++) {
        if (cli->dyn_cmds[i].name != NULL
            && strcmp(cli->dyn_cmds[i].name, name) == 0) {
            return &cli->dyn_cmds[i];
        }
    }
#endif

    return NULL;   /* not found */
}

/* ==================================================================
 *  In-place tokenizer with double-quote support
 *
 *  Modifies the line buffer by inserting '\0' between tokens.
 *  argv entries point directly into line — no memory copy.
 *
 *  Quoted strings: "hello world" → single arg "hello world"
 *  Escaped quotes: \" inside a quoted string → literal '"'
 * ================================================================== */

static int cli_tokenize(char *line, char *argv[], int max_args)
{
    int    argc   = 0;
    char  *p      = line;
    int    in_quote;
    char  *token_start;

    while (*p != '\0' && argc < max_args) {
        /* Skip leading whitespace */
        while (*p == ' ' || *p == '\t') {
            p++;
        }
        if (*p == '\0') {
            break;
        }

        /* Handle double-quoted argument */
        if (*p == '"') {
            p++;  /* skip opening '"' */
            token_start = p;
            in_quote    = 1;
            while (*p != '\0' && in_quote) {
                if (*p == '\\' && *(p + 1) == '"') {
                    /* Escaped quote: shift left to remove backslash */
                    {
                        char *q = p;
                        while (*q != '\0') {
                            *q = *(q + 1);
                            q++;
                        }
                    }
                    p++;  /* now points to the literal '"' */
                } else if (*p == '"') {
                    /* Closing quote */
                    *p = '\0';
                    p++;
                    in_quote = 0;
                } else {
                    p++;
                }
            }
            argv[argc++] = token_start;
        } else {
            /* Unquoted argument */
            token_start = p;
            while (*p != '\0' && *p != ' ' && *p != '\t') {
                p++;
            }
            if (*p != '\0') {
                *p = '\0';
                p++;
            }
            argv[argc++] = token_start;
        }
    }

    argv[argc] = NULL;
    return argc;
}

/* ==================================================================
 *  Line redraw helpers (VT100)
 *
 *  On Cortex-M, serial output is slow (~1 ms/char at 115200).
 *  We optimise by minimising escape sequences sent.
 * ================================================================== */

/**
 * @brief  Move cursor left by n positions.
 *         Uses CSI n D escape sequence.
 */
static void cli_cursor_left(hw2c_cli_t *cli, int n)
{
    if (n <= 0) {
        return;
    }
#if HW2C_CLI_CFG_NO_ESCAPE
    int i;
    for (i = 0; i < n; i++) {
        cli->putc('\b');
    }
#else
    /* For n=1, single CSI D is shorter than CSI n D */
    if (n == 1) {
        cli->putc('\x1b');
        cli->putc('[');
        cli->putc('D');
    } else {
        char buf[12];
        int len;
        len = snprintf(buf, sizeof(buf), "\x1b[%dD", n);
        {
            int i;
            for (i = 0; i < len; i++) {
                cli->putc(buf[i]);
            }
        }
    }
#endif
}

/**
 * @brief  Move cursor right by n positions.
 */
static void cli_cursor_right(hw2c_cli_t *cli, int n)
{
    if (n <= 0) {
        return;
    }
#if HW2C_CLI_CFG_NO_ESCAPE
    /* Output characters from old cursor position to advance */
    int start = (int)cli->cursor_pos - n;
    int i;
    for (i = 0; i < n; i++) {
        cli->putc(cli->line_buf[start + i]);
    }
#else
    if (n == 1) {
        cli->putc('\x1b');
        cli->putc('[');
        cli->putc('C');
    } else {
        char buf[12];
        int len;
        len = snprintf(buf, sizeof(buf), "\x1b[%dC", n);
        {
            int i;
            for (i = 0; i < len; i++) {
                cli->putc(buf[i]);
            }
        }
    }
#endif
}

/**
 * @brief  Clear from cursor to end of line.
 *         Uses CSI K (VT100) or space-overwrite (NO_ESCAPE mode).
 */
static void cli_clear_to_eol(hw2c_cli_t *cli)
{
#if HW2C_CLI_CFG_NO_ESCAPE
    int remain = (int)cli->line_len - (int)cli->cursor_pos;
    int i;
    /* Overwrite remaining visible chars with spaces */
    for (i = 0; i < remain; i++) {
        cli->putc(' ');
    }
    /* Move cursor back */
    for (i = 0; i < remain; i++) {
        cli->putc('\b');
    }
#else
    cli->putc('\x1b');
    cli->putc('[');
    cli->putc('K');
#endif
}

/**
 * @brief  Redraw the line from cli->cursor_pos to end, then restore cursor.
 *
 *          Used after insert/delete in the middle of the line:
 *            1. Clear from cursor to EOL (visual erase)
 *            2. Output remaining characters
 *            3. Move cursor back to original position
 */
static void cli_redraw_tail(hw2c_cli_t *cli)
{
    int tail_len;
    int i;

    cli_clear_to_eol(cli);

    tail_len = (int)cli->line_len - (int)cli->cursor_pos;
    for (i = 0; i < tail_len; i++) {
        cli->putc(cli->line_buf[cli->cursor_pos + i]);
    }

    /* Restore cursor to original position */
    cli_cursor_left(cli, tail_len);
}

/**
 * @brief  Erase the current line visually and reposition cursor to column 0.
 */
/* Forward declaration at top of file */
static void cli_erase_line(hw2c_cli_t *cli)
{
#if HW2C_CLI_CFG_NO_ESCAPE
    int i;
    /* CR + spaces to overwrite prompt + line, then CR again */
    cli->putc('\r');
    /* Clear: cover prompt (up to 4 chars) + full line content */
    for (i = 0; i < (int)cli->line_len + 4; i++) {
        cli->putc(' ');
    }
    cli->putc('\r');
#else
    /* CR + clear to EOL: does not rely on prompt knowledge */
    cli->putc('\r');
    cli_clear_to_eol(cli);
#endif
}

/**
 * @brief  Print the prompt and current line content.
 */
static void cli_redraw_line(hw2c_cli_t *cli)
{
    int i;

    hw2c_cli_puts(cli, cli->prompt);
    for (i = 0; i < (int)cli->line_len; i++) {
        cli->putc(cli->line_buf[i]);
    }
}

/* ==================================================================
 *  History management
 * ================================================================== */

#if HW2C_CLI_CFG_HISTORY

/**
 * @brief  Get pointer to history slot by index (0 = most recent).
 */
static char *cli_history_get(hw2c_cli_t *cli, int index)
{
    int slot;
    if (index < 0 || index >= (int)cli->hist_count) {
        return NULL;
    }
    /* hist_head is oldest; most recent = (head + count - 1 - index) */
    slot = ((int)cli->hist_head + (int)cli->hist_count - 1 - index)
            % HW2C_CLI_CFG_HISTORY_DEPTH;
    if (slot < 0) {
        slot += HW2C_CLI_CFG_HISTORY_DEPTH;
    }
    return &cli->hist_buf[slot * HW2C_CLI_CFG_MAX_CMD_LEN];
}

/**
 * @brief  Save current line into history ring buffer.
 *          Called before executing a command.
 */
static void cli_history_save(hw2c_cli_t *cli)
{
    int    slot;
    char  *dst;

    if (cli->hist_buf == NULL || cli->line_len == 0) {
        return;
    }

    /* Don't save duplicate of most recent entry */
    if (cli->hist_count > 0) {
        char *last = cli_history_get(cli, 0);
        if (last != NULL && strcmp(last, cli->line_buf) == 0) {
            return;
        }
    }

    /* New entry goes at (head + count) % depth */
    slot = ((int)cli->hist_head + (int)cli->hist_count)
            % HW2C_CLI_CFG_HISTORY_DEPTH;
    dst  = &cli->hist_buf[slot * HW2C_CLI_CFG_MAX_CMD_LEN];

    (void)memcpy(dst, cli->line_buf, (size_t)cli->line_len);
    dst[cli->line_len] = '\0';

    if (cli->hist_count < (uint8_t)HW2C_CLI_CFG_HISTORY_DEPTH) {
        cli->hist_count++;
    } else {
        /* Ring full — advance head (overwrite oldest) */
        cli->hist_head = (cli->hist_head + 1) % HW2C_CLI_CFG_HISTORY_DEPTH;
    }
}

/**
 * @brief  Restore a history entry into the line buffer and redraw.
 */
static void cli_history_restore_entry(hw2c_cli_t *cli)
{
    char *entry;
    int   entry_len;
    int   i;

    if (cli->hist_pos < 0 || cli->hist_pos >= (int)cli->hist_count) {
        return;
    }

    entry = cli_history_get(cli, cli->hist_pos);
    if (entry == NULL) {
        return;
    }

    entry_len = (int)strlen(entry);
    if (entry_len >= (int)cli->line_size) {
        entry_len = (int)cli->line_size - 1;
    }

    /* Copy history entry into line buffer first */
    (void)memcpy(cli->line_buf, entry, (size_t)entry_len);
    cli->line_buf[entry_len] = '\0';
    cli->line_len   = (uint16_t)entry_len;
    cli->cursor_pos = (uint16_t)entry_len;

    /* Erase current line and redraw (prompt + line content) */
    cli_erase_line(cli);
    hw2c_cli_puts(cli, cli->prompt);
    for (i = 0; i < entry_len; i++) {
        cli->putc(cli->line_buf[i]);
    }
}

/**
 * @brief  Handle up-arrow: browse to older history entry.
 */
static void cli_history_up(hw2c_cli_t *cli)
{
    if (cli->hist_count == 0) {
        return;
    }

    if (cli->hist_pos < 0) {
        /* First press: save current line */
        int i;
        cli->saved_len = cli->line_len;
        for (i = 0; i < (int)cli->line_len && i < HW2C_CLI_CFG_MAX_CMD_LEN - 1; i++) {
            cli->saved_line[i] = cli->line_buf[i];
        }
        cli->saved_line[i] = '\0';
        cli->hist_pos = 0;   /* most recent */
    } else if (cli->hist_pos < (int)cli->hist_count - 1) {
        cli->hist_pos++;
    } else {
        return;   /* already at oldest */
    }

    cli_history_restore_entry(cli);
}

/**
 * @brief  Handle down-arrow: browse to newer history entry.
 */
static void cli_history_down(hw2c_cli_t *cli)
{
    if (cli->hist_pos < 0) {
        return;
    }

    if (cli->hist_pos > 0) {
        cli->hist_pos--;
        cli_history_restore_entry(cli);
    } else {
        /* Restore the saved line (exiting history browsing) */
        int i;
        cli->hist_pos = -1;

        (void)memcpy(cli->line_buf, cli->saved_line, cli->saved_len);
        cli->line_buf[cli->saved_len] = '\0';
        cli->line_len   = cli->saved_len;
        cli->cursor_pos = cli->saved_len;

        cli_erase_line(cli);
        hw2c_cli_puts(cli, cli->prompt);
        for (i = 0; i < (int)cli->saved_len; i++) {
            cli->putc(cli->line_buf[i]);
        }
    }
}

#endif /* HW2C_CLI_CFG_HISTORY */

/* ==================================================================
 *  Tab completion
 * ================================================================== */

#if HW2C_CLI_CFG_TAB_COMPLETION

/**
 * @brief  Find the longest common prefix of two strings, up to max_len.
 * @return Length of common prefix.
 */
static int cli_find_common_prefix(const char *a, const char *b, int max_len)
{
    int i;
    for (i = 0; i < max_len; i++) {
        if (a[i] == '\0' || b[i] == '\0' || a[i] != b[i]) {
            break;
        }
    }
    return i;
}

/**
 * @brief  Complete a single command token at current cursor position.
 *
 *          1. Extract the token (word before cursor)
 *          2. Find all matching commands
 *          3. If exactly one match → autocomplete + space
 *          4. If multiple matches → print common prefix, then list all
 */
static void cli_tab_complete(hw2c_cli_t *cli)
{
    int           token_start;
    int           token_len;
    int           match_count;
    const char   *match_name;
    int           i;
    uint16_t      j;
    const char   *names[32];  /* max matches to display */
    int           name_count;

    /* Find start of current token (walk left from cursor) */
    token_start = (int)cli->cursor_pos;
    while (token_start > 0 && cli->line_buf[token_start - 1] != ' '
           && cli->line_buf[token_start - 1] != '\t') {
        token_start--;
    }
    token_len = (int)cli->cursor_pos - token_start;

    if (token_len == 0) {
        return;   /* nothing to complete */
    }

    /* Search static commands for matches */
    match_count = 0;
    match_name  = NULL;
    name_count  = 0;

    for (j = 0; j < cli->static_cmd_count; j++) {
        const char *name = cli->static_cmds[j].name;
        if (name == NULL) {
            continue;
        }
        if (strncmp(name, &cli->line_buf[token_start], (size_t)token_len)
            == 0) {
            match_count++;
            match_name = name;
            if (name_count < 32) {
                names[name_count++] = name;
            }
        }
    }

#if HW2C_CLI_CFG_DYN_CMD
    for (j = 0; j < cli->dyn_cmd_count; j++) {
        const char *name = cli->dyn_cmds[j].name;
        if (name == NULL) {
            continue;
        }
        if (strncmp(name, &cli->line_buf[token_start], (size_t)token_len)
            == 0) {
            match_count++;
            match_name = name;
            if (name_count < 32) {
                names[name_count++] = name;
            }
        }
    }
#endif

    if (match_count == 0) {
        return;
    }

    if (match_count == 1 && match_name != NULL) {
        /* Unique match — autocomplete */
        int name_len;
        int suffix_len;
        int k;

        name_len = (int)strlen(match_name);
        suffix_len = name_len - token_len;

        /* Insert remaining chars of the matched name */
        for (k = 0; k < suffix_len; k++) {
            if ((int)cli->line_len >= (int)cli->line_size - 1) {
                break;
            }
            /* Shift chars right from cursor */
            {
                int m;
                for (m = (int)cli->line_len; m > (int)cli->cursor_pos; m--) {
                    cli->line_buf[m] = cli->line_buf[m - 1];
                }
            }
            cli->line_buf[cli->cursor_pos] = match_name[token_len + k];
            cli->line_len++;
            cli->cursor_pos++;
            cli->line_buf[cli->line_len] = '\0';
        }
        /* Append a trailing space */
        if ((int)cli->line_len < (int)cli->line_size - 1) {
            {
                int m;
                for (m = (int)cli->line_len; m > (int)cli->cursor_pos; m--) {
                    cli->line_buf[m] = cli->line_buf[m - 1];
                }
            }
            cli->line_buf[cli->cursor_pos] = ' ';
            cli->line_len++;
            cli->cursor_pos++;
            cli->line_buf[cli->line_len] = '\0';
        }

        /* Redraw tail */
        cli_redraw_tail(cli);

    } else if (name_count > 1) {
        /* Multiple matches — find common prefix and fill it */
        int common_len;
        int first_len;
        int k;
        int extra;

        first_len = (int)strlen(names[0]);
        common_len = first_len;

        for (i = 1; i < name_count; i++) {
            int l;
            l = cli_find_common_prefix(names[i - 1], names[i],
                                       common_len);
            if (l < common_len) {
                common_len = l;
            }
        }

        /* Fill common prefix beyond current token */
        extra = common_len - token_len;
        if (extra > 0) {
            for (k = 0; k < extra; k++) {
                if ((int)cli->line_len >= (int)cli->line_size - 1) {
                    break;
                }
                {
                    int m;
                    for (m = (int)cli->line_len; m > (int)cli->cursor_pos; m--) {
                        cli->line_buf[m] = cli->line_buf[m - 1];
                    }
                }
                cli->line_buf[cli->cursor_pos] =
                    names[0][token_len + k];
                cli->line_len++;
                cli->cursor_pos++;
                cli->line_buf[cli->line_len] = '\0';
            }
            cli_redraw_tail(cli);
        }

        /* Print all matching commands */
        hw2c_cli_puts(cli, "\r\n");
        for (i = 0; i < name_count; i++) {
            hw2c_cli_printf(cli, "  %s", names[i]);
        }
        hw2c_cli_puts(cli, "\r\n");
        cli_redraw_line(cli);
        /* Restore cursor position */
        cli_cursor_left(cli, (int)cli->line_len - (int)cli->cursor_pos);
    }
}

#endif /* HW2C_CLI_CFG_TAB_COMPLETION */

/* ==================================================================
 *  Line editor: insert a character at cursor position
 * ================================================================== */

static void cli_insert_char(hw2c_cli_t *cli, char ch)
{
    int i;

    if ((int)cli->line_len >= (int)cli->line_size - 1) {
        return;   /* line full */
    }

    /* Shift chars right from cursor position */
    for (i = (int)cli->line_len; i > (int)cli->cursor_pos; i--) {
        cli->line_buf[i] = cli->line_buf[i - 1];
    }
    cli->line_buf[cli->cursor_pos] = ch;
    cli->line_len++;
    cli->cursor_pos++;
    cli->line_buf[cli->line_len] = '\0';

    /* Echo: clear tail and redraw */
    cli_redraw_tail(cli);
}

/* ==================================================================
 *  Line editor: delete character left of cursor (backspace)
 * ================================================================== */

static void cli_delete_left(hw2c_cli_t *cli)
{
    int i;

    if (cli->cursor_pos == 0) {
        return;   /* nothing to delete */
    }

    cli->cursor_pos--;

    /* Move cursor left visually */
    cli_cursor_left(cli, 1);

    /* Shift chars left from cursor */
    for (i = (int)cli->cursor_pos; i < (int)cli->line_len - 1; i++) {
        cli->line_buf[i] = cli->line_buf[i + 1];
    }
    cli->line_len--;
    cli->line_buf[cli->line_len] = '\0';

    /* Clear tail and redraw */
    cli_redraw_tail(cli);
}

/* ==================================================================
 *  Command execution: save history, tokenize, dispatch
 * ================================================================== */

static void cli_parse_and_dispatch(hw2c_cli_t *cli)
{
    int                   argc;
    char                 *argv[HW2C_CLI_CFG_MAX_ARGS + 1];
    const hw2c_cli_cmd_t *cmd;

#if HW2C_CLI_CFG_HISTORY
    cli_history_save(cli);
    cli->hist_pos = -1;   /* exit history browsing */
#endif

    if (cli->line_len == 0) {
        return;   /* empty line */
    }

    /* Make a local, mutable copy of the line (tokenizer is destructive) */
    {
        char  line_copy[HW2C_CLI_CFG_MAX_CMD_LEN];
        (void)memcpy(line_copy, cli->line_buf,
                     (size_t)cli->line_len + 1);
        argc = cli_tokenize(line_copy, argv, HW2C_CLI_CFG_MAX_ARGS);
    }

    if (argc == 0) {
        return;
    }

    /* Check for built-in "-h" / "--help" suffix on another cmd */
    if (argc >= 2
        && (strcmp(argv[argc - 1], "-h") == 0
            || strcmp(argv[argc - 1], "--help") == 0)) {
        /* Treat as "help <command>" */
        const hw2c_cli_cmd_t *target;
        target = cli_find_command(cli, argv[0]);
        if (target != NULL && target->help != NULL) {
            hw2c_cli_printf(cli, "%s — %s\r\n",
                            target->name, target->help);
            return;
        }
    }

    /* Lookup and dispatch */
    cmd = cli_find_command(cli, argv[0]);
    if (cmd == NULL) {
        hw2c_cli_printf(cli,
            "Unknown command: %s. Type 'help' for available commands.\r\n",
            argv[0]);
        return;
    }

    if (cmd->handler != NULL) {
        cmd->handler(argc, argv, cli);
    }
}

/**
 * @brief  Execute the current line (called on CR/LF).
 *          Echoes "\r\n", dispatches, resets line, prints prompt.
 */
static void cli_execute(hw2c_cli_t *cli)
{
    /* Echo newline */
    hw2c_cli_puts(cli, "\r\n");

    CLI_LOCK(cli);
    cli_parse_and_dispatch(cli);
    CLI_UNLOCK(cli);

    /* Reset line state */
    cli->line_len   = 0;
    cli->cursor_pos = 0;
    cli->line_buf[0] = '\0';

    /* Print prompt for next command */
    hw2c_cli_puts(cli, cli->prompt);
}

/* ==================================================================
 *  Public: hw2c_cli_input — main state machine
 *
 *  Single-byte entry point. Handles:
 *    - Printable ASCII     → insert into line buffer
 *    - Backspace (BS / DEL) → delete left
 *    - CR / LF             → execute command
 *    - Tab                 → auto-complete
 *    - ESC                 → start VT100 escape sequence parser
 * ================================================================== */

void hw2c_cli_input(hw2c_cli_t *cli, uint8_t ch)
{
    if (cli == NULL) {
        return;
    }

    /* ---- VT100 escape sequence parser ---- */
    if (cli->esc_state == 0 && ch == 0x1B) {
        cli->esc_state = 1;
        return;
    }

    if (cli->esc_state == 1) {
        if (ch == '[') {
            cli->esc_state = 2;
            return;
        }
        /* Unknown escape — abort sequence, fall through to normal */
        cli->esc_state = 0;
    }

    if (cli->esc_state == 2) {
        cli->esc_state = 0;   /* consume the command byte */

        switch (ch) {
        case 'A':   /* Up arrow */
#if HW2C_CLI_CFG_HISTORY
            cli_history_up(cli);
#endif
            return;

        case 'B':   /* Down arrow */
#if HW2C_CLI_CFG_HISTORY
            cli_history_down(cli);
#endif
            return;

        case 'C':   /* Right arrow */
            if (cli->cursor_pos < cli->line_len) {
                cli->cursor_pos++;
                cli_cursor_right(cli, 1);
            }
            return;

        case 'D':   /* Left arrow */
            if (cli->cursor_pos > 0) {
                cli->cursor_pos--;
                cli_cursor_left(cli, 1);
            }
            return;

#if HW2C_CLI_CFG_HISTORY
        case 'H':   /* Home (CSI H, older terminals) */
            if (cli->cursor_pos > 0) {
                int n = (int)cli->cursor_pos;
                cli->cursor_pos = 0;
                cli_cursor_left(cli, n);
            }
            return;

        case 'F':   /* End (CSI F, older terminals) */
            if (cli->cursor_pos < cli->line_len) {
                int n = (int)cli->line_len - (int)cli->cursor_pos;
                cli->cursor_pos = cli->line_len;
                cli_cursor_right(cli, n);
            }
            return;
#endif

        default:
            /* Unrecognised CSI sequence — ignore */
            return;
        }
    }

    /* ---- Normal character processing ---- */

    switch (ch) {

    case '\r':   /* Carriage return */
    case '\n':   /* Line feed */
        CLI_LOCK(cli);
        cli_execute(cli);
        CLI_UNLOCK(cli);
        break;

    case 0x08:   /* Backspace (BS) */
    case 0x7F:   /* Delete (DEL) */
        CLI_LOCK(cli);
        cli_delete_left(cli);
        CLI_UNLOCK(cli);
        break;

    case '\t':   /* Horizontal tab → auto-complete */
#if HW2C_CLI_CFG_TAB_COMPLETION
        CLI_LOCK(cli);
        cli_tab_complete(cli);
        CLI_UNLOCK(cli);
#endif
        break;

    case 0x03:   /* Ctrl+C — reset line */
        CLI_LOCK(cli);
        hw2c_cli_puts(cli, "^C\r\n");
        cli->line_len   = 0;
        cli->cursor_pos = 0;
        cli->line_buf[0] = '\0';
#if HW2C_CLI_CFG_HISTORY
        cli->hist_pos = -1;
#endif
        hw2c_cli_puts(cli, cli->prompt);
        CLI_UNLOCK(cli);
        break;

    default:
        /* Printable ASCII only */
        if (ch >= 0x20 && ch <= 0x7E) {
            CLI_LOCK(cli);
            cli_insert_char(cli, (char)ch);
            CLI_UNLOCK(cli);
        }
        break;
    }
}
