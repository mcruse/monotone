"""
Copyright (C) 2003 2005 2010 2011 Cisco Systems

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
## @notes Class TCS
##        Simple abstraction for dynamically
##        discovering TCS nodes and presenting
##        them as nodes in the framework

import array
import time
import random
import string

from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.lib.configure import set_attribute, get_attribute, \
     as_boolean, as_onoff, REQUIRED
from mpx.lib.exceptions import EAlreadyRunning, \
     ETimeout, EInvalidValue, MpxException, EPermission
from mpx.lib.tcs import value
from mpx.lib import EnumeratedDictionary, EnumeratedValue
from mpx.lib import datetime
from mpx.lib.tcs import command
from mpx.lib.node import as_node_url

debug = 0
class Result:
    ##
    # The node's value.
    #
    value = None
    ##
    # The timestamp of when the value was actually retrieved
    # from the device.  This is important in some cases where
    # caching is used as the timestamp will show when the value
    # was last updated.
    timestamp = None
    ##
    # True iff the value returned was a cached value.
    cached = 1
## Class TCS point
#  Used to encapsulate a single point on the TCS controller
#
#@todo  Limit test against range     
class _Value(CompositeNode):
    
    def configure(self, dict):
        self.result = None
        CompositeNode.configure(self, dict)    
        set_attribute(self, 'debug', 0, dict, as_boolean)            
        set_attribute(self, 'parameter', REQUIRED, dict)
        set_attribute(self, 'position', REQUIRED, dict, int)
        set_attribute(self, 'description', '', dict)
        set_attribute(self, 'ttl', 1.0, dict, float)
        set_attribute(self, 'readwrite', 0, dict, int)
        if self.readwrite != 1:
            self.set = self._set
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'parameter',config, str)
        get_attribute(self, 'debug',config, str)
        get_attribute(self, 'position', config, str)
        get_attribute(self, 'description', config, str)
        get_attribute(self, 'ttl', config, str)
        get_attribute(self, 'readwrite', config, str)
        return config
    def _new_result(self, value): #just get it
        self.value = value
        self.result = Result()
        self.result.timestamp = time.time()
        self.cached = 1
        self.result.value = self.value
        return self.result
    def _get_result(self): #just get it
        self.value = self.point.get()
        return self._new_result(self.value)
    def get_result(self, skipCache=0, **keywords): 
        if debug: print 'get from cache'
        if skipCache:
            if debug: print 'skipping cache, get just this point'
            return self._get_result()
        if self.result: #there was a previously cached value, see if it is any good
            now = time.time()
            if (now - self.ttl) < self.result.timestamp:
                return self.result #give them the cached result
        if self.parameter != 'H': #holiday entries cannot be grouped
            if self.parent.__class__ == ParameterGroup: #get all peers at once
                self.parent.get_children_values() #this will update self.result
                return self.result
        return self._get_result()
    def get(self, skip_cache=0):
        if self.readwrite == 2: #write only
            raise EPermission('write-only', as_node_url(self))
        return self.get_result(skip_cache).value
    def _set(self, v):
        if (self.parameter == 'L' or self.parameter == 'K' or self.parameter == 'M'):
            return #those are read only
        if v == "":
            v = None
        else:
            v = float(v)
            self.point.set(v)
            self.result = None #force new read next time

    def start(self):
        if self.readwrite != 1: #since not readonly
            if not(self.parameter == 'L' or self.parameter == 'K' or self.parameter == 'M'):
                self.set = self._set  #read only parameters
        self.line_handler = self.parent.line_handler
        self.unit_number = self.parent.unit_number
        CompositeNode.start(self)

class Value(_Value):
    def __init__(self):
        _Value.__init__(self)
        self.__node_id__ = '1256'
    def configuration(self):
        config = _Value.configuration(self)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        _Value.start(self)
        self.point = value.TCSValue(self.line_handler, self.parameter, self.position, self.unit_number)
  
class PValue(Value):
    def __init__(self):
        Value.__init__(self)
        self.__node_id__ = '120062'
    def configure(self, dict):
        if not dict.has_key('parameter'):
            dict['parameter'] = None
        Value.configure(self, dict)    
    def configuration(self):
        config = _Value.configuration(self)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        self.parameter = self.parent.parameter
        Value.start(self)    
 
class Time(_Value):
    def __init__(self):
        _Value.__init__(self)
        self.__node_id__ = '1257'
    def configuration(self):
        config = _Value.configuration(self)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        _Value.start(self)
        self.point = value.TCSTime(self.line_handler, self.parameter, self.position, self.unit_number)
    def get(self, skip_cache=0):
        answer = datetime.TimeOfDay(_Value.get(self, skip_cache) * 60)
        if debug: print 'get time: ', type(answer), str(answer)
        return str(answer)
    def _set(self, value):
        if debug: print 'set time: ', value
        _Value._set(self, int(datetime.TimeOfDay(value)) / 60)
    
class PTime(Time):
    def __init__(self):
        Time.__init__(self)
        self.__node_id__ = '120064'
    def configure(self, dict):
        if not dict.has_key('parameter'):
            dict['parameter'] = None
        Time.configure(self, dict)    
    def start(self):
        self.parameter = self.parent.parameter
        Time.start(self)    
    def configuration(self):
        config = Time.configuration(self)
        get_attribute(self, '__node_id__', config, str)
        return config

class Date(_Value):
    def __init__(self):
        _Value.__init__(self)
        self.__node_id__ = '120067'
    def configuration(self):
        config = _Value.configuration(self)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        _Value.start(self)
        self.point = value.TCSHoliday(self.line_handler, self.parameter, self.position, self.unit_number)
    ## value = tuple of month, date, duration
    def get(self, skipCache=1):
        answer = _Value.get(self, 1) #always skip cache
        if answer is None:
            return answer
        if debug: print 'date = ', str(answer)
        return str((answer.start_date.month, answer.start_date.day, answer.get_duration()))    
    def _set(self, value):
        if debug: print 'set holiday: ', value
        if value == 'None':
            self.point.set(None)
            return
        v = eval(value)
        dr = datetime.DateRange()
        dr.start_date = datetime.Date(month=v[0],day=v[1])
        dr.end_date = dr.start_date + (max(v[2] - 1,0))
        self.point.set(dr)
    
class PDate(Date):
    def __init__(self):
        Date.__init__(self)
        self.__node_id__ = '120066'
    def configure(self, dict):
        if not dict.has_key('parameter'):
            dict['parameter'] = None
        Date.configure(self, dict)    
    def configuration(self):
        config = Date.configuration(self)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        self.parameter = self.parent.parameter
        Date.start(self)    

class Type(_Value):
    def start(self):
        _Value.start(self)
        self.point = value.TCSType(self.line_handler, self.parameter, self.position, self.unit_number)

class Enumerator(_Value):
    def __init__(self):
        _Value.__init__(self)
        self.__node_id__ = '120065'
    def configure(self, dict):
        _Value.configure(self, dict)    
        set_attribute(self, 'scale_or_enum', REQUIRED, dict)
        if type(self.scale_or_enum) == str: #eonvert to list of words
            if self.scale_or_enum[0] == '[': #self discovered
                self.scale_or_enum = eval(self.scale_or_enum)
            else: #static
                self.scale_or_enum = string.split(self.scale_or_enum, ';')
    def configuration(self):
        config = _Value.configuration(self)
        get_attribute(self, 'scale_or_enum', config, str)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        i = 0
        enumeration = {}
        for word in self.scale_or_enum:
            enumeration[i] = word
            i += 1
        self.enumeration = EnumeratedDictionary(enumeration)
        _Value.start(self)
        self.point = value.TCSValue(self.line_handler, self.parameter, self.position, self.unit_number)
    def get(self, skipCache=0):
        answer = _Value.get(self, skipCache)
        if self.enumeration.has_key(answer):
            return self.enumeration[answer]
        return answer
    def _set(self, value):
        if self.enumeration.has_key(value):
            _Value._set(self, int(self.enumeration[value]))
            return
        raise EInvalidValue(str(self.enumeration), str(value), 'not found in enumeration list')
        
class PEnumerator(Enumerator):
    def __init__(self):
        Enumerator.__init__(self)
        self.__node_id__ = '120063'
    def configure(self, dict):
        if not dict.has_key('parameter'):
            dict['parameter'] = None
        Enumerator.configure(self, dict)    
    def configuration(self):
        config = Enumerator.configuration(self)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        self.parameter = self.parent.parameter
        Enumerator.start(self)    

class ParameterGroup(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.__node_id__ = '120061'
        self.positions = None
    def configure(self, dict):
        CompositeNode.configure(self, dict)
        set_attribute(self, 'parameter', REQUIRED, dict)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'parameter', config)
        get_attribute(self, '__node_id__', config, str)
        return config
    def start(self):
        self.line_handler = self.parent.line_handler
        self.unit_number = self.parent.unit_number
        CompositeNode.start(self)
    def get(self, skipCache=0):
        answer = self.children_names()
        answer.sort()
        return answer
    def get_children_values(self): #get all readable children
        if self.positions is None: #build the list of readable positions
            self.positions = []
            for p in self.children_nodes():
                if p.readwrite != 2:
                    self.positions.append(p.position)
            self.positions.sort()
        c = command.GetValue(self.parameter, self.positions)
        if debug: print str(c)
        last_response = self.line_handler.send_request_with_response(c,self.unit_number,numretries=3)
        if debug: print str(last_response)
        for p in self.children_nodes():
            p._new_result(last_response.at(p.position)) #updates cached result
    
