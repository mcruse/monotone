/*
Copyright (C) 2003 2010 2011 Cisco Systems

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

static PyObject * set_custom_baud(PyObject *self, PyObject *args);

#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include <config.h>
#ifdef HAVE_SYS_IO_H
#include <sys/io.h>
#endif

#include <sys/ioctl.h>
#include <asm/ioctls.h>
#include <fcntl.h>
#include <termios.h>
#include <errno.h>

#include <linux/serial.h>

static PyObject *
set_custom_baud(self, args)
	PyObject *self;
	PyObject *args;
{
	int fd = -1, bps = 0;
	double dCustDiv = 0.0, dErr = 0.0;
	struct serial_struct ss;
	char msg[256];

	if((!PyArg_ParseTuple(args, "ii", &fd, &bps)) || (fd < 0) || (bps < 1))
	{
		PyErr_SetString(PyExc_TypeError, 
				"set_custom_baud requires two integers: fd > -1, baud > 0.");
		return NULL;
	}
	
	// Get current serial port settings:
	memset(&ss, 0, sizeof(ss));
	ioctl(fd, TIOCGSERIAL, &ss);
	ss.flags |= ASYNC_SPD_CUST;
	
	// Calc custom_divisor, and check for excessive bit rate error (more than 5%):
	dCustDiv = (double)(ss.baud_base) / (double)bps;
	ss.custom_divisor = (unsigned int)(dCustDiv + 0.5);
	dErr = (fabs(dCustDiv - ss.custom_divisor) / dCustDiv);
	if(dErr > 0.05)
	{
		sprintf(msg, "set_custom_baud: excessive bit rate error = %0.2f", dErr);
		PyErr_SetString(PyExc_ValueError, msg);
		return NULL;
	}
	
	// Set custom_divisor without changing other serial port settings:
	if(ioctl(fd, TIOCSSERIAL, &ss) != 0)
	{
		PyErr_SetFromErrno(PyExc_OSError);
		return NULL;
	}
		
	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef SetSerMethods[] = {
	
	{"set_custom_baud",  set_custom_baud, METH_VARARGS,
		"Sets custom baud rate by setting custom_divisor of serial_struct."},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

void
initset_ser(void)
{
	(void) Py_InitModule("set_ser", SetSerMethods);
}

