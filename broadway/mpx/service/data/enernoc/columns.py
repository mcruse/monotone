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
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.service.logger.periodic_column import PeriodicColumn
from mpx.service.logger.periodic_delta_column import PeriodicDeltaColumn


class ChannelAttrsColumn(PeriodicColumn):
    attr_names = [('data_stream_name', str, 'data_stream_name'),
                  ('measure', str, 'measure'),
                  ('commodity', str, 'commodity'),
                  ('measurement_type', str, 'measurement_type'),
                  ('uom', str, 'uom'),
                  ]
    def configure(self, cd):
        super(ChannelAttrsColumn, self).configure(cd)
        for attr_name, conv, def_val in self.attr_names:
            set_attribute(self, attr_name, def_val, cd, conv)
        return
    
    def configuration(self):
        cd = super(ChannelAttrsColumn, self).configuration()
        for attr_name, conv, def_val in self.attr_names:
            get_attribute(self, attr_name, cd, conv)
        return cd
    
class ChannelAttrsDeltaColumn(PeriodicDeltaColumn):
    attr_names = [('data_stream_name', str, 'data_stream_name'),
                  ('measure', str, 'measure'),
                  ('commodity', str, 'commodity'),
                  ('measurement_type', str, 'measurement_type'),
                  ('uom', str, 'uom'),
                  ]
    def configure(self, cd):
        super(ChannelAttrsDeltaColumn, self).configure(cd)
        for attr_name, conv, def_val in self.attr_names:
            set_attribute(self, attr_name, def_val, cd, conv)
        return
    
    def configuration(self):
        cd = super(ChannelAttrsDeltaColumn, self).configuration()
        for attr_name, conv, def_val in self.attr_names:
            get_attribute(self, attr_name, cd, conv)
        return cd
    
