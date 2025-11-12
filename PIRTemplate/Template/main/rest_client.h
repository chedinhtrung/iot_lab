#ifndef _REST_CLIENT_H_
#define _REST_CLIENT_H_

#include "esp_err.h"
#include "esp_http_client.h"
#include "stdbool.h"
#include "cJSON.h"

typedef enum
{
  INT,
  STRING,
  OBJECT,
} cjson_types_t;

/**
 * @brief Initializes the CAPS IoT Platform REST Client
 *
 *
 * @param url URL of the endpoint (either fetch or update)
 */
void rest_client_init(const char *url);

/**
 * @brief It sets a query key and value to interact with the REST API.
 *
 * The keys define the behavior with the REST API. The possible keys are:
 *
 *    - type: defines which settings the API must interact with, either your
 *            User's or Device's Settings. The possible values are:
 *
 *              - global: the API will fetch (or update) your User' Settings
 *              - device: the API will fetch (or update) your Device's Settings
 *
 *    - keys: it defines which keys to seek in your User's or Device's Settings.
 *            This function does not provide any input validation and it will return
 *            only those keys that were found.
 *            This query key is only required when you are fetching. To update an
 *            specific key on your User's or Device's Settings, please use <key>
 *
 *    - deviceId: this query key is required when type has value device. For security,
 *                you cannot access other user's device settings.
 *
 *    - <key>: It defines the key on your User's or Device's Settings to update. This
 *              function does not provide input validation since the API will only interact
 *              with your settings if <key> exists.
 *
 * Before performing the operation, this will be appended to the URL such as <url>?type=<value>[[[&keys=<key1>,...,<keyn>]&deviceId=<deviceId>]&<key>=<val>&...&<key>=<val>]
 *
 * @param name The name of the query key. It can be type, keys, deviceId, or the value for <key>
 * @param value It is the value for the query key. When you want to fetch multiple keys, they should be comma (,) separated
 * @return if the library cannot allocate the memory for your query keys, it will return ESP_FAIL, otherwise ESP_OK.
 */
esp_err_t rest_client_set_key(const char *key, const char *value);

/**
 * @brief It starts the interaction with the REST API.
 *
 * @param http_op_data For now, this value should be NULL
 * @return It returns an error code if there was an error communicating with the REST API, otherwise ESP_OK
 */
esp_err_t rest_client_perform(cJSON *http_op_data);

/**
 * @brief This method defines how it communicates with the RESP API.
 *
 * For the time being, the REST API only supports HTTP GET, which is the default
 * behavior, thus this function is not necessary.
 *
 * @param method One of the supported HTTP Methods.
 */
void rest_client_set_method(esp_http_client_method_t method);

/**
 * @brief Fetches specific keys from the response data.
 *
 * If rest_client_perform was successful, you can use this function to retrieve your data from the
 * response buffer. Successive calls to rest_client_perform will override the response buffer thus,
 * make sure you have retrived all the information before interacting with the API again.
 *
 * If is_json is false, it will return a copy of the response buffer.
 *
 * If you specify STRING as value_type, it will return a malloc-ed buffer of type char* casted to void*
 *
 * If you specify INT as value_type, it will return a malloc-ed buffer of type int* with length 1 casted to void*
 *
 * If you specify OBJECT as value_type, it will return the cJSON object of type cJSON* of size CJSON casted to void*
 *
 * @param[in] key A key in the response buffer.
 * @param[in] value_type The type to return of the key in the response buffer
 * @param[in] is_json Indicating if the response buffer should be treated as a JSON object.
 * @param[out] ret Error value if there was an error processing the response buffer.
 * @return If there is an error, this function will return NULL otherwise a pointer to your data.
 */
void *rest_client_fetch_key(const char *key, cjson_types_t value_type, bool is_json, esp_err_t *ret);

/**
 * @brief Sets user token for addition to the HTTP Header required to communicate with the REST API.
 *
 * The token must be extracted from your device key.
 *
 * @param token a string representing the device token.
 */
void rest_client_set_user_token(char *token);

#endif
