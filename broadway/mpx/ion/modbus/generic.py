"""
Copyright (C) 2002 2003 2004 2007 2008 2009 2010 2011 Cisco Systems

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

import time

from mpx.lib import msglog
from mpx.lib.node import ConfigurableNode, CompositeNode, as_node
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.exceptions import *

from mpx.ion import Result
from mpx.lib.modbus import command
from mpx.lib.modbus.response import ReadHoldingRegisters, \
     ReadCoilStatus, ReadInputStatus, ReadInputRegisters
from mpx.ion.modbus.cached_ion import CachedION
from mpx.ion.modbus.register_cache import _EntryION, RegisterCache
from mpx.lib.modbus.cache_writer import CacheWriter
from mpx.ion.modbus.batch_manager import BatchManagerMixin

##
# @todo Speed up timeouts on missing devices
# @todo Have modbus parity check on start

##
# @fixme Determin if RegisterDescription should be generic.
class RegisterDescription:
    def __init__(self, offset, count, name, unbound_read,
                 unbound_write=None):
        self.offset  = offset
        self.count   = count
        self.name    = name
        self.read    = unbound_read	    # self == response.ReadHoldingRegisters
        self.write   = unbound_write    # self == CacheWriter
##
# Modules the SCD2000 as an ION.
class Device(CachedION, BatchManagerMixin):
    def __init__(self):
        CachedION.__init__(self)
        self.debug = 0
        self.use_batch_manager = 0
    ##
    # Apply a multiplier to a value before setting it and divide the value
    # when getting it.
    # @fixme Move to mpx.lib.translator.
    # @todo Add an offset?
    def configure(self, config):
        if self.debug: print 'Device Configure start '
        CompositeNode.configure(self, config) #skip our parents configure to delay building the register map
        set_attribute(self, 'address', REQUIRED, config, int)
        set_attribute(self, 'line_handler', self.parent, config, as_node)
        set_attribute(self, 'boundries', [], config)
        set_attribute(self, 'split_cache_at_gaps', 1, config, int)
        set_attribute(self, 'use_batch_manager', self.use_batch_manager, config, int)
        if self.debug: print self.boundries
        if self.boundries is None:
            self.boundries = []
        set_attribute(self, 'exclude', [], config)
        set_attribute(self, 'maximum_coils', 2000, config, int)
        set_attribute(self, 'maximum_input_status', 2000, config, int)
        set_attribute(self, 'maximum_holding_registers', 125, config, int)
        set_attribute(self, 'maximum_input_registers', 125, config, int)
        set_attribute(self, 'debug', 0, config, int)
        self._register_maps = []
        if self.debug: print 'Device Configured ', self.name
    def configuration(self):
        config = CachedION.configuration(self)
        get_attribute(self, 'address', config, str)
        get_attribute(self, 'line_handler', config, str)
        get_attribute(self, 'boundries', config, str)
        get_attribute(self, 'exclude', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'split_cache_at_gaps', config, str)
        get_attribute(self, 'use_batch_manager', config, str)
        get_attribute(self, 'maximum_coils', config, str)
        get_attribute(self, 'maximum_input_status', config, str)
        get_attribute(self, 'maximum_holding_registers', config, str)
        get_attribute(self, 'maximum_input_registers', config, str)
        get_attribute(self, 'maps', config, str)
        return config
        
    def start(self):
        if self.debug: print 'start generic device: ', self.name
        self.maps = {}
        # insert the default boundries due to point type ranges
        self.maps[1]     = ([], 1.0)
        self.maps[10001] = ([], 1.0)
        self.maps[30001] = ([], 1.0)
        self.maps[40001] = ([], 1.0)
        if self.debug: print self.maps 
        for b in self.boundries:
            if self.debug: print b
            self.maps[int(b['register'])] = ([], float(b['ttl'])) #overwrite any default 1 sec TTL if desired
        if self.debug: print self.maps
        #todo:
        # deal with excludes
        CachedION.start(self) #let the children play (and ask find_cache_for)
        self.split_long_caches()
        if self.debug: print self.maps
        self._register_maps = self.maps.values()
        self._define_caches(self.holding_register_maps())
        #del self.maps
        if self.debug: print 'started generic device: ', self.name

    def find_cache_for(self, point):
        #determine which cache this point belongs too
        keys = self.maps.keys()
        keys.sort()
        keys.reverse()
        for k in keys:
            if (point.offset + point.base_register()) >= k: #found first usable cache
                self.maps[k][0].append(point)
                return
        raise EInvalidValue('unable to find cache for: ', (point.name, point.offset, keys))

    def split_long_caches(self):
        keys = self.maps.keys() #keys are register numbers
        keys.sort()
        new_maps = {}
        for k in keys:
            c = self.maps[k] #tuple with point list and TTL value
            if len(c[0]) > 0: #at least one point in this cache
                ttl = c[1]
                ps = c[0] #list of registers - points
                ps.sort(_compare_points)
                new_key = None
                new_list = []
                prev_p = None
                for p in ps: #iterage through points and look for reasons to break up the cache
                    pp = p
                    if self.split_cache_at_gaps and prev_p is not None: #check for a gap between the last register and this one
                        max_gap = 2 #number of registers of gap allowed before breaking cache
                        if p.base_register() < 30001: #must be coil or status - 8 registers per byte, allow gaps that are still within a word
                            max_gap = 15
                        if prev_p.offset + prev_p.length + max_gap < p.offset: #GAP!! Split the cache at the gap
                            new_maps[new_key] = (new_list, ttl) #enter new cache entry into maps
                            new_key = None
                            new_list = []
                            pp = None
                    if new_key is None: new_key = p.offset + p.base_register() #this would be the beginning register of a new cache
                    if (p.offset + p.base_register() + p.length) > (new_key + p.max_register_count()): #this point is too far from the begining
                        new_maps[new_key] = (new_list, ttl) #enter new cache entry into maps
                        new_key = None
                        new_list = []
                        pp = None
                    new_list.append(p)
                    prev_p = pp #last point or None if a new cache was started
                new_maps[new_key] = (new_list, ttl)
        self.maps = new_maps    
                    
    ##
    # @return A list of register map, timeout tuples used to create the caches
    #         used by the SCD2000.
    def register_maps(self):
        return self._register_maps

    def _define_caches(self, register_maps):
        for map, ttl in register_maps:
            cache = RegisterCache(self, self.address, CacheWriter, ttl, None, self.parent.ip)
            for d in map:
                cache.map_register_entry(d)
                d.cache = cache
            self.caches.append(cache)
    def get(self,skipCache=0):
        return self.get_result(skipCache).value
    def get_result(self,skipCache=0):
        result = Result()
        result.value = len(self.children_nodes())
        result.timestamp = time.time()
        return result
    def get_group_base_register(self):
        return 0
    def get_batch_manager(self):
        if self.use_batch_manager:
            return self
        return None
    def get_device(self):
        return self
class TcpDevice(Device):
    def _define_caches(self, register_maps):
        for map, ttl in register_maps:
            cache = RegisterCache(self, 255, CacheWriter, ttl, None, self.address)
            for d in map:
                cache.map_register_entry(d)
                d.cache = cache
            self.caches.append(cache)

from mpx.ion.modbus.register_cache import _EntryION

class _GenericPoint(_EntryION):
    def __init__(self):
        CompositeNode.__init__(self) #note: not _EntryION
        self.orders = 0
        self.debug = 0
        self.read_command_class = command.ReadHoldingRegisters
    def configure(self, config):
        if self.debug: print 'Configure modbus point'
        CompositeNode.configure(self, config)
        self.__batch_manager = self.parent.get_batch_manager()
        set_attribute(self, 'register', REQUIRED, config, int)
        set_attribute(self, 'offset', self.register, config, int)
        set_attribute(self, 'read_only', 1, config, int)
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'length', 1, config, int)
        self.debug = 0
        self.absolute_offset = self.register
        if self.debug: print 'Configured modbus point', self
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'register', config, str)
        get_attribute(self, 'read_only', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'offset', config, str)
        return config
    def start(self):
        if self.debug: print 'Start: ', self.name
        try:
            self.cache = None #gets set in _define_caches
            group = self.parent.get_group_base_register()
            if group is None:
                group = 0
            self.offset = self.register + group - self.base_register()
            self.absolute_offset = self.offset + self.base_register()
            if self.offset < 0:
                raise EInvalidValue('offset out of range for: ', self.name)
            self.read = self.type_read_method()
            self.write = self.type_write_method()
            self.parent.find_cache_for(self)
            if self.read_only == 0:
                self.set = self._set
        except:
            msglog.exception()
        if self.debug: print 'Started ', self.name
        _EntryION.start(self)
    def _set(self, value, asyncOK=1):
        if self.debug: print 'set modbus client point'
        if self.read_only:
            raise EPermission('read only: ', self.name)
        if value == 'None':
            self.value = None
            return
        _EntryION._set(self, value, asyncOK)
    def type_write_method(self):
        return None
    def max_register_count(self):
        return 125
    def set_batch_manager(self, bm):
        self.__batch_manager = bm
    def get_batch_manager(self):
        return self.__batch_manager
    def get_device(self):
        return self.parent.get_device()
    def __repr__(self):
        return '%d:%d' % (self.register, self.length)
class Coil(_GenericPoint):
    def __init__(self):
        _GenericPoint.__init__(self)
        self.read_command_class = command.ReadCoilStatus
    def type_read_method(self):
        return ReadCoilStatus.status
    def base_register(self):
        return 1
    def max_register_count(self):
        return self.get_device().maximum_coils
    def type_write_method(self):
        return CacheWriter.write_coil
class InputStatus(_GenericPoint):
    def __init__(self):
        _GenericPoint.__init__(self)
        self.read_command_class = command.ReadInputStatus
    def type_read_method(self):
        return ReadInputStatus.status
    def base_register(self):
        return 10001
    def max_register_count(self):
        return self.get_device().maximum_input_status

_register_as = {'int'   :{1:(ReadHoldingRegisters.register_as_int, CacheWriter.write_int),
                          2:(ReadHoldingRegisters.register_as_long, CacheWriter.write_long)},
               'IEEE float':{2:(ReadHoldingRegisters.register_as_float, CacheWriter.write_float),
                             4:(ReadHoldingRegisters.register_as_float8, CacheWriter.write_double)},
               'hibyte' :{1:(ReadHoldingRegisters.register_hibyte, CacheWriter.write_hibyte)},
               'lobyte' :{1:(ReadHoldingRegisters.register_lobyte, CacheWriter.write_lobyte)},
               'loint'  :{1:(ReadHoldingRegisters.register_as_loint, CacheWriter.write_loint)},
               'hiint'  :{1:(ReadHoldingRegisters.register_as_hiint, CacheWriter.write_hiint)},
               'lochar' :{1:(ReadHoldingRegisters.register_as_lochar, CacheWriter.write_lobyte)},
               'hichar' :{1:(ReadHoldingRegisters.register_as_hichar, CacheWriter.write_hibyte)},
               'word'   :{1:(ReadHoldingRegisters.register_as_word, CacheWriter.write_word),
                          2:(ReadHoldingRegisters.register_as_dword, CacheWriter.write_dword)},
               'dword'  :{2:(ReadHoldingRegisters.register_as_dword, CacheWriter.write_dword)},
               'string' :{0:(ReadHoldingRegisters.register_as_string, CacheWriter.write_string)},
               'zstring':{0:(ReadHoldingRegisters.register_as_zstring, CacheWriter.write_string)},
               'modulo' :{1:(ReadHoldingRegisters.register_as_modulo_10000_1, CacheWriter.write_modulo_1),
                          2:(ReadHoldingRegisters.register_as_modulo_10000_2, CacheWriter.write_modulo_2),
                          3:(ReadHoldingRegisters.register_as_modulo_10000_3, CacheWriter.write_modulo_3),
                          4:(ReadHoldingRegisters.register_as_modulo_10000_4, CacheWriter.write_modulo_4)},
               'PowerLogic Energy':{3:(ReadHoldingRegisters.register_as_power_logic_3, CacheWriter.write_power_logic_3),
                                    4:(ReadHoldingRegisters.register_as_power_logic_4, CacheWriter.write_power_logic_4)},
               'DL06 Energy':{4:(ReadHoldingRegisters.register_as_dl06_energy_4, CacheWriter.write_dl06_energy_4)},
               'time'   :{3:(ReadHoldingRegisters.register_as_time_3, CacheWriter.write_time_3),
                          6:(ReadHoldingRegisters.register_as_time_6, CacheWriter.write_time_6)},
                'Encorp Real':{2:
                               (ReadHoldingRegisters.register_as_encorp_real_2,
                                CacheWriter.write_encorp_real_2)}
                }

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
        _GenericPoint.start(self)
    ##
    # @todo  Should probably move this conversion function into configure
    #        so that the InvalidValue exception is thrown at configure time.
    def type_read_method(self):
        t = _register_as.get(self.type, None)
        if t is None: raise EInvalidValue('type',self.type,
                                          'Invalid type for %s.' % self.name)
        answer = t.get(self.length, None)
        if answer is None: 
            answer = t.get(0, None)
            if answer is None:
                raise EInvalidValue('wrong length for type', self.name + '  ' + \
                                               self.type + '  '+ str(self.length))
            #need a little extra help. This must be one of the two string types.  Length info must be passed in
            self.__read_register = answer[0]
            return self.__read_string_register
        if self.debug:
           print str(answer)
           print str(self)
        return answer[0]
    def __read_string_register(self, response, offset, start=0, orders=0):
        #need local register length
        return self.__read_register(response, offset, self.length * 2, start, orders)
        

class InputRegister(_Register):
    def __init__(self):
        _GenericPoint.__init__(self)
        self.read_command_class = command.ReadInputRegisters
    def base_register(self):
        return 30001
    def max_register_count(self):
        return self.get_device().maximum_input_registers
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
        return _EntryION._set(self, value, asyncOK)
    def base_register(self):
        return 40001
    def type_write_method(self):
        t = _register_as.get(self.type, None)
        if t is None: raise EInvalidValue('type',self.type,
                                          'Invalid type for %s.' % self.name)
        answer = t.get(self.length, None)
        if answer is None: 
            answer = t.get(0, None)
            if answer is None:
                raise EInvalidValue('wrong length for type', self.name)
            self.__write_register = answer[1]
            return self.__write_string_register
        return answer[1]
    def __write_string_register(self, command, reg, value, orders):
        v = value + ('\x00\x00' * self.length) #pad with zeros
        v = v[:self.length*2]
        self.__write_register(command, reg, v, orders)
    def max_register_count(self):
        return self.get_device().maximum_holding_registers
##
# Holds a group of generic points under one composite parent
# reflects any messages from its children to its parent
class RegisterGroup(CompositeNode):
    def configure(self, config):
        CompositeNode.configure(self, config) #skip our parents configure to delay building the register map
        set_attribute(self, 'group_base_register', 0, config, int)
        set_attribute(self, 'separate_cache', 0, config, int)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'group_base_register', config, str)
        get_attribute(self, 'separate_cache', config, str)
        return config
    def find_cache_for(self, point):
        self.parent.find_cache_for(point)
    def get_group_base_register(self):
        return self.group_base_register + self.parent.get_group_base_register()
    def start(self):
        self.maps = self.parent.maps #children may reference maps
        if self.separate_cache:
            if self.group_base_register:
                if not self.maps.has_key(self.group_base_register):
                    self.maps[self.group_base_register] = ([], 1.0)
        CompositeNode.start(self)
    def get_batch_manager(self):
        return self.parent.get_batch_manager()
    def get_device(self):
        return self.parent.get_device()
def _compare_points(one, other):
    if isinstance(one, _GenericPoint):
        if isinstance(other, _GenericPoint):
            return cmp(one.absolute_offset, other.absolute_offset)
    raise EInvalidValue('modbus generic points compared to wrong class type', one.__class__, other.__class__)
    
   
