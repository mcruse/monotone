/*
Copyright (C) 2001 2002 2008 2009 2010 2011 Cisco Systems

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
// @todo Move IP specific queries (addr, bcast_addr), to mpx.lib.ifconfig.
// @todo A low-level send (or sends) for BBMD.
// @todo Support multicast.

#include <Python.h>

#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>

#include <sys/socket.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/poll.h>
#include <net/if.h>
#include <net/if_packet.h>
#include <netpacket/packet.h>
#include <netinet/if_ether.h>
#include <netinet/in.h>

#include "lib.h"
#include "ip.h"
#include "_bvlc_stub.h"

////
// @todo Ensure the entire message is sent.
// @note bnb->p_npci and bnb->s_data must be valid.  This also assumes that
//       bnb->p_data immediately follows bnb->p_npci.
// @todo determine how to choose between ORIGINAL_BROADCAST_NPDU and
//       DISTRIBUTE_BROADCAST_TO_NETWORK.
int send_ip(int socket,
    const struct ADDR *source,
    const struct ADDR *destination,
    struct BACNET_BUFFER *bnb) {
  int length;
  struct BVLC_HEADER *bvlc;
  struct sockaddr_in to;
  unsigned short function;
  struct SOCKET_MAP *entry = get_socket_entry(socket);
  struct ifreq ifr_broadcast;
  struct in_addr in_addr_bcast;

  if (entry == NULL) {
    // Bad argument.
    return -1; // @fixme raise Exception!
  }

  // Get pointers to the MAC data and the LLC data (both point to the BVLC).
  bnb->p_llc = (unsigned char *)bnb->p_npci - sizeof *bvlc;
  bnb->p_mac = bnb->p_llc;
  bvlc = (struct BVLC_HEADER *)bnb->p_llc;

  // Construct MAC data.
  if (destination->length != 6) {
    return -1; // @fixme raise Exception!
  }

  if (inet_aton("255.255.255.255", &in_addr_bcast) < 0) {
      return -1; // @fixme raise Exception!
  }

  if (memcmp(destination->address, \
    entry->broadcast_address.address, 4) == 0 || memcmp(destination->address, \
    &in_addr_bcast, 4) == 0) {
    function = (1)
      ? ORIGINAL_BROADCAST_NPDU			// "Regular" broadcast.
      : DISTRIBUTE_BROADCAST_TO_NETWORK ;	// From foreign device to BBMD.
  } else {
    function = ORIGINAL_UNICAST_NPDU;		// All unicasts use this.
  }
  memset(&to, 0, sizeof(to));
  to.sin_family = AF_INET;
  memcpy(&to.sin_addr.s_addr, destination->address, 4);
  memcpy(&to.sin_port,  destination->address+4, 2);

  // Construct the BACnet/IP LLC data.
  bvlc->type = BVLL_FOR_BACNET_IP;
  bvlc->function = function;
  length = npci_length(bnb) + bnb->s_data + sizeof(*bvlc);
  bvlc->length = htons(length);

  if (function == ORIGINAL_BROADCAST_NPDU) {
    // The recv_ip() function does not pass ORIGINAL_BROADCAST_NPDUs from
    // the interface's direct address to the BVLC queue.  This is to avoid
    // a perpetual broadcast storm. Therefore, we push a copy when we send
    // it.
    bvlc_copy_to_queue(entry->network, source->address,
            (union BVLC_FUNCTION *)bvlc);
  }
  return sendto(entry->direct, bnb->p_llc, length, 0,
    (struct sockaddr *)&to, sizeof(to));
}

////
// @todo Use BVLC to ensure the entire message is received.
int recv_ip(int socket, struct ADDR *source, struct BACNET_BUFFER *bnb) {
  int i,n;
  union BVLC_FUNCTION *bvlc;
  struct pollfd fds[3];
  struct sockaddr_in sin_source;
  socklen_t sin_length = sizeof(sin_source);
  struct SOCKET_MAP *entry = get_socket_entry(socket);
  struct ADDR scratch_address;

  if (entry == NULL) {
    // Bad argument.
    return -1; // @fixme raise Exception!
  }

  bnb->p_mac = bnb->pad;
  bnb->p_llc = bnb->pad;
  if (!source) {
    source = &scratch_address;
  }
  while (1) {
    memset(fds, 0, sizeof fds);
    fds[0].fd = entry->broadcast;
    fds[0].events = POLLIN;
    fds[1].fd = entry->limited_broadcast;
    fds[1].events = POLLIN;
    fds[2].fd = entry->direct;
    fds[2].events = POLLIN;
    Py_BEGIN_ALLOW_THREADS ;
    n = poll(fds, 3, -1);
    Py_END_ALLOW_THREADS ;
    if (n < 0) {
      if (errno == EINTR) {
          continue;
      }
      // @fixme Set a better exception condition?
      PyErr_SetFromErrno(PyExc_OSError);
      return -1;
    }
    socket = -1;
    for (i=0; i<3; i++) {
      if (fds[i].revents & POLLIN) {
        // Read from the first available socket.  (Broadcasts have priority)
        socket = fds[i].fd;
        break;
      }
    }
    if (socket < 0) {
      // @fixme Do something to avoid spinning?  Is this an error condition?
      continue;
    }
    Py_BEGIN_ALLOW_THREADS ;
    n = recvfrom(socket, bnb->p_llc,
		 bacnet_max_data_size(bnb) + sizeof(bnb->pad), 0,
		 (struct sockaddr *)&sin_source,
		 &sin_length);
    Py_END_ALLOW_THREADS ;
    if (n < 0) {
      if (errno == EINTR) {
        continue;
      }
      // @fixme Set a better exception condition?
      PyErr_SetFromErrno(PyExc_OSError);
      return -1;
    }
    // Report the source MAC address.
    source->length = 6;
    memcpy(source->address, &sin_source.sin_addr, 4);
    memcpy(source->address+4, &sin_source.sin_port, 2);
    bvlc = (union BVLC_FUNCTION *)bnb->p_llc;
    if (n >= sizeof bvlc->header && bvlc->header.type == BVLL_FOR_BACNET_IP) {
      switch (bvlc->header.function) {
      case ORIGINAL_UNICAST_NPDU:
      case ORIGINAL_BROADCAST_NPDU:
        // To decode the NCPI, p_data and s_data, bacnet_decode_npci_data()
        // needs p_ncpi to be valid, p_data -> p_ncpi and s_data to equal
        // the length of the message, starting at p_ncpi.
        bnb->p_npci = (struct PACKED_NPCI*)(bnb->p_llc +
                                            sizeof bvlc->original_unicast_npdu);
        bnb->p_data = (void*)bnb->p_npci;
        bnb->s_data = n - sizeof bvlc->original_unicast_npdu;
        bacnet_decode_npci_data(bnb);
        if (bvlc->header.function == ORIGINAL_BROADCAST_NPDU) {
          if (memcmp(entry->interface_address.address,source->address,6)) {
            // Send to BVLC layer.  (Iff we did not send it).
            bvlc_copy_to_queue(entry->network, source->address, bvlc);
          }
        }
        return n;
      case FORWARDED_NPDU:
        if (i > 1) { // socket index implies broadcast socket if i <= 1;
	             // therefore, another bbmd sent it
          if (memcmp(entry->interface_address.address,source->address,6)) {
            // Send to BVLC layer.  (Iff we did not send it).
            bvlc_copy_to_queue(entry->network, source->address, bvlc);
            continue;   //we will resend in it will then go through below
          }
        }
        // To decode the NCPI, p_data and s_data, bacnet_decode_npci_data()
        // needs p_ncpi to be valid, p_data -> p_ncpi and s_data to equal
        // the length of the message, starting at p_ncpi.
        bnb->p_npci = (struct PACKED_NPCI*)(bnb->p_llc +
                                            sizeof bvlc->forwarded_npdu);
        bnb->p_data = (void*)bnb->p_npci;
        bnb->s_data = n - sizeof bvlc->forwarded_npdu;
        bacnet_decode_npci_data(bnb);
        if (source) {
          // Report the source MAC address.
          source->length = 6;
          memcpy(source->address, bvlc->forwarded_npdu.source, 6);
        }		// Send to BVLC layer.
        return n;
      case RESULT:
      case WRITE_BROADCAST_DISTRIBUTION_TABLE:
      case READ_BROADCAST_DISTRIBUTION_TABLE:
      case READ_BROADCAST_DISTRIBUTION_TABLE_ACK:
      case REGISTER_FOREIGN_DEVICE:
      case READ_FOREIGN_DEVICE_TABLE:
      case READ_FOREIGN_DEVICE_TABLE_ACK:
      case DELETE_FOREIGN_DEVICE_TABLE_ENTRY:
      case DISTRIBUTE_BROADCAST_TO_NETWORK:
        // Send to BVLC layer.
        bvlc_copy_to_queue(entry->network, source->address, bvlc);
        break;
      default:
        // @todo Huh?
        break;
      }
    }
  }
}

////
// Close the IP interface referred to by <close>socket</close>.
int close_ip(int socket) {
  struct SOCKET_MAP *entry = get_socket_entry(socket);
  if (entry == NULL) {
    return -1; // @fixme raise Exception!
  }
  close(entry->direct);
  close(entry->broadcast);
  del_socket_entry(socket);
  return 0;
}

int open_ip(const char *name, struct ADDR *addr,
	    int port, struct ADDR *get_broadcast,
	    int network) {
  static int limited_broadcast = -1;
  int direct, broadcast, mapped_socket;
  int bool;
  struct sockaddr_in sin_direct, sin_broadcast, sin_l_broadcast, sin_netmask;
  struct ifreq ifr_direct, ifr_broadcast;
  unsigned short htons_port = htons(port);

  // Get a UDP socket for directed datagrams.
  direct = socket(PF_INET, SOCK_DGRAM, 0);
  if (direct < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Direct socket() failed");
    return -1; // @fixme raise a better Exception!
  }

  // Allow REUSE of the direct socket.
  bool = 1;
  if (setsockopt(direct, SOL_SOCKET, SO_REUSEADDR, &bool, sizeof bool) == -1) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Could not set the direct socket to REUSEADDR.");
    close(direct);
    return -1; // @fixme raise a better Exception!
  }

  // Get a UDP socket for broadcast datagrams.
  broadcast = socket(PF_INET, SOCK_DGRAM, 0);
  if (broadcast < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Broadcast socket() failed");
    close(direct);
    return -1; // @fixme raise a better Exception!
  }

  // Allow REUSE of the broadcast socket.
  bool = 1;
  if (setsockopt(broadcast, SOL_SOCKET,
		 SO_REUSEADDR, &bool, sizeof bool) == -1) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Could not set the broadcast socket to REUSEADDR.");
    close(direct);
    close(broadcast);
    return -1;  // @fixme raise a better Exception!
  }

  // Find the interface's IP address which (along with the port) is the
  // BACnet/IP MAC address.
  memset(&ifr_direct, 0, sizeof(ifr_direct));
  strncpy(ifr_direct.ifr_name, name, sizeof(ifr_direct.ifr_name));

  if (ioctl(direct, SIOCGIFADDR, &ifr_direct) == -1) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Direct ioctl SIOCGIFADDR failed.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }

  // Bind to the interface's direct address so we can send and receive
  // directed datagrams.
  memset(&sin_direct, 0, sizeof(sin_direct));
  sin_direct.sin_family = AF_INET;
  // @todo Figure out why the address starts at +2...
  sin_direct.sin_addr.s_addr=*(unsigned long*)(ifr_direct.ifr_addr.sa_data+2);
  sin_direct.sin_port = htons_port;

  if (bind(direct, (struct sockaddr *)&sin_direct, sizeof(sin_direct)) < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Direct bind failed.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }

  // Enable sending broadcast datagrams from the direct port.
  bool = 1;
  if (setsockopt(direct, SOL_SOCKET, SO_BROADCAST,
		 &bool, sizeof(bool)) == -1) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Could not enable sending broadcasts from " \
	   "the direct socket.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }

  // Ensure that the interface supports broadcasts.
  memset(&ifr_broadcast, 0, sizeof(ifr_broadcast));
  strncpy(ifr_broadcast.ifr_name, name, sizeof(ifr_broadcast.ifr_name));
  if (ioctl(broadcast, SIOCGIFFLAGS, &ifr_broadcast) == -1) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Broadcast ioctl SIOCGIFFLAGS failed.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }
  if ((ifr_broadcast.ifr_flags & (IFF_LOOPBACK|IFF_BROADCAST)) == 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Interface does not support broadcasts.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }

  // Get the interface's netmask.
  memset(&ifr_broadcast, 0, sizeof(ifr_broadcast));
  strncpy(ifr_broadcast.ifr_name, name, sizeof(ifr_broadcast.ifr_name));
  if (ioctl(broadcast, SIOCGIFNETMASK, &ifr_broadcast) == -1) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Broadcast ioctl SIOCGIFNETMASK failed.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }
  memset(&sin_netmask, 0, sizeof(sin_netmask));
  sin_netmask.sin_family = AF_INET;
  // @todo Figure out why the address starts at +2...
  sin_netmask.sin_addr.s_addr=*(unsigned long*)(ifr_broadcast.ifr_broadaddr.\
                                                sa_data+2);
  sin_netmask.sin_port  = htons_port;

  // Find the interface's broadcast address.
  memset(&ifr_broadcast, 0, sizeof(ifr_broadcast));
  strncpy(ifr_broadcast.ifr_name, name, sizeof(ifr_broadcast.ifr_name));
  if (ioctl(broadcast, SIOCGIFBRDADDR, &ifr_broadcast) == -1) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Broadcast ioctl SIOCGIFBRDADDR failed.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }
  memset(&sin_broadcast, 0, sizeof(sin_broadcast));
  sin_broadcast.sin_family = AF_INET;
  // @todo Figure out why the address starts at +2...
  sin_broadcast.sin_addr.s_addr=*(unsigned long*)(ifr_broadcast.ifr_broadaddr.\
                                                  sa_data+2);
  sin_broadcast.sin_port  = htons_port;

  // Ensure that the broadcast address looks reasonable.
  if (sin_broadcast.sin_addr.s_addr !=
      (sin_direct.sin_addr.s_addr |
       (sin_netmask.sin_addr.s_addr ^ 0xFFFFFFFF))) {
	if (sin_broadcast.sin_addr.s_addr == 0xFFFFFFFF) {
		// we already have a 255.255.255.255 broadcast socket so force
		// one equal to the local broadcast on the subnet
		sin_broadcast.sin_addr.s_addr = sin_direct.sin_addr.s_addr |
			       (sin_netmask.sin_addr.s_addr ^ 0xFFFFFFFF);
	}
	else {
		PyErr_SetFromErrno(PyExc_OSError);
		perror("open_ip: Broadcast address looks invalid.");
		close(direct);
		close(broadcast);
		return -1; // @fixme raise a better Exception!
	}
  }

  // Bind to the interface's broadcast address so we can receive broadcasts.
  if (bind(broadcast, (struct sockaddr *)&sin_broadcast,
	   sizeof(sin_broadcast)) < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    perror("open_ip: Broadcast bind failed.");
    close(direct);
    close(broadcast);
    return -1; // @fixme raise a better Exception!
  }

  if (limited_broadcast < 0) {
    limited_broadcast = socket(PF_INET, SOCK_DGRAM, 0);
    if (limited_broadcast < 0) {
      PyErr_SetFromErrno(PyExc_OSError);
      perror("open_ip: limited broadcast socket() failed");
      close(direct);
      close(broadcast);
      limited_broadcast = -1;
      return -1;
    }

    bool = 1;
    if (setsockopt(limited_broadcast, SOL_SOCKET,
      SO_REUSEADDR, &bool, sizeof bool) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        perror("open_ip: Could not set the limited broadcast socket to REUSEADDR.");
        close(direct);
        close(broadcast);
        close(limited_broadcast);
        limited_broadcast = -1;
        return -1;
    }

    memset(&sin_l_broadcast, 0, sizeof(sin_l_broadcast));
    sin_l_broadcast.sin_family = AF_INET;
    sin_l_broadcast.sin_addr.s_addr = inet_addr("255.255.255.255");
    sin_l_broadcast.sin_port = htons_port;

    if (bind(limited_broadcast, (struct sockaddr *)&sin_l_broadcast,
      sizeof(sin_l_broadcast)) < 0) {
      PyErr_SetFromErrno(PyExc_OSError);
      perror("open_ip: Limited broadcast bind failed.");
      close(direct);
      close(broadcast);
      close(limited_broadcast);
      limited_broadcast = -1;
      return -1;
    }
  } // if (limited_broadcast < 0)

  // Extract the interfaces BACnet address.
  memset(addr, 0, sizeof addr);
  addr->length = 6;
  memcpy(addr->address, &sin_direct.sin_addr.s_addr, 4);
  memcpy(addr->address+4, &htons_port, 2);

  // Report the interface's broadcast address.
  memset(get_broadcast, 0, sizeof get_broadcast);
  get_broadcast->length = 6;
  memcpy(get_broadcast->address, &sin_broadcast.sin_addr.s_addr, 4);
  memcpy(get_broadcast->address+4, &htons_port, 2);

  // Get a 'mapped' socket used to locate the actual sockets.
  mapped_socket = new_socket_entry(direct, broadcast, limited_broadcast,
    network, addr, get_broadcast);
  if (mapped_socket < 0) {
    errno = EMFILE;
    perror("open_ip: Mapping sockets failed");
    close(direct);
    close(broadcast);
    PyErr_SetFromErrno(PyExc_OSError); // @fixme raise a better Exception!
    return -1;
  }

  // Return the 'mapped' socket, used internally to locate the actual sockets.
  return mapped_socket;
}
