/*
Copyright (C) 2002 2008 2010 2011 Cisco Systems

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
#include <Python.h>

#include <stdio.h>
#include <dlfcn.h>

#include "_lib.h"

void (*broadway_get_buffer)(const unsigned char **buffer, UINT32 *length,
			    PyObject *object);

PyObject *(*broadway_raise)(char *name, PyObject *args, PyObject *keywords);
PyObject *(*broadway_exception_from_name)(char *name);
void (*broadway_raise_parse_failure)(const char *msg, unsigned char value);
void (*broadway_raise_invalid_ulong)(unsigned long value, const char *name,
				     const char *msg);
void (*broadway_raise_invalid_object)(PyObject *value, const char *name,
				      const char *msg);
void (*broadway_assert_exception_set)(const char *filename, int lineno);
int (*is_buffer)(PyObject *object);
int (*new_socket_entry)(int direct, int broadcast, int limited_broadcast, 
            int network,
			const struct ADDR *interface_address,
			const struct ADDR *broadcast_address);
struct SOCKET_MAP *(*del_socket_entry)(int entry_id);
struct SOCKET_MAP *(*get_socket_entry)(int entry_id);
int (*bacnet_add_interface)(unsigned short network,
			    int socket,
			    int (*send)(int socket,
					const struct ADDR *source,
					const struct ADDR *destination,
					struct BACNET_BUFFER *bnb),
			    int (*recv)(int socket, struct ADDR *source,
					struct BACNET_BUFFER *bnb),
			    int (*close)(int socket),
			    const struct ADDR *source,
			    const struct ADDR *broadcast);
int (*bacnet_add_route)(unsigned short remote_network,
			unsigned short interface_network,
			const struct ADDR *router_addr);
int (*bacnet_del_route)(unsigned short network);

int (*bacnet_network_is_local)(unsigned short network);

const struct ADDR *(*bacnet_interface_addr)(unsigned short network);
const struct ADDR *(*bacnet_interface_broadcast)(unsigned short network);
int (*bacnet_interface_socket)(unsigned short network);

const struct ADDR *(*bacnet_router_addr)(unsigned short network);
struct BACNET_BUFFER *(*encode_new_buffer)(const struct BACNET_NPCI *npci,
					   const struct BACNET_APCI* apci,
					   void *data,
					   int length);
int (*decode_existing_buffer)(struct BACNET_BUFFER *buffer,
			      struct BACNET_NPCI* npci,
			      struct BACNET_APCI* apci,
			      void **ppdata);
int (*bacnet_send_message)(unsigned short network,
			   const struct ADDR *dest,
			   const struct BACNET_NPCI *npci,
			   const struct BACNET_APCI* apci,
			   void *data,
			   int length,
			   long debug_level);
int (*bacnet_recv_message)(unsigned short network,
			   struct ADDR *source,
			   struct BACNET_NPCI* npci,
			   struct BACNET_APCI* apci,
			   void *data,
			   int maxlen,
			   long debug_level);
int (*bacnet_close)(unsigned short network);
unsigned short (*npci_length)(struct BACNET_BUFFER *bnb);
void (*bacnet_decode_npci_data)(struct BACNET_BUFFER *bnb);
struct BACNET_BUFFER *(*bacnet_alloc_buffer)(int data_size);
void (*bacnet_free_buffer)(struct BACNET_BUFFER *bnb);
void (*bacnet_reset_buffer)(struct BACNET_BUFFER *bnb);
int (*bacnet_buffer_size)(struct BACNET_BUFFER *bnb);
int (*bacnet_max_data_size)(const struct BACNET_BUFFER *bnb);

struct lib_entry{
  const char *name;
  void **ptr;
};

struct lib_entry lib_table[] = {
  {"broadway_get_buffer", (void**)&broadway_get_buffer},
  {"broadway_raise", (void**)&broadway_raise},
  {"broadway_exception_from_name", (void**)&broadway_exception_from_name},
  {"broadway_raise_parse_failure", (void**)&broadway_raise_parse_failure},
  {"broadway_raise_invalid_ulong", (void**)&broadway_raise_invalid_ulong},
  {"broadway_raise_invalid_object", (void**)&broadway_raise_invalid_object},
  {"broadway_assert_exception_set", (void**)&broadway_assert_exception_set},
  {"is_buffer", (void**)&is_buffer},
  {"new_socket_entry", (void**)&new_socket_entry},
  {"del_socket_entry", (void**)&del_socket_entry},
  {"get_socket_entry", (void**)&get_socket_entry},
  {"bacnet_add_interface", (void**)&bacnet_add_interface},
  {"bacnet_add_route", (void**)&bacnet_add_route},
  {"bacnet_del_route", (void**)&bacnet_del_route},
  {"bacnet_network_is_local", (void**)&bacnet_network_is_local},
  {"bacnet_interface_addr", (void**)&bacnet_interface_addr},
  {"bacnet_interface_broadcast", (void**)&bacnet_interface_broadcast},
  {"bacnet_interface_socket", (void**)&bacnet_interface_socket},
  {"bacnet_router_addr", (void**)&bacnet_router_addr},
  {"encode_new_buffer", (void**)&encode_new_buffer},
  {"decode_existing_buffer", (void**)&decode_existing_buffer},
  {"bacnet_send_message", (void**)&bacnet_send_message},
  {"bacnet_recv_message", (void**)&bacnet_recv_message},
  {"bacnet_close", (void**)&bacnet_close},
  {"npci_length", (void**)&npci_length},
  {"bacnet_decode_npci_data", (void**)&bacnet_decode_npci_data},
  {"bacnet_alloc_buffer", (void**)&bacnet_alloc_buffer},
  {"bacnet_free_buffer", (void**)&bacnet_free_buffer},
  {"bacnet_reset_buffer", (void**)&bacnet_reset_buffer},
  {"bacnet_buffer_size", (void**)&bacnet_buffer_size},
  {"bacnet_max_data_size", (void**)&bacnet_max_data_size},
  {NULL, NULL}
};

int load_lib_references(void)
{
  int i;
  char *error;
  void *handle;
  PyObject *lib_module = PyImport_ImportModule("mpx.lib.bacnet.lib");
  PyObject *file_attr;

  if (!lib_module) {
    return 0;
  }
  file_attr = PyObject_GetAttrString(lib_module, "__file__");
  if (!file_attr) {
    return 0;
  }
  handle = dlopen(PyString_AS_STRING(file_attr), RTLD_LAZY);
  Py_DECREF(file_attr);
  Py_DECREF(lib_module);
  if (!handle) {
    fputs(dlerror(), stderr);
    exit(1);
  }
  for (i=0; lib_table[i].name != NULL; i++) {
    *(lib_table[i].ptr) = dlsym(handle, lib_table[i].name);
    if ((error = dlerror()) != NULL)  {
      fputs(error, stderr);
      exit(1);
    }
  }
  return 1;
}
