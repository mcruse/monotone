"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute,get_attribute
from mpx.lib.event import AlarmTriggerEvent,EventConsumerMixin

class LastAlarm(CompositeNode,EventConsumerMixin):
    def __init__(self):
        self._last_alarm = None
        self._started = 0
        CompositeNode.__init__(self)
        EventConsumerMixin.__init__(self,self._alarm_triggered)
    def configure(self, config):
        CompositeNode.configure(self, config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        return config
    def start(self):
        self._pdo = PersistentDataObject(self)
        self._pdo.last_dictionary = None
        self._pdo.load()
        self._started = 1
        self.parent.event_subscribe(self,AlarmTriggerEvent)
        CompositeNode.start(self)
    def stop(self):
        selt._started = 0
        self.parent.cancel(self,AlarmTriggerEvent)
        CompositeNode.stop(self)
    def _alarm_triggered(self, alarm):
        self._last_alarm = alarm
        self._pdo.last_dictionary = alarm.dictionary()
        self._pdo.save()
    def get(self, skipCache=0):
        return self._last_alarm
    def get_dictionary(self):
        return self._pdo.last_dictionary
