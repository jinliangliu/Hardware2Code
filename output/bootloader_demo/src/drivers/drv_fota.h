#ifndef __DRV_FOTA_H
#define __DRV_FOTA_H

#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#include <stdbool.h>
#endif

#include <stdint.h>

/* ---- Protocol constants ---- */

#define FOTA_CHUNK_SIZE         1024
#define FOTA_PROTOCOL_START_CMD 0xF00AU
#define FOTA_PROTOCOL_END_CMD   0xF00EU
#define FOTA_PROTOCOL_ACK       0x06U
#define FOTA_PROTOCOL_NAK       0x15U

/* ---- TAMP BKP4R flag bits ---- */

#define FOTA_FLAG_IN_PROGRESS   0x01U   /* Bit 0: receiving patch */
#define FOTA_FLAG_PATCH_READY   0x02U   /* Bit 1: patch fully written to Slot B */
#define FOTA_FLAG_VERIFY_FAIL   0x04U   /* Bit 2: CRC verify failed */
#define FOTA_FLAG_APPLY_FAIL    0x08U   /* Bit 3: bspatch apply error */

/* Version number encoded in BKP4R upper 24 bits */
#define FOTA_VERSION_MASK       0xFFFFFF00U
#define FOTA_VERSION_SHIFT      8U

/* ---- State enum ---- */

typedef enum {
    FOTA_STATE_IDLE,
    FOTA_STATE_RECEIVING,
    FOTA_STATE_APPLYING,
    FOTA_STATE_VERIFYING,
    FOTA_STATE_COMPLETE,
    FOTA_STATE_ERROR
} fota_state_t;

/* ---- API ---- */

void fota_init(void);
fota_state_t fota_get_state(void);
void fota_process(void);
uint32_t fota_get_progress(void);

#endif /* __DRV_FOTA_H */