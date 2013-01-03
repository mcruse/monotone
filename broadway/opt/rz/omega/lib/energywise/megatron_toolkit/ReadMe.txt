
# Copyright (c) 2009-2010 by Cisco Systems, Inc.

Release Notes
-------------

Contents of the Cisco EnergyWise Installation Toolkit
	* "include" directory with .h header files for Cisco EnergyWise SDK and API
	* "libewsdk.so" & "libewapi.so" - Linux library for Cisco EnergyWise SDK and API
	* "libewsdk.dll" & "libewapi.dll" - Windows XP library for Cisco EnergyWise SDK and API
        * "libewsdk.lib" - Windows XP import library for libewsdk
        * "libewapi.lib" - Windows XP import library for libewapi
	* "tests" directory with source code for Cisco EnergyWise Managment API query examples
	* "ref_agent" directory with source code for a reference implementation of the Energywise SDK

The C code included here requires a C99 compatible compiler and has been tested with the portable GCC compiler.

Use of the Cisco EnergyWise Toolkit is subject to the agreement in software_license_disclaimer.txt"

Windows Runtime Install
-----------------------

Pre-requisites
	1. .NET3.5 
	2. OpenSSL runime libraries
	3. MinGW runtime libraries 
	
Installation
	1. Copy the pre-requisite libraries into \windows\system32
		* libeay32.dll and libssl32.dll  (OpenSSL) 
		* mingwm10.dll (MinGW)
	
	2. Copy the appropriate Cisco EnergyWise DLL "libewapi.dll" or "libewsdk.dll" to C:\windows\system32 
	
Link libraries
   * ws2_32
   * rpcrt4
   * eay32

Note, Visual Studio C++ and older C++ compilers may require compatiblity.  Several 
C99 features can be applied to older environments with these additions:
   * stdint.h can be found here http://msinttypes.googlecode.com/svn/trunk/stdint.h
   * getopt has several open source implementations

Linux Runtime Install
---------------------
	1. OpenSSL runtime libraries

Pre-requisites

	1. Verify that your Linux has the OpenSSL libraries available.  If not, please install them
	2. Install the appropriate Cisco EnergyWise library "libewapi.so" or "libewsdk.so" 
	3. Set LD_LIBRARY_PATH to include the directory containing the appropriate Cisco EnergyWise 
            library and OpenSSL
	
	
Distribution Contents
---------------------

	examples/
		MgmtApiTest.c			- Management API example source file
		QueryTests.c			- Management API example source file
		QueryTests.h			- Management API example header file
		RefAgent.c			- SDK reference implementation
	
	include/
		EnergyWise.h			- Cisco EnergyWise constants
		Log.h				- logging declarations and constants
		MgmtApi.h			- Management API main header file
		SvcApi.h			- SDK main header file
		platform_types.h 		- platform specific type definitions and includes
		powernet_types_pnxml.h	        - Cisco EnergyWise Protocol constants
		
	lib/
		libewapi.dll			- Cisco EnergyWise toolkit API library for Windows
		libewapi.so			- Cisco EnergyWise toolkit API library for i86 Linux
		libewsdk.dll			- Cisco EnergyWise toolkit SDK library for Windows
		libewsdk.so			- Cisco EnergyWise toolkit SDK library for i86 Linux
                libewapi.lib                    - Cisco EnergyWise toolkit API import library for Windows
                libewsdk.lib                    - Cisco EnergyWise toolkit SDK import library for Windows 
		
Management API Use & Examples
-----------------------------

The functions included in the Management API are declared in include/MgmtApi.h.  To write 
a C program using the API, you would include this file and link your program with the appropriate
'libewtools' library for your platform. 

As an example, the file QueryTest.c has a number of functions which execute different types of
Cisco EnergyWise queries.   The MgmtApiTest.c source file reads command line arguments and invokes 
the desired tests.


SDK Use & Examples
------------------

To develop a Cisco EnergyWise EndPoint agent using C, you would include the file include/SvcApi.h
and link your implementation with the appropriate 'libewtools' library for your platform.

An example reference implementation of the Cisco EnergyWise SDK is provided in the source file 
RefAgent.c.  This illustrates sample implementation of callback functions and the use of the
SDK function calls for initialization, configuration, and startup.  When run, the reference 
agent will appear as an EndPoint in a Cisco EnergyWise domain.  

The reference implementation does not provide real values for energy usage, UUID, or persist 
the sequence number and is thus only useful for demonstration purposes. 


