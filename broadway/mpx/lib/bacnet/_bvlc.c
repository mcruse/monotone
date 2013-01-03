/*
Copyright (C) 2002 2010 2011 Cisco Systems

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

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include "_bvlc.h"
#include "lib.h"

static char __doc__[] = "\n"
"##\n"
"# This module provides the BVLC interface.\n"
"";

static PyObject *__dict__;
static PyObject *_recv_queue;
static PyObject *_recv_queue_put;

static long debug_level(void)
{
  // @fixme Get reference to mpx.lib.bacnet.bvlc.debug
  PyObject *debug = PyDict_GetItemString(__dict__, "debug");
  if (debug != NULL) {
    if (PyInt_Check(debug)) {
      return PyInt_AS_LONG(debug);
    }
  }
  return 0;
}

void bvlc_copy_to_queue(int network, const char *address,
			union BVLC_FUNCTION *bvlc)
{
  static PyObject *args = NULL;
  static PyObject *timeout;
  PyObject *network_object;
  PyObject *address_object;
  PyObject *bvlc_object;
  PyObject *tuple;

#if 0
  const unsigned char *dump = address;
  printf("bvlc_copy_to_queue(%d, %d.%d.%d.%d:%x, ...)\n", network,
	 dump[0], dump[1], dump[2], dump[3], (dump[4] << 8) | dump[5]);
#endif

  if (!args) {
    args = PyTuple_New(2);
    timeout = PyFloat_FromDouble(0.0);
    PyTuple_SetItem(args, 0, timeout);
  }
  network_object = PyInt_FromLong(network);
  address_object = PyString_FromStringAndSize(address, 6);
  bvlc_object = PyString_FromStringAndSize((char*)bvlc,
					   ntohs(bvlc->header.length));
  tuple = PyTuple_New(3);
  PyTuple_SetItem(tuple, 0, network_object);
  PyTuple_SetItem(tuple, 1, address_object);
  PyTuple_SetItem(tuple, 2, bvlc_object);
  PyTuple_SetItem(args, 1, tuple);
  PyObject_CallMethod(_recv_queue, "put", "Of", tuple, 0.0);
  PyErr_Clear();
  return;
}

static char __doc__send[] = "\n"
"##\n"
"# MontyDoc string for send.\n"
"";
static PyObject *
bvlc_send(PyObject *self, PyObject *args)
{
  int ret;
  int network;
  struct SOCKET_MAP *entry;
  struct sockaddr_in to;
  char *pAddress;
  union BVLC_FUNCTION *pBvlc;
  int cAddress, cBvlc, socket;

  // send(network, address, bvlc)
  if (!PyArg_ParseTuple(args, "is#s#", &network, &pAddress, &cAddress,
			&pBvlc, &cBvlc)) {
    return NULL;
  }
  if (cAddress != 6) {
    // @fixme Raise hell.
    return NULL;
  }
  if (cBvlc != ntohs(pBvlc->header.length)) {
    // @fixme Raise hell.
    return NULL;
  }
  socket = bacnet_interface_socket(network);
  entry = get_socket_entry(socket);
  memset(&to, 0, sizeof(to));
  to.sin_family = AF_INET;
  memcpy(&to.sin_addr.s_addr, pAddress, 4);
  memcpy(&to.sin_port,  pAddress+4, 2);
  ret = sendto(entry->direct, pBvlc, cBvlc, 0,
	       (struct sockaddr *)&to, sizeof(to));
  if (ret < 0) {
    // @fixme Raise a better exception.
    PyErr_SetFromErrno(PyExc_OSError);
    return NULL;
  }
  return Py_BuildValue("i", ret);
}

static PyMethodDef bvlc_functions[] = {
  {"bvlc_send", bvlc_send, METH_VARARGS, __doc__send},
  {NULL, NULL}
};

void
init_bvlc(void)
{
  // Function codes.
  static const char *function_code_enums[] = {
    "RESULT",
    "WRITE_BROADCAST_DISTRIBUTION_TABLE",
    "READ_BROADCAST_DISTRIBUTION_TABLE",
    "READ_BROADCAST_DISTRIBUTION_TABLE_ACK",
    "FORWARDED_NPDU",
    "REGISTER_FOREIGN_DEVICE",
    "READ_FOREIGN_DEVICE_TABLE",
    "READ_FOREIGN_DEVICE_TABLE_ACK",
    "DELETE_FOREIGN_DEVICE_TABLE_ENTRY",
    "DISTRIBUTE_BROADCAST_TO_NETWORK",
    "ORIGINAL_UNICAST_NPDU",
    "ORIGINAL_BROADCAST_NPDU",
    NULL
  };
  static const char *result_code_enums_x_16[] = {
    "SUCCESSFUL_COMPLETION",
    "WRITE_BROADCAST_DISTRIBUTION_TABLE_NAK",
    "READ_BROADCAST_DISTRIBUTION_TABLE_NAK",
    "REGISTER_FOREIGN_DEVICE_NAK",
    "READ_FOREIGN_DEVICE_TABLE_NAK",
    "DELETE_FOREIGN_DEVICE_TABLE_ENTRY_NAK",
    "DISTRIBUTE_BROADCAST_TO_NETWORK_NAK",
    NULL
  };
  // The indenting (four spaces) and final \n are vital for this code to work.
  static char *new_queue_code = "def _new_queue():\n"
    "    from mpx.lib.threading import Queue\n"
    "    return Queue(10)\n";

  int i;
  char *name;
  PyObject *new_queue_function;
  PyObject *new_queue_args;

  // Create the new module definition.
  PyObject *module = Py_InitModule("_bvlc", bvlc_functions);


  // Add the debug flag the module.
  // @fixme Get reference to mpx.lib.bacnet.bvlc.debug
  PyModule_AddObject(module, "debug", PyInt_FromLong(0));

  // Get a reference to this modules namespace dictionary.
  __dict__ = PyModule_GetDict(module);

  // Add the recv queue to the module.
  PyRun_String(new_queue_code, Py_single_input,
	       PyModule_GetDict(PyImport_AddModule("__main__")),
	       __dict__);
  new_queue_function = PyDict_GetItemString(__dict__, "_new_queue");
  new_queue_args = PyTuple_New(0);
  _recv_queue = PyEval_CallObject(new_queue_function, new_queue_args);
  PyModule_AddObject(module, "_recv_queue", _recv_queue);
  Py_DECREF(new_queue_args);

  // Get a reference to the _recv_queue and the bound "put" method.
  _recv_queue = PyDict_GetItemString(__dict__, "_recv_queue");
  _recv_queue_put = PyObject_GetAttrString(_recv_queue, "put");

  // Load the references to the shared library code.
  load_lib_references();

  // Define the message type constants.
  for (i=0; (name = (char*)function_code_enums[i]); i++) {
    PyModule_AddIntConstant(module, name, i);
  }
  for (i=0; (name = (char*)result_code_enums_x_16[i]); i++) {
    PyModule_AddIntConstant(module, name, i*16);
  }

  // Add the modules documentation.
  PyModule_AddStringConstant(module, "__doc__", __doc__);
}
