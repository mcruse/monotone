"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
from StringIO import StringIO
from mpx.lib import EnumeratedValue
from mpx.lib import msglog
from mpx.componentry import implements
from mpx.lib.neode.node import ConfigurableNode
from mpx.lib.bacnet.datatype import _data as BACnetDataType
from mpx.lib.bacnet.datatype import _enum as BACnetEnumBase
from utilities import jsonlib
from interfaces import *

class COVJSONFormatter(ConfigurableNode):
    implements(ICOVDataFormatter)
    
    def format(self, covdata, **kw):
        covstructure = _SimpleCOVStructure(covdata)
        return JSONString(jsonlib.write(covstructure))

class JSONStream(StringIO):
    mimetype = 'text/json'

class JSONString(str):
    mimetype = 'text/json'

def as_simple_result(value):
    result = {}
    if isinstance(value, Exception):
        result['type'] = 'Exception'
        result['name'] = value.__class__.__name__
        result['args'] = getattr(value, 'args', ())
        result['detail'] = repr(value)
        result['value'] = None
    else:
        result['value'] = as_simple_value(value)
    return result

##
# Capture and convert instances into simple data 
# types that can be written using JSON library.
# JSON library cannot even accept new-style extensions 
# of simple types.
def as_simple_value(value):
    if isinstance(value, (EnumeratedValue, BACnetEnumBase)):
        value = {'value': int(value), 'name': str(value)}
    elif isinstance(value, BACnetDataType):
        value = value.value
    elif isinstance(value, (list, tuple)):
        value = type(value)(map(as_simple_value, value))
    return value

###
#    Although class subsclasses dict, method 
#    '__new__' returns an instance of an actual 
#    dictionary.  This is a workaround for the json 
#    library which only works with native pyhton types, 
#    and not subsclasses.
#
#    Using resultdict.update() rather than replacing 
#    value alone so that handling of exceptions or 
#    other unique scenarios can modify the result 
#    dictionary itself, and not just the value.  
#    This allows the value in those scenarios to be 
#    set to None, indicating invalid, while additional 
#    details can be included with in formatted data.
##
class _SimpleResultStructure(dict):
    KEYS = ['cached', 'timestamp', 'value']
    def __new__(klass, resultdict):
        values = map(resultdict.get, klass.KEYS)
        resultdict = dict(zip(klass.KEYS, values))
        resultdict.update(as_simple_result(values[-1]))
        return resultdict

###
#    Although class subsclasses dict, method 
#    '__new__' returns an instance of an actual 
#    dictionary.  This is a workaround for the json 
#    library which only works with native pyhton types, 
#    and not subsclasses.
##
class _SimpleCOVStructure(dict):
    def __new__(klass, covdict):
        names = covdict.keys()
        results = map(covdict.get, names)
        try: 
            values = map(_SimpleResultStructure, results)
        except AttributeError:
            nonecount = results.count(None)
            if nonecount == 0:
                raise
            msglog.log('broadway', msglog.types.WARN, 
                       'COV Conversion object filtering NoneType values. ')
            msglog.log('broadway', msglog.types.INFO, 
                       'Original COV dictionary was: %r' % covdict)
            while nonecount:
                index = results.index(None)
                results.pop(index)
                names.pop(index)
                nonecount = nonecount - 1
            values = map(_SimpleResultStructure, results)
        return dict(zip(names, values))
