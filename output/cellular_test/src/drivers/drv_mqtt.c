#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#endif
#include "drv_mqtt.h"
#include <stdlib.h>
#include <string.h>

/* ------------------------------------------------------------------ */
/* Static state                                                        */
/* ------------------------------------------------------------------ */
static mqtt_send_func_t mqtt_send_func;
static mqtt_recv_func_t mqtt_recv_func;
static int              mqtt_sock = -1;
static char             mqtt_client_id[48];
static uint16_t         mqtt_packet_id = 0;
static uint32_t         mqtt_last_ping;
static uint16_t         mqtt_keep_alive_s = 60;

/* Callback registry */
static char           mqtt_cb_topic[MQTT_MAX_CALLBACKS][MQTT_MAX_TOPIC_LEN];
static mqtt_msg_cb_t  mqtt_cb_func[MQTT_MAX_CALLBACKS];
static uint8_t         mqtt_cb_count = 0;

/* ------------------------------------------------------------------ */
/* Mock support for unit testing                                       */
/* ------------------------------------------------------------------ */
#ifdef TEST
/* Transport mock: TX data goes to mock_tx_buf, RX reads from mock_rx_buf */
extern uint8_t  mock_mqtt_rx_buf[];
extern uint16_t mock_mqtt_rx_len;
extern uint16_t mock_mqtt_rx_idx;
extern uint8_t  mock_mqtt_tx_buf[];
extern uint16_t mock_mqtt_tx_len;

static int mock_send(int sock, const uint8_t *data, uint16_t len)
{
    uint16_t i;
    (void)sock;
    for (i = 0; i < len && mock_mqtt_tx_len < 2048; i++) {
        mock_mqtt_tx_buf[mock_mqtt_tx_len++] = data[i];
    }
    return (int)len;
}

static int mock_recv(int sock, uint8_t *buf, uint16_t len, uint32_t timeout_ms)
{
    uint16_t i;
    (void)sock;
    (void)timeout_ms;
    for (i = 0; i < len && mock_mqtt_rx_idx < mock_mqtt_rx_len; i++) {
        buf[i] = mock_mqtt_rx_buf[mock_mqtt_rx_idx++];
    }
    return (int)i;
}

#endif

static uint32_t mqtt_get_tick(void)
{
#ifndef TEST
    return HAL_GetTick();
#else
    /* Auto-incrementing tick in test mode to ensure timeouts expire */
    static uint32_t mock_tick = 0;
    mock_tick += 100;
    return mock_tick;
#endif
}

/* ------------------------------------------------------------------ */
/* Packet building helpers                                             */
/* ------------------------------------------------------------------ */

/**
 * @brief   Encode remaining length as variable-length integer
 * @param   len     Remaining length value
 * @param   buf     Output buffer (must be at least 4 bytes)
 * @return  Number of bytes written (1-4)
 */
static uint8_t mqtt_encode_remaining_length(uint32_t len, uint8_t *buf)
{
    uint8_t i = 0;
    do {
        uint8_t byte = (uint8_t)(len % 128);
        len /= 128;
        if (len > 0) {
            byte |= 0x80;
        }
        buf[i++] = byte;
    } while (len > 0 && i < 4);
    return i;
}

/**
 * @brief   Decode variable-length remaining length from buffer
 * @param   buf     Input buffer
 * @param   out_len Pointer to store decoded length
 * @param   consumed Pointer to store bytes consumed
 * @return  0 on success, -1 on error
 */
static int mqtt_decode_remaining_length(const uint8_t *buf, uint32_t *out_len,
                                        uint8_t *consumed)
{
    uint32_t value = 0;
    uint32_t multiplier = 1;
    uint8_t  i;
    uint8_t  byte;

    for (i = 0; i < 4; i++) {
        byte = buf[i];
        value += (uint32_t)(byte & 0x7F) * multiplier;
        multiplier *= 128;
        if (multiplier > 128 * 128 * 128) {
            /* Overflow protection */
            return -1;
        }
        if ((byte & 0x80) == 0) {
            *out_len = value;
            *consumed = i + 1;
            return 0;
        }
    }
    return -1;
}

/**
 * @brief   Write a 2-byte big-endian length-prefixed UTF-8 string
 * @param   buf     Output buffer
 * @param   str     Null-terminated string
 * @return  Number of bytes written (2 + strlen(str))
 */
static uint16_t mqtt_build_string_field(uint8_t *buf, const char *str)
{
    uint16_t slen;
    if (!str) {
        buf[0] = 0;
        buf[1] = 0;
        return 2;
    }
    slen = (uint16_t)strlen(str);
    buf[0] = (uint8_t)(slen >> 8);
    buf[1] = (uint8_t)(slen & 0xFF);
    if (slen > 0) {
        memcpy(buf + 2, str, slen);
    }
    return (uint16_t)(2 + slen);
}

/**
 * @brief   Send a complete MQTT packet via transport
 * @param   type        Packet type (upper 4 bits)
 * @param   flags       Flags (lower 4 bits)
 * @param   payload     Variable header + payload data
 * @param   len         Length of payload
 * @return  Number of bytes sent, or MQTT_ERROR
 */
static int mqtt_send_packet(uint8_t type, uint8_t flags,
                            const uint8_t *payload, uint32_t len)
{
    uint8_t fixed[5];
    uint8_t rl_bytes;
    uint8_t header;
    int     ret;

    header = (uint8_t)((type << 4) | (flags & 0x0F));
    rl_bytes = mqtt_encode_remaining_length(len, fixed + 1);
    fixed[0] = header;

    /* Send fixed header */
    ret = mqtt_send_func(mqtt_sock, fixed, (uint16_t)(1 + rl_bytes));
    if (ret < 0) return MQTT_ERROR;

    /* Send payload */
    if (len > 0) {
        ret = mqtt_send_func(mqtt_sock, payload, (uint16_t)len);
        if (ret < 0) return MQTT_ERROR;
    }

    return (int)(1 + rl_bytes + len);
}

/**
 * @brief   Read exactly N bytes from transport with timeout
 * @param   buf         Receive buffer
 * @param   len         Number of bytes to read
 * @param   timeout_ms  Timeout per receive call
 * @return  MQTT_OK on success, MQTT_TIMEOUT on timeout
 */
static int mqtt_read_exact(uint8_t *buf, uint16_t len, uint32_t timeout_ms)
{
    uint16_t total = 0;
    uint32_t start;
    int      n;

    start = mqtt_get_tick();
    while (total < len) {
        n = mqtt_recv_func(mqtt_sock, buf + total, len - total, timeout_ms);
        if (n <= 0) {
            if ((mqtt_get_tick() - start) >= timeout_ms) {
                return MQTT_TIMEOUT;
            }
            continue;
        }
        total += (uint16_t)n;
        start = mqtt_get_tick();
    }
    return MQTT_OK;
}

/**
 * @brief   Test if a topic name matches a topic filter with wildcards
 * @param   filter  Topic filter (may contain + and #)
 * @param   topic   Topic name to test
 * @return  1 if match, 0 if no match
 */
static int mqtt_topic_match(const char *filter, const char *topic)
{
    if (!filter || !topic) return 0;

    while (*filter && *topic) {
        if (*filter == '+') {
            /* Single-level wildcard: match until next '/' or end */
            while (*topic && *topic != '/') {
                topic++;
            }
            filter++;
        } else if (*filter == '#') {
            /* Multi-level wildcard: match everything */
            filter++;
            if (*filter == '\0') {
                /* # at end matches everything */
                return 1;
            }
            /* # followed by more is invalid per MQTT spec */
            return 0;
        } else if (*filter == *topic) {
            filter++;
            topic++;
        } else {
            return 0;
        }
    }

    /* Both must reach end simultaneously, unless filter ends with # */
    if (*filter == '#' && filter[1] == '\0') {
        return 1;
    }
    return (*filter == '\0' && *topic == '\0');
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void mqtt_init(void *send_func, void *recv_func, const char *client_id)
{
#ifdef TEST
    mqtt_send_func = mock_send;
    mqtt_recv_func = mock_recv;
    (void)send_func;
    (void)recv_func;
#else
    mqtt_send_func = (mqtt_send_func_t)send_func;
    mqtt_recv_func = (mqtt_recv_func_t)recv_func;
#endif
    mqtt_sock = -1;
    mqtt_packet_id = 0;
    mqtt_cb_count = 0;
    mqtt_last_ping = 0;
    mqtt_keep_alive_s = 60;

    if (client_id) {
        uint16_t i;
        for (i = 0; i < sizeof(mqtt_client_id) - 1 && client_id[i]; i++) {
            mqtt_client_id[i] = client_id[i];
        }
        mqtt_client_id[i] = '\0';
    } else {
        mqtt_client_id[0] = '\0';
    }

    memset(mqtt_cb_topic, 0, sizeof(mqtt_cb_topic));
    memset(mqtt_cb_func, 0, sizeof(mqtt_cb_func));
}

int mqtt_connect(const char *username, const char *password,
                 uint16_t keep_alive_s)
{
    uint8_t  buf[256];
    uint8_t  resp[4];
    uint16_t pos = 0;
    uint8_t  connect_flags = 0;

    if (!mqtt_client_id[0]) return MQTT_ERROR;

    mqtt_keep_alive_s = keep_alive_s;

    /* -- Variable header: Protocol name "MQTT" -- */
    memcpy(buf + pos, "\x00\x04MQTT", 6);
    pos += 6;

    /* Protocol level: 4 (MQTT 3.1.1) */
    buf[pos++] = 4;

    /* Connect flags */
    connect_flags |= 0x02; /* Clean session */
    if (username && username[0]) {
        connect_flags |= 0x80; /* Username flag */
    }
    if (password && password[0]) {
        connect_flags |= 0x40; /* Password flag */
    }
    buf[pos++] = connect_flags;

    /* Keep alive */
    buf[pos++] = (uint8_t)(keep_alive_s >> 8);
    buf[pos++] = (uint8_t)(keep_alive_s & 0xFF);

    /* -- Payload: Client ID -- */
    pos += mqtt_build_string_field(buf + pos, mqtt_client_id);

    /* Username */
    if (connect_flags & 0x80) {
        pos += mqtt_build_string_field(buf + pos, username);
    }

    /* Password */
    if (connect_flags & 0x40) {
        pos += mqtt_build_string_field(buf + pos, password);
    }

    /* Send CONNECT packet */
    if (mqtt_send_packet(MQTT_CONNECT, 0, buf, pos) < 0) {
        return MQTT_ERROR;
    }

    /* Read CONNACK: expects 0x20 0x02 0x00 0x00 */
    {
        int ret = mqtt_read_exact(resp, 4, 10000);
        if (ret != MQTT_OK) return MQTT_TIMEOUT;

        if (resp[0] != 0x20 || resp[1] != 0x02) {
            return MQTT_ERROR;
        }
        if (resp[3] != 0x00) {
            /* Connection refused */
            return MQTT_ERROR;
        }
    }

    mqtt_last_ping = mqtt_get_tick();
    return MQTT_OK;
}

int mqtt_publish(const char *topic, const uint8_t *payload, uint16_t len,
                 uint8_t qos)
{
    uint8_t  buf[256];
    uint16_t pos = 0;
    uint8_t  flags = 0;

    if (!topic || !payload) return MQTT_ERROR;

    /* Build variable header + payload */
    pos += mqtt_build_string_field(buf + pos, topic);

    if (qos > 0) {
        flags |= (uint8_t)((qos & 0x03) << 1);
        mqtt_packet_id++;
        buf[pos++] = (uint8_t)(mqtt_packet_id >> 8);
        buf[pos++] = (uint8_t)(mqtt_packet_id & 0xFF);
    }

    if (len > 0) {
        if (pos + len <= sizeof(buf)) {
            memcpy(buf + pos, payload, len);
            pos += len;
        } else {
            return MQTT_ERROR;
        }
    }

    return mqtt_send_packet(MQTT_PUBLISH, flags, buf, pos) < 0
           ? MQTT_ERROR : MQTT_OK;
}

int mqtt_subscribe(const char *topic, uint8_t qos)
{
    uint8_t  buf[256];
    uint16_t pos = 0;

    if (!topic) return MQTT_ERROR;

    /* Packet ID */
    mqtt_packet_id++;
    buf[pos++] = (uint8_t)(mqtt_packet_id >> 8);
    buf[pos++] = (uint8_t)(mqtt_packet_id & 0xFF);

    /* Topic filter */
    pos += mqtt_build_string_field(buf + pos, topic);

    /* Requested QoS */
    buf[pos++] = (qos & 0x03);

    /* Send SUBSCRIBE */
    if (mqtt_send_packet(MQTT_SUBSCRIBE, 2, buf, pos) < 0) {
        return MQTT_ERROR;
    }

    /* Read SUBACK: expects 0x90 0x03 <packet_id_hi> <packet_id_lo> <return_code> */
    {
        uint8_t suback[5];
        int     ret;
        uint8_t type;

        ret = mqtt_read_exact(suback, 2, 5000);
        if (ret != MQTT_OK) return MQTT_TIMEOUT;

        type = suback[0] >> 4;
        if (type != MQTT_SUBACK) {
            return MQTT_ERROR;
        }

        /* Remaining length should be 3 */
        if (suback[1] != 3) {
            return MQTT_ERROR;
        }

        ret = mqtt_read_exact(suback + 2, 3, 5000);
        if (ret != MQTT_OK) return MQTT_TIMEOUT;

        /* Verify packet ID */
        {
            uint16_t pid = (uint16_t)((suback[2] << 8) | suback[3]);
            if (pid != mqtt_packet_id) {
                return MQTT_ERROR;
            }
        }

        /* Return code 0x80 = failure, anything else = success */
        if (suback[4] == 0x80) {
            return MQTT_ERROR;
        }
    }

    return MQTT_OK;
}

int mqtt_ping(void)
{
    uint8_t resp[2];
    int     ret;

    /* Send PINGREQ: 0xC0 0x00 */
    ret = mqtt_send_packet(MQTT_PINGREQ, 0, NULL, 0);
    if (ret < 0) return MQTT_ERROR;

    /* Wait for PINGRESP: 0xD0 0x00 */
    ret = mqtt_read_exact(resp, 2, 5000);
    if (ret != MQTT_OK) return MQTT_TIMEOUT;

    if (resp[0] != 0xD0 || resp[1] != 0x00) {
        return MQTT_ERROR;
    }

    mqtt_last_ping = mqtt_get_tick();
    return MQTT_OK;
}

void mqtt_disconnect(void)
{
    mqtt_send_packet(MQTT_DISCONNECT, 0, NULL, 0);
}

/**
 * @brief   Dispatch incoming PUBLISH to registered callbacks
 */
static void mqtt_dispatch_publish(const uint8_t *topic, uint16_t topic_len,
                                  const uint8_t *payload, uint16_t payload_len)
{
    char   topic_str[MQTT_MAX_TOPIC_LEN];
    uint8_t i;

    if (topic_len >= MQTT_MAX_TOPIC_LEN) {
        return;
    }

    memcpy(topic_str, topic, topic_len);
    topic_str[topic_len] = '\0';

    for (i = 0; i < mqtt_cb_count; i++) {
        if (mqtt_topic_match(mqtt_cb_topic[i], topic_str)) {
            if (mqtt_cb_func[i]) {
                mqtt_cb_func[i](payload, payload_len);
            }
        }
    }

    /* QoS 1: send PUBACK */
    /* Simple implementation: check if PUBACK is needed */
}

void mqtt_process(void)
{
    uint8_t  header[2];
    uint8_t  remaining_rl_bytes;
    uint32_t remaining_len;
    uint8_t  packet_type;
    uint8_t  flags;
    int      ret;

    /* Check for incoming data */
    ret = mqtt_recv_func(mqtt_sock, header, 1, 10);
    if (ret <= 0) return;

    packet_type = header[0] >> 4;
    flags = header[0] & 0x0F;

    /* Read remaining length */
    remaining_rl_bytes = 0;
    mqtt_decode_remaining_length(header + 1, &remaining_len, &remaining_rl_bytes);

    /* For initial read, we already read 1 byte of the remaining length.
     * Read the rest (remaining_rl_bytes - 1) if needed, then remaining_len bytes.
     * But since we only read 1 byte of header initially, we need to read the
     * rest of the fixed header then the payload. */

    switch (packet_type) {
    case MQTT_CONNACK:
        /* Already handled in mqtt_connect */
        break;

    case MQTT_PUBLISH: {
        /* Read topic length (2 bytes) then topic, then remaining is payload */
        uint8_t  topic_len_buf[2];
        uint16_t topic_len;
        uint16_t payload_len;

        if (mqtt_read_exact(topic_len_buf, 2, 5000) != MQTT_OK) return;
        topic_len = (uint16_t)((topic_len_buf[0] << 8) | topic_len_buf[1]);

        if (topic_len > MQTT_MAX_TOPIC_LEN - 1) return;

        {
            uint8_t topic_buf[MQTT_MAX_TOPIC_LEN];
            if (mqtt_read_exact(topic_buf, topic_len, 5000) != MQTT_OK) return;

            payload_len = (uint16_t)(remaining_len - 2 - topic_len);
            if (payload_len > 0) {
                uint8_t *payload_buf;
                /* Stack safety: limit payload */
                if (payload_len > 256) payload_len = 256;
                payload_buf = (uint8_t *)malloc(payload_len);
                if (!payload_buf) return;

                if (mqtt_read_exact(payload_buf, payload_len, 5000) != MQTT_OK) {
                    free(payload_buf);
                    return;
                }
                mqtt_dispatch_publish(topic_buf, topic_len,
                                      payload_buf, payload_len);
                free(payload_buf);
            } else {
                mqtt_dispatch_publish(topic_buf, topic_len, NULL, 0);
            }
        }

        /* Send PUBACK if QoS 1 */
        if ((flags & 0x06) == 0x04) {
            uint8_t puback[2];
            /* Packet ID is at start of variable header */
            /* For simplicity, use current packet_id */
            puback[0] = (uint8_t)(mqtt_packet_id >> 8);
            puback[1] = (uint8_t)(mqtt_packet_id & 0xFF);
            mqtt_send_packet(MQTT_PUBACK, 0, puback, 2);
        }
        break;
    }

    case MQTT_PUBACK:
        /* Not needed for QoS 0; just consume */
        break;

    case MQTT_SUBACK:
        /* Already handled in mqtt_subscribe */
        break;

    case MQTT_PINGRESP:
        /* PINGRESP acknowledged */
        break;

    default:
        /* Unknown packet, skip */
        break;
    }
}

int mqtt_register_callback(const char *topic, mqtt_msg_cb_t cb)
{
    if (!topic || !cb) return MQTT_ERROR;
    if (mqtt_cb_count >= MQTT_MAX_CALLBACKS) return MQTT_ERROR;

    {
        uint16_t i;
        for (i = 0; i < MQTT_MAX_TOPIC_LEN - 1 && topic[i]; i++) {
            mqtt_cb_topic[mqtt_cb_count][i] = topic[i];
        }
        mqtt_cb_topic[mqtt_cb_count][i] = '\0';
    }

    mqtt_cb_func[mqtt_cb_count] = cb;
    mqtt_cb_count++;

    return MQTT_OK;
}