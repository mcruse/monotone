"""
Copyright (C) 2010 2011 Cisco Systems

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
"""
# Note: By design this module has as little dependency on the framework as possible.
#       Any dependencies which exist should be optional.

import time

didimport = 0
try:
    from mpx.lib.threading import Lock
    didimport = 1
except:
    pass
if not didimport:
    from threading import Lock

didimport = 0
try:
    from moab.linux.lib import uptime
    secs_func = uptime.secs
    didimport = 0
except:
    pass
if not didimport:
    secs_func = time.time

didimport = 0
try:
    from mpx.lib.exceptions import MpxException
    didimport = 1
except:
    pass
if not didimport:
    # Redefine a watered-down MpxException here to derive from.
    class MpxException(Exception):
        ##
        # The constructor for the base MPX exception class.
        #
        # @param *args  Tuple of all non-keyword args.
        # @param **keywords Dictionary of keyword args.
        def __init__(self, *args, **keywords):
            Exception.__init__(self, *args)
            self.keywords = keywords
        def __str__(self):
            if len(self.args) == 1:
                return str(self.args[0])
            elif len(self.args) > 1:
                return str(self.args)
            return ''

class GDException(MpxException):
    pass

class GDTimeoutException(GDException):
    pass

class GDConnectionClosedException(GDException):
    pass

def get_lock():
    return Lock()

def get_time():
    return secs_func()

def dump_binary_str(buffer):
    retstr = ''
    for x in buffer:
        retstr += "%.2X " % ord(x)
    # Trim the last space if present
    if len(retstr):
        retstr = retstr[:-1]
    return retstr
