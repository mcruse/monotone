/*
Copyright (C) 2002 2003 2007 2008 2010 2011 Cisco Systems

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
// This should be part of a common C development library.

#include <Python.h>

#include <stdlib.h>
#include <netinet/in.h>

#include "_lib.h"

void bacnet_decode_npci_data(struct BACNET_BUFFER *bnb);
static int sizeof_apci(const struct UNKNOWN_PDU *unknown,
               const struct BACNET_NPCI *npci);
//
// Buffer functions.
//
struct BACNET_BUFFER *bacnet_alloc_buffer(int data_size);
void bacnet_free_buffer(struct BACNET_BUFFER *bnb);
void bacnet_reset_buffer(struct BACNET_BUFFER *bnb);
int bacnet_buffer_size(struct BACNET_BUFFER *bnb);
int bacnet_max_data_size(const struct BACNET_BUFFER *bnb);

static PyObject *exception_module = NULL;
static PyTypeObject *ArrayType = NULL;

struct ROUTING_TABLE_ENTRY {
  unsigned short network;
  int local_interface;
  union {
    struct {
      int socket;
      int (*send)(int socket,
          const struct ADDR *source,
          const struct ADDR *destination,
          struct BACNET_BUFFER *bnb);
      int (*recv)(int socket, struct ADDR *source, struct BACNET_BUFFER *bnb);
      int (*close)(int socket);
      struct ADDR addr;
      struct ADDR broadcast;
        unsigned char max_apdu_length_accepted; // shp: extracted by network.open_interface() from interface type; used in bacnet_send_message()
    } interface;
    struct {
      unsigned short interface_network;
      struct ADDR router_addr;
    } route;
  } u;
};

typedef struct ROUTING_TABLE_ENTRY *ROUTING_TABLE_ENTRY_REF;

// A routing table segment contains 256 entries.
typedef struct ROUTING_TABLE_ENTRY ROUTING_TABLE_SEGMENT[256];
typedef ROUTING_TABLE_SEGMENT *ROUTING_TABLE_SEGMENT_REF;

// There are a maximum of 256 segments, allocated on an 'as needed'
// basis.
static ROUTING_TABLE_SEGMENT_REF segments[256];

////
// Return the segment for the specified network.
// @return A pointer to the network's segment.  NULL iff no segment
//         exists for the network.
static ROUTING_TABLE_SEGMENT_REF segment_for(unsigned short network) {
  return segments[network >> 8];
}

////
// Returns the class object for exception <code>name</name>.  This works for
// looking up all exceptions in mpx.lib.exceptions, which include all the
// built-in Python exceptions.
// @param name A zero terminated string that is the name of the exception
//             class object to find.
// @return The class object for <code>name</code>.
// @fixme Only return exceptions (currently anything in mpx.lib.exceptions
//        can be returned).
PyObject *broadway_exception_from_name(char *name) {
  PyObject *attr;
  char *module_name = "mpx.lib.exceptions";

  if (!exception_module) {
    exception_module = PyImport_ImportModule(module_name);
    if (!exception_module) {
      return NULL;
    }
  }

  attr = PyObject_GetAttrString(exception_module, name);  // Increments ref.
  if (!attr) {
    return NULL;
  }
  return attr;
}

////
// Set the current exception state.
// @param name A zero terminated string that is the name of the exception
//             class object to find.
// @param args A tuple of arguments to pass to the exception's constructor.
//             If there are no arguments, this can be NULL.  As a convenience,
//             if a PyStringObject is passed in, it will be used as the only
//             argument.
// @param keywords A PyDictObject containing the keywords to pass to the
//                 exceptions's constructor.
// @note If args is a PyStringObject, then it's reference is stolen.  If the
//       caller wish to keep a reference to the string then it's reference
//       must be incremented.  If args is a PyTupleObject, then the reference
//       is <b>not</b> stolen.  Thus, the caller <b>must</b> decrement the
//       tuple's reference to delete it.
PyObject *broadway_raise(char *name, PyObject *args, PyObject *keywords) {
  PyObject *klass;
  PyObject *instance;
  PyObject *string = NULL;

  klass = broadway_exception_from_name(name);
  if (!klass) {
    return NULL;
  }
  if (args != NULL && PyString_Check(args)) {
    string = args;
    args = PyTuple_New(1);
    PyTuple_SetItem(args, 0, string);	// "Steals" a reference to string args.
  }
  if (PyCallable_Check(klass)) {
    // New style classes (2.5 exceptions)
    instance = PyObject_Call(klass, args, keywords);
  } else {
    // Old style classes (2.2 exceptions)
    instance = PyInstance_New(klass, args, keywords);
  }
  if (string) {
    Py_DECREF(args);			// Delete tuple we created.
  }
  PyErr_SetObject(klass, instance);
  Py_DECREF(instance);			// Release "our" exception reference.
  Py_DECREF(klass);			// Release "our" klass reference.
  return NULL;
}

////
// Check that PyErr_Set* has been called.  If not, then set it to
// EInternalError.
void broadway_assert_exception_set(const char *filename, int lineno) {
  if (PyErr_Occurred() == NULL) {
    broadway_raise("EInternalError",
           PyString_FromFormat("Exception not correctly set. (%s:%d)",
                       filename, lineno),
           NULL);
  }
  return;
}

////
// @fixme Make honest, return a buffer "type" code (0 == not a buffer).
int is_buffer(PyObject *object)
{
  if (PyString_Check(object) || (object->ob_type == ArrayType)) {
    return 1;
  }
  return 0;
}

////
// @todo Support all objects that implement the buffer interface?
// @fixme Accept a buffer type code.
void broadway_get_buffer(const unsigned char **buffer, UINT32 *length,
             PyObject *object)
{
  PyObject *tuple, *address, *size, *typecode;
  char *zcode;
  *buffer = NULL;
  *length = 0;

  if (PyString_Check(object)) {
    *buffer = PyString_AS_STRING(object);
    *length = PyString_GET_SIZE(object);
  } else if (object->ob_type == ArrayType) {
    typecode = PyObject_GetAttrString(object, "typecode");
    if (typecode != NULL) {
      zcode = PyString_AsString(typecode);
      if (zcode == NULL && (*zcode != 'c' && *zcode != 'b' && *zcode != 'B')) {
        Py_DECREF(typecode);
        broadway_raise("ETypeError",
                       PyString_FromString("array must be of type \'c\', "
                                           "\'b\', or \'B\'"), NULL);
        return;
      }
      Py_DECREF(typecode);
      tuple = PyObject_CallMethod(object, "buffer_info", "");
      if (tuple != NULL) {
        address = PySequence_GetItem(tuple, 0);
        if (address != NULL) {
          size = PySequence_GetItem(tuple, 1);
          if (size != NULL) {
            if (PyInt_Check(address) || PyInt_Check(size)) {
              *buffer = (unsigned char *)PyInt_AsLong(address);
              *length = (UINT32)PyInt_AsLong(size);
            }
            Py_DECREF(size);
          }
          Py_DECREF(address);
        }
        Py_DECREF(tuple);
      }
    }
  } else {
    broadway_raise("ETypeError",
                   PyString_FromString("Can not decode supplied type."), NULL);
  }
}

void broadway_raise_parse_failure(const char *msg, unsigned char value)
{
  PyObject *args = PyTuple_New(2);
  PyTuple_SetItem(args, 0, PyString_FromString(msg));
  PyTuple_SetItem(args, 1, PyInt_FromLong(value));
  broadway_raise("EParseFailure", args, NULL);
  Py_DECREF(args);
}

void broadway_raise_invalid_ulong(unsigned long value, const char *name,
                  const char *msg)
{
  PyObject *args = PyTuple_New((msg) ? 3 : 2);
  PyTuple_SetItem(args, 0, PyString_FromString(name));
  PyTuple_SetItem(args, 1, PyInt_FromLong(value));
  if (msg) {
    PyTuple_SetItem(args, 2, PyString_FromString(msg));
  }
  broadway_raise("EInvalidValue", args, NULL);
  Py_DECREF(args);
}

void broadway_raise_invalid_object(PyObject *value, const char *name,
                   const char *msg)
{
  PyObject *args = PyTuple_New((msg) ? 3 : 2);
  PyTuple_SetItem(args, 0, PyString_FromString(name));
  Py_INCREF(value); // @fixme - I think this is right...
  PyTuple_SetItem(args, 1, value);
  if (msg) {
    PyTuple_SetItem(args, 2, PyString_FromString(msg));
  }
  broadway_raise("EInvalidValue", args, NULL);
  Py_DECREF(args);
}

static struct SOCKET_MAP socket_map[16];

int new_socket_entry(int direct, int broadcast, int limited_broadcast,
            int network,
            const struct ADDR *interface_address,
            const struct ADDR *broadcast_address)
{
  struct SOCKET_MAP *entry;
  int i;
  for (i=0; i<sizeof(socket_map)/sizeof(*socket_map);i++) {
    entry = socket_map + i;
    if (entry->direct == entry->broadcast) {
      entry->direct = direct;
      entry->broadcast = broadcast;
      entry->limited_broadcast = limited_broadcast;
      entry->network = network;
      entry->interface_address.length = interface_address->length;
      memcpy(entry->interface_address.address,
         interface_address->address, interface_address->length);
      entry->broadcast_address.length = broadcast_address->length;
      memcpy(entry->broadcast_address.address,
         broadcast_address->address, broadcast_address->length);
      return i;
    }
  }
  return -1; // @fixme raise Exception?
}

struct SOCKET_MAP *del_socket_entry(int entry_id)
{
  struct SOCKET_MAP *entry;
  if (entry_id < 0 || entry_id >= sizeof(socket_map)/sizeof(*socket_map)) {
    // Bad argument.
    return NULL;
  }
  entry = socket_map + entry_id;
  entry->direct = -1;
  entry->broadcast = -1;
  return entry;
}

struct SOCKET_MAP *get_socket_entry(int entry_id)
{
  struct SOCKET_MAP *entry;
  if (entry_id < 0 || entry_id >= sizeof(socket_map)/sizeof(*socket_map)) {
    // Bad argument.
    return NULL;
  }
  entry = socket_map + entry_id;
  if (entry->direct == entry->broadcast) {
    // Null record.
    return NULL;
  }
  return entry;
}

////
// Return the segment for the specified network.  If there is no segment
// for the network, one is allocated.
// @return A pointer to the network's segment.
static ROUTING_TABLE_SEGMENT_REF alloc_segment(unsigned short network) {
  ROUTING_TABLE_SEGMENT_REF segment;
  segment = segment_for(network);
  if (segment) {
    return segment;
  }
  segment = (ROUTING_TABLE_SEGMENT_REF)malloc(sizeof(*segment));
  if (segment) {
    memset(segment, 0, sizeof(*segment));
    segments[network >> 8] = segment;
    if ((network & 0xff00) == 0) {
      // If this is segment 0, than network 0 requires 'special' initialization
      // to ensure that it is recognized as invalid.
      (*segment)[0].network = 0xffff;
    }
  } else {
    broadway_raise("EResourceError",
                   PyString_FromString("Could not allocate segment."), NULL);
  }
  return segment;
}

////
// Return the routing entry for the specified network.
// @return A pointer to the network's route entry.  NULL iff no valid entry
//         exists for the network.
static ROUTING_TABLE_ENTRY_REF entry_for(unsigned short network) {
  ROUTING_TABLE_SEGMENT_REF segment;
  ROUTING_TABLE_ENTRY_REF entry;
  segment = segment_for(network);
  if (segment) {
    entry = &(*segment)[network & 0x00ff];
    if (entry->network == network) {
      return entry;
    }
  }
  errno = ENETUNREACH;
  PyErr_SetFromErrno(PyExc_OSError);
  return NULL;
}

////
// Return the routing entry for an interface directly connected to the
// specified network.
// @return A pointer to the network's route entry.
static ROUTING_TABLE_ENTRY_REF alloc_if(unsigned short network,
                    int socket,
                    int (*send)(int socket,
                            const struct
                            ADDR *source,
                            const struct
                            ADDR *destination,
                            struct
                            BACNET_BUFFER *bnb),
                    int (*recv)(int socket,
                            struct ADDR *source,
                            struct BACNET_BUFFER
                            *bnb),
                    int (*close)(int socket),
                    const struct ADDR *addr,
                    const struct ADDR *broadcast,
               int max_apdu_code) {
  ROUTING_TABLE_SEGMENT_REF segment;
  ROUTING_TABLE_ENTRY_REF entry;
  segment = alloc_segment(network);
  if (segment) {
    entry = &(*segment)[network & 0x00ff];
    entry->network = network;
    entry->local_interface = 1;
    entry->u.interface.socket = socket;
    entry->u.interface.send = send;
    entry->u.interface.recv = recv;
    entry->u.interface.close = close;
    memcpy(&entry->u.interface.addr, addr, sizeof(*addr));
    memcpy(&entry->u.interface.broadcast, broadcast, sizeof(*broadcast));
    entry->u.interface.max_apdu_length_accepted = max_apdu_code; // autoconv from int to unsigned char...
    return entry;
  }
  return NULL;
}

////
// Return the routing entry to the specified remote network.
// @return A pointer to the network's route entry.
static ROUTING_TABLE_ENTRY_REF alloc_route(unsigned short remote_network,
                       unsigned short interface_network,
                       const struct ADDR *router_addr) {
  ROUTING_TABLE_SEGMENT_REF segment;
  ROUTING_TABLE_ENTRY_REF entry;

  entry = entry_for(interface_network);
  if (!entry || !entry->local_interface) {
    // The interface does not exist.
    return NULL;
  }
  segment = alloc_segment(remote_network);
  if (segment) {
    entry = &(*segment)[remote_network & 0x00ff];
    // if this the right place to test for attempting to create a route to an existing interface?
    // if an interface has the same network number as a remote route, this could lead to
    // overwriting the interface's entry and create a closed loop that never terminated
    // with an interface entry.  Since the procedure that looks up the interface
    // for a remote network is recursive, we get a segfault when that happens.
    // if entry is new, local_interface should already be 0.  any other value
    // indicates this entry is already in use.
    if (entry->local_interface > 0) {
        broadway_raise("EInvalidValue",
               PyString_FromFormat("Attempt to set Remote network number: %d to an Interface network number: %d",
                           remote_network, entry->network),
               NULL);
        return NULL;
    }
    entry->network = remote_network;
    entry->local_interface = 0; //redundant?
    entry->u.route.interface_network = interface_network;
    memcpy(&entry->u.route.router_addr, router_addr, sizeof(*router_addr));
    return entry;
  }
  return NULL;
}

int bacnet_add_interface(unsigned short network,
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
          int max_apdu_code) {
  if (alloc_if(network, socket, send, recv, close, source, broadcast, max_apdu_code)) {
    return (int)network;
  }
  return -1;
}

int bacnet_add_route(unsigned short remote_network,
             unsigned short interface_network,
             const struct ADDR *router_addr) {
  if (alloc_route(remote_network, interface_network, router_addr)) {
    return (int)remote_network;
  }
  return -1;
}

int bacnet_del_route(unsigned short network) {
  ROUTING_TABLE_SEGMENT_REF segment;
  ROUTING_TABLE_ENTRY_REF entry;
  segment = segment_for(network);
  if (segment) {
    entry = &(*segment)[network & 0x00ff];
    if (entry) {
      entry->network = !network;
      return 0;
    }
  }
  return -1;
}

int bacnet_network_is_local(unsigned short network) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    return entry->local_interface;
  }
  PyErr_Clear();
  return 0;
}

const struct ADDR *bacnet_router_addr(unsigned short network) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry && !entry->local_interface) {
    return &entry->u.route.router_addr;
  }
  return NULL;
}

const struct ADDR *bacnet_interface_addr(unsigned short network) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    if (entry->local_interface) {
      return &entry->u.interface.addr;
    } else {
      return bacnet_interface_addr(entry->u.route.interface_network);
    }
  }
  return NULL;
}

const struct ADDR *bacnet_interface_broadcast(unsigned short network) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    if (entry->local_interface) {
      return &entry->u.interface.broadcast;
    } else {
      return bacnet_interface_broadcast(entry->u.route.interface_network);
    }
  }
  return NULL;
}

int bacnet_interface_socket(unsigned short network) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    if (entry->local_interface) {
      return entry->u.interface.socket;
    } else {
      return bacnet_interface_socket(entry->u.route.interface_network);
    }
  }
  return -1;
}

int bacnet_max_apdu(unsigned short network) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    if (entry->local_interface) {
      return entry->u.interface.max_apdu_length_accepted;
    } else {
      return bacnet_max_apdu(entry->u.route.interface_network);
    }
  }
  return -1;
}

static int invalid_network_send(int socket,
                const struct ADDR *source,
                const struct ADDR *destination,
                struct BACNET_BUFFER *bnb)
{
  PyErr_Clear();
  errno = ENETUNREACH;
  PyErr_SetFromErrno(PyExc_OSError);
  return -1;
}

int (*bacnet_interface_send(unsigned short network))
     (int socket,
      const struct ADDR *source,
      const struct ADDR *destination,
      struct BACNET_BUFFER *bnb) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    if (entry->local_interface) {
      return entry->u.interface.send;
    } else {
      return bacnet_interface_send(entry->u.route.interface_network);
    }
  }
  return invalid_network_send;
}

static int invalid_network_recv(int socket,
                struct ADDR *source,
                struct BACNET_BUFFER *bnb)
{
  PyErr_Clear();
  errno = ENETUNREACH;
  PyErr_SetFromErrno(PyExc_OSError);
  return -1;
}

int (*bacnet_interface_recv(unsigned short network))
     (int socket, struct ADDR *source, struct BACNET_BUFFER *bnb) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    if (entry->local_interface) {
      return entry->u.interface.recv;
    } else {
      return bacnet_interface_recv(entry->u.route.interface_network);
    }
  }
  return invalid_network_recv;
}

static int invalid_network_close(int socket)
{
  PyErr_Clear();
  errno = ENETUNREACH;
  PyErr_SetFromErrno(PyExc_OSError);
  return -1;
}

int (*bacnet_interface_close(unsigned short network))(int socket) {
  ROUTING_TABLE_ENTRY_REF entry;
  entry = entry_for(network);
  if (entry) {
    if (entry->local_interface) {
      return entry->u.interface.close;
    } else {
      return invalid_network_close;
    }
  }
  return invalid_network_close;
}

static int dump_line(FILE *stream,
                     const char *header, const unsigned char *pdump, int ndump)
{
#define cpl 16
  int i, n;
  fputs(header, stream);
  fputc('|', stream);
  n = ndump;
  for (i=0; i<cpl; i++, n--) {
    if (n > 0 && isprint(pdump[i])) {
      fputc(pdump[i], stream);
    } else {
      fputc(' ', stream);
    }
  }
  fputs("| ", stream);
  n = (ndump < cpl) ? ndump : cpl ;
  for (i=0; i<n; i++) {
    fprintf(stream, " %02x", pdump[i]);
  }
  fputc('\n', stream);
  return n;
}

static void bacnet_dump(const char *header,
                        unsigned short network,
                        const struct ADDR *source,
                        const struct ADDR *dest,
                        const struct BACNET_BUFFER *buffer)
{
  int i;
  unsigned char *pdump;
  int ndump;

  fprintf(stdout, "%s network=%d\n", header, network);
  if (source != NULL) {
    fprintf(stdout, "%s source= ", header);
    for (i=0; i<source->length; i++) {
      fprintf(stdout, "%02x ", source->address[i]);
    }
    fputc('\n', stdout);
  }
  if (dest != NULL) {
    fprintf(stdout, "%s dest=   ", header);
    for (i=0; i<dest->length; i++) {
      fprintf(stdout, "%02x ", dest->address[i]);
    }
    fputc('\n', stdout);
  }
  pdump = (unsigned char *)buffer->p_npci;
  ndump = buffer->s_data + ((unsigned char *)buffer->p_data - pdump);
  while (ndump > 0) {
    i = dump_line(stdout, header, pdump, ndump);
    pdump += i;
    ndump -= i;
  }
}

// All those helpful helper functions...

static unsigned short npci_dnet(struct BACNET_BUFFER *bnb) {
  int offset;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.dnet;
  if (offset >= 0) {
    return ntohs(*(unsigned short*)(bnb->p_npci->data+offset));
  }
  return 0;
}

static unsigned char npci_dlen(struct BACNET_BUFFER *bnb) {
  int offset;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.dlen;
  if (offset >= 0) {
    return *(unsigned char*)(bnb->p_npci->data+offset);
  }
  return 0;
}

static int npci_dadr(struct BACNET_BUFFER *bnb, struct ADDR *dadr) {
  int offset;
  int dlen;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.dadr;
  if (offset >= 0) {
    dlen = npci_dlen(bnb);
    if (dlen > sizeof dadr->address) {
      dadr->length = 0;
      memset(dadr->address, 0, sizeof dadr->address);
      return 0;
    }
    memcpy(dadr->address, bnb->p_npci->data+offset, dlen);
  } else {
    dadr->length = 0;
  }
  return dadr->length;
}

static unsigned short npci_snet(struct BACNET_BUFFER *bnb) {
  int offset;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.snet;
  if (offset >= 0) {
    return ntohs(*(unsigned short*)(bnb->p_npci->data+offset));
  }
  return 0;
}

static unsigned char npci_slen(struct BACNET_BUFFER *bnb) {
  int offset;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.slen;
  if (offset >= 0) {
    return *(unsigned char*)(bnb->p_npci->data+offset);
  }
  return 0;
}

static int npci_sadr(struct BACNET_BUFFER *bnb, struct ADDR *sadr) {
  int offset;
  int slen;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.sadr;
  if (offset >= 0) {
    slen = npci_slen(bnb);
    if (slen > sizeof sadr->address) {
      sadr->length = 0;
      memset(sadr->address, 0, sizeof sadr->address);
      return 0;
    }
    memcpy(sadr->address, bnb->p_npci->data+offset, slen);
  } else {
    sadr->length = 0;
  }
  return sadr->length;
}

static unsigned char npci_hop_count(struct BACNET_BUFFER *bnb) {
  int offset;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.hop_count;
  if (offset >= 0) {
    return *(unsigned char*)(bnb->p_npci->data+offset);
  }
  return 0;
}

static enum NET_MSG_TYPE npci_msg_type(struct BACNET_BUFFER *bnb) {
  int offset;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.msg_type;
  if (offset >= 0) {
    return *(enum NET_MSG_TYPE*)(bnb->p_npci->data+offset);
  }
  return NONE;
}

static unsigned short npci_vendor_id(struct BACNET_BUFFER *bnb) {
  int offset;
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  offset = bnb->npci_offset.vendor_id;
  if (offset >= 0) {
    return ntohs(*(unsigned short*)(bnb->p_npci->data+offset));
  }
  return 0;
}

unsigned short npci_length(struct BACNET_BUFFER *bnb) {
  return (unsigned short)( bnb->p_data - (void*)bnb->p_npci);
}

static struct APCI *npci_apci(struct BACNET_BUFFER *bnb) {
  if (!bnb->npci_offset.valid) {
    bacnet_decode_npci_data(bnb);
  }
  return (struct APCI *)bnb->p_data;
}

static void *npci_data(struct BACNET_BUFFER *bnb) {
  return (void *)npci_apci(bnb);
}

////
// Decodes a BACNET_BUFFER, setting up all the offsets used to find
// the NPCI data and the APCI.
// @note bnb->p_npci must point to the beginning of the NPCI data,
//       bnb->p_data should point to bnb->p_npci and bnb->s_data
//       MUST be set to the length of the message FROM BNB->P_NPCI.
void bacnet_decode_npci_data(struct BACNET_BUFFER *bnb) {
  int offset;
  unsigned char dlen;
  struct BACNET_NPCI scratch_npci;
  struct BACNET_NPCI_OFFSET *o = &bnb->npci_offset;
  memset(o, (unsigned char)-1, sizeof(*o));
  offset = 0;
  if (bnb->p_npci->dspec) {
    o->dnet = 0;
    offset += 2;
    o->dlen = offset;
    offset += 1;
    dlen = *(bnb->p_npci->data+o->dlen);
    if (dlen) {
      o->dadr = offset;
      offset += dlen;
    }
  }
  if (bnb->p_npci->sspec) {
    o->snet = offset;
    offset += 2;
    o->slen = offset;
    offset += 1;
    o->sadr = offset;
    offset += *(bnb->p_npci->data+o->slen);
  }
  if (bnb->p_npci->dspec) {
    o->hop_count = offset;
    offset += 1;
  }
  if (bnb->p_npci->network_msg) {
    o->msg_type = offset;
    offset += 1;
  }
  if (bnb->p_npci->network_msg && (bnb->p_npci->data[o->msg_type] >= 0x80)) {
    o->vendor_id = offset;
    offset += 2;
  }
  if (!bnb->p_npci->network_msg) {
    o->apci = offset;
    bnb->apci.unknown = (struct UNKNOWN_PDU *)(bnb->p_npci->data+offset);
    // @note Create a fake struct BACNET_NPCI for use by sizeof_apci.  This is
    //       required because it appears the decoding of a BACnet-Complex-ACK-PDU
    //       is based on the NPCI's data_expecting_reply bit, not on the the
    //       APDU's segmented-message bit as per ASHREA 135-1995 20.1.5.4-5.
    memset(&scratch_npci, 0, sizeof scratch_npci);
    scratch_npci.data_expecting_reply = bnb->p_npci->data_expecting_reply;
    offset += sizeof_apci(bnb->apci.unknown, &scratch_npci);
  } else {
    bnb->apci.unknown = NULL;
  }
  o->data = offset;
  o->valid = 1;
  // Adjust p_data and s_data accordingly.
  bnb->p_data = (bnb->p_npci->data+o->data);
  bnb->s_data = bnb->s_data - (bnb->p_data - (void*)bnb->p_npci);
  return;
}

////
// Prepend an NPCI header to a BACNET_BUFFER.  Uses a public BACNET_NPCI
// structure to create and prepend the variable length BACnet NCPI data
// (struct PACKED_NPCI) to a BACNET_BUFFER.  Updates the BACNET_BUFFER's
// p_npci pointer to reference the prepended header.  Sets the BACNET_BUFFER's
// p_llc and p_mac pointers to NULL (since they MUST precede the NPCI header.
//
// @param buffer The BACNET_BUFFER to prepend the NPCI data to.
// @param npci The public BACNET_NPCI structure describing how to construct
//             the NPCI message header.
// @note The BACNET_BUFFER's p_data pointer MUST be valid when this function
//       is called.  If it is NOT a network message, then the buffer's
//       apci.p_start pointer must also be set.  apci.p_start is calculated by
//       prepend_apci().
// @fixme Validate the <code>npci</code>, raise an exception if there is
//        non-zero data that will not be sent.
static int prepend_npci(struct BACNET_BUFFER *buffer,
            const struct BACNET_NPCI *npci) {
  int length;
  struct {
    struct PACKED_NPCI npci;
    unsigned char pad[32];
  } packed;
  unsigned char *p_data = packed.npci.data;
  memset(&packed, 0, sizeof packed);
  memcpy(&packed, npci, 2); // Copy version and control byte.
  length = 2;
  // dnet      -    2 optional octets.
  // dlen      -    1 optional octet.
  // dadr      - dlen optional octets.
  if (npci->dspec) {
    *(unsigned short*)p_data = htons(npci->dnet);
    length += 2;
    p_data += 2;
    *p_data = npci->dlen;
    length += 1;
    p_data += 1;
    memcpy(p_data, npci->dadr, npci->dlen);
    length += npci->dlen;
    p_data += npci->dlen;
  }
  // snet      -    2 optional octets.
  // slen      -    1 optional octet.
  // sadr      - slen optional octets.
  if (npci->sspec) {
    *(unsigned short*)p_data = htons(npci->snet);
    length += 2;
    p_data += 2;
    *p_data = npci->slen;
    length += 1;
    p_data += 1;
    memcpy(p_data, npci->sadr, npci->slen);
    length += npci->slen;
    p_data += npci->slen;
  }
  // hop_count -    1 optional octet.
  if (npci->dspec) {
    *p_data = npci->hop_count;
    length += 1;
    p_data += 1;
  }
  // msg_type  -    1 optional octet.
  if (npci->network_msg) {
    *p_data = npci->msg_type;
    length += 1;
    p_data += 1;
  }
  // vendor_id -    2 optional octets.
  if (npci->network_msg && (npci->msg_type >= 0x80)) {
    *(unsigned short*)p_data = htons(npci->vendor_id);
    length += 2;
    p_data += 2;
  }
  // Calculate the NPCI pointer in the BACNET_BUFFER and copy in the
  // 'packed' NPCI data.
  if (npci->network_msg) {
    buffer->p_npci = (struct PACKED_NPCI *)(buffer->p_data-length);
  } else {
    buffer->p_npci = (struct PACKED_NPCI *)(buffer->apci.p_start-length);
  }
  memcpy(buffer->p_npci, &packed, length);
  // Since we are constructing the BACNET_BUFFER 'backwards', (first we
  // copied the data, now we've prepended the NPCI) the LLC and MAC
  // pointers can NOT be valid at this time.
  buffer->p_llc = NULL;
  buffer->p_mac = NULL;
  return 0;
}

static int encode_segmented_confirmed_request(struct UNKNOWN_PDU *target,
                                              const struct BACNET_APCI *source)
{
  struct SEGMENTED_CONFIRMED_REQUEST_PDU *pdu =
    (struct SEGMENTED_CONFIRMED_REQUEST_PDU *)target;
  pdu->segmented_response_accepted = source->segmented_response_accepted;
  pdu->more_follows = source->more_follows;
  pdu->segmented_message = source->segmented_message;
  pdu->pdu_type = source->pdu_type;
  pdu->max_apdu_length_accepted = source->max_apdu_length_accepted;
  pdu->invoke_id = source->invoke_id;
  pdu->sequence_number = source->sequence_number;
  pdu->proposed_window_size = source->window_size;
  pdu->service_choice = source->choice;
  return 0;
}

static int encode_confirmed_request(struct UNKNOWN_PDU *target,
                                    const struct BACNET_APCI *source) {
  struct CONFIRMED_REQUEST_PDU *pdu = (struct CONFIRMED_REQUEST_PDU *)target;
  pdu->segmented_response_accepted = source->segmented_response_accepted;
  pdu->more_follows = source->more_follows;
  pdu->segmented_message = source->segmented_message;
  pdu->pdu_type = source->pdu_type;
  pdu->max_apdu_length_accepted = source->max_apdu_length_accepted;
  pdu->invoke_id = source->invoke_id;
  pdu->service_choice = source->choice;
  return 0;
}

static int encode_unconfirmed_request(struct UNKNOWN_PDU *target,
                                      const struct BACNET_APCI *source) {
  struct UNCONFIRMED_REQUEST_PDU *pdu =
    (struct UNCONFIRMED_REQUEST_PDU *)target;
  pdu->pdu_type = source->pdu_type;
  pdu->service_choice = source->choice;
  return 0;
}

static int encode_segmented_complex_ack(struct UNKNOWN_PDU *target,
                                        const struct BACNET_APCI *source) {
  struct SEGMENTED_COMPLEX_ACK_PDU *pdu =
    (struct SEGMENTED_COMPLEX_ACK_PDU *)target;
  pdu->more_follows = source->more_follows;
  pdu->segmented_message = source->segmented_message;
  pdu->pdu_type = source->pdu_type;
  pdu->invoke_id = source->invoke_id;
  pdu->sequence_number = source->sequence_number;
  pdu->proposed_window_size = source->window_size;
  pdu->service_ack_choice = source->choice;
  return 0;
}

static int encode_simple_ack(struct UNKNOWN_PDU *target,
                             const struct BACNET_APCI *source) {
  struct SIMPLE_ACK_PDU *pdu = (struct SIMPLE_ACK_PDU *)target;
  pdu->pdu_type = source->pdu_type;
  pdu->service_ack_choice = source->choice;
  pdu->invoke_id = source->invoke_id;
  return 0;
}

static int encode_complex_ack(struct UNKNOWN_PDU *target,
                              const struct BACNET_APCI *source) {
  struct COMPLEX_ACK_PDU *pdu = (struct COMPLEX_ACK_PDU *)target;
  pdu->pdu_type = source->pdu_type;
  pdu->invoke_id = source->invoke_id;
  pdu->service_ack_choice = source->choice;
  return 0;
}

static int encode_segment_ack(struct UNKNOWN_PDU *target,
                              const struct BACNET_APCI *source) {
  struct SEGMENT_ACK_PDU *pdu = (struct SEGMENT_ACK_PDU *)target;
  pdu->server = source->server;
  pdu->negative_ack = source->negative_ack;
  pdu->pdu_type = source->pdu_type;
  pdu->invoke_id = source->invoke_id;
  pdu->sequence_number = source->sequence_number;
  pdu->actual_window_size = source->window_size;
  return 0;
}

static int encode_error(struct UNKNOWN_PDU *target,
                        const struct BACNET_APCI *source) {
  struct ERROR_PDU *pdu = (struct ERROR_PDU *)target;
  pdu->pdu_type = source->pdu_type;
  pdu->invoke_id = source->invoke_id;
  pdu->error_choice = source->choice;
  return 0;
}

static int encode_reject(struct UNKNOWN_PDU *target,
                         const struct BACNET_APCI *source) {
  struct REJECT_PDU *pdu = (struct REJECT_PDU *)target;
  pdu->pdu_type = source->pdu_type;
  pdu->invoke_id = source->invoke_id;
  pdu->reject_reason = source->reason;
  return 0;
}

static int encode_abort(struct UNKNOWN_PDU *target,
                        const struct BACNET_APCI *source) {
  struct ABORT_PDU *pdu = (struct ABORT_PDU *)target;
  pdu->server = source->server;
  pdu->pdu_type = source->pdu_type;
  pdu->invoke_id = source->invoke_id;
  pdu->abort_reason = source->reason;
  return 0;
}

static int encode_apci(struct UNKNOWN_PDU *target,
               const struct BACNET_NPCI *npci,
               const struct BACNET_APCI *source) {
  switch (source->pdu_type) {
  case CONFIRMED_REQUEST_TYPE:
    if (source->segmented_message) {
      return encode_segmented_confirmed_request(target, source);
    }
    return encode_confirmed_request(target, source);
  case UNCONFIRMED_REQUEST_TYPE:
    return encode_unconfirmed_request(target, source);
  case SIMPLE_ACK_TYPE:
    return encode_simple_ack(target, source);
  case COMPLEX_ACK_TYPE:
    if (source->segmented_message || npci->data_expecting_reply) {
      // @fixme According to ASHRAE 135-1995, the test should only be
      //        for source->segmented_message.  But the Trane BCU specifies
      //        sequence-number and proposed-window-size even though
      //        segmented-message == 0.
      return encode_segmented_complex_ack(target, source);
    }
    return encode_complex_ack(target, source);
  case SEGMENT_ACK_TYPE:
    return encode_segment_ack(target, source);
  case ERROR_TYPE:
    return encode_error(target, source);
  case REJECT_TYPE:
    return encode_reject(target, source);
  case ABORT_TYPE:
    return encode_abort(target, source);
  }
  return -1;
}

static int sizeof_apci(const struct UNKNOWN_PDU *unknown,
               const struct BACNET_NPCI *npci) {
  switch (unknown->pdu_type) {
  case CONFIRMED_REQUEST_TYPE:
    if (unknown->segmented_message) {
      return sizeof(struct SEGMENTED_CONFIRMED_REQUEST_PDU);
    }
    return sizeof(struct CONFIRMED_REQUEST_PDU);
  case UNCONFIRMED_REQUEST_TYPE:
    return sizeof(struct UNCONFIRMED_REQUEST_PDU);
  case SIMPLE_ACK_TYPE:
    return sizeof(struct SIMPLE_ACK_PDU);
  case COMPLEX_ACK_TYPE:
    if (unknown->segmented_message || npci->data_expecting_reply) {
      // @fixme According to ASHRAE 135-1995, the test should only be
      //        for source->segmented_message.  But the Trane BCU specifies
      //        sequence-number and proposed-window-size even though
      //        segmented-message == 0.
      return sizeof(struct SEGMENTED_COMPLEX_ACK_PDU);
    }
    return sizeof(struct COMPLEX_ACK_PDU);
  case SEGMENT_ACK_TYPE:
    return sizeof(struct SEGMENT_ACK_PDU);
  case ERROR_TYPE:
    return sizeof(struct ERROR_PDU);
  case REJECT_TYPE:
    return sizeof(struct REJECT_PDU);
  case ABORT_TYPE:
    return sizeof(struct ABORT_PDU);
  }
  return 0;
}

////
// Prepend the APCI header to a BACNET_BUFFER.  Uses a public BACNET_APCI
// structure to create and prepend the variable length BACnet APCI header
// to a BACNET_BUFFER.  Updates the BACNET_BUFFER's APCI pointers (apci.*)
// to reference the prepended header.  Sets the BACNET_BUFFER's p_npci,
// p_llc and p_mac pointers to NULL (since they MUST precede the APCI header.
//
// @param buffer The BACNET_BUFFER to prepend the APCI header to.
// @param apci The public BACNET_APCI structure describing how to construct
//             the APCI header.
// @note The BACNET_BUFFER's p_data pointer MUST be valid when this function
//       is called.
int prepend_apci(struct BACNET_BUFFER *buffer,
                 const struct BACNET_NPCI *npci,
                 const struct BACNET_APCI *apci) {
  struct UNKNOWN_PDU unknown;
  int length;
  if (!apci) {
    return 0;
  }
  // Calculate where the APCI header needs to start and zero it out.
  unknown.pdu_type = apci->pdu_type;
  unknown.more_follows = apci->more_follows;
  unknown.segmented_message = apci->segmented_message;
  length = sizeof_apci(&unknown, npci);
  buffer->apci.p_start = buffer->p_data - length;
  memset(buffer->apci.p_start, 0, length);

  // Encode the specific APCI header into the buffer.
  encode_apci(buffer->apci.unknown, npci, apci);

  // Since we are constructing the BACNET_BUFFER 'backwards', (first we
  // copied the data, now we've prepended the APCI header) the LLC, MAC and
  // NPCI pointers can NOT be valid at this time.
  buffer->p_llc = NULL;
  buffer->p_mac = NULL;
  buffer->p_npci = NULL;
  return 0;
}

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
struct BACNET_BUFFER *encode_new_buffer(const struct BACNET_NPCI *npci,
                    const struct BACNET_APCI* apci,
                    void *data,
                    int length) {
  struct BACNET_BUFFER *buffer;

  // Allocate a new buffer that is big enough for all of the data.
  buffer = bacnet_alloc_buffer(length);
  if (!buffer) {
    PyErr_NoMemory();
    return NULL;
  }
  // Copy the data to the BACNET_BUFFER.
  memcpy(buffer->p_data, data, length);
  buffer->s_data = length;

  if (apci != NULL && !npci->network_msg) {
    // Add the APCI header.
    if (prepend_apci(buffer, npci, apci) == -1) {
      bacnet_free_buffer(buffer);
      return NULL;
    }
  }
  // Add the BACnet Network control data.
  if (prepend_npci(buffer, npci) == -1) {
    bacnet_free_buffer(buffer);
    return NULL;
  }
  return buffer;
}

////
// Send data to a BACnet device.
//
// @param network The BACnet device's network.
// @param dest The BACnet device's address.  If <code>dest->dlen</code> == 0,
//             Then the message is broadcast to all devices on the
//             <code>network</code>.
// @param npci Describes the NPCI information for the message.
// @param apci Describes the APCI header (everything upto, but not
//             including, the tag data).  Should be NULL for network
//             messages (messages where ncpi.network_msg == 1).
// @param data The data to send to the device.
// @param length The length of the data to send.
// @todo  Handle segmenting the messages.
int bacnet_send_message(unsigned short network,
                        const struct ADDR *dest,
                        const struct BACNET_NPCI *npci,
                        struct BACNET_APCI* apci, // shp: rmvd 'const' to allow setting of max_apdu_length_accepted bitfield
                        void *data,
                        int length,
                        long debug_level) {
  struct BACNET_NPCI temp_npci;
  struct BACNET_BUFFER *buffer;
  int socket;
  const struct ADDR *source;
  int ret, max_apdu_code = 0;

  if (!bacnet_network_is_local(network)) {
    temp_npci = *npci;
    temp_npci.dspec = 1;
    temp_npci.dnet = network;
    temp_npci.dlen = dest->length;
    temp_npci.hop_count = 255; //fgd
    memcpy(temp_npci.dadr, dest->address, dest->length);
    npci = &temp_npci;
    dest = bacnet_router_addr(network);
    if (dest == NULL) {
      return -1;
    }
  }

  max_apdu_code = bacnet_max_apdu(network);
  if(max_apdu_code < 0)
     return max_apdu_code;

  apci->max_apdu_length_accepted = max_apdu_code;

  buffer = encode_new_buffer(npci, apci, data, length);

  socket = bacnet_interface_socket(network);
  if (socket < 0) {
    return socket;
  }
  source = bacnet_interface_addr(network);
  if (!source) {
    return -1;
  }
  if (!dest || !dest->length) {
    dest = bacnet_interface_broadcast(network);
  }
  if (debug_level > 0) {
    bacnet_dump("sending:", network, source, dest, buffer);
  }
  ret = bacnet_interface_send(network)(socket, source, dest, buffer);
  bacnet_free_buffer(buffer);
  return ret;
}

static int decode_segmented_confirmed_request(struct BACNET_APCI *target,
                                              const struct UNKNOWN_PDU *source)
{
  struct SEGMENTED_CONFIRMED_REQUEST_PDU *pdu =
    (struct SEGMENTED_CONFIRMED_REQUEST_PDU *)source;
  target->segmented_response_accepted = pdu->segmented_response_accepted;
  target->more_follows = pdu->more_follows;
  target->segmented_message = pdu->segmented_message;
  target->pdu_type = pdu->pdu_type;
  target->max_apdu_length_accepted = pdu->max_apdu_length_accepted;
  target->invoke_id = pdu->invoke_id;
  target->sequence_number = pdu->sequence_number;
  target->window_size = pdu->proposed_window_size;
  target->choice = pdu->service_choice;
  return 0;
}

static int decode_confirmed_request(struct BACNET_APCI *target,
                                    const struct UNKNOWN_PDU *source) {
  struct CONFIRMED_REQUEST_PDU *pdu = (struct CONFIRMED_REQUEST_PDU *)source;
  target->segmented_response_accepted = pdu->segmented_response_accepted;
  target->more_follows = pdu->more_follows;
  target->segmented_message = pdu->segmented_message;
  target->pdu_type = pdu->pdu_type;
  target->max_apdu_length_accepted = pdu->max_apdu_length_accepted;
  target->invoke_id = pdu->invoke_id;
  target->choice = pdu->service_choice;
  return 0;
}

static int decode_unconfirmed_request(struct BACNET_APCI *target,
                                      const struct UNKNOWN_PDU *source) {
  struct UNCONFIRMED_REQUEST_PDU *pdu =
    (struct UNCONFIRMED_REQUEST_PDU *)source;
  target->pdu_type = pdu->pdu_type;
  target->choice = pdu->service_choice;
  return 0;
}

static int decode_segmented_complex_ack(struct BACNET_APCI *target,
                                        const struct UNKNOWN_PDU *source) {
  struct SEGMENTED_COMPLEX_ACK_PDU *pdu =
    (struct SEGMENTED_COMPLEX_ACK_PDU *)source;
  target->more_follows = pdu->more_follows;
  target->segmented_message = pdu->segmented_message;
  target->pdu_type = pdu->pdu_type;
  target->invoke_id = pdu->invoke_id;
  target->sequence_number = pdu->sequence_number;
  target->window_size = pdu->proposed_window_size;
  target->choice = pdu->service_ack_choice;
  return 0;
}

static int decode_simple_ack(struct BACNET_APCI *target,
                             const struct UNKNOWN_PDU *source) {
  struct SIMPLE_ACK_PDU *pdu = (struct SIMPLE_ACK_PDU *)source;
  target->pdu_type = pdu->pdu_type;
  target->choice = pdu->service_ack_choice;
  target->invoke_id = pdu->invoke_id;
  return 0;
}

static int decode_complex_ack(struct BACNET_APCI *target,
                              const struct UNKNOWN_PDU *source) {
  struct COMPLEX_ACK_PDU *pdu = (struct COMPLEX_ACK_PDU *)source;
  target->pdu_type = pdu->pdu_type;
  target->invoke_id = pdu->invoke_id;
  target->choice = pdu->service_ack_choice;
  return 0;
}

static int decode_segment_ack(struct BACNET_APCI *target,
                              const struct UNKNOWN_PDU *source) {
  struct SEGMENT_ACK_PDU *pdu = (struct SEGMENT_ACK_PDU *)source;
  target->server = pdu->server;
  target->negative_ack = pdu->negative_ack;
  target->pdu_type = pdu->pdu_type;
  target->invoke_id = pdu->invoke_id;
  target->sequence_number = pdu->sequence_number;
  target->window_size = pdu->actual_window_size;
  return 0;
}

static int decode_error(struct BACNET_APCI *target,
                        const struct UNKNOWN_PDU *source) {
  struct ERROR_PDU *pdu = (struct ERROR_PDU *)source;
  target->pdu_type = pdu->pdu_type;
  target->invoke_id = pdu->invoke_id;
  target->choice = pdu->error_choice;
  return 0;
}

static int decode_reject(struct BACNET_APCI *target,
                         const struct UNKNOWN_PDU *source) {
  struct REJECT_PDU *pdu = (struct REJECT_PDU *)source;
  target->pdu_type = pdu->pdu_type;
  target->invoke_id = pdu->invoke_id;
  target->reason = pdu->reject_reason;
  return 0;
}

static int decode_abort(struct BACNET_APCI *target,
                        const struct UNKNOWN_PDU *source) {
  struct ABORT_PDU *pdu = (struct ABORT_PDU *)source;
  target->server = pdu->server;
  target->pdu_type = pdu->pdu_type;
  target->invoke_id = pdu->invoke_id;
  target->reason = pdu->abort_reason;
  return 0;
}

static int decode_apci(struct BACNET_APCI *target,
               const struct BACNET_NPCI *npci,
               const struct UNKNOWN_PDU *source) {
  switch (source->pdu_type) {
  case CONFIRMED_REQUEST_TYPE:
    if (source->segmented_message) {
      return decode_segmented_confirmed_request(target, source);
    }
    return decode_confirmed_request(target, source);
  case UNCONFIRMED_REQUEST_TYPE:
    return decode_unconfirmed_request(target, source);
  case SIMPLE_ACK_TYPE:
    return decode_simple_ack(target, source);
  case COMPLEX_ACK_TYPE:
    if (source->segmented_message || npci->data_expecting_reply) {
      // @fixme According to ASHRAE 135-1995, the test should only be
      //        for source->segmented_message.  But the Trane BCU specifies
      //        sequence-number and proposed-window-size even though
      //        segmented-message == 0.
      return decode_segmented_complex_ack(target, source);
    }
    return decode_complex_ack(target, source);
  case SEGMENT_ACK_TYPE:
    return decode_segment_ack(target, source);
  case ERROR_TYPE:
    return decode_error(target, source);
  case REJECT_TYPE:
    return decode_reject(target, source);
  case ABORT_TYPE:
    return decode_abort(target, source);
  }
  return -1;
}

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
//        error condition.
int decode_existing_buffer(struct BACNET_BUFFER *buffer,
               struct BACNET_NPCI* npci,
               struct BACNET_APCI* apci,
               void **ppdata) {
  struct ADDR addr;
  // Fill in public BACNET_NCPI data from the message's NCPI.
  if (npci) {
    memset(npci, 0, sizeof(*npci));
    // Version and control.
    memcpy(npci, buffer->p_npci, 2);
    npci->dnet = npci_dnet(buffer);
    npci->dlen = npci_dlen(buffer);
    npci_dadr(buffer, &addr);
    memcpy(npci->dadr, addr.address, npci->dlen);
    npci->snet = npci_snet(buffer);
    npci->slen = npci_slen(buffer);
    npci_sadr(buffer, &addr);
    memcpy(npci->sadr, addr.address, npci->slen);
    npci->hop_count = npci_hop_count(buffer);
    npci->msg_type = npci_msg_type(buffer);
    npci->vendor_id = npci_vendor_id(buffer);
  }
  if (apci) {
    memset(apci, 0, sizeof(*apci));
    if (npci->network_msg) {
      apci->invalid_apci = 1;
    } else {
      decode_apci(apci, npci, buffer->apci.unknown);
    }
  }
  if (ppdata) {
    *ppdata = buffer->p_data;
  }
  return buffer->s_data;
}

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
// @param maxlen The maximum number of bytes to copy to <code>data</code>.
// @return The number of bytes received beyond the NPCI and APCI structures.
//         If the extra data exceeded <code>maxlen</code>, then only maxlen
//         bytes are copied to <code>data</code>.  It is up to the caller to
//         check that the returned value exceeded <code>maxlen</code> and
//         that the data was truncated.<p>
//         If an error occurs, -1 is returned and an appropriate Python
//         error condition is set.
int bacnet_recv_message(unsigned short network,
                        struct ADDR *source,
                        struct BACNET_NPCI* npci,
                        struct BACNET_APCI* apci,
                        void *data, int maxlen,
                        long debug_level) {
  struct BACNET_BUFFER *buffer;
  int socket;
  int length;
  void *pdata;

  buffer = bacnet_alloc_buffer(1600);
  if (!buffer) {
    return -1;
  }
  socket = bacnet_interface_socket(network);
  length = bacnet_interface_recv(network)(socket, source, buffer);
  if (length < 0) {
    bacnet_free_buffer(buffer);
    return -1;
  }
  length = decode_existing_buffer(buffer, npci, apci, &pdata);
  if (length < 0) {
    bacnet_free_buffer(buffer);
    return -1;
  }
  if (length > maxlen) {
    memcpy(data, buffer->p_data, maxlen);
  } else {
    memcpy(data, pdata, length);
  }
  if (debug_level > 0) {
    bacnet_dump("recving:", network, source, NULL, buffer);
  }
  bacnet_free_buffer(buffer);
  return length;
}

////
// Close the interface attached to a specific <code>network</code>.
//
// @param network The BACnet network to close.
int bacnet_close(unsigned short network) {
  int socket;
  int ret;

  socket = bacnet_interface_socket(network);
  if (socket < 0) {
    // No such network.
    return socket;
  }
  ret = bacnet_interface_close(network)(socket);
  return ret;
}

// Buffer management helpers.
int bacnet_buffer_size(struct BACNET_BUFFER *bnb) {
  return bnb->size;
}

int bacnet_max_data_size(const struct BACNET_BUFFER *bnb) {
  static struct BACNET_BUFFER *p = NULL;
  static const int extra_bits = (unsigned char*)p->_data - (unsigned char*)p;
  return bnb->size - extra_bits;
}

void bacnet_reset_buffer(struct BACNET_BUFFER *bnb) {
  memset(&bnb->npci_offset, -1, sizeof bnb->npci_offset);
  bnb->npci_offset.valid = 0;
  bnb->p_mac = NULL;
  bnb->p_llc = NULL;
  bnb->p_npci = NULL;
  bnb->apci.unknown = NULL;
  memset(bnb->pad, 0, sizeof bnb->pad);
  bnb->p_data = bnb->_data;
  bnb->s_data = 0;
}

static void init_buffer(struct BACNET_BUFFER *bnb, int allocated, int size) {
  bnb->allocated = allocated;
  bnb->valid = 1;
  bacnet_reset_buffer(bnb);
  bnb->size = size;
}

struct BACNET_BUFFER *bacnet_alloc_buffer(int data_size) {
  int size = sizeof(struct BACNET_BUFFER) + data_size;
  struct BACNET_BUFFER *buffer = (struct BACNET_BUFFER *)malloc(size);
  if (buffer) {
    init_buffer(buffer, 1, size);
  }
  return buffer;
}

void bacnet_free_buffer(struct BACNET_BUFFER *bnb) {
  if (bnb && bnb->valid && bnb->allocated) {
    bnb->valid = 0;
    bnb->allocated = 0;
    free(bnb);
  }
}

static char __doc__test_assert_exception[] = "\n"
"##\n"
"# test_assert_exception is a hook to test the broadway_assert_exception_set\n"
"# function.\n"
"#\n"
"# raises EInternalError.\n"
"#";
static PyObject *test_assert_exception(PyObject *self, PyObject *args)
{
  broadway_assert_exception_set("lib.c", __LINE__);
  return NULL;
}

void initlib(void)
{
  static PyMethodDef module_functions[] = {
  {"test_assert_exception", test_assert_exception,
   METH_VARARGS, __doc__test_assert_exception},
    {NULL}
  };
  // Get a refererence to array.ArrayType.
  PyObject *array = PyImport_ImportModule("array");
  if (array) {
    ArrayType = (PyTypeObject*)PyObject_GetAttrString(array, "ArrayType");
    Py_DECREF(array);
  }
  // Create the new module definition.
  Py_InitModule("lib", module_functions);
  if (!ArrayType) {
    broadway_raise("EInternal",
           PyString_FromString("Failed to load the array module"),
           NULL);
  }
  return;
}
