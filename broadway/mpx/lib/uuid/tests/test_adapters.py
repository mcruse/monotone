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
from mpx.componentry.tests import verify_class
from mpx.componentry import implements
from mpx.componentry import Interface
from mpx.lib.uuid.interfaces import IUniquelyIdentified
from mpx.lib.uuid.adapters import UniquelyIdentified

assert verify_class(IUniquelyIdentified, UniquelyIdentified), (
    'fails interface verify')

class Test(object):
    implements(Interface)

t1 = Test()
t2 = Test()
adapted1 = IUniquelyIdentified(t1)
adapted2 = IUniquelyIdentified(t2)

id1 = adapted1.identifier
id2 = adapted2.identifier

assert id1 != id2, 'Have same ID!'
assert id1 == adapted1.identifier, 'ID changed!'
del adapted1

adapted1 = IUniquelyIdentified(t1)
assert adapted1.identifier == id1, 'ID changed!'

assert UniquelyIdentified.get_identifier(t1) == id1, 'Static not working.'





