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
import string
from mpx.lib.node import as_node,as_node_url,is_node
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.service import ServiceNode
from mpx.lib import msglog

class LogHelper(ServiceNode):
    def __init__(self):
        ServiceNode.__init__(self)
        self.column_names = ()  # Must be lazily initialized.
        return
    def configure(self, config):
        ServiceNode.configure(self,config)
        set_attribute(self,'default_log','/services/logger/local_view',config)
        set_attribute(self,'use_cache', 1, config, int)
        set_attribute(self,'debug', 1, config, int)
        return
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self,'default_log',config,as_node_url)
        get_attribute(self,'use_cache', config)
        get_attribute(self,'debug', config)
        return config
    def get(self, skipCache=0):
        return 'LogHelper Version 1.0'
    def start(self):
        return ServiceNode.start(self)
    ##
    # Generic get slice.  Uses internal (future) caches to keep the
    # specific data.
    # if log_name is not specified, then use default from configuration
    def get_slice_on_interval(self, column, start, end, interval, log_name=None):
        if log_name == None:
            log_name = self.default_log
        log = as_node(log_name)
        if not self.column_names:
            self.column_names = log.get_column_names()
        log_object = log.log
        if hasattr(log_object,'_log'):
            log_object = log_object._log
        file = open(log_object.filename,'r')
        try:
            start_seek,end_seek=log_object._get_slice_boundries(file,column,
                                                                start,end)
        except IndexError:
            start_seek = 0
            end_seek = 0
        file.seek(start_seek)
        lines = [string.join(self.column_names,',')]
        previous_time = start - interval
        if start_seek == end_seek:
            while start < end:
                lines.append(str(start) + 
                             (',' * (len(self.column_names) - 1)))
                start += interval
        else:
            while file.tell() < end_seek:
                line = file.readline()[1:-2]
                values = string.split(line, ', ')[0:-1]
                timestamp = float(values[0])
                this_time = previous_time + interval
                while this_time < timestamp:
                    lines.append(str(this_time) + 
                                 (',' * (len(self.column_names) - 1)))
                    this_time += interval
                previous_time = this_time - interval
                if timestamp == this_time:
                    previous_time = timestamp
                    lines.append(string.join(values,','))
        return string.join(lines,'\n')
