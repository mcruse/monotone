/*
 ============================================================================
 Name        : RefAgent.c
 Author      : Brad Schoening
 Description : Example SDK Reference Client
 ============================================================================

 Copyright (c) 2009-2010 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise SDK reference client source file
 */

#include <string.h>	
#include <errno.h>
#ifndef _MSC_VER
#include <getopt.h>
#else
// stub out getopt functionallity
#define getopt(a,b,c)	-1
#define optarg			""
#endif

#include "../include/EnergyWiseLog.h"
#include "../include/EnergyWiseSdk.h"
#include "../include/EnergyWiseUtil.h"

/********************** STORAGE *************************/

static uint8_t my_energywise_level = 10;

/*
 * The University of Waterloo published the following statistics for a
 * a Pentium 4, 1.7GHz machine w/out monitor:
 *   - during boot power in watts is close to 110w
 *   - during idle, no power management, close to 60w
 *   - during full power saving, no hard disk spin, machine in sleep mode, 35w
 *
 * We'll use these statistics to populate our usage and delta vector for level 8.
 */

static uint16_t usageVec[ENERGYWISE_MAX_LEVEL] = { 0, 35, 35, 60, 60, 120, 120, 120, 120, 120, 120 };

/********************** CALLBACKS *************************/

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to retrieve the platform's unit field that is associated with the current
 * power usage value.  This example always returns back the SI unit of Watts,
 * which has an exponent of 0.
 */
int8_t
proto_get_units()
{
	return ENERGYWISE_UNIT_WATTS;
}

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to retrieve the platform's current power usage.  This example will always
 * return back 120 Watts.
 */
uint16_t
proto_get_usage()
{
	return usageVec[my_energywise_level];
}

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to retrieve the caliber associated with the platform's current power usage. 
 * This should return back an ENUM of type energywise_usage_caliber_t to provide
 * context on how accurate the power measurement currently is.
 *
 * @see energywise_usage_caliber_t
 */
int
proto_get_usageCaliber()
{
	return ENERGYWISE_USAGE_CALIBER_PRESUMED;
}

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to retrieve the platform's current power level.  This example is returning
 * back whatever the current 'my_energywise_level' is.  This field is set 
 * whenever a new SET_LEVEL query is received for this client.
 */
uint8_t
proto_get_level()
{
	return my_energywise_level;
}

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to set the power level of the running system.  This is a soft example that
 * will always set the desired level, except level 0.  Returning -1 from this
 * callback indicates that the client is not going to perform the level change.
 * Returning 0 or greater indicates that the client succeeded in changing
 * to the new level.
 */
int proto_set_level(uint8_t level)
{
	if (level >= ENERGYWISE_MAX_LEVEL) {
                printf("ERROR: invalid level %d\n", level);
                return -1;
        }

	if (level == 0) {
                printf("WARN: can't set level %d\n", level);
		return -1;
	}

	my_energywise_level = level;
	return level;
}

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to retrieve the platform's usage vector and copy it into the vector
 * address provided.  This example is simply copying in the hard-coded
 * usage vector defined at the beginning of the file.
 */
int
proto_fill_usage_vector(uint16_t* aVector)
{
	memcpy(aVector, usageVec, ENERGYWISE_MAX_LEVEL*sizeof(int16_t));
	return 0;
}

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to retrieve the platform's delta vector and copy it into the vector
 * address provided.  This example is simply copying in the hard-coded
 * delta vector defined at the beginning of the file.
 */
int
proto_fill_delta_vector(int* aVector)
{
    int32_t deltaVec[ENERGYWISE_MAX_LEVEL];
    int i = 0;
    for (i = 0; i < ENERGYWISE_MAX_LEVEL; i++) {
        deltaVec[i] = usageVec[i] - usageVec[my_energywise_level];
    }
    memcpy(aVector, deltaVec, ENERGYWISE_MAX_LEVEL*sizeof(int32_t));
    return 0;
}

/**
 * This callback function will be used in the service registry.  Its purpose is
 * to retrieve the next event sequence id.  This example is starting at 0 and 
 * just incrementing each time.  It is highly recommended that you persist
 * the current value so that it can be preserved whenever the client needs
 * to restart.  
 */
int
proto_next_seqid()
{
	static int id = 0;
	return ++id;
}

/**
 * This callback function is used to notify the user of a newly modified
 * attribute.  This callback will be generated whenever a set query
 * has modified some attribute on the client.  This is provided in case
 * any further action needs to be done, like persisting the new value,
 * for example.
 */
void
proto_attribute_changed(ew_attribute_type_t type)
{
    printf("Client notified of modified attribute:  %d\n", type);
}
   
void
ewlog_cb (log_levels_t level, char* msg)
{
    printf("%s\n", msg);
}

void
ew_notify_port (unsigned short port)
{
    printf("Client has opened TCP port %d\n", port);
}

/********************** SDK SETUP *************************/
/**
 * This function contains the example sequence of steps to initialize
 * and startup the EnergyWise SDK service.  It is called by the
 * example main program and passes in the requried arguments to
 * startup the service.
 *
 * @param[in] domain The domain name for the EnergyWise network.
 * @param[in] secret The EnergyWise secret for the client to run on.
 * @param[in] secret_len Length of the secret.
 * @param[in] localhost A character representaion of the localhost's IP 
 * address in the form of "###.###.###.###".
 *
 * @retval 0 Service was started and stopped with no error.
 * @retval -2 Service did not start up successfully.
 *
 * @note
 * This is an example of how to initialize and start the SDK service.  It
 * is only provided to show the basic steps on how to get up and running.
 *
 * @usage
 * This function starts by defining a hard-coded MAC address to generate a
 * unique UUID for the client.  It then defines a service registry, and some
 * basic keywords and role.  The UUID is created using the MAC address from
 * the provided utility function, energywise_utl_createUuidFromMac.  Using
 * the secret and UUID, a device-specific key is generated that will be 
 * passed into the service create function.  The service is then created
 * and returned back with a session handler to manage the service.
 *
 * Once the session is created, the identity attributes are then 
 * configured to the desired values.  Lastly, then registry's function
 * pointers are initialized to point to the local functions that we
 * have written above.  Once these are set, the configure registry 
 * function is called to set the values and then the service can be
 * started.
 *
 * The energywise_svc_startup() a blocking function and will only return
 * if there is an error or if another thread has requested that the 
 * service be shutdown.
 */
int
startDiscovery(char* domain, unsigned char* secret, int secret_len, char* localhost)
{
	enw_svc_session_t* session;
	energywise_sender_id_t sid;
        memset(&sid, 0, sizeof (energywise_sender_id_t));

	/* A persistent MAC address can be initialized as follows
	 *
	 * 	DOT11_MAC_ADDRESS macAddress[6] = { 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F };
	 */
	char name[ENERGYWISE_STR_LEN];
	energywise_svc_registry_t registry;

	char* role = "EndPoint";
	char* keywords = "endpoint,host,laptop";

	energywise_utl_createUuid(&sid);
	/* Would call this to generate UUID from Mac */
	/* energywise_utl_createUuidFromMac(&sid, macAddress); */
        printf("DEBUG: UUID %s\n", sid.id);

	// compose key using secret + uuid
	unsigned char key[SHA_DIGEST_LENGTH];
        unsigned char *sec = secret;
        int sec_len = 0;
        if (secret_len) {
            energywise_utl_composeKey(secret, secret_len, &sid, key,
                    sizeof (key));
            sec = key;
            sec_len = SHA_DIGEST_LENGTH;
        }

	/*
	 * For the reference client, we'll pass a NULL MAC address and initialize
	 * the sequence number to zero (proto_next_seqid).  An complete
	 * implementation of the SDK must provide a persistent MAC address and
	 * sequence number.
	 */
	if ((session = energywise_svc_create(localhost, ENERGYWISE_DEFAULT_PORT, &sid, sec, sec_len, 0)) == NULL) {
                printf("ERROR: failed to create service\n");
		return -1;
	}

	gethostname(name, ENERGYWISE_STR_LEN);
        printf("DEBUG: hostname : %s\n", name);

	energywise_svc_configIdentity(session, domain, name, role, keywords, "TestPC", 5);

	// begin configure callbacks

        registry.fn_get_units = &proto_get_units;
        registry.fn_get_usage = &proto_get_usage;
        registry.fn_get_usageCaliber = &proto_get_usageCaliber;
        registry.fn_get_level = &proto_get_level;

	registry.fn_set_level = &proto_set_level;
 	registry.fn_fill_usageVector = &proto_fill_usage_vector;
	registry.fn_fill_deltaVector = &proto_fill_delta_vector;

	registry.energywise_next_seqid = &proto_next_seqid;
        registry.energywise_modified_attribute = &proto_attribute_changed;
        registry.energywise_listen_port = &ew_notify_port;
	energywise_svc_configRegistry(session, &registry);
	// end configure callbacks
       
        /* Example of how to setup logging callback */
        //enableLogCallback(TRUE);
        //setLogCallback(&ewlog_cb);
	if (energywise_svc_startup(session) < 0) {
                printf("ERROR: failed to startup service\n");
		return -2;
	}
	return 0;
}

/**
 * This is the reference client's main function.  It simply takes in a
 * list of paramaters from the command line and passes them into the
 * 'startDiscovery' function.  The purpose of this is to allow the
 * reference client to be manipulated quickly from the command line.
 */
int
main(int argc, char* argv[]) {
	char c;
	int errflag = 0;
	char* domain = "cisco";
	char* secret = "";
	char* localhost = NULL;
	boolean consoleMode = FALSE;
	FILE* logfd = NULL;

	while ((c = getopt (argc, argv, "cd:l:s:")) != -1)
	         switch (c)
	           {
	           case 'c':
	             consoleMode = TRUE;
	             break;
	           case 'd':
	             domain = optarg;
	             break;
	           case 'l':
	             localhost = optarg;
	             break;
	           case 's':
	             secret = optarg;
	             break;
	           case '?':
	        	 errflag++;
	             break;
	           default:
	             abort ();
	}

    if ((errflag) || (localhost == NULL)) {
    	fprintf(stderr, "usage: -l localhost -d domain -s secret -c\n");
    	exit(2);
    }

	if (!consoleMode) {
		logfd = fopen("RefAgent.log", "w");
		if (logfd == NULL) {
			printf("error opening log file (errno %d)\n", errno);
		} else {
			setLogFile(logfd);
		}
	}

	setLogLevel(LOGLEVEL_DEBUG);
        printf("INFO: startup %s\n", argv[0]);

        printf("INFO: starting agent (localhost: %s domain: %s secret: %cXXX)\n", localhost, domain, secret[0]);


	startDiscovery(domain, (unsigned char*) secret, strlen(secret), localhost);

	if (logfd != NULL) {
		fclose(logfd);
	}
	return(EXIT_SUCCESS);
}

