"""
Copyright (C) 2002 2005 2010 2011 Cisco Systems

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
import sys
import array
import traceback
from mpx._python import types as _types
from mpx.lib.msglog import types, log
StringType = _types.StringType
ClassType = _types.ClassType
TracebackType = _types.TracebackType
del _types

class _Exception:
    def __init__(self):
        self.sys = sys
        self.array = array
        self.traceback = traceback
        self.log = log
        self.types = types
        self.StringType = StringType
        self.ClassType = ClassType
        self.TracebackType = TracebackType
    def __call__(self,e_type=types.ERR,exc_info=None,prefix='Unhandled',
                 level=0):
        msg = None
        text = None
        stack = None
        if exc_info is None:
            exc_info = self.sys.exc_info()
        try:
            if not exc_info or exc_info == (None,None,None):
                self.log(e_type,
                         'mpx.lib.msglog.exception() called ' +
                         'outside of an exception.')
                return
            msg = self.array.array('c', prefix)
            msg.fromstring(' ')
            if type(exc_info[0]) == self.ClassType:# Build an appropriate
                msg.fromstring(str(exc_info[0]))   # message for Exception
                msg.fromstring(' exception.')      # classes.
            elif type(exc_info[0]) == self.StringType:# Build an appropriate
                msg.fromstring('exception ')	      # message for an
                msg.fromstring(repr(exc_info[0]))     # exception string.
                msg.fromstring('.')
            else:				# Build an appropriate message
                				# for something impossible.
                msg.fromstring('exception of unknown type.')
            self.log(e_type, msg.tostring())
            msg = self.array.array('c')
            for text in self.traceback.format_exception_only(exc_info[0],
                                                             exc_info[1]):
                msg.fromstring(text)
            if len(msg):
                if msg[-1] == '\n':
                    msg.pop()
                self.log(self.types.EXC, msg.tostring())
            msg = self.array.array('c')
            stack = exc_info[2]
            if type(stack) == self.TracebackType:
                stack = self.traceback.format_tb(stack)
            else:
                stack = self.traceback.format_list(stack)
            for text in stack:
                msg.fromstring(text)
            if len(msg):
                if msg[-1] == '\n':
                    msg.pop()
                self.log(self.types.TB, msg.tostring())
        except Exception,e:
            # Best attempt to log an unexpected failure of this function.
            # Note: @fixme.  For now, just print a message and return.
            #       The code below the return doesn't seem to work right,
            #       and is generating tons of noise.
            str_exception = str(e)
            if str_exception == 'maximum recursion depth exceeded':
                # For now, just swallow this exception as it occurs too many
                # times to really be useful.
                pass
            else:
                msg = 'mpx.lib.msglog.exception() failed with Exception: %s.' % str_exception
                print msg
            return
            if not level:
                try:
                    print "*** INTERNAL ERROR:  FAILED TO LOG. ***"
                    self.traceback.print_exception(exc_info[0], exc_info[1],
                                                   exc_info[2])
                    self.log(self.types.ERR, msg)
                    self.__call__(self.types.FATAL, self.sys.exc_info(),
                                  e_type, level+1)
                    print "*** INTERNAL ERROR:  FAILED TO LOG BECAUSE. ***"
                    self.traceback.print_exc()
                except Exception,e:
                    try:
                        print msg
                        print "*** INTERNAL ERROR:  " + \
                              "FAILED TO LOG WHY WE FAILED TO LOG. (Exception: %s) ***" % str(e)
                        self.traceback.print_exc()
                    except:	pass # Things are really in a bad way...
            else:
                print "*** INTERNAL ERROR:  EXCEPTION LOG TOO REENTRANT. ***"
        del msg
        del exc_info
        del text
        del stack

##
# Log an exception.
#
# @param e_type  Type to use when loggin the exception.
# @default mpx.lib.msglog.types.FATAL
# @param exc_info  The exc_info() tuple to log.
# @defualt sys.exc_info()
#
exception = _Exception()
