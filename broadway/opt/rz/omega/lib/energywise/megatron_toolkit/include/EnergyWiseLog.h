/*
 ============================================================================
 Name        : Log.h
 Author      : Brad Schoening
 Description : Macro definitions for logging
 ============================================================================

 Copyright (c) 2009 by Cisco Systems, Inc.
*/

/**
 * @file
 * EnergyWise log functions and information 
 */
#ifndef LOG_H_
#define LOG_H_

#include <stdio.h>
#include <time.h>
#include "EnergyWise.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
	LOGLEVEL_TRACE,
	LOGLEVEL_DEBUG,
	LOGLEVEL_INFO,
	LOGLEVEL_WARN,
	LOGLEVEL_ERROR,
	LOGLEVEL_FATAL
} log_levels_t;


/**
 * Sets the message level to INFO, DEBUG or TRACE.  The initial level is INFO.
 * 
 * @param[in] severity A log_levels_t enum value indicating the log level desired.
 * 
 * @return NONE
 * 
 * @usage Use this anytime in the application when the log level needs to be changed.
 *
 * @codeexample
 * For example, conditionally turn on debug based on some command line arg to the
 * application.
 * @code
 * // debug = TRUE if user passed the -debug option on command line
 * if (debug == TRUE) {
 *      setLogLevel (LOGLEVEL_DEBUG);
 * }
 * @endcode  
 */
void
setLogLevel(log_levels_t severity);

/**
 * Indicates the file descriptor that you want to write log messages to.
 *
 * @param[in] *fd File descriptor for writing to.
 *
 * @return NONE
 *
 * @usage Use this when you'd like to write the log messages to a file instead
 * just printing to stdout.
 *
 * @codeexample
 * Set the logfile to myfile.log.
 * @code
 * FILE* log_fd = fopen("myfile.log", "w");
 * setLogFile(log_fd);
 * @endcode
 */
void
setLogFile(FILE *fd);

/**
 * Specify whether logging should be sent to a user-defined callback function. 
 *
 * @param[in] enable Boolean value to indicate whether to enable or disable
 * the feature.  Logging callback is disabled by default.  Set TRUE to enable.
 *
 * @return NONE
 *
 * @usage Use this if you'd rather have all logging messages redirected to
 * a user-specified callback function.  If enabled, default internal logging
 * will be ignored, even if a log file has been set.  Enabling this feature
 * requires a complimentary call to setLogCallback to specify the user-defined
 * funtion.
 */
void
enableLogCallback(boolean enable);

/**
 * Specify the user-defined function for logging to call if logging callback is
 * enabled.
 * 
 * @param[in] (*cb)(log_levels_t, char *) A function pointer that points to
 * the user-defined logging function.  It MUST take in two paramaters:  a 
 * log_levels_t variable to indicate the log level of the message, and a 
 * char * string that is the composite message.
 * 
 * @retval TRUE Logging callback function set properly
 * @retval FALSE Logging callback function not set, verify the function pointer.
 * 
 * @usage Use this to set the function callback for logging.  Requires a 
 * complimentary call to enableLogCallback() to enable the feature.
 *
 * @codeexample
 * For example, I want all logging to be redirected to my local logging 
 * fuction, logging_cb().
 * @code
 * // My function is defined as:  void logging_cb(log_levels_t lev, char* s);
 * enableLogCallback (TRUE); //to enable the feature
 * if (setLogCallback (&logging_cb)) {
 *      //SUCCESS
 * }
 * @endcode  
 */
boolean
setLogCallback(void (*cb)(log_levels_t, char *));

#ifdef __cplusplus
}
#endif

#endif /* LOG_H_ */
