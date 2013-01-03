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
from mpx.lib.eventdispatch import Event
from mpx.lib.node import as_node
from mpx.componentry import implements
from mpx.componentry.interfaces import IPickles

class EventSource(object):
    implements(IPickles)
    def __init__(self, source):
        self.__state = None
        self.__source = source
    def __getstate__(self):
        if self.__state is None:
            state = {}
            source = self.__source
            if isinstance(source, EventSource):
                state['type'] = 'EventSource'
                state['source'] = source
            elif isinstance(source, Event):
                state['type'] = 'Event'
                state['GUID'] = source.GUID
                state['origin'] = source.origin
            else:
                state['type'] = 'Node'
                state['URL'] = source.url
                state['origin'] = Event.LOCALORIGIN
                state['config'] = source.configuration()
            self.__state = state
        return self.__state
    def __setstate__(self, state):
        self.__source = None
        self.__state = state
    def __call__(self, local=False):
        if self.__source is None:
            state = self.__state
            if local:
                state["origin"] = Event.LOCALORIGIN
            if state['type'] == 'EventSource':
                self.__source = state['source']
            elif state['type'] == 'Event':
                self.__source = Event.get_event(state['GUID'])
                if local and not self.__source.is_local():
                    message = "%s overriding source %s origin to local."
                    msglog.warn(message % (self, self.__source))
                    self.__source.set_local()
            elif state['origin'] == Event.LOCALORIGIN:
                self.__source = as_node(state['URL'])
            else:
                self.__dict__.update(state['config'])
                self.__source = self
        return self.__source

