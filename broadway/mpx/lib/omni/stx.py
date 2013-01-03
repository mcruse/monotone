"""
Copyright (C) 2011 Cisco Systems

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
# This code was generated from File: mpx/lib/omni/stx.proto .
# Please modify the original source rather than this generated code.

didimport = 0
try:
    import mpx.lib.genericdriver.gdhelpers as gd
    didimport = 1
except:
    pass
if not didimport:
    try:
        import gdhelpers as gd
        didimport = 1
    except:
        pass
if not didimport:
    raise "Error: Could not import gdhelpers."


class start_byte(gd.BaseGDClass):
    def __init__(self):
        gd.BaseGDClass.__init__(self)
        #
        self.name = 'start_byte'
        self._isFixed = 1
        self._width = 1
        self._num_items = 1
        self._isPackCompatible = 1
        self._packSpec = '<B'
        #
        # Code to create item objects.
        self.items = []
        #
        x = gd.IntItem(name="stx1", width=1, value=0x68, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)


