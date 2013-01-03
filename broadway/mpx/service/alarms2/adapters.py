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
# Refactor 2/11/2007
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.neode.node import ConfigurableNode
from mpx.lib.eventdispatch import Event
from mpx.lib.eventdispatch.adapters import EventSource
from mpx.lib.eventdispatch.dispatcher import Dispatcher
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.interfaces import IPickles
from mpx.componentry.bases import OrderedCollection
from mpx.componentry.bases import FieldStorage
from mpx.componentry.bases import FieldStorageCollection
from mpx.service.alarms2.interfaces import IAlarmManager
from mpx.service.alarms2.interfaces import IAlarm
from mpx.service.alarms2.interfaces import IAlarmEvent
from mpx.service.alarms2.interfaces import IStateEvent
from mpx.service.alarms2.interfaces import IActionEvent
from mpx.service.alarms2.interfaces import IFlatAlarmManager
from mpx.componentry.security.interfaces import ISecurityContext

class AlarmEventSecurityContext(object):
    implements(ISecurityContext)
    adapts(IAlarmEvent)
    def __init__(self, event):
        self.event = event
    def get_context(self):
        return self.event.source
    def get_context_url(self):
        return self.get_context().url
    url = property(get_context_url)

register_adapter(AlarmEventSecurityContext)

class ActionEventPickler(object):
    implements(IPickles)
    adapts(IActionEvent)
    def __init__(self, action):
        self.action = action
        self.state = None
    def __getstate__(self):
        if self.action is None:
            return self.state
        action = self.action
        if not hasattr(action, '__picklestate'):
            state = {'class': type(action),
                     'GUID': action.GUID,
                     'source': EventSource(action.source)}
            state['args'] = (action.timestamp, action.actuatorstr,
                             action.context, action.origin, action.GUID)
            action.__picklestate = state
        return action.__picklestate
    def __setstate__(self, state):
        self.action = None
        self.state = state
    def __call__(self, local=False):
        if self.action is None:
            try: 
                self.action = Event.get_event(self.state.get('GUID'))
            except KeyError:
                args = self.state.get("args", ())
                source = self.state.get("source")(local)
                self.action = self.state.get('class')(source, *args)
        return self.action
    def __str__(self):
        return 'ActionEventPickler(%s)' % str(self.action)

register_adapter(ActionEventPickler)

class StateEventPickler(object):
    implements(IPickles)
    adapts(IStateEvent)

    def __init__(self, stateevent):
        self.event = stateevent
        self.state = None
    def __getstate__(self):
        if self.event is None:
            return self.state
        event = self.event
        if not hasattr(event, '__picklestate'):
            state = {'class': type(event),
                     'GUID': event.GUID,
                     'source': EventSource(event.source),
                     'action': IPickles(event.action),
                     'origin': event.origin}
            event.__picklestate = state
        return event.__picklestate
    def __setstate__(self, state):
        self.event = None
        self.state = state
    def __call__(self, local=False):
        if self.event is None:
            try: 
                self.event = Event.get_event(self.state['GUID'])
            except KeyError:
                guid = self.state.get('GUID')
                source = self.state.get('source')(local)
                action = self.state.get('action')(local)
                origin = None if local else self.state.get('origin')
                event_class = self.state.get('class')
                self.event = event_class(source, action, origin, guid)
        return self.event
    def __str__(self):
        return 'StateEventPickler(%s)' % str(self.event)
register_adapter(StateEventPickler)

class AlarmEventPickler(object):
    implements(IPickles)
    adapts(IAlarmEvent)

    def __init__(self, alarmevent):
        self.event = alarmevent
        self.state = None
        super(AlarmEventPickler, self).__init__()
    def __getstate__(self):
        if self.event is None:
            return self.state
        if not hasattr(self.event, '__picklestate'):
            state = {'class': type(self.event),
                     'GUID': self.event.GUID,
                     'source': EventSource(self.event.source),
                     'origin': self.event.origin,
                     'history': []}
            self.event.__picklestate = state
        state = self.event.__picklestate
        history = self.event.get_history()
        if self.event.current_event is not None:
            history.append(self.event.current_event)
        knownevents = len(state['history'])
        state['history'].extend(map(IPickles, history[knownevents:]))
        return state
    def __setstate__(self, state):
        self.event = None
        self.state = state
    def __call__(self, local=False):
        """
            Get Event instance from pickle adapter.  
            
            If pickled event does not match existing event, 
            instantiate one using class.
            
            If optional parameter 'local' provided and true, 
            override event's 'origin' with None so current 
            LOCALORIGIN is used.  This picks up IP address 
            changes 
            
        """
        if self.event is None:
            try: 
                self.event = Event.get_event(self.state['GUID'])
            except KeyError:
                guid = self.state.get('GUID')
                source = self.state.get('source')(local)
                origin = None if local else self.state.get('origin')
                event_class = self.state.get('class')
                self.event = event_class(source, origin, guid)
                self.event.message('created by AlarmEventPickler.__call__().')
            else: 
                self.event.message('used by AlarmEventPickler.__call__().')
            history = self.state['history']
            self.event.synchronize([IPickles(evt)(local) for evt in history])
        return self.event
    def __str__(self):
        return 'AlarmEventPickler(%s)' % str(self.event)

register_adapter(AlarmEventPickler)

class AlarmPickler(object):
    implements(IPickles)
    adapts(IAlarm)

    def __init__(self, alarm):
        self.alarm = alarm
    def __getstate__(self):
        alarm = self.alarm
        if not hasattr(alarm, '__picklestate'):
            state = {'class': type(alarm),
                     'url': alarm.url,
                     'config': alarm.configuration()}
            alarm.__picklestate = state
        state = alarm.__picklestate
        state['events'] = map(IPickles, alarm.get_events())
        return state
    def __setstate__(self, state):
        self.alarm = None
        self.state = state
    def __call__(self, local=False):
        if self.alarm is None:
            try: 
                self.alarm = as_node(self.state['url'])
            except KeyError: 
                self.alarm = self.state.get('class')()
            config = self.state['config']
            parent = as_node(config['parent'])
            config.setdefault('nodespace', parent.nodespace)
            self.alarm.configure(config)
            self.alarm.start()
            events = [IPickles(evt)(local) for evt in self.state['events']]
            msglog.log('broadway', msglog.types.WARN,
                       'Deprecated AlarmPickler used to unpickle %s.' % self.alarm.name)
        return self.alarm

class AlarmNodePickler(object):
    implements(IPickles)
    adapts(IAlarm)

    def __init__(self, alarm):
        self.alarm = alarm
    def __getstate__(self):
        alarm = self.alarm
        if not hasattr(alarm, '__picklestate'):
            state = {'class': type(alarm),
                     'url': alarm.url,
                     'config': alarm.configuration()}
            alarm.__picklestate = state
        state = alarm.__picklestate
        return state
    def __setstate__(self, state):
        self.alarm = None
        self.state = state
    def __call__(self, local=False):
        if self.alarm is None:
            try: 
                self.alarm = as_node(self.state['url'])
            except KeyError: 
                self.alarm = self.state.get('class')()
            config = self.state['config']
            parent = as_node(config['parent'])
            config.setdefault('nodespace', parent.nodespace)
            self.alarm.configure(config)
            self.alarm.start()
        return self.alarm

register_adapter(AlarmNodePickler)

class FlatAlarmManager(OrderedCollection):
    implements(IFlatAlarmManager)
    adapts(IAlarmManager)
    def __init__(self, manager):
        self.manager = manager
        alarms = self.manager.get_alarms()
        events = []
        for alarm in alarms:
            events.extend(alarm.get_events())
        super(FlatAlarmManager, self).__init__(events)
    def get_alarm(self,name):
        return self.manager.get_alarm(name)
    def get_alarms(self):
        return self.return_type()(self.manager.get_alarms())
    def get_alarm_events(self, name):
        return self.return_type()(self.get_alarm(name).get_events())
    def return_type(self):
        return OrderedCollection
register_adapter(FlatAlarmManager, [IAlarmManager], IFlatAlarmManager)

class AlarmCollection(OrderedCollection):
    # implements(mpx.componentry.interfaces.IOrderedCollection)
    adapts(IAlarmManager)

    def __init__(self,manager):
        super(AlarmCollection, self).__init__(manager.get_alarms())
    def return_type(self): return OrderedCollection

register_adapter(AlarmCollection)

class AlarmEventCollection(OrderedCollection):
    # implements(mpx.componentry.interfaces.IOrderedCollection)
    adapts(IAlarm)

    def __init__(self,alarm):
        super(AlarmEventCollection, self).__init__(alarm.get_events())
    def return_type(self): return OrderedCollection

register_adapter(AlarmEventCollection)

class AlarmEventFieldStorage(FieldStorage):
    # implements(IFieldStorage)
    adapts(IAlarmEvent)
    fields = ['source', 'current_event', 'state', 'history']

    def __init__(self, event):
        self.event = event
        super(AlarmEventFieldStorage, self).__init__()

    def _populate(self, dictionary):
        for name in dictionary.keys():
            dictionary[name] = str(getattr(self.event, name))
        return

    def get_field_value(self, name):
        return str(getattr(self.event, name))

register_adapter(AlarmEventFieldStorage)
