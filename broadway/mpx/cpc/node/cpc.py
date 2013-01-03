"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
# cpc.py: Defines classes for top-level node for CPC protocol. One instance of
# this node is created under each /interfaces/comX node to which a CPC "COM C"
# type network is attached.

import time, types
from mpx.lib.node import ConfigurableNode, CompositeNode, as_internal_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.threading import Lock, Event
from mpx.ion.host.port import Port
from mpx.lib.configure import REQUIRED, get_attribute, set_attribute
from mpx.cpc.lib.line_handler import LineHandler, AutoDiscDoneEvent
from mpx.cpc.lib import tables
from mpx.lib import msglog, event

##
# @fixme default_discover_mode should probably be 'new' for production code:
default_discover_mode = 'always'
default_discover_interval = 60

class BaseCpcNode(CompositeNode, AutoDiscoveredNode):
   def __init__(self):
      AutoDiscoveredNode.__init__(self)
      self._lock = Lock()
      return
   def configure(self, cd):
      CompositeNode.configure(self, cd)
      set_attribute(self, 'discover', default_discover_mode, cd, str)
      set_attribute(self, 'discover_interval', default_discover_interval, cd, int)
      set_attribute(self, 'discovered', 0, cd, int)
   def configuration(self):
      cd = CompositeNode.configuration(self)
      get_attribute(self, 'discover', cd, str)
      get_attribute(self, 'discover_interval', cd, str)
      get_attribute(self, 'discovered', cd, str)
      return cd

class CpcNode(BaseCpcNode,event.EventConsumerMixin,event.EventProducerMixin):
   _state_table = {0:'Stopped',1:'Able to send',2:'Preempted by CPC modem'}
   def __init__(self):
      BaseCpcNode.__init__(self)
      event.EventConsumerMixin.__init__(self,self._event_handler)
      event.EventProducerMixin.__init__(self)
      self._line_handler = None
      self.running = 0
      self._children_have_been_discovered = 0
      self._autodisc_done_evt = Event()
      return
   def start(self):
      if self.running == 0:
         assert isinstance(self.parent, Port), 'Parent of CpcNode must be Port, not %s' \
            % self.parent.__class__.__name__
         self._line_handler = LineHandler(self.parent)
         self._line_handler.event_subscribe(self,AutoDiscDoneEvent)
         self._autodisc_done_evt.clear()
         self._line_handler.start()
         self.running = 1
         BaseCpcNode.start(self)
      return
   def stop(self):
      if self.running != 0:
         BaseCpcNode.stop(self)
         self.running = 0
         self._line_handler.stop()
         del self._line_handler
         self._line_handler = None
      return
   def get_state(self):
      if self._line_handler:
         return self._line_handler.get_state()
      return None
   def get(self, skipCache=0):
      state = self.get_state()
      return self._state_table[state]
   def _discover_children(self):
      if (self.running != 0) and (self._children_have_been_discovered == 0):
         autodisc_period = self._line_handler.get_autodiscover_period()
         self._autodisc_done_evt.wait()
         # If we timed out or the LineHandler never found any devices, then abort:
         if (not self._autodisc_done_evt.isSet()) \
            or (self._line_handler.get_state() == 0):
            self.event_generate(event.Event(source=self))
            msglog.log('mpx',msglog.types.ERR,'CPC_UHP: LineHandler autodisc failed.' \
                      ' Aborting child autodisc.')
            # Don't come back this way until node has been stopped and restarted:
            self._children_have_been_discovered = 1
            return self._nascent_children # should be empty
         devs = self._line_handler.get_devs()
         for dev_id,dev_inst_data in devs.items():
            dev = dev_inst_data.dev
            dev_child = DeviceNode(dev)
            dev_node_name = dev.get_name()
            if dev_node_name is None:
               msglog.log('mpx',msglog.types.ERR,'Failed to get name from device %s' \
                  % id(dev))
               continue
            self._nascent_children[dev_node_name] = dev_child
         self._children_have_been_discovered = 1
      return self._nascent_children
   def get_alarms(self):
      if self._line_handler is None:
         return []
      return self._line_handler.get_alarms()
   def _event_handler(self, event):
      if not isinstance(event, AutoDiscDoneEvent):
         return
      self._autodisc_done_evt.set()
      return
   
class DeviceNode(BaseCpcNode):
   def __init__(self, dev):
      BaseCpcNode.__init__(self)
      self._dev = dev # ref to lib-side object created by LineHandler's autodiscover()
      self._line_handler = dev._line_handler
      self.running = 0
      self._children_have_been_discovered = 0
   def start(self):
      self.running = 1
      return
   def stop(self):
      self.running = 0
      return
   def get(self, skipCache=0):
      return self._dev.as_list()
   def _discover_children(self):
      if (self.running != 0) and (self._children_have_been_discovered == 0):
         self._lock.acquire()
         try:
            item_type_names = self._dev.get_item_type_names()
            for item_type_name in item_type_names:
               item_type_child = ItemTypeNode(item_type_name, self._dev)
               self._nascent_children[item_type_name] = item_type_child
            self._children_have_been_discovered = 1
         finally:
            self._lock.release()
      return self._nascent_children
   
class ItemTypeNode(BaseCpcNode):
   def __init__(self, item_type_name, dev):
      BaseCpcNode.__init__(self)
      self._dev = dev
      self._children_have_been_discovered = 0
   def start(self):
      self.running = 1
      return
   def stop(self):
      self.running = 0
      return
   def get(self):
      item_children_names = []
      if hasattr(self, '_children'):
         for child_name in self._children.keys():
            item_children_names.append(child_name)
      return item_children_names
   def _discover_children(self):
      if (self.running != 0) and (self._children_have_been_discovered == 0):
         self._lock.acquire()
         try:
            item_inst_nums = self._dev.get_item_inst_nums(self.name)
            # If this ItemType has a Name Object, get its Value for use "in" 
            # (but not "as") node name. (Need to preserve node name uniqueness):
            if self._dev.item_types[self.name].obj_types.has_key('Name'):
               while len(item_inst_nums) > 0:
                  reqs = []
                  for i in range(4):
                     item_inst_num = item_inst_nums.pop(0)
                     req = [self.name,item_inst_num,'Name',0,'Value',0,0,0,None]
                     reqs.append(req)
                     if len(item_inst_nums) == 0:
                        break
                  results = self._dev.get_values(reqs)
                  if isinstance(results, Exception):
                     msglog.exception() # @fixme Retry? More msg detail?
                     continue # ???
                  elif (type(results) == types.StringType) \
                       or (results is None):
                     msglog.log('mpx',msglog.types.ERR,'Failed to get Name Object Value: %s' \
                                % results)
                     continue
                  for i in range(4):
                     result = results.pop(0)
                     item_inst_num = reqs[i][1]
                     item_inst_name = '%s_%03u' % (self.name, item_inst_num)
                     if result[0] != 0:
                        msglog.log('mpx',msglog.types.ERR, \
                                   'Failed to get Name Object Value for %s Item %s. '\
                                   'Return code = %s' % (str(self.name), str(item_inst_num), str(result[0])))
                     else:
                        item_inst_name = result[1] + ' (' + item_inst_name + ')'
                     item_child = ItemNode(item_inst_num, self.name, self._dev)
                     self._nascent_children[item_inst_name] = item_child
                     if len(results) == 0:
                        break
            else:
               for item_inst_num in item_inst_nums:
                  item_inst_name = '%s_%03u' % (self.name, item_inst_num)
                  item_child = ItemNode(item_inst_num, self.name, self._dev)
                  self._nascent_children[item_inst_name] = item_child
            self._children_have_been_discovered = 1
         finally:
            self._lock.release()
      return self._nascent_children
   
class ItemNode(BaseCpcNode):
   def __init__(self, item_inst_num, item_type_name, dev):
      BaseCpcNode.__init__(self)
      self._item_type_name = item_type_name
      self._item_inst_num = item_inst_num
      self._dev = dev
      self._req_templ = [self._item_type_name, self._item_inst_num, \
                  0, 0, 0, 0, 0, 0, None]
      self._children_have_been_discovered = 0
   def start(self):
      self.running = 1
      return
   def stop(self):
      self.running = 0
      return
   ##
   # get():
   # @return string: status of Item (if Status Object is supported)
   # @fixme Interpret LIST_ITEM return value, to allow return of a string, rather than a tuple.
   def get(self, skipCache=0):
      result = None
      if self._dev.item_types[self._item_type_name].obj_types.has_key('Status'):
         reqs = [self._req_templ[:]]
         reqs[0][2] = 'Status'
         item_resp_list = self._dev._line_handler.get_values(self._dev._id,reqs)
         if isinstance(item_resp_list, Exception):
            msglog.log('mpx',msglog.types.ERR,'Failed to get response to request for Status for %s Item %u' \
                        % (self._item_type_name, self._item_inst_num))
            result = item_resp_list
         elif item_resp_list[0][0] != 0:
            msglog.log('mpx',msglog.types.ERR,'Recvd error response (%s) to request for Status for %s Item %u' \
                        % (item_resp_list[0][0], self._item_type_name, self._item_inst_num))
            result = 'Response Error %s' % item_resp_list[0][0]
         else:
            result = item_resp_list[0][1]
      if type(result) == types.TupleType:
         result = list(result)
      return result
   def _discover_children(self):
      if (self.running != 0) and (self._children_have_been_discovered == 0):
         self._lock.acquire()
         try:
            obj_types = self._dev.item_types[self._item_type_name].obj_types
            for obj_data in obj_types.values():
               if obj_data.default != 0:
                  obj_type_name = str(obj_data)
                  obj_type_id = int(obj_data)
                  obj_child = ObjectNode(obj_type_id, obj_type_name, 0, self._dev)
                  first_obj_name = obj_type_name
                  if obj_data.max_num_instances > 1:
                     first_obj_name += '0'
                  self._nascent_children[first_obj_name] = obj_child
                  for i in range(1, obj_data.max_num_instances):
                     obj_child = ObjectNode(obj_type_id, obj_type_name, i, self._dev)
                     self._nascent_children[obj_type_name + str(i)] = obj_child
            self._children_have_been_discovered = 1
         finally:
            self._lock.release()
      return self._nascent_children

class ObjectNode(BaseCpcNode):
   def __init__(self, obj_type_id, obj_type_name, obj_inst_num, dev):
      BaseCpcNode.__init__(self)
      self._obj_type_id = obj_type_id
      self._obj_type_name = obj_type_name
      self._obj_inst_num = obj_inst_num
      self._dev = dev
      self._req_templ = None
      self._children_have_been_discovered = 0
      self.prop_types = None
   def start(self):
      self._req_templ = [self.parent._item_type_name, self.parent._item_inst_num, \
                  self._obj_type_id, self._obj_inst_num, 0, 0, 0, 0, None]
      self.running = 1
      self.prop_types = self._dev.item_types[self.parent._item_type_name].obj_types[self._obj_type_id].prop_types
      return
   def stop(self):
      self.running = 0
      return
   def get(self, skipCache=0):
      if 0 in self.prop_types: # 0: PropertyType 'Value'
         req = self._req_templ[:]
         resp_list = self._dev.get_values([req])
         result = None
         if isinstance(resp_list, Exception):
            msglog.log('mpx',msglog.types.ERR,'Failed to get Value Property of %s Object.' \
                       % self._obj_type_name)
            result = resp_list[0][0]
         elif resp_list[0][0] != 0:
            msglog.log('mpx',msglog.types.ERR,'Recvd error response (%u) to request for Value for %s Object %u' \
                        % (resp_list[0][0], self._obj_type_name, self._obj_inst_num))
            result = 'Response Error %u' % resp_list[0][0]
         else:
            result = resp_list[0][1]
         if type(result) == types.TupleType:
            result = list(result)
      return result
   def _discover_children(self):
      if (self.running != 0) and (self._children_have_been_discovered == 0):
         self._lock.acquire()
         try:
            for prop_type in self.prop_types:
               if not tables._props.has_key(prop_type):
                  msglog.log('mpx',msglog.types.ERR,'%u does not correspond to a ' \
                            'valid PropertyType; PropertyNode not created' \
                             % prop_type)
                  continue
               prop_type_name = str(tables._props[prop_type])
               prop_child = PropertyNode(prop_type, prop_type_name, 0, self._dev)
               self._nascent_children[prop_type_name] = prop_child
            self._children_have_been_discovered = 1
         finally:
            self._lock.release()
      return self._nascent_children
##
# @fixme Add articulation for indexed properties, with either 256 or less, or 257 or greater.
class PropertyNode(ConfigurableNode):
   def __init__(self, prop_type_id, prop_type_name, prop_inst_num, dev):
      ConfigurableNode.__init__(self)
      self._prop_type_id = prop_type_id
      self._prop_type_name = prop_type_name
      self._prop_inst_num = prop_inst_num
      self._dev = dev
      self.running = 0
   def start(self):
      self._req_templ = [self.parent.parent._item_type_name, self.parent.parent._item_inst_num, \
                  self.parent._obj_type_id, self.parent._obj_inst_num, self._prop_type_id, self._prop_inst_num, 0, 0, None]
      self.running = 1
   def stop(self):
      self.running = 0
   def get(self, skipCache=0):
      req = self._req_templ[:]
      resp_list = self._dev.get_values([req])
      result = None
      if isinstance(resp_list, Exception):
         msglog.log('mpx',msglog.types.ERR,'Failed to get value of Property %s of %s Object %u.' \
                    % (self._prop_type_name, self.parent._obj_type_name,
                       self.parent._obj_inst_num))
         result = resp_list[0][0]
      elif resp_list[0][0] != 0:
         msglog.log('mpx',msglog.types.ERR,'Recvd error response (%s) to request for ' \
                    'value of Property %s for %s Object %s' \
                     % (resp_list[0][0], self._prop_type_name, 
                        self.parent._obj_type_name, self.parent._obj_inst_num))
         result = 'Response Error %s' % str(resp_list[0][0])
      else:
         result = resp_list[0][1]
      if type(result) == types.TupleType:
         result = list(result)
      return result
 
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
