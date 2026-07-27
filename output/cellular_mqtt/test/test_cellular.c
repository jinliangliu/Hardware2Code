#include "unity.h"
#include "mock_hal.h"
#include <string.h>

/* ====================================================================== */
/* Mock buffers for the cellular driver (TEST mode)                        */
/* ====================================================================== */
char     mock_cellular_rx_buf[4096];
uint16_t mock_cellular_rx_len = 0;
uint16_t mock_cellular_rx_idx = 0;
char     mock_cellular_tx_buf[4096];
uint16_t mock_cellular_tx_len = 0;

/* ---- Helper to reset all mock state ---- */
static void mock_cellular_reset(void)
{
    memset(mock_cellular_rx_buf, 0, sizeof(mock_cellular_rx_buf));
    mock_cellular_rx_len = 0;
    mock_cellular_rx_idx = 0;
    memset(mock_cellular_tx_buf, 0, sizeof(mock_cellular_tx_buf));
    mock_cellular_tx_len = 0;
}

/* ---- Helper: set the RX buffer to a specific response ---- */
static void mock_cellular_set_rx(const char *data)
{
    mock_cellular_reset();
    if (data) {
        mock_cellular_rx_len = (uint16_t)strlen(data);
        memcpy(mock_cellular_rx_buf, data, mock_cellular_rx_len);
    }
}

/* ---- Helper: set RX with AT echo + response ---- */
static void mock_cellular_set_rx_with_echo(const char *cmd, const char *resp)
{
    mock_cellular_reset();
    int cmd_len = (int)strlen(cmd);
    int resp_len = (int)strlen(resp);
    int total = cmd_len + 2 + resp_len;
    if (total < (int)sizeof(mock_cellular_rx_buf)) {
        memcpy(mock_cellular_rx_buf, cmd, cmd_len);
        memcpy(mock_cellular_rx_buf + cmd_len, "\r\n", 2);
        memcpy(mock_cellular_rx_buf + cmd_len + 2, resp, resp_len);
        mock_cellular_rx_len = (uint16_t)(cmd_len + 2 + resp_len);
    }
}

/* ====================================================================== */
/* Include driver source under test                                        */
/* ====================================================================== */
#include "../src/drivers/drv_cellular.c"

/* ====================================================================== */
/* Test cases                                                              */
/* ====================================================================== */

void setUp(void)
{
    mock_cellular_reset();
}

void tearDown(void)
{
    /* nothing */
}

/* ---- test_cellular_init_stores_handle ---- */
void test_cellular_init_stores_handle(void)
{
    cellular_init(NULL);
    /* In TEST mode this is a no-op; just verify it does not crash */
    TEST_PASS();
}

/* ---- test_cellular_send_at_timeout_returns_error ---- */
void test_cellular_send_at_timeout_returns_error(void)
{
    char resp[256];
    /* RX buffer is empty -> timeout */
    mock_cellular_set_rx("");
    int ret = cellular_send_at("AT", resp, sizeof(resp), 500);
    TEST_ASSERT_EQUAL_INT(CELLULAR_TIMEOUT, ret);
}

/* ---- test_cellular_send_at_ok_returns_success ---- */
void test_cellular_send_at_ok_returns_success(void)
{
    char resp[256];
    mock_cellular_set_rx("OK\r\n");
    int ret = cellular_send_at("AT", resp, sizeof(resp), 500);
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
}

/* ---- test_cellular_send_at_error_returns_error ---- */
void test_cellular_send_at_error_returns_error(void)
{
    char resp[256];
    mock_cellular_set_rx("ERROR\r\n");
    int ret = cellular_send_at("AT", resp, sizeof(resp), 500);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

/* ---- test_cellular_send_at_with_echo ---- */
void test_cellular_send_at_with_echo(void)
{
    char resp[256];
    /* Simulate echo: "AT\r\nOK\r\n" */
    mock_cellular_set_rx("AT\r\nOK\r\n");
    int ret = cellular_send_at("AT", resp, sizeof(resp), 500);
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
}

/* ---- test_cellular_wait_network_registered ---- */
void test_cellular_wait_network_registered(void)
{
    /* First AT+CREG? returns "+CREG: 0,1", second AT+CGREG? returns "+CGREG: 0,1" */
    char combined[512];
    snprintf(combined, sizeof(combined),
             "AT+CREG?\r\n+CREG: 0,1\r\nOK\r\n"
             "AT+CGREG?\r\n+CGREG: 0,1\r\nOK\r\n");
    mock_cellular_set_rx(combined);
    int ret = cellular_wait_network(10000);
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
}

/* ---- test_cellular_get_imei_parses_correctly ---- */
void test_cellular_get_imei_parses_correctly(void)
{
    char imei[32];
    mock_cellular_set_rx("AT+GSN\r\n866723040000123\r\nOK\r\n");
    int ret = cellular_get_imei(imei, sizeof(imei));
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
    TEST_ASSERT_EQUAL_STRING("866723040000123", imei);
}

/* ---- test_cellular_get_ccid ---- */
void test_cellular_get_ccid_parses_correctly(void)
{
    char ccid[32];
    mock_cellular_set_rx("AT+QCCID\r\n+QCCID: 89860000000000000000\r\nOK\r\n");
    int ret = cellular_get_ccid(ccid, sizeof(ccid));
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
    TEST_ASSERT_EQUAL_STRING("89860000000000000000", ccid);
}

/* ---- test_cellular_pdp_activate_sequence ---- */
void test_cellular_pdp_activate_sequence(void)
{
    char combined[512];
    snprintf(combined, sizeof(combined),
             "AT+CGDCONT=1,\"IP\",\"CMNET\"\r\nOK\r\n"
             "AT+CGACT=1,1\r\nOK\r\n");
    mock_cellular_set_rx(combined);
    int ret = cellular_pdp_activate("CMNET");
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
}

/* ---- test_cellular_get_ip ---- */
void test_cellular_get_ip_parses_correctly(void)
{
    char ip[32];
    mock_cellular_set_rx(
        "AT+CGPADDR=1\r\n+CGPADDR: 1,\"10.80.123.45\"\r\nOK\r\n");
    int ret = cellular_get_ip(ip, sizeof(ip));
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
    TEST_ASSERT_EQUAL_STRING("10.80.123.45", ip);
}

/* ---- test_cellular_create_socket_parses_connect_id ---- */
void test_cellular_create_socket_parses_connect_id(void)
{
    mock_cellular_set_rx(
        "AT+QIOPEN=1,0,\"TCP\",\"example.com\",80,0,0\r\nOK\r\n+QIOPEN: 0,0\r\n");
    int sock = cellular_create_socket("example.com", 80);
    TEST_ASSERT_EQUAL_INT(0, sock);
}

/* ---- test_cellular_close_socket ---- */
void test_cellular_close_socket_returns_ok(void)
{
    mock_cellular_set_rx("AT+QICLOSE=0\r\nOK\r\n");
    int ret = cellular_close_socket(0);
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
}

/* ---- test_search_response_helper ---- */
void test_search_response_finds_substring(void)
{
    /* search_response is static; test indirectly via send_at */
    char resp[256];
    mock_cellular_set_rx("SOME TEXT\r\n+CGREG: 0,5\r\nOK\r\n");
    int ret = cellular_send_at("AT+CGREG?", resp, sizeof(resp), 500);
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
}

/* ---- test_send_at_null_pointer_guard ---- */
void test_cellular_send_at_null_cmd_returns_error(void)
{
    char resp[256];
    int ret = cellular_send_at(NULL, resp, sizeof(resp), 500);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

void test_cellular_send_at_null_resp_returns_error(void)
{
    int ret = cellular_send_at("AT", NULL, 0, 500);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

/* ---- test_null_pointer_guard ---- */
void test_cellular_get_imei_null_returns_error(void)
{
    int ret = cellular_get_imei(NULL, 32);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

void test_cellular_get_ccid_null_returns_error(void)
{
    int ret = cellular_get_ccid(NULL, 32);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

void test_cellular_get_ip_null_returns_error(void)
{
    int ret = cellular_get_ip(NULL, 32);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

void test_cellular_create_socket_null_returns_error(void)
{
    int ret = cellular_create_socket(NULL, 80);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

void test_cellular_send_null_data_returns_error(void)
{
    int ret = cellular_send(0, NULL, 10);
    TEST_ASSERT_EQUAL_INT(CELLULAR_ERROR, ret);
}

void test_cellular_pdp_activate_null_apn(void)
{
    char combined[512];
    snprintf(combined, sizeof(combined),
             "AT+CGDCONT=1,\"IP\",\"\"\r\nOK\r\n"
             "AT+CGACT=1,1\r\nOK\r\n");
    mock_cellular_set_rx(combined);
    int ret = cellular_pdp_activate(NULL);
    TEST_ASSERT_EQUAL_INT(CELLULAR_OK, ret);
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_cellular_init_stores_handle);
    RUN_TEST(test_cellular_send_at_timeout_returns_error);
    RUN_TEST(test_cellular_send_at_ok_returns_success);
    RUN_TEST(test_cellular_send_at_error_returns_error);
    RUN_TEST(test_cellular_send_at_with_echo);
    RUN_TEST(test_cellular_wait_network_registered);
    RUN_TEST(test_cellular_get_imei_parses_correctly);
    RUN_TEST(test_cellular_get_ccid_parses_correctly);
    RUN_TEST(test_cellular_pdp_activate_sequence);
    RUN_TEST(test_cellular_get_ip_parses_correctly);
    RUN_TEST(test_cellular_create_socket_parses_connect_id);
    RUN_TEST(test_cellular_close_socket_returns_ok);
    RUN_TEST(test_search_response_finds_substring);
    RUN_TEST(test_cellular_send_at_null_cmd_returns_error);
    RUN_TEST(test_cellular_send_at_null_resp_returns_error);
    RUN_TEST(test_cellular_get_imei_null_returns_error);
    RUN_TEST(test_cellular_get_ccid_null_returns_error);
    RUN_TEST(test_cellular_get_ip_null_returns_error);
    RUN_TEST(test_cellular_create_socket_null_returns_error);
    RUN_TEST(test_cellular_send_null_data_returns_error);
    RUN_TEST(test_cellular_pdp_activate_null_apn);

    return UNITY_END();
}