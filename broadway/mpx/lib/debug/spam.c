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
// @todo Rewrite as a real class.

#include <Python.h>

static PyObject *spam_system(PyObject *self, PyObject *args);
static PyObject *crash_system(PyObject *self, PyObject *args);

static PyObject *
spam_system(self, args)
    PyObject *self;
    PyObject *args;
{
    char *command;
    int sts;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;
    sts = system(command);
    return Py_BuildValue("i", sts);
}

static PyObject *
crash_system(self, args)
    PyObject *self;
    PyObject *args;
{
    //char *command;
    int sts;
    int *status;

    status = 0;
    sts = *status; //CRASH!!!!

    return Py_BuildValue("i", sts);
}

static PyMethodDef SpamMethods[] = {
    
    {"system",  spam_system, METH_VARARGS,
     "Execute a shell command."},
    {"crash",  crash_system, METH_VARARGS,
     "Execute a controlled crash."},
    
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

void
initspam(void)
{
    (void) Py_InitModule("spam", SpamMethods);
}

