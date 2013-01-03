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
import string
import time
from mpx.lib.ifconfig import ip_address
from mpx.lib.configure import set_attribute,get_attribute
from mpx.service.data import Formatter
from mpx.service.data.ftp_transporter import FTPTransporter

class _ColumnFormatter:
    def __init__(self,column,time_function=time.gmtime):
        self._column = column
        self._time_function = time_function
        self._entries = []
    def add_entry(self,entry):
        # [timestamp,value,count]
        self._entries.append(self._column.values(entry))
    def _date(self,ts):
        return time.strftime('%m/%d/%y,%H:%M:00',self._time_function(ts))
    def output(self):
        meter_desc = self._column.meter_description
        account = self._column.account
        meter_number = self._column.meter_number
        units = self._column.units
        type = self._column.type
        register = self._column.register
        output = []
        for entry in self._entries:
            timestamp = self._date(entry[0])
            value = entry[1]
            count = entry[2]
            output.append(string.join([timestamp,meter_desc,account,
                                       meter_number,units,str(value),
                                       str(count),type,str(register)],','))
        return string.join(output,'\n')
class EBidFormatter(Formatter):
    def start(self):
        self._columns = []
        self.time_function = self.parent.time_function
        columns = self.parent.parent.parent.get_child('columns')
        for child in columns.children_nodes():
            if child.name != 'timestamp':
                self._columns.append(child)
        Formatter.start(self)
    def format(self,data):
        formatters = []
        for column in self._columns:
            formatters.append(_ColumnFormatter(column,self.time_function))
        for entry in data:
            for formatter in formatters:
                formatter.add_entry(entry)
        output = ('#Date,Time,MeterDesc,Account#,Meter#,' + 
                  'Units,Value,Count,Type,RegisterNo')
        for formatter in formatters:
            output += '\n' + formatter.output()
        return output + '\n'
##
# Overrides regular FTP's filename.
class Transporter(FTPTransporter):
    def configure(self,config):
        set_attribute(self,'serial','000300',config)
        set_attribute(self,'interface','eth0',config)
        FTPTransporter.configure(self,config)
    def configuration(self):
        config = FTPTransporter.configuration(self)
        get_attribute(self,'interface',config)
        get_attribute(self,'serial',config)
        return config
    def _generate_filename(self,filenumber=None):
        ip = string.replace(ip_address(self.interface),'.','-')
        serial = self.serial
        ts = self.parent.scheduled_time()
        date = time.strftime('%m%d%Y_%H-%M-%S',time.gmtime(ts))
        return serial + '_' + ip + '_' + date + self.file_suffix


