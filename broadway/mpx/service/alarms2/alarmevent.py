"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
from urllib import urlopen
from mpx.lib import msglog
from interfaces import IStateEvent
from interfaces import IAlarmEvent
from interfaces import IActionEvent
from mpx.componentry import implements
from mpx.lib.eventdispatch import Event
from mpx.lib.node import as_node
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

def format(timestamp, milliseconds=True):
    msvalue = ""
    if milliseconds:
        msvalue = ".%0.3d" % ((timestamp - int(timestamp)) * 1000)
    format = "%Y-%b-%d %H:%M:%S" + msvalue + " %Z"
    timestruct = time.localtime(timestamp)
    return time.strftime(format, timestruct)

class ActionEvent(Event):
    implements(IActionEvent)
    def __init__(self, source, timestamp, actuator,
                 context, origin=None, guid=None, **kw):
        super(ActionEvent, self).__init__(source, origin, guid)
        self.timestamp = timestamp
        self.actuator = actuator
        self.context = context
        if not isinstance(actuator, str) and hasattr(actuator, 'name'):
            self.actuatorstr = actuator.name
        else: 
            self.actuatorstr = str(actuator)
        self.user_msg=kw.get("message")

class AlarmAction(ActionEvent): 
    pass

class AlarmTriggered(AlarmAction): 
    pass

class AlarmCleared(AlarmAction): 
    pass

class AlarmEventAction(ActionEvent): 
    pass

class AlarmEventAcknowledged(AlarmEventAction): 
    pass

class AlarmEventTerminated(AlarmEventAction):
    """
        Special purpose action used by alarm management policies 
        to force trimming of expired alarm event instances.
        
        Note that the definition of 'expired' is policy specific.
    """

class StateEvent(Event):
    implements(IStateEvent)
    name = 'NONE'
    datestring = None
    timestring = None
    def __init__(self, alarmevent, action, origin = None, guid = None):
        super(StateEvent, self).__init__(alarmevent, origin, guid)
        self.action = action
    def tostring(self):
        if not (self.datestring and self.timestring):
            localtime = time.localtime(self.action.timestamp)
            self.datestring = time.strftime('%m/%d/%Y', localtime)
            self.timestring = time.strftime('%H:%M:%S %Z', localtime)
        format = '%s by %s on %s, %s %s'
        message = format % (self.name.upper(), self.action.actuatorstr,
                            self.origin, self.datestring, self.timestring)
        if self.action.context:
            message = '%s: %s' % (message, self.action.context)
        return message
    def get_alarm_event(self):
        return self.source
    def __call__(self, event):
        if isinstance(event, AlarmEventTerminated):
            return AlarmEventClosed(self.source, event)
        return self
    def __str__(self):
        # Initialize time-strings.
        name = type(self).__name__
        timestamp = time.ctime(self.action.timestamp)
        return "%s(%r, %r, %r)" % (name, self.GUID, self.origin, timestamp)
    def __repr__(self):
        return "<%s instance at %#x>" % (self, id(self))

class AlarmEventRaised(StateEvent):
    name = 'RAISED'
    def __call__(self, event):
        if isinstance(event, AlarmCleared):
            return AlarmEventCleared(self.source, event)
        elif isinstance(event, AlarmEventAcknowledged):
            return AlarmEventAccepted(self.source, event)
        return super(AlarmEventRaised, self).__call__(event)

class AlarmEventAccepted(StateEvent):
    name = 'ACCEPTED'
    def __call__(self, event):
        if isinstance(event, AlarmCleared):
            return AlarmEventClosed(self.source, event)
        return super(AlarmEventAccepted, self).__call__(event)

class AlarmEventCleared(StateEvent):
    name = 'CLEARED'
    def __call__(self, event):
        if isinstance(event, AlarmEventAcknowledged):
            return AlarmEventClosed(self.source, event)
        return super(AlarmEventCleared, self).__call__(event)

class AlarmEventClosed(StateEvent):
    name = 'CLOSED'
    def __call__(self, event):
        return self

class AlarmEvent(Event):
    implements(IAlarmEvent)
    manager = None
    security = SecurityInformation('View', 'Configure', 'Private')
    secured_by(security)
    def __init__(self, alarm, origin = None, guid = None):
        super(AlarmEvent, self).__init__(alarm, origin, guid)
        if AlarmEvent.manager is None:
            AlarmEvent.manager = as_node('/services/Alarm Manager')
        self.__history = []
        self.current_event = None
        if self.is_local():
            self._dispatcher = alarm
            self._subscription = alarm.dispatcher.register_for_type(
                self.handle_event, AlarmAction)
        else:
            self._dispatcher = self.manager
            self._subscription = None
        self.debug = 0
        self.message('created.')
    def get_audit(self):
        return self.get_history() + [self.current_event]
    def first_action(self):
        return self.get_audit()[0].action
    def last_action(self):
        return self.get_audit()[-1].action
    def created(self):
        return self.first_action().timestamp
    def modified(self):
        return self.last_action().timestamp
    def get_history(self):
        return self.__history[:]
    history = property(get_history)
    def handle_event(self, event):
        previous = self.current_event
        if isinstance(event, StateEvent):
            next = event
        elif previous:
            next = previous(event)
        else:
            next = AlarmEventRaised(self, event)
        if next is not previous:
            if previous is not None:
                self.__history.append(previous)
            self.current_event = next
            if isinstance(next, AlarmEventClosed) and self._subscription:
                self.source.dispatcher.unregister(self._subscription)
                self._subscription = None
            self._dispatcher.dispatch(next)
            return True
        return False
    security.protect('acknowledge', 'Override')
    def acknowledge(self, actuator, timestamp, context):
        event = AlarmEventAcknowledged(self, timestamp, actuator, context)
        self.handle_event(event)
    security.protect('notify', 'Override')
    def acknowledged(self):
        return any(self.is_state(state) for state in ("accepted", "closed"))
    def asitem(self):
        item = {}
        item["id"] = self.GUID
        item["name"] = self.source.name
        item["state"] = self.state
        item["origin"] = self.origin
        item["priority"] = self.source.priority
        item["categories"] = ["alarm", "event"]
        item["createdUTC"] = self.created()
        item["modifiedUTC"] = self.modified()
        item["created"] = format(self.created())
        item["modified"] = format(self.modified())
        item["acknowledged"] = self.acknowledged()
        item["description"] = self.source.description
        item["history"] = [ev.tostring() for ev in self.get_audit()]
        return item
    def terminate(self, actuator, reason, timestamp=None):
        if not timestamp:
            timestamp = time.time()
        event = AlarmEventTerminated(self, timestamp, actuator, reason)
        self.handle_event(event)
    def notify(self, command, *args, **kw):
        method = getattr(self, command)
        return method(*args, **kw)
    def synchronize(self, events):
        current = self.get_history()
        if self.current_event is not None:
            current.append(self.current_event)
        newevents = events[len(current):]
        for event in newevents:
            self.handle_event(event)
        messages = map(str, newevents)
        self.message('synchronized with new events: %s.' % (messages,))
    def get_state(self): 
        return self.current_event.name
    state = property(get_state)
    def is_state(self, state):
        return self.state == state.upper()
    def get_alarm_event(self):
        return self
    def message(self, message, category = 'debug'):
        if category != 'debug' or (category == 'debug' and self.debug):
            print '%s: %s' % (str(self), message)
        return
