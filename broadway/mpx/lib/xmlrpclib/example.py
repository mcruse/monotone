"""
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
"""
print ">>> from mpx.lib.xmlrpclib import *"
from mpx.lib.xmlrpclib import *
print ">>> import types"
import types
print """
#
# default marshaller does not handle derived classes well.
#
"""
print ">>> dumps(('this is a test.',)"
print dumps(('this is a test.',))

print """
#
# Normal str is explicitly handled, but create a class derived from str
# to test it with...
#
>>> class StringClass(str):
...     def __new__(self, value):
...         return str.__new__(self, value)
>>>"""

class StringClass(str):
    def __new__(self, value):
        return str.__new__(self, value)

print ">>> print dumps((StringClass('this is a test.'),)"
try:
    print dumps((StringClass("this is a test."),))
except:
    import traceback
    traceback.print_exc()

print """
#
# But I've modified mpx.lib.xmlrpc to extend the way marshallers can be
# registerred to support "best fit" derived classes.
#
# To install a marshaller for all instances derived from str.
#
>>> register_marshaller(types.StringType, StringMarshaller())"""
register_marshaller(types.StringType, StringMarshaller())
print ">>> print dumps((StringClass('this is a test.'),)"
print dumps((StringClass("this is a test."),))

print """
#
# Notice that the StringMarshaller implementation also handles CData, etc...
#

>>> print dumps((StringClass("<![CDATA[this is a test.]]>"),))
"""
print dumps((StringClass("<![CDATA[this is a test.]]>"),))
print '>>> print dumps((StringClass("Text with ]]>"),))'
print dumps((StringClass("Text with ]]>"),))

print """
#
# The StringMarshaller is more advanced then the built in string marshelling.
# We could remove our escape hack and replace the string marshalling.
#
>>> Marshaller.dispatch[types.StringType] = \\
    Marshaller.dispatch[types.InstanceType]
"""
Marshaller.dispatch[types.StringType] = Marshaller.dispatch[types.InstanceType]
print """
#
# We could do a cleaner reimplementation, but this just show that now the str
# marshaller uses the InstanceType, which I've extended to support registerring
# handlers, blah, blah, blah...
#
>>> print dumps(('this is a test.',)) # Look ma, CDATA goodies!
"""
print dumps(('this is a test.',))

from mpx.lib import EnumeratedValue
print dumps((EnumeratedValue(2,"asdf"),))

from mpx.lib.magnitude import MagnitudeInterface

print dumps((MagnitudeInterface(1),))
print dumps((MagnitudeInterface(2L),))
print dumps((MagnitudeInterface(3.0),))
