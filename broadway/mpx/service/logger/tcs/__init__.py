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
import types
from mpx.service.logger.group_log import GroupLog,ChangedPointGroup
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED

def _device_sort(d1,d2):
    return d1.address - d2.address

class DeviceSet(GroupLog):
    def __init__(self):
        self._devices = []
        GroupLog.__init__(self)
    def _sort_groups(self):
        self._groups.sort(_device_sort)
    def _get_type(self,seq,group,index):
        return self._configs[seq][group]['types'][int(index)]
    def _expand_names(self,seq,group,data):
        if type(data) != types.DictType:
            return data
        expanded = {}
        for key in data.keys():
            data_type = self._get_type(seq,group,key)
            expanded[self._get_name(seq,group,key)] = {'value':data[key],
                                                       'type':data_type}
        return expanded
    def devices(self):
        return self._groups
class Device(ChangedPointGroup):
    def __init__(self):
        ChangedPointGroup.__init__(self)
        self.meta['types'] = []
    def configure(self,config):
        ChangedPointGroup.configure(self,config)
        set_attribute(self,'type','',config)
        set_attribute(self,'address',REQUIRED,config,int)
        for point in self.points:
            self.meta['types'].append(point['type'])
        return
    def configuration(self):
        config = ChangedPointGroup.configuration(self)
        get_attribute(self,'type',config)
        get_attribute(self,'address',config,str)
        return config
