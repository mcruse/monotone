/*
Copyright (C) 2001 2010 2011 Cisco Systems

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
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <net/if.h>
#include <net/if_packet.h>
#include <netpacket/packet.h>
#include <netinet/if_ether.h>
#include <netinet/in.h>

/*
 * Python 2.3 defines this as 200112L, but GNU wants this to be 199506L.
 *  -- STM 09.15.2004
 */
#ifdef _POSIX_C_SOURCE
#undef _POSIX_C_SOURCE
#endif

#include <Python.h>
#include <structmember.h>
#include <compile.h>
#include <eval.h>

static PyObject *_eth_module;
static PyObject *exception_module;

void set_mpx_exception(char *name, PyObject *args, PyObject *kw)
{
  PyObject *klass;
  PyObject *object;
  klass = PyObject_GetAttrString(exception_module, name);
  object = PyInstance_New(klass, args, kw);
  PyErr_SetObject(klass, object);
}

static PyObject *
get_mac_address(PyObject *self, PyObject *args)
{
  int s;
  struct sockaddr_ll sll;
  struct ifreq ifr;
  int i;
  char *adapter;
  char hex[8];
  PyObject *result;

  // >>> get_mac_address(adapter_name)
  if (!PyArg_ParseTuple(args, "s", &adapter)) {
    return NULL;
  }
  s = socket(PF_PACKET, SOCK_RAW, htons(ETH_P_802_2));
  if (s < 0) {
    if (errno == EPERM) {
      args = PyTuple_New(3);
      PyTuple_SetItem(args, 0, PyInt_FromLong(EPERM));
      PyTuple_SetItem(args, 1, PyString_FromString(strerror(EPERM)));
      PyTuple_SetItem(args, 2, PyString_FromString(adapter));
      set_mpx_exception("EPermission", args, NULL);
      return NULL;
    }
    goto raise_os_error;
  }
  // Find the interface's index.
  memset(&ifr, 0, sizeof(ifr));
  strncpy(ifr.ifr_name, adapter, sizeof(ifr.ifr_name));

  if (ioctl(s, SIOCGIFINDEX, &ifr) == -1) {
    if (errno == ENODEV) {
      args = PyTuple_New(1); 
      PyTuple_SetItem(args, 0, PyString_FromString(adapter));
      set_mpx_exception("ENoSuchName", args, NULL);
      return NULL;
    }
    goto raise_os_error;
  }

  // Use the interface's index to bind the socket.
  memset(&sll, 0, sizeof(sll));
  sll.sll_family          = AF_PACKET;
  sll.sll_ifindex         = ifr.ifr_ifindex;
  sll.sll_protocol        = htons(ETH_P_ALL);

  if (bind(s, (struct sockaddr *) &sll, sizeof(sll)) == -1) {
    goto raise_os_error;
  }
  // Find the MAC address of the interface and set addr accordingly.
  memset(&ifr, 0, sizeof(ifr));
  strncpy(ifr.ifr_name, adapter, sizeof(ifr.ifr_name));

  if (ioctl(s, SIOCGIFHWADDR, &ifr) == -1) {
    goto raise_os_error;
  }
  // There's probably a more efficient way to do this...
  result = PyString_FromString("");
  for (i=0; i<6; i++) {
    sprintf(hex, "%02x", (unsigned char)ifr.ifr_ifru.ifru_hwaddr.sa_data[i]);
    PyString_ConcatAndDel(&result, PyString_FromString(hex));
  }
  return result;
 raise_os_error:
  PyErr_SetFromErrno(PyExc_OSError);
  if (s > -1) {
    close(s);
  }
  return NULL;
}

static PyMethodDef _eth_functions[] = {
  {"get_mac_address", get_mac_address, METH_VARARGS},
  {NULL, NULL}
};

void
init_eth(void)
{
  exception_module = PyImport_ImportModule("mpx.lib.exceptions");
  _eth_module = Py_InitModule("_eth", _eth_functions);
}
