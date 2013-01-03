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
# Add MeterMail Archiver specific attributes to a log column.
#

from mpx.lib.configure import stripped_str
from mpx.lib.node import NodeDecorator

class MeterMailColumnDecorator(NodeDecorator):
    _PREFIX = 'mmafmt_'
    def configure(self, cd):
        NodeDecorator.configure(self, cd)
        self.set_attribute('mmafmt_channel_id', self.REQUIRED, cd, str)
        self.set_attribute('mmafmt_channel_label', self.REQUIRED, cd, str)
        self.set_attribute('mmafmt_channel_pos', '', cd, stripped_str)
        return
    def configuration(self):
        cd = NodeDecorator.configuration(self)
        self.get_attribute('mmafmt_channel_id', cd, str)
        self.get_attribute('mmafmt_channel_label', cd, str)
        self.get_attribute('mmafmt_channel_pos', cd, str)
        return cd

#
# DEPRECATED:
#

def MeterMailDecorator():
    from mpx.lib import deprecated
    deprecated("Update configuration to use the MeterMailColumnDecorator.")
    return MeterMailColumnDecorator()

from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.configure import REQUIRED

from mpx.service.logger.periodic_column import PeriodicColumn
from mpx.service.logger.periodic_delta_column import PeriodicDeltaColumn

class MeterMailColumn(PeriodicColumn):
    def __init__(self, *args, **kw):
        from mpx.lib import deprecated
        PeriodicColumn.__init__(self, *args, **kw)
        deprecated("Update configuration to use the MeterMailColumnDecorator.")
        return
    def configure(self, cd):
        PeriodicColumn.configure(self, cd)
        set_attribute(self, 'mmafmt_channel_id', REQUIRED, cd, str)
        set_attribute(self, 'mmafmt_channel_label', REQUIRED, cd, str)
        set_attribute(self, 'mmafmt_channel_pos', '', cd, stripped_str)
        return
    def configuration(self):
        cd = PeriodicColumn.configuration(self)
        get_attribute(self, 'mmafmt_channel_id', cd, str)
        get_attribute(self, 'mmafmt_channel_label', cd, str)
        get_attribute(self, 'mmafmt_channel_pos', cd, str)
        return cd

class MeterMailDeltaColumn(PeriodicDeltaColumn):
    def __init__(self, *args, **kw):
        from mpx.lib import deprecated
        PeriodicDeltaColumn.__init__(self, *args, **kw)
        deprecated("Update configuration to use the MeterMailColumnDecorator.")
        return
    def configure(self, cd):
        PeriodicDeltaColumn.configure(self, cd)
        set_attribute(self, 'mmafmt_channel_id', REQUIRED, cd, str)
        set_attribute(self, 'mmafmt_channel_label', REQUIRED, cd, str)
        set_attribute(self, 'mmafmt_channel_pos', '', cd, stripped_str)
        return
    def configuration(self):
        cd = PeriodicDeltaColumn.configuration(self)
        get_attribute(self, 'mmafmt_channel_id', cd, str)
        get_attribute(self, 'mmafmt_channel_label', cd, str)
        get_attribute(self, 'mmafmt_channel_pos', cd, str)
        return cd
