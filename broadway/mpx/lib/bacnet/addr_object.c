/*
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
// @todo Rewrite as a real class.

#include <Python.h>
#include <structmember.h>

#include "lib.h"
#include "addr_object.h"

long n_Addr_instances = 0;

// Initialise the object descriptor and hook in the supported internal methods.
static void addr_dealloc(PyObject *self);
static PyObject *addr_getattr(addr_object *self, char *name);
static int addr_setattr(addr_object *self, char *name, PyObject *o);
static PyObject *__repr__(PyObject *self);
static PyObject *__str__(PyObject *self);
static int len(PyObject *self);
static PyObject *item(PyObject *, int);
static PyObject *slice(PyObject *, int, int);

static PyMethodDef addr_methods[] = {
  {NULL, NULL}
};

static PySequenceMethods sq_methods = {
  len,		/* inquiry sq_length; */
  0,		/* binaryfunc sq_concat; */
  0,		/* intargfunc sq_repeat; */
  item,		/* intargfunc sq_item; */
  slice,	/* intintargfunc sq_slice; */
  0,		/* intobjargproc sq_ass_item; */
  0,		/* intintobjargproc sq_ass_slice; */
  0,		/* objobjproc sq_contains; */
  0,		/* binaryfunc sq_inplace_concat; */
  0,		/* intargfunc sq_inplace_repeat; */
};

// Allocate a new object and zap our bit (BACNET_NPDU) with zeros
// The ":Addr" argument to PyArg_ParseTuple() is used in the
// error string if there is a problem. Less the ':' that is.

char __doc__Addr[] = "\n"
"##\n"
"# MontyDoc string for Addr.\n"
"#";
PyObject *
new_addr(PyObject *self, PyObject *args)
{
  PyObject *address = Py_None;
  const char *msg;
  addr_object *to, *from;

  if (!PyArg_ParseTuple(args, "|O:Addr",&address)) {
    return NULL;
  }
  to = PyObject_New(addr_object, AddrType);
  if (to) {
    n_Addr_instances += 1;
    memset(&to->addr, 0, sizeof(to->addr));
    if (PyString_Check(address)) {
      to->addr.length = PyString_GET_SIZE(address);
      if (to->addr.length > sizeof(to->addr.address)) {
        Py_DECREF(to);
	broadway_raise("EOverflow", PyString_FromString("address too long."),
                       NULL);
        return NULL;
      }
      memcpy(to->addr.address, PyString_AS_STRING(address), to->addr.length);
    } else if (address->ob_type == AddrType) {
      from = (addr_object *)address;
      memcpy(to->addr.address, from->addr.address, from->addr.length);
      to->addr.length = from->addr.length;
    } else if (address != Py_None) {
      Py_DECREF(to);
      msg = "npdu.Addr's optional argument must be a string or Addr.";
      PyErr_SetString(PyExc_TypeError, msg);
      return NULL;
    }
  }
  return (PyObject *)to;
}

static int __cmp__(PyObject *this, PyObject *that)
{
  addr_object *self = (addr_object *)this;
  addr_object *other = (addr_object *)that;
  int result = strncmp(self->addr.address, other->addr.address, 31);
  if (result == 0) return 0;
  if (result < 0) return -1;
  return 1;
}

static PyObject *__repr__(PyObject *self)
{
  PyObject *result;
  char buf[8];
  int i;
  addr_object *object = (addr_object *)self;

  result = PyString_FromString("mpx.lib.bacnet.npdu.Addr(\'");
  for (i=0; i<object->addr.length; i++) {
    sprintf(buf,"\\x%02x", object->addr.address[i]);
    PyString_ConcatAndDel(&result, PyString_FromString(buf));
  }
  PyString_ConcatAndDel(&result, PyString_FromString("\')"));
  return result;
}

static PyObject *__str__(PyObject *self)
{
  PyObject *result;
  char buf[16];
  int i,n;
  addr_object *object = (addr_object *)self;

  sprintf(buf,"%s:", self->ob_type->tp_name);
  result = PyString_FromString(buf);
  for (i=0; i<object->addr.length; i++) {
    if (i && !(i % 16)) {
      PyString_ConcatAndDel(&result, PyString_FromString("\n"));
      for (n=0; n<=strlen(self->ob_type->tp_name); n++) {
        PyString_ConcatAndDel(&result, PyString_FromString(" "));
      }
    }
    sprintf(buf," %02x", object->addr.address[i]);
    PyString_ConcatAndDel(&result, PyString_FromString(buf));
  }
  return result;
}

static int len(PyObject *self)
{
  addr_object *object = (addr_object *)self;
  return object->addr.length;
}

static PyObject *item(PyObject *self, int index)
{
  addr_object *object = (addr_object *)self;
  if (index < 0 || index >= object->addr.length) {
    PyErr_SetString(PyExc_IndexError, "index out of range");
    return NULL;
  }
  return PyString_FromStringAndSize(object->addr.address+index, 1);
}

static PyObject *slice(PyObject *self, int start, int end)
{
  addr_object *object = (addr_object *)self;
  if (start < 0)  start = 0;
  if (end < 0)  end = 0;
  if (end > object->addr.length) {
    end = object->addr.length;
  }
  if (end < start) {
    /* Will return an empty string (len == 0). */
    end = start;
  }
  return PyString_FromStringAndSize(object->addr.address+start, end-start);
}

static void
addr_dealloc(PyObject *self)
{
  n_Addr_instances -= 1;
  PyObject_Del(self); // Accounted for (in dealloc).
}

// Get an NPCI attribute value. Things that can be done automatically
// do not appear here and are described in the npci_memberlist[] array.
// They only include simple types for now. Strings will work in 2.1.1.
// Bitfields will need some more magic from the Python guys.

static PyObject *
addr_getattr(addr_object *self, char *name)
{
  if (strcmp(name, "__members__") == 0)
    return Py_BuildValue("[ss]", "length", "address");

  if (strcmp(name, "length") == 0)
    return Py_BuildValue("i", self->addr.length);

  if (strcmp(name, "address") == 0)
    return Py_BuildValue("s#", self->addr.address, self->addr.length);

  return Py_FindMethod(addr_methods, (PyObject*)self, name);
}

// This is the complement of npci_getattr() and all the comments for
// that function apply here as well. The only non-symmetry is due to
// the validation code necessary variable sized arguments like strings.
// Some range checking may be useful for integer and bitfields in the
// future.

static int
addr_setattr(addr_object *self, char *name, PyObject *o)
{
  if (strcmp(name, "length") == 0) {
    PyErr_SetString(PyExc_TypeError,
                    "object doesn't support item assignment");
    return -1;
  }

  if (strcmp(name, "address") == 0) {
    if (PyString_Size(o) < sizeof(self->addr.address)) {
      memcpy(self->addr.address, PyString_AsString(o), PyString_Size(o));
      self->addr.length = (unsigned char)PyString_Size(o);
      return 0;
    } else {
      broadway_raise("EOverflow", PyString_FromString("address too long."),
                     NULL);
      return -1;
    }
  }
  PyErr_SetString(PyExc_AttributeError, name);
  return -1;
}

PyTypeObject _AddrType = {
  PyObject_HEAD_INIT(&PyType_Type) /* PyObject_VAR_HEAD */
  0,				/* PyObject_VAR_HEAD */

  "Addr",			/* char *tp_name; */
  sizeof(addr_object),		/* int tp_basicsize; */
  0,				/* int tp_itemsize;       * not used much */
  addr_dealloc,			/* destructor tp_dealloc; */
  0,				/* printfunc  tp_print;   */
  (getattrfunc)addr_getattr,	/* getattrfunc  tp_getattr; * __getattr__ */
  (setattrfunc)addr_setattr,	/* setattrfunc  tp_setattr;  * __setattr__ */
  __cmp__,			/* cmpfunc  tp_compare;  * __cmp__ */
  __repr__,			/* reprfunc  tp_repr;    * __repr__ */
  0,				/* PyNumberMethods *tp_as_number; */
  &sq_methods,			/* PySequenceMethods *tp_as_sequence; */
  0,				/* PyMappingMethods *tp_as_mapping; */
  0,				/* hashfunc tp_hash;     * __hash__ */
  0,				/* ternaryfunc tp_call;  * __call__ */
  __str__,			/* reprfunc tp_str;      * __str__ */
  0,				/* getattrofunc tp_getattro; */
  0,				/* setattrofunc tp_setattro; */
  0,				/* PyBufferProcs *tp_as_buffer; */
  0,				/* long tp_flags; */
  0,				/* char *tp_doc; * Documentation string * */
  0,				/* traverseproc tp_traverse; */
  0,				/* inquiry tp_clear; */
  0,				/* richcmpfunc tp_richcompare; */
  0,				/* long tp_weaklistoffset; */
};
PyTypeObject *AddrType = &_AddrType;
