/*
 ============================================================================
 Name        : QueryTests.h
 Author      : Brad Schoening
 Description : Mgmt API header file
 ============================================================================

 Copyright (c) 2009 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise API query tests header
 */

#ifndef QUERYTESTS_H_
#define QUERYTESTS_H_

/*
 * Test PDU w/query for usage
 */
void
testGetUsageQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);

/*
 * Test PDU w/query for delta vector
 */
void
testGetDeltaQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char* name, char* keywords);

/*
 * Test PDU w/sum query for usage
 */
void
testSumQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);

/*
 * Test PDU w/set query for level
 */
void
testSetQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);

/*
 * Test PDU w/set recurrence
 */

void
testSetRecurrence(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);

/*
 * Test PDU w/query for usage by filtering on ID
 */
void
testGetUsageQueryById(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);

void
testGetRecurrence(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);

void
testDeleteRecurrence(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);

void
testSaveQuery(char* domain, energywise_sender_id_t *id, unsigned char* secret, int secret_len, char* dest, char *name, char *keywords);
#endif /* QUERYTESTS_H_ */
