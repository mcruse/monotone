"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute

class LinearAdjustor(Translator):
    ##
    # @param config the configuration dictionary
    # @key multiplier the multiplier to use
    # @default 1.0
    # @key offset the offset to use
    # @default 0.0
    # @note the get method uses the function
    # y = mx + b <br>x is the multipler and b is the 
    # offset
    def configure(self,config):        
        Translator.configure(self,config)
        set_attribute(self,'multiplier',1.0,config,float)        
        set_attribute(self,'offset',0.0,config,float)  
    ##
    # @returns the configuration dictionary
    def configuration(self):
        config = Translator.configuration(self)
        get_attribute(self,'multiplier',config,str)
        get_attribute(self,'offset',config,str)
        return config
    def _mutate(self):
        if hasattr(self.ion, 'set'):
            self.__class__ = SettableLinearAdjustor
        else:
            self.__class__ = GettableLinearAdjustor

##
# Translator that translates it's parents value
# <b>y = mx + b</b><br>
# x = the multiplier.
class GettableLinearAdjustor(LinearAdjustor):
    ##
    # @return y = mx + b <br>x being the multiplier and 
    # b being the offset
    def get(self, skipCache=0):
        value = self.parent.get()
        rtValue = (value*self.multiplier) + self.offset
        return rtValue
class SettableLinearAdjustor(GettableLinearAdjustor):
    ##
    # sets the value as (value - offsett)/multiplier
    def set(self,value):
        return self.parent.set((value-self.offset)/self.multiplier)

##
# @return an instaniated LinearAdjustor object
def factory():
    return LinearAdjustor()
