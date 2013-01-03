"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
from _translator import Translator

##
# ION that translates degrees Fahrenheit IONs to degrees Celsius IONs.
class CfromF(Translator):
    def _mutate(self):
        if hasattr(self.ion, 'set'):
            self.__class__ = SettableCfromF
        else:
            self.__class__ = GettableCfromF
class GettableCfromF(CfromF):    
    def get(self, skipCache=0):
        return ((self.ion.get(skipCache)-32.0)*5.0)/9.0
class SettableCfromF(GettableCfromF):
    def set(self, value, asyncOK=1):
        return self.ion.set(((value*9.0)/5.0)+32.0,asyncOK)

def factory():
    return CfromF()
