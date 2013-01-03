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
import gdutil

class IOPointMixin:
    def __init__(self):
        self.lh = None       # Initialize line-handler to None
        self.po_obj = None   # Initialize protocol object to None
        self.value = None
    #
    def setLineHandler(self, lh):
        self.lh = lh
    #
    def setProtocolObject(self, po_obj):
        self.po_obj = po_obj

##
# Note: Classes which inherit from IOInputPointMixin, AnalogInputPointMixin, or
#       DigitalInputPointMixin should provide a _getValue method which takes
#       the following parameters:
#          linehandler, protocol_object
#       and returns either a new value, raises an exception, or returns  None
#       if no value could get read or raises for some reason.
class IOInputPointMixin:
    def __init__(self):
        IOPointMixin.__init__(self)

        self.last_read_time = 0
        self.refresh_secs   = 5   # The number of seconds which an input value can be cached (0 for None).
    #
    def _setValue(self, new_value):
        self.value = new_value
        self.last_read_time = gdutil.get_time()
    #
    def get(self, skipCache=0):
        doget = 0
        if skipCache:
            doget = 1
        if self.last_read_time == 0:
            doget = 1
        if not doget:
            if self.refresh_secs == 0:
                doget = 1
        if not doget:
            curtime = gdutil.get_time()
            if curtime - self.last_read_time > self.refresh_secs:
                # Looks like our value needs to be refreshed.
                doget = 1
        if doget:
            new_val = self._getValue(self.lh, self.po_obj)
            #
            if not new_val is None:
                self.value = new_val
                self.last_read_time = gdutil.get_time()
            return new_val
        return self.value
        
##
# Note: Classes which inherit from IOOutputPointMixin, AnalogOutputPointMixin, or
#       DigitalOutputPointMixin should provide a _setValue method which takes
#       the following parameters:
#          linehandler, protocol_object, value
#       and raises an exception if the value could not be set for some reason.
class IOOutputPointMixin:
    def set(self, value):
        self.value = value
        return self._setValue(self.lh, self.po_obj, value)

class AnalogInputPointMixin(IOInputPointMixin):
    pass

class AnalogOutputPointMixin(IOOutputPointMixin):
    pass

class DigitalInputPointMixin(IOInputPointMixin):
    pass

class DigitalOutputPointMixin(IOOutputPointMixin):
    pass
