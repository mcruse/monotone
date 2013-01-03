/*
 ============================================================================
 Name        : platform_types.h
 Author      : Brad Schoening
 Description : Standard data type definitions
 ============================================================================

 Copyright (c) 2009 by Cisco Systems, Inc.
*/

/**
 * @file
 * Platform-specific data type definitions 
 */
#ifndef PLATFORM_TYPES_H_
#define PLATFORM_TYPES_H_

#include <time.h>

#ifndef _MSC_VER
#include <stdint.h>
#else
	// Use these definitions with Microsoft Visual C++ compilers
   typedef __int8            int8_t;
   typedef __int16           int16_t;
   typedef __int32           int32_t;
   typedef unsigned __int8   uint8_t;
   typedef unsigned __int16  uint16_t;
   typedef unsigned __int32  uint32_t;
#endif

typedef int ios_boolean;
typedef unsigned char boolean;
typedef unsigned char uchar;


#ifdef _WIN32
#include <winsock2.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#define INVALID_SOCKET -1
typedef int SOCKET;
typedef struct sockaddr    SOCKADDR;
typedef struct sockaddr_in SOCKADDR_IN;
#endif

#ifndef _WIN32
#include <rpc/types.h>				// defines TRUE
#endif

#ifdef _WIN32
#define MIN(a,b)	min(a,b)	// WIN32 defines lowercase "min()"
#define MAX(a,b)	max(a,b)	//
#include <windef.h>
#else
#include <sys/param.h>			// MIN/MAX
#endif

#endif /* PLATFORM_TYPES_H_ */
