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
from mpx.lib import factory as _factory

class __Chimera:
    def configure(self,config):
        self._factory = config['factory']
        configuration = {'name':config['name'],'parent':config['parent']}
        if config.has_key('attributes'):
            for attribute in config['attributes']:
                configuration[attribute['name']] = attribute['definition']
        self._node = _factory(self._factory)
        self._node.configure(configuration)
    def configuration(self):
        config = self._node.configuration()
        configuration = {'name':config['name'],
                         'parent':config['parent'],
                         'factory':self._factory}
        attributes = []
        for name,definition in config.items():
            if name not in ('name','parent'):
                attributes.append({'name':name,'definition':definition})
        configuration['attributes'] = attributes
        return configuration
    def __getattr__(self,name):
        attr = getattr(self._node,name)
        if callable(attr):
            setattr(self,name,attr)
        return attr

def factory():
    return __Chimera()
