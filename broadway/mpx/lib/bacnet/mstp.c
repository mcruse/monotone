/*
Copyright (C) 2003 2010 2011 Cisco Systems

This program is free software; you can redistribute it and/or         
modify it under the terms of the GNU General Public License         
as published by the Free Software Foundation; either version 2         
of the License, or (at your option) any later version.         
    
This program is distributed in the hope that it will be useful,         
but WITHOUT ANY WARRANTY; without even the implied warranty of         
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
GNU General Public License for more details.         
    
You should have received a copy of the GNU General Public License         
along with this program; if not, write to:         
The Free Software Foundation, Inc.         
59 Temple Place - Suite 330         
Boston, MA  02111-1307, USA.         
    
As a special exception, if other files instantiate classes, templates  
or use macros or inline functions from this project, or you compile         
this file and link it with other works to produce a work based         
on this file, this file does not by itself cause the resulting         
work to be covered by the GNU General Public License. However         
the source code for this file must still be made available in         
accordance with section (3) of the GNU General Public License.         
    
This exception does not invalidate any other reasons why a work         
based on this file might be covered by the GNU General Public         
License.
*/
// mstp.h: Implementation file for BACnet MSTP datalink layer adapter functions. 
// Communicate between MFW and n_mstp ldisc.

#include <Python.h>

#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include <config.h>
#ifdef HAVE_SYS_IO_H
#include <sys/io.h>     // For direct access to Linux I/O ports for Trane boards
#endif

#include <sys/ioctl.h>
#include <asm/ioctls.h>
#include <fcntl.h>
#include <termios.h>
#include <errno.h>

#include <linux/serial.h>

#include "lib.h"

#include "mstp.h"

// dump_block(): Formats and "printk"s block of bytes as space-separated hex 
// digit pairs, with 16 pairs per line:
void dump_block(const unsigned char* block, unsigned int length)
{
	unsigned int i,j;
	char linebuf[16*3+1];
	
	for(i=0;i<length;i+=16)
	{
		for(j=0;(j<16) && (j+i<length);j++)
		{
			sprintf(linebuf+3*j,"%02x ",block[i+j]);
		}
		linebuf[3*j]='\0';
		fprintf(stdout, "%s\n", linebuf);
	}
}

// send_mstp():
// @note bnb->p_npci and bnb->s_data must be valid.  This also assumes that
//       bnb->p_data immediately follows bnb->p_npci in memory, AND that
//       bnb->p_npci is at least 1 byte AFTER bnb->pad, AND that destination
//       is valid.
int send_mstp(int fd_mstp,
		const struct ADDR *source,
		const struct ADDR *destination,
		struct BACNET_BUFFER *bnb)
{
	int length = 0;
struct timeval tm;
	
	// NPDU consists of npci plus data. Make space for destination MAC
	// addr (one byte before NPDU):
	bnb->p_mac = (unsigned char*)bnb->p_npci - 1;

	// Set dst MAC addr:
	switch(destination->length)
	{
		case 0: *(unsigned char*)(bnb->p_mac) = 0xFF; break; // assume bcast
		case 1: *(unsigned char*)(bnb->p_mac) = *(destination->address); break; // unicast
		default: return -1;  // @fixme raise Exception!
	}
	
	length = 1 + npci_length(bnb) + bnb->s_data;
	return write(fd_mstp, bnb->p_mac, length);
}

// recv_mstp(): BLOCKING
int recv_mstp(int fd_mstp, struct ADDR *source, struct BACNET_BUFFER *bnb)
{
	int nBytesRead = -1;
struct timeval tm;
	
	bnb->p_mac = bnb->pad;
	bnb->p_npci = bnb->p_mac + 1; // all MSTP MAC addrs are exactly one byte long
	Py_BEGIN_ALLOW_THREADS ;
	nBytesRead = read(fd_mstp, bnb->p_mac, bacnet_max_data_size(bnb));
	Py_END_ALLOW_THREADS ;
	
	if(nBytesRead < 0)
		return -1;
	
	// Set source address:
	if(source)
	{
		source->address[0] = ((unsigned char*)(bnb->p_mac))[0];
		source->length = 1;
	}
	
	// To decode the NPCI, p_data and s_data, bacnet_decode_npci_data()
	// needs p_npci to be valid, p_data -> p_npci and s_data to equal
	// the length of the message, starting at p_npci.
	bnb->p_data = (void*)bnb->p_npci;
	bnb->s_data = nBytesRead - 1; // all MSTP MAC addrs are exactly one byte long
	bacnet_decode_npci_data(bnb);
	return nBytesRead;
}

// close_mstp(): Close the serial port associated with the given name.
int close_mstp(int fd_mstp)
{
	int iRtn = 0, iLdNum = 0; // n_tty: default
	unsigned char temp = 0;
	int fd_procfs_model = -1, iLenRd = 0;
	char cBuf[200];
	struct serial_struct serial;
	
	// Swap in the default ldisc...:
	ioctl(fd_mstp, TIOCSETD, &iLdNum);
	
	// If this code is running on a 1200 or 2400, then we should passivate the port:
	fd_procfs_model = open("/proc/mediator/model", O_RDONLY);
	if(fd_procfs_model < 0)
		return iRtn;
	iLenRd = read(fd_procfs_model, cBuf, sizeof(cBuf) - 1);
	cBuf[iLenRd] = '\0';
#if 0
	if((strncmp("1200",cBuf,4) == 0) || (strncmp("2400",cBuf,4) == 0))
	{
		memset(&serial,0,sizeof(serial));
		iRtn = ioctl(fd_mstp, TIOCGSERIAL, &serial); // get port num (eg 0x240)
		if(serial.port == 0)
			return iRtn;
		ioperm(0x240, 32, 1);
		temp = inb(serial.port + 3);
		outb(0xbf, serial.port + 3);
		inb(serial.port + 1);
		outb(0x08, serial.port + 1);
		outb(temp, serial.port + 3);
	}
#endif
	return iRtn;
}

//@FIXME: Include this define gracefully...
#define MSTP_IOCGADDRS    0x54E00010  // get own and next addrs (8 bytes total)
#define MSTP_IOCSADDR     0x54E00011  // set own addr (4 bytes total)

// open_mstp(): Open and configure the serial port associated with the given name.
// @param name: name of hardware port (eg 'com1', etc.): currently not used, since port is already open...
// @param addr: struct containing desired MAC address, into which this
//   function puts the actual MAC address.
// @param fd_mstp: file descriptor for already-open RS485 port
int open_mstp(const char *name, struct ADDR *addr, int fd_mstp)
{
	int iComNum = -1, iLdNum = 5, iAddrs[2], iAddr = 0; //@FIXME: replace "5" with symbolic ref to actual, new ldisc num for MSTP
	struct termios tios;
	struct serial_struct ss;
	
	// Replace current ldsc with n_mstp ldisc:
	ioctl(fd_mstp, TIOCSETD, &iLdNum);

	// Attempt to set MAC address as per given:
	iAddr = addr->address[0];
	ioctl(fd_mstp, MSTP_IOCSADDR, &iAddr);
	
	// Return actual MAC address read from ldisc:
	memset(addr->address, 0, sizeof addr->address);
	ioctl(fd_mstp, MSTP_IOCGADDRS, iAddrs);
	
	addr->length = 1;
	addr->address[0] = iAddrs[0] & 0xFF;
	
	return fd_mstp;
}


