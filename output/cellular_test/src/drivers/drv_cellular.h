#ifndef __DRV_CELLULAR_H
#define __DRV_CELLULAR_H

#ifdef TEST
#include "mock_hal.h"
#else
#include "stm32g0xx_hal.h"
#include <stdbool.h>
#endif

#include <stdint.h>

#define CELLULAR_OK      0
#define CELLULAR_ERROR   (-1)
#define CELLULAR_TIMEOUT (-2)

/**
 * @brief   Initialize cellular module, store UART handle and power on
 * @param   huart   Pointer to configured UART handle (ignored in TEST mode)
 */
void cellular_init(UART_HandleTypeDef *huart);

/**
 * @brief   Power on the cellular module by toggling power pin
 * @note    Does nothing if power_pin is not configured
 */
void cellular_power_on(void);

/**
 * @brief   Hardware reset the module, then wait for "+PBREADY" URC
 * @note    Does nothing if reset_pin is not configured
 * @return  CELLULAR_OK on success, CELLULAR_TIMEOUT if no "+PBREADY"
 */
int cellular_reset(void);

/**
 * @brief   Send an AT command and collect response
 * @param   cmd         AT command string (null-terminated, without trailing \r\n)
 * @param   resp        Buffer for response text
 * @param   resp_len    Size of response buffer
 * @param   timeout_ms  Timeout in milliseconds
 * @return  CELLULAR_OK if "OK" found in response,
 *          CELLULAR_ERROR if "ERROR" found,
 *          CELLULAR_TIMEOUT if timeout expired
 */
int cellular_send_at(const char *cmd, char *resp, uint16_t resp_len,
                     uint32_t timeout_ms);

/**
 * @brief   Get IMEI via AT+GSN
 * @param   imei    Output buffer for IMEI string
 * @param   len     Buffer size
 * @return  CELLULAR_OK on success
 */
int cellular_get_imei(char *imei, uint16_t len);

/**
 * @brief   Get CCID via AT+QCCID
 * @param   ccid    Output buffer for CCID string
 * @param   len     Buffer size
 * @return  CELLULAR_OK on success
 */
int cellular_get_ccid(char *ccid, uint16_t len);

/**
 * @brief   Wait for network registration
 * @param   timeout_ms  Maximum time to wait in milliseconds
 * @return  CELLULAR_OK when registered (stat=1 or stat=5),
 *          CELLULAR_TIMEOUT if timeout expired
 */
int cellular_wait_network(uint32_t timeout_ms);

/**
 * @brief   Activate PDP context with given APN
 * @param   apn     APN string (e.g. "CMNET")
 * @return  CELLULAR_OK on success
 */
int cellular_pdp_activate(const char *apn);

/**
 * @brief   Get assigned IP address via AT+CGPADDR=1
 * @param   ip      Output buffer for IP string
 * @param   len     Buffer size
 * @return  CELLULAR_OK on success
 */
int cellular_get_ip(char *ip, uint16_t len);

/**
 * @brief   Create a TCP socket to remote host
 * @param   host    Remote hostname or IP
 * @param   port    Remote port number
 * @return  Socket ID on success, CELLULAR_ERROR on failure
 */
int cellular_create_socket(const char *host, uint16_t port);

/**
 * @brief   Send data over an established socket
 * @param   sock    Socket ID
 * @param   data    Data buffer to send
 * @param   len     Number of bytes to send
 * @return  Number of bytes sent, or CELLULAR_ERROR
 */
int cellular_send(int sock, const uint8_t *data, uint16_t len);

/**
 * @brief   Receive data from a socket
 * @param   sock        Socket ID
 * @param   buf         Receive buffer
 * @param   len         Maximum bytes to receive
 * @param   timeout_ms  Timeout in milliseconds
 * @return  Number of bytes received, or CELLULAR_TIMEOUT
 */
int cellular_recv(int sock, uint8_t *buf, uint16_t len, uint32_t timeout_ms);

/**
 * @brief   Close a socket
 * @param   sock    Socket ID
 * @return  CELLULAR_OK on success
 */
int cellular_close_socket(int sock);

#endif /* __DRV_CELLULAR_H */