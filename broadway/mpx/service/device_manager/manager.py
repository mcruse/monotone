"""
Copyright (C) 2010 2011 Cisco Systems

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
import os
import urllib

from mpx.lib import msglog
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import EUnreachableCode
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.lib.node import as_internal_node
from mpx.lib.node import is_node
from mpx.lib.threading import Lock

from udi import UniqueDeviceIdentifier

##
# A namespace for UDIs.  Yet another acyclic directed graph, highly specialized
# for UDIs.
#
# @note Assumes it is accessed in a thread safe manner. 
class UDINS(object):
    def __init__(self):
        self.__root = {}
        self.__ids = {}
        return
    def __lookup_udi(self, udi_class, ordered_keys, udi_dict, parent_ns):
        current_key = ordered_keys.pop(0)
        child_key = udi_dict[current_key]
        current_ns = parent_ns.get(current_key, None)
        if current_ns is None:
            current_ns = {}
            parent_ns[current_key] = current_ns
        if not ordered_keys:
            udi = current_ns.get(child_key, None)
            if udi is None:
                udi = udi_class(udi_dict)
                current_ns[child_key] = udi
                self.__ids[udi.id()] = udi
            return udi
        child_ns = current_ns.get(child_key, None)
        if child_ns is None:
            child_ns = {}
            current_ns[child_key] = child_ns
        return self.__lookup_udi(udi_class,
                                 ordered_keys, udi_dict, child_ns)
    def udi_from_kw(self, udi_class, **kw):
        keys = udi_class.sort_keys(kw.keys())
        return self.__lookup_udi(udi_class, keys, kw, self.__root)
    def udi_from_udi(self, udi):
        udi_id = id(udi)
        if self.__ids.has_key(udi_id):
            return udi
        return self.__lookup_udi(udi.__class__, udi.keys(), udi, self.__root)
    def udi_from_id(self, udi_id):
        return self.__ids[udi_id]

def node_exists(path):
    try:
        as_internal_node(path)
    except ENoSuchName:
        return False
    return True

class MonitorContainer(CompositeNode):
    def __init__(self):
        self.device_manager = None
        return
    def configure(self, config):
        super(MonitorContainer, self).configure(config)
        self.device_manger = self.parent
        return

class DynamicMonitorContainer(MonitorContainer):
    pass

class StaticMonitorContainer(MonitorContainer):
    pass

import mpx.service.alarms
import mpx.service.alarms.trigger
import mpx.lib.node

from mpx.lib import thread_pool
from mpx.lib import thread_queue

##
# @note Must provide basic functionality regardless of start/stop state, but
#       configuration must be complete.
#       Start/Stop only effect any background processing...
class DeviceManager(CompositeNode):
    DEFAULT_NAME = 'Device Manager'
    DYNAMIC_CONTAINER = 'Dynamic Monitors'
    STATIC_CONTAINER = 'Statically Configured Monitors'
    ALARMS_PATH_COMPONENTS = (
        ('services',mpx.service.factory),
        ('alarms',mpx.lib.node.CompositeNode),
        ('Device Unavailable Alarms', mpx.service.alarms.AlarmManager),
        ('alarms', mpx.lib.node.CompositeNode),
        )
    ALARM_PATH = '/'.join(map(lambda c: urllib.quote(c[0]),
                              (('', ''),) + ALARMS_PATH_COMPONENTS))
    EXPORTER_PATH_ELEMENTS = (
        map(lambda e: e[0], ALARMS_PATH_COMPONENTS[:-1]) + ['exporters']
        )
    EXPORTER_PATH = '/'.join([''] + EXPORTER_PATH_ELEMENTS)
    def DEVICE_MANAGER_NODE(klass):
        DEVICE_MANAGER_PATH_COMPONENTS = (
            ('services',mpx.service.factory),
            (klass.DEFAULT_NAME,klass),
            )
        DEVICE_MANAGER_PATH = '/'.join(map(lambda c: urllib.quote(c[0]),
                                           (('', ''),) +
                                           DEVICE_MANAGER_PATH_COMPONENTS))
        try:
            return as_node(DEVICE_MANAGER_PATH)
        except ENoSuchName:
            return DeviceManager.__node_from_components(
                DEVICE_MANAGER_PATH_COMPONENTS
                )
        raise EUnreachableCode()
    DEVICE_MANAGER_NODE = classmethod(DEVICE_MANAGER_NODE)
    def __init__(self, *args):
        CompositeNode.__init__(self)
        self.__running = False
        self.__udins = UDINS()
        self.__monitors = {}
        self.__alarms = {}
        self.__lock = Lock()
        self.__dynamic_container = None
        self.__static_container = None
        self.__alarm_container = None
        self.__serial_queue = thread_queue.ThreadQueue(thread_pool.NORMAL, 1)
        return
    def __new_container(self, name, factory):
        if not self.has_child(name):
            child = factory()
            child.configure({'parent':self,
                             'name':name})
            return child
        return self.get_child(name)
    def __node_from_components(klass, components):
        elements = ['/']
        parent = as_node('/')
        for element, factory in components:
            elements.append(urllib.quote(element))
            path = os.path.join(*elements)
            if node_exists(path):
                parent = as_node(path)
                continue
            msglog.log('Device Manager', msglog.types.INFO,
                   "Creating %r." % path)
            node = factory()
            node.configure({'parent':parent,'name':element})
            parent = node
        return parent
    __node_from_components = classmethod(__node_from_components)
    def __init_alarm_container(self):
        if not is_node(self.ALARM_PATH):
            msglog.log('Device Manager', msglog.types.WARN,
                       "%s does not exist, Device Unavailable alarms may"
                       " not be configured for export." % self.ALARM_PATH)
            self.__node_from_components(self.ALARMS_PATH_COMPONENTS)
        self.__alarm_container = as_node(self.ALARM_PATH)
        if not is_node(self.EXPORTER_PATH):
            msglog.log('Device Manager', msglog.types.WARN,
                       "%s does not exist, Device Unavailable alarms will"
                       " not be exported." % self.EXPORTER_PATH)
        else:
            exporters = as_node(self.EXPORTER_PATH)
            if not exporters.children_names():
                msglog.log('Device Manager', msglog.types.WARN,
                           "%s does not have any exporters configured,"
                           " Device Unavailable alarms will"
                           " not be exported." %
                           self.EXPORTER_PATH)
        return
    def __create_monitor_alarm(self, udi_id, device_monitor):
        #assert self.__lock.locked()
        #assert not self.__alarms.has_key(udi_id)
        #assert self.__monitors.has_key(udi_id)
        new_alarm = mpx.service.alarms.trigger.DynamicComparisonTrigger()
        new_alarm.configure(
            {'parent':self.__alarm_container,
             'name':device_monitor.name,
             'send_retries':3,
             'input':device_monitor.as_node_url(),
             'enabled':1,
             'message':("%s is unavailable" % device_monitor.udi.as_text()),
             'poll_period':60,
             'comparison':'greater_than',
             'constant':0,
             'require_acknowledge':1,
             }
            )
        new_alarm.start()
        return
    def __register_monitor(self, device_monitor):
        udi = self.__udins.udi_from_udi(device_monitor.udi)
        udi_id = udi.id()
        if not self.__monitors.has_key(udi_id):
            self.__monitors[udi_id] = device_monitor
        else:
            pass #assert self.__monitors[udi_id] is device_monitor
        if not self.__alarms.has_key(udi_id):
            self.__create_monitor_alarm(udi_id, device_monitor)
        return
    def register_monitor(self, device_monitor):
        msglog.log('Device Manager', msglog.types.INFO,
                   'Registering %s: %s' % (device_monitor.as_node_url(),
                                           device_monitor.udi.as_text()))
        self.__lock.acquire()
        try:
            self.__register_monitor(self, device_monitor)
        finally:
            self.__lock.release()
        return
    def static_container(self):
        return self.__static_container
    def dynamic_container(self):
        return self.__dynamic_container
    def configure(self, config):
        self.setattr('name', config.get('name',self.DEFAULT_NAME))
        super(DeviceManager, self).configure(config)
        #
        # Create inherent children if they don't exist.
        #
        self.__dynamic_container = self.__new_container(
            self.DYNAMIC_CONTAINER,
            DynamicMonitorContainer
            )
        self.__static_container = self.__new_container(
            self.STATIC_CONTAINER,
            StaticMonitorContainer
            )
        self.__init_alarm_container()
        return
    def configuration(self):
        config = super(DeviceManager, self).configuration()
        return config
    def start(self):
        if self.__running:
            return
        super(DeviceManager, self).start()
        return
    def stop(self):
        self.__running = False
        super(DeviceManager, self).stop()
        return
    def udi_from_kw(self, udi_class, **kw):
        self.__lock.acquire()
        try:
            return self.__udins.udi_from_kw(udi_class, **kw)
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def udi_from_udi(self, udi):
        self.__lock.acquire()
        try:
            return self.__udins.udi_from_udi(udi)
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def __monitor_from_id(self, udi_id):
        #assert self.__lock.locked()
        device_monitor = self.__monitors.get(udi_id, None)
        if device_monitor is None:
            udi = self.__udins.udi_from_id(udi_id)
            device_monitor = udi.monitor_class()
            device_monitor.configure({'parent':self.__dynamic_container,
                                      'name':udi.as_text(),
                                      'udi':udi})
            self.__register_monitor(device_monitor)
            if self.__running:
                # In case a DeviceMonitor.start() implementation calls
                # a public DeviceManager method that could deadlock.
                self.__serial_queue.queue_noresult(device_monitor.start)
        return device_monitor
    def monitor_from_udi(self, udi):
        self.__lock.acquire()
        try:
            udi = self.__udins.udi_from_udi(udi)
            udi_id = id(udi)
            return self.__monitor_from_id(udi_id)
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def monitor_from_kw(self, udi_class, **kw):
        self.__lock.acquire()
        try:
            udi = self.__udins.udi_from_kw(udi_class, **kw)
            udi_id = id(udi)
            return self.__monitor_from_id(udi_id)
        finally:
            self.__lock.release()
        raise EUnreachableCode()
