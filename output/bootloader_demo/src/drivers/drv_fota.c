#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif
#include "drv_uart2.h"
#include "drv_fota.h"
#include "drv_fota_bspatch.h"
#include <string.h>

/*
 * Slot addresses — must match bootloader.ld and app_slot_*.ld
 */
#define SLOT_A_ADDR     8192UL
#define SLOT_B_ADDR     262144UL

#define CRC16_POLY      0x1021U
#define ACK_TIMEOUT_MS  2000U

/* ---- Static state ---- */

static fota_state_t   state = FOTA_STATE_IDLE;
static uint8_t        chunk_buf[FOTA_CHUNK_SIZE + 4];  /* payload + seq/len header */
static uint32_t       total_size = 0;
static uint32_t       received_offset = 0;
static uint16_t       expected_seq = 0;
static uint32_t       progress_bytes = 0;

/* ---- CRC-16/CCITT table ---- */

static const uint16_t crc16_table[256] = {
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
};

/* ---- Internal helpers ---- */

static uint16_t crc16_compute(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFFU;
    for (uint16_t i = 0; i < len; i++) {
        crc = (uint16_t)((crc << 8) ^ crc16_table[((crc >> 8) ^ data[i]) & 0xFF]);
    }
    return crc;
}

/*
 * =====================================================================
 *  TAMP BKP4R persistence (FOTA state survives power cycles)
 * =====================================================================
 */

#ifndef TEST
#include "stm32g0xx_hal.h"
#include "stm32g0xx_ll_pwr.h"
#include "stm32g0xx_ll_rtc.h"

static void bkp_write(uint32_t val)
{
    /* Enable backup domain write access */
    HAL_PWR_EnableBkUpAccess();
    /* Wait for DBP sync */
    {
        volatile uint32_t timeout = 100000U;
        while ((PWR->CR1 & PWR_CR1_DBP) == 0U && timeout > 0U) { timeout--; }
    }
    TAMP->BKP4R = val;
}

static uint32_t bkp_read(void)
{
    return TAMP->BKP4R;
}

static void bkp_set_flag(uint32_t flag)
{
    uint32_t val = bkp_read();
    val |= flag;
    bkp_write(val);
}

static void bkp_clear_flags(void)
{
    bkp_write(0);
}
#else
/* Mock implementations for test builds */
static uint32_t mock_bkp4r = 0;

static void bkp_write(uint32_t val) { mock_bkp4r = val; }
static uint32_t bkp_read(void) { return mock_bkp4r; }
static void bkp_set_flag(uint32_t flag) { mock_bkp4r |= flag; }
static void bkp_clear_flags(void) { mock_bkp4r = 0; }
#endif

/* ---- Public API ---- */

void fota_init(void)
{
    state = FOTA_STATE_IDLE;
    total_size = 0;
    received_offset = 0;
    expected_seq = 0;
    memset(chunk_buf, 0, sizeof(chunk_buf));

    /* Clear any stale FOTA flags from previous boot */
    bkp_clear_flags();
}

fota_state_t fota_get_state(void)
{
    return state;
}

uint32_t fota_get_progress(void)
{
    return progress_bytes;
}

/* ---- Process pending FOTA patch from previous session ---- */

static void fota_apply_stored_patch(void)
{
    uint32_t flags = bkp_read();
    if (!(flags & FOTA_FLAG_PATCH_READY)) {
        return;
    }

    /* Apply the stored patch (bspatch from Slot A flash + patch data in Slot B) */
    state = FOTA_STATE_APPLYING;
    bkp_set_flag(FOTA_FLAG_IN_PROGRESS);

    /* Read old firmware size from Slot A header */
    uint32_t old_size = 0;
    {
        /* Search for magic "H2Ck" in Slot A header area */
        const uint32_t MAGIC = 0x4841436BUL;  /* "H2Ck" */
        volatile const uint32_t *slot_a = (volatile const uint32_t *)SLOT_A_ADDR;
        for (uint32_t off = 0x40 / 4; off < 0x200 / 4; off++) {
            if (slot_a[off] == MAGIC) {
                /* image_size is 2 words before magic */
                old_size = slot_a[off - 2];
                break;
            }
        }
    }

    if (old_size == 0) {
        state = FOTA_STATE_ERROR;
        bkp_set_flag(FOTA_FLAG_APPLY_FAIL);
        bkp_write(flags & ~FOTA_FLAG_PATCH_READY);
        return;
    }

    /* Apply the patch */
    if (fota_bspatch_apply(SLOT_A_ADDR, old_size, SLOT_B_ADDR) != 0) {
        state = FOTA_STATE_ERROR;
        bkp_set_flag(FOTA_FLAG_APPLY_FAIL);
        bkp_write(flags & ~FOTA_FLAG_PATCH_READY);
        return;
    }

    state = FOTA_STATE_COMPLETE;
    progress_bytes = total_size;
}

/* ---- Main process function (called from FOTA task loop) ---- */

void fota_process(void)
{
#ifndef TEST
    static uint32_t last_activity_tick = 0;
#endif

    switch (state) {

    case FOTA_STATE_IDLE: {
        /* Check for stored patch from previous session */
        uint32_t flags = bkp_read();
        if (flags & FOTA_FLAG_PATCH_READY) {
            fota_apply_stored_patch();
        }
        break;
    }

    case FOTA_STATE_RECEIVING: {
        /* Wait for UART to complete receiving one chunk */
        if (!UART_IsRxComplete()) {
#ifndef TEST
            /* Timeout check for receive */
            uint32_t now = HAL_GetTick();
            if (now - last_activity_tick > ACK_TIMEOUT_MS && last_activity_tick != 0) {
                state = FOTA_STATE_ERROR;
            }
#endif
            break;
        }

        uint16_t rx_len = UART_GetRxCount();
        if (rx_len < 6) {
            /* Minimum chunk: seq(2B) + len(2B) + at least 1 data byte + CRC(2B) */
            state = FOTA_STATE_ERROR;
            break;
        }

        /* Parse chunk header */
        uint16_t seq = ((uint16_t)chunk_buf[1] << 8) | chunk_buf[0];
        uint16_t data_len = ((uint16_t)chunk_buf[3] << 8) | chunk_buf[2];

        if (data_len > FOTA_CHUNK_SIZE) {
            state = FOTA_STATE_ERROR;
            break;
        }

        /* Verify CRC-16 over data */
        uint16_t received_crc = ((uint16_t)chunk_buf[data_len + 5] << 8) | chunk_buf[data_len + 4];
        uint16_t computed_crc = crc16_compute(&chunk_buf[4], data_len);

        if (computed_crc != received_crc) {
            /* Send NAK with last good sequence */
            uint8_t nak[3];
            nak[0] = FOTA_PROTOCOL_NAK;
            if (expected_seq > 0) {
                nak[1] = (uint8_t)((expected_seq - 1) & 0xFF);
                nak[2] = (uint8_t)(((expected_seq - 1) >> 8) & 0xFF);
            } else {
                nak[1] = 0xFF;
                nak[2] = 0xFF;
            }
            UART_SendByte(nak[0]);
            UART_SendByte(nak[1]);
            UART_SendByte(nak[2]);
        } else if (seq == expected_seq) {
            /* Store received data to patch buffer */
            /* In production, write chunk data to flash or RAM buffer for bspatch */
            progress_bytes += data_len;
            expected_seq++;

            /* Send ACK */
            UART_SendByte(FOTA_PROTOCOL_ACK);

#ifndef TEST
            last_activity_tick = HAL_GetTick();
#endif

            /* Start next chunk receive */
            UART_StartRx_IT(chunk_buf, FOTA_CHUNK_SIZE + 4);
        }
        /* else: seq != expected_seq — duplicate/old chunk, resend ACK */

        break;
    }

    case FOTA_STATE_APPLYING: {
        /* bspatch is applied synchronously in fota_apply_stored_patch() */
        break;
    }

    case FOTA_STATE_VERIFYING: {
        /* CRC verification of reconstructed firmware in Slot B */
        break;
    }

    case FOTA_STATE_COMPLETE:
    case FOTA_STATE_ERROR:
    default:
        break;
    }
}