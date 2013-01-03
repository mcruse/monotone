/*
Copyright (C) 2011 Cisco Systems

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

#include <errno.h>
#include <time.h>
#include <stdint.h>
#include <sys/times.h>
#include <sys/sysinfo.h>

static int wHertz;
static unsigned long uptime_offset;
static double last_uptime;
static double max_uptime;
#ifdef DEBUG
static double override_secs;
#endif

// If you want a bunch of output, un-comment the following line,
// or compile with -DVERBOSE
//#define VERBOSE
// If you want even more output, un-comment the following line,
// or compile with -DEXTEA_VERBOSE
//#define EXTRA_VERBOSE

#ifdef EXTRA_VERBOSE
#define VERBOSE
#endif

static char __doc__[] = "##\n# This module provides the API required "
                        "to get seconds past boot.\n#\n"
                        "# Note: The uptime (raw_secs) will wrap "
                        "if the system is up long enough.\n#\n";

// posix_error, ripped off from Modules/posixmodule.c
static PyObject *
posix_error(void)
{
        return PyErr_SetFromErrno(PyExc_OSError);
}

#ifdef DEBUG
static char __doc__override_secs[] = "##\n# MontyDoc string for override_secs.";

static PyObject *
_override_secs(PyObject *self, PyObject *args)
{
        double new_override_secs;

	// Make sure that one double was specified
        if (!PyArg_ParseTuple(args, "d", &new_override_secs))
                return NULL;
#ifdef VERBOSE
	printf("Got new override seconds of %lf.\n", new_override_secs);
#endif
	// Note: An override value of 0.0 has a special meaning.  Basically
	//       reset all internal data structures.
	if (override_secs == 0.0) {
	  last_uptime = 0.0;
	  max_uptime = 0.0;
	  uptime_offset = 0;
	}

	override_secs = new_override_secs;

	return Py_BuildValue("d", override_secs);
}
#endif

static char __doc__secs[] = "##\n# MontyDoc string for secs.";

static PyObject *
_uptime_secs(PyObject *self, PyObject *args)
{
    int iRslt = -1;
    double cur_uptime = 0.0;
    struct sysinfo si;

	// Make sure that no arguments were specified
    if(!PyArg_ParseTuple(args, ":secs"))
        return NULL;
    errno = 0;
    iRslt = sysinfo(&si);
    if(iRslt < 0)
        return posix_error();
    cur_uptime = (double)(si.uptime);

#ifdef DEBUG
	// If we are in debug mode, check to see if the uptime has
	// been overriden.
    if (override_secs != 0.0)
 	    cur_uptime = override_secs;
#endif

	// Now check for a wrap.
	if (cur_uptime < (last_uptime - 1.0)) {
#ifdef VERBOSE
 	        printf("Detected a wrap! (%lf and %lf).\n", cur_uptime, last_uptime);
#endif
	        // OK, we've got a wrap.
     	        if (last_uptime > max_uptime) {
		      max_uptime = last_uptime;
#ifdef VERBOSE
		      printf("max_uptime is now set to %lf.\n", max_uptime);
#endif
		}
		uptime_offset += (unsigned long) max_uptime;
#ifdef VERBOSE
		printf("uptime_offset is now %ld.\n", uptime_offset);
#endif
	}
	
	last_uptime = cur_uptime;
   
	// If we've had a wrap, add the uptime_offset to the current uptime
	if (uptime_offset != 0) {
   	        cur_uptime += (double) uptime_offset;
	}
#ifdef EXTRA_VERBOSE
	printf("uptime_secs: Returning %lf.\n", cur_uptime);
#endif
        return Py_BuildValue("d", cur_uptime);
}

static char __doc__raw_secs[] = "##\n# MontyDoc string for raw_secs.";

static PyObject *
_uptime_raw_secs(PyObject *self, PyObject *args)
{
    int iRslt = -1;
    double cur_uptime = 0.0;
    struct sysinfo si;
    // Make sure that no arguments were specified:
    if (!PyArg_ParseTuple(args, ":secs"))
        return NULL;
    errno = 0;
    iRslt = sysinfo(&si);
    if(iRslt < 0)
        return posix_error();
    cur_uptime = (double)(si.uptime);
    return Py_BuildValue("d", cur_uptime);
}

static char __doc__max_uptime[] = "##\n# MontyDoc string for max_uptime.";

static PyObject *
_max_uptime(PyObject *self, PyObject *args)
{
        // Make sure that no arguments were specified
        if (!PyArg_ParseTuple(args, ":max_uptime"))
                return NULL;
        return Py_BuildValue("d", (double)INT32_MAX / (double)wHertz * (double)2);
}

static char __doc__tics_per_sec[] = "##\n# MontyDoc string for tics_per_sec.";

static PyObject *
_tics_per_sec(PyObject *self, PyObject *args)
{
        // Make sure that no arguments were specified
        if (!PyArg_ParseTuple(args, ":tics_per_sec"))
                return NULL;
        return Py_BuildValue("d", (double)wHertz);
}

static PyMethodDef pyuptime_methods[] = {
    {"secs", _uptime_secs, METH_VARARGS, __doc__secs},
#ifdef DEBUG
	{"override_secs", _override_secs, METH_VARARGS, __doc__override_secs},
#endif
	{"raw_secs", _uptime_raw_secs, METH_VARARGS, __doc__raw_secs},
	{"max_uptime", _max_uptime, METH_VARARGS, __doc__max_uptime},
	{"tics_per_sec", _tics_per_sec, METH_VARARGS, __doc__tics_per_sec},
	{NULL, NULL}
};

#ifdef DEBUG
void
inituptime_debug(void)
#else
void
inituptime(void)
#endif
{ 
        PyObject *module;
  
        // Initialize global variables
        uptime_offset = 0;
	last_uptime = 0.0;
	max_uptime = 0.0;
#ifdef DEBUG
	override_secs = 0.0;
#endif

	// Initialize wHertz (or don't bother):
	// DOES NOT WORK WITH MEGATRON KERNEL (which uses CONFIG_HZ == 1000)
	// Do not attempt to use the value for wHertz ANYWHERE! (Note that Megatron
	// kernel and MOE are provided by MonteVista Linux, and are subject to ...
	// um ... "irregularities"...
	wHertz = sysconf(_SC_CLK_TCK);
	if (wHertz == -1) 
	{
	  // Not exactly clear what to do in case of a failure here.
	  // Guess we'll just have to assume that we are at
	  // 100 ticks per second.
	  wHertz = 100;

	  printf("Error getting ticks per second, assuming 100 per second.\n");
	}

	// Create the new module definition.
#ifdef DEBUG
        module = Py_InitModule("uptime_debug", pyuptime_methods);
#else
	module = Py_InitModule("uptime", pyuptime_methods);
#endif

        // Add the modules documentation.
        PyModule_AddStringConstant(module, "__doc__", __doc__);
}
