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
# @idea Allow for a DeviceManagerParamaters class that provides for tweaking
#       defaults.
# @idea Dynamically created DeviceMonitors are named as_string of UID.

from mpx.lib.node import CompositeNode

from udi import UniqueDeviceIdentifier
from util import import_factory

class DeviceMonitor(CompositeNode):
    udi_class_name = 'mpx.service.device_manager.udi.UniqueDeviceIdentifier'
    def __init__(self):
        CompositeNode.__init__(self)
        self.udi_class = import_factory(self.udi_class_name)
        self.udi = None
        self._last_notification_class = None.__class__
        return
    def configure(self, config):
        CompositeNode.configure(self, config)
        # Deal with UDI voodoo.  Basically, if use param is a dict,
        # then use the DM to assign an instance.  If it's a UDI, don't.
        self.device_manger = self.parent.device_manger
        # UDI configuration is a bit magical.  If this node is dynamically
        # instanciated, then the UDI exists AND we  could be being called by
        # the DeviceManager in a manner that is not conducive to reentrancy...
        udi = config.get('udi', None)
        if udi is not None and self.udi is None:
            if isinstance(udi, UniqueDeviceIdentifier):
                # Implies dynamic configuration, the UDI exists.
                # @note Dynamic Monitor creation occurs in the DeviceManager
                #       and the implementation is not conducive reentering
                #       the DeviceManager (think deadlock).
                self.udi = udi
            else:
                # Implies static configuration.  *The* UDI should not exist, or
                # at least it should not reference a monitor yet.  Create *the*
                # UDI and associate it with this monitor.
                assert isinstance(udi, dict)
                self.udi = udi
                self.device_manger.register_monitor(self)
                self.udi = self.device_manger.udi_from_udi(udi)
        return
    def configuration(self):
        config = CompositeNode.configuration(self)
        config['udi'] = dict(self.udi)
        return config
    def get(self, skipCache=0):
        return issubclass(self._last_notification_class,Exception)
    def notify_exception(self, e):
        self._last_notification_class = e.__class__
        return
    def notify_success(self):
        self._last_notification_class = None.__class__
        return
