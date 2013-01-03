"""
Copyright (C) 2002 2005 2006 2010 2011 Cisco Systems

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
##
# 

import types

# Create the mpx.lib.msglog.log() function.

import types

# Create the msglog.msglog singleton.
from _msglog import Msglog
_ml = Msglog()

##
# Log a message to the MPX msglog.
# @param application The application that logs the message, i.e broadway
# @param type
#   The type of message.  See mpx.lib.msglog.types.
# @param message
#  The text to log.
#
def log(*args):
    if len(args) == 2:
        _log('unknown',args[0],args[1])
    else:
        _log(*args)
    return

def _log(application,type,message):
    return _ml.add_entry([application,type,message])

def add(message, type, **kw):
    application = kw.get("application", "broadway")
    return log(application, type, message)

def debug(message, **kw):
    return add(message, types.DB, **kw)

def inform(message, **kw):
    return add(message, types.INFO, **kw)

def warn(message, **kw):
    return add(message, types.WARN, **kw)

def error(message, **kw):
    return add(message, types.ERR, **kw)

##
# return A reference to the underlying Log object.
def log_object():
    return _ml.log

##
# @see get_column_names
# @depricated typo
def get_columns_names():
    return _ml.log.get_column_names()

##
# @author Craig Warren
# @return a dictionary of the msglog's column names.
def get_column_names():
    return _ml.log.get_column_names()

##
# @author Craig Warren
# @return a dictionary of the msglog's column objects.
def get_columns():
    return _ml.log.get_columns()

# Create msglog.exception() function.
from _exception import exception
del _exception

from string import join as _join
from traceback import extract_stack as _extract_stack
from traceback import format_list as _format_list

##
# Log the current stack trace.
# @param application The application logging the TB.
# @param unknown  No application specified.
# @param limit  Limit the depth of the logged traceback.
# @default None  Log the whole traceback.
#
def traceback(application='unknown', limit=None):
    stack = _extract_stack(limit)
    formatted_stack = _format_list(stack[:-1])
    _log(application, types.TB, _join(formatted_stack,''))
    return
