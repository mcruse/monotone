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
mpx/service/hal/alarms/__init__.py: Defines alarms.Manager subclass.
"""
from mpx.lib.exceptions import ENotImplemented,EInvalidValue
from mpx.service.hal.manager import Manager as _Manager
from mpx.lib.event import Event


class Alarm:
    FIELD_NAMES = ['id','type','source','data','state', 'timestamp']
    def __init__(self, *args, **keywords):
        if (not args and not keywords) or (args and not keywords):
            self.from_list(args)
        elif keywords and not args:
            self.from_dictionary(keywords)
        else:
            raise EInvalidValue('keywords',keywords,
                                'Alarm must be initialized with '
                                'either keywords or args, not both.')
    def field_names(self):
        return self.FIELD_NAMES[:]
    def as_list(self):
        answer = []
        for n in self.FIELD_NAMES:
            answer.append(getattr(self, n))
        return answer
    def from_list(self,values):
        for index in range(len(self.FIELD_NAMES)):
            value = None
            if index < len(values):
                value = values[index]
            setattr(self, self.FIELD_NAMES[index], value)
    def as_dictionary(self):
        dict = {}
        values = self.as_list()
        names = self.field_names()
        for index in range(0,len(names)):
            dict[names[index]] = values[index]
        return dict
    def from_dictionary(self,dict):
        values = []
        for name in self.field_names():
            if dict.has_key(name):
                values.append(dict[name])
            else:
                values.append(None)
        self.from_list(values)
    def __str__(self):
        return str(self.as_dictionary())
class NewAlarmsEvent(Event):
    def __init__(self, client, new_alarms):
        self.new_alarms = new_alarms
        Event.__init__(self, source=client)
    def __getitem__(self,index):
        return self.new_alarms[index]
    def alarms(self):
        return self.new_alarms
    
class Manager(_Manager):
    def __init__(self):
        _Manager.__init__(self)
    # @param alarms list of 1 to N Alarm objects
    def put_alarms(self, alarms):
        self.event_generate(NewAlarmsEvent(self, alarms))
    
    
    
    
