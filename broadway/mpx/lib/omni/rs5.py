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
# This code was generated from File: mpx/lib/omni/rs5.proto .
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


class readmeterreq(gd.BaseGDClass):
    def __init__(self):
        gd.BaseGDClass.__init__(self)
        #
        self.name = 'readmeterreq'
        self._isFixed = 1
        self._width = 16
        self._num_items = 11
        self._isPackCompatible = 0
        self._packSpec = None
        #
        # Code to create item objects.
        self.items = []
        #
        x = gd.IntItem(name="wake_up1", width=1, value=0xFE, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="wake_up2", width=1, value=0xFE, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="stx1", width=1, value=0x68, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.BufferItem(name="addr", isfixedwidth=1, width=6, ispack=0, widthispack=0, type="fbuffer")
        self.items.append(x)
        #
        x = gd.IntItem(name="stx2", width=1, value=0x68, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="opcode", width=1, value=0x01, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="len", width=1, value=0x02, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="di_b1", width=1, value=0x52, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="di_b2", width=1, value=0x14, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="cs", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="etx", width=1, value=0x16, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)


class readmeterres(gd.BaseGDClass):
    def __init__(self):
        gd.BaseGDClass.__init__(self)
        #
        self.name = 'readmeterres'
        self._isFixed = 1
        self._width = 38
        self._num_items = 9
        self._isPackCompatible = 0
        self._packSpec = None
        #
        # Code to create item objects.
        self.items = []
        #
        x = gd.BufferItem(name="addr",isfixedwidth=1, width=6, ispack=0, widthispack=0, type="fbuffer")
        self.items.append(x)
        #
        x = gd.IntItem(name="stx2", width=1, value=0x68, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="opcode", width=1, value=0x81, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="len", width=1, value=0x1B, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="di_b1", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="di_b2", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.BufferItem(name="data", isfixedwidth=1, width=25, ispack=0, widthispack=0, type="fbuffer")
        self.items.append(x)
        #
        x = gd.IntItem(name="cs", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)
        #
        x = gd.IntItem(name="etx", width=1, value=0x16, packspec="<B", ispack=1, widthispack=0, type="uint8")
        self.items.append(x)


