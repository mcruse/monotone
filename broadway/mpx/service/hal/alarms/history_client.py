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
from mpx.lib.log import TrimmingLog
from mpx.service.hal.client import Client
from mpx.service.hal.alarms import NewAlarmsEvent,Alarm
from mpx.lib.exceptions import ENotStarted
from mpx.lib.configure import get_attribute,set_attribute

class HistoryClient(Client):
    def __init__(self):
        self.__log = None
        self.__log_configured = 0
        Client.__init__(self)
    def configure(self,config):
        set_attribute(self,'minimum_size',100,config,int)
        set_attribute(self,'maximum_size',200,config,int)
        Client.configure(self,config)
    def configuration(self):
        config = Client.configuration(self)
        get_attribute(self,'minimum_size',config,str)
        get_attribute(self,'maximum_size',config,str)
        return config
    def start(self):
        self.__log_configured = 0
        self.__log = TrimmingLog(self.parent.name + '_alarm_history')
        self.register_event(NewAlarmsEvent,self._log_alarms)
        Client.start(self)
    def stop(self):
        self.unregister_event(NewAlarmsEvent)
        Client.stop(self)
        self.__log = None
        self.__log_configured = 0
    def _log_alarms(self,event):
        if self.__log is None:
            raise ENotStarted('History log is None')
        if not self.__log_configured:
            self.__log.configure(event.alarms()[0].field_names(),
                                 self.minimum_size,self.maximum_size)
            self.__log_configured = 1
        for alarm in event:
            self.__log.add_entry(alarm.as_list())
    def newest_alarm_entry(self):
        return self.__log.get_last_record()
    def newest_alarm_values(self):
        return self.__log._get_last_row()
    def newest_alarm(self):
        entry = self.newest_alarm_entry()
        if not entry:
            return None
        alarm = Alarm()
        alarm.from_dictionary(entry)
        return alarm
    def newest_n_alarm_entries(self,count):
        sequence = len(self.__log)
        return self.__log.get_range('_seq',sequence - count,sequence)
    def newest_n_alarm_values(self,count):
        sequence = len(self.__log)
        return self.__log.get_range_values('_seq',sequence - count,sequence)
    def newest_n_alarms(self,count):
        alarms = []
        configs = self.newest_n_alarm_entries(count)
        for config in configs:
            alarm = Alarm()
            alarm.from_dictionary(config)
            alarms.append(alarm)
        return alarms
    def alarm_field_names(self):
        return self.__log.get_column_names()
    
