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

#include <stdio.h>
#include <dlfcn.h>

#include "lib.h"
#include "_data.h"

UINT64 (*data_decode_enumerated)(const unsigned char *buffer, int len);
UINT64 (*data_decode_unsigned_integer)(const unsigned char *buffer, int len);
INT64 (*data_decode_signed_integer)(const unsigned char *buffer, int len);
float (*data_decode_real)(const char *buffer, int len);
double (*data_decode_double)(const char *buffer, int len);
// _decode_octet_string is not used outside of data.c at the moment.
struct OctetString (*data_decode_octet_string)(const char *buffer, int len);
PyObject *(*data_decode_character_string)(const char *buffer, int len);
PyObject *(*data_decode_bit_string)(const char *buffer, int len);
PyObject *(*data_decode_time)(const unsigned char *buffer, int len);
PyObject *(*data_decode_date)(const unsigned char *buffer, int len);
PyObject *(*data_decode_bacnet_object_identifier)
     (const unsigned char *buffer, int len);

int (*data_encode_unsigned_integer)(char *buffer, int len, UINT64 value);
int (*data_encode_signed_integer)(char *buffer, int len, INT64 value);
int (*data_encode_real)(char *buffer, int len, float value);
int (*data_encode_double)(const char *buffer, int len, double value);

PyObject *(*data_encoded_date)(PyObject *this);
PyObject *(*data_encoded_time)(PyObject *this);
PyObject *(*data_encoded_bacnet_object_identifier)(PyObject *this);

PyTypeObject *data_DateType;
PyTypeObject *data_TimeType;
PyTypeObject *data_BACnetObjectIdentifierType;

PyObject *data_CharacterString;
PyObject *data_BitString;

struct data_entry{
  const char *name;
  void **ptr;
};

struct data_entry data_table[] = {
  // @note It is intentional that data_decode_enumerated resolves to
  //       data_decode_unsigned_integer.
  {"data_decode_unsigned_integer", (void**)&data_decode_enumerated},
  {"data_decode_unsigned_integer", (void**)&data_decode_unsigned_integer},
  {"data_decode_signed_integer", (void**)&data_decode_signed_integer},
  {"data_decode_real", (void**)&data_decode_real},
  {"data_decode_double", (void**)&data_decode_double},
  {"data_decode_octet_string", (void**)&data_decode_octet_string},
  {"data_decode_character_string", (void**)&data_decode_character_string},
  {"data_decode_bit_string", (void**)&data_decode_bit_string},
  {"data_decode_time", (void**)&data_decode_time},
  {"data_decode_date", (void**)&data_decode_date},
  {"data_decode_bacnet_object_identifier",
   (void**)&data_decode_bacnet_object_identifier},
  {"data_encode_unsigned_integer", (void**)&data_encode_unsigned_integer},
  {"data_encode_signed_integer", (void**)&data_encode_signed_integer},
  {"data_encode_real", (void**)&data_encode_real},
  {"data_encode_double", (void**)&data_encode_double},
  {"data_encoded_date", (void**)&data_encoded_date},
  {"data_encoded_time", (void**)&data_encoded_time},
  {"data_encoded_bacnet_object_identifier",
   (void**)&data_encoded_bacnet_object_identifier},
  {"data_DateType", (void**)&data_DateType},
  {"data_TimeType", (void**)&data_TimeType},
  {"data_BACnetObjectIdentifierType",
   (void**)&data_BACnetObjectIdentifierType},
  {"data_CharacterString", (void**)&data_CharacterString},
  {"data_BitString", (void**)&data_BitString},
  {NULL, NULL}
};

int load_data_references(void)
{
  int i;
  char *error;
  void *handle;
  PyObject *data_module = PyImport_ImportModule("mpx.lib.bacnet.data");
  PyObject *file_attr;

  if (!data_module) {
    return 0;
  }
  file_attr = PyObject_GetAttrString(data_module, "__file__");
  if (!file_attr) {
    return 0;
  }
  handle = dlopen(PyString_AS_STRING(file_attr), RTLD_LAZY);
  Py_DECREF(file_attr);
  Py_DECREF(data_module);
  if (!handle) {
    fputs(dlerror(), stderr);
    exit(1);
  }
  for (i=0; data_table[i].name != NULL; i++) {
    *(data_table[i].ptr) = dlsym(handle, data_table[i].name);
    if ((error = dlerror()) != NULL)  {
      fputs(error, stderr);
      exit(1);
    }
  }
  return 1;
}
