/*
 ============================================================================
 Name        : Util.h
 Author      : Brad Schoening
 Description : Utility functions for EnergyWise Toolkit
 ============================================================================

 Copyright (c) 2009 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise utility functions and information 
 */
#ifndef UTIL_H_
#define UTIL_H_

#ifdef __cplusplus
extern "C" {
#endif

#define SHA_DIGEST_LENGTH	20

/**
 * Computes a HMAC-SHA digest (20 chars) with the secret and id
 * arguments.  The key argument provides the output storage for
 * the digest.
 *
 * @param[in] *secret The secret to compute the HMAC digest over.
 *
 * @param[in] secret_len The length of the provided secret in bytes.
 *
 * @param[in] *id The EnergyWise id of the locally running service.
 *
 * @param[out] *key A 20 byte buffer to store the resulting digest in.
 *
 * @param[in] key_len The length of the key buffer provided.
 *
 * @return This will return 0 if an insufficient buffer was provided, otherwise
 * returns the key length.
 *
 * @usage
 * Use this to generate a HMAC SHA-1 key over a secret and id.
 *
 * @codeexample
 * @code
 * unsigned char key[SHA_DIGEST_LENGTH];
 * energywise_svc_composeKey(aSecret, secret_len, id, key, key_len);
 * @endcode
 */
int
energywise_utl_composeKey(const unsigned char* secret, int secret_len, const energywise_sender_id_t *id, unsigned char* key, int key_len);

/**
 * Create a 32-character SenderId that will uniquely identify this device.
 * A UUID is instantiated using an operating system call.  Then, a 32-character
 * hex representation of the 16-byte UUID is created in the arg 'uuidString'.
 *
 * @param[out] *id This is where the 36-byte EnergyWise ID will be stored (UUID + physical index).
 *
 * @usage
 * Use this to create a randomized UUID for this device.  It is preferred that
 * you use the mac addres version of this function instead.
 */
int
energywise_utl_createUuid(energywise_sender_id_t *id);

/**
 * Create a 32-character SenderId that will uniquely identify this device.
 * The UUID is created using the specified mac address.  Then, a 32-character
 * hex representation of the 16-byte UUID is created in the arg 'uuidString'.
 *
 * @param[out] *id This is where the 36-byte EnergyWise ID will be stored (UUID + physical index).
 * 
 * @param[in] *mac The Media Access Control (MAC) address of the host.  The 
 * MAC address is used to create a Unique UUID for this Cisco EnergyWise host.
 * 
 * @usage
 * Use this to create a UUID for this device based on your MAC address.  It is 
 * preferred that you use this over the randomized version.
 */
int
energywise_utl_createUuidFromMac(energywise_sender_id_t *id,
                                 const DOT11_MAC_ADDRESS *mac);

/**
 * Get the current version of this toolkit.
 *
 * @return This will return a string in the form of "X.Y.Z" indicating the
 * version number.
 */
char *
energywise_utl_getVersion();
    
#define PRODUCT_ID_LEN      18
#define VERSION_LEN          3
#define SERIALNO_LEN         5
#define IEEEBYTES            6

/**
 * Create a 32-character SenderId that will uniquely identify this device.
 * The UUID is created using the specified mac address.  Then, a 32-character
 * hex representation of the 16-byte UUID is created in the arg 'uuidString'.
 *
 * @param[out] *id This is where the 36-byte EnergyWise ID will be stored (UUID + physical index).
 * 
 * @param[in] product_id The product identifier will max PRODUCT_ID_LEN length.
 * 
 * @param[in] version The version identifier of VERSION_LEN length.
 * 
 * @param[in] serial_no The serial number of SERIALNO_LEN length.
 * 
 * @param[in] mac The Media Access Control (MAC) address of the host.  The 
 * MAC address is used to create a Unique UUID for this Cisco EnergyWise host.
 * 
 * @usage
 * Use this to create a UUID for this device based on your MAC address.  It is 
 * preferred that you use this over the randomized version.
 */
int
energywise_utl_createUuidFromDetails (energywise_sender_id_t *id, 
            unsigned char product_id[PRODUCT_ID_LEN],
            unsigned char version[VERSION_LEN],
            unsigned char serial_no[SERIALNO_LEN],
            unsigned char mac[IEEEBYTES]);

#ifdef __cplusplus
}
#endif

#endif /* UTIL_H_ */
