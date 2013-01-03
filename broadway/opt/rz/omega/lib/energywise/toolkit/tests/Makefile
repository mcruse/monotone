# Copyright (c) 2009 by Cisco Systems, Inc.
#
CMODE=

LIBDIR = ../lib

ifdef COMSPEC
LDFLAGS = -L$(LIBDIR) -lewapi -leay32 -lWs2_32 -lrpcrt4
EXE_EXT=.exe
else
LDFLAGS = -lssl -lcrypto -luuid -lewapi -lm -L$(LIBDIR)
endif

ifeq ($(OS),Windows) #compiling for Windows on Linux
PREFIX=/auto/energywise/mingw/mingw32/bin/i386-mingw32-
EXE_EXT=.exe
LDFLAGS = -L$(LIBDIR) -lewapi -leay32 -lws2_32 -lrpcrt4
endif

CC = $(PREFIX)gcc
LD = $(CC) 
CFLAGS = $(CMODE) -Wall -I../include -I. -I\openssl -I../src -O0 -g3

OBJECTS = MgmtApiTest.o QueryTests.o InternalTests.o

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

MgmtApiTest: MgmtApiTest.o QueryTests.o 
	$(LD) -o MgmtApiTest$(EXE_EXT) MgmtApiTest.o QueryTests.o $(LDFLAGS)

#
# Use:  make CMODE=-DINTERNAL_TESTS tests
#

tests: MgmtApiTest.o QueryTests.o InternalTests.o
	$(LD) -o MgmtApiTest$(EXE_EXT) $(OBJECTS) $(LDFLAGS)

clean:
	rm -f *.o MgmtApiTest MgmtApiTest.exe
