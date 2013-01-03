/*
 ============================================================================
 Name        : EnergyWise.h
 Author      : Brock Miller
 Description : EnergyWise protocol constants & type definitions
 ============================================================================

 Copyright (c) 2009-2010 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise constant defintions and data types
 */
#ifndef ENERGYWISE_H_
#define ENERGYWISE_H_

#include "platform_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*** ENERGYWISE CONSTANT DEFINITIONS ***/
#define ENERGYWISE_DEFAULT_PORT	43440			// IANA registered

#define ENERGYWISE_ID_SIZE_V1 32
#define ENERGYWISE_ID_SIZE ENERGYWISE_ID_SIZE_V1
#define ENERGYWISE_ID_LEN ENERGYWISE_ID_SIZE
#define ENERGYWISE_MAX_LEVEL 	11

#define ENERGYWISE_STR_LEN_V1  128
#define ENERGYWISE_STR_LEN     ENERGYWISE_STR_LEN_V1
#define ENERGYWISE_UNIT_WATTS   0
#define ENERGYWISE_UNIT_MWATTS -3

#define ENERGYWISE_QUERY_TIMEOUT_DEFAULT 6 
#define ENERGYWISE_QUERY_TIMEOUT_MAX     180 
#define ENERGYWISE_QUERY_TIMEOUT_MIN     1 
#define ENERGYWISE_IMPORTANCE_DEFAULT 1	
#define ENERGYWISE_LEVEL_DEFAULT 10			

#define PN_CHR_PER_LINE 0x10
#define ENERGYWISE_PROTOCOL_VERSION 0x01

typedef unsigned char DOT11_MAC_ADDRESS;

/*** ENERGYWISE TYPE DEFINITIONS ***/
typedef unsigned char energywise_id_v1_t[ENERGYWISE_ID_SIZE];
typedef energywise_id_v1_t energywise_id_t;

struct energywise_sender_id_t_ {
    energywise_id_t       id;
    uint32_t              phy_idx;
};
typedef struct energywise_sender_id_t_ energywise_sender_id_t;

typedef int32_t energywise_delta_vector_t[11];
typedef uint16_t energywise_usage_vector_t[11];

typedef enum energywise_usage_caliber_t_ {
    ENERGYWISE_USAGE_CALIBER_MAX = -2,
    ENERGYWISE_USAGE_CALIBER_PRESUMED = -1,
    ENERGYWISE_USAGE_CALIBER_UNKNOWN = 0,
    ENERGYWISE_USAGE_CALIBER_ACTUAL = 1,
    ENERGYWISE_USAGE_CALIBER_TRUSTED = 2
} energywise_usage_caliber_t;

typedef struct energywise_recurrence_t_ {
    char                               *cron;
    uint8_t                             level;
    uint8_t                             importance;
    ios_boolean                         remove;
} energywise_recurrence_t;

/**
 * EnergyWise enumeration declaring public attribute types.
 * These are for use with adding SET/GET attributes to a 
 * query, as well as binding to the results.  Some can also
 * be used for adding query qualifiers.  Next to each attribute is
 * a brief description indicating its type, size, whether it is 
 * gettable or settable, and if it can be used as a query qualifier.\n\n
 * G:  Gettable\n
 * S:  Settable\n
 */
typedef enum ew_attribute_type_t_ {
    /** Type:  energywise_sender_id_t \n
     *  Size:  36 bytes \n
     *  Use:  This attribute comes back with each query response and can be 
     *        retrieved from each row.  It always comes back and does not need 
     *        to be added as a GET attribute.  Can not be set via query. \n
     *  Qualifier:  Yes \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_ENERGYWISE_ID = 1,
    /** Type:  string \n
     *  Size:  variable length \n
     *  Use:  G,S \n
     *  Qualifier:  Y \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_ROLE = 2,
    /** Type:  string \n
     *  Size:  variable length \n
     *  Use:  Similar to ID, this attribute comes back with each query 
     *        response and does not need to be added as a GET attribute.
     *        It cannot be set. \n
     *  Qualifier:  N \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_DOMAIN = 3,
    /** Type:  string \n
     *  Size:  variable length \n
     *  Use:  G,S \n
     *  Qualifier:  Y \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_NAME = 4,
    /** Type:  string \n
     *  Size:  variable length \n
     *  Use:  G,S \n
     *  Qualifier:  Y \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_KEYWORDS = 5,
    /** Type:  string \n
     *  Size:  variable length \n
     *  Use:  Comes back in query response if error exists.  Can be bound to. \n 
     *  Qualifier:  N \n
     *  Status:  Not working \n
     */
    EW_ATTRIBUTE_TYPE_ERROR_STRING = 6,
    /** Type:  int8_t \n
     *  Size:  1 byte \n
     *  Use:  G \n
     *  Qualifier:  N \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_UNITS = 7,
    /** Type:  uint16_t \n
     *  Size:  2 bytes \n
     *  Use:  G \n
     *  Qualifier:  N \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_USAGE = 8,
    /** Type:  uint8_t \n
     *  Size:  1 byte \n
     *  Use:  G,S \n
     *  Qualifier:  N \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_LEVEL = 9,
    /** Type:  uint8_t \n
     *  Size:  1 byte \n
     *  Use:  G,S \n
     *  Qualifier:  Y, passed in as part of createQuery \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_IMPORTANCE = 10,
    /** Type:  enum, currently not exposed \n
     *  Size:  4 bytes \n
     *  Use:  G \n
     *  Qualifier:  N \n
     *  Status:  Not working \n
     */
    EW_ATTRIBUTE_TYPE_ENTITY_TYPE = 11,
    /** Type:  struct sockaddr \n
     *  Size:  variable length, depends on type \n
     *  Use:  This is similar to ID and domain and will always come back 
     *        in query results.  Can be bound to using bind.  Not settable. \n
     *  Qualifier:  N \n
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_REPLY_TO = 12,
    /** Type:  struct, currently not exposed \n
     *  Size:  variable length \n
     *  Use:  G \n
     *  Qualifier: N \n 
     *  Status:  Not working \n
     */
    EW_ATTRIBUTE_TYPE_NEIGHBOR = 13,
    /** Type:  uint16_t \n
     *  Size:  2 bytes \n
     *  Use:  G \n
     *  Qualifier:  N \n
     *  Status:  Not working \n
     */
    EW_ATTRIBUTE_TYPE_NEIGHBOR_COUNT = 14,
    /** Type:  uint32_t \n
     *  Size:  4 bytes \n
     *  Use:  Currently not externally exposed \n
     *  Qualifier:  N \n 
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_NANNY_VECTOR = 15,
    /** Type:  int32_t[11] \n
     *  Size:  44 bytes \n
     *  Use:  G \n
     *  Qualifier:  N \n 
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_DELTA_VECTOR = 16,
    /** Type:  energywise_usage_caliber_t \n
     *  Size:  4 bytes \n
     *  Use:  G \n
     *  Qualifier:  N \n 
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_USAGE_CALIBER = 17,
    /** Type:  uint16_t[11] \n
     *  Size:  22 bytes \n
     *  Use:  G \n
     *  Qualifier:  N \n 
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_USAGE_VECTOR = 18,
    /** Type:  uint8_t \n
     *  Size:  1 byte \n
     *  Use:  Can be used as a qualifier to set the timeout value on a query. \n
     *  Qualifier:  Y \n 
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_QUERY_TIMEOUT = 19,
    /** Type:  energywise_recurrence_t \n
     *  Size:  variable length \n
     *  Use:  G,S \n
     *  Qualifier:  N \n 
     *  Status:  Working \n
     */
    EW_ATTRIBUTE_TYPE_RECURRENCE = 20,
    /** Type:  string \n
     *  Size:  variable length \n
     *  Use:  G \n
     *  Qualifier:  N \n 
     *  Status:  Working \n 
     */
    EW_ATTRIBUTE_TYPE_DEVICE_TYPE = 21
} ew_attribute_type_t;

typedef enum ew_class_t_ {
    EW_CLASS_QUERY = 1,
    EW_CLASS_AGGREGATE = 2
} ew_class_t;

typedef enum ew_action_query_t_ {
    EW_ACTION_QUERY_SET = 1,
    EW_ACTION_QUERY_COLLECT = 2,
    EW_ACTION_QUERY_SAVE = 3
} ew_action_query_t;

typedef enum ew_action_aggregate_t {
    EW_ACTION_AGGREGATE_SUM = 1
} ew_action_aggregate_t;
#ifdef __cplusplus
}
#endif

#endif /* ENERGYWISE_H_ */
