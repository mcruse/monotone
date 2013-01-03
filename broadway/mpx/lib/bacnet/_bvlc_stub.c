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
#include <stdio.h>
#include <dlfcn.h>

/*
 * Python 2.3 defines this as 200112L, but GNU wants this to be 199506L.
 *  -- STM 09.15.2004
 */
#ifdef _POSIX_C_SOURCE
#undef _POSIX_C_SOURCE
#endif

#include <Python.h>

#include "lib.h"

void (*bvlc_copy_to_queue)(int network,
			   const char *address,
			   struct BACNET_BUFFER *bnb);

struct bvlc_entry{
  const char *name;
  void **ptr;
};

struct bvlc_entry bvlc_table[] = {
  {"bvlc_copy_to_queue", (void**)&bvlc_copy_to_queue},
  {NULL, NULL}
};

int load_bvlc_references(void)
{
  int i;
  char *error;
  void *handle;
  PyObject *bvlc_module = PyImport_ImportModule("mpx.lib.bacnet._bvlc");
  PyObject *file_attr;

  if (!bvlc_module) {
    return 0;
  }
  file_attr = PyObject_GetAttrString(bvlc_module, "__file__");
  if (!file_attr) {
    return 0;
  }
  handle = dlopen(PyString_AS_STRING(file_attr), RTLD_LAZY);
  Py_DECREF(file_attr);
  Py_DECREF(bvlc_module);
  if (!handle) {
    fputs(dlerror(), stderr);
    exit(1);
  }
  for (i=0; bvlc_table[i].name != NULL; i++) {
    *(bvlc_table[i].ptr) = dlsym(handle, bvlc_table[i].name);
    if ((error = dlerror()) != NULL)  {
      fputs(error, stderr);
      exit(1);
    }
  }
  return 1;
}
