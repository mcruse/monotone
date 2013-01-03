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
"""
    Contains class definitions helpful to other modules within this package.
"""

class AttrNode(object):

    def from_tuple(name_value):
        return AttrNode(name_value[0], name_value[1])
    from_tuple = staticmethod(from_tuple)

    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.localName = name
        self.prefix = ''
        self.namespaceURI = ''

class AttrNodeMap(dict):
    
    def from_items(name_value_list):
        attrs = map(AttrNode.from_tuple, name_value_list)
        return AttrNodeMap([(attr.name, attr) for attr in attrs if attr.value is not None])
    from_items = staticmethod(from_items)

    def from_dict(dictionary):
        return AttrNodeMap.from_items(dictionary.items())
    from_dict = staticmethod(from_dict)

    def item(self, index):
        return self[index]
    
    def __get_length(self):
        return len(self)
    length = property(__get_length)


