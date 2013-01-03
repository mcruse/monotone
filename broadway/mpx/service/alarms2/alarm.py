"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from threading import Event
from mpx.lib import msglog
from mpx.lib.neode.node import ConfigurableNode
from mpx.componentry import implements
from mpx.lib.eventdispatch.dispatcher import Dispatcher
from interfaces import IAlarm
from alarmevent import AlarmEvent
from alarmevent import AlarmTriggered
from alarmevent import AlarmCleared
from alarmevent import AlarmEventClosed
from alarmevent import AlarmEventRaised
from alarmevent import AlarmEventCleared
from alarmevent import AlarmEventAccepted
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from mpx.componentry.backports import Dictionary

class NeoAlarm(ConfigurableNode):
    implements(IAlarm)
    security = SecurityInformation.from_default()
    secured_by(security)
    security.make_private('events')
    def __init__(self, *args):
        self.events = {}
        self.max_raised = ""
        self.max_cleared = ""
        self.max_accepted = ""
        #CSCtf98046:changing default priority to P1
        self.priority = "P1"
        self.description = ""
        self.source = 'broadway'
        self.dispatcher = Dispatcher()
        super(NeoAlarm, self).__init__(*args)
    def configure(self,config):
        super(NeoAlarm, self).configure(config)
        self.setattr('source', config.get('source', self.source))
        priority = config.get("priority", self.priority)
        #CSCtf98046-changing all the blank priorities to P1. PH alarms have blank priority.
        if priority == "":
            priority = "P1"
        self.setattr('priority', priority)
        if "max_raised" in config:
            policy = config["max_raised"]
            if policy:
                try:
                    policy = int(policy)
                except ValueError:
                    raise ValueError('Value of field \'Max raised\' is not numeric')
            self.max_raised = policy
        if "max_cleared" in config:
            policy = config["max_cleared"]
            if policy:
                try:
                    policy = int(policy)
                except ValueError:
                    raise ValueError('Value of field \'Max cleared\' is not numeric')
            self.max_cleared = policy
        if "max_accepted" in config:
            policy = config["max_accepted"]
            if policy:
                try:
                    policy = int(policy)
                except ValueError:
                    raise ValueError('Value of field \'Max accepted\' is not numeric')
            self.max_accepted = policy
        description = config.get("description", self.description)
        self.setattr('description', description)
    def configuration(self):
        config = super(NeoAlarm, self).configuration()
        config['source'] = self.getattr('source')
        config['priority'] = self.getattr('priority')
        config["max_raised"] = self.getattr("max_raised", str)
        config["max_cleared"] = self.getattr("max_cleared", str)
        config["max_accepted"] = self.getattr("max_accepted", str)
        config['description'] = self.getattr('description')
        return config
    security.protect('trigger', 'Override')
    def trigger(self, source, timestamp, context, 
                information='', *args, **keywords):
        alarm_event = AlarmEvent(self)
        kwargs = {"message": information}
        triggered = AlarmTriggered(self, timestamp, source, context, **kwargs)
        self.dispatcher.dispatch(triggered)
    security.protect('clear', 'Override')
    def get_raised_policy(self):
        if isinstance(self.max_raised, int):
            policy = self.max_raised
        else:
            policy = self.parent.max_raised
        return policy
    def get_cleared_policy(self):
        if isinstance(self.max_cleared, int):
            policy = self.max_cleared
        else:
            policy = self.parent.max_cleared
        return policy
    def get_accepted_policy(self):
        if isinstance(self.max_accepted, int):
            policy = self.max_accepted
        else:
            policy = self.parent.max_accepted
        return policy
    def clear(self, source, timestamp, context, 
              information='', *args, **keywords):
        cleared = AlarmCleared(self, timestamp, source, context)
        self.dispatcher.dispatch(cleared)
    def prune(self, *args, **kw):
        events = self.get_events()
        self._terminate_events(events, "source alarm removed")
        return super(NeoAlarm, self).prune(*args, **kw)
    def _trim_backlog(self, state, limit):
        events = self.events_by_state(state)
        sortable = [(event.created(), event) for event in events]
        events = [event for ts,event in reversed(sorted(sortable))][limit:]
        return self._terminate_events(events, "trim %r event backlog" % state)
    def _terminate_events(self, events, reason):
        for event in events:
            try:
                event.terminate("Alarm %r" % self.name, reason)
            except:
                message = "Failed to terminate: %s."
                msglog.warn("Failed to terminate: %s." % event)
                msglog.exception(prefix="handled")
            else:
                message = "Alarm %r terminated event %s: %s."
                msglog.inform(message % (self.name, event, reason))
        return events
    def get_event(self, id): 
        return self.events[id]
    # Trick to make Framework's as_node work with AlarmEvents.
    get_child = get_event
    def get_events(self): 
        return self.events.values()
    def get_events_dictionary(self):
        states = {"raised": [], "accepted": [], "cleared": [], "closed": []}
        for event in self.get_events():
            states[event.state.lower()].append(event)
        return states
    def get_event_count(self):
        return len(self.get_events())
    def get_event_counts(self):
        states = self.get_events_dictionary()
        return dict([(st, len(evs)) for st,evs in states.items()])
    def events_by_state(self, state, negate=False):
        state = state.upper()
        events = self.get_events()
        if negate: 
            events = [event for event in events if event.state != state]
        else: 
            events = [event for event in events if event.state == state]
        return events
    def get_raised(self): 
        return self.events_by_state('raised')
    def get_accepted(self): 
        return self.events_by_state('accepted')
    def get_cleared(self): 
        return self.events_by_state('cleared')
    def get_closed(self): 
        return self.events_by_state('closed')
    def get_not_raised(self): 
        return self.events_by_state('raised', True)
    def get_not_accepted(self): 
        return self.events_by_state('accepted', True)
    def get_not_cleared(self): 
        return self.events_by_state('cleared', True)
    def get_not_closed(self): 
        return self.events_by_state('closed', True)
    def dispatch(self, event):
        if isinstance(event, AlarmEventRaised):
            self.events[event.source.GUID] = event.source
            self.dispatcher.dispatch(event.source)
            self.parent.dispatch(event.source)
        self.dispatcher.dispatch(event)
        result = self.parent.dispatch(event)
        if isinstance(event, AlarmEventRaised):
            policy = self.get_raised_policy()
            if policy > 0:
                self._trim_backlog("raised", policy)
        elif isinstance(event, AlarmEventAccepted):
            policy = self.get_accepted_policy()
            if policy > 0:
                self._trim_backlog("accepted", policy)
        elif isinstance(event, AlarmEventCleared):
            policy = self.get_cleared_policy()
            if policy > 0:
                self._trim_backlog("cleared", policy)
        elif isinstance(event, AlarmEventClosed):
            del(self.events[event.source.GUID])
        return result
    def __str__(self):
        typename = type(self).__name__
        return "%s(%r)" % (typename, self.as_node_url())
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

class Alarm(NeoAlarm):
    """
        This extension is provided to replace the new Alarm class with
        a version having reverse-compatibility hooks for PHWin's existing
        framework interaction.
    """
    security = SecurityInformation.from_default()
    secured_by(security)

    def __init__(self, *args):
        self.__in_alarm = Event()
        super(Alarm, self).__init__(*args)

    security.protect('trigger', 'Override')
    def trigger(self, *args, **kw):
        self.__in_alarm.set()
        return super(Alarm, self).trigger(*args, **kw)

    security.protect('clear', 'Override')
    def clear(self, *args, **kw):
        self.__in_alarm.clear()
        return super(Alarm, self).clear(*args, **kw)

    security.protect('set', 'Override')
    def set(self, value, *args):
        source = 'Alarm "set" adapter(PhWin)'
        timestamp = time.time()
        context = 'Invocation: "set(%s)"' % (value,)
        if value: 
            self.trigger(source, timestamp, context)
        else: 
            self.clear(source, timestamp, context)

    security.protect('get', 'View')
    def get(self, *args):
        return self.__in_alarm.isSet()
