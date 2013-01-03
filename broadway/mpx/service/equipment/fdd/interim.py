"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import time
from mpx.lib.node import as_node
from mpx.lib.scheduler import scheduler
from mpx.service.alarms2.alarmevent import StateEvent
from mpx.service.alarms2.alarmevent import ActionEvent
from mpx.service.alarms2.alarmevent import AlarmCleared
from mpx.service.alarms2.alarmevent import AlarmTriggered
from mpx.service.alarms2.alarmevent import AlarmEventRaised
from mpx.service.alarms2.alarmevent import AlarmEventClosed
from mpx.service.equipment.fdd.event import FaultEvent as _FaultEvent

##
# This module defines classes based on the similar alarm-based 
# events to enable integration into the non-refactored alarm 
# manager.  This is an interim solution until a generic event 
# module is created and the alarm management rolled into the 
# new manager or integrated with in clean manner.
class FaultDetected(AlarmTriggered): 
    TYPE = 'Triggered'

class FaultCleared(AlarmCleared): 
    TYPE = 'Cleared'

class FaultUpdated(ActionEvent):
    TYPE = 'Updated'

class FaultTimedOut(AlarmCleared):
    TYPE = 'Timeout'

class FaultEventRaised(AlarmEventRaised):
    TYPE = 'Open'
    name = TYPE.upper()
    def __init__(self, faultevent, action, origin = None, guid = None):
        super(FaultEventRaised, self).__init__(
            faultevent, action, origin, guid)
    def __call__(self, event):
        if isinstance(event, FaultTimedOut):
            return FaultEventClosed(self.source, event)
        elif isinstance(event, FaultCleared):
            return FaultEventClosed(self.source, event)
        else:
            return FaultChanged(self.source, event)

class FaultChanged(StateEvent):
    TYPE = 'Fault State'
    name = TYPE.upper()    
    def __init__(self, faultevent, action, origin = None, guid = None):
        super(FaultChanged, self).__init__(faultevent, action, origin, guid)
    def __call__(self, event):
        if isinstance(event, FaultTimedOut):
            return FaultEventClosed(self.source, event)
        elif isinstance(event, FaultCleared):
            return FaultEventClosed(self.source, event)
        else: 
            return FaultChanged(self.source, event)

class FaultEventClosed(AlarmEventClosed):
    TYPE = 'Normal'
    name = TYPE.upper()
    def __init__(self, faultevent, action, origin = None, guid = None):
        super(FaultEventClosed, self).__init__(
            faultevent, action, origin, guid)
    def __call__(self, event):
        return self

class FaultEvent(_FaultEvent):
    TYPE = 'Fault'
    manager = None

    def __init__(self, source, title, timestamp, 
                 description, origin = None, guid = None):
        super(FaultEvent, self).__init__(
            source, title, 'Normal', timestamp, description, origin, guid)
        if FaultEvent.manager is None:
            FaultEvent.manager = as_node('/services/Alarm Manager')
        self.__history = []
        self.current_event = None
        self._dispatcher = self.manager
        self.debug = 0
        self.message('created.')
        self.state_name = 'Normal'
        self.detectedevent = None
    def set_state(self, state, timestamp, detail):
        if state == self.state_name:
            return
        if self.state_name == 'Normal':
            self.timestamp = timestamp
            actionevent = FaultDetected(self, timestamp, 
                                        self.source, None, 
                                        self.origin, None)
            self.detectedevent = actionevent
        elif state == 'Normal':
            # Overriding close time because feed doesn't give TZ.
            self.closetime = timestamp = time.time()
            actionevent = FaultCleared(self, timestamp, 
                                       self.source, None, 
                                       self.origin, None)
        else:
            actionevent = FaultUpdated(self, timestamp, 
                                       self.source, None, 
                                       self.origin, None)
        self.state_name = state
        actionevent.detail = detail
        self.handle_event(actionevent)
    def get_history(self):
        return self.__history[:]
    history = property(get_history)
    def handle_event(self, event):
        previous = self.current_event
        if previous and previous.name == self.state_name:
            return
        if isinstance(event, StateEvent):
            next = event
        elif previous:
            next = previous(event)
        else:
            next = FaultEventRaised(self, event)
        if next is previous:
            return
        elif previous is not None:
            self.__history.append(previous)
        next.detail = event.detail
        self.current_event = next
        self.current_event.name = self.state_name
        self._dispatcher.dispatch(self.current_event)
    def notify(self, command, *args, **kw):
        method = getattr(self, command)
        return method(*args, **kw)
    def get_state(self): 
        return self.current_event.name
    state = property(get_state)
    def is_state(self, state):
        state = state.upper()
        if state == 'CLOSED':
            return isinstance(self.current_event, FaultEventClosed)
        else:
            return self.state == state.upper()
    def get_alarm_event(self):
        return self
    def set_timeout(self, timeout):
        super(FaultEvent, self).set_timeout(timeout)
        self.timeoutevent = FaultTimedOut(
            self, self.closetime, self.source, None, self.origin, None)
        self.scheduled_timeout = scheduler.at(
            self.closetime, self.handle_event, (self.timeoutevent,))
    def message(self, message, category = 'debug'):
        if category != 'debug' or (category == 'debug' and self.debug):
            print '%s: %s' % (str(self), message)
        return
