/*
Copyright (C) 2002 2003 2008 2010 2011 Cisco Systems

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
#include "_lib.h"
#include <stdio.h>
#include <dlfcn.h>

extern void (*broadway_get_buffer)(const unsigned char **buffer,
           UINT32 *length,
           PyObject *object);

extern PyObject *(*broadway_raise)(char *name,
           PyObject *args, PyObject *keywords);
extern PyObject *(*broadway_exception_from_name)(char *name);
extern void (*broadway_raise_parse_failure)(const char *msg,
              unsigned char value);
extern void (*broadway_raise_invalid_ulong)(unsigned long value,
              const char *name,
             const char *msg);
extern void (*broadway_raise_invalid_object)(PyObject *value, const char *name,
               const char *msg);
extern void (*broadway_assert_exception_set)(const char *filename, int lineno);
extern int (*new_socket_entry)(int direct, int broadcast, int limited_broadcast,
             int network,
             const struct ADDR *interface_address,
             const struct ADDR *broadcast_address);
extern struct SOCKET_MAP *(*del_socket_entry)(int entry_id);
extern struct SOCKET_MAP *(*get_socket_entry)(int entry_id);

////
// Routing functions.
//

extern int (*bacnet_add_interface)(unsigned short network,
           int socket,
           int (*send)(int socket,
                 const struct ADDR *source,
                 const struct ADDR *destination,
                 struct BACNET_BUFFER *bnb),
           int (*recv)(int socket, struct ADDR *source,
                 struct BACNET_BUFFER *bnb),
           int (*close)(int socket),
           const struct ADDR *source,
           const struct ADDR *broadcast,
          int max_apdu_code);
extern int (*bacnet_add_route)(unsigned short remote_network,
             unsigned short interface_network,
             const struct ADDR *router_addr);
extern int (*bacnet_del_route)(unsigned short network);

extern int (*bacnet_network_is_local)(unsigned short network);

extern const struct ADDR *(*bacnet_interface_addr)(unsigned short network);
extern const struct ADDR *(*bacnet_interface_broadcast)(unsigned short
              network);
extern int (*bacnet_interface_socket)(unsigned short network);

extern const struct ADDR *(*bacnet_router_addr)(unsigned short network);

////
// Allocate a buffer and encode an NPDU into the new buffer.
// @param npci The BACNET_NPCI structure to encode.
// @param apci The BACNET_APCI structure to encode.
// @param data A pointer to the data to append to the encoded buffer.
// @param length The number of bytes to append to the encoded buffer.
// @return An encoded buffer.  If any failure occurs, then NULL is
//         returned.
// @note If an error occurs, then an appropriate Python error condition is set.
// @note No MAC or LLC data is encoded in the buffer, but it is ready
//       to have such data prepended to it.
// @fixme In the case of failure, raise an exception derived from MpxException.
extern struct BACNET_BUFFER *(*encode_new_buffer)
     (const struct BACNET_NPCI *npci,
      const struct BACNET_APCI* apci,
      void *data,
      int length);

////
// Decode a BACnet message in a <code>BACNET_BUFFER</code>.
//
// @param buffer The <code>BACNET_BUFFER</code> to decode.
// @param npci Where the NPCI information is stored.  If npci == NULL,
//             then the information is discarded.
// @param apci Where the APCI header information is stored.  If apci == NULL,
//             then the information is discarded.  If it is a network message,
//             then apci.invalid_apci == 1.
// @param ppdata Where to store the address of the raw bytes beyond the NPCI
//               and APCI structures.  If it is NULL, then it is not set.
// @param maxlen The maximum number of bytes to copy to <code>data</code>.
// @return The number of bytes received beyond the NPCI and APCI structures,
//         which could be coped from *ppdata.
//         If an error occurs, -1 is returned and an appropriate Python
//         error condition is set.
// @fixme Detect errors, return -1 and set the appropriate Python
//        error condition is set.
extern int (*decode_existing_buffer)(struct BACNET_BUFFER *buffer,
             struct BACNET_NPCI* npci,
             struct BACNET_APCI* apci,
             void **ppdata);

// Basic I/O.

////
// Send data to a BACnet device.
//
// @param network The BACnet device's network.
// @param dest The BACnet device's address.
// @param npci Describes the NPCI information for the message.
// @param apci Describes the APCI header (everything upto, but not
//             including, the tag data).  Should be NULL for network
//             messages (messages where ncpi.network_msg == 1).
// @param data The data to send to the device.
// @param length The length of the data to send.
// @todo  Handle segmenting the messages.
extern int (*bacnet_send_message)(unsigned short network,
          const struct ADDR *dest,
          const struct BACNET_NPCI *npci,
          struct BACNET_APCI* apci, // shp: rmvd 'const' to allow setting of max_apdu_length_accepted bitfield
          void *data,
          int length,
          long debug_level);

////
// Receive data from a BACnet network.
//
// @param network The (local) BACnet network on which to receive.
// @param source Where the BACnet address of the sending device is
//               stored (reported).  If source == NULL, then the
//               information is not reported.
// @param npci Where the NPCI information is stored.  If npci == NULL,
//             then the information is discarded.
// @param apci Where the APCI header information is stored.  If apci == NULL,
//             then the information is discarded.  If it is a network message,
//             then apci.invalid_apci == 1.
// @param data Where to copy the received data.
// @param length The maximum amount of data to copy.
extern int (*bacnet_recv_message)(unsigned short network,
          struct ADDR *source,
          struct BACNET_NPCI* npci,
          struct BACNET_APCI* apci,
          void *data,
          int maxlen,
          long debug_level);

////
// Close the interface attached to a specific <code>network</code>.
//
// @param network The BACnet network to close.
extern int (*bacnet_close)(unsigned short network);
extern unsigned short (*npci_length)(struct BACNET_BUFFER *bnb);
extern void (*bacnet_decode_npci_data)(struct BACNET_BUFFER *bnb);
extern int (*is_buffer)(PyObject *object);

//
// Buffer functions.
//
extern struct BACNET_BUFFER *(*bacnet_alloc_buffer)(int data_size);
extern void (*bacnet_free_buffer)(struct BACNET_BUFFER *bnb);
extern void (*bacnet_reset_buffer)(struct BACNET_BUFFER *bnb);
extern int (*bacnet_buffer_size)(struct BACNET_BUFFER *bnb);
extern int (*bacnet_max_data_size)(const struct BACNET_BUFFER *bnb);

extern int load_lib_references(void);
