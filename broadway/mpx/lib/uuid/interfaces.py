"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
# Refactor 2/11/2007
from mpx.componentry import Interface
from mpx.componentry import Attribute

class IUniquelyIdentified(Interface):
    """
        Interface provided by objects which can be identified
        by a GUID.
    """
    identifier = Attribute("""GUID identifying this object.""")

    def get_identifier(obj, default = None, create = False):
        """
            NOTE: Static
            Static method to quickly retreive identifier stored
            on object 'obj' without needing to instantiate and
            operate on an adapter.

            If 'create' is True and object 'obj' does not
            already have an identifier, create one and return.
        """

    def get_identified(uuid, default = None):
        """
            NOTE: Static
            Static method to quickly retreive object associated
            with UUID 'uuid' if one exists.

            If no such object exists within the registry, returns
            default value 'default'.
        """

class IGUIDMarked(Interface):
    GUID = Attribute(
        """
            GUID identifying this object.  This attribute may 
            only be set once, after which point it becomes a 
            read-only attribute.  Although GUID may be an instance 
            of a user-defined object, attribute accessor will convert 
            to string value before returning.
        """)
