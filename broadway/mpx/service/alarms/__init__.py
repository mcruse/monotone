"""
Copyright (C) 2002 2003 2006 2008 2010 2011 Cisco Systems

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
# @tag Tagged pre_dm in an attempt to assist with merge to trunl.
#      After merge, remove the tag and this comment.

from mpx.service import ServiceNode
from mpx.lib import msglog
from mpx.lib.event import EventConsumerMixin, AlarmTriggerEvent, \
     AlarmClearEvent
from mpx.lib.threading import Queue,ImmortalThread
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.threading import Lock,Thread

class UniqueID(PersistentDataObject):
    def __init__(self,node):
        self._lock = Lock()
        self.id = 0
        PersistentDataObject.__init__(self,node)
        self.load()
    def allocate_id(self):
        self._lock.acquire()
        try:
            id = self.id
            self.id += 1
            self.save('id')
        finally:
            self._lock.release()
        return id
##
# This class will manage a group of alarm triggers 
# and will have information associated with it like 
# the action to be taken when one of its triggers 
# throws an AlarmEvent.
class AlarmManager(ServiceNode,EventConsumerMixin):
    def __init__(self):
        ServiceNode.__init__(self)
        EventConsumerMixin.__init__(self, self.handle_alarm, \
                                    self.handle_exception)
        self.__running = 0
        self.__queue = Queue()
        self._id_manager = None
        self._dynamic_alarms = {}
        return
    def configure(self, config):
        ServiceNode.configure(self, config)
        if self._id_manager is None:
            self._id_manager = UniqueID(self)
        return
    def unique_id(self):
        return self._id_manager.allocate_id()
    def active(self):
        children = []
        for child in self.chidlren_nodes():
            if child.active():
                children.append(child)
        return children
    def acknowledged(self):
        children = []
        for child in self.children_nodes():
            if child.active() and child.acknowledged():
                children.append(child)
        return children
    def unacknowledged(self):
        children = []
        for child in self.children_nodes():
            if child.active() and not child.acknowledged():
                children.append(child)
        return children
    def add_dynamic_alarm(self, dynamic_alarm):
        dynamic_alarm_id = id(dynamic_alarm)
        if not self._dynamic_alarms.has_key(dynamic_alarm_id):
            self._dynamic_alarms[dynamic_alarm_id] = dynamic_alarm
            dynamic_alarm.event_subscribe(self, AlarmTriggerEvent)
            dynamic_alarm.event_subscribe(self, AlarmClearEvent)
        return
    def start(self):
        if not self.__running:
            known_alarms = self.get_child('alarms')
            for child in known_alarms.children_nodes():
                child.event_subscribe(self, AlarmTriggerEvent)
                child.event_subscribe(self, AlarmClearEvent)
            self.__running = 1
            self.__thread = ImmortalThread(name=self.name,target=self.__run)
            self.__thread.start()
            ServiceNode.start(self)
        return
    def stop(self):
        self.__running = 0
        self.__thread = None
        self.__queue.put(None)
        try:
            # @fixme try/except/else is a hack to survive testcases use
            #        of prune.  Really should revisit...
            alarms = self.get_child('alarms')
        except:
            pass
        else:
            for child in alarms.children_nodes():
                child.cancel(self, AlarmTriggerEvent)
                child.cancel(self, AlarmClearEvent)
        return ServiceNode.stop(self)
    def queue_alarm_check(self,alarm):
        self.__queue.put(alarm)
    def __run(self):
        while self.__running:
            alarm = self.__queue.get()
            if alarm:
                alarm.check_condition()
        else:
            self.__thread.should_die()
        return
    ##
    # Both AlarmClear and AlarmTrigger events come here,
    # separate the two and send to the appropriate handler.
    def handle_alarm(self, alarm):
        alarm.source.caught(alarm)
        if self.debug:
            msglog.log('broadway',msglog.types.ALARM,str(alarm))
        if alarm.__class__ == AlarmTriggerEvent:
            return self._handle_trigger(alarm)
        elif alarm.__class__ == AlarmClearEvent:
            return self._handle_clear(alarm)
        msglog.log('broadway', msglog.types.WARN,'Alarm manager %s got ' +
                   'an event that it does not recoginize, ignoring.' % 
                   self.name)
    def _handle_trigger(self, alarm):
        export_thread = Thread(name=alarm.source.name,
                               target=self._run_exports,
                               args=(alarm,))
        export_thread.start()
    def _run_exports(self,alarm):
        if self.has_child('exporters'):
            exporters = self.get_child('exporters').children_nodes()
            exceptions = []
            for exporter in exporters:
                try:
                    exporter.export(alarm)
                except Exception, e:
                    msglog.exception()
                    exceptions.append(e)
            if exceptions:
                alarm.source.fail(alarm)
            else:
                alarm.source.success(alarm)
        else:
            msglog.log('broadway', msglog.types.WARN,
                       "Alarm manager %s can't export.  No exporters defined."
                       % self.name)
            alarm.source.success(alarm)
        return
    ##
    # Perhaps with some Managers we would want to cancel 
    # unsent alarms, here is where that would be done.
    def _handle_clear(self, alarm):
        pass
    ##
    # This means that an exception was raised when my 
    # _handle_event code was running.
    def handle_exception(self, exc, alarm=None):
        msglog.exception()
