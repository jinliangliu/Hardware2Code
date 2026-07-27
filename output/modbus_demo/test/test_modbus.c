#include "unity.h"
#include "mock_hal.h"
#include <string.h>

/* Include driver source to access static functions */
#include "../src/drivers/drv_modbus.c"

/* ---- Mock buffers for TX/RX simulation ---- */
static uint8_t mock_tx_buf[256];
static uint16_t mock_tx_len;
static uint8_t mock_rx_buf[256];
static uint16_t mock_rx_len;
static uint16_t mock_rx_idx;

/* ---- Mock TX function (captures transmitted data) ---- */
static uint8_t mock_modbus_tx(uint8_t *data, uint16_t len)
{
    if (len <= sizeof(mock_tx_buf)) {
        memcpy(mock_tx_buf, data, len);
        mock_tx_len = len;
    }
    return 1;
}

/* ---- Mock RX function (feeds pre-set data byte by byte) ---- */
static uint8_t mock_modbus_rx(uint8_t *buf, uint16_t len, uint32_t timeout)
{
    (void)timeout;
    uint16_t i;
    for (i = 0; i < len && mock_rx_idx < mock_rx_len; i++) {
        buf[i] = mock_rx_buf[mock_rx_idx++];
    }
    return i;
}

/* ---- Mock register callbacks ---- */
static uint16_t mock_regs[256];

static uint8_t mock_read_writes_called;
static uint16_t mock_last_write_addr;
static uint16_t mock_last_write_val;

static void mock_reg_read(uint16_t addr, uint16_t *val)
{
    if (addr < 256) {
        *val = mock_regs[addr];
    } else {
        *val = 0;
    }
}

static void mock_reg_write(uint16_t addr, uint16_t val)
{
    mock_read_writes_called = 1;
    mock_last_write_addr = addr;
    mock_last_write_val = val;
    if (addr < 256) {
        mock_regs[addr] = val;
    }
}

/* ---- Helper: reset all mock state ---- */
static void mock_modbus_reset(void)
{
    memset(mock_tx_buf, 0, sizeof(mock_tx_buf));
    mock_tx_len = 0;
    memset(mock_rx_buf, 0, sizeof(mock_rx_buf));
    mock_rx_len = 0;
    mock_rx_idx = 0;
    memset(mock_regs, 0, sizeof(mock_regs));
    mock_read_writes_called = 0;
    mock_last_write_addr = 0;
    mock_last_write_val = 0;
}

/* ---- Helper: set RX buffer and init modbus ---- */
static void mock_modbus_init_with_rx(const uint8_t *data, uint16_t len)
{
    mock_modbus_reset();
    if (data && len > 0 && len <= sizeof(mock_rx_buf)) {
        memcpy(mock_rx_buf, data, len);
        mock_rx_len = len;
    }
    modbus_init(1, mock_modbus_tx, mock_modbus_rx,
                mock_reg_read, mock_reg_write);
}

/* ---- Helper: add CRC to a frame and return full length ---- */
static uint16_t mock_frame_add_crc(uint8_t *frame, uint16_t len)
{
    uint16_t crc = crc16_modbus_compute(frame, len);
    frame[len] = (uint8_t)(crc & 0xFF);     /* low byte first */
    frame[len + 1] = (uint8_t)(crc >> 8);
    return (uint16_t)(len + 2);
}

/* ====================================================================== */
/* Test cases                                                              */
/* ====================================================================== */

void setUp(void)
{
    mock_modbus_reset();
    modbus_init(1, mock_modbus_tx, mock_modbus_rx,
                mock_reg_read, mock_reg_write);
}

void tearDown(void)
{
    /* nothing */
}

/* ---- test_crc16_modbus_known_vector ---- */
/* "123456789" -> 0x4B37 (CRC-16/MODBUS, NOT 0x29B1 CCITT!) */
void test_crc16_modbus_known_vector(void)
{
    const uint8_t test_data[] = {'1','2','3','4','5','6','7','8','9'};
    uint16_t crc = crc16_modbus_compute(test_data, sizeof(test_data));
    TEST_ASSERT_EQUAL_HEX16(0x4B37, crc);
}

/* ---- test_crc16_modbus_all_zeros ---- */
void test_crc16_modbus_all_zeros(void)
{
    const uint8_t test_data[8] = {0};
    uint16_t crc = crc16_modbus_compute(test_data, sizeof(test_data));
    TEST_ASSERT_EQUAL_HEX16(0x0B40, crc);
}

/* ---- test_crc16_modbus_differs_from_ccitt ---- */
/* Same input produces different CRC for 0x8005 vs 0x1021 polynomials */
void test_crc16_modbus_differs_from_ccitt(void)
{
    const uint8_t test_data[] = {'1','2','3','4','5','6','7','8','9'};
    uint16_t crc_modbus = crc16_modbus_compute(test_data, sizeof(test_data));
    /* CCITT would be 0x29B1, Modbus must NOT be that */
    TEST_ASSERT_NOT_EQUAL(0x29B1, crc_modbus);
    /* But it must be the known Modbus value */
    TEST_ASSERT_EQUAL_HEX16(0x4B37, crc_modbus);
}

/* ---- test_modbus_read_holding_regs_frame_build ---- */
/* Build a read response and verify CRC */
void test_modbus_read_holding_regs_frame_build(void)
{
    uint8_t frame[8];
    uint16_t crc;

    /* Build read holding regs request: addr=1, func=03, start=0, count=2 */
    frame[0] = 0x01;  /* slave addr */
    frame[1] = MODBUS_FC_READ_HOLDING_REGS;
    frame[2] = 0x00;  /* start addr high */
    frame[3] = 0x00;  /* start addr low */
    frame[4] = 0x00;  /* count high */
    frame[5] = 0x02;  /* count low (2 registers) */
    crc = crc16_modbus_compute(frame, 6);
    frame[6] = (uint8_t)(crc & 0xFF);
    frame[7] = (uint8_t)(crc >> 8);

    /* Feed to driver */
    mock_modbus_init_with_rx(frame, 8);

    /* Set register values after init (reset zeros them) */
    mock_regs[0] = 0x1234;
    mock_regs[1] = 0x5678;

    /* Process: call the static handler directly */
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* Verify response: addr=1, func=03, byte_count=4, data=12 34 56 78, crc */
    TEST_ASSERT_EQUAL_UINT8(0x01, mock_tx_buf[0]);
    TEST_ASSERT_EQUAL_UINT8(MODBUS_FC_READ_HOLDING_REGS, mock_tx_buf[1]);
    TEST_ASSERT_EQUAL_UINT8(4, mock_tx_buf[2]);  /* byte_count = 2*2 */
    TEST_ASSERT_EQUAL_UINT8(0x12, mock_tx_buf[3]);
    TEST_ASSERT_EQUAL_UINT8(0x34, mock_tx_buf[4]);
    TEST_ASSERT_EQUAL_UINT8(0x56, mock_tx_buf[5]);
    TEST_ASSERT_EQUAL_UINT8(0x78, mock_tx_buf[6]);

    /* Verify CRC of response */
    {
        uint16_t resp_crc = crc16_modbus_compute(mock_tx_buf, 7);
        uint8_t crc_lo = (uint8_t)(resp_crc & 0xFF);
        uint8_t crc_hi = (uint8_t)(resp_crc >> 8);
        TEST_ASSERT_EQUAL_UINT8(crc_lo, mock_tx_buf[7]);
        TEST_ASSERT_EQUAL_UINT8(crc_hi, mock_tx_buf[8]);
    }
}

/* ---- test_modbus_write_single_reg_echo ---- */
void test_modbus_write_single_reg_echo(void)
{
    uint8_t frame[8];

    /* Build write single register request */
    frame[0] = 0x01;
    frame[1] = MODBUS_FC_WRITE_SINGLE_REG;
    frame[2] = 0x00;  /* addr high */
    frame[3] = 0x0A;  /* addr low = 10 */
    frame[4] = 0xAB;  /* value high */
    frame[5] = 0xCD;  /* value low */
    mock_frame_add_crc(frame, 6);

    mock_modbus_init_with_rx(frame, 8);

    /* Process frame */
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* Verify callback was called */
    TEST_ASSERT_EQUAL_UINT8(1, mock_read_writes_called);
    TEST_ASSERT_EQUAL_UINT16(10, mock_last_write_addr);
    TEST_ASSERT_EQUAL_UINT16(0xABCD, mock_last_write_val);

    /* Verify echo response: addr, func, addr(2), value(2), crc(2) */
    TEST_ASSERT_EQUAL_UINT8(0x01, mock_tx_buf[0]);
    TEST_ASSERT_EQUAL_UINT8(MODBUS_FC_WRITE_SINGLE_REG, mock_tx_buf[1]);
    TEST_ASSERT_EQUAL_UINT8(0x00, mock_tx_buf[2]);
    TEST_ASSERT_EQUAL_UINT8(0x0A, mock_tx_buf[3]);
    TEST_ASSERT_EQUAL_UINT8(0xAB, mock_tx_buf[4]);
    TEST_ASSERT_EQUAL_UINT8(0xCD, mock_tx_buf[5]);

    /* CRC of response */
    {
        uint16_t resp_crc = crc16_modbus_compute(mock_tx_buf, 6);
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(resp_crc & 0xFF), mock_tx_buf[6]);
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(resp_crc >> 8), mock_tx_buf[7]);
    }
}

/* ---- test_modbus_write_multiple_response ---- */
void test_modbus_write_multiple_response(void)
{
    uint8_t frame[256];
    uint16_t len;

    /* Build write multiple registers request: addr=0, count=2, 4 bytes data */
    frame[0] = 0x01;  /* slave addr */
    frame[1] = MODBUS_FC_WRITE_MULTIPLE_REGS;
    frame[2] = 0x00;  /* start addr high */
    frame[3] = 0x05;  /* start addr low = 5 */
    frame[4] = 0x00;  /* count high */
    frame[5] = 0x02;  /* count low = 2 */
    frame[6] = 0x04;  /* byte_count = 4 */
    frame[7] = 0x11;  /* reg[5] high */
    frame[8] = 0x22;  /* reg[5] low */
    frame[9] = 0x33;  /* reg[6] high */
    frame[10] = 0x44; /* reg[6] low */
    len = mock_frame_add_crc(frame, 11);

    mock_modbus_init_with_rx(frame, len);

    /* Process frame */
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* Verify registers were written */
    TEST_ASSERT_EQUAL_UINT16(0x1122, mock_regs[5]);
    TEST_ASSERT_EQUAL_UINT16(0x3344, mock_regs[6]);

    /* Verify response format: addr, func, start(2), count(2), crc(2) */
    TEST_ASSERT_EQUAL_UINT8(0x01, mock_tx_buf[0]);
    TEST_ASSERT_EQUAL_UINT8(MODBUS_FC_WRITE_MULTIPLE_REGS, mock_tx_buf[1]);
    TEST_ASSERT_EQUAL_UINT8(0x00, mock_tx_buf[2]);
    TEST_ASSERT_EQUAL_UINT8(0x05, mock_tx_buf[3]);
    TEST_ASSERT_EQUAL_UINT8(0x00, mock_tx_buf[4]);
    TEST_ASSERT_EQUAL_UINT8(0x02, mock_tx_buf[5]);

    /* CRC of response */
    {
        uint16_t resp_crc = crc16_modbus_compute(mock_tx_buf, 6);
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(resp_crc & 0xFF), mock_tx_buf[6]);
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(resp_crc >> 8), mock_tx_buf[7]);
    }
}

/* ---- test_modbus_broadcast_no_response ---- */
/* Address 0x00 should process write but not reply */
void test_modbus_broadcast_no_response(void)
{
    uint8_t frame[8];

    /* Build broadcast write single register request */
    frame[0] = MODBUS_BROADCAST_ADDR;
    frame[1] = MODBUS_FC_WRITE_SINGLE_REG;
    frame[2] = 0x00;
    frame[3] = 0x03;
    frame[4] = 0xDE;
    frame[5] = 0xAD;
    mock_frame_add_crc(frame, 6);

    mock_modbus_init_with_rx(frame, 8);

    /* Process frame */
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* Write callback should be called */
    TEST_ASSERT_EQUAL_UINT8(1, mock_read_writes_called);
    TEST_ASSERT_EQUAL_UINT16(3, mock_last_write_addr);
    TEST_ASSERT_EQUAL_UINT16(0xDEAD, mock_last_write_val);

    /* No response should be sent */
    TEST_ASSERT_EQUAL_UINT16(0, mock_tx_len);
}

/* ---- test_modbus_exception_illegal_function ---- */
void test_modbus_exception_illegal_function(void)
{
    uint8_t frame[6];

    /* Build request with unknown function code 0x2B */
    frame[0] = 0x01;  /* slave addr */
    frame[1] = 0x2B;  /* unknown function */
    frame[2] = 0x00;
    frame[3] = 0x00;
    mock_frame_add_crc(frame, 4);

    mock_modbus_init_with_rx(frame, 6);

    /* Process frame */
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* Should get exception: addr=1, func=0xAB (0x2B|0x80), excode=01 */
    TEST_ASSERT_EQUAL_UINT8(0x01, mock_tx_buf[0]);
    TEST_ASSERT_EQUAL_UINT8(0xAB, mock_tx_buf[1]); /* 0x2B | 0x80 */
    TEST_ASSERT_EQUAL_UINT8(MODBUS_EX_ILLEGAL_FUNCTION, mock_tx_buf[2]);

    /* CRC should be correct */
    {
        uint16_t exc_crc = crc16_modbus_compute(mock_tx_buf, 3);
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(exc_crc & 0xFF), mock_tx_buf[3]);
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(exc_crc >> 8), mock_tx_buf[4]);
    }
}

/* ---- test_modbus_crc_little_endian ---- */
/* CRC bytes must be in correct order: low byte first */
void test_modbus_crc_little_endian(void)
{
    const uint8_t test_data[] = {'1','2','3','4','5','6','7','8','9'};
    uint16_t crc = crc16_modbus_compute(test_data, sizeof(test_data));

    /* CRC = 0x4B37; low byte = 0x37, high byte = 0x4B */
    TEST_ASSERT_EQUAL_UINT8(0x37, (uint8_t)(crc & 0xFF));
    TEST_ASSERT_EQUAL_UINT8(0x4B, (uint8_t)(crc >> 8));
}

/* ---- test_modbus_crc_bad_frame_silently_dropped ---- */
/* Frame with wrong CRC should be silently dropped */
void test_modbus_crc_bad_frame_silently_dropped(void)
{
    uint8_t frame[8];

    /* Build read request with intentional CRC error */
    frame[0] = 0x01;
    frame[1] = MODBUS_FC_READ_HOLDING_REGS;
    frame[2] = 0x00;
    frame[3] = 0x00;
    frame[4] = 0x00;
    frame[5] = 0x01;
    /* Intentionally wrong CRC */
    frame[6] = 0xFF;
    frame[7] = 0xFF;

    mock_modbus_init_with_rx(frame, 8);

    /* Process frame */
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* No response should be sent */
    TEST_ASSERT_EQUAL_UINT16(0, mock_tx_len);
}

/* ---- test_modbus_wrong_address_ignored ---- */
void test_modbus_wrong_address_ignored(void)
{
    uint8_t frame[8];

    /* Build valid read request but addressed to slave 0x10 */
    frame[0] = 0x10;  /* different slave ID */
    frame[1] = MODBUS_FC_READ_HOLDING_REGS;
    frame[2] = 0x00;
    frame[3] = 0x00;
    frame[4] = 0x00;
    frame[5] = 0x01;
    mock_frame_add_crc(frame, 6);

    mock_modbus_init_with_rx(frame, 8);

    /* Process frame */
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* No response (not our address) */
    TEST_ASSERT_EQUAL_UINT16(0, mock_tx_len);
}

/* ---- test_modbus_read_holding_regs_count_zero ---- */
/* Count of 0 should trigger exception */
void test_modbus_read_holding_regs_count_zero(void)
{
    uint8_t frame[8];

    frame[0] = 0x01;
    frame[1] = MODBUS_FC_READ_HOLDING_REGS;
    frame[2] = 0x00;
    frame[3] = 0x00;
    frame[4] = 0x00;
    frame[5] = 0x00;  /* count = 0 (invalid) */
    mock_frame_add_crc(frame, 6);

    mock_modbus_init_with_rx(frame, 8);
    modbus_handle_frame(mock_rx_buf, mock_rx_len);

    /* Should get exception response */
    TEST_ASSERT_EQUAL_UINT8(0x01, mock_tx_buf[0]);
    TEST_ASSERT_EQUAL_UINT8(MODBUS_FC_READ_HOLDING_REGS | 0x80, mock_tx_buf[1]);
    TEST_ASSERT_EQUAL_UINT8(MODBUS_EX_ILLEGAL_DATA, mock_tx_buf[2]);
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_crc16_modbus_known_vector);
    RUN_TEST(test_crc16_modbus_all_zeros);
    RUN_TEST(test_crc16_modbus_differs_from_ccitt);
    RUN_TEST(test_modbus_read_holding_regs_frame_build);
    RUN_TEST(test_modbus_write_single_reg_echo);
    RUN_TEST(test_modbus_write_multiple_response);
    RUN_TEST(test_modbus_broadcast_no_response);
    RUN_TEST(test_modbus_exception_illegal_function);
    RUN_TEST(test_modbus_crc_little_endian);
    RUN_TEST(test_modbus_crc_bad_frame_silently_dropped);
    RUN_TEST(test_modbus_wrong_address_ignored);
    RUN_TEST(test_modbus_read_holding_regs_count_zero);

    return UNITY_END();
}