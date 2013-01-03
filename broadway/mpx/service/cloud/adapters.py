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
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.interfaces import IPickles
from mpx.lib.eventdispatch import Event
from mpx.lib.eventdispatch.adapters import EventSource
from interfaces import ICloudEvent

class CloudEventPickler(object):
    implements(IPickles)
    adapts(ICloudEvent)

    def __init__(self, event):
        self.event = event
    def __getstate__(self):
        state = {}
        state['class'] = type(self.event)
        source = self.event.source
        if not IPickles.providedBy(source):
            source = EventSource(source)
        state['source'] = source
        state['origin'] = self.event.origin
        state['targets'] = self.event.targets
        state['topics'] = self.event.topics
        state['event'] = self.event.event
        state['guid'] = self.event.GUID
        state['portal']=self.event.portal
 
        return state
    def __setstate__(self, state):
        self.state = state
        self.event = None
    def __call__(self):
        if self.event is None:
            state = self.state
            guid = state.get('guid')
            try: cloudevent = Event.get_event(guid)
            except KeyError:
                source = state.get('source')()
                topics = state.get('topics')
                origin = state.get('origin')
                targets = state.get('targets')
                event = state.get('event')
                portal=state.get('portal')
                cloudevent = state.get('class')(source, origin, targets,portal,
                                                topics, event, guid)
            self.event = cloudevent
        return self.event
    def __str__(self):
        return 'CloudEventPickler(%s)' % str(self.event)

register_adapter(CloudEventPickler)
