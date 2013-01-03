"""
Copyright (C) 2007 2011 Cisco Systems

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
from mpx.lib import msglog
from mpx.componentry import implements
from interfaces import ITriggerManager
from triggers import Trigger
from triggers import TriggerActivated
from triggers import TriggerCleared
from threading import Event as Flag
from mpx.lib.threading import Queue
from mpx.lib.threading import NOTHING
from mpx.lib.threading import ImmortalThread
from mpx.lib.eventdispatch.dispatcher import Dispatcher
from mpx.lib.neode.node import CompositeNode
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

class TriggerManager(CompositeNode):
    implements(ITriggerManager)
    security = SecurityInformation.from_default()
    secured_by(security)

    def __init__(self, *args):
        self.dispatcher = None
        self._queue = None
        self._stopflag = None
        self._thread = None
        CompositeNode.__init__(self, *args)
    security.protect('get_trigger', 'View')
    def get_triggers(self):
        return self.children_nodes()
    security.protect('get_trigger', 'View')
    def get_trigger(self, name):
        return self.get_child(name)
    security.protect('add_trigger', 'Configure')
    def add_trigger(self, trigger):
        return self.add_child(trigger)
    security.protect('remove_trigger', 'Configure')
    def remove_trigger(self, trigger):
        return self.prune_child(trigger)
    security.protect('get_trigger_names', 'View')
    def get_trigger_names(self):
        return self.children_names()
    security.protect('get_active', 'View')
    def get_active(self):
        children = self.children_nodes()
        active = map(Trigger.is_active, children)
        return [child for child in children if child.is_active()]
    security.protect('get_inactive', 'View')
    def get_inactive(self):
        children = self.children_nodes()
        active = map(Trigger.is_active, children)
        return [child for child in children if not child.is_active()]
    def start(self):
        if self._thread is not None:
            raise Exception('Cannot call start on started '
                            'Manager without stopping.')
        if self.dispatcher is None:
            self.dispatcher = Dispatcher(self.url)
        self.triggersub = self.dispatcher.register_for_type(
            self.handle_triggered, TriggerActivated)
        self.clearsub = self.dispatcher.register_for_type(
            self.handle_cleared, TriggerCleared)
        self._startmanager()
        return super(TriggerManager, self).start()
    def stop(self):
        if self.triggersub: self.dispatcher.unregister(self.triggersub)
        if self.clearsub: self.dispatcher.unregister(self.clearsub)
        self.triggersub = self.clearsub = None
        self._stopmanager()
        return super(TriggerManager, self).stop()
    def _add_child(self, child): pass
    def _rename_child(self, *args): pass
    def queue_trigger(self, trigger):
        self._queue.put(trigger)
    def is_running(self):
        return not not (self._thread and self._thread.isAlive())
    security.protect('handle_triggered', 'Override')
    def handle_triggered(self, event):
        trigger = event.get_trigger()
        targets = trigger.get_targets()
        arguments = event.get_arguments()
        for target in targets: target.trigger(*arguments)
        return len(targets)
    security.protect('handle_cleared', 'Override')
    def handle_cleared(self, event):
        trigger = event.get_trigger()
        targets = trigger.get_targets()
        arguments = event.get_arguments()
        for target in targets: target.clear(*arguments)
        return len(targets)
    def _startmanager(self):
        self._queue = queue = Queue()
        self._stopflag = stopflag = Flag()
        self._thread = thread = ImmortalThread(
            name=self.url, target=self._runmanager, args = (stopflag, queue))
        thread.start()
    def _stopmanager(self):
        stopflag, self._stopflag = self._stopflag, None
        thread, self._thread = self._thread, None
        if not thread: return
        thread.should_die()
        stopflag.set()
        thread.join()
    def _runmanager(self, stopflag, queue):
        while not stopflag.isSet():
            trigger = queue.get(1)
            if trigger is not NOTHING:
                trigger()
        else:
            msglog.log('broadway', msglog.types.INFO,
                       'Trigger Manager exiting run.')
            print 'Trigger Manager run exiting.'
        return
