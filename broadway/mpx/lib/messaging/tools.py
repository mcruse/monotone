"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
import datetime
from mpx.lib.url import ParsedURL
Undefined = object()
Debug = False

class Address(object):
    def __init__(self, parsed):
        self.parsed = parsed
    def name(self):
        return self.parsed.path[1:]
    def hostname(self):
        return self.parsed.hostname or ""
    def fullname(self):
        return self.parsed.geturl()
    def fromurl(klass, url):
        return klass(ParsedURL.fromstring(url))
    fromurl = classmethod(fromurl)

class Counter(object):
    def __init__(self, value=0):
        self.value = 0
        super(Counter, self).__init__()
    def get(self):
        return self.value
    def increment(self):
        current = self.value
        self.value = self.value + 1
        return current
    def decrement(self):
        current = self.value
        self.value = self.value - 1
        return current
    def __str__(self):
        return "%s(%d)" % (type(self).__name__, self.value)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

def debug(func):
    """
        Method decorator providing debug output on invocation.
    """    
    fname = func.func_name
    names = func.func_code.co_varnames[:func.func_code.co_argcount]
    def debuginvoke(*values, **kwargs):
        timestamp = datetime.datetime.now().time().isoformat()
        result = func(*values, **kwargs)
        if names and names[0] == "self":
            debug = getattr(values[0], "debug", True)
        else:
            debug = True
        if debug:
            argitems = zip(names, values)
            varargs = values[len(names):]
            if varargs:
                argitems.append(("*args", tuple(varargs)))
            argitems.extend(kwargs.items())
            argstring = ", ".join("%s=%r" % item for item in argitems)
            print "[%s] %s(%s) -> %r" % (timestamp, fname, argstring, result)
        return result
    return debuginvoke

