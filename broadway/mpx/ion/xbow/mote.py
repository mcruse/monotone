"""
Copyright (C) 2006 2007 2010 2011 Cisco Systems

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
# @notes    Support for dynamically discovering Crossbow wireless sensor network motes
#           and representing them as nodes within the framework

import time, struct
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.event import EventProducerMixin, ChangeOfValueEvent
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.exceptions import ETimeout
from mpx.lib.xbow.surge import XbowWsn, TcpLineHandler, SerialLineHandler
from mpx.lib.xbow.cache import XbowCache
from mpx.lib.xbow.xconvert import *

# simple helper funtions to isolate .parent.parent abuse
def _get_cache(o):
    return o.parent.cache
        
def _get_group_id(o):
    return o.parent.group_id
        
def _get_timeout(o):
    return o.parent.timeout
        
def _get_addr(o):
    return o.parent.addr
        
class _XbowConnection(CompositeNode, AutoDiscoveredNode):
    def __init__(self):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        
    def _discover_children(self):
        answer = {}
        if self.discover == 'never' or not self.running:
            return answer
        known_groups = []
        for n in self._get_children().values():
            known_groups.append(n.group_id)
        all_groups = self.cache.get_group_ids()
        for g in all_groups:
            if g not in known_groups:
                answer['group_' + str(g)] = XbowGroup(g)
        return answer
            
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'timeout', 120, config, int)
        # scan_time purposed as a "hidden attribute" not included in nodedef 
        set_attribute(self, 'scan_time', 0, config, int) 
        set_attribute(self, 'discover', 'never', config, str)
        
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'timeout', config, str)
        get_attribute(self, 'discover', config, str)
        return config
        
    def start(self):
        CompositeNode.start(self)
        self.driver.start()
        self.running = 1
        
    def stop(self):
        if self.driver:
            self.driver.stop()
        self.driver = None

class XbowTcpConnection(_XbowConnection):	
    def __init__(self):
        _XbowConnection.__init__(self)
        self.driver = None
        self.lh = None
        self.running = 0
        self.cache = None
        
    def configure(self, config):
        _XbowConnection.configure(self, config)
        set_attribute(self, 'tcp_port', 10002, config, int)
        set_attribute(self, 'host', REQUIRED, config)
        set_attribute(self, 'debug', 0, config, int)
        # create appropriate cache, linehander and driver
        self.cache = XbowCache(self.timeout, self.scan_time)
        self.lh = TcpLineHandler(self.tcp_port, self.host, self.debug)
        self.driver = XbowWsn(self.lh, self.cache)
        
    def configuration(self):
        config = _XbowConnection.configuration(self)
        get_attribute(self, 'tcp_port', config, str)
        get_attribute(self, 'host', config, str)
        get_attribute(self, 'debug', config, str)
        return config

class XbowSerialConnection(_XbowConnection):	
    def __init__(self):
        _XbowConnection.__init__(self)
        self.driver = None
        self.lh = None
        self.running = 0
        self.cache = None
        
    def configure(self, config):
        _XbowConnection.configure(self, config)
        set_attribute(self, 'debug', 0, config, int)
        # create appropriate cache, linehandler and driver
        self.cache = XbowCache(self.timeout, self.scan_time)
        self.lh = SerialLineHandler(self.parent, self.debug)
        self.driver = XbowWsn(self.lh, self.cache)
        
    def configuration(self):
        config = _XbowConnection.configuration(self)
        get_attribute(self, 'debug', config, str)
        return config
        
class XbowGroup(CompositeNode, AutoDiscoveredNode):
    def __init__(self, group_id=None):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.group_id = group_id
        self.cache = None

    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'group_id', 0, config, int)
        set_attribute(self, 'discover', 'always', config, str)
        
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'group_id', config, str)
        get_attribute(self, 'discover', config, str)
        return config
        
    def start(self):
        self.cache = _get_cache(self)
        self.timeout = _get_timeout(self)
        self.cache.add_group(self.group_id)
        CompositeNode.start(self)
        
    def _discover_children(self):
        answer = {}
        # allow a bit of granularity wrt what groups we auto-discover motes in
        if self.discover == 'never':
            return answer
        known_motes = []
        for m in self._get_children().values():
            known_motes.append(m.addr)
        all_motes = self.cache.get_mote_ids(self.group_id)
        for addr in all_motes:
            if addr not in known_motes:
                answer['mote_' + str(addr)] = MoteMTS(addr, 1)
        return answer
            
class MoteMTS(CompositeNode, AutoDiscoveredNode):
    def __init__(self, addr=None, discovered=0):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.cache = None
        self.addr = addr
        self.needs_discovery = discovered
    
    def configure(self, config):
        CompositeNode.configure(self, config)
        if not self.addr:
            set_attribute(self, 'addr', REQUIRED, config)
         
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'addr', config, str)
        return config
        
    def start(self):
        self.cache = _get_cache(self)
        self.timeout = _get_timeout(self)
        self.group_id = _get_group_id(self)
        CompositeNode.start(self)
        
    def _discover_children(self):
        answer = {}
        # if this is a nascent node - we'll be kind and create necessary children
        if self.needs_discovery:
            self.needs_discovery = 0
            for snsr_type in ("Light", "Temp", "MagX", "MagY", "AccelX", "AccelY"):
                answer[snsr_type] = MoteValueRaw(snsr_type, 1)
        return answer
        
    # the sequence number of the last message also encodes present batt. voltage,
    # which is needed for some sensor readings. 
    def get_seq_num(self):
        msg = self.cache.get_msg(self.group_id, self.addr)
        if not msg:
            raise ETimeout
        seq_num = msg.get_element('_SequenceNum')
        return seq_num
    
    # Calculates the voltage.  First the Vref value must be computed using the 
    # upper 9 bits of the _SequenceNum.  The voltage is calculated using the
    # formula:
    # (courtesy of Martin Turon & Crossbow)
    #
    #   BV = RV * ADC_FS/data
    #   where:
    #   BV == Battery Voltage
    #   ADC_FS == 1023
    #   RV == Voltage reference for the mica2 (1.223 volts)
    #   data == data from the adc measurement of channel 1

    def get_ref_voltage_from_seq(self):
        seq = self.get_seq_num()
        vref = (seq & 0xff800000L) >> 23
        if vref == 0:
            return 0
        return 1252352.0 / vref
        
class MoteCOVEventProducer(EventProducerMixin):
    def __init__(self):
        EventProducerMixin.__init__(self)
        self.old_value = None
        
    # note - self.cache, self.group_id and self.addr must be set correctly
    def event_subscribe(self, *args):
        EventProducerMixin.event_subscribe(self, *args)
        self.old_value = self.get()
        # generate initial event
        self.event_generate(ChangeOfValueEvent(self, self.old_value, self.old_value, time.time()))
        self.cache.add_callback((self.group_id, self.addr), self._trigger_cov)
        
    def event_unsubscribe(self, *args):
        EventProducerMixin.event_unsubscribe(self, *args)
        if not self.event_class_consumer_count:
            self.cache.remove_callback((self.group_id, self.addr), self._trigger_cov)
        
    def _trigger_cov(self):
        try:
            v = self.get()
        except:
            v = ETimeout
        cov = ChangeOfValueEvent(self, self.old_value, v, time.time())
        self.event_generate(cov)
        self.old_value = v
        
class MoteValueRaw(CompositeNode, AutoDiscoveredNode, MoteCOVEventProducer):
    def __init__(self, snsr_type=None, discovered=0):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        MoteCOVEventProducer.__init__(self)
        self.snsr_type = snsr_type
        self.needs_discovery = discovered
        
    def configure(self, config):
        CompositeNode.configure(self, config)
        if not self.snsr_type:
            set_attribute(self, 'snsr_type', REQUIRED, config)
        
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'snsr_type', config, str)
        return config
        
    def start(self):
        self.group_id = _get_group_id(self)
        self.addr = _get_addr(self)
        self.timeout = _get_timeout(self)
        self.cache = _get_cache(self)
        CompositeNode.start(self)
        
    def has_cov(self):
        return 1
    
    def _discover_children(self):
        answer = {}
        if self.needs_discovery:
            self.needs_discovery = 0
            # the most common sensor board we'll be discovering is the MTS series, all
            # have temp and light readings which require value translators.
            if self.name == "Light":
                answer["Lux"] = MoteValueTranslator('LightFromRaw')
            if self.name == "Temp":
                answer["F"] = MoteValueTranslator('TempFFromRaw')
                answer["C"] = MoteValueTranslator('TempCFromRaw')
        return answer
        
    def get(self, skipCache=0):
        msg = self.cache.get_msg(self.group_id, self.addr)
        if msg:
            last_read_time = msg.time_stamp
            if time.time() - last_read_time < self.timeout:
                return msg.get_element(self.snsr_type)
        raise ETimeout
        
class MoteValueTranslator(CompositeNode, MoteCOVEventProducer):
    def __init__(self, cls_name=None):
        MoteCOVEventProducer.__init__(self)
        self.cls_name = cls_name

    def configure(self, config):
        CompositeNode.configure(self, config)
        #if not discovered, class to instantiate passed via config
        if not self.cls_name:
            set_attribute(self, 'cls_name', REQUIRED, config)
            
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'cls_name', config, str)
        return config
        
    def start(self):
        # all known relevant calculators are presently imported to this name space from xconvert. 
        # NameError raised if there's issue. 
        self.group_id = _get_group_id(self)
        self.addr = _get_addr(self)
        self.timeout = _get_timeout(self)
        self.cache = _get_cache(self)
        self.ion = self.parent
        self.translator = ConversionFactory(self.cls_name, self)
        CompositeNode.start(self)
        
    def has_cov(self):
        return 1
        
    def get(self, skipCache=0):
        return self.translator.convert()
        
    
	
