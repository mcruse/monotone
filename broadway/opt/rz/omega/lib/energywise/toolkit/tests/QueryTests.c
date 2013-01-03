/*
 ============================================================================
 Name        : QueryTests.c
 Author      : Brad Schoening
 Description : Mgmt API query examples
 ============================================================================

 Copyright (c) 2009-2010 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise API query tests source file
 */

#include <stdio.h>				// printf()
#include <math.h>				// pow()
#include <string.h>

#include "EnergyWiseApi.h"
#include "QueryTests.h"


/*
 * Test PDU w/query for usage
 *
 * Equivalent CLI: energywise query imp 100 name * collect usage
 */
void
testGetUsageQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t* resultset;
    enw_resultrow_t *result_row;
    
    char *aName, *aRole, *aDomain, *aDeviceType;
    struct sockaddr_in *aSender;
    uint16_t *aUsage;
    uint8_t *aLevel;
    int8_t *aUnit;
    int i = 0;
    uint8_t to = 6;
    /*
     * create PDU
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL) {
        return;
    }

    query = energywise_createCollectQuery(domain, 100);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_NAME);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_ROLE);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_USAGE);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_UNITS);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_LEVEL);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_DEVICE_TYPE);

    /* Set the query timeout to 6 seconds from the above variable */
    energywise_addQualifier(query, EW_ATTRIBUTE_TYPE_QUERY_TIMEOUT, &to);

    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);
    
    energywise_execQuery(session, query);
    // read results
    if ((resultset = energywise_queryResults(session, query))) {
        
        /*
        int n;
        int count = energywise_getAckCount(resultset);
        energywise_sender_id_t* ids = energywise_getAcks(resultset);
        for (n=0; n < count; n++){
            printf("ACK %3d %s %d\n", n, ids->id, ids->phy_idx);
            ids++;
        }
        count = energywise_getNakCount(resultset);
        ids = energywise_getNaks(resultset);

        for (n=0; n < count; n++){
            printf("NAK %3d %s %d\n", n, ids->id, ids->phy_idx);
            ids++;
        }
        */

        while ((result_row = energywise_getNextRow(resultset))) {
            i++;
            int length;
            aName = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_NAME, &length);
            aRole = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_ROLE, &length);
            aUsage = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_USAGE, &length);
            aLevel = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_LEVEL, &length);
            aUnit = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_UNITS, &length);
            aDomain = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_DOMAIN, &length);
            aSender = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_REPLY_TO, &length);
            aDeviceType = energywise_getAttributeFromRowByType(result_row, 
                    EW_ATTRIBUTE_TYPE_DEVICE_TYPE, &length);
            
            printf("row %d Results: ", i);
            printf("Domain = %s, ", aDomain);
            printf("Name = %s, ", aName);
            printf("Role = %s, ", aRole);
            if (aUsage && aUnit) {
                printf("Usage = %d (%d), ", *aUsage, *aUnit);
            } else {
                printf("Usage = ???, ");
            }
            if (aLevel) {
                printf("Level = %d, ", *aLevel);
            } else {
                printf("Level = ???, ");
            }
            if (aSender) {
                printf("Addr = %s, ", inet_ntoa(aSender->sin_addr));
            } else {
                printf("Addr = ???, ");
            }
            printf("Type = %s\n", aDeviceType);
        }

        energywise_releaseResult(resultset);
    }
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}


/*
 * Test PDU w/query for delta vector
 */
void
testGetDeltaQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char* name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t *resultset;
    enw_resultrow_t *result_row;

    char *aName;
    SOCKADDR_IN *aSender;
    int8_t *aUnit;
    int32_t *aVec;
    int i,j;

    /*
     * create PDU
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL )
        return;

    query = energywise_createCollectQuery(domain, 100);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_DELTA_VECTOR);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_NAME);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_ROLE);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_UNITS);
    
    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);
    // read results
    resultset = energywise_queryResults(session, query);

    i = 0;
    printf("Delta usage (Watts) @ Levels \n");
    printf("Host            Name            0      1      2      3      4      5      6      7      8      9      10\n");
    printf("----            ----            ------------------------------------------------------------------------\n");

    while ((result_row = energywise_getNextRow(resultset))) {
        i++;
        int length;
        double units;
        aUnit = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_UNITS, &length);
        aSender = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_REPLY_TO, &length);
        aName = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_NAME, &length);
        aVec = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_DELTA_VECTOR, &length);
        if (aUnit && aSender && aName && aVec) {
            units = pow(10.0, *aUnit);
            
            printf("%-15s %-15s ", inet_ntoa(aSender->sin_addr), aName);
            for (j = 0; j < ENERGYWISE_MAX_LEVEL; j++) {
                int val = aVec[j];
                printf("%-6.1f ", val * units);
            }
            printf("\n");
        } else {
            printf("Could not get all attributes for row\n");
        }
    }

    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}

/*
 * Test PDU w/sum query for usage
 */
void
testSumQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t *resultset;
    enw_resultrow_t *result_row;

    char *aDomain;
    SOCKADDR_IN *aSender;
    uint16_t *aUsage;
    int8_t *aUnit;
    int i = 0;

    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL ) {
        return;
    }

    query = energywise_createSumQuery(domain, 100);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_USAGE);
    
    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);

    // read results
    resultset = energywise_queryResults(session, query);

    while ((result_row = energywise_getNextRow(resultset))) {
        int length;
        i++;

        aDomain = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_DOMAIN, &length);
        aUsage = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_USAGE, &length);
        aUnit = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_UNITS, &length);
        aSender = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_REPLY_TO, &length);
        if (aDomain && aUsage && aUnit && aSender) {
        printf("row %d Results: Domain = %s, Usage = %d, Units = %d, Addr = %s\n", i, aDomain, *aUsage, *aUnit, inet_ntoa(aSender->sin_addr));
        } else {
            printf("Could not get all attributes from row\n");
        }
    }

    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}

/*
 * Test PDU w/set query for level
 */
void
testSetQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t *resultset;

    int n;

    uint8_t level = 5; 

    /*
     * create PDU with zero bytes
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL) {
        return;
    }

    query = energywise_createSetQuery(domain, 100);
    energywise_addSetAttribute(query, EW_ATTRIBUTE_TYPE_NAME, "name_is_set");
    energywise_addSetAttribute(query, EW_ATTRIBUTE_TYPE_ROLE, "role_is_set");
    energywise_addSetAttribute(query, EW_ATTRIBUTE_TYPE_KEYWORDS, "keywords,are,set");
    energywise_addSetAttribute(query, EW_ATTRIBUTE_TYPE_IMPORTANCE, &level);
    energywise_addSetAttribute(query, EW_ATTRIBUTE_TYPE_LEVEL, &level);

    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);

    // read results
    resultset = energywise_queryResults(session, query);

    int count = energywise_getAckCount(resultset);
    energywise_sender_id_t* ids = energywise_getAcks(resultset);
    for (n=0; n < count; n++){
        printf("ACK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }

    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}

void
testGetRecurrence(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t *resultset;
    energywise_recurrence_t *r;
    energywise_sender_id_t *sender;
    enw_resultrow_t *result_row;
    /*
     * create PDU with zero bytes
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL )
        return;

    query = energywise_createCollectQuery(domain, 100);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_RECURRENCE);

    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);

    // read results
    resultset = energywise_queryResults(session, query);

    int n;
    int count = energywise_getAckCount(resultset);
    energywise_sender_id_t* ids = energywise_getAcks(resultset);
    for (n=0; n < count; n++){
        printf("ACK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }
    count = energywise_getNakCount(resultset);
    ids = energywise_getNaks(resultset);

    for (n=0; n < count; n++){
        printf("NAK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }

    while ((result_row = energywise_getNextRow(resultset))) {
        int length;
        sender = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_ENERGYWISE_ID, &length);
        while ((r = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_RECURRENCE, &length))) {
            if (r && sender) {
                printf("%s %d %d %s %d\n", r->cron, r->level, r->importance, sender->id, sender->phy_idx);
            }
        }
    }
    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}

void
testSetRecurrence(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t *resultset;
    energywise_recurrence_t r = {
        .cron = "0 5 * * *",
        .level = 5,
        .importance = 100,
        .remove = 0 /* set TRUE to delete this recurrence */
    };
    /*
     * create PDU with zero bytes
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL )
        return;

    query = energywise_createSetQuery(domain, 100);

    energywise_addSetAttribute(query, EW_ATTRIBUTE_TYPE_RECURRENCE, &r);

    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);

    // read results
    resultset = energywise_queryResults(session, query);

    int n;
    int count = energywise_getAckCount(resultset);
    energywise_sender_id_t *ids = energywise_getAcks(resultset);
    for (n=0; n < count; n++){
        printf("ACK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }
    count = energywise_getNakCount(resultset);
    ids = energywise_getNaks(resultset);

    for (n=0; n < count; n++){
        printf("NAK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }

    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}

void
testDeleteRecurrence(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t *resultset;
    energywise_recurrence_t r = {
        .cron = "0 5 * * *",
        .level = 5,
        .importance = 100,
        .remove = 1 /* set TRUE to delete this recurrence */
    };
    /*
     * create PDU with zero bytes
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL )
        return;

    query = energywise_createSetQuery(domain, 100);

    energywise_addSetAttribute(query, EW_ATTRIBUTE_TYPE_RECURRENCE, &r);
   
    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);

    // read results
    resultset = energywise_queryResults(session, query);

    int n;
    int count = energywise_getAckCount(resultset);
    energywise_sender_id_t* ids = energywise_getAcks(resultset);
    for (n=0; n < count; n++){
        printf("ACK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }
    count = energywise_getNakCount(resultset);
    ids = energywise_getNaks(resultset);

    for (n=0; n < count; n++){
        printf("NAK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }

    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}


/*
 * This function will collect the ID and other attributes from an
 * interface using the name qualifier "foo".  It will then issue a 
 * subsequent query using the ID it just collected as the only 
 * qualifier.  Proper functionality will show the exact same results
 * from both queries.  The first filtered by name "foo", the second filtered
 * by foo's ID.
 *
 * NOTE:  You need to give one of the switch interfaces or endpoints the name
 * "foo" for this exact sample to work, or alternatively change the name
 * qualifier value in this example.
 */
void
testGetUsageQueryById(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t* resultset;
    enw_resultrow_t *result_row;

    char *aName;
    char *aRole;
    char *aDomain;
    struct sockaddr_in *aSender;
    uint16_t *aUsage;
    uint8_t *aLevel;
    int8_t *aUnit;
    
    int i;
    energywise_sender_id_t localId, *anId;
    int length; 
    /*
     * create PDU
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL) {
        return;
    }

    query = energywise_createCollectQuery(domain, 100);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_NAME);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_ROLE);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_USAGE);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_UNITS);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_LEVEL);
    
    /* First collect the ID for interface based on name and/or kw */
    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);
    // read results
    resultset = energywise_queryResults(session, query);

    i = 0;
    while ((result_row = energywise_getNextRow(resultset))) {
        i++;
        aDomain = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_DOMAIN, &length);
        aName = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_NAME, &length);
        aRole = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_ROLE, &length);
        aUsage = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_USAGE, &length);
        aLevel = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_LEVEL, &length);
        aUnit = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_UNITS, &length);
        aSender = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_REPLY_TO, &length);
        anId = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_ENERGYWISE_ID, &length);
        if (aDomain && aName && aRole && aUsage && aUnit && aLevel && aSender) {
            printf("row %d Results: Domain = %s, Name = %s, Role = %s, Usage = %d (%d), Level = %d, Addr = %s\n", i, aDomain, aName, aRole, *aUsage, *aUnit, *aLevel, inet_ntoa(aSender->sin_addr));
        }
    }
    memcpy (&localId, anId, sizeof (energywise_sender_id_t));
    printf("\nReceived ID from first query.\n");
    printf("Using as filter for query 2.\n");
    printf("-----\n");

    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);

    /* Query 2 code to filter on ID */
    query = energywise_createCollectQuery(domain, 100);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_NAME);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_ROLE);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_USAGE);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_UNITS);
    energywise_addGetAttribute(query, EW_ATTRIBUTE_TYPE_LEVEL);

    /* Use ID stored in z to filter on */
    energywise_addIdQualifier(query, &localId);
    
    energywise_execQuery(session, query);
    // read results
    resultset = energywise_queryResults(session, query);

    i = 0;
    while ((result_row = energywise_getNextRow(resultset))) {
        i++;
        aDomain = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_DOMAIN, &length);
        aName = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_NAME, &length);
        aRole = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_ROLE, &length);
        aUsage = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_USAGE, &length);
        aUnit = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_UNITS, &length);
        aLevel = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_LEVEL, &length);
        aSender = energywise_getAttributeFromRowByType(result_row, 
                EW_ATTRIBUTE_TYPE_REPLY_TO, &length);
        if (aDomain && aName && aRole && aUsage && aUnit && aLevel && aSender) {
            printf("row %d Results: Domain = %s, Name = %s, Role = %s, Usage = %d (%d), Level = %d, Addr = %s\n", i, aDomain, aName, aRole, *aUsage, *aUnit, *aLevel, inet_ntoa(aSender->sin_addr));
        }
    }

    energywise_releaseResult(resultset);
    energywise_releaseQuery(query);
    energywise_closeSession(session);
}

void
testSaveQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char* keywords)
{
    enw_session_t* session;
    enw_query_t* query;
    enw_resultset_t *resultset;
    
    /*
     * create PDU with zero bytes
     */
    if ((session = energywise_createSession(dest, ENERGYWISE_DEFAULT_PORT, id, secret, secret_len)) == NULL )
        return;

    query = energywise_createQuery(EW_CLASS_QUERY, EW_ACTION_QUERY_SAVE, domain, 100);

    /* Parse name and kw qualifiers from command line */
    if (name) 
        energywise_addNameQualifier (query, name);
    if (keywords)
        energywise_addKeyQualifier (query, keywords);

    energywise_execQuery(session, query);

    // read results
    resultset = energywise_queryResults(session, query);

    int n;
    int count = energywise_getAckCount(resultset);
    energywise_sender_id_t* ids = energywise_getAcks(resultset);
    for (n=0; n < count; n++){
        printf("ACK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }
    count = energywise_getNakCount(resultset);
    ids = energywise_getNaks(resultset);

    for (n=0; n < count; n++){
        printf("NAK %3d %s %d\n", n, ids->id, ids->phy_idx);
        ids++;
    }

    energywise_releaseQuery(query);
    energywise_releaseResult(resultset);
    energywise_closeSession(session);
}
