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
////
// @fixme Implement data module in several files.
// @fixme Move shared helper code into it's own library (.a or .so) that
//        is separate from files that assume they are part of a module.
// @fixme Get consistent with EInvalidValue and EParseFailure
#include <Python.h>
#include <structmember.h>

#include <byteswap.h>

#include "lib.h"
#include "_data.h"

static long n_BACnetObjectIdentifier_instances = 0;
static long n_Time_instances = 0;
static long n_Date_instances = 0;
#if 1
static const char *lots_of_fs =
     "\377\377\377\377\377\377\377\377\377\377\377\377"
     "\377\377\377\377\377\377\377\377\377\377\377\377";
#endif

struct Date {
  unsigned char year;
  unsigned char month;
  unsigned char day;
  unsigned char day_of_week;
#if 1
  unsigned char foot_print[4];
#endif
};

typedef struct {
  PyObject_HEAD
  struct Date c_data;
} date_object;

struct Time {
  unsigned char hour;
  unsigned char minute;
  unsigned char second;
  unsigned char hundredths;
#if 1
  unsigned char foot_print[4];
#endif
};

typedef struct {
  PyObject_HEAD
  struct Time c_data;
} time_object;

struct BACnetObjectIdentifier {
  UINT32 id;
  UINT32 instance_number;
  UINT16 object_type;
#if 1
  unsigned char foot_print[2];
#endif
};

typedef struct {
  PyObject_HEAD
  struct BACnetObjectIdentifier c_data;
} bacnet_object_identifier_object;

PyTypeObject data_DateType;
PyTypeObject data_TimeType;
PyTypeObject data_BACnetObjectIdentifierType;

PyObject *data_CharacterString;
PyObject *data_BitString;

static int _decode_null(const char *buffer, int len)
{
  if (len != 1 || *buffer != '\0') {
    return -1;
  }
  return 1;
}
static char  __doc__decode_null[] = "\n"
"##\n"
"# Return the Python native representation of the BACnet octet NULL.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return None\n"
"# @note This only decode\'s an application NULL.";
static PyObject *decode_null(PyObject *this, PyObject *args)
{
  PyObject *object;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, object);
  if (!buffer) {
    return NULL;
  }
  if (_decode_null(buffer, length) < 0) {
    broadway_raise_invalid_object(object, "buffer", NULL);
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}
static char __doc__encode_null[] = "\n"
"##\n"
"# Return the BACnet encoding of NULL.\n"
"# @return A string of bytes that represents a BACnet NULL value.\n"
"# @note This only returns an application NULL.";
static PyObject *encode_null(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return PyString_FromStringAndSize("\0", 1);
}

static int _decode_boolean(const char *buffer, int len)
{
  if (len != 1 || (*buffer != '\0' && *buffer != '\1')) {
    return -1;
  }
  return *buffer;
}
static char __doc__decode_boolean[] = "\n"
"##\n"
"# Return the Python native representation of the boolean encoded in BACnet\n"
"# the octets.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return 1 if the boolean is true, otherwise 0.\n"
"# @note This only decode\'s an context boolean.";
static PyObject *decode_boolean(PyObject *this, PyObject *args)
{
  PyObject *object;
  const unsigned char *buffer;
  UINT32 length;
  int result;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, object);
  if (!buffer) {
    return NULL;
  }
  result = _decode_boolean(buffer, length);
  if (result < 0) {
    broadway_raise_invalid_object(object, "buffer", NULL);
    return NULL;
  }
  return PyInt_FromLong(result);
}

static char __doc__encode_boolean[] = "\n"
"##\n"
"# Return the BACnet encoding of a boolean.\n"
"# @return A string of bytes that represents a BACnet NULL value.\n"
"# @note This only returns an context encoded boolean.";
static PyObject *encode_boolean(PyObject *this, PyObject *args)
{
  int value;
  PyObject *object;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  if (!PyInt_Check(object)) {
    broadway_raise("ETypeError",
                   PyString_FromString("Only integers can "
                                       "be encoded as booleans."), NULL);
    return NULL;
  }
  value = PyInt_AsLong(object);
  if (value != 0 && value != 1) {
    broadway_raise_invalid_object(object, "buffer", NULL);
    return NULL;
  }
  return PyString_FromStringAndSize((value) ? "\1" : "\0", 1);
}

// @note No validation, only call with length [1,8].
UINT64 data_decode_unsigned_integer(const unsigned char *buffer, int len)
{
  UINT64 result = 0;
  while (len--) {
    result = (result << 8) | *buffer++;
  }
  return result;
}
static char __doc__decode_unsigned_integer[] = "\n"
"##\n"
"# Return the Python native representation of the BACnet unsigned integer\n"
"# encoded in the octets.of <code>buffer</code>.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return A Python IntType or LongType representing the enceoded value.  The\n"
"#         smaller Python type that can represent the value as a positive\n"
"#         integer is returned.";
static PyObject *decode_unsigned_integer(PyObject *this, PyObject *args)
{
  PyObject *object;
  const unsigned char *buffer;
  UINT32 length;
  UINT64 result;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, object);
  if (!buffer) {
    return NULL;
  }
  if (length < 1 || length > 8) {
    broadway_raise_invalid_object(object, "buffer", NULL);
    return NULL;
  }
  result = data_decode_unsigned_integer(buffer, length);
  if (length <= 4 && !(result & 0x80000000)) {
    return PyInt_FromLong(result);
  }
  return PyLong_FromUnsignedLongLong(result);
}

////
// @note Perfoms the minimum length encoding that will fit the value.
int data_encode_unsigned_integer(char *buffer, int len, UINT64 value)
{
  UINT64 mask = 0xff00000000000000ULL;
  int shift;
  int required;

  for (shift=7*8;shift && !(mask & value);shift-=8) {
    // Loop exits with the smallest required shift value.
    mask = mask >> 8;
  }
  required = (shift / 8) + 1;
  if (required > len) {
    return -1;
  }
  while (shift >= 0) {
    *buffer++ = (unsigned char)(value >> shift);
    shift -= 8;
  }
  return required;
}
static char __doc__encode_unsigned_integer[] = "\n"
"##\n"
"# Return the BACnet encoding of an unsigned.integer in the shortest possible\n"
"# representation.\n"
"# @param value The integer or long integer to encode.\n"
"# @return A string of bytes that represents a BACnet unsigned integer value.\n"
"# @note Values -1 through -2147483648 are treated as 4294967295L through\n"
"#       2147483648L (0xffffffff through 0x80000000L).\n"
"# @note Negative long integers will raise an EOverflow.";
static PyObject *encode_unsigned_integer(PyObject *this, PyObject *args)
{
  unsigned char buffer[8];
  int length;
  UINT64 value;
  PyObject *object;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  if (PyInt_Check(object)) {
    value = (UINT32)PyInt_AsLong(object);
  } else if (PyLong_Check(object)) {
    value = PyLong_AsUnsignedLongLong(object);
    if (PyErr_Occurred() != NULL) {
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
                   PyString_FromString("Only integers and long integers can "
                                       "be encoded as unsigned integers."),
                   NULL);
    return NULL;
  }
  length = data_encode_unsigned_integer(buffer, sizeof(buffer), value);
  if (length < 1) {
    broadway_raise("EOverflow", PyString_FromString("Value too large."), NULL);
    return NULL;
  }
  return PyString_FromStringAndSize(buffer, length);
}

// @note No validation, only call with length [1,8].
INT64 data_decode_signed_integer(const unsigned char *buffer, int len)
{
  UINT64 result = 0;
  if (*buffer & 0x80) {
    // Super-duper sign extension.  It works, trust me...
    result = 0xffffffffffffffffLL;
  }
  while (len--) {
    result = (result << 8) | *buffer++;
  }
  return result;
}
static char __doc__decode_signed_integer[] = "\n"
"##\n"
"# Return the Python native representation of the BACnet signed integer\n"
"# encoded in the octets.of <code>buffer</code>.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return A Python IntType or LongType representing the enceoded value.  The\n"
"#         smaller Python type that can represent the value is returned.";
static PyObject *decode_signed_integer(PyObject *this, PyObject *args)
{
  PyObject *object;
  const unsigned char *buffer;
  UINT32 length;
  INT64 result;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, object);
  if (!buffer) {
    return NULL;
  }
  if (length < 1 || length > 8) {
    broadway_raise_invalid_object(object, "buffer", NULL);
    return NULL;
  }
  result = data_decode_signed_integer(buffer, length);
  if (length <= 4) {
    return PyInt_FromLong(result);
  }
  return PyLong_FromLongLong(result);
}

////
// @note Prefoms the minimum length encoding that will fit the value.
int data_encode_signed_integer(char *buffer, int len, INT64 value)
{
  UINT64 sign_byte, next_sign_bit, mask;

  if (value & 0x8000000000000000ULL) {
    // Adjust negative value to the shortest representation.
    // There is probably an easier way to do this.  Basically, the idea
    // is that if the most significant byte's value is 0xff and the second
    // most significant byte's sign bit is set, then the most significant
    // byte can be discarded without a loss of information.
    for (sign_byte = 0xff00000000000000ULL,
           next_sign_bit = 0x0080000000000000ULL,
           mask = 0x00ffffffffffffffULL;
         (sign_byte & value) == sign_byte && next_sign_bit & value;
         sign_byte = sign_byte >> 8,
           next_sign_bit = next_sign_bit >> 8,
           mask = mask >> 8) {
      value = value & mask;
    }
  } else if (!(value & 0xFF00000000000000ULL)) {
    // With positive values, it may be necessary to add an initial '\0' to
    // prevent the byte-string from being decoded as a negative number.
    for (sign_byte = 0x0080000000000000ULL, mask = 0x00ff000000000000ULL;
         mask && !(mask & value);
         sign_byte = sign_byte >> 8, mask = mask >> 8) {
    }
    if (mask && (sign_byte & value)) {
      // The first non-zero byte has the high-bit set.  Pad the
      // buffer so the byte-stream is not interpretted as a
      // negative number.
      *buffer = '\0';
      return data_encode_unsigned_integer(buffer+1, len-1, value) + 1;
    }
  }
  return data_encode_unsigned_integer(buffer, len, value);
}
static char __doc__encode_signed_integer[] = "\n"
"##\n"
"# Return the BACnet encoding of a signed.integer in the shortest possible\n"
"# representation.\n"
"# @param value The integer or long integer to encode.\n"
"# @return A string of bytes that represents a BACnet signed integer value.";
static PyObject *encode_signed_integer(PyObject *this, PyObject *args)
{
  unsigned char buffer[9];
  int length;
  INT64 value;
  PyObject *object;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  if (PyInt_Check(object)) {
    value = PyInt_AsLong(object);
  } else if (PyLong_Check(object)) {
    value = PyLong_AsLongLong(object);
    if (PyErr_Occurred() != NULL) {
      return NULL;
    }
  } else {
    broadway_raise("ETypeError",
                   PyString_FromString("Only integers and long integers can "
                                       "be encoded as signed integers."),
                   NULL);
    return NULL;
  }
  length = data_encode_signed_integer(buffer, sizeof(buffer), value);
  if (length < 1) {
    broadway_raise("EOverflow", PyString_FromString("Value too large."), NULL);
    return NULL;
  }
  return PyString_FromStringAndSize(buffer, length);
}

#if __BYTE_ORDER == __BIG_ENDIAN
float data_decode_real(const char *buffer, int len)
{
  float result;
  if (len != 4) {
    return NAN;
  }
  result = *(float*)buffer;
  return result;
}
#else
float data_decode_real(const char *buffer, int len)
{
  float result;
  UINT32 four_bytes;
  if (len != 4) {
    return NAN;
  }
  four_bytes = bswap_32(*(UINT32*)buffer);
  result = *(float*)&four_bytes;
  return result;
}
#endif
static char __doc__decode_real[] = "\n"
"##\n"
"# Return the Python native representation of the BACnet real\n"
"# encoded in the octets.of <code>buffer</code>.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return A Python FloatType representing the enceoded value.";
static PyObject *decode_real(PyObject *this, PyObject *args)
{
  PyObject *object;
  const unsigned char *buffer;
  UINT32 length;
  float result;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, object);
  if (!buffer) {
    return NULL;
  }
  if (length != 4) {
    broadway_raise_invalid_object(object, "buffer", NULL);
    return NULL;
  }
  result = data_decode_real(buffer, length);
  return PyFloat_FromDouble(result);
}

#if __BYTE_ORDER == __BIG_ENDIAN
int data_encode_real(char *buffer, int len, float value)
{
  if (len < 4) {
    return -1;
  }
  *(float*)buffer = value;
  return 4;
}
#else
int data_encode_real(char *buffer, int len, float value)
{
  if (len < 4) {
    return -1;
  }
  *(UINT32*)buffer = bswap_32(*(UINT32*)&value);
  return 4;
}
#endif
static char __doc__encode_real[] = "\n"
"##\n"
"# Return the BACnet encoding of a real.\n"
"# @param value The Python float to encode.\n"
"# @return A string of bytes that represents a BACnet real value.";
static PyObject *encode_real(PyObject *this, PyObject *args)
{
  unsigned char buffer[4];
  int length;
  double value;
  PyObject *object;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  if (PyFloat_Check(object)) {
    value = PyFloat_AsDouble(object);
  } else {
    broadway_raise("ETypeError",
                   PyString_FromString("Only floats can "
                                       "be encoded as floats."),
                   NULL);
    return NULL;
  }
  length = data_encode_real(buffer, sizeof(buffer), value);
  if (length < 1) {
    broadway_raise("EOverflow", PyString_FromString("Value too large."), NULL);
    return NULL;
  }
  return PyString_FromStringAndSize(buffer, length);
}

#if __BYTE_ORDER == __BIG_ENDIAN
double data_decode_double(const char *buffer, int len)
{
  double result;
  if (len != 8) {
    return NAN;
  }
  result = *(double*)buffer;
  return result;
}
#else
double data_decode_double(const char *buffer, int len)
{
  double result;
  UINT64 eight_bytes;
  if (len != 8) {
    return NAN;
  }
  eight_bytes = bswap_64(*(UINT64*)buffer);
  result = *(double*)&eight_bytes;
  return result;
}
#endif
static char __doc__decode_double[] = "\n"
"##\n"
"# Return the Python native representation of the BACnet double\n"
"# encoded in the octets.of <code>buffer</code>.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return A Python FloatType representing the enceoded value.";
static PyObject *decode_double(PyObject *this, PyObject *args)
{
  PyObject *object;
  const unsigned char *buffer;
  UINT32 length;
  double result;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, object);
  if (!buffer) {
    return NULL;
  }
  if (length != 8) {
    broadway_raise_invalid_object(object, "buffer", NULL);
    return NULL;
  }
  result = data_decode_double(buffer, length);
  return PyFloat_FromDouble(result);
}

#if __BYTE_ORDER == __BIG_ENDIAN
int data_encode_double(const char *buffer, int len, double value)
{
  if (len < 8) {
    return -1;
  }
  *(double*)buffer = value;
  return 8;
}
#else
int data_encode_double(const char *buffer, int len, double value)
{
  UINT64 eight_bytes;
  if (len < 8) {
    return -1;
  }
  eight_bytes = *(UINT64*)&value;
  *(UINT64*)buffer = bswap_64(eight_bytes);
  return 8;
}
#endif
static char __doc__encode_double[] = "\n"
"##\n"
"# Return the BACnet encoding of a double.\n"
"# @param value The Python float to encode.\n"
"# @return A string of bytes that represents a BACnet double value.";
static PyObject *encode_double(PyObject *this, PyObject *args)
{
  unsigned char buffer[8];
  int length;
  double value;
  PyObject *object;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  if (PyFloat_Check(object)) {
    value = PyFloat_AsDouble(object);
  } else {
    broadway_raise("ETypeError",
                   PyString_FromString("Only floats can "
                                       "be encoded as floats."),
                   NULL);
    return NULL;
  }
  length = data_encode_double(buffer, sizeof(buffer), value);
  if (length < 1) {
    broadway_raise("EOverflow", PyString_FromString("Value too large."), NULL);
    return NULL;
  }
  return PyString_FromStringAndSize(buffer, length);
}

struct OctetString data_decode_octet_string(const char *buffer, int len)
{
  struct OctetString result;
  result.buffer = buffer;
  result.length = len;
  return result;
}
static char __doc__decode_octet_string[] = "\n"
"##\n"
"# Return a Python string representation of the BACnet octet string\n"
"# encoded in the octets.of <code>buffer</code>.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return A Python StringType representing the enceoded value.\n"
"# @note This is essentially a pass through...";
static PyObject *decode_octet_string(PyObject *this, PyObject *args)
{
  PyObject *object;
  const unsigned char *buffer;
  UINT32 length;
  struct OctetString result;

  if (!PyArg_ParseTuple(args, "O", &object)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, object);
  if (!buffer) {
    return NULL;
  }
  result = data_decode_octet_string(buffer, length);
  return PyString_FromStringAndSize(result.buffer, result.length);
}

static char __doc__encode_octet_string[] = "\n"
"##\n"
"# Return the BACnet encoding of a string as an octet string.\n"
"# @param value The Python float to encode.\n"
"# @return A string of bytes that represents a BACnet octet string.\n"
"# @note This is essentially a pass through...";
static PyObject *encode_octet_string(PyObject *this, PyObject *args)
{
  return decode_octet_string(this, args);
}

static PyObject *load_from_module(char *module, char *attr)
{
  PyObject *result = NULL;
  PyObject *_data = PyImport_ImportModule(module);
  if (_data != NULL) {
    PyObject *_data__dict__ = PyObject_GetAttrString(_data, "__dict__");
    if (_data__dict__ != NULL) {
      // Get a handle on the functions written in Python that we need.
      result = PyDict_GetItemString(_data__dict__, attr);
      Py_DECREF(_data__dict__);
    }
    Py_DECREF(_data);
  }
  return result;
}
PyObject *data_decode_character_string(const char *buffer, int len)
{
// Uses the Python decode_character_string.
  static PyObject *decode_character_string;
  PyObject *result;
  PyObject *args = PyTuple_New(1);

  if (decode_character_string == NULL) {
    decode_character_string = load_from_module("mpx.lib.bacnet._data",
					       "decode_character_string");
    Py_XINCREF(decode_character_string);
  }
  if (!PyCallable_Check(decode_character_string)) {
    PyErr_SetString(PyExc_TypeError,
		    "decode_character_string must be callable");
    return NULL;
  }
  PyTuple_SetItem(args, 0, PyString_FromStringAndSize(buffer, len));
  result = PyEval_CallObject(decode_character_string, args);
  Py_DECREF(args);
  return result;
}

PyObject *data_decode_bit_string(const char *buffer, int len)
{
// Uses the Python decode_bit_string.
  static PyObject *decode_bit_string;
  PyObject *result;
  PyObject *args = PyTuple_New(1);

  if (decode_bit_string == NULL) {
    decode_bit_string = load_from_module("mpx.lib.bacnet._data",
					 "decode_bit_string");
    Py_XINCREF(decode_bit_string);
  }
  if (!PyCallable_Check(decode_bit_string)) {
    PyErr_SetString(PyExc_TypeError,
		    "decode_bit_string must be callable");
    return NULL;
  }
  PyTuple_SetItem(args, 0, PyString_FromStringAndSize(buffer, len));
  result = PyEval_CallObject(decode_bit_string, args);
  Py_DECREF(args);
  return result;
}

static char __doc__decode_enumerated[] = "\n"
"##\n"
"# Return the Python native representation of the BACnet enumerated value\n"
"# encoded in the octets.of <code>buffer</code>.\n"
"# @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').\n"
"# @return A Python IntType or LongType representing the enceoded value.  The\n"
"#         smaller Python type that can represent the value as a positive\n"
"#         integer is returned.\n"
"# @note Enumerated types are encoded the same as unsigned integers.";
static PyObject *decode_enumerated(PyObject *this, PyObject *args)
{
  return decode_unsigned_integer(this, args);
}

static char __doc__encode_enumerated[] = "\n"
"##\n"
"# Return the BACnet encoding of an enumerated value (an unsigned.integer)\n"
"# in the shortest possible representation.\n"
"# @param value The integer or long integer to encode as an enumerated value.\n"
"# @return A string of bytes that represents a BACnet unsigned integer value.\n"
"# @note Values -1 through -2147483648 are treated as 4294967295L through\n"
"#       2147483648L (0xffffffff through 0x80000000L).\n"
"# @note Negative long integers will raise an EOverflow.\n"
"# @note Enumerated values are encoded exactly like unsigned integers";
static PyObject *encode_enumerated(PyObject *this, PyObject *args)
{
  return encode_unsigned_integer(this, args);
}

////
// @note Does not check type.
PyObject *data_encoded_date(PyObject *self)
{
  unsigned char buffer[4];
  date_object *this = (date_object *)self;
  buffer[0] = this->c_data.year;
  buffer[1] = this->c_data.month;
  buffer[2] = this->c_data.day;
  buffer[3] = this->c_data.day_of_week;
  return PyString_FromStringAndSize(buffer, 4);
}

static int _encode_date(date_object *this,
			PyObject *year_object, PyObject *month_object,
			PyObject *day_object, PyObject *day_of_week_object)
{
  UINT32 year, month, day, day_of_week;
  year = (year_object != Py_None) ? PyInt_AsLong(year_object) : 0xff ;
  month = (month_object != Py_None) ? PyInt_AsLong(month_object) : 0xff ;
  day = (day_object != Py_None) ? PyInt_AsLong(day_object) : 0xff ;
  day_of_week = (day_of_week_object != Py_None)
              ? PyInt_AsLong(day_of_week_object) : 0xff ;
  if (PyErr_Occurred()) {
    return 0;
  }
  if (year != 0xff && (year < 1900 || year > 2154)) {
    broadway_raise_invalid_ulong(year, "year",
				 "year must be between 1900 and 2154, or None");
    return 0;
  } else {
    year = (year == 0xff) ? year : year - 1900;
  }
  if (month != 0xff && (month < 1 || month > 12)) {
    broadway_raise_invalid_ulong(month, "month",
				 "month must be between 1 and 12, or None");
    return 0;
  }
  if (day != 0xff && (day < 1 || day > 31)) {
    broadway_raise_invalid_ulong(day, "day",
				 "day must be between 1 and 31, or None");
    return 0;
  }
  if (day_of_week != 0xff && (day_of_week < 1 || day_of_week > 7)) {
    broadway_raise_invalid_ulong(day_of_week, "day_of_week",
				 "day_of_week must be between 1 and 7,"
				 " or None");
    return 0;
  }
  this->c_data.year = (unsigned char)year;
  this->c_data.month = (unsigned char)month;
  this->c_data.day = (unsigned char)day;
  this->c_data.day_of_week = (unsigned char)day_of_week;
  return 1;
}

static char __doc__encode_date[] = "\n"
"##\n"
"# MontyDoc string for _encode_date.\n"
"# @todo Implement.";
static PyObject *encode_date(PyObject *this, PyObject *args)
{
  date_object *date;
  if (!PyArg_ParseTuple(args, "O", (PyObject*)&date)) {
    return NULL;
  }
  if (date->ob_type != &data_DateType) {
    broadway_raise("ETypeError", NULL, NULL);
  }
  return data_encoded_date((PyObject*)date);
}

static time_object *alloc_new_time(void)
{
  time_object *that = PyObject_New(time_object, &data_TimeType);
  if (that) {
    memset(&that->c_data, 0, sizeof(that->c_data));
  }
  n_Time_instances +=1;
  return that;
}

////
// @note Assumes that length == 4.
// @fixme Validate the encoded values.
static int
_update_time(time_object *this, const unsigned char *buffer, int len)
{
  if (len != 4) {
    broadway_raise_invalid_ulong(len, "buffer length",
				 "times are exactly four bytes");
    return 0;
  }
  if (buffer[0] != 0xff && buffer[0] > 23) {
    broadway_raise_parse_failure("hour out of range", buffer[1]);
    return 0;
  }
  if (buffer[1] != 0xff && buffer[1] > 59) {
    broadway_raise_parse_failure("minute out of range", buffer[1]);
    return 0;
  }
  if (buffer[2] != 0xff && buffer[2] > 59) {
    broadway_raise_parse_failure("second out of range", buffer[2]);
    return 0;
  }
  if (buffer[3] != 0xff && buffer[3] > 99) {
    broadway_raise_parse_failure("hundredths out of range", buffer[3]);
    return 0;
  }
  this->c_data.hour = buffer[0];
  this->c_data.minute = buffer[1];
  this->c_data.second = buffer[2];
  this->c_data.hundredths = buffer[3];
  return 1;
}

static void time_dealloc(PyObject *self)
{
  time_object *this = (time_object *)self;
#if 1
  if (!memcmp(&this->c_data, lots_of_fs, sizeof(this->c_data))) {
    Py_FatalError("Dealloc of already deallocated Time");
  }
#endif
  memset(&this->c_data, 0, sizeof(this->c_data));
  n_Time_instances -=1;
  PyObject_Del(self); // Accounted for (in dealloc).
}

////
// @note Assumes that length == 4.
PyObject *data_decode_time(const unsigned char *buffer, int len)
{
  time_object *that = alloc_new_time();
  if (!that) {
    return NULL;
  }
  if (!_update_time(that, buffer, len)) {
    return NULL;
  }
  return (PyObject*)that;
}

static char __doc__decode_time[] = "\n"
"##\n"
"# MontyDoc string for _decode_time.\n"
"# @todo Implement.";
static PyObject *decode_time(PyObject *self, PyObject *args)
{
  time_object *this;
  PyObject *decode = NULL;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTuple(args, "O", &decode)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, decode);
  if (!buffer) {
    return NULL;
  }
  this = alloc_new_time();
  if (this) {
    if (!_update_time(this, buffer, length)) {
      return NULL;
    }
  }
  return (PyObject *)this;
}

PyObject *data_encoded_time(time_object *this)
{
  unsigned char buffer[4];
  buffer[0] = this->c_data.hour;
  buffer[1] = this->c_data.minute;
  buffer[2] = this->c_data.second;
  buffer[3] = this->c_data.hundredths;
  return PyString_FromStringAndSize(buffer, 4);
}

static int _encode_time(time_object *this,
			PyObject *hour_object, PyObject *minute_object,
			PyObject *second_object, PyObject *hundredths_object)
{
  UINT32 hour, minute, second, hundredths;
  hour = (hour_object != Py_None) ? PyInt_AsLong(hour_object) : 0xff ;
  minute = (minute_object != Py_None) ? PyInt_AsLong(minute_object) : 0xff ;
  second = (second_object != Py_None) ? PyInt_AsLong(second_object) : 0xff ;
  hundredths = (hundredths_object != Py_None)
              ? PyInt_AsLong(hundredths_object) : 0xff ;
  if (PyErr_Occurred()) {
    return 0;
  }
  if (hour != 0xff && (hour < 0 || hour > 23)) {
    broadway_raise_invalid_ulong(hour, "hour",
				 "hour must be between 0 and 23, or None");
    return 0;
  }
  if (minute != 0xff && (minute < 0 || minute > 59)) {
    broadway_raise_invalid_ulong(minute, "minute",
				 "minute must be between 0 and 59, or None");
    return 0;
  }
  if (second != 0xff && (second < 0 || second > 59)) {
    broadway_raise_invalid_ulong(second, "second",
				 "second must be between 0 and 59, or None");
    return 0;
  }
  if (hundredths != 0xff && (hundredths < 0 || hundredths > 99)) {
    broadway_raise_invalid_ulong(hundredths, "hundredths",
				 "hundredths must be between 0 and 99,"
				 " or None");
    return 0;
  }
  this->c_data.hour = (unsigned char)hour;
  this->c_data.minute = (unsigned char)minute;
  this->c_data.second = (unsigned char)second;
  this->c_data.hundredths = (unsigned char)hundredths;
  return 1;
}

static char __doc__encode_time[] = "\n"
"##\n"
"# MontyDoc string for _encode_time.\n"
"# @todo Implement.";
static PyObject *encode_time(PyObject *this, PyObject *args)
{
  time_object *time;
  if (!PyArg_ParseTuple(args, "O", (PyObject*)&time)) {
    return NULL;
  }
  if (time->ob_type != &data_TimeType) {
    broadway_raise("ETypeError", NULL, NULL);
  }
  return data_encoded_time(time);
}

////
// @note Assumes that length == 4.
// @fixme Validate the encoded values.
static int
_update_date(date_object *this, const unsigned char *buffer, int len)
{
  if (len != 4) {
    broadway_raise_invalid_ulong(len, "buffer length",
				 "dates are exactly four bytes");
    return 0;
  }
  if (buffer[1] != 0xff && (buffer[1] == 0 || buffer[1] > 12)) {
    broadway_raise_parse_failure("month out of range", buffer[1]);
    return 0;
  }
  if (buffer[2] != 0xff && (buffer[2] == 0 || buffer[2] > 31)) {
    broadway_raise_parse_failure("day out of range", buffer[2]);
    return 0;
  }
  if (buffer[3] != 0xff && (buffer[3] == 0 || buffer[3] > 7)) {
    broadway_raise_parse_failure("day_of_week out of range", buffer[3]);
    return 0;
  }
  this->c_data.year = buffer[0];
  this->c_data.month = buffer[1];
  this->c_data.day = buffer[2];
  this->c_data.day_of_week = buffer[3];
  return 1;
}

static date_object *alloc_new_date(void)
{
  date_object *that = PyObject_New(date_object, &data_DateType);
  if (that) {
    memset(&that->c_data, 0, sizeof(that->c_data));
  }
  n_Date_instances +=1;
  return that;
}

static void date_dealloc(PyObject *self)
{
  date_object *this = (date_object *)self;
#if 1
  if (!memcmp(&this->c_data, lots_of_fs, sizeof(this->c_data))) {
    Py_FatalError("Dealloc of already deallocated Date");
  }
#endif
  memset(&this->c_data, 0, sizeof(this->c_data));
  n_Date_instances -=1;
  PyObject_Del(self); // Accounted for (in dealloc).
}

////
// @note Assumes that length == 4.
PyObject *data_decode_date(const unsigned char *buffer, int len)
{
  date_object *that = alloc_new_date();
  if (!that) {
    return NULL;
  }
  if (!_update_date(that, buffer, len)) {
    return NULL;
  }
  return (PyObject*)that;
}

static char __doc__decode_date[] = "\n"
"##\n"
"# MontyDoc string for _decode_date.\n"
"# @todo Implement.";
static PyObject *decode_date(PyObject *self, PyObject *args)
{
  date_object *this;
  PyObject *decode = NULL;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTuple(args, "O", &decode)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, decode);
  if (!buffer) {
    return NULL;
  }
  this = alloc_new_date();
  if (this) {
    if (!_update_date(this, buffer, length)) {
      return NULL;
    }
  }
  return (PyObject *)this;
}

static char __doc__Date[] = "\n"
"##\n"
"# MontyDoc string for the Date factory.\n"
"# @implements Data\n"
"#";
static PyObject *Date(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"year", "month", "day", "day_of_week",
			   "decode", NULL};
  date_object *this;
  PyObject *year = Py_None;
  PyObject *month = Py_None;
  PyObject *day = Py_None;
  PyObject *day_of_week = Py_None;
  PyObject *decode = NULL;
  char *msg;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOOO", kwlist,
				   &year, &month, &day, &day_of_week,
				   &decode)) {  return NULL;
  }
  this = alloc_new_date();
  if (!this) {
    return NULL;
  }
  if (decode) {
    if (year != Py_None || month != Py_None ||
	day != Py_None || day_of_week != Py_None) {
      Py_DECREF((PyObject*)this);
      msg = "too many arguments:  "
	"the decode keyword is exclusive of all other arguments";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
      return NULL;
    }
    broadway_get_buffer(&buffer, &length, decode);
    if (!buffer) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
    if (!_update_date(this, buffer, length)) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
  } else {
    if (!_encode_date(this, year, month, day, day_of_week)) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
  }
  return (PyObject*)this;
}

static char __doc__Time[] = "\n"
"##\n"
"# MontyDoc string for the Time factory.\n"
"# @implements Data\n"
"#";
static PyObject *Time(PyObject *self, PyObject *args, PyObject *keywords)
{
  static char *kwlist[] = {"hour", "minute", "second", "hundredths",
			   "decode", NULL};
  time_object *this;
  PyObject *hour = Py_None;
  PyObject *minute = Py_None;
  PyObject *second = Py_None;
  PyObject *hundredths = Py_None;
  PyObject *decode = NULL;
  char *msg;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOOOO", kwlist,
				   &hour, &minute, &second, &hundredths,
				   &decode)) {
    return NULL;
  }
  this = alloc_new_time();
  if (!this) {
    return NULL;
  }
  if (decode) {
    if (hour || minute || second || hundredths) {
      Py_DECREF((PyObject*)this);
      msg = "too many arguments:  "
	"the decode keyword is exclusive of all other arguments";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
      return NULL;
    }
    broadway_get_buffer(&buffer, &length, decode);
    if (!buffer) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
    if (!_update_time(this, buffer, length)) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
  } else {
    if (!_encode_time(this, hour, minute, second, hundredths)) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
  }
  return (PyObject*)this;
}

////
// @note Assumes that length == 4.
static int
_update_bacnet_object_identifier(bacnet_object_identifier_object *this,
				 const unsigned char *buffer, int len)
{
  UINT32 id;
  if (len != 4) {
    broadway_raise_invalid_ulong(len, "buffer length", NULL);
    return 0;
  }
#if __BYTE_ORDER == __BIG_ENDIAN
  id = *(UINT32*)buffer;
#else
  id = bswap_32(*(UINT32*)buffer);
#endif
  this->c_data.id = id;
  this->c_data.instance_number = id & 0x3fffff;
  this->c_data.object_type = id >> 22;
  return 1;
}

static
bacnet_object_identifier_object *alloc_new_bacnet_object_identifier(void)
{
  bacnet_object_identifier_object *that =
    PyObject_New(bacnet_object_identifier_object,
		 &data_BACnetObjectIdentifierType);
  if (that) {
    memset(&that->c_data, 0, sizeof(that->c_data));
  }
  n_BACnetObjectIdentifier_instances += 1;
  return that;
}

static void bacnet_object_identifier_dealloc(PyObject *self)
{
  bacnet_object_identifier_object *this =
    (bacnet_object_identifier_object *)self;
#if 1
  if (!memcmp(&this->c_data, lots_of_fs, sizeof(this->c_data))) {
    Py_FatalError("Dealloc of already deallocated BACnetObjectIdentifier");
  }
#endif
  memset(&this->c_data, 0xff, sizeof(this->c_data));
  n_BACnetObjectIdentifier_instances -=1;
  PyObject_Del(self); // Accounted for (in dealloc).
}

////
// @note Assumes that length == 4.
PyObject *
data_decode_bacnet_object_identifier(const unsigned char *buffer, int len)
{
  bacnet_object_identifier_object *that = alloc_new_bacnet_object_identifier();
  if (!that) {
    return NULL;
  }
  if (!_update_bacnet_object_identifier(that, buffer, len)) {
    return NULL;
  }
  return (PyObject*)that;
}

PyObject *
data_encoded_bacnet_object_identifier(bacnet_object_identifier_object *this)
{
#if __BYTE_ORDER == __BIG_ENDIAN
  UINT32 id = this->c_data.id;
#else
  UINT32 id = bswap_32(this->c_data.id);
#endif
  return PyString_FromStringAndSize((char*)&id, 4);
}

static int
_encode_bacnet_object_identifier(bacnet_object_identifier_object *this,
				 PyObject *id_or_type,
				 PyObject *instance_object)
{
  UINT32 id, object_type, instance;
  char *msg;
  if (!id_or_type) {
    if (instance_object) {
      msg = "too few arguments:  instance requires id_or_type";
    } else {
      msg = "too few arguments:  id_or_type is required";
    }
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return 0;
  }
  if (instance_object) {
    object_type = PyInt_AsLong(id_or_type);
    instance = PyInt_AsLong(instance_object);
    if (PyErr_Occurred()) {
      return 0;
    }
    if (object_type >= (1 << 10)) {
      msg = "object_type exceeds 1023";
      broadway_raise("EOverflow", PyString_FromString(msg), NULL);
      return 0;
    }
    if (instance >= (1 << 22)) {
      msg = "instance_number exceeds 1023";
      broadway_raise("EOverflow", PyString_FromString(msg), NULL);
      return 0;
    }
    id = (object_type << 22) | instance;
  } else {
    id = PyInt_AsLong(id_or_type);
    instance = id & 0x3fffff;
    object_type = id >> 22;
  }
  this->c_data.id = id;
  this->c_data.instance_number = instance;
  this->c_data.object_type = object_type;
  return 1;
}

static char __doc__decode_bacnet_object_identifier[] = "\n"
"##\n"
"# MontyDoc string for _decode_bacnet_object_identifier.\n"
"";
static PyObject *decode_bacnet_object_identifier(PyObject *self, PyObject *args)
{
  bacnet_object_identifier_object *this;
  PyObject *decode = NULL;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTuple(args, "O", &decode)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, decode);
  if (!buffer) {
    return NULL;
  }
  this = alloc_new_bacnet_object_identifier();
  if (this) {
    if (!_update_bacnet_object_identifier(this, buffer, length)) {
      return NULL;
    }
  }
  return (PyObject *)this;
}

static char __doc__encode_bacnet_object_identifier[] = "\n"
"##\n"
"# MontyDoc string for _encode_bacnet_object_identifier.\n"
"";
static PyObject *encode_bacnet_object_identifier(PyObject *self, PyObject *args)
{
  bacnet_object_identifier_object *object;
  if (!PyArg_ParseTuple(args, "O", (PyObject*)&object)) {
    return NULL;
  }
  if (object->ob_type != &data_BACnetObjectIdentifierType) {
    broadway_raise("ETypeError", NULL, NULL);
  }
  return data_encoded_bacnet_object_identifier(object);
}

static char __doc__BACnetObjectIdentifier[] = "\n"
"##\n"
"# MontyDoc string for the BACnetObjectIdentifier factory.\n"
"# @implements Data\n"
"#";
static PyObject *BACnetObjectIdentifier(PyObject *self, PyObject *args,
					PyObject *keywords)
{
  static char *kwlist[] = {"id_or_type", "instance", "decode", NULL};
  bacnet_object_identifier_object *this;
  PyObject *id_or_type = NULL;
  PyObject *instance = NULL;
  PyObject *decode = NULL;
  char *msg;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTupleAndKeywords(args, keywords, "|OOO", kwlist,
				   &id_or_type, &instance, &decode)) {
    return NULL;
  }
  this = alloc_new_bacnet_object_identifier();
  if (!this) {
    return NULL;
  }
  if (decode) {
    if (id_or_type || instance) {
      Py_DECREF((PyObject*)this);
      msg = "too many arguments:  "
	"decode is exclusive of id_or_type and instance";
      broadway_raise("ETypeError", PyString_FromString(msg), NULL);
      return NULL;
    }
    broadway_get_buffer(&buffer, &length, decode);
    if (!buffer) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
    if (!_update_bacnet_object_identifier(this, buffer, length)) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
  } else if (id_or_type || instance) {
    if (!_encode_bacnet_object_identifier(this, id_or_type, instance)) {
      Py_DECREF((PyObject*)this);
      return NULL;
    }
  } else {
    msg = "too few arguments:  "
      "decode keyword or id_or_type are required";
    broadway_raise("ETypeError", PyString_FromString(msg), NULL);
    return NULL;
  }
  return (PyObject*)this;
}

static struct memberlist bacnet_object_identifier_memberlist[] = {
  {"id", T_UINT,
   offsetof(bacnet_object_identifier_object, c_data.id), READONLY},
  {"object_type", T_USHORT,
   offsetof(bacnet_object_identifier_object, c_data.object_type), READONLY},
  {"instance_number", T_UINT,
   offsetof(bacnet_object_identifier_object, c_data.instance_number), READONLY},
  // So __setattr__ will raise a READONLY exception.
  {"encoding", T_UINT,
   offsetof(bacnet_object_identifier_object, c_data.id), READONLY},
  {NULL}
};

static PyObject *bacnet_object_identifier_decode(PyObject *self, PyObject *args)
{
  bacnet_object_identifier_object *this =
    (bacnet_object_identifier_object *)self;
  PyObject *decode = NULL;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTuple(args, "O", &decode)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, decode);
  if (!buffer) {
    return NULL;
  }
  if (!_update_bacnet_object_identifier(this, buffer, length)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject *bacnet_object_identifier_encode(PyObject *self, PyObject *args)
{
  bacnet_object_identifier_object *this;
  PyObject *id_or_type = Py_None;
  PyObject *instance_object = Py_None;

  this = (bacnet_object_identifier_object *)self;
  if (!PyArg_ParseTuple(args, "|OO", &id_or_type, &instance_object)) {
    return NULL;
  }
  if (!_encode_bacnet_object_identifier(this, id_or_type, instance_object)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef bacnet_object_identifier_methodlist[] = {
  {"decode", bacnet_object_identifier_decode, METH_VARARGS},
  {"encode", bacnet_object_identifier_encode, METH_VARARGS},
  {NULL}
};

static int bacnet_object_identifier_compare(PyObject *this, PyObject *that)
{
  bacnet_object_identifier_object *self = 
    (bacnet_object_identifier_object *)this;
  bacnet_object_identifier_object *other =
    (bacnet_object_identifier_object *)that;

  int instance_number = (int)self->c_data.instance_number -
    (int)other->c_data.instance_number;
  int object_type = (int)self->c_data.object_type -
    (int)other->c_data.object_type;
  int result;
  if (instance_number) {
    result = instance_number;
  } else if (object_type) {
    result = object_type;
  } else {
    result = 0;
  }
  if (result == 0) return 0;
  if (result < 0) return -1;
  return 1;
}

static PyObject *bacnet_object_identifier_getattr(PyObject *self, char *name)
{
  PyObject *result;
  bacnet_object_identifier_object *this =
    (bacnet_object_identifier_object*)self;
  if (strcmp(name, "encoding") == 0) {
    return data_encoded_bacnet_object_identifier(this);
  }
  result = Py_FindMethod(bacnet_object_identifier_methodlist,
			 (PyObject *)self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not clear, it will be incorrectly rasied
			// later.
  return PyMember_Get((char *)self, bacnet_object_identifier_memberlist, name);
}

static int bacnet_object_identifier_setattr(PyObject *self,
					    char *name, PyObject *value)
{
  bacnet_object_identifier_object *this =
    (bacnet_object_identifier_object *)self;
  return PyMember_Set((char *)this, bacnet_object_identifier_memberlist,
		      name, value);
}

static struct memberlist date_memberlist[] = {
  // So __setattr__ will raise a READONLY exception.
  {"year", T_BYTE, offsetof(date_object, c_data.year), READONLY},
  {"month", T_BYTE, offsetof(date_object, c_data.month), READONLY},
  {"day", T_BYTE, offsetof(date_object, c_data.day), READONLY},
  {"day_of_week", T_BYTE, offsetof(date_object, c_data.day_of_week), READONLY},
  {"encoding", T_BYTE, offsetof(date_object, c_data.year), READONLY},
  {NULL}
};

static PyObject *_escaped_integer(UINT32 value, UINT32 as_none)
{
  if (value == as_none) {
    Py_INCREF(Py_None);
    return Py_None;
  }
  return PyInt_FromLong(value);
}

static PyObject *date_decode(PyObject *self, PyObject *args)
{
  date_object *this = (date_object *)self;
  PyObject *decode = NULL;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTuple(args, "O", &decode)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, decode);
  if (!buffer) {
    return NULL;
  }
  if (!_update_date(this, buffer, length)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject *date_encode(PyObject *self, PyObject *args)
{
  date_object *this;
  PyObject *year = Py_None;
  PyObject *month = Py_None;
  PyObject *day = Py_None;
  PyObject *day_of_week = Py_None;

  this = (date_object *)self;
  if (!PyArg_ParseTuple(args, "|OOOO", &year, &month, &day, &day_of_week)) {
    return NULL;
  }
  if (!_encode_date(this, year, month, day, day_of_week)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static struct PyMethodDef date_methodlist[] = {
  {"decode", date_decode, METH_VARARGS},
  {"encode", date_encode, METH_VARARGS},
  {NULL}
};

static int date_compare(PyObject *this, PyObject *that)
{
  date_object *self = (date_object *)this;
  date_object *other = (date_object *)that;
  int year = (self->c_data.year == 0xff || other->c_data.year == 0xff) ? 0 :
    (int)self->c_data.year - (int)other->c_data.year;
  int month = (self->c_data.month == 0xff || other->c_data.month == 0xff) ? 0 :
    (int)self->c_data.month - (int)other->c_data.month;
  int day = (self->c_data.day == 0xff || other->c_data.day == 0xff) ? 0 :
    (int)self->c_data.day - (int)other->c_data.day;
  int day_of_week = (self->c_data.day_of_week == 0xff ||
		     other->c_data.day_of_week == 0xff) ? 0 :
    ((int)self->c_data.day_of_week - (int)other->c_data.day_of_week);
  int result;
  if (year) {
    result = year;
  } else if (month) {
    result = month;
  } else if (day) {
    result = day;
  } else if (day_of_week) {
    // @todo Should day_of_week be part of the comparison?
    result = day_of_week;
  } else {
    result = 0;
  }
  if (result == 0) return 0;
  if (result < 0) return -1;
  return 1;
}

static PyObject *date_getattr(PyObject *self, char *name)
{
  PyObject *result;
  date_object *this = (date_object*)self;
  if (strcmp(name, "encoding") == 0) {
    return data_encoded_date(self);
  }
  if (strcmp(name, "day") == 0) {
    return _escaped_integer(this->c_data.day, 0xff);
  }
  if (strcmp(name, "day_of_week") == 0) {
    return _escaped_integer(this->c_data.day_of_week, 0xff);
  }
  if (strcmp(name, "month") == 0) {
    return _escaped_integer(this->c_data.month, 0xff);
  }
  if (strcmp(name, "year") == 0) {
    return _escaped_integer(this->c_data.year+1900, 0xff+1900);
  }
  result = Py_FindMethod(date_methodlist, (PyObject *)self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not clear, it will be incorrectly rasied
			// later.
  return PyMember_Get((char *)self, date_memberlist, name);
}

static int date_setattr(PyObject *self, char *name, PyObject *value)
{
  date_object *this = (date_object *)self;
  return PyMember_Set((char *)this, date_memberlist, name, value);
}

PyTypeObject data_DateType = {
  PyObject_HEAD_INIT(&PyType_Type)	/* PyObject_VAR_HEAD */
  0,					/* PyObject_VAR_HEAD */

  "Date",		/* char *tp_name; */
  sizeof(date_object),	/* int tp_basicsize; */
  0,			/* int tp_itemsize;       * not used much */
  date_dealloc,		/* destructor tp_dealloc; */
  0,			/* printfunc  tp_print;   */
  date_getattr,		/* getattrfunc  tp_getattr; * __getattr__ */
  date_setattr,		/* setattrfunc  tp_setattr;  * __setattr__ */
  date_compare,		/* cmpfunc  tp_compare;  * __cmp__ */
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

static struct memberlist time_memberlist[] = {
  // So __setattr__ will raise a READONLY exception.
  {"hour", T_BYTE, offsetof(time_object, c_data.hour), READONLY},
  {"minute", T_BYTE, offsetof(time_object, c_data.minute), READONLY},
  {"second", T_BYTE, offsetof(time_object, c_data.second), READONLY},
  {"hundredths", T_BYTE, offsetof(time_object, c_data.hundredths), READONLY},
  {"encoding", T_BYTE, offsetof(time_object, c_data.hour), READONLY},
  {NULL}
};

static PyObject *time_decode(PyObject *self, PyObject *args)
{
  time_object *this = (time_object *)self;
  PyObject *decode = NULL;
  const unsigned char *buffer;
  UINT32 length;

  if (!PyArg_ParseTuple(args, "O", &decode)) {
    return NULL;
  }
  broadway_get_buffer(&buffer, &length, decode);
  if (!buffer) {
    return NULL;
  }
  if (!_update_time(this, buffer, length)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject *time_encode(PyObject *self, PyObject *args)
{
  time_object *this;
  PyObject *hour = Py_None;
  PyObject *minute = Py_None;
  PyObject *second = Py_None;
  PyObject *hundredths = Py_None;

  this = (time_object *)self;
  if (!PyArg_ParseTuple(args, "|OOOO", &hour, &minute, &second, &hundredths)) {
    return NULL;
  }
  if (!_encode_time(this, hour, minute, second, hundredths)) {
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}
static struct PyMethodDef time_methodlist[] = {
  {"decode", time_decode, METH_VARARGS},
  {"encode", time_encode, METH_VARARGS},
  {NULL}
};

static int time_compare(PyObject *this, PyObject *that)
{
  time_object *self = (time_object *)this;
  time_object *other = (time_object *)that;
  int hour = (self->c_data.hour == 0xff || other->c_data.hour == 0xff) ? 0 :
    (int)self->c_data.hour - (int)other->c_data.hour;
  int minute = (self->c_data.minute == 0xff ||
		other->c_data.minute == 0xff) ? 0 :
    (int)self->c_data.minute - (int)other->c_data.minute;
  int second = (self->c_data.second == 0xff ||
		other->c_data.second == 0xff) ? 0 :
    (int)self->c_data.second - (int)other->c_data.second;
  int hundredths = (self->c_data.hundredths == 0xff ||
		    other->c_data.hundredths == 0xff) ? 0 :
    ((int)self->c_data.hundredths - (int)other->c_data.hundredths);
  int result;
  if (hour) {
    result = hour;
  } else if (minute) {
    result = minute;
  } else if (second) {
    result = second;
  } else if (hundredths) {
    result = hundredths;
  } else {
    result = 0;
  }
  if (result == 0) return 0;
  if (result < 0) return -1;
  return 1;
}

static PyObject *time_getattr(PyObject *self, char *name)
{
  PyObject *result;
  time_object *this = (time_object*)self;
  if (strcmp(name, "encoding") == 0) {
    return data_encoded_time(this);
  }
  if (strcmp(name, "second") == 0) {
    return _escaped_integer(this->c_data.second, 0xff);
  }
  if (strcmp(name, "hundredths") == 0) {
    return _escaped_integer(this->c_data.hundredths, 0xff);
  }
  if (strcmp(name, "minute") == 0) {
    return _escaped_integer(this->c_data.minute, 0xff);
  }
  if (strcmp(name, "hour") == 0) {
    return _escaped_integer(this->c_data.hour, 0xff);
  }
  result = Py_FindMethod(time_methodlist, (PyObject *)self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not clear, it will be incorrectly rasied
			// later.
  return PyMember_Get((char *)self, time_memberlist, name);
}

static int time_setattr(PyObject *self, char *name, PyObject *value)
{
  time_object *this = (time_object *)self;
  return PyMember_Set((char *)this, time_memberlist, name, value);
}

static PyObject *count_Date_instances(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return PyInt_FromLong(n_Date_instances);
}

static PyObject *count_Time_instances(PyObject *this, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return PyInt_FromLong(n_Time_instances);
}

static PyObject *count_BACnetObjectIdentifier_instances(PyObject *this,
							PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return PyInt_FromLong(n_BACnetObjectIdentifier_instances);
}

PyTypeObject data_TimeType = {
  PyObject_HEAD_INIT(&PyType_Type)	/* PyObject_VAR_HEAD */
  0,					/* PyObject_VAR_HEAD */

  "Time",		/* char *tp_name; */
  sizeof(time_object),	/* int tp_basicsize; */
  0,			/* int tp_itemsize;       * not used much */
  time_dealloc,		/* destructor tp_dealloc; */
  0,			/* printfunc  tp_print;   */
  time_getattr,		/* getattrfunc  tp_getattr; * __getattr__ */
  time_setattr,		/* setattrfunc  tp_setattr;  * __setattr__ */
  time_compare,		/* cmpfunc  tp_compare;  * __cmp__ */
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

PyTypeObject data_BACnetObjectIdentifierType = {
  PyObject_HEAD_INIT(&PyType_Type)	/* PyObject_VAR_HEAD */
  0,					/* PyObject_VAR_HEAD */

  "BACnetObjectIdentifier",			/* char *tp_name; */
  sizeof(bacnet_object_identifier_object),	/* int tp_basicsize; */
  0,			/* int tp_itemsize;       * not used much */
  bacnet_object_identifier_dealloc,/* destructor tp_dealloc; */
  0,			/* printfunc  tp_print;   */
  bacnet_object_identifier_getattr,/* getattrfunc  tp_getattr; * __getattr__ */
  bacnet_object_identifier_setattr,/* setattrfunc  tp_setattr; * __setattr__ */
  bacnet_object_identifier_compare,/* cmpfunc  tp_compare;  * __cmp__ */
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

static PyMethodDef data_functions[] = {
  {"decode_null", decode_null, METH_VARARGS, __doc__decode_null},
  {"encode_null", encode_null, METH_VARARGS, __doc__encode_null},
  {"decode_boolean", decode_boolean, METH_VARARGS, __doc__decode_boolean},
  {"encode_boolean", encode_boolean, METH_VARARGS, __doc__encode_boolean},
  {"decode_unsigned_integer", decode_unsigned_integer, METH_VARARGS,
   __doc__decode_unsigned_integer},
  {"encode_unsigned_integer", encode_unsigned_integer, METH_VARARGS,
   __doc__encode_unsigned_integer},
  {"decode_signed_integer", decode_signed_integer, METH_VARARGS,
   __doc__decode_signed_integer},
  {"encode_signed_integer", encode_signed_integer, METH_VARARGS,
   __doc__encode_signed_integer},
  {"decode_real", decode_real, METH_VARARGS, __doc__decode_real},
  {"encode_real", encode_real, METH_VARARGS, __doc__encode_real},
  {"decode_double", decode_double, METH_VARARGS, __doc__decode_double},
  {"encode_double", encode_double, METH_VARARGS, __doc__encode_double},
  {"decode_octet_string", decode_octet_string, METH_VARARGS,
   __doc__decode_octet_string},
  {"encode_octet_string", encode_octet_string, METH_VARARGS,
   __doc__encode_octet_string},
  //  {"encode_bit_string", encode_bit_string, METH_VARARGS,
  // __doc__encode_bit_string},
  {"decode_enumerated", decode_enumerated, METH_VARARGS,
   __doc__decode_enumerated},
  {"encode_enumerated", encode_enumerated, METH_VARARGS,
   __doc__encode_enumerated},
  {"decode_date", decode_date, METH_VARARGS, __doc__decode_date},
  {"encode_date", encode_date, METH_VARARGS, __doc__encode_date},
  {"decode_time", decode_time, METH_VARARGS, __doc__decode_time},
  {"encode_time", encode_time, METH_VARARGS, __doc__encode_time},
  {"decode_bacnet_object_identifier", decode_bacnet_object_identifier,
   METH_VARARGS, __doc__decode_bacnet_object_identifier},
  {"encode_bacnet_object_identifier", encode_bacnet_object_identifier,
   METH_VARARGS, __doc__encode_bacnet_object_identifier},
  {"Date", (PyCFunction)Date, METH_VARARGS | METH_KEYWORDS,
   __doc__Date},
  {"Time", (PyCFunction)Time, METH_VARARGS | METH_KEYWORDS, __doc__Time},
  {"BACnetObjectIdentifier", (PyCFunction)BACnetObjectIdentifier,
   METH_VARARGS | METH_KEYWORDS,
   __doc__BACnetObjectIdentifier},
  {"count_Date_instances", count_Date_instances, METH_VARARGS},
  {"count_Time_instances", count_Time_instances, METH_VARARGS},
  {"count_BACnetObjectIdentifier_instances",
   count_BACnetObjectIdentifier_instances, METH_VARARGS},
  {NULL, NULL}
};

void initdata(void)
{
  PyObject *_data;
  // Create the new module definition.
  PyObject *module = Py_InitModule("data", data_functions);

  // Load the references to the shared library code.
  load_lib_references();

  // Load all publics from _data.
  _data = PyImport_ImportModule("mpx.lib.bacnet._data");
  if (_data != NULL) {
    PyObject *_data__dict__ = PyObject_GetAttrString(_data, "__dict__");
    if (_data__dict__ != NULL) {
      int pos = 0;
      PyObject *pkey;
      PyObject *pvalue;
      while (PyDict_Next(_data__dict__, &pos, &pkey, &pvalue)) {
        if (PyString_Check(pkey) && PyString_AS_STRING(pkey)[0] != '_') {
          PyObject_SetAttr(module, pkey, pvalue);
        }
      }
      Py_DECREF(_data__dict__);
    }
    // Get an exportable pointer to the CharacterString type.
    data_CharacterString = PyObject_GetAttrString(_data, "CharacterString");
    // Get an exportable pointer to the BitString type.
    data_BitString = PyObject_GetAttrString(_data, "BitString");
    Py_DECREF(_data);
  }
}
