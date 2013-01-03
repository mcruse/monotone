"""
Copyright (C) 2010 2011 Cisco Systems

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
##
# This module implements the classes related to creating and managing "Unique
# Device Identifiers" used by the "Device Manager" service and the devices that
# cooperate with it.

from util import import_factory

##
# UniqueDeviceIdentifier
class UniqueDeviceIdentifier(dict):
    ##
    # Used by the Device Manager to dynamically instanciate a new Device
    # Monitor.  Derived classes can override this variable to support
    # speciallized device monitors.
    monitor_class_name = 'mpx.service.device_manager.monitor.DeviceMonitor'
    ##
    # UIDs must always return their keys in the same order.  Furthermore,
    # all UIDs must return the "device_class" key first.
    key_map = {
        }
    def extend_key_map(klass, *ordered_keys):
        i_key = len(klass.key_map)
        for key in ordered_keys:
            klass.key_map[key] = i_key
            i_key += 1
        return
    extend_key_map = classmethod(extend_key_map)
    def cmp_keys(klass,k1,k2):
        return cmp(klass.key_map[k1],klass.key_map[k2])
    cmp_keys = classmethod(cmp_keys)
    def sort_keys(klass, *keys):
        keys = list(*keys)
        keys.sort(klass.cmp_keys)
        return keys
    sort_keys = classmethod(sort_keys)
    ##
    # @note Constructor exists because Python 2.2 dict does not support keyword
    #       arguments. (but 2.3 does)
    def __init__(self, arg={}, **kw):
        self.monitor_class = import_factory(self.monitor_class_name,
                                            globals(), locals())
        self.update(arg)
        self.update(kw)
        return
    def keys(self):
        keys = dict.keys(self)
        keys.sort(self.cmp_keys)
        return keys
    def as_text(self):
        elements = []
        for key in self.keys():
            elements.append("%s=%r"%(key,self[key]))
        return ",".join(elements)
    def id(self):
        return id(self)

UniqueDeviceIdentifier.extend_key_map("device_class")

# @fixme move these...

class UniqueRznetIdentifier(UniqueDeviceIdentifier):
    pass

UniqueRznetIdentifier.extend_key_map("port", "unit")
