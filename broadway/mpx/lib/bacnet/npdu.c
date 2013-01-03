/*
Copyright (C) 2001 2002 2003 2008 2010 2011 Cisco Systems

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
// @todo Make interfaces loadable instead of hardcoded.
// @todo rationalize addr, bcast order in API.

#include <Python.h>
#include <structmember.h>

#include "lib.h"
#include "_bvlc_stub.h"
#include "eth.h"
#include "ip.h"
#include "virtual.h"
#include "mstp.h"

#include "addr_object.h"
#include "npdu_object.h"

extern long n_Addr_instances;
extern long n_NPDU_instances;

static char __doc__[] = "\n"
"##\n"
"# This module provides the API required to create, send and receive BACnet\n"
"# NPDU messages.\n"
"#\n"
"# @note This is Broadway's lowest level access to the BACnet abstraction\n"
"# and is not intended for general use.  The network and apdu modules\n"
"# implement higher level abstractions that provide for a usable Network\n"
"# Application Layer.";

static PyObject *__dict__;

static long debug_level(void)
{
  PyObject *debug = PyDict_GetItemString(__dict__, "debug");
  if (debug != NULL) {
    if (PyInt_Check(debug)) {
      return PyInt_AS_LONG(debug);
    }
  }
  return 0;
}

static char __doc__close[] = "\n"
"##\n"
"# MontyDoc string for close.\n"
"#";
static PyObject *
_close(PyObject *self, PyObject *args)
{
  int ret;
  int network;

  // close(network)
  if (!PyArg_ParseTuple(args, "i", &network)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  ret = bacnet_close(network);
  if (ret < 0) {
    broadway_assert_exception_set("npdu.c", __LINE__);
    return NULL;
  }
  return Py_BuildValue("i", ret);
}

static char __doc__send[] = "\n"
"##\n"
"# MontyDoc string for send.";
static PyObject *
_send(PyObject *self, PyObject *args)
{
  int ret;
  unsigned char *pdata;
  struct BACNET_APCI *papci;
  int network;
  addr_object *addr;
  npdu_object *npdu;
  const char *msg;

  // send(network, addr, ndpu)
  if (!PyArg_ParseTuple(args, "iOO", &network, &addr, &npdu)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  if (addr->ob_type != AddrType) {
    msg = "npdu.send requires an npdu.Addr object as its second argument.";
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  if (npdu->ob_type != &npdu_type) {
    msg = "npdu.send requires an npdu.NPDU object as its third argument.";
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  if (npdu->datalen) {
    pdata = npdu->data;
  } else {
    pdata = NULL;
  }
  if (npdu->npci.network_msg) {
    papci = NULL;
  } else {
    papci = &npdu->apci;
  }
  ret = bacnet_send_message(network, &addr->addr,
			    &npdu->npci, papci,
			    pdata, npdu->datalen,
			    debug_level());
  if (ret < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    return NULL;
  }
  return Py_BuildValue("i", ret);
}

static char __doc__recv[] = "\n"
"##\n"
"# MontyDoc string for recv.";
static PyObject *
_recv(PyObject *self, PyObject *args)
{
  struct ADDR _addr = {0, {0}};
  int network;
  addr_object *addr;
  npdu_object *npdu;
  const char *msg;

  // receive(network, addr)
  if (!PyArg_ParseTuple(args, "iO", &network, &addr)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  if (addr->ob_type != AddrType) {
    msg = "npdu.recv requires an npdu.Addr object as its second argument.";
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  npdu = PyObject_New(npdu_object, &npdu_type);
  if (npdu) {
    memset(&npdu->npci, 0, sizeof(npdu->npci));
    memset(&npdu->apci, 0, sizeof(npdu->apci));
    memset(&npdu->data, 0, sizeof(npdu->data));
    npdu->datalen = 0;
  } else {
    PyErr_NoMemory();
    return NULL;
  }
  npdu->datalen = bacnet_recv_message(network, &_addr,
				      &npdu->npci, &npdu->apci,
				      npdu->data, sizeof(npdu->data),
				      debug_level());
  if (npdu->datalen < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    PyObject_Del(npdu); // Accounted for (in recv).
    return NULL;
  }
  n_NPDU_instances += 1;
  addr->addr.length = _addr.length;
  memcpy(addr->addr.address, _addr.address, _addr.length);
  return (PyObject *)npdu;
}

static char __doc__add_route[] = "\n"
"##\n"
"# MontyDoc string for add_route.";
static PyObject *
add_route(PyObject *self, PyObject *args)
{
  int ret;
  struct ADDR _addr = {0, {0}};
  int remote_network;
  int local_network;
  addr_object *addr;
  const char *msg;

  // add_route(remote_network, local_network, address?)
  if (!PyArg_ParseTuple(args, "iiO", &remote_network, &local_network,
			&addr)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  if (addr->ob_type != AddrType) {
    msg = "npdu.add_route requires an npdu.Addr object as its third argument.";
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  _addr.length = addr->addr.length;
  memcpy(_addr.address, addr->addr.address, _addr.length);
  ret = bacnet_add_route(remote_network, local_network, &_addr);
  if (ret < 0) {
	msg = "npdu.add_route unable to add route";
    PyErr_SetString(PyExc_ValueError, msg);
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static char __doc___open_eth[] = "\n"
"##\n"
"# MontyDoc string for _open_eth.\n"
"# @fixme Ensure that objects are correctly released.\n"
"";
static PyObject *
_open_eth(PyObject *self, PyObject *args)
{
  struct ADDR _addr;
  struct ADDR _broadcast;
  int bs;
  char *name;
  int network;
  addr_object *addr;
  addr_object *get_broadcast;
  const char *msg;
  int noptions;
  int i;
  char *zkey;
  PyObject *options = NULL;    // "Borrowed" from caller.
  PyObject *option = NULL;    // "Borrowed" from options.
  PyObject *keys = NULL;    // "New" object from options.
  PyObject *key = NULL;        // "Borrowed" from keys.

  // _open_eth(adapter, network, addr, options=None)
  // options:  get_broadcast
  get_broadcast = NULL;
  if (!PyArg_ParseTuple(args, "siO|O", &name, &network, &addr, &options)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  if (addr->ob_type != AddrType) {
    msg = "npdu._open_eth requires an npdu.Addr object as its third argument.";
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  if (PyDict_Check(options)) {
    // Loop through the options.
    noptions = PyDict_Size(options);
    keys = PyDict_Keys(options);
    for (i=0;i<noptions;i++) {
      key = PyList_GetItem(keys, i);
      if (!PyString_Check(key)) {
	msg = "npdu._open_eth the option keys must be strings.";
	PyErr_SetString(PyExc_TypeError, msg);
	return NULL;
      }
      zkey = PyString_AsString(key);
      option = PyDict_GetItemString(options, zkey);
      if (!strcmp(zkey, "get_broadcast")) {
	if (option->ob_type == AddrType) {
	  get_broadcast = (addr_object*)option;
	} else {
	  msg = "npdu._open_eth the get_broadcast option must be an Addr.";
	  PyErr_SetString(PyExc_TypeError, msg);
	  return NULL;
	}
      } else {
	msg = "npdu._open_eth unknown option.";
	PyErr_SetString(PyExc_TypeError, msg);
	return NULL;
      }
    }
  } else if (options == Py_None) {
    // No options.
  } else {
    msg = "npdu._open_eth optional options must be in a dictionary.";
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  bs = open_eth(name, &_addr);
  if (bs < 0) {
    broadway_assert_exception_set("npdu.c", __LINE__);
    return NULL;
  }
  // Ethernet broadcast address is always ff:ff:ff:ff:ff:ff.
  _broadcast.length = 6;
  memset(_broadcast.address, 0xff, _broadcast.length);
  if (bacnet_add_interface(network, bs, send_eth, recv_eth, close_eth,
			   &_addr, &_broadcast, BACNET_MAX_APDU_ETH) < 0) {
    broadway_assert_exception_set("npdu.c", __LINE__);
    return NULL;
  }
  // Update the supplied Addr with the interface's actual address.
  addr->addr.length = _addr.length;
  memcpy(addr->addr.address, _addr.address, _addr.length);
  if (get_broadcast != NULL) {
    // Update the get_broadcast Addr object.
    get_broadcast->addr.length = _broadcast.length;
    memcpy(get_broadcast->addr.address, _broadcast.address,
	   _broadcast.length);
  }
  return PyInt_FromLong(bs);
}

static char __doc___open_ip[] = "\n"
"##\n"
"# MontyDoc string for _open_ip\n"
"# @fixme Ensure that objects are correctly released.\n"
"";
static PyObject *
_open_ip(PyObject *self, PyObject *args)
{
  struct ADDR _addr;
  struct ADDR _broadcast;
  addr_object *addr;
  addr_object *get_broadcast;
  int bs;
  char *name;
  int network;
  const char *msg;
  unsigned short port;
  int noptions;
  int i;
  char *zkey;
  PyObject *options = NULL;    // "Borrowed" from caller.
  PyObject *option = NULL;    // "Borrowed" from options.
  PyObject *keys = NULL;    // "New" object from options.
  PyObject *key = NULL;        // "Borrowed" from keys.
  PyObject *result = NULL;    // "New" Int, returned to caller.
  PyObject *cleanup_list[] = {keys};
  // _open_ip(adapter, network, address, options=None)
  // options:  get_broadcast, port
  get_broadcast = NULL;

  // @fixme Port value should be configurable
  port = 0xBAC0;
  if (!PyArg_ParseTuple(args, "siO|O", &name, &network, &addr, &options)) {
    goto cleanup_and_exit;
  }
  if (addr->ob_type != AddrType) {
    msg = "npdu._open_ip requires an npdu.Addr object as its third argument.";
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  if (PyDict_Check(options)) {
    // Loop through the options.
    noptions = PyDict_Size(options);
    keys = PyDict_Keys(options);
    for (i=0;i<noptions;i++) {
      key = PyList_GetItem(keys, i);
      if (!PyString_Check(key)) {
	msg = "npdu._open_ip the option keys must be strings.";
	PyErr_SetString(PyExc_TypeError, msg);
	goto cleanup_and_exit;
      }
      zkey = PyString_AsString(key);
      option = PyDict_GetItemString(options, zkey);
      if (!strcmp(zkey, "port")) {
	if (PyInt_Check(option)) {
	  port = (unsigned short)PyInt_AsLong(option);
	} else {
	  msg = "npdu._open_ip the port option must be an integer.";
	  PyErr_SetString(PyExc_TypeError, msg);
	  goto cleanup_and_exit;
	}
      } else if (!strcmp(zkey, "get_broadcast")) {
	if (option->ob_type == AddrType) {
	  get_broadcast = (addr_object*)option;
	} else {
	  msg = "npdu._open_ip the get_broadcast option must be an Addr.";
	  PyErr_SetString(PyExc_TypeError, msg);
	  goto cleanup_and_exit;
	}
      } else {
	msg = "npdu._open_ip unknown option.";
	PyErr_SetString(PyExc_TypeError, msg);
	goto cleanup_and_exit;
      }
    }
  } else if (options == Py_None) {
    // No options.
  } else {
    msg = "npdu._open_ip optional options must be in a dictionary.";
    PyErr_SetString(PyExc_TypeError, msg);
    goto cleanup_and_exit;
  }
  bs = open_ip(name, &_addr, port, &_broadcast, network);
  if (bs < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    goto cleanup_and_exit;
  }
  addr->addr.length = _addr.length;
  memcpy(addr->addr.address, _addr.address, _addr.length);
  if (get_broadcast != NULL) {
    // Update the get_broadcast Addr object.
    get_broadcast->addr.length = _broadcast.length;
    memcpy(get_broadcast->addr.address, _broadcast.address,
	   _broadcast.length);
  }
  if (bacnet_add_interface(network, bs, send_ip, recv_ip, close_ip,
			   &_addr, &_broadcast, BACNET_MAX_APDU_IP) < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    goto cleanup_and_exit;
  }
  result = PyInt_FromLong(bs);
 cleanup_and_exit:
  for (i=0; i<sizeof(cleanup_list)/sizeof(PyObject*); i++) {
    Py_XDECREF(cleanup_list[i]);
  }
  return result;
}

static char __doc___open_mstp[] = "\n"
"##\n"
"# MontyDoc string for _open_mstp.\n"
"# @fixme Ensure that objects are correctly released.\n"
"";
static PyObject *
_open_mstp(PyObject *self, PyObject *args)
{
  struct ADDR _addr;
  struct ADDR _broadcast;
  int fd_mstp = -1;
  char *name = NULL;
  int network = -1;
  addr_object *addr = NULL;
  addr_object *get_broadcast = NULL;
  const char *msg;
  int noptions = 0, i = 0;
  char *zkey = NULL;
  PyObject *options = NULL;    // "Borrowed" from caller.
  PyObject *option = NULL;    // "Borrowed" from options.
  PyObject *keys = NULL;    // "New" object from options.
  PyObject *key = NULL;        // "Borrowed" from keys.
  // _open_mstp(name, address, options=None)
  // options:   get_broadcast

  // _open_mstp(adapter, network, addr, options=None)
  if(!PyArg_ParseTuple(args, "siO|O", &name, &network, &addr, &options)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }

  if(addr->ob_type != AddrType) {
    msg = ("npdu._open_mstp() requires an npdu.Addr object as its "
	   "third argument.");
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }

  if(PyDict_Check(options)) {
    // Loop through the options.
    noptions = PyDict_Size(options);
    keys = PyDict_Keys(options);
    for(i = 0; i < noptions; i++) {
      key = PyList_GetItem(keys, i);
      if(!PyString_Check(key)) {
	msg = "npdu._open_mstp(): option keys must be strings.";
	PyErr_SetString(PyExc_TypeError, msg);
	return NULL;
      }
      zkey = PyString_AsString(key);
      option = PyDict_GetItemString(options, zkey);

      if(!strcmp(zkey, "get_broadcast")) {
	if(option->ob_type == AddrType) {
	  get_broadcast = (addr_object*)option;
	}
	else {
	  msg = ("npdu._open_mstp(): 'get_broadcast' option must "
		 "be an Addr.");
	  PyErr_SetString(PyExc_TypeError, msg);
	  return NULL;
	}
      } else if(!strcmp(zkey, "MACaddr")) {
	// Prep to pass given address to ldisc:
	_addr.address[0] = (unsigned char)PyInt_AsLong(option);
      } else if(!strcmp(zkey, "fd_mstp")) {
	// Prep to pass given address to ldisc:
	fd_mstp = (unsigned char)PyInt_AsLong(option);
      } else {
	msg = "npdu._open_mstp(): Unknown option.";
	PyErr_SetString(PyExc_TypeError, msg);
	return NULL;
      }
    }
  } else {
    msg = ("npdu._open_mstp(): Options must be passed in a "
	   "Python dictionary.");
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }

  // Open/config RS485 port for MSTP:
  fd_mstp = open_mstp(name, &_addr, fd_mstp);
  if(fd_mstp < 0) {
    broadway_assert_exception_set("npdu.c", __LINE__);
    return NULL;
  }

  // MSTP broadcast address is 0xFF:
  _broadcast.length = 1;
  _broadcast.address[0] = 0xFF;

  // Add/config new, local BACnet MSTP interface wrapper:
  if(bacnet_add_interface(network, fd_mstp, send_mstp, recv_mstp, close_mstp,
			  &_addr, &_broadcast, BACNET_MAX_APDU_MSTP) < 0) {
    broadway_assert_exception_set("npdu.c", __LINE__);
    return NULL;
  }

  // Replace given Addr with address returned in call to
  // bacnet_add_interface():
  addr->addr.length = _addr.length;
  memcpy(addr->addr.address, _addr.address, _addr.length);

  return PyInt_FromLong(fd_mstp);
}

static char __doc___open_virtual[] = "\n"
"##\n"
"# MontyDoc string for _open_vritual\n"
"# @fixme Ensure that objects are correctly released.\n"
"";
static PyObject *
_open_virtual(PyObject *self, PyObject *args)
{
  struct ADDR _addr;
  struct ADDR _broadcast;
  addr_object *addr;
  addr_object *get_broadcast;
  int bs;
  char *name;
  int network;
  const char *msg;
  unsigned short port;
  int noptions;
  int i;
  char *zkey;
  PyObject *options = NULL;   // "Borrowed" from caller.
  PyObject *option = NULL;    // "Borrowed" from options.
  PyObject *keys = NULL;      // "New" object from options.
  PyObject *key = NULL;       // "Borrowed" from keys.
  PyObject *result = NULL;    // "New" Int, returned to caller.
  PyObject *cleanup_list[] = {keys};
  // _open_virtual(adapter, network, address, options=None)
  // options:  get_broadcast, port
  get_broadcast = NULL;

  // @fixme Port value should be configurable
  port = 0xBAC0;
  if (!PyArg_ParseTuple(args, "siO|O", &name, &network, &addr, &options)) {
    goto cleanup_and_exit;
  }
  if (addr->ob_type != AddrType) {
    msg = ("npdu._open_virtual requires an npdu.Addr object as "
	   "its third argument.");
    PyErr_SetString(PyExc_TypeError, msg);
    return NULL;
  }
  if (PyDict_Check(options)) {
    // Loop through the options.
    noptions = PyDict_Size(options);
    keys = PyDict_Keys(options);
    for (i=0;i<noptions;i++) {
      key = PyList_GetItem(keys, i);
      if (!PyString_Check(key)) {
	msg = "npdu._open_virtual the option keys must be strings.";
	PyErr_SetString(PyExc_TypeError, msg);
	goto cleanup_and_exit;
      }
      zkey = PyString_AsString(key);
      option = PyDict_GetItemString(options, zkey);
      if (!strcmp(zkey, "get_broadcast")) {
	if (option->ob_type == AddrType) {
	  get_broadcast = (addr_object*)option;
	} else {
	  msg = "npdu._open_virtual the get_broadcast option must be an Addr.";
	  PyErr_SetString(PyExc_TypeError, msg);
	  goto cleanup_and_exit;
	}
      } else {
	msg = "npdu._open_ unknown option.";
	PyErr_SetString(PyExc_TypeError, msg);
	goto cleanup_and_exit;
      }
    }
  } else if (options == Py_None) {
    // No options.
  } else {
    msg = "npdu._open_virtual optional options must be in a dictionary.";
    PyErr_SetString(PyExc_TypeError, msg);
    goto cleanup_and_exit;
  }
  bs = open_virtual(name, &_addr, network);
  if (bs < 0) {
    broadway_assert_exception_set("npdu.c", __LINE__);
    return NULL;
  }
  // Virtual broadcast address is always ff:ff:ff:ff:ff:ff.
  _broadcast.length = 6;
  memset(_broadcast.address, 0xff, _broadcast.length);
  addr->addr.length = _addr.length;
  memcpy(addr->addr.address, _addr.address, _addr.length);
  if (get_broadcast != NULL) {
    // Update the get_broadcast Addr object.
    get_broadcast->addr.length = _broadcast.length;
    memcpy(get_broadcast->addr.address, _broadcast.address,
	   _broadcast.length);
  }
  if (bacnet_add_interface(network, bs, send_virtual, recv_virtual,
			   close_virtual, &_addr, &_broadcast,
			   BACNET_MAX_APDU_VIRT) < 0) {
    PyErr_SetFromErrno(PyExc_OSError);
    goto cleanup_and_exit;
  }
  result = PyInt_FromLong(bs);
 cleanup_and_exit:
  for (i=0; i<sizeof(cleanup_list)/sizeof(PyObject*); i++) {
    Py_XDECREF(cleanup_list[i]);
  }
  return result;
}

static char __doc__is_NPDU[] = "\n"
"##\n"
"# MontyDoc string for is_NPDU.\n"
"#";
static PyObject *is_NPDU(PyObject *this, PyObject *args)
{
  PyObject *instance, *value, *tmp;

  // is_NPDU(instance)
  if (!PyArg_ParseTuple(args, "O", &instance)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  if (instance->ob_type == &npdu_type) {
    return PyInt_FromLong(1);
  }
  value = PyObject_GetAttrString(instance, "_is_NPDU");
  if (value && !PyInt_Check(value)) {
    tmp = value;
    value = PyNumber_Int(tmp);
    Py_DECREF(tmp);
  }
  if (value) {
    if (PyInt_Check(value)) {
      return value;
    } else {
      Py_DECREF(value);
    }
  }
  PyErr_Clear();
  return PyInt_FromLong(0);
}

static char __doc__is_Addr[] = "\n"
"##\n"
"# MontyDoc string for is_Addr.\n"
"#";
static PyObject *is_Addr(PyObject *this, PyObject *args)
{
  PyObject *instance;

  // is_Addr(instance)
  if (!PyArg_ParseTuple(args, "O", &instance)) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  if (instance->ob_type == AddrType) {
    return PyInt_FromLong(1);
  }
  return PyInt_FromLong(0);
}

static PyObject *count_Addr_instances(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  return PyInt_FromLong(n_Addr_instances);
}

static PyObject *count_NPDU_instances(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    // PyArg_ParseTuple set's PyErr.
    return NULL;
  }
  return PyInt_FromLong(n_NPDU_instances);
}

static PyMethodDef pybacnet_methods[] = {
  {"send", _send, METH_VARARGS, __doc__send},
  {"recv", _recv, METH_VARARGS, __doc__recv},
  {"close", _close, METH_VARARGS, __doc__close},
  {"add_route", add_route, METH_VARARGS, __doc__add_route},
  {"NPDU", new_npdu, METH_VARARGS, __doc__NPDU},
  {"is_NPDU", is_NPDU, METH_VARARGS, __doc__is_NPDU},
  {"Addr", new_addr, METH_VARARGS, __doc__Addr},
  {"is_Addr", is_Addr, METH_VARARGS, __doc__is_Addr},
  {"_open_eth", _open_eth, METH_VARARGS, __doc___open_eth},
  {"_open_ip", _open_ip, METH_VARARGS, __doc___open_ip},
  {"_open_virtual", _open_virtual, METH_VARARGS, __doc___open_virtual},
  {"_open_mstp", _open_mstp, METH_VARARGS, __doc___open_mstp},
  {"count_Addr_instances", count_Addr_instances, METH_VARARGS},
  {"count_NPDU_instances", count_NPDU_instances, METH_VARARGS},
  {NULL, NULL}
};

void
initnpdu(void)
{
  // Message types
  static const char *message_type_enums[] = {
    "WHO_IS_ROUTER",          // 0X00
    "I_AM_ROUTER",            // 0X01
    "I_COULD_BE_ROUTER",      // 0X02
    "REJECT_MESSAGE",         // 0X03
    "ROUTER_BUSY",            // 0X04
    "ROUTER_AVAILABLE",       // 0X05
    "INIT_ROUTING_TABLE",     // 0X06
    "INIT_ROUTING_TABLE_ACK", // 0X07
    "ESTABLISH_CONNECTION",   // 0X08
    "DISCONNECT_CONNECTION",  // 0X09
    NULL
  };
  int i;
  char *name;

  // Create the new module definition.
  PyObject *module = Py_InitModule("npdu", pybacnet_methods);

  // Load the references to the shared library code.
  load_lib_references();

  // Load the references to the shared BVLC library code.
  load_bvlc_references();

  // Add the debug flag the module.
  PyModule_AddObject(module, "debug", PyInt_FromLong(0));

  // Get a reference to this modules namespace dictionary.
  __dict__ = PyModule_GetDict(module);

  // Define the message type constants.
  for (i=0; (name = (char*)message_type_enums[i]); i++) {
    PyModule_AddIntConstant(module, name, i);
  }

  // Add the modules documentation.
  PyModule_AddStringConstant(module, "__doc__", __doc__);
}
