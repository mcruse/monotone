"""
Copyright (C) 2002 2003 2004 2007 2010 2011 Cisco Systems

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
# Provides the factory used to instantiate the ABB SCD2000 ION.

import array
import time
from mpx.lib.modbus.base import buffer
from mpx.lib.modbus.server import Server as _Server
from mpx.ion import Result
from mpx.lib import msglog
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.debug import dump_tostring
from mpx.lib.exceptions import *
from mpx.lib.node import ConfigurableNode, CompositeNode, as_node
from mpx.lib.modbus.conversions import ConvertRegister, ConvertBitField, ConvertValue
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.node.proxy import ProxyAbstractClass

debug = 0
_module_lock = Lock()

##
# @todo Speed up timeouts on missing devices
# @todo Have modbus parity check on start

##
# Modules the SCD2000 as an ION.
class ServerDevice(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.debug = 0
        self.server = _Server()
        self.proxy = None

    def configure(self, config):
        if self.debug: print 'Server Device Configure start '
        CompositeNode.configure(self, config) #skip our parents configure to delay building the register map
        set_attribute(self, 'address', REQUIRED, config, int)
        set_attribute(self, 'line_handler', self.parent, config, as_node)
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'proxy', 0, config, int)
        if debug: self.debug = debug  #override individual debug with module debug if present
        if self.debug: print 'Server Device Configured ', self.name

    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'address', config, str)
        get_attribute(self, 'line_handler', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'proxy', config, str)
        return config
        
    def start(self):
        if self.debug: print 'start generic server device: ', self.name
        CompositeNode.start(self) #let the children play (and ask find_cache_for)
        if self.debug: print 'started generic server device: ', self.name

    def add_register_to_map_for(self, register, node):
        self.server.add_register_to_map_for(register, node)

    def get(self,skipCache=0):
        return self.get_result(skipCache).value

    def get_result(self,skipCache=0, **keywords):
        result = Result()
        result.value = len(self.children_nodes())
        result.timestamp = time.time()
        return result

    def get_group_base_register(self):
        return 0
    
    def perform_command(self, command):
        return self.server.perform_command(command)
    def is_proxy(self):
        return self.proxy
        
class _GenericPoint(CompositeNode, ProxyAbstractClass):
    def __init__(self):
        CompositeNode.__init__(self)
        ProxyAbstractClass.__init__(self)
        self.debug = 0
        self.value = None
        self.buffer = None
        self.last_set_exception = None
    def configure(self, config):
        if self.debug: print 'Configure modbus point'
        CompositeNode.configure(self, config)
        set_attribute(self, 'register', REQUIRED, config, int)
        self.offset = self.register - self.base_register()
        set_attribute(self, 'read_only', 1, config, int)
        set_attribute(self, 'debug', 1, config, int)
        set_attribute(self, 'length', 1, config, int)
        ProxyAbstractClass.configure(self, config)
        if self.debug: print 'Configured modbus point', self
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'register', config, str)
        get_attribute(self, 'read_only', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'offset', config, str)
        ProxyAbstractClass.configuration(self, config)
        return config
    def start(self):
        if self.debug: print 'Start: ', self.name
        try:
            group = self.parent.get_group_base_register()
            if group is None:
                group = 0
            self.offset = self.register + group - self.base_register()
            if self.offset < 0:
                raise EInvalidValue('offset out of range for: ', self.name)
            if self.read_only == 0:
                self.set = self._set
            for i in range(0, self.length): #add self to lookup table
                self.parent.add_register_to_map_for(self.offset + self.base_register() + i, self)
        except:
            msglog.exception()
        CompositeNode.start(self)
        ProxyAbstractClass.start(self)
        if self.debug: print 'Started ', self.name
    def _set(self, value, asyncOK=1):
        if self.read_only:
            raise EPermission('read only: ', self.name)
        _module_lock.acquire()
        try:
            if value == 'None':
                value = None
            self.value = value
            self.buffer = None
            self.last_set_exception = None
        finally:
            _module_lock.release()
    def set_exception(self, exception):
        self.last_set_exception = exception
    def type_write_method(self):
        return None
    def max_register_count(self):
        return 125
    def get(self, skipCache=0):
        if self.last_set_exception:
            raise self.last_set_exception
        return self.get_result(skipCache).value
    def get_result(self, skipCache=0, **keywords):
        result = Result()
        result.timestamp = time.time()
        _module_lock.acquire()
        try:
            if self.value is None:
                if not self.buffer is None: #only affects _Register classes
                    #convert the buffer bytes to our value
                    self.convert_buffer_to_value()
            result.value = self.value
            return result
        finally:
            _module_lock.release()
    def read(self):
        if self.is_proxy():
            self.value = self.get() #@todo deal with skipcache configuration?
        if self.last_set_exception:
            raise self.last_set_exception
        return self.value
    def write(self, value):
        self.value = value
        self.last_set_exception = None
        if self.is_proxy():
            self.set(value)
    def is_proxy(self):
        return self.parent.is_proxy()
        
class Coil(_GenericPoint):
    def base_register(self):
        return 1
    def max_register_count(self):
        return 2000
    def read_function_code(self):
        return 1
    def read(self):
        _GenericPoint.read(self)
        if self.value is None:
            return 0
        return self.value
class InputStatus(_GenericPoint):
    def base_register(self):
        return 10001
    def max_register_count(self):
        return 2000
    def read_function_code(self):
        return 2
    def read(self):
        _GenericPoint.read(self)
        if self.value is None:
            return 0
        return self.value
    

_register_types = {'int'   :{1:(ConvertRegister.register_as_int, ConvertValue.convert_short),
                             2:(ConvertRegister.register_as_long, ConvertValue.convert_long)},
               'IEEE float':{2:(ConvertRegister.register_as_float, ConvertValue.convert_float),
                             4:(ConvertRegister.register_as_float8, ConvertValue.convert_float8)},
                  'hibyte' :{1:(ConvertRegister.register_hibyte, ConvertValue.convert_hibyte)},
                  'lobyte' :{1:(ConvertRegister.register_lobyte, ConvertValue.convert_lobyte)},
                  'loint'  :{1:(ConvertRegister.register_as_loint, ConvertValue.convert_loint)},
                  'hiint'  :{1:(ConvertRegister.register_as_hiint, ConvertValue.convert_hiint)},
                  'lochar' :{1:(ConvertRegister.register_as_lochar, ConvertValue.convert_lochar)},
                  'hichar' :{1:(ConvertRegister.register_as_hichar, ConvertValue.convert_hichar)},
                  'word'   :{1:(ConvertRegister.register_as_word, ConvertValue.convert_ushort),
                             2:(ConvertRegister.register_as_ulong, ConvertValue.convert_ulong)},
                  'dword'  :{2:(ConvertRegister.register_as_ulong, ConvertValue.convert_ulong)},
                  'string' :{0:(ConvertRegister.register_as_string, ConvertValue.convert_string)},
                  'zstring':{0:(ConvertRegister.register_as_zstring, ConvertValue.convert_zstring)},
                  'modulo' :{1:(ConvertRegister.register_as_modulo_10000_1, ConvertValue.convert_modulo_1),
                             2:(ConvertRegister.register_as_modulo_10000_2, ConvertValue.convert_modulo_2),
                             3:(ConvertRegister.register_as_modulo_10000_3, ConvertValue.convert_modulo_3),
                             4:(ConvertRegister.register_as_modulo_10000_4, ConvertValue.convert_modulo_4)},
                  'PowerLogic Energy':{3:(ConvertRegister.register_as_power_logic_3, ConvertValue.convert_power_logic_3),
                                       4:(ConvertRegister.register_as_power_logic_4, ConvertValue.convert_power_logic_4)},
                  'DL06 Energy':{4:(ConvertRegister.register_as_dl06_energy_4, ConvertValue.convert_dl06_energy_4)},
                  'time'   :{3:(ConvertRegister.register_as_time_3, ConvertValue.convert_time_3),
                             6:(ConvertRegister.register_as_time_6, ConvertValue.convert_time_6)}}

               
class _Register(_GenericPoint):
    def configure(self, config):
        _GenericPoint.configure(self, config)
        set_attribute(self, 'type', REQUIRED, config)
        set_attribute(self, 'length', REQUIRED, config, int)
        set_attribute(self, 'word_order', 'Network Order', config, str)
        set_attribute(self, 'byte_order', 'Network Order', config, str)
        set_attribute(self, 'bit_order', 'Network Order', config, str)
    def configuration(self):
        config = _GenericPoint.configuration(self)
        get_attribute(self, 'type', config, str)
        get_attribute(self, 'length', config, str)
        get_attribute(self, 'word_order', config, str)
        get_attribute(self, 'byte_order', config, str)
        get_attribute(self, 'bit_order', config, str)
        return config
    def start(self):
        self.orders = 0 #bit 0=byte order, bit 1=word order, bit 2=bit order. 000=Network order
        if self.byte_order != 'Network Order': self.orders += 1
        if self.word_order != 'Network Order': self.orders += 2
        if self.bit_order  != 'Network Order': self.orders += 4
        self.read_conversion = self.type_convert_value_method()
        self.write_conversion = self.type_convert_buffer_method()
        _GenericPoint.start(self)
    def type_convert_value_method(self):
        t = _register_types.get(self.type, None)
        if t is None: 
            print 'type_convert_value_method exception', self.type
            raise EInvalidValue('type',self.type,
                                          'Invalid type for %s.' % self.name)
        if self.type in ['string', 'zstring']:
            answer = t.get(0)
        else:
            answer = t.get(self.length, None)
            if answer is None: raise EInvalidValue('wrong length for type', self.name + '  ' + \
                                               self.type + '  '+ str(self.length))
        return answer[1]
    def type_convert_buffer_method(self):
        t = _register_types.get(self.type, None)
        if t is None: 
            print 'type_convert_buffer_method exception'
            raise EInvalidValue('type',self.type,
                                          'Invalid type for %s.' % self.name)
        if self.type in ['string', 'zstring']:
            answer = t.get(0)
        else:
            answer = t.get(self.length, None)
            if answer is None: raise EInvalidValue('wrong length for type', self.name + '  ' + \
                                               self.type + '  '+ str(self.length))
        return answer[0]
        
    def read(self, offset):
        if self.debug: print '_Register, modbus read :', self.name
        if self.is_proxy():
            self.value = self.get()
            self.buffer = None #force conversion
        if self.last_set_exception:
            raise self.last_set_exception
        if self.buffer is None:
            self.convert_value_to_buffer()
        if offset < self.offset:
            raise EInvalidValue('bad offset', str(offset), self.name)
        if offset - self.offset >= self.length:
            raise EInvalidValue('bad offset', str(offset), self.name)
        s = (offset - self.offset) * 2
        return self.buffer[s:s+2] #answer two bytes from our local buffer
    def write(self, offset, new_value):
        if self.debug: print '_Register, modbus write :', self.name, repr(self.buffer), repr(new_value)
        if self.buffer is None:
            self.buffer = array.array('B', '\x00'*(self.length*2))
        if offset < self.offset:
            raise EInvalidValue('bad offset', str(offset), self.name)
        if offset - self.offset >= self.length:
            raise EInvalidValue('bad offset', str(offset), self.name)
        s = (offset - self.offset) * 2
        self.buffer[s:s+2] = array.array('B', new_value) #answer two bytes from our local buffer
        if self.debug: print 'buffer now: ', repr(self.buffer)
        self.value = None #force lazy conversion
        self.last_set_exception = None
        if self.is_proxy():
            #only update on last piece of multiple register nodes
            if (offset - self.offset) == (self.length - 1):
                self.convert_buffer_to_value()
                self.set(self.value)
    def convert_value_to_buffer(self):
        value = self.value
        if value is None:
            value = 0
        cv = ConvertValue()
        self.read_conversion(cv, value, self.orders)
        self.buffer=cv.buffer
        if self.debug: print '_Register: convert value to buffer: ', self.value, self.buffer
    def convert_buffer_to_value(self):
        if self.buffer is None:
            raise EInvalidValue('modbus get before buffer written', self.name)
        cv = ConvertRegister(self.buffer)
        self.value = self.write_conversion(cv, 0, 0, self.orders)
        return self.value

class InputRegister(_Register):
    def base_register(self):
        return 30001
    def read_function_code(self):
        return 4
class HoldingRegister(_Register):
    def configure(self, config):
        _Register.configure(self, config)
        set_attribute(self, 'minimum', None, config, self._float_or_none)
        set_attribute(self, 'maximum', None, config, self._float_or_none)
        # Only check boundries on every set if the boundries 
        # are set, otherwise do not hide super's set.
        if self.minimum != None or self.maximum != None:
            self._set = self._set_with_boundry_check 
            #if not readonly then self.set will be set in superclass during start
    def configuration(self):
        config = _Register.configuration(self)
        get_attribute(self, 'minimum', config, str)
        get_attribute(self, 'maximum', config, str)
        return config
    def _float_or_none(self, value):
        if (value is None) or (value == 'None'): return None
        return float(value)
    def _set_with_boundry_check(self,value,asyncOK=1):
        if self.read_only:
            raise EPermission('read only: ', self.name)
        if self.minimum != None and value < self.minimum:
            raise EInvalidValue('value', value, 'Value cannot be below %s' % 
                                self.minimum)
        if self.maximum != None and value > self.maximum:
            raise EInvalidValue('value', value, 'Value cannot be above %s' % 
                                self.maximum)
        return _Register._set(self, value, asyncOK)
    def base_register(self):
        return 40001
    def read_function_code(self):
        return 3
##
# Holds a group of generic points under one composite parent
# reflects any messages from its children to its parent
class RegisterGroup(CompositeNode):
    def configure(self, config):
        CompositeNode.configure(self, config) #skip our parents configure to delay building the register map
        set_attribute(self, 'group_base_register', 0, config, int)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'group_base_register', config, str)
        return config
    def add_register_to_map_for(self, register, node):
        self.parent.add_register_to_map_for(register, node)
    def get_group_base_register(self):
        return self.group_base_register
    def is_proxy(self):
        return self.parent.is_proxy()

def _compare_points(one, other):
    if isinstance(one, _GenericPoint):
        if isinstance(other, _GenericPoint):
            return cmp(one.register, other.register)
    raise EInvalidValue('modbus generic points compared to wrong class type', one.__class__, other.__class__)


        

        
   