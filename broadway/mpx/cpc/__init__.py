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
import types, time, array
from mpx.lib import msglog
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.node import as_node, as_node_url, CompositeNode, ConfigurableNode
from mpx.lib.configure import REQUIRED, get_attribute, set_attribute
from mpx.lib.threading import Thread
from mpx.cpc.node.cpc import CpcNode
from mpx.cpc.lib import tables, utils
from mpx.service.hal import alarms
from mpx.service.hal.alarms import cpc_client
from mpx.service.hal.alarms import ewebconnect

class VistaCpcServiceNode(CompositeNode):
   def __init__(self):
      CompositeNode.__init__(self)
      self._cpc_uhp_node = None
      self._cases = []
      self._racks = []
      self.running = 0
      self._start_thread_inst = None
      self._ready = 0
      self.debug_lvl = 1
      return
   def configure(self, cd):
      set_attribute(self, 'com_port', 'com1', cd, str)
      cd['name'] = 'vista_cpc_%s' % self.com_port
      CompositeNode.configure(self, cd)
      return
   def configuration(self):
      cd = CompositeNode.configuration(self)
      get_attribute(self, 'com_port', cd, str)
      return cd
   def start(self):
      self._start_thread_inst = Thread(name='Vista CPC Startup',target=self._start_thread)
      self._start_thread_inst.start()
      self.running = 1
      return
   def stop(self):
      self.running = 0
      return
   def _start_thread(self):
      # Create a CPC_UHP node under proper COM port:
      com_port_node = as_node('/interfaces/' + self.com_port)
      self._cpc_uhp_node = CpcNode()
      cd = {'parent':com_port_node,'name':'CPC_UHP'}
      self._cpc_uhp_node.configure(cd)
      self._cpc_uhp_node.start()
      # Create Circuits and Racks children:
      ckts_svc_node = CompositeNode()
      cd = {'parent':self,'name':'Circuits'}
      ckts_svc_node.configure(cd)
      racks_svc_node = CompositeNode()
      cd = {'parent':self,'name':'Racks'}
      racks_svc_node.configure(cd)
      # Force complete autodiscovery to create CPC node subtree:
      start_time = time.time()
      dev_nodes = self._cpc_uhp_node.children_nodes()
      for dev_node in dev_nodes:
         item_type_nodes = dev_node.children_nodes()
         for item_type_node in item_type_nodes:
            item_nodes = item_type_node.children_nodes()
            for item_node in item_nodes:
               obj_nodes = item_node.children_nodes()
               for obj_node in obj_nodes:
                  prop_nodes = obj_node.children_nodes()
      self.debug_print('%s: Finished autodiscover of CPC_UHP nodetree' % time.time(), 1)
      # Scan CPC_UHP subnodetree for nodes needed for Vista handler clients:
      self._setup()
      self.debug_print('%s: Finished _setup()' % time.time(),1)
      ckts_svc_node.start() # starts all children as well
      racks_svc_node.start() # starts all children as well
      self.debug_print('%s: Finished starting Circuits and Racks children of vista_cpc node' % time.time(),1)
      ##
      # Create a CpcClient at proper place in nodetree:
      self._setup_alarm_nodes()
      self.debug_print('%s: Finished creating Alarm CpcClient' % time.time(),1)
      self._start_thread_inst = None
      self._ready = 1
      return
   ##
   # is_ready(): Called by any entity interested in calling get_XXX() methods,
   # and getting non-error values.
   # @return 1: CPC node tree is ready, 0: CPC node tree is not yet ready
   def is_ready(self):
      return self._ready
   def get_case_temps(self):
      return self._cases
   ##
   # get_cases(): Called by Vista handlers to get CaseTemp data. Handlers
   # display this data to user to allow user to associate CaseTemps with widgets.
   # @return List of lists: [[<ckt_name>,<case_temp_idx>,<temp_url>,<stat_url>,<desc_url>],...]
   def get_cases(self):
      return self._cases
   ##
   # get_racks(): Called by Vista handlers to get Rack data. Handlers
   # display this data to user to allow user to associate Racks with widgets.
   # @return List of lists: [[<rack_name>,<stat_url>],...]
   def get_racks(self):
      return self._racks
   ##
   # _setup(): Called by self._start_thread(), to scan existing CPC_UHP subtrees,
   # and to use the garnered info to create appropriate child nodes. These
   # children aggregate Rack and Case statuses for easy monitoring by Vista.
   def _setup(self):
      ckts_svc_node = self.get_child('Circuits')
      racks_svc_node = self.get_child('Racks')
      dev_nodes = self._cpc_uhp_node.children_nodes()
      has_CircuitStatus_node = 0
      for dev_node in dev_nodes:
         ckt_svc_nodes = []
         if dev_node.has_child('Circuit'):
            ckts_dev_node = dev_node.get_child('Circuit')
            ckt_dev_nodes = ckts_dev_node.children_nodes()
            for ckt_dev_node in ckt_dev_nodes:
               ckt_name = ckt_dev_node.get_child('Name').get()
               ckt_svc_node = CktStatusXltrNode(ckt_dev_node)
               cd = {'parent':ckts_svc_node,'name':ckt_dev_node.name}
               ckt_svc_node.configure(cd)
               ckt_svc_nodes.append(ckt_svc_node)
               num_temps_node = ckt_dev_node.get_child('NumberOfTempSensors')
               num_temps = num_temps_node.get()
               if (num_temps is None) or isinstance(num_temps,Exception):
                  num_temps = 6
               for i in range(num_temps):
                  case_temp_dev_node = ckt_dev_node.get_child('CaseTemps' + str(i))
                  case_temp_svc_node = CompositeNode()
                  cd = {'parent':ckt_svc_node,'name':str(case_temp_dev_node._obj_inst_num)}
                  case_temp_svc_node.configure(cd)
                  status_svc_node = CktCaseTempsStatusXltrNode(ckt_svc_node,case_temp_dev_node)
                  cd = {'parent':case_temp_svc_node,'name':'Status'} 
                  status_svc_node.configure(cd)
                  descr_svc_node = SingleAttrNode('Not initialized')
                  cd = {'parent':case_temp_svc_node,'name':'Description'} 
                  descr_svc_node.configure(cd)
                  self._cases.append([ckt_name, \
                                           case_temp_dev_node._obj_inst_num, \
                                           as_node_url(case_temp_dev_node), \
                                           as_node_url(status_svc_node),
                                           as_node_url(descr_svc_node)],)
         rack_svc_node = CompositeNode()
         cd = {'parent':racks_svc_node,'name':dev_node.name}
         rack_svc_node.configure(cd)
         rack_status_node = RackStatusXltrNode(dev_node,ckt_svc_nodes)
         cd = {'parent':rack_svc_node,'name':'Status'} 
         rack_status_node.configure(cd)
         dev_name = dev_node._dev.get_name()
         self._racks.append([dev_name, as_node_url(rack_status_node)])
      return
   def _setup_alarm_nodes(self):
      services = as_node('/services')
      if not services.has_child('External Alarms'):
         alarms_node = CompositeNode()
         alarms_node.configure({'name':'External Alarms','parent':services})
      alarms_node = as_node('/services/External Alarms')
      alarm_node = alarms.Manager()
      alarm_node.configure({'name':'CPC Alarm','parent':alarms_node})
      cpc_client_node = cpc_client.CpcClient(self._cpc_uhp_node)
      cpc_client_node.configure({'name':'CPC Client',
                              'parent':alarm_node,'node':''})
      ewebconnect_client_node = ewebconnect.EWebConnectAlarmClient()
      ewebconnect_client_node.configure({
         'name':'eWebConnect Alarm Client',
         'parent':alarm_node,
         'host':'10.0.1.88', #'mother.envenergy.com',
         'port':16161,
         'enabled':1,
         })
      alarms_node.start()
      return
   def debug_print(self, msg, msg_lvl):
      if msg_lvl < self.debug_lvl:
         if isinstance(msg, array.ArrayType):
            utils.print_array_as_hex(msg, 16)
         else:
            print 'opt.trane.vista.cpc.VistaCpcServiceNode: ' + msg
      return
##
#
class SingleAttrNode(ConfigurableNode):
   def __init__(self, value):
      ConfigurableNode.__init__(self)
      self.value = value
      return
   def get(self, skipCache=0):
      return self.value
   def set(self,value):
      self.value = value
      return
##
# proc_StatusProp():
# @param value single byte
# @return 1: bit0 and/or bit1 are set in the given byte, 0: neither is set
def proc_StatusProp(value):
   if (value & 0x03) != 0:
      return 1
   return 0
##
# proc_ListItemValueProp():
# @param value 2-list
# @return Entry number of LIST_ITEM (ie 1st list elem)
def proc_ListItemValueProp(value):
   assert len(value) == 2, 'Bad value passed into proc_ListItemValueProp(): %s' \
          % str(value)
   return value[0]
##
# proc_AlarmStateValueProp():
# @param value 2-list
# @return 0: Normal, 1: Not Normal
def proc_AlarmStateValueProp(value):
   assert len(value) == 2, 'Bad value passed into proc_AlarmStateValueProp(): %s' \
          % str(value)
   if value[0] == 1:
      return 0
   return 1
##
# proc_DigOutStatusValueProp():
# @param value 2-list
# @return 0: Normal, 1: Not Normal
def proc_DigOutStatusValueProp(value):
   assert len(value) == 2, 'Bad value passed into proc_DigOutStatusValueProp(): %s' \
          % str(value)
   if value[0] == 0:
      return 0
   return 1
##
# class CktStatusXltrNode:
class CktStatusXltrNode(CompositeNode):
   _alm_status_components = { \
                             'Refrigeration':['Status',proc_StatusProp], \
                             'Defrost':['Status',proc_StatusProp], \
                             'Termination':['Status',proc_StatusProp], \
                             'CleaningState':['Status',proc_StatusProp], \
                             #'DemandDefrostState':['Status',proc_StatusProp], # apparently not supported by CPC anymore \
                             'Humidity':['Status',proc_StatusProp], \
                             'LLS':['Status',proc_StatusProp], \
                             }
   _defr_status_components = {'Status':['Value',proc_ListItemValueProp]}
   def __init__(self, ckt_dev_node):
      CompositeNode.__init__(self)
      self._alm_status_nodes = []
      self._defr_status_nodes = []
      self.running = 0
      self._ckt_dev_node = ckt_dev_node
      self._alarms = []
      self._alm_reqs = []
      self._defr_reqs = []
      return
   def start(self):
      self._alm_reqs = []
      self._connect_to_status_nodes(self._alm_status_components, self._alm_status_nodes, self._alm_reqs)
      self._defr_reqs = []
      self._connect_to_status_nodes(self._defr_status_components, self._defr_status_nodes, self._defr_reqs)
      self.running = 1
      return
   def _connect_to_status_nodes(self, status_components, status_nodes, reqs):
      item_type_name = 'Circuit'
      dev = self._ckt_dev_node._dev
      for obj_type_name, prop_info in status_components.items():
         obj_types = dev.item_types[item_type_name].obj_types
         max_num_obj_insts = obj_types[obj_type_name].max_num_instances
         num_obj_insts = max_num_obj_insts
         if max_num_obj_insts > 1:
            num_insts_obj_type_name = obj_types[obj_type_name].num_insts_obj_type_name
            if not num_insts_obj_type_name is None:
               reqs = [[item_type_name,self._ckt_dev_node._item_inst_num, \
                        num_insts_obj_type_name,0,'Value',0,0,0,None]]
               resp_list = dev.get_values(reqs)
               if (not resp_list is None) \
                  and (not isinstance(resp_list,Exception)) \
                  and (resp_list[0][0] == 0):
                  num_obj_insts = resp_list[0][1]
         for i in range(num_obj_insts):
            obj_node = None
            status_node = None
            obj_name = obj_type_name
            if max_num_obj_insts > 1:
               obj_name += str(i)
            try:
               obj_node = self._ckt_dev_node.get_child(obj_name)
               status_node = obj_node.get_child(prop_info[0])
            except ENoSuchName, e:
               msglog.exception()
               continue # do not include this node in our list of status_nodes
            raw_value = status_node.get()
            if raw_value is None:
               continue # do not include this node in our list of status_nodes
            status_node_entry = (status_node, prop_info[1], obj_name)
            status_nodes.append(status_node_entry)
            req = ['Circuit',self._ckt_dev_node._item_inst_num, \
                   obj_node._obj_type_name,obj_node._obj_inst_num, \
                   status_node._prop_type_name,status_node._prop_inst_num, \
                   0, 0, None]
            reqs.append(req)
      return
   def stop(self):
      self.running = 0
      self._status_nodes = [] # clear list
      return
   ##
   # get_status():
   def get_status(self):
      result0 = self._get_sub_status(self._defr_reqs, self._defr_status_nodes, 'Defrost')
      result1 = self._get_sub_status(self._alm_reqs, self._alm_status_nodes, 'Alarm')
      if result1 == 'Normal':
         return result0 # might be Normal or Defrost
      return result1 # definitely Alarm
   def _get_sub_status(self, reqs, status_nodes, active_result):
      result = 'Normal'
      dev = self._ckt_dev_node._dev
      resp_list = dev.get_values(reqs)
      if len(resp_list) != len(reqs):
         msglog.log('mpx',msglog.types.ERR,'CktStatusXltrNode._get_status(): Sent %u Requests, recvd %u Responses.' \
                    % (len(reqs),len(resp_list)))
         return active_result # fail safe: indicate active ('Alarm' or 'Defrost') when actual state is unknown
      for i in range(len(resp_list)):
         resp = resp_list[i]
         if (resp is None) or isinstance(resp,Exception) or (resp[0] != 0):
            msglog.log('mpx',msglog.types.ERR,'Recvd invalid Response (%s) to Request (%s).' \
                       % (resp, reqs[i]))
            continue
         status_node_entry = status_nodes[i]
         is_active = status_node_entry[1](resp[1])
         if is_active == 1:
            result = active_result
            msglog.log('mpx',msglog.types.INFO,'Ckt %s %s, on %s' \
                       % (self.name, active_result, status_node_entry[2]))
      return result      

##
# class CktCaseTempsStatusXltrNode:
class CktCaseTempsStatusXltrNode(CompositeNode):
   def __init__(self, ckt_status_svc_node, case_temp_dev_node):
      CompositeNode.__init__(self)
      self._ckt_status_svc_node = ckt_status_svc_node
      self._case_temp_dev_node = case_temp_dev_node
      self._status_dev_node = self._case_temp_dev_node.get_child('Status')
      self.running = 0
      self._alarms = []
      return
   def start(self):
      self.running = 1
      return
   def stop(self):
      self.running = 0
      return
   ##
   # get():
   def get(self, skipCache=0):
      self._alarms = []
      if self._ckt_status_svc_node.get_status() == 'Alarm':
         self._alarms.append(self._ckt_status_svc_node.get_alarms())
         return 'Alarm'
      raw_value = self._status_dev_node.get()
      if (not raw_value is None) \
      and (type(raw_value) != types.StringType) \
      and (proc_StatusProp(raw_value) != 0):
         msglog.log('mpx',msglog.types.INFO,'Alarm on %s' % self._case_temp_dev_node.name)
         return 'Alarm'
      return 'Normal'

_rack_status_components = { \
                           'Group':{ \
                                    'Suction':['Status',proc_StatusProp] ,\
                                    'SuctionTemp':['Status',proc_StatusProp], \
                                    'DischargePressure':['Status',proc_StatusProp], \
                                    'DischargeTemperature':['Status',proc_StatusProp], \
                                    'PhaseLoss':['Value',proc_ListItemValueProp], \
                                    }, \
                           'Compressor':{ \
                                    'Status':['Status',proc_StatusProp] ,\
                                    'OilPressure':['Status',proc_StatusProp], \
                                    }, \
                           'Sensor':{ \
                                    'SensorValues':['Status',proc_StatusProp],\
                                    }, \
                           'AI':{ \
                                 'CalcCommandValue':['Status',proc_StatusProp] ,\
                                 'AnalogOutputValue':['Status',proc_StatusProp], \
                                 'AlarmState':['Value',proc_AlarmStateValueProp], \
                                 }, \
                           'AO':{ \
                                 'PIDOutput':['Status',proc_StatusProp], \
                                 }, \
                           'DO':{ \
                                 'CommandValue':['Status',proc_StatusProp] ,\
                                 'Status':['Value',proc_DigOutStatusValueProp], \
                                 }, \
                           'Power':{ \
                                 'CurrentPowerUsage':['Status',proc_StatusProp] ,\
                                 }, \
                           'Condenser':{ \
                                    'FanStatus':['Status',proc_StatusProp], \
                                    'AmbientTemperature':['Status',proc_StatusProp], \
                                    'InletTemp':['Status',proc_StatusProp], \
                                    'OutletTemp':['Status',proc_StatusProp], \
                                    'DischargePressure':['Status',proc_StatusProp], \
                                    'DischargeTemperature':['Status',proc_StatusProp], \
                                    'InletPressure':['Status',proc_StatusProp], \
                                    'OutletPressure':['Status',proc_StatusProp], \
                                    'TwoSpeedStatus':['Status',proc_StatusProp], \
                                    'VSOutput':['Status',proc_StatusProp], \
                                    }, \
                           'AntiSweat':{ \
                                 'Output':['Status',proc_StatusProp] ,\
                                 }, \
                           }
##
# class RackStatusXltrNode:
class RackStatusXltrNode(CompositeNode):
   _status_components = _rack_status_components
   def __init__(self, dev_node, ckt_svc_nodes=None):
      CompositeNode.__init__(self)
      if ckt_svc_nodes is None:
         ckt_svc_nodes = []
      self._ckt_svc_nodes = ckt_svc_nodes
      self._status_nodes = []
      self.running = 0
      self._dev_node = dev_node
      self._reqs = []
      return
   def start(self):
      self._reqs = []
      # Walk maps of gathered item_node refs, and add status_node_entries:
      for item_type_name, obj_map in self._status_components.items():
         if not self._dev_node.has_child(item_type_name):
            msglog.log('mpx',msglog.types.INFO,'Device %s does not have any Items of type %s' \
                       % (self._dev_node.name,item_type_name))
            continue
         item_type_node = self._dev_node.get_child(item_type_name)
         item_nodes = item_type_node.children_nodes()
         for item_node in item_nodes:
            for obj_type_name, prop_info in obj_map.items():
               obj_types = self._dev_node._dev.item_types[item_type_name].obj_types
               max_num_obj_insts = obj_types[obj_type_name].max_num_instances
               num_obj_insts = max_num_obj_insts
               if max_num_obj_insts > 1:
                  num_insts_obj_type_name = obj_types[obj_type_name].num_insts_obj_type_name
                  if not num_insts_obj_type_name is None:
                     reqs = [[item_type_name,item_node._item_inst_num, \
                              num_insts_obj_type_name,0,'Value',0,0,0,None]]
                     resp_list = self._dev_node._dev.get_values(reqs)
                     if (not resp_list is None) \
                        and (not isinstance(resp_list,Exception)) \
                        and (resp_list[0][0] == 0):
                        num_obj_insts = resp_list[0][1]
               for i in range(num_obj_insts):
                  obj_node = None
                  status_node = None
                  obj_name = obj_type_name
                  if max_num_obj_insts > 1:
                     obj_name += str(i)
                  try:
                     obj_node = item_node.get_child(obj_name)
                     status_node = obj_node.get_child(prop_info[0])
                  except ENoSuchName, e:
                     msglog.exception()
                     continue # do not include this node in our list of status_nodes
                  raw_value = status_node.get()
                  if raw_value is None:
                     continue # do not include this node in our list of status_nodes
                  status_node_entry = (status_node, prop_info[1], obj_name, item_type_name, item_node._item_inst_num)
                  self._status_nodes.append(status_node_entry)
                  req = [item_type_name,item_node._item_inst_num, \
                         obj_node._obj_type_name,obj_node._obj_inst_num, \
                         status_node._prop_type_name,status_node._prop_inst_num, \
                         0, 0, None]
                  self._reqs.append(req)
      self.running = 1
      return
   def stop(self):
      self.running = 0
      self._status_nodes = [] # clear list
      return
   ##
   # get():
   # @fixme get() should send up to 4 requests simultaneously, rather than 1 at a time;
   # however, get() should also cause the individual status nodes' values to be updated...
   def get(self, skipCache=0):
      result = 'Normal'
      for ckt_svc_node in self._ckt_svc_nodes:
         if ckt_svc_node.get_status() == 'Alarm':
            result = 'Alarm'
      resp_list = self._dev_node._dev.get_values(self._reqs)
      if len(resp_list) != len(self._reqs):
         msglog.log('mpx',msglog.types.ERR,'RackStatusXltrNode.get(): Sent %u Requests, recvd %u Responses.' \
                    % (len(self._reqs),len(resp_list)))
         return 'Alarm'
      for i in range(len(resp_list)):
         resp = resp_list[i]
         if (resp is None) or isinstance(resp,Exception) or (resp[0] != 0):
            msglog.log('mpx',msglog.types.ERR,'Recvd invalid Response (%s) to Request (%s).' \
                       % (resp, self._reqs[i]))
            continue
         status_node_entry = self._status_nodes[i]
         is_alarm = status_node_entry[1](resp[1])
         if is_alarm == 1:
            result = 'Alarm'
            msglog.log('mpx',msglog.types.INFO,'Rack %s Alarm on %s,%s,%s' \
                       % (self.name, status_node_entry[3], status_node_entry[4], \
                          status_node_entry[2]))
      return result

   
   
   
   
   
