"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.ion.modbus.register_cache import RegisterCache
from mpx.lib.modbus.cache_writer import CacheWriter

class CachedION(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.caches = []

    def _define_caches(self, register_maps):
        for map, ttl in register_maps:
            cache = RegisterCache(self, self.address, CacheWriter, ttl)
            for d in map:
                ion = cache.map_register(d.offset, d.count, d.name,
                                         d.read, d.write)
                self._add_child(ion)
            self.caches.append(cache)

    def coil_maps(self):
        return []

    def input_status_maps(self):
        return []

    def holding_register_maps(self):
        # For reverse compatibility.
        result = self.register_maps()
        if result:
            # @fixme Raise deprication warning.
            pass
        return result

    ##
    # Depricate me, you skank.
    def register_maps(self):
        return []

    def input_register_maps(self):
        return []

    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'address', REQUIRED, config, int)
        set_attribute(self, 'line_handler', self.parent, config, as_node)
        self._define_caches(self.holding_register_maps())

    ##
    # @fixme Why is line_handler 'exposed?'
    def configuration(self):
        config = CompositeNode.configuration(self)
        config['line_handler'] = config['parent']
        get_attribute(self, 'address', config, str)
        return config

    def refresh(self):
        for c in self.caches:
            c.refresh()
