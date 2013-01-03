# Copyright (c) 2009 by Cisco Systems, Inc.

LIBDIR = ../lib

ifdef COMSPEC #compiling for Windows on Windows
LDFLAGS = -L$(LIBDIR) -lewsdk -leay32 -lws2_32 -lrpcrt4
EXE_EXT=.exe
else #compiling on Linux
LDFLAGS = -lssl -lcrypto -luuid -lewsdk -L$(LIBDIR)
endif

ifeq ($(OS),Windows) #compiling for Windows on Linux
PREFIX=/auto/energywise/mingw/mingw32/bin/i386-mingw32-
EXE_EXT=.exe
LDFLAGS = -L$(LIBDIR) -lewsdk -leay32 -lws2_32 -lrpcrt4
endif

CC = $(PREFIX)gcc
LD = $(CC) 
CCFLAGS = -Wall -I../include -I../src -I\openssl -O0 -g3

OBJECTS = RefAgent.o

%.o: %.c
	$(CC) $(CCFLAGS) -c $< -o $@

RefAgent: $(OBJECTS)
	$(LD) -o RefAgent${EXE_EXT} $(OBJECTS) $(LDFLAGS)

clean:
	rm -f *.o RefAgent.exe RefAgent

cleanobjs:
	rm -f *.o 
