/*
 ============================================================================
 Name        : MgmtApiTest.c
 Author      : Brad Schoening
 Description : Main test harness for Management API
 ============================================================================

 Copyright (c) 2009-2010 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise API query tests command line wrapper functions 
 */

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>				// exit(), abort()
#include <string.h>				// strlen()
#include <platform_types.h>			// FALSE/TRUE
#include <EnergyWiseApi.h>

#ifndef _MSC_VER
#include <getopt.h>
#else
// Stub out POSIX getopt().  VisualStudio users should hard code their
// arguments or build their own own command line parsing.
#define getopt(a,b,c)	-1
#define optarg			""
#endif

#include "EnergyWiseLog.h"
#include "QueryTests.h"
#include "EnergyWiseUtil.h"

#ifdef INTERNAL_TESTS
void runInternalTests();
#endif


void
ewlog_cb (log_levels_t level, char* msg)
{
    printf("[%d]:%s\n", level, msg);
}

int
main(int argc, char* argv[]) {
	char c;
	int errflag = 0, entry = 0;
	char* domain = "cisco";
	unsigned char* secret = (unsigned char*) "cisco";
	char* name = NULL;
	char* keywords = NULL;
	char* host = NULL;
	int consoleMode = FALSE;
        char *sdkVersion;
	log_levels_t level = LOGLEVEL_INFO;
        boolean run = TRUE;

	while ((c = getopt (argc, argv, "cd:h:k:l:n:s:")) != -1)
	         switch (c)
	           {
	           case 'c':
	             consoleMode = TRUE;
	             break;
	           case 'd':
	             domain = optarg;
	             break;
	           case 'n':
	             name = optarg;
	             break;
	           case 'k':
	             keywords = optarg;
	             break;
	           case 'h':
	             host = optarg;
	             break;
	           case 'l':
			 level = atoi(optarg);
	        	 break; 
	           case 's':
	             secret = (unsigned char*) optarg;
	             break;
	           case '?':
	        	 errflag++;
	             break;
	           default:
	             abort();
	}

    if ((errflag) || (host == NULL)) {
    	fprintf(stderr, "usage: -h host -d domain -s secret -l log_level -n name -k keywords -c\n");
    	exit(2);
    }

	if (!consoleMode) {
		FILE* logfd = fopen("MgmtApiTest.log", "w");
		if (logfd == NULL) {
			printf("error opening log file (errno %d)\n", errno);
		} else {
			setLogFile(logfd);
		}
	}

	setLogLevel(level);
        //enableLogCallback(TRUE);
        //setLogCallback(&ewlog_cb);
        printf("Welcome to Management API Unit Tests.\n");

	// create UUID

        printf("Creating unique ID.\n");
	energywise_sender_id_t sid;
        memset(&sid, 0, sizeof (energywise_sender_id_t));
	energywise_utl_createUuid(&sid);

	// create composite key using secret + uuid
	unsigned char digest[SHA_DIGEST_LENGTH] = { 0 };
	energywise_utl_composeKey(secret, strlen((char*) secret), &sid, digest, SHA_DIGEST_LENGTH);

#ifdef INTERNAL_TESTS
	runInternalTests();
#endif
        sdkVersion = energywise_utl_getVersion();
        printf("EnergyWise API version:  %s\n", sdkVersion);
        printf("EnergyWise parameters:\n");
        printf("\tHost: %s\n\tDomain: %s\n\tSecret: %cXXX\n\tName qualifier: %s\n\tKeyword(s) qualifier: %s\n", host, domain, secret[0], name, keywords);

        while (run) {
            printf("\nPlease enter the API query test example you would like to run:\n");
            printf("\t1) Collect usage - Collect usage as well as other attributes about entities.\n"
                   "\t2) Collect usage by ID - Collect usage based on name/keyword qualifier from entity.\n"
                   "\t                         Then, store the ID from one result row and use as a qualifier\n"
                   "\t                         for another query to verify ID filter is working properly.\n"
                   "\t3) Sum usage - Sum usage accross entities.\n"
                   "\t4) Collect delta vector - Collect delta vectors from entities.\n"
                   "\t5) Set query - Set name, role, keywords, importance, and level.\n"
                   "\t6) Save query - Save query to persist running-config of the switches.\n"
                   "\t7) Set recurrence - Set a recurrence.\n"
                   "\t8) Collect recurrences - Collect recurrences based on name/keyword qualifiers.\n"
                   "\t9) Delete recurrences - Delete the previously set recurrence.\n"
                   "\t10) Quit\n");
            
            printf("\nEntry:  ");
            scanf ("%d", &entry);
            
            switch (entry) {
                
            case 1:         
                printf("\nRunning testGetUsageQuery()...\n");
                testGetUsageQuery(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 2:
                printf("\nRunning testGetUsageQueryById()...\n");
                testGetUsageQueryById(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 3:
                printf("\nRunning testSumQuery()...\n");
                testSumQuery(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 4:
                printf("\nRunning testGetDeltaQuery()...\n");
                testGetDeltaQuery(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 5:
                printf("\nRunning testSetQuery()...\n");
	        testSetQuery(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 6:
                printf("\nRunning testSaveQuery()...\n");
	        testSaveQuery(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 7:
                printf("\nRunning testSetRecurrence()...\n");
                testSetRecurrence(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 8:
                printf("\nRunning testGetRecurrence()...\n");
                testGetRecurrence(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 9:
                printf("\nRunning testDeleteRecurrence()...\n");
                testDeleteRecurrence(domain, &sid, digest, SHA_DIGEST_LENGTH, host, name, keywords);
                break;
            case 10: 
                printf("Exiting...\n");
                run = FALSE;
                break;
            default:
                printf("Invalid option %d, please try again.\n", entry);
                break;
            }
        }
                

	return(EXIT_SUCCESS);

}

