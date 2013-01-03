/*
Copyright (C) 2010 2011 Cisco Systems

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
////
// @todo Move Enternet specific queries (MAC), to mpx.lib.ifconfig.

#include <Python.h>

#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <net/if_packet.h>
#include <netpacket/packet.h>
#include <netinet/if_ether.h>
#include <netinet/in.h>

#include "lib.h"

#include "virtual.h"

// Virtual MAC 'Protocol Control Information'.
struct MPCI {
  struct {
    unsigned char id[4];
    unsigned char bcast[2];
  } da;
  struct {
    unsigned char id[4];
    unsigned char bcast[2];
  } sa;
  unsigned short length; // Length of entire packet.
};

////
// @todo Ensure the entire message is sent.
// @note bnb->p_npci and bnb->s_data must be valid.  This also assumes that
//       bnb->p_data immediately follows bnb->p_npci.
int send_virtual(int socket,
		 const struct ADDR *source,
		 const struct ADDR *destination,
		 struct BACNET_BUFFER *bnb) {
  int length;
  struct MPCI *mpci;

  // Get pointers to the MAC data and the LLC data.
  bnb->p_llc = (unsigned char *)bnb->p_npci;
  bnb->p_mac = (unsigned char *)bnb->p_llc - sizeof(struct MPCI);
  mpci = (struct MPCI *)bnb->p_mac;

  // Construct MAC data.
  switch (source->length) {
  case 0: memset(&mpci->sa, 0, 6);
    break;
  case 6: memcpy(&mpci->sa, source->address, 6);
    break;
  default:
    return -1;  // @fixme raise Exception!
  }
  switch (destination->length) {
  case 0: memset(&mpci->da, 0xff, 6);
    break;
  case 6: memcpy(&mpci->da, destination->address, 6);
    break;
  default:
    return -1;  // @fixme raise Exception!
  }
  length = npci_length(bnb) + bnb->s_data;
  mpci->length = htons(length);

  // Add 12 bytes for the source and destination addresses and
  // another 2 bytes for the length of the LLC.
  length += sizeof(*mpci);
  return sendto(socket >> 16, bnb->p_mac, length, 0, NULL, 0);
}

////
// @todo Use MPCI to ensure the entire message is received.
int recv_virtual(int socket, struct ADDR *source, struct BACNET_BUFFER *bnb) {
  int n;
  int length;
  bnb->p_mac = bnb->pad;
  bnb->p_llc = bnb->pad + sizeof(struct MPCI);
  bnb->p_npci = (struct PACKED_NPCI*)bnb->p_llc;
  while (1) {
    Py_BEGIN_ALLOW_THREADS ;
    n = recvfrom(socket & 0x00007fff, bnb->p_mac, bacnet_max_data_size(bnb) +
		 sizeof(bnb->pad), 0, NULL, 0);
    Py_END_ALLOW_THREADS ;
    // To decode the NCPI, p_data and s_data, bacnet_decode_npci_data()
    // needs p_ncpi to be valid, p_data -> p_ncpi and s_data to equal
    // the length of the message, starting at p_ncpi.
    bnb->p_data = (void*)bnb->p_npci;
    length = ntohs(((struct MPCI*)bnb->p_mac)->length);
    bnb->s_data = length;
    bacnet_decode_npci_data(bnb);
    if (source) {
      // Report the source MAC address.
      source->length = 6;
      memcpy(source->address, &((struct MPCI*)bnb->p_mac)->sa, 6);
    }
    return n;
  }
}

////
// Close the ethernet interface referred to by <close>socket</close>.
int close_virtual(int socket) {
  int result = close(socket >> 16);
  if (result < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    return result;
  }
  result = close(socket & 0x00007ffff);
  if (result < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
  }
  return result;
}

int open_virtual(const char *name, struct ADDR *addr, int network) {
  const static unsigned char vrtual_router_mask[2] = {0x00,0xff};
  int err, sockets[2], result;
  struct sockaddr_ll sll;
  struct ifreq ifr;

  err = socketpair(PF_UNIX, SOCK_DGRAM, 0, sockets);
  if (err < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    return -1;
  }
  if (sockets[0] & 0xffff8000 || sockets[1] & 0xffff8000) {
    // Assumes that both fds are < 32768...
    // @fixme SET A BETTER ERROR.
    PyErr_SetFromErrno(PyExc_OSError);
    return -1;
  }
  result = (sockets[0] << 16) | sockets[1];

  // Make up a unique MAC address for this interface.
  memset(addr->address, 0, sizeof addr->address);
  addr->length = 6;
  memcpy(addr->address, &network, 4);
  memcpy(addr->address+4,vrtual_router_mask, 2);

  return result;
}
