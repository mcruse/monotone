"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
# fsg_nodes.py: Definitions of node classes for FSG Demo at EEI
#

from mpx.lib.configure import stripped_str
from mpx.lib.node import NodeDecorator

class FSG_FormatterColumnDecorator(NodeDecorator):
    _PREFIX = 'fsgfmt_'
    ATTR_NAMES = [('fsgfmt_channel_name',str,''),
                  ('fsgfmt_uom',str,''),
                  ('fsgfmt_meastype',str,''),
                  ('fsgfmt_Delta',str,'N'),
                  ('fsgfmt_Totalized',str,'N'),
                  ('fsgfmt_key',int,'0'),
                  ]
    def configure(self, cd):
        NodeDecorator.configure(self, cd)
        for attr_name,conv,def_val in self.ATTR_NAMES:
            self.set_attribute(attr_name, def_val, cd, conv)
        return
    def configuration(self):
        cd = NodeDecorator.configuration(self)
        for attr_name,conv,def_val in self.ATTR_NAMES:
            self.get_attribute(attr_name, cd, conv)
        return cd

#
# Soon to be DEPRECATED:
#

import types, time, array, struct, os, StringIO, threading as _threading, urllib as _urllib
from mpx import properties
from mpx.lib import msglog
from mpx.lib.configure import get_attribute, set_attribute
from mpx.lib.exceptions import ENoSuchName, ETimeout, ENoData, EConnectionError
from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.service.logger.periodic_column import PeriodicColumn
from mpx.service.logger.periodic_delta_column import PeriodicDeltaColumn
from mpx.service.alarms.trigger import ComparisonTrigger

class ChannelAttrsColumn(PeriodicColumn):
    attr_names = [('channel_name',str,''),
                  ('uom',str,''),
                  ('meastype',str,''),
                  ('Delta',str,'N'),
                  ('Totalized',str,'N'),
                  ('key',int,'0'),
                  ]
    def configure(self, cd):
        PeriodicColumn.configure(self, cd)
        for attr_name,conv,def_val in self.attr_names:
            set_attribute(self, attr_name, def_val, cd, conv)
        return
    def configuration(self):
        cd = PeriodicColumn.configuration(self)
        for attr_name,conv,def_val in self.attr_names:
            get_attribute(self, attr_name, cd, conv)
        return cd
    
class ChannelAttrsDeltaColumn(PeriodicDeltaColumn):
    attr_names = [('channel_name',str,''),
                  ('uom',str,''),
                  ('meastype',str,''),
                  ('Delta',str,'N'),
                  ('Totalized',str,'N'),
                  ('key',int,'0'),
                  ]
    def configure(self, cd):
        PeriodicDeltaColumn.configure(self, cd)
        for attr_name,conv,def_val in self.attr_names:
            set_attribute(self, attr_name, def_val, cd, conv)
        return
    def configuration(self):
        cd = PeriodicDeltaColumn.configuration(self)
        for attr_name,conv,def_val in self.attr_names:
            get_attribute(self, attr_name, cd, conv)
        return cd
    
class FsgComparisonTrigger(ComparisonTrigger):
    def configure(self, cd):
        ComparisonTrigger.configure(self,cd)
        set_attribute(self, 'key','DefaultTriggerKey',cd)
        return
    def configuration(self):
        cd = ComparisonTrigger.configuration(self)
        get_attribute(self, 'key',cd)
        return cd
    
