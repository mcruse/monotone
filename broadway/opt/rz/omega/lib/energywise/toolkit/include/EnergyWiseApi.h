/*
 ============================================================================
 Name        : MgmtApi.h
 Author      : Brad Schoening
 Description : Management API header file
 ============================================================================

 Copyright (c) 2009-2010 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise management API function signatures and descriptions 
 */
#ifndef MGMTAPI_H_
#define MGMTAPI_H_

#include "EnergyWise.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ENW_NETWORK_ERROR	0x100

#define ERRORCODE_TIMEOUT_EXPIRED	10
#define ERRORCODE_INVALID_READ		11
#define ERRORCODE_OUT_OF_MEMORY		12

/* forward declaration of internal structure types */

typedef struct enw_session enw_session_t;
typedef struct enw_resultset enw_resultset_t;
typedef struct enw_query enw_query_t;
typedef struct enw_result_row_t enw_resultrow_t;

/**
 * Create a session which will hold common attributes and initialize network I/O
 * connections.  The initialized results of the function are returned in the 
 * 'session' argument.
 *
 * @param[in] *targetaddr An IP address in dotted quad notation ("x.x.x.x") of 
 * the Cisco EnergyWise device the SDK will establish communications with.
 * 
 * @param[in] targetport The IP port of the target Cisco EnergyWise device to 
 * use for socket communications.If zero, the default of 43440 will be used.
 * 
 * @param[in] *id A 36-byte EnergyWise ID.  Includes a 32-byte representaiton of 
 * a UUID or Cisco UDI and a 4-byte physical index.
 * 
 * @param[in] *key A compiled security key used for authentication that has 
 * been generated using the provided utility function.
 *
 * @param[in] key_len Length of the uchar* key passed in.
 *
 * @return session A handle to the structure holding all information used by
 * the API to create and execute queries.  NULL if an error occured.
 *
 * @pre The EnergyWise management security and port have been configured on the 
 * target switch.
 * 
 * @usage 
 * This function should be used each time you want to create a new 
 * session with the EnergyWise network.  This session handler needs to be 
 * created before any queries can be issued.
 *
 * @codeexample
 * Provided that you have already created a unique UUID and generated the
 * security key, create a new session to the switch at 10.10.10.1:43440, with a 
 * query timeout value of 12 seconds.
 * @code
 * if ((session = energywise_createSession ("10.10.10.1", 43440, uuid, key, 
 *                                          key_length, 12)) {
 *      // Success, begin rest of application code for this session
 * } else {
 *      // Log error on creating session
 * }
 * @endcode
 */
enw_session_t*
energywise_createSession(char* targetaddr, int targetport, 
                         energywise_sender_id_t *id, unsigned char* key, 
                         int key_len); 

/**
 * Close open file descriptors and release session structures.
 *
 * @param[in] *session A handle to the session structure holding all information used by
 * the API to create and execute queries.
 *
 * @return NONE
 * 
 * @pre The session as already been created using energywise_createSession().
 * 
 * @usage 
 * Use this function when the session is over and all session related
 * data can be released.
 *
 * @codeexample
 * To simply announce and close an open session named 'session'.
 * @code
 * printf ("Closing management session.\n");
 * energywise_closeSession (session);
 * @endcode
 */
void
energywise_closeSession(enw_session_t *session);

/**
 * Generic query creation is used by the parameterized query functions. 
 * It is prefered to use the parameterized query creation methods instead.
 
 * Individual queries
 * 		energywise_createSetQuery
 * 		energywise_createCollectQuery
 *
 * Aggregate queries
 * 		energywise_createSumQuery
 *
 * @see energywise_createSetQuery(), energywise_createCollectQuery(), 
 * energywise_createSumQuery()
 */
enw_query_t*
energywise_createQuery(const ew_class_t ew_class, const int action, const char* domain, const uint8_t importance);

/**
 * Parameterized query function to create a new set query.
 *
 * @param[in] *domain The EnergyWise domain name.  This must match the domain 
 * name of the target switch that the API is communicating with.
 *
 * @param[in] importance The device importance level for which the query will 
 * gather results.  Responding entities should be less than or equal to
 * this importance in order to respond.
 *
 * @return A handler for the newly created query structure.
 *
 * @usage 
 * Use this to create a query when you want to set certain attributes
 * on EnergyWise endpoints.
 *
 * @codeexample
 * Create a set query for domain "cisco" to devices of importance 50 or less.
 * @code
 * if ((query = energywise_createSetQuery ("cisco", 50))) {
 *      // Set query created, begin adding qualifiers and set attributes
 * }
 * @endcode
 */
enw_query_t*
energywise_createSetQuery(char* domain, uint8_t importance);

/**
 * Parameterized query function to create a new collect query.
 *
 * @param[in] *domain The EnergyWise domain name.  This must match the domain 
 * name of the target switch that the API is communicating with.
 *
 * @param[in] importance The device importance level for which the query will 
 * gather results.  Responding entities should be less than or equal to
 * this importance in order to respond.
 *
 * @return A handler for the newly created query structure.
 *
 * @usage
 * Use this to create a query when you want to get certain attributes
 * from EnergyWise endpoints.
 *
 * @codeexample
 * Create a collect query for domain "cisco" from devices of importance 50 or 
 * less.
 * @code
 * if ((query = energywise_createCollectQuery ("cisco", 50))) {
 *      // Collect query created, begin adding qualifiers and get attributes
 * }
 * @endcode
 */
enw_query_t*
energywise_createCollectQuery(char* domain, uint8_t importance);

/**
 * Parameterized query function to create a new sum query.
 *
 * @param[in] *domain The EnergyWise domain name.  This must match the domain 
 * name of the target switch that the API is communicating with.
 *
 * @param[in] importance The device importance level for which the query will 
 * gather results.  Responding entities should be less than or equal to
 * this importance in order to respond.
 *
 * @return A handler for the newly created query structure.
 *
 * @usage
 * Use this to create a query when you want to sum the USAGE or
 * DELTA_VECTOR accross EnergyWise endpoints.
 *
 * @codeexample
 * Create a sum query for domain "cisco" from devices of importance 50 or 
 * less.
 * @code
 * if ((query = energywise_createSumQuery ("cisco", 50))) {
 *      // Sum query created, begin adding qualifiers and get attributes
 * }
 * @endcode
 */
enw_query_t*
energywise_createSumQuery(char* domain, uint8_t importance);

/**
 * Add a get attribute to the query.  This is specific to a COLLECT query or
 * a SUM query.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @param[in] type The enum value for which attribute type being specified.
 *
 * @retval 0 Attribute type was added to the query successfully.
 * @retval -1 Specified attribute type could not be added to the query.  This
 * is usually because the attribute type is not compatible with the query type.
 *      
 * @pre The query must already be created.
 *
 * @usage
 * Use this function when you would like to add a certain attribute to
 * a COLLECT or SUM query to return back in the results.
 *
 * @codeexample
 * I would like to retrieve the NAME and ROLE field for all responding 
 * entities in my query.
 * @code
 * // Just created a new collect query
 * if (energywise_addGetAttribute (query, EW_ATTRIBUTE_TYPE_NAME) == 0 &&
 *     energywise_addGetAttribute (query, EW_ATTRIBUTE_TYPE_ROLE) == 0) {
 *     // Proceed with rest of query execution
 * }
 * @endcode
 */
int
energywise_addGetAttribute(enw_query_t *query, const ew_attribute_type_t type);

/**
 * Add a set attribute to the query.  This is specific to a SET query only.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @param[in] type The enum value for which attribute type being specified.
 *
 * @param[in] *valueAddr A pointer to where the data of type type resides that
 * you want to set to.
 * 
 * @retval 0 Attribute type was added to the query successfully.
 * @retval -1 Specified attribute type could not be added to the query.  This
 * is usually because the attribute type is not compatible with the query type.
 *      
 * @pre The query must already be created.
 *
 * @usage
 * Use this function when you would like to set an attribute to a certain
 * value.
 *
 * @codeexample
 * I would like to set any matching entities to power level 5.
 * @code
 * // Create the local data
 * uint8_t level = 5;
 * if (energywise_addSetAttribute (query, EW_ATTRIBUTE_TYPE_LEVEL, &level) == 0) { 
 *     // Proceed with rest of query execution
 * }
 * @endcode
 */
int
energywise_addSetAttribute(enw_query_t *query, const ew_attribute_type_t type, const void *valueAddr);

/**
 * Generic function to add qualifier types to a query.   
 * It is prefered to use the parameterized qualifier methods instead.
 * 
 * Accepted qualifier types
 *      EW_ATTRIBUTE_TYPE_NAME
 *      EW_ATTRIBUTE_TYPE_KEYWORDS
 *      EW_ATTRIBUTE_TYPE_ROLE
 *      EW_ATTRIBUTE_TYPE_ID
 *
 * @see energywise_addNameQualifier(), energywise_addKeyQualifier(),
 * energywise_addRoleQualifier(), energywise_addIdQualifier()
 */
int
energywise_addQualifier(enw_query_t *query, const ew_attribute_type_t type, const void *valueAddr);

/**
 * Add a qualifier to a GET or SET query.  Each device evaluating the query 
 * will match the regular expression 'name' with its device NAME attribute and
 * respond to the query only if there is a match.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @param[in] *name A string containing the qualifier name.
 *
 * @retval 0 Name was successfully added to query.
 * @retval -1 Invalid query class, cannot add qualifier.
 * @retval -2 Invalid query action, cannot add qualifier.
 *
 * @usage
 * Use this when you need to add a name qualifier to the query.  Entities
 * will use this when filtering to determine whether the query is meant for 
 * them.
 *
 * @codeexample
 * To generate a query that filters on all entites matching the name "cisco".
 * @code
 * if (energywise_addNameQualifier (query, "cisco") == 0) {
 *      // Success
 * }
 * @endcode
 */
int
energywise_addNameQualifier(enw_query_t *query, const char* name);

/**
 * Add a qualifier to a GET or SET query.  Each device evaluating the query will 
 * match the regular expression 'key' with its device's KEYWORD attributes and 
 * respond to the query only if there is a match.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @param[in] *keys A string containing one or more keywords to filter on.  
 * Multiple keywords must be comma-separated. 
 *
 * @note If multiple keywords, the entities will filter on them using the logical or operator.
 *
 * @retval 0 Keyword was successfully added to query.
 * @retval -1 Invalid query class, cannot add qualifier.
 * @retval -2 Invalid query action, cannot add qualifier.
 *
 * @usage
 * Use this when you need to add a keyword qualifier to the query.  
 * Entities will use this when filtering to determine whether the query is 
 * meant for them.
 *
 * @codeexample
 * To generate a query that filters on all entites matching the keywords 
 * "cisco" OR "public".
 * @code
 * if (energywise_addKeyQualifier (query, "cisco,public") == 0) {
 *      // Success
 * }
 * @endcode
 */
int
energywise_addKeyQualifier(enw_query_t *query, const char* keys);

/**
 * Add a qualifier to a GET or SET query.  Each device evaluating the query 
 * will match the regular expression 'role' with its device ROLE attribute and
 * respond to the query only if there is a match.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @param[in] *role A string containing the qualifier role.
 *
 * @retval 0 Role was successfully added to query.
 * @retval -1 Invalid query class, cannot add qualifier.
 * @retval -2 Invalid query action, cannot add qualifier.
 *
 * @usage
 * Use this when you need to add a role qualifier to the query.  Entities
 * will use this when filtering to determine whether the query is meant for 
 * them.
 *
 * @codeexample
 * To generate a query that filters on all entites matching the role "laptop".
 * @code
 * if (energywise_addRoleQualifier (query, "laptop") == 0) {
 *      // Success
 * }
 * @endcode
 */
int
energywise_addRoleQualifier(enw_query_t *query, const char* role);

/**
 * Add a qualifier to a GET or SET query.  Each device evaluating the query 
 * will match their EnergyWise ID with this and respond to the query only 
 * if there is a match.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @param[in] *id The ID that is to be added.
 * 
 * @retval 0 The ID was successfully added to query.
 * @retval -1 Invalid query class, cannot add qualifier.
 * @retval -2 Invalid query action, cannot add qualifier.
 *
 * @usage
 * Use this when you need to add an EnergyWise ID as the query
 * qualifier.  Entities will use this when filtering to determine whether
 * the query is meant for them.
 *
 * @note One can add multiple IDs to a query by repeating this function
 * for each ID to be added.  Entites receiving this query will check each
 * ID contained within and respond if their ID is found.  Additionally,
 * adding the ID qualifier to a query automatically negates any other
 * qualifiers that are added (name, role, keywords).
 *
 * @codeexample
 * To generate a query that filters on all entites matching the given ID.
 * @code
 * // Need better example here...
 * if (energywise_addIdQualifier (query, id) == 0) {
 *      // Success
 * }
 * @endcode
 */
int
energywise_addIdQualifier(enw_query_t *query, const energywise_sender_id_t *id);

/**
 * Translate the query into a PDU and propagate it out to the EnergyWise domain.
 *
 * @param[in] *session A handle to the session structure holding all information used by
 * the API to create and execute queries.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @return The return value of this function is positive number indication the
 * number of bytes NOT sent out when the query was executed.  Zero should be
 * expected.
 *
 * @usage
 * Use this function once you have already created a query and attached
 * attributes and qualifiers to it.  This will send it out to the rest of the 
 * EnergyWise network.
 *
 * @codeexample
 * To issue a query which has already been created.
 * @code
 * // Issue the query now, then get the results
 * energywise_execQuery (session, query);
 * @endcode
 */
int
energywise_execQuery(enw_session_t *session, enw_query_t *query);

/**
 * Performs a blocking read for the response PDU and returns a result set
 *
 * @param[in] *session A handle to the session structure holding all information
 * used by the API to create and execute queries.
 *
 * @param[in] *query A handle to the query structure holding the information
 * used by the API.
 *
 * @return A result set structure holding the query results.
 *
 * @usage
 * You must use this function aftering issuing a query with 
 * energywise_execQuery() to grab the results and store them in a result 
 * handler.
 * 
 * @codeexample
 * Need to grab the results to iterate over aftering issuing the query
 * @code
 * // Store the resultset in my_result
 * enw_resultset_t *my_result = energywise_queryResults (session, query);
 * @endcode
 */
enw_resultset_t *
energywise_queryResults(enw_session_t *session, enw_query_t* query);

/**
 * Retrieve the next row in the resultset and return back a row type.
 *
 * @param[in] *resultset A resultset structure holding the query results.
 *
 * @return Returns back a pointer to the next row of type enw_result_row_t*.
 * Null means end of results.
 *
 * @usage
 * Use this when you need to iterate over each row in the resultset..
 *
 * @codeexample
 * To iterate over the name field that we bound to
 * @code
 * int length;
 * char *aName;
 * enw_result_row_t *row;
 * while ((row = energywise_getNextRow (resultset))) {
       aName = energywise_getAttributeFromRowByType(row, EW_ATTRIBUTE_TYPE_NAME, 
                                                    &length);
       printf("Name:  %s\n", aName);
 * }
 * @endcode
 */
struct enw_result_row_t *
energywise_getNextRow(enw_resultset_t *resultset);

/**
 * Given a row from the resultset, retrieve an attribute by type.
 *
 * @param[in] *result_row A structure holding the next row in the resultset.
 *
 * @param[in] attribute An ew_attribute_type_t enum value indicating the desired type.
 *
 * @param[out] *length A pointer to a length variable to indicate the size of the data
 * to be returned.
 *
 * @return This function returns a void pointer to the data requested.  The size of 
 * the data can be determined by the length field parameter that is set by the function.
 * Null indicates that the data could not be found on the given row.
 *
 * @usage
 * Use this function to retrieve the desired data from a given row.  This function only
 * returns a pointer to the data buffer and its length.  The calling function should copy 
 * out the data as necessary, as the buffer and length will no longer be valid after the
 * resultset is gone.
 *
 * @codeexample
 * To iterate over the name field that we bound to
 * @code
 * int length;
 * char *aName;
 * enw_result_row_t *row;
 * while ((row = energywise_getNextRow (resultset))) {
       aName = energywise_getAttributeFromRowByType(row, EW_ATTRIBUTE_TYPE_NAME, 
                                                    &length);
       printf("Name:  %s\n", aName);
 * }
 * @endcode
 */
void *
energywise_getAttributeFromRowByType(struct enw_result_row_t *result_row, 
        ew_attribute_type_t attribute, uint32_t *length);


/**
 * Answer the total number of ACK's received for this query
 *
 * @param[in] resultset A result set structure holding the query results.
 *
 * @return Returns the number of ACK's received
 *
 * @usage
 * Use this to get the number of entities that responded with ACK_WILL
 */
int
energywise_getAckCount(enw_resultset_t* resultset);

/**
 * Answer the total number of NAK's received for this query
 *
 * @param[in] *resultset A result set structure holding the query results.
 *
 * @return Returns the number of NAK's received.
 *
 * @usage
 * Use this to get the number of entities that responded with ACK_WONT (NAK)
 */
int
energywise_getNakCount(enw_resultset_t* resultset);

/**
 * Answer an ordered list of IP addresses (v4) that responded with ACK
 *
 * @param[in] *resultset A result set structure holding the query results.
 *
 * @return This will return an array of 'energywise_sender_id_t' data 
 * where the number of indices is energywise_getAckCount().
 *
 * @usage
 * Use this to get more detailed information about who responded with ACK.
 */
energywise_sender_id_t*
energywise_getAcks(enw_resultset_t* resultset);

/**
 * Answer an ordered list of IP addresses (v4) that responded with NAK
 *
 * @param[in] *resultset A result set structure holding the query results.
 *
 * @return This will return an array of 'energywise_sender_id_t' data 
 * where the number of indices is energywise_getNakCount().
 *
 * @usage
 * Use this to get more detailed information about who responded with NAK.
 */
energywise_sender_id_t*
energywise_getNaks(enw_resultset_t* resultset);

/**
 * Answer the number of rows in the result set
 *
 * @param[in] *resultset A result set structure holding the query results.
 *
 * @return The number of rows in the query results.
 */
int
energywise_getRowCount(enw_resultset_t* resultset);

/**
 * Answer an ordered list of IP addresses (v4) that responded with NAK
 *
 * @param[in] *resultset A result set structure holding the query results.
 *
 * @return Returns an enum value indicating the error code, if any.
 */
int
energywise_getErrorCode(enw_resultset_t* resultset);

/**
 * Release the results held in resultset and free the associated memory.
 *
 * @param[in] *resultset A result set structure holding the query results.
 *
 * @return NONE
 *
 * @usage
 * Use this when completely done with a query and you need to free the 
 * associated memory that has been allocated.  This will only free up
 * the memory taken by internal structures, not any associated with
 * the local program.
 */
void
energywise_releaseResult(enw_resultset_t *resultset);

/**
 * Release the query object used in the query, close the associated socket, 
 * and free the associated memory.
 *
 * @param[in] *query A query structure holding the query info created by
 * energywise_create*Query calls.
 *
 * @return NONE
 *
 * @usage
 * Use this when completely done with a query and you need to free the 
 * associated memory that has been allocated.  This will only free up
 * the memory taken by internal structures, not any associated with
 * the local program.
 */
void
energywise_releaseQuery (enw_query_t *query);

#ifdef __cplusplus
}
#endif

#endif /* MGMTAPI_H_ */
