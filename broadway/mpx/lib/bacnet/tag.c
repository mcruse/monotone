/*
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
// @fixme Add morph_ok to decode methods.

#include <Python.h>
#include <structmember.h>
#include <netinet/in.h>

#include "lib.h"
#include "data.h"

static long n_Tag_instances = 0;
static long n_Outstanding_Mallocs = 0;
static long n_Buffer_References = 0;

static char __doc__[] = "\n"
"##\n"
"# This module provides the API required to encode and decode BACnet\n"
"# tags via an easy to use object-oriented model.";

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

//
// 20.2.1.4 Applications Tags (ASHRAE 135-1995 page 336)
//

#define BACNET_NULL 0
#define BOOLEAN 1
#define UNSIGNED_INTEGER 2
#define SIGNED_INTEGER 3    // (2's complement notation)
#define REAL 4		    // (ANSI/IEEE-754 floating point)
#define DOUBLE 5	    // (ANSI/IEEE-754 double precision floating port)
#define OCTET_STRING 6
#define CHARACTER_STRING 7
#define BIT_STRING 8
#define ENUMERATED 9
#define DATE 10
#define TIME 11
#define BACNETOBJECTIDENTIFIER 12
#define RESERVED13 13
#define RESERVED14 14
#define RESERVED15 15

static const char *apptag_constants[] = {
  "NULL", "BOOLEAN", "UNSIGNED_INTEGER", "SIGNED_INTEGER", "REAL", "DOUBLE",
  "OCTET_STRING", "CHARACTER_STRING", "BIT_STRING", "ENUMERATED",
  "DATE", "TIME", "BACNETOBJECTIDENTIFIER",
  "RESERVED13", "RESERVED14", "RESERVED15",
  NULL
};
static const char *apptag_descriptions[] = {
  "Null", "Boolean", "Unsigned Integer", "Signed Integer", "Real", "Double",
  "Octet String", "Character String", "Bit String", "Enumerated",
  "Date", "Time", "BACnetObjectIdentifier",
  "Reserved 13", "Reserved 14", "Reserved 15"
};

// Supported buffer types.
#define STRING 0
#define ARRAY  1

// Classes of tags.
#define INVALID     0	// Special value, memset(c_data, 0) marks it invalid.
#define APPLICATION 1
#define CONTEXT     2
#define OPEN        3
#define CLOSE       4
#define CONSTRUCT   5

struct Tag {
  unsigned char buffer_type;
  PyObject *buffer;
  PyObject *value;
  const unsigned char *start;// Pointer in the buffer where the tag starts.
  const unsigned char *next;// Pointer in the buffer where the next tag starts.
  const unsigned char *end; // Pointer to the first byte beyond the buffer.
  const unsigned char *data;// Pointer in the buffer where the primitive data
                            // starts.
  unsigned length;     // The length of the primitive data.
  unsigned char number;// The tag's number.
  unsigned char class; // The class of tag.
};

typedef struct {
  PyObject_HEAD
  struct Tag c_data;
} tag_object;

////
// Sets the Tag's c_data to a valid, *empty* state.
static void tag_init_c_data(tag_object *tag)
{
  memset(&tag->c_data, 0, sizeof(tag->c_data));
  // Set all pointers to the same, non-NULL, address.
  tag->c_data.start = tag->c_data.next = tag->c_data.end = \
    tag->c_data.data = "";
  tag->c_data.value = Py_None;
  Py_INCREF(Py_None);
}

static void tag_free_c_data(tag_object *tag)
{
  if (tag->c_data.buffer) {
    n_Buffer_References -= 1;
  }
  Py_XDECREF(tag->c_data.buffer);
  Py_XDECREF(tag->c_data.value);
  tag_init_c_data(tag);
}

////
// A construct is a 'special' tag, the value of which is a list
// of tags.  Constructs have more methods than other tags to help
// access the list in meaningful ways.  The outer-most construct
// reports its number as None (since it's not a tag in the BACnet
// sense).
static void tag_set_c_data_as_construct(tag_object *tag,
					PyObject * list,	// *Steals*
					unsigned char number)
{
  tag_free_c_data(tag);
  tag->c_data.value = list;
  tag->c_data.number = number;
  tag->c_data.class = CONSTRUCT;
}

////
// A construct is a 'special' tag, the value of which is a list
// of tags.  Constructs have more methods than other tags to help
// access the list in meaningful ways.  The outer-most construct
// reports its number as None (since it's not a tag in the BACnet
// sense).
static void tag_init_c_data_as_construct(tag_object *tag)
{
  tag_init_c_data(tag);
  tag_set_c_data_as_construct(tag, PyList_New(0), 255);
}

static void tag_dealloc(PyObject *self)
{
  tag_object *this = (tag_object *)self;
  tag_free_c_data(this);
  n_Tag_instances -= 1;
  PyObject_Del(self);  // Accounted for (in dealloc).
}

static PyTypeObject TagType;			// Forward declaration.

static PyTypeObject ContextType;
static PyTypeObject OpenType;
static PyTypeObject CloseType;
static PyTypeObject ConstructType;

static PyTypeObject NullType;
static PyTypeObject BooleanType;
static PyTypeObject UnsignedIntegerType;
static PyTypeObject SignedIntegerType;
static PyTypeObject RealType;
static PyTypeObject DoubleType;
static PyTypeObject OctetStringType;
static PyTypeObject CharacterStringType;
static PyTypeObject BitStringType;
static PyTypeObject EnumeratedType;
static PyTypeObject DateType;
static PyTypeObject TimeType;
static PyTypeObject BACnetObjectIdentifierType;

static PyTypeObject InvalidType;

struct tag_type_entry {
  PyTypeObject *type_object;
  char *type_name;
};
static struct tag_type_entry application_type[] = {
  {&NullType, "NullType"}, {&BooleanType, "BooleanType"},
  {&UnsignedIntegerType, "UnsignedIntegerType"},
  {&SignedIntegerType, "SignedIntegerType"}, {&RealType, "RealType"},
  {&DoubleType, "DoubleType"}, {&OctetStringType, "OctetStringType"},
  {&CharacterStringType, "CharacterStringType"},
  {&BitStringType, "BitStringType"}, {&EnumeratedType, "EnumeratedType"},
  {&DateType, "DateType"}, {&TimeType, "TimeType"},
  {&BACnetObjectIdentifierType, "BACnetObjectIdentifierType"},
  {NULL}};

static struct tag_type_entry other_type[] = {
  {&ContextType, "ContextType"}, {&OpenType, "OpenType"},
  {&CloseType, "CloseType"}, {&ConstructType, "ConstructType"},
  {&TagType, "TagType"}, {NULL}};

static PyObject *construct_getattr(PyObject *self, char *name);
static PyObject *null_getattr(PyObject *self, char *name);
static PyObject *boolean_getattr(PyObject *self, char *name);
static PyObject *unsigned_integer_getattr(PyObject *self, char *name);
static PyObject *signed_integer_getattr(PyObject *self, char *name);
static PyObject *real_getattr(PyObject *self, char *name);
static PyObject *double_getattr(PyObject *self, char *name);
static PyObject *octet_string_getattr(PyObject *self, char *name);
static PyObject *character_string_getattr(PyObject *self, char *name);
static PyObject *bit_string_getattr(PyObject *self, char *name);
static PyObject *enumerated_getattr(PyObject *self, char *name);
static PyObject *date_getattr(PyObject *self, char *name);
static PyObject *time_getattr(PyObject *self, char *name);
static PyObject *bacnet_object_identifier_getattr(PyObject *self, char *name);

static void init_types(void)
{
  memcpy(&ContextType, &TagType, sizeof(TagType));
  ContextType.tp_name = "ContextTag";
  memcpy(&OpenType, &TagType, sizeof(TagType));
  OpenType.tp_name = "OpenTag";
  memcpy(&CloseType, &TagType, sizeof(TagType));
  CloseType.tp_name = "CloseTag";
  memcpy(&ConstructType, &TagType, sizeof(TagType));
  ConstructType.tp_name = "ConstructTag";
  ConstructType.tp_getattr = construct_getattr;
  memcpy(&NullType, &TagType, sizeof(TagType));
  NullType.tp_name = "NullTag";
  NullType.tp_getattr = null_getattr;
  memcpy(&BooleanType, &TagType, sizeof(TagType));
  BooleanType.tp_name = "BooleanTag";
  BooleanType.tp_getattr = boolean_getattr;
  memcpy(&UnsignedIntegerType, &TagType, sizeof(TagType));
  UnsignedIntegerType.tp_name = "UnsignedIntegerTag";
  UnsignedIntegerType.tp_getattr = unsigned_integer_getattr;
  memcpy(&SignedIntegerType, &TagType, sizeof(TagType));
  SignedIntegerType.tp_name = "SignedIntegerTag";
  SignedIntegerType.tp_getattr = signed_integer_getattr;
  memcpy(&RealType, &TagType, sizeof(TagType));
  RealType.tp_name = "RealTag";
  RealType.tp_getattr = real_getattr;
  memcpy(&DoubleType, &TagType, sizeof(TagType));
  DoubleType.tp_name = "DoubleTag";
  DoubleType.tp_getattr = double_getattr;
  memcpy(&OctetStringType, &TagType, sizeof(TagType));
  OctetStringType.tp_name = "OctetStringTag";
  OctetStringType.tp_getattr = octet_string_getattr;
  memcpy(&CharacterStringType, &TagType, sizeof(TagType));
  CharacterStringType.tp_name = "CharacterStringTag";
  CharacterStringType.tp_getattr = character_string_getattr;
  memcpy(&BitStringType, &TagType, sizeof(TagType));
  BitStringType.tp_name = "BitStringTag";
  BitStringType.tp_getattr = bit_string_getattr;
  memcpy(&EnumeratedType, &TagType, sizeof(TagType));
  EnumeratedType.tp_name = "EnumeratedTag";
  EnumeratedType.tp_getattr = enumerated_getattr;
  memcpy(&DateType, &TagType, sizeof(TagType));
  DateType.tp_name = "DateTag";
  DateType.tp_getattr = date_getattr;
  memcpy(&TimeType, &TagType, sizeof(TagType));
  TimeType.tp_name = "TimeTag";
  TimeType.tp_getattr = time_getattr;
  memcpy(&BACnetObjectIdentifierType, &TagType, sizeof(TagType));
  BACnetObjectIdentifierType.tp_name = "BACnetObjectIdentifierTag";
  BACnetObjectIdentifierType.tp_getattr = bacnet_object_identifier_getattr;
  // @fixme Add invalid handlers...
  memcpy(&InvalidType, &TagType, sizeof(TagType));
  InvalidType.tp_name = "InvalidTag";
  return;
}

#define exceeded_end(pdata, pend) ((pdata) >= (pend))

static int buffer_to_tag(tag_object *tag,
			 PyObject *decode,
			 const unsigned char *buffer,
			 unsigned long length)
{
  char *msg;
  UINT32 lvt, context;
  const unsigned char *data, *end;
  PyTypeObject *previous_type = tag->ob_type;

  tag_free_c_data(tag);
  tag->c_data.buffer = decode;
  Py_INCREF(tag->c_data.buffer);
  n_Buffer_References += 1;

  end = buffer + length;  
  data = buffer;
  if (exceeded_end(data, end)) {
    msg = "End of data while decoding.";
    broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
    goto error;
  }
  tag->c_data.start = data;
  tag->c_data.number = *data >> 4;
  context = (*data >> 3) & 1;
  lvt = *data & 0x07;
  data += 1;  // Advance past the initial octet.
  if (!context) {
    if (tag->c_data.number >= RESERVED13) {
      msg = "Invalid application tag number.";
      broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
      goto error;
    }
    if (tag->c_data.number == BACNET_NULL && lvt != 0) {
      msg = "Invalid NULL application tag.";
      broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
      goto error;
    }
    if (lvt > 5) {
      msg = "Invalid application tag length encoding.";
      broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
      goto error;
    }
  }
  if (tag->c_data.number == 0x0f) {
    if (exceeded_end(data, end)) {
      // Test before dereference, since this is the first time we 'know'
      // we're really interested in data past the initial tag.
      msg = "End of data while decoding.";
      broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
      goto error;
    }
    tag->c_data.number = *data;   // Extract the extended tag number.
    data += 1;		    // Advance past the extended tag number.
  }
  switch (lvt) {
  case 7:
    tag->c_data.length = 0;
    tag->c_data.class = CLOSE;
    break;
  case 6:
    tag->c_data.length = 0;
    tag->c_data.class = OPEN;
    break;
  case 5:
    if (exceeded_end(data, end)) {
      // Test before dereference, since this is the first time we 'know'
      // we're really interested in data past the tag or extended tag number.
      msg = "End of data while decoding.";
      broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
      goto error;
    }
    // Extended length.
    lvt = *data;
    data += 1;
    if (lvt == 254) {
      if (exceeded_end(data+1, end)) {
	// Test before dereference, +1 ensure it's valid to read the
	// extended length from the buffer.
	msg = "End of data while decoding.";
	broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
	goto error;
      }
      lvt = ntohs(*(unsigned short*)data);
      data += 2;
    } else if (lvt == 255) {
      if (exceeded_end(data+3, end)) {
	// Test before dereference, +3 ensure it's valid to read the
	// extended length from the buffer.
	msg = "End of data while decoding.";
	broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
	goto error;
      }
      lvt = ntohl(*(unsigned long*)data);
      data += 4;
    }
    // Fall through to set length and validate.
  default:
    tag->c_data.class = (context) ? CONTEXT : APPLICATION ;
    if (!context && tag->c_data.number == BOOLEAN) {
      // It's the BOOLEAN application tag exception!
      // see ASHRAE 135-1995 20.2.3
      tag->c_data.length = 0;
    } else {
      tag->c_data.length = lvt;
    }
    break;
  }
  tag->c_data.next = data + tag->c_data.length;
  if (exceeded_end(tag->c_data.next-1, end)) {
    // The specified amount of data exceeds the buffer size.
    msg = "End of data while decoding.";
    broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
    goto error;
  }
  tag->c_data.data = data;
  tag->c_data.end = end;
  // Now for the black magic.  Morph the Tag to the appropriate type.  Scary.
  switch (tag->c_data.class) {
  case APPLICATION:
    // It's an application tag.
    tag->ob_type = application_type[tag->c_data.number].type_object;
    break;
  case CONTEXT:
    // It's a context tag.
    tag->ob_type = &ContextType;
    break;
  case OPEN:
    // It's an open tag.
    tag->ob_type = &OpenType;
    break;
  case CLOSE:
    // It's a close tag.
    tag->ob_type = &CloseType;
    break;
  case INVALID:
  default:
    // It's an invalid tag.
    tag->ob_type = &TagType;
    break;
  }
  if (previous_type != &TagType && previous_type != tag->ob_type) {
    msg = "decode would require changing established object type";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    goto error;
  }
  return 1;
 error:
  tag->ob_type = previous_type;
  tag_free_c_data(tag);
  return 0;
}

static int decode_to_tag(tag_object *tag, PyObject *decode,
			 PyObject *offset_object)
{
  const unsigned char *buffer;
  char *msg;
  UINT32 length;
  int offset = (offset_object) ? PyInt_AsLong(offset_object) : 0 ;
  if (PyErr_Occurred()) {
    if (!PyInt_Check(offset_object)) {
      msg = "offset must be an integer.";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    }
    return 0;
  }
  broadway_get_buffer(&buffer, &length, decode);
  if (!buffer) {
    msg = "End of data while decoding.";
    broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
    return 0;
  }
  return buffer_to_tag(tag, decode, buffer+offset, length-offset);
}

////
// @param buffer A string or array.
// @param offset An optional offset to apply to the buffer before decoding
//        the tag.
static PyObject *tag_decode(PyObject *self, PyObject *args)
{
  tag_object *this = (tag_object *)self;
  PyObject *buffer = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTuple(args, "O|O", &buffer, &offset)) {
    return NULL;
  }
  if (!decode_to_tag(this, buffer, offset)) {
    return NULL;
  }
  Py_INCREF(self);
  return self;
}

////
//
static PyObject *tag_encode(PyObject *self, PyObject *args)
{
  char *msg = "Encoding requires specific Tag objects.";
  broadway_raise("ENotImplemented", PyString_FromString(msg), NULL);
  return NULL;
}

static struct PyMethodDef tag_methodlist[] = {
  {"decode", tag_decode, METH_VARARGS},
  {"encode", tag_encode, METH_VARARGS},
  {NULL}
};

static struct memberlist tag_memberlist[] = {
  {"length", T_UINT, offsetof(tag_object, c_data.length), READONLY},
  {"number", T_UBYTE, offsetof(tag_object, c_data.number), READONLY},
  // The remaining definitions have bogus offsets and types:  tag_getattr()
  // explicitly handles these and tag_setattr() will raise a READONLY
  // exception.
  {"data", T_UBYTE, offsetof(tag_object, c_data.data), READONLY},
  {"data_offset", T_UBYTE, offsetof(tag_object, c_data.data), READONLY},
  {"encoding", T_UBYTE, offsetof(tag_object, c_data.data), READONLY},
  {"is_application", T_UBYTE, offsetof(tag_object, c_data.class), READONLY},
  {"is_close", T_UBYTE, offsetof(tag_object, c_data.class), READONLY},
  {"is_constructed", T_UBYTE, offsetof(tag_object, c_data.class), READONLY},
  {"is_context", T_UBYTE, offsetof(tag_object, c_data.class), READONLY},
  {"is_open", T_UBYTE, offsetof(tag_object, c_data.class), READONLY},
  {"is_valid", T_UBYTE, offsetof(tag_object, c_data.class), READONLY},
  {"name", T_UBYTE, offsetof(tag_object, c_data.class), READONLY},
  {"next_offset", T_UBYTE, offsetof(tag_object, c_data.next), READONLY},
  {"remainder", T_UBYTE, offsetof(tag_object, c_data.next), READONLY},
  {"value", T_UBYTE, offsetof(tag_object, c_data.value), READONLY},
  {NULL}
};

static PyObject *tag_getattr(PyObject *self, char *name)
{
  tag_object *this = (tag_object *)self;
  PyObject *result = NULL;
  const char *msg = "Internal error.";
  if (strcmp(name, "data") == 0)
    return PyString_FromStringAndSize(this->c_data.data, this->c_data.length);
  if (strcmp(name, "data_offset") == 0)
    return PyInt_FromLong(this->c_data.data - this->c_data.start);
  if (strcmp(name, "encoding") == 0)
    return PyString_FromStringAndSize(this->c_data.start, (this->c_data.next -
							   this->c_data.start));
  if (strcmp(name, "name") == 0) {
    msg = "Unknown";
    switch (this->c_data.class) {
    case APPLICATION:
      msg = apptag_descriptions[this->c_data.number];
      break;
    case CONTEXT:
      msg = "Context";
      break;
    case OPEN:
      msg = "Open";
      break;
    case CLOSE:
      msg = "Close";
      break;
    case CONSTRUCT:
      msg = "Construct";
      break;
    case INVALID:
      msg = "Invalid";
    }
    return PyString_FromString(msg);
  }
  if (strcmp(name, "next_offset") == 0)
    return PyInt_FromLong(this->c_data.next - this->c_data.start);
  if (strcmp(name, "is_application") == 0)
    return PyInt_FromLong(this->c_data.class == APPLICATION);
  if (strcmp(name, "is_close") == 0)
    return PyInt_FromLong(this->c_data.class == CLOSE);
  if (strcmp(name, "is_constructed") == 0)
    return PyInt_FromLong(this->c_data.class == CONSTRUCT);
  if (strcmp(name, "is_context") == 0)
    return PyInt_FromLong(this->c_data.class == CONTEXT ||
			  this->c_data.class == CONSTRUCT ||
			  this->c_data.class == CLOSE ||
			  this->c_data.class == OPEN);
  if (strcmp(name, "is_open") == 0)
    return PyInt_FromLong(this->c_data.class == OPEN);
  if (strcmp(name, "is_valid") == 0)
    return PyInt_FromLong(this->c_data.class != INVALID);
  if (strcmp(name, "remainder") == 0)
    return PyString_FromStringAndSize(this->c_data.next,
				      this->c_data.end - this->c_data.next);
  if (strcmp(name, "value") == 0) {
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(tag_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return PyMember_Get((char *)self, tag_memberlist, name);
}

static int _is_tag(PyObject *thingy)
{
  int i;
  PyTypeObject *tag_type;
  PyTypeObject *thingy_type = thingy->ob_type;
  for (i=0; (tag_type = application_type[i].type_object); i++) {
    if (thingy_type == tag_type) {
      return 1;
    }
  }
  for (i=0; (tag_type = other_type[i].type_object); i++) {
    if (thingy_type == tag_type) {
      return 1;
    }
  }
  return 0;
}

static unsigned char *set_tag_number(unsigned char *tag, long number)
{
  if (number < 0 || number > 254) {
    broadway_raise_invalid_ulong(number, "number",
				 "tag number must be between 0 and 254");
    return NULL;
  }
  if (number < 0x0f) {
    *tag = (*tag & 0x0f) | (unsigned char)(number << 4);
    return tag+1; // Where to start the length.
  }
  *tag = *tag | 0xf0;
  *(tag+1) = (unsigned char)number;
  return tag+2;   // Where to start the length.
}

static unsigned char *set_tag_length(unsigned char *tag,
				     unsigned char *extended_length,
				     int length)
{
  if (length < 5) {
    *tag |= (unsigned char)length;
    return extended_length;	// Data follows the (extended) tag.
  }
  if (length < 254) {
    *tag |= 0x05;
    *extended_length++ = (unsigned char)length;
    return extended_length;	// Data follows the extended length byte.
  }
  if (length < 65636) {
    *tag |= 0x05;
    *extended_length++ = (unsigned char)254;
    *extended_length++ = (unsigned char)(length>>8);
    *extended_length++ = (unsigned char)length;
    return extended_length;	// Data follows the extended length word.
  }
  *tag |= 0x05;
  *extended_length++ = (unsigned char)255;
  *extended_length++ = (unsigned char)(length>>24);
  *extended_length++ = (unsigned char)(length>>16);
  *extended_length++ = (unsigned char)(length>>8);
  *extended_length++ = (unsigned char)length;
  return extended_length;	// Data follows the extended length double word.
}

static unsigned char *set_tag_data(unsigned char *data,
				   const unsigned char *source, 
				   int length)
{
  memcpy(data, source, length);
  return data+length;
}

static PyObject *construct_encoding(tag_object *this)
{
  char start[4];
  char *end;
  int i, len;
  PyObject *result;

  if (this->c_data.number != 255) {
    // Encode the openning tag.
    *start = '\x0e';
    end = set_tag_number(start, this->c_data.number);
    result = PyString_FromStringAndSize(start, end-start);
    if (!result) {
      return NULL;
    }
  } else {
    result = PyString_FromString("");
    if (!result) {
      return NULL;
    }
  }
  len = PyList_Size(this->c_data.value);
  if (PyErr_Occurred()) {
    Py_DECREF(result);
    return NULL;
  }
  for (i=0; i<len; i++) {
    PyObject *tag = PyList_GetItem(this->c_data.value, i);
    PyObject *encoding = PyObject_GetAttrString(tag, "encoding");
    if (!encoding) {
      Py_DECREF(result);
      return NULL;
    }
    PyString_ConcatAndDel(&result, encoding);
    if (!result) {
      return NULL;
    }
  }
  if (this->c_data.number != 255) {
    // Append the closing tag.
    *start = '\x0f';
    end = set_tag_number(start, this->c_data.number);
    PyString_ConcatAndDel(&result,
			  PyString_FromStringAndSize(start, end-start));
    if (!result) {
      return NULL;
    }
  }
  return result;
}

tag_object *buffer_as_construct(tag_object *open_tag,
				PyObject *decode, PyObject *offset);

////
// @param buffer A string or array.
// @param offset An optional offset to apply to the buffer before decoding
//        the tag.
static PyObject *construct_decode(PyObject *self, PyObject *args)
{
  char *msg;
  tag_object *this = (tag_object *)self;
  tag_object *temp_construct;
  PyObject *buffer = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTuple(args, "O|O", &buffer, &offset)) {
    return NULL;
  }
  // OK, this is too scary, but I'm tired and that's the best time to
  // write scary code.
  this->ob_type = &TagType;         // Allow this to become an open tag.
  if (!decode_to_tag(this, buffer, offset)) {
    this->ob_type = &ConstructType; // Restore correct type!
    return NULL;
  }
  if (this->ob_type != &OpenType) {
    this->ob_type = &ConstructType; // Restore correct type!
    msg = "decode would require changing established object type";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return NULL;
  }
  // Parse the entire construct using this as the openning tag.
  temp_construct = buffer_as_construct(this, buffer, offset);
  if (!temp_construct) {
    this->ob_type = &ConstructType; // Restore correct type!
    return NULL;
  }
  // Release all of this tag's (the open tag) resources.
  tag_free_c_data(this);
  // Steal all of the [temp_]construct's references.
  this->c_data = temp_construct->c_data;
  memset(&temp_construct->c_data, 0, sizeof(temp_construct->c_data));
  // Behave like the construct we are.
  this->ob_type = temp_construct->ob_type;
  Py_DECREF(temp_construct);
  Py_INCREF(Py_None);
  return Py_None;
}

static int encode_construct(tag_object *tag,
			    PyObject *number, PyObject *values);

////
//
static PyObject *construct_encode(PyObject *self, PyObject *args,
				  PyObject *keywords)
{
  static char *kwlist[] = {"number", "values", NULL};
  tag_object *this = (tag_object*)self;
  PyObject *number = NULL;
  PyObject *values = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OO", kwlist,
				   &number, &values)) {
    return NULL;
  }
  tag_free_c_data(this);
  if (number) {
    if (!encode_construct(this, number, values)) {
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("number required for encode"),
		   NULL);
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef construct_methodlist[] = {
  {"decode", construct_decode, METH_VARARGS},
  {"encode", (PyCFunction)construct_encode, METH_VARARGS | METH_KEYWORDS},
  {NULL}
};

//
// "Overload" getattr for the specific data types.
//
static PyObject *construct_getattr(PyObject *self, char *name)
{
  PyObject *result;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "number") == 0) {
    if (this->c_data.number == 255) {
      Py_INCREF(Py_None);
      return Py_None;
    }
  } else if (strcmp(name, "encoding") == 0) {
    return construct_encoding(this);
  }
  result = Py_FindMethod(construct_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Null.
static int encode_null(tag_object *tag)
{
  tag_free_c_data(tag);
  tag->c_data.buffer = PyString_FromStringAndSize("\x00", 1);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + 1;
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next;
  tag->c_data.length = 0;
  tag->c_data.number = BACNET_NULL;
  tag->c_data.class = APPLICATION;
  return 1;
}
////
// (Re)encode an existing Tag object as a BACnet Null.
static PyObject *null_encode(PyObject *self, PyObject *args)
{
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  if (!encode_null(this)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef null_methodlist[] = {
  {"encode", (PyCFunction)null_encode, METH_VARARGS},
  {NULL}
};

static PyObject *null_getattr(PyObject *self, char *name)
{
  PyObject *result = Py_FindMethod(null_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Boolean.
static int encode_boolean(tag_object *tag, PyObject *value)
{
  static unsigned char encodings[] = {0x10, 0x11};
  long true;
  tag_free_c_data(tag);
  true = PyInt_AsLong(value);
  if (PyErr_Occurred()) {
    return 0;
  }
  if (true < 0 || true > 1) {
    broadway_raise_invalid_ulong(true, "value",
				 "value must be 0 or 1");
    return 0;
  }
  tag->c_data.buffer = PyString_FromStringAndSize(encodings+true, 1);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + 1;
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next;
  tag->c_data.length = 0;
  tag->c_data.number = BOOLEAN;
  tag->c_data.class = APPLICATION;
  return 1;
}
////
// (Re)encode an existing Tag object as a BACnet Boolean.
static PyObject *boolean_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_boolean(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef boolean_methodlist[] = {
  {"encode", (PyCFunction)boolean_encode, METH_VARARGS},
  {NULL}
};

static PyObject *boolean_getattr(PyObject *self, char *name)
{
  PyObject *result;
  long value;
  char *msg;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      if ((*this->c_data.start&0x07) > 1) {
	msg = "Invalid boolean value.";
	broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
	return NULL;
      }
      value = *this->c_data.start & 1;
      this->c_data.value = PyInt_FromLong(value);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(boolean_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Boolean.
static int encode_unsigned_integer(tag_object *tag, PyObject *value)
{
  unsigned char buffer[32];
  unsigned char temp[24];
  unsigned char *next;
  unsigned char *data;
  long long unsigned_integer = PyInt_AsLong(value);
  int length;

  if (PyErr_Occurred()) {
    PyErr_Clear();
    unsigned_integer = PyLong_AsLongLong(value);
    if (PyErr_Occurred()) {
      return 0;
    }
  }
  tag_free_c_data(tag);
  if (unsigned_integer < 0) {
    broadway_raise_invalid_ulong(unsigned_integer, "value",
				 "value must be greater than or equal to 0");
    return 0;
  }
  length = data_encode_unsigned_integer(temp, sizeof(temp), unsigned_integer);
  if (length < 0) {
    return 0;
  }
  *buffer = '\0';
  next = set_tag_number(buffer, UNSIGNED_INTEGER);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, temp, length);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = UNSIGNED_INTEGER;
  tag->c_data.class = APPLICATION;
  return 1;
}
////
// (Re)encode an existing Tag object as a BACnet Unsigned Integer.
static PyObject *unsigned_integer_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_unsigned_integer(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef unsigned_integer_methodlist[] = {
  {"encode", (PyCFunction)unsigned_integer_encode, METH_VARARGS},
  {NULL}
};

static PyObject *unsigned_integer_getattr(PyObject *self, char *name)
{
  unsigned long long value;
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      value = data_decode_unsigned_integer(this->c_data.data,
					   this->c_data.length);
      this->c_data.value = (value & 0xffffffff80000000ULL)
	                 ? PyLong_FromLongLong(value)
	                 : PyInt_FromLong((long)value);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(unsigned_integer_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Signed Integer.
static int encode_signed_integer(tag_object *tag, PyObject *value)
{
  unsigned char buffer[32];
  unsigned char temp[24];
  unsigned char *next;
  unsigned char *data;
  long long signed_integer = PyInt_AsLong(value);
  int length;

  if (PyErr_Occurred()) {
    PyErr_Clear();
    signed_integer = PyLong_AsLongLong(value);
    if (PyErr_Occurred()) {
      return 0;
    }
  }
  tag_free_c_data(tag);
  length = data_encode_signed_integer(temp, sizeof(temp), signed_integer);
  if (length < 0) {
    return 0;
  }
  *buffer = '\0';
  next = set_tag_number(buffer, SIGNED_INTEGER);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, temp, length);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = SIGNED_INTEGER;
  tag->c_data.class = APPLICATION;
  return 1;
}
////
// (Re)encode an existing Tag object as a BACnet Signed Integer.
static PyObject *signed_integer_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_signed_integer(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef signed_integer_methodlist[] = {
  {"encode", (PyCFunction)signed_integer_encode, METH_VARARGS},
  {NULL}
};

static PyObject *signed_integer_getattr(PyObject *self, char *name)
{
  long long value;
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      value = data_decode_signed_integer(this->c_data.data,
					 this->c_data.length);
      if (value >= 0) {
	this->c_data.value = (value & 0xffffffff00000000ULL)
	                   ? PyLong_FromLongLong(value)
	                   : PyInt_FromLong((long)value);
      } else {
	this->c_data.value = (-value & 0xffffffff00000000ULL)
	                   ? PyLong_FromLongLong(value)
	                   : PyInt_FromLong((long)value);
      }
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(signed_integer_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Real.
static int encode_real(tag_object *tag, PyObject *value)
{
  unsigned char buffer[32];
  unsigned char temp[24];
  unsigned char *next;
  unsigned char *data;
  double single_percision = PyFloat_AsDouble(value);
  int length;

  if (PyErr_Occurred()) {
    return 0;
  }
  tag_free_c_data(tag);
  length = data_encode_real(temp, sizeof(temp), (float)single_percision);
  if (length < 0) {
    return 0;
  }
  *buffer = '\0';
  next = set_tag_number(buffer, REAL);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, temp, length);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = REAL;
  tag->c_data.class = APPLICATION;
  return 1;
}
////
// (Re)encode an existing Tag object as a BACnet Real.
static PyObject *real_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_real(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef real_methodlist[] = {
  {"encode", (PyCFunction)real_encode, METH_VARARGS},
  {NULL}
};

static PyObject *real_getattr(PyObject *self, char *name)
{
  double value;
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      value = data_decode_real(this->c_data.data, this->c_data.length);
      this->c_data.value = PyFloat_FromDouble(value);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(real_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Double.
static int encode_double(tag_object *tag, PyObject *value)
{
  unsigned char buffer[32];
  unsigned char temp[24];
  unsigned char *next;
  unsigned char *data;
  double double_percision = PyFloat_AsDouble(value);
  int length;

  if (PyErr_Occurred()) {
    return 0;
  }
  tag_free_c_data(tag);
  length = data_encode_double(temp, sizeof(temp), double_percision);
  if (length < 0) {
    return 0;
  }
  *buffer = '\0';
  next = set_tag_number(buffer, DOUBLE);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, temp, length);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = DOUBLE;
  tag->c_data.class = APPLICATION;
  return 1;
}
////
// (Re)encode an existing Tag object as a BACnet Double.
static PyObject *double_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_double(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef double_methodlist[] = {
  {"encode", (PyCFunction)double_encode, METH_VARARGS},
  {NULL}
};

static PyObject *double_getattr(PyObject *self, char *name)
{
  double value;
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      value = data_decode_double(this->c_data.data, this->c_data.length);
      this->c_data.value = PyFloat_FromDouble(value);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(double_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Octet String.
//
// @fixme Use less memory...
static int encode_octet_string(tag_object *tag, PyObject *value)
{
  const char *msg;
  unsigned char *next;
  unsigned char *data;
  unsigned char *buffer;
  const unsigned char *source;
  int length;

  if (PyErr_Occurred()) {
    return 0;
  }
  tag_free_c_data(tag);
  broadway_get_buffer(&source, &length, value);
  if (!source) {
    msg = "value must be a StringType or ArrayType object";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return 0;
  }
  buffer = malloc(length+1+1+1+4); /* Worst case size:
                                    * 1 byte for the tag "header"
				    * 1 byte for an extended tag number.
				    * 1 byte for an extended length reference.
				    * 4 bytes for a 32-bit length.
				    */
  if (!buffer) {
    msg = "could not allocate sufficient memory";
    broadway_raise("EMemoryError", PyString_FromString(msg), NULL);
  }
  n_Outstanding_Mallocs += 1;
  *buffer = '\0';
  next = set_tag_number(buffer, OCTET_STRING);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, source, length);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  free(buffer);
  n_Outstanding_Mallocs -= 1;
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = OCTET_STRING;
  tag->c_data.class = APPLICATION;
  return 1;
}
////
// (Re)encode an existing Tag object as a BACnet Octet String.
static PyObject *octet_string_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_octet_string(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef octet_string_methodlist[] = {
  {"encode", (PyCFunction)octet_string_encode, METH_VARARGS},
  {NULL}
};

static PyObject *octet_string_getattr(PyObject *self, char *name)
{
  PyObject *result = NULL;
  if (strcmp(name, "value") == 0) {
    name = "data";
  }
  result = Py_FindMethod(octet_string_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Character String.
static int encode_character_string(tag_object *tag,
				   PyObject *character_string)
{
  const char *msg;
  unsigned char *next;
  unsigned char *data;
  unsigned char *buffer;
  const unsigned char *source;
  PyObject *encoded_object;
  int length;
 
  if (!PyObject_IsInstance(character_string, *data_CharacterString)) {
    msg = "character_string must be derived from CharacterClass";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return 0;
  }
  encoded_object = PyObject_GetAttrString(character_string, "encoding");
  if (!encoded_object) {
    if (!PyErr_Occurred()) {
      msg = "character_string encoding failed";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    }
    return 0;
  }

  tag_free_c_data(tag);
  broadway_get_buffer(&source, &length, encoded_object);
  if (!source) {
    if (encoded_object) {
      Py_DECREF(encoded_object);
    }
    msg = "encoded data must be a StringType object or an ArrayType object";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return 0;
  }
  buffer = malloc(length+1+1+4); /* Worst case size:
				  * 1 byte for the tag "header"
				  * 1 byte for an extended length reference.
				  * 4 bytes for a 32-bit length.
				  */
  if (!buffer) {
    if (encoded_object) {
      Py_DECREF(encoded_object);
    }
    msg = "could not allocate sufficient memory";
    broadway_raise("EMemoryError", PyString_FromString(msg), NULL);
  }
  n_Outstanding_Mallocs += 1;
  *buffer = '\x00';
  next = set_tag_number(buffer, CHARACTER_STRING);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, source, length);
  if (encoded_object) {
    Py_DECREF(encoded_object);
  }
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  free(buffer);
  n_Outstanding_Mallocs -= 1;
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = CHARACTER_STRING;
  tag->c_data.class = APPLICATION;
  return 1;
}

////
// (Re)encode an existing Tag object as a BACnet Character String.
static PyObject *character_string_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_character_string(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef character_string_methodlist[] = {
  {"encode", (PyCFunction)character_string_encode, METH_VARARGS},
  {NULL}
};

static PyObject *character_string_getattr(PyObject *self, char *name)
{
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      this->c_data.value = data_decode_character_string(this->c_data.data,
							this->c_data.length);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(character_string_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Bit String.
static int encode_bit_string(tag_object *tag, PyObject *bit_string)
{
  const char *msg;
  unsigned char *next;
  unsigned char *data;
  unsigned char *buffer;
  const unsigned char *source;
  PyObject *encoded_object;
  int length;
 
  if (!PyObject_IsInstance(bit_string, *data_BitString)) {
    msg = "bit_string must be derived from BitString";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return 0;
  }
  encoded_object = PyObject_GetAttrString(bit_string, "encoding");
  if (!encoded_object) {
    if (!PyErr_Occurred()) {
      msg = "bit_string encoding failed";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    }
    return 0;
  }

  tag_free_c_data(tag);
  broadway_get_buffer(&source, &length, encoded_object);
  if (!source) {
    if (encoded_object) {
      Py_DECREF(encoded_object);
    }
    msg = "encoded data must be a StringType object or an ArrayType object";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return 0;
  }
  buffer = malloc(length+1+1+4); /* Worst case size:
				  * 1 byte for the tag "header"
				  * 1 byte for an extended length reference.
				  * 4 bytes for a 32-bit length.
				  */
  if (!buffer) {
    if (encoded_object) {
      Py_DECREF(encoded_object);
    }
    msg = "could not allocate sufficient memory";
    broadway_raise("EMemoryError", PyString_FromString(msg), NULL);
  }
  n_Outstanding_Mallocs += 1;
  *buffer = '\x00';
  next = set_tag_number(buffer, BIT_STRING);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, source, length);
  if (encoded_object) {
    Py_DECREF(encoded_object);
  }
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  free(buffer);
  n_Outstanding_Mallocs -= 1;
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = BIT_STRING;
  tag->c_data.class = APPLICATION;
  return 1;
}

////
// (Re)encode an existing Tag object as a BACnet Bit String.
static PyObject *bit_string_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_bit_string(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef bit_string_methodlist[] = {
  {"encode", (PyCFunction)bit_string_encode, METH_VARARGS},
  {NULL}
};

static PyObject *bit_string_getattr(PyObject *self, char *name)
{
  PyObject *result;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      this->c_data.value = data_decode_bit_string(this->c_data.data,
						  this->c_data.length);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(bit_string_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Enumerated.
static int encode_enumerated(tag_object *tag, PyObject *value)
{
  unsigned char buffer[32];
  unsigned char temp[24];
  unsigned char *next;
  unsigned char *data;
  long long enumerated = PyInt_AsLong(value);
  int length;

  if (PyErr_Occurred()) {
    PyErr_Clear();
    enumerated = PyLong_AsLongLong(value);
    if (PyErr_Occurred()) {
      return 0;
    }
  }
  tag_free_c_data(tag);
  if (enumerated < 0) {
    broadway_raise_invalid_ulong(enumerated, "value",
				 "value must be greater than or equal to 0");
    return 0;
  }
  length = data_encode_unsigned_integer(temp, sizeof(temp), enumerated);
  if (length < 0) {
    return 0;
  }
  *buffer = '\0';
  next = set_tag_number(buffer, ENUMERATED);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, temp, length);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = ENUMERATED;
  tag->c_data.class = APPLICATION;
  return 1;
}

////
// (Re)encode an existing Tag object as a BACnet Enumerated.
static PyObject *enumerated_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_enumerated(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef enumerated_methodlist[] = {
  {"encode", (PyCFunction)enumerated_encode, METH_VARARGS},
  {NULL}
};

static PyObject *enumerated_getattr(PyObject *self, char *name)
{
  unsigned long long value;
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      value = data_decode_enumerated(this->c_data.data,
				     this->c_data.length);
      this->c_data.value = (value & 0xffffffff80000000ULL)
	                 ? PyLong_FromLongLong(value)
	                 : PyInt_FromLong((long)value);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(enumerated_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Time.
static int encode_time(tag_object *tag, PyObject *value)
{
  PyObject *time;
  unsigned char buffer[32];
  unsigned char *next;
  unsigned char *data;
  int length;

  if (value->ob_type != data_TimeType) {
    broadway_raise("ETypeError",
		   PyString_FromString("value must be a Time object"),
		   NULL);
    return 0;
  }
  tag_free_c_data(tag);
  time = data_encoded_time(value);
  if (!time) {
    return 0;
  }
  length = PyString_GET_SIZE(time);
  *buffer = '\0';
  next = set_tag_number(buffer, TIME);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, PyString_AS_STRING(time), length);
  Py_DECREF(time);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = TIME;
  tag->c_data.class = APPLICATION;
  return 1;
}

////
// (Re)encode an existing Tag object as a BACnet Time.
static PyObject *time_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_time(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef time_methodlist[] = {
  {"encode", (PyCFunction)time_encode, METH_VARARGS},
  {NULL}
};

static PyObject *time_getattr(PyObject *self, char *name)
{
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      this->c_data.value = data_decode_time(this->c_data.data,
					    this->c_data.length);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(time_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Date.
static int encode_date(tag_object *tag, PyObject *value)
{
  PyObject *date;
  unsigned char buffer[32];
  unsigned char *next;
  unsigned char *data;
  int length;

  if (value->ob_type != data_DateType) {
    broadway_raise("ETypeError",
		   PyString_FromString("value must be a Date object"),
		   NULL);
    return 0;  
  }
  tag_free_c_data(tag);
  date = data_encoded_date(value);
  if (!date) {
    return 0;
  }
  length = PyString_GET_SIZE(date);
  *buffer = '\0';
  next = set_tag_number(buffer, DATE);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, PyString_AS_STRING(date), length);
  Py_DECREF(date);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = DATE;
  tag->c_data.class = APPLICATION;
  return 1;
}

////
// (Re)encode an existing Tag object as a BACnet Date.
static PyObject *date_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_date(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef date_methodlist[] = {
  {"encode", (PyCFunction)date_encode, METH_VARARGS},
  {NULL}
};

static PyObject *date_getattr(PyObject *self, char *name)
{
  PyObject *result;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      this->c_data.value = data_decode_date(this->c_data.data,
					    this->c_data.length);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(date_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

////
// (Re)encode an existing tag's c_data as a BACnet Object Identifier.
static int encode_bacnet_object_identifier(tag_object *tag, PyObject *value)
{
  PyObject *bacnet_object_identifier;
  unsigned char buffer[32];
  unsigned char *next;
  unsigned char *data;
  int length;

  if (value->ob_type != data_BACnetObjectIdentifierType) {
    broadway_raise("ETypeError",
		   PyString_FromString("value must be a "
				       "BACnetObjectIdentifier object"),
		   NULL);
    return 0;
  }
  tag_free_c_data(tag);
  bacnet_object_identifier = data_encoded_bacnet_object_identifier(value);
  if (!bacnet_object_identifier) {
    return 0;
  }
  length = PyString_GET_SIZE(bacnet_object_identifier);
  *buffer = '\0';
  next = set_tag_number(buffer, BACNETOBJECTIDENTIFIER);
  data = set_tag_length(buffer, next, length);
  next = set_tag_data(data, PyString_AS_STRING(bacnet_object_identifier),
		      length);
  Py_DECREF(bacnet_object_identifier);
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = BACNETOBJECTIDENTIFIER;
  tag->c_data.class = APPLICATION;
  return 1;
}

////
// (Re)encode an existing Tag object as a BACnet Object Identifier.
static PyObject *bacnet_object_identifier_encode(PyObject *self, PyObject *args)
{
  PyObject *value = NULL;
  tag_object *this = (tag_object*)self;

  if (!PyArg_ParseTuple(args, "O", &value)) {
    return NULL;
  }
  if (!encode_bacnet_object_identifier(this, value)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef bacnet_object_identifier_methodlist[] = {
  {"encode", (PyCFunction)bacnet_object_identifier_encode, METH_VARARGS},
  {NULL}
};

static PyObject *bacnet_object_identifier_getattr(PyObject *self, char *name)
{
  PyObject *result = NULL;
  tag_object *this = (tag_object *)self;
  if (strcmp(name, "value") == 0) {
    if (this->c_data.value == Py_None) {
      this->c_data.value =
	data_decode_bacnet_object_identifier(this->c_data.data,
					     this->c_data.length);
    }
    Py_XINCREF(this->c_data.value);
    return this->c_data.value;
  }
  result = Py_FindMethod(bacnet_object_identifier_methodlist, self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not cleared, it will be incorrectly rasied
			// later for no apparent reason.
  return tag_getattr(self, name);
}

static int tag_setattr(PyObject *self, char *name, PyObject *value)
{
  tag_object *this = (tag_object *)self;
  return PyMember_Set((char *)this, tag_memberlist, name, value);
}

static PyObject *encode_and_decode_exclusive(void)
{
  char *msg = "encoding and decoding arguments are mutually exclusive";
  broadway_raise("ETypeError", PyString_FromString(msg), NULL);
  return NULL;
}

static PyObject *too_many_args(void)
{
  char *msg = "too many arguments";
  broadway_raise("ETypeError", PyString_FromString(msg), NULL);
  return NULL;
}

////
// @fixme Use less memory...
static int encode_context(tag_object *tag,
			  PyObject *number, PyObject *data_object)
{
  const char *msg;
  unsigned char *next;
  unsigned char *data;
  unsigned char *buffer;
  const unsigned char *source;
  int length;
  PyObject *encoded_object = NULL;
  long long tag_number = PyInt_AsLong(number);

  if (PyErr_Occurred()) {
    PyErr_Clear();
    tag_number = PyLong_AsLongLong(number);
    if (PyErr_Occurred()) {
      return 0;
    }
  }
  if (tag_number < 0 || tag_number > 254) {
    broadway_raise_invalid_ulong(tag_number, "number",
				 "tag number must be between 0 and 254");
    return 0;
  }
  tag_free_c_data(tag);
  source = NULL;
  if (data_object) {
    if (is_buffer(data_object)) {
      broadway_get_buffer(&source, &length, data_object); 
    } else {
      encoded_object = PyObject_GetAttrString(data_object, "encoding");
      if (encoded_object) {
	broadway_get_buffer(&source, &length, encoded_object);
      }
    }
    if (!source) {
      if (encoded_object) {
	Py_DECREF(encoded_object);
      }
      msg = "data must be a StringType object, an ArrayType object or"
	" support the encoding attribute";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
      return 0;
    }
  } else {
    // There is no data.
    source = NULL;
    length = 0;
  }
  buffer = malloc(length+1+1+1+4); /* Worst case size:
				    * 1 byte for the tag "header"
				    * 1 byte for an extended tag number.
				    * 1 byte for an extended length reference.
				    * 4 bytes for a 32-bit length.
				    */
  if (!buffer) {
    if (encoded_object) {
      Py_DECREF(encoded_object);
    }
    msg = "could not allocate sufficient memory";
    broadway_raise("EMemoryError", PyString_FromString(msg), NULL);
  }
  n_Outstanding_Mallocs += 1;
  *buffer = '\x08';
  next = set_tag_number(buffer, tag_number);
  data = set_tag_length(buffer, next, length);
  if (source) {
    next = set_tag_data(data, source, length);
  } else {
    // There is no data.
    next = data;
  }
  if (encoded_object) {
    Py_DECREF(encoded_object);
  }
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, next-buffer);
  free(buffer);
  n_Outstanding_Mallocs -= 1;
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + (next-buffer);
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next - length;
  tag->c_data.length = length;
  tag->c_data.number = tag_number;
  tag->c_data.class = CONTEXT;
  return 1;
}

static int encode_open(tag_object *tag, PyObject *number)
{
  int length;
  unsigned char *next;
  unsigned char buffer[2] = "\x0E\x00";
  long n = PyInt_AsLong(number);
  if (PyErr_Occurred()) {
    return 0;
  }
  tag_free_c_data(tag);
  next = set_tag_number(buffer, n);
  if (!next) {
    return 0;
  }
  length = next - buffer;
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, length);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + length;
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next;
  tag->c_data.length = 0;
  tag->c_data.number = (unsigned char)n;
  tag->c_data.class = OPEN;
  return 1;
}
static int encode_close(tag_object *tag, PyObject *number)
{
  int length;
  unsigned char *next;
  unsigned char buffer[2] = "\x0F\x00";
  long n = PyInt_AsLong(number);
  if (PyErr_Occurred()) {
    return 0;
  }
  tag_free_c_data(tag);
  next = set_tag_number(buffer, n);
  if (!next) {
    return 0;
  }
  length = next - buffer;
  tag->c_data.buffer = PyString_FromStringAndSize(buffer, length);
  if (!tag->c_data.buffer) {
    return 0;
  }
  n_Buffer_References += 1;
  tag->c_data.start = PyString_AS_STRING(tag->c_data.buffer);
  tag->c_data.next = tag->c_data.start + length;
  tag->c_data.end = tag->c_data.next;
  tag->c_data.data = tag->c_data.next;
  tag->c_data.length = 0;
  tag->c_data.number = (unsigned char)n;
  tag->c_data.class = CLOSE;
  return 1;
}
static int encode_construct(tag_object *tag,
			    PyObject *number, PyObject *values)
{
  int (*Size)(PyObject *p);
  PyObject* (*GetItem)(PyObject *p, int pos);
  int len;
  PyObject *item, *list;
  char *msg;
  long n;

  if (number == Py_None) {
    n = 255; // Just a container, not really a tag.
  } else {
    n = PyInt_AsLong(number);
    if (PyErr_Occurred()) {
      return 0;
    }
    if (n < 0 || n > 254) {
      broadway_raise_invalid_ulong(n, "number",
				   "tag number must be between 0 and 254 "
				   "or None");
    }
  }
  if (values) {
    if (PyList_Check(values)) {
      Size = PyList_Size;
      GetItem = PyList_GetItem;
    } else if (PyTuple_Check(values)) {
      Size = PyTuple_Size;
      GetItem = PyTuple_GetItem;
    } else {
      msg = "values must be in a list or tuple";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
      return 0;
    }
    len = Size(values);
    if (PyErr_Occurred()) {
      return 0;
    }
    // Create a list to copy the objects.  
    list = PyList_New(len);
    if (!list) {
      return 0;
    }
    // Copy the sequence into a list. (backwords 'cause I can)
    while (--len >= 0) {
      item = GetItem(values, len);
      if (!item) {
	Py_DECREF(list);
	return 0;
      }
      if (!_is_tag(item)) {
	Py_DECREF(list);
	msg = "values must only contain be in tag objects";
	broadway_raise("ETypeError", PyString_FromString(msg), NULL);
	return 0;
      }
      if (PyList_SetItem(list, len, item)) {
	Py_DECREF(list);
	return 0;
      }
      Py_INCREF(item);
    }
  } else {
    list = PyList_New(0);
    if (!list) {
      return 0;
    }
  }
  tag_set_c_data_as_construct(tag, list, (unsigned char)n);
  return 1;
}

static char __doc__Tag[] = "\n"
"##\n"
"# MontyDoc string for the Tag factory.\n"
"#\n";
static PyObject *Tag(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOO", kwlist,
				   &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();

  this = PyObject_New(tag_object, &TagType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this); // Accounted for (in new);
      return NULL;
    }
  }
  return (PyObject*)this;
}

static char __doc__Context[] = "\n"
"##\n"
"# MontyDoc string for the Context factory.\n"
"#\n";
static PyObject *Context(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"number", "data", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *number = NULL;
  PyObject *data = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOOO", kwlist,
				   &number, &data, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if ((number||data)&&(decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &ContextType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (number) {
    if (!encode_context(this, number, data)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("number or None required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Open[] = "\n"
"##\n"
"# MontyDoc string for the Open factory.\n"
"#\n";
static PyObject *Open(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"number", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *number = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &number, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (number && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &OpenType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (number) {
    if (!encode_open(this, number)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("number required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Close[] = "\n"
"##\n"
"# MontyDoc string for the Close factory.\n"
"#";
static PyObject *Close(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"number", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *number = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &number, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (number && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &CloseType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (number) {
    if (!encode_close(this, number)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("number required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Construct[] = "\n"
"##\n"
"# MontyDoc string for the Construct factory.\n"
"#";
static PyObject *Construct(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"number", "values", "bogus", "decode", "offset",
			   NULL};
  tag_object *this;
  PyObject *number = NULL;
  PyObject *values = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOOO", kwlist,
				   &number, &values,
				   &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (number && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &ConstructType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (number) {
    if (!encode_construct(this, number, values)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("number required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Null[] = "\n"
"##\n"
"# MontyDoc string for the Null factory.\n"
"#";
static PyObject *Null(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOO", kwlist,
				   &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();

  this = PyObject_New(tag_object, &NullType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    if (!encode_null(this)) {
      Py_DECREF(this);
      return NULL;
    }
  }
  return (PyObject*)this;
}
static char __doc__Boolean[] = "\n"
"##\n"
"# MontyDoc string for the Boolean factory.\n"
"#";
static PyObject *Boolean(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &BooleanType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_boolean(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__UnsignedInteger[] = "\n"
"##\n"
"# MontyDoc string for the UnsignedInteger factory.\n"
"#";
static PyObject *UnsignedInteger(PyObject *self,
				 PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &UnsignedIntegerType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_unsigned_integer(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__SignedInteger[] = "\n"
"##\n"
"# MontyDoc string for the SignedInteger factory.\n"
"#";
static PyObject *SignedInteger(PyObject *self,
			       PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &SignedIntegerType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_signed_integer(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Real[] = "\n"
"##\n"
"# MontyDoc string for the Real factory.\n"
"#";
static PyObject *Real(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &RealType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_real(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Double[] = "\n"
"##\n"
"# MontyDoc string for the Double factory.\n"
"#";
static PyObject *Double(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &DoubleType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_double(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__OctetString[] = "\n"
"##\n"
"# MontyDoc string for the OctetString factory.\n"
"#";
static PyObject *OctetString(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &OctetStringType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_octet_string(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__CharacterString[] = "\n"
"##\n"
"# MontyDoc string for the CharacterString factory.\n"
"#";
static PyObject *CharacterString(PyObject *self,
				 PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &CharacterStringType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_character_string(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__BitString[] = "\n"
"##\n"
"# MontyDoc string for the BitString factory.\n"
"#";
static PyObject *BitString(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &BitStringType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_bit_string(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Enumerated[] = "\n"
"##\n"
"# MontyDoc string for the Enumerated factory.\n"
"#";
static PyObject *Enumerated(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &EnumeratedType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_enumerated(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Date[] = "\n"
"##\n"
"# MontyDoc string for the Date factory.\n"
"#";
static PyObject *Date(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &DateType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_date(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__Time[] = "\n"
"##\n"
"# MontyDoc string for the Time factory.\n"
"#";
static PyObject *Time(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &TimeType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_time(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}
static char __doc__BACnetObjectIdentifier[] = "\n"
"##\n"
"# MontyDoc string for the BACnetObjectIdentifier factory.\n"
"#";
static PyObject *BACnetObjectIdentifier(PyObject *self, PyObject *args,
					PyObject *keywords)
{
  static char *kwlist[] = {"value", "bogus", "decode", "offset", NULL};
  tag_object *this;
  PyObject *value = NULL;
  PyObject *bogus = NULL;
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOO", kwlist,
				   &value, &bogus, &decode, &offset)) {
    return NULL;
  }
  if (bogus) return too_many_args();
  if (value && (decode||offset)) return encode_and_decode_exclusive();

  this = PyObject_New(tag_object, &BACnetObjectIdentifierType);
  if (!this) {
    return NULL;
  }
  tag_init_c_data(this);
  n_Tag_instances += 1;
  if (decode) {
    if (!decode_to_tag(this, decode, offset)) {
      Py_DECREF(this);
      return NULL;
    }
  } else if (value) {
    if (!encode_bacnet_object_identifier(this, value)) {
      Py_DECREF(this);
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
		   PyString_FromString("value required for encode"),
		   NULL);
    Py_DECREF(this);
    return NULL;
  }
  return (PyObject*)this;
}

////
// @note open_tag is NULL or borrowed.
tag_object *buffer_as_construct(tag_object *open_tag,
				PyObject *decode, PyObject *offset)
{
  tag_object *next_tag;
  const unsigned char *buffer;
  char *msg;
  unsigned long length;
  tag_object *result = PyObject_New(tag_object, &ConstructType);
  
  if (!result) {
    return NULL;
  }
  n_Tag_instances += 1;

  tag_init_c_data_as_construct(result);
  if (!result->c_data.value) {
    Py_DECREF(result);
    return NULL;
  }
  if (!open_tag) {
    next_tag = PyObject_New(tag_object, &TagType);
    if (!next_tag) {
      Py_DECREF(result);
      return NULL;
    }
    n_Tag_instances += 1;
    tag_init_c_data(next_tag);
    // Use decode_to_tag to prime the pump.
    if (!decode_to_tag(next_tag, decode, offset)) {
      Py_DECREF(result);
      Py_DECREF(next_tag);
      return NULL;
    }
    if (next_tag->c_data.class == OPEN) {
      // @note:  buffer_as_construct borrows the open tag and returns
      //         a reference to a new construct.
      tag_object *new_open_tag = next_tag;
      next_tag = buffer_as_construct(new_open_tag, decode, offset);
      Py_DECREF(new_open_tag);
      if (!next_tag) {
	Py_DECREF(result);
	return NULL;
      }
    } else if (next_tag->c_data.class == CLOSE) {
      Py_DECREF(next_tag);
      Py_DECREF(result);
      msg = "Unexpected close tag";
      broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
      return NULL;
    }
    if (PyList_Append(result->c_data.value, (PyObject *)next_tag) != 0) {
      Py_DECREF(result);
      Py_DECREF(next_tag);
      return NULL;
    }
    // Lose our reference to next_tag.
    Py_DECREF(next_tag);
  } else {
    next_tag = open_tag;	// Parsing will continue from the open_tag.
				// Give the construct a valid tag number.
    result->c_data.number = open_tag->c_data.number;
  }
  while (next_tag->c_data.next < next_tag->c_data.end) {
    buffer = next_tag->c_data.next;
    length = next_tag->c_data.end - next_tag->c_data.next;
    next_tag = PyObject_New(tag_object, &TagType);
    if (!next_tag) {
      Py_DECREF(result);
      return NULL;
    }
    n_Tag_instances += 1;
    tag_init_c_data(next_tag);
    if (!buffer_to_tag(next_tag, decode, buffer, length)) {
      Py_DECREF(result);
      Py_DECREF(next_tag);
      return NULL;
    }
    if (next_tag->c_data.class == OPEN) {
      // @note:  buffer_as_constrct borrows the open tag and returns
      //         a new reference.
      tag_object *new_open_tag = next_tag;
      next_tag = (tag_object*)buffer_as_construct(new_open_tag, decode, offset);
      Py_DECREF(new_open_tag);
      if (!next_tag) {
	Py_DECREF(result);
	return NULL;
      }
    } else if (next_tag->c_data.class == CLOSE) {
      if (!open_tag) {
	Py_DECREF(next_tag);
	Py_DECREF(result);
	msg = "Unexpected close tag";
	broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
	return NULL;
      }
      if (open_tag->c_data.number != next_tag->c_data.number) {
	Py_DECREF(next_tag);
	Py_DECREF(result);
	msg = "Incorrect close tag";
	broadway_raise("EParseFailure", PyString_FromString(msg), NULL);
	return NULL;
      }
      // Set result such that parsing will continue after the close tag.
      result->c_data.start = next_tag->c_data.start;
      result->c_data.next = next_tag->c_data.next;
      result->c_data.end = next_tag->c_data.end;
      result->c_data.data = next_tag->c_data.data;
      // Lose the close tag.
      Py_DECREF(next_tag);
      return result;
    }
    if (PyList_Append(result->c_data.value, (PyObject *)next_tag) != 0) {
      Py_DECREF(result);
      Py_DECREF(next_tag);
      return NULL;
    }
    // Lose our reference to next_tag.
    Py_DECREF(next_tag);
  }
  return result;
}

static char __doc__decode[] = "\n"
"##\n"
"# MontyDoc string for decode.\n"
"#";
static PyObject *decode(PyObject *self, PyObject *args)
{
  PyObject *decode = NULL;
  PyObject *offset = NULL;

  if (!PyArg_ParseTuple(args, "O|O", &decode, &offset)) {
    return NULL;
  }
  return (PyObject*)buffer_as_construct(NULL, decode, offset);
}
static char __doc__encode[] = "\n"
"##\n"
"# MontyDoc string for encode.\n"
"# @param construct A Construct (or any object with an &quot;encoding&quot;\n"
"#                  attribute), list or tuple of tags.\n"
"# @return An encoded string representing the <code>construct</code>.\n"
"#";
static PyObject *encode(PyObject *self, PyObject *args)
{
  PyObject *object;
  PyObject *encoding;
  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  if (PyList_Check(object) || PyTuple_Check(object)) {
    args = PyTuple_New(2);
    Py_INCREF(Py_None);
    Py_INCREF(object);
    PyTuple_SetItem(args, 0, Py_None);
    PyTuple_SetItem(args, 1, object);
    object = Construct(self, args, NULL);
    Py_DECREF(args);
    if (!object) {
      return NULL;
    }
  } else {
    // This way we can always decrement it after invoking it's "encoding"
    // attribute.
    Py_INCREF(object);
  }
  encoding = PyObject_GetAttrString(object, "encoding");
  Py_DECREF(object);
  return encoding;
}

static PyObject *count_Tag_instances(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return PyInt_FromLong(n_Tag_instances);
}
static PyObject *count_outstanding_mallocs(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return PyInt_FromLong(n_Outstanding_Mallocs);
}
static PyObject *count_buffer_references(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return PyInt_FromLong(n_Buffer_References);
}

static PyMethodDef module_functions[] = {
  {"decode", decode, METH_VARARGS, __doc__decode},
  {"encode", encode, METH_VARARGS, __doc__encode},
  {"Tag", (PyCFunction)Tag, METH_VARARGS | METH_KEYWORDS, __doc__Tag},
  {"Context", (PyCFunction)Context, METH_VARARGS | METH_KEYWORDS,
   __doc__Context},
  {"Open", (PyCFunction)Open, METH_VARARGS | METH_KEYWORDS,
   __doc__Open},
  {"Close", (PyCFunction)Close, METH_VARARGS | METH_KEYWORDS,
   __doc__Close},
  {"Construct", (PyCFunction)Construct, METH_VARARGS | METH_KEYWORDS,
   __doc__Construct},
  {"Null", (PyCFunction)Null, METH_VARARGS | METH_KEYWORDS, __doc__Null},
  {"Boolean", (PyCFunction)Boolean, METH_VARARGS | METH_KEYWORDS,
   __doc__Boolean},
  {"UnsignedInteger", (PyCFunction)UnsignedInteger,
   METH_VARARGS | METH_KEYWORDS, __doc__UnsignedInteger},
  {"SignedInteger", (PyCFunction)SignedInteger, METH_VARARGS | METH_KEYWORDS,
   __doc__SignedInteger},
  {"Real", (PyCFunction)Real, METH_VARARGS | METH_KEYWORDS, __doc__Real},
  {"Double", (PyCFunction)Double, METH_VARARGS | METH_KEYWORDS, __doc__Double},
  {"OctetString", (PyCFunction)OctetString, METH_VARARGS | METH_KEYWORDS,
   __doc__OctetString},
  {"CharacterString", (PyCFunction)CharacterString,
   METH_VARARGS | METH_KEYWORDS, __doc__CharacterString},
  {"BitString", (PyCFunction)BitString, METH_VARARGS | METH_KEYWORDS,
   __doc__BitString},
  {"Enumerated", (PyCFunction)Enumerated, METH_VARARGS | METH_KEYWORDS,
   __doc__Enumerated},
  {"Date", (PyCFunction)Date, METH_VARARGS | METH_KEYWORDS,
   __doc__Date},
  {"Time", (PyCFunction)Time, METH_VARARGS | METH_KEYWORDS, __doc__Time},
  {"BACnetObjectIdentifier", (PyCFunction)BACnetObjectIdentifier,
   METH_VARARGS | METH_KEYWORDS,
   __doc__BACnetObjectIdentifier},
  {"count_Tag_instances", (PyCFunction)count_Tag_instances, METH_VARARGS},
  {"count_outstanding_mallocs", (PyCFunction)count_outstanding_mallocs,
   METH_VARARGS},
  {"count_buffer_references", (PyCFunction)count_buffer_references,
   METH_VARARGS},
  {NULL}
};

void inittag(void)
{
  int i;
  char *constant;

  // Create the new module definition.
  PyObject *module = Py_InitModule("tag", module_functions);

  // Load references to shared code.
  load_lib_references();
  load_data_references();

  // Create the "derived" Tag types.
  init_types();

  // Add the debug flag the module.
  PyModule_AddObject(module, "debug", PyInt_FromLong(0));

  // Add the new 'types' to the module.
  for (i=0; application_type[i].type_object; i++) {
    Py_INCREF(application_type[i].type_object);
    PyModule_AddObject(module, application_type[i].type_name,
		       (PyObject*)application_type[i].type_object);
  }
  for (i=0; other_type[i].type_object; i++) {
    Py_INCREF(other_type[i].type_object);
    PyModule_AddObject(module, other_type[i].type_name,
		       (PyObject*)other_type[i].type_object);
  }

  // Get a reference to this modules namespace dictionary.
  __dict__ = PyModule_GetDict(module);

  // Define the application tag type constants.
  for (i=0; (constant = (char*)apptag_constants[i]); i++) {
    PyModule_AddIntConstant(module, constant, i);
  }

  // Add the modules documentation.
  PyModule_AddStringConstant(module, "__doc__", __doc__);
}

static PyTypeObject TagType = {
  PyObject_HEAD_INIT(&PyType_Type)	/* PyObject_VAR_HEAD */
  0,					/* PyObject_VAR_HEAD */

  "Tag",		/* char *tp_name; */
  sizeof(tag_object),	/* int tp_basicsize; */
  0,			/* int tp_itemsize;       * not used much */
  tag_dealloc,		/* destructor tp_dealloc; */
  0,			/* printfunc  tp_print;   */
  tag_getattr,		/* getattrfunc  tp_getattr; * __getattr__ */
  tag_setattr,		/* setattrfunc  tp_setattr;  * __setattr__ */
  0,			/* cmpfunc  tp_compare;  * __cmp__ */
  0,			/* reprfunc  tp_repr;    * __repr__ */
  0,			/* PyNumberMethods *tp_as_number; */
  0,			/* PySequenceMethods *tp_as_sequence; */
  0,			/* PyMappingMethods *tp_as_mapping; */
  0,			/* hashfunc tp_hash;     * __hash__ */
  0,			/* ternaryfunc tp_call;  * __call__ */
  0,			/* reprfunc tp_str;      * __str__ */
  0,			/* getattrofunc tp_getattro; */
  0,			/* setattrofunc tp_setattro; */
  0,			/* PyBufferProcs *tp_as_buffer; */
  0,			/* long tp_flags; */
  0,			/* char *tp_doc; * Documentation string * */
  0,			/* traverseproc tp_traverse; */
  0,			/* inquiry tp_clear; */
  0,			/* richcmpfunc tp_richcompare; */
  0,			/* long tp_weaklistoffset; */
};
