#ifndef __DRV_MQTT_H
#define __DRV_MQTT_H

#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#include <stdbool.h>
#endif

#include <stdint.h>

/* MQTT packet types */
#define MQTT_CONNECT      1
#define MQTT_CONNACK      2
#define MQTT_PUBLISH      3
#define MQTT_PUBACK       4
#define MQTT_SUBSCRIBE    8
#define MQTT_SUBACK       9
#define MQTT_PINGREQ     12
#define MQTT_PINGRESP    13
#define MQTT_DISCONNECT  14

/* Return codes */
#define MQTT_OK           0
#define MQTT_ERROR       -1
#define MQTT_TIMEOUT     -2

/* Max topic length */
#define MQTT_MAX_TOPIC_LEN    128
/* Max callbacks */
#define MQTT_MAX_CALLBACKS    8

/* Transport function types */
typedef int (*mqtt_send_func_t)(int sock, const uint8_t *data, uint16_t len);
typedef int (*mqtt_recv_func_t)(int sock, uint8_t *buf, uint16_t len,
                                uint32_t timeout_ms);

/* Message callback */
typedef void (*mqtt_msg_cb_t)(const uint8_t *payload, uint16_t len);

/**
 * @brief   Initialize MQTT client with transport callbacks
 * @param   send_func   Function to send data via transport (e.g. cellular_send)
 * @param   recv_func   Function to receive data via transport (e.g. cellular_recv)
 * @param   client_id   Unique client identifier string
 */
void mqtt_init(void *send_func, void *recv_func, const char *client_id);

/**
 * @brief   Connect to MQTT broker with optional credentials
 * @param   username       Username (NULL if none)
 * @param   password       Password (NULL if none)
 * @param   keep_alive_s   Keep-alive interval in seconds
 * @return  MQTT_OK on success, MQTT_ERROR on protocol error, MQTT_TIMEOUT on timeout
 */
int  mqtt_connect(const char *username, const char *password,
                  uint16_t keep_alive_s);

/**
 * @brief   Publish a message to a topic
 * @param   topic    Topic string (UTF-8)
 * @param   payload  Payload data
 * @param   len      Payload length in bytes
 * @param   qos      QoS level (0 or 1)
 * @return  MQTT_OK on success
 */
int  mqtt_publish(const char *topic, const uint8_t *payload, uint16_t len,
                  uint8_t qos);

/**
 * @brief   Subscribe to a topic
 * @param   topic   Topic filter string (may contain wildcards + and #)
 * @param   qos     Requested QoS level (0 or 1)
 * @return  MQTT_OK on success
 */
int  mqtt_subscribe(const char *topic, uint8_t qos);

/**
 * @brief   Send PINGREQ and wait for PINGRESP
 * @return  MQTT_OK on success
 */
int  mqtt_ping(void);

/**
 * @brief   Send DISCONNECT packet
 */
void mqtt_disconnect(void);

/**
 * @brief   Process incoming MQTT packets (call periodically in main loop)
 */
void mqtt_process(void);

/**
 * @brief   Register a callback for a specific topic
 * @param   topic   Topic filter string
 * @param   cb      Callback function
 * @return  MQTT_OK on success, MQTT_ERROR if max callbacks reached
 */
int  mqtt_register_callback(const char *topic, mqtt_msg_cb_t cb);

#endif /* __DRV_MQTT_H */