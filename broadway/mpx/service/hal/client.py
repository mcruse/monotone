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
"""
mpx/service/hal/client.py: Superclass Client provides event consumption features 
to subclasses. Assumes that parent is instance of Manager subclass.
"""

from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.exceptions import ENotImplemented, EInvalidValue, EAlreadyRunning
from mpx.lib.event import EventConsumerMixin

class Client(CompositeNode, EventConsumerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventConsumerMixin.__init__(self, self._handle_event, self._handle_exception)
        self._event_handlers = {} # map of event class to handler method
        self._running = 0
    def configure(self,config):
        set_attribute(self,'description','',config)
        CompositeNode.configure(self,config)
    def configuration(self,config=None):
        config = CompositeNode.configuration(self,config)
        get_attribute(self,'description',config)
        return config
    def start(self):
        if self._running == 0:
            self._running = 1
            for event_class in self._event_handlers.keys():
                self.parent.event_subscribe(self, event_class)
        else:
            msglog.log('broadway', msglog.types.WARN, \
                       'Instance of %s is already running.' % str(self.__class__))
        CompositeNode.start(self)
    def stop(self):
        CompositeNode.stop(self)
        self._running = 0
        for event_class in self._event_handlers.keys():
            try:
                self.parent.event_unsubscribe(self, event_class)
            except:
                pass
    # Subclass calls this method in overridden start(), to register callbacks for
    # instances of desired event classes:
    def register_event(self, event_class, callback):
        self._event_handlers[event_class] = callback # note: writes over any previous entry w/same key
        if self._running != 0:
            self.parent.event_subscribe(self, event_class)
    def unregister_event(self, event_class):
        if self._running != 0:
            self.parent.event_unsubscribe(self, event_class)
        del self._event_handlers[event_class]
    def _handle_event(self, event):
        callback = None
        if self._event_handlers.has_key(event.__class__):
            callback = self._event_handlers[event.__class__]
        else: # else, search for event subclass matches:
            for event_class in self._event_handlers.keys():
                if isinstance(event, event_class):
                    callback = self._event_handlers[event_class]
                    break
        if callback is None:
            msglog.log('broadway', msglog.types.ERR, \
                       'Instance of unhandled Event subclass (%s) received.' \
                       % str(event_class.__class__))
        else:
            callback(event)
    def _handle_exception(self, exc):
        msglog.exception()
