"""
Copyright (C) 2002 2005 2010 2011 Cisco Systems

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
import tag
import sequence
import string
from mpx.lib.exceptions import *

class BACnetException(MpxException):
    pass

class BACnetTimeout(BACnetException,ETimeout):
    pass

class BACnetNPDU(BACnetException):
    def __init__(self, npdu, *args, **keywords) :
        largs = [self]
        largs.extend(args)
        apply(BACnetException.__init__, largs, keywords)
        self.npdu = npdu

class BACnetError(BACnetNPDU):
    def __str__(self):
        try:
            if (self.npdu.pdu_type == 5) and (self.npdu.choice == 12):
                if str(self.npdu.data[:4]) == '\x91\x02\x91\x20':
                    return 'UNKNOWN PROPERTY'  #might want to create an unk
            return (
                "BACnetError():\n" +
                (78*"=") + "\n" +
                str(self.npdu) + "\n" +
                (78*"=")
                )
        except:
            return "%s: %r" % (BACnetNPDU.__str__(self), self.npdu.tostring())

class BACnetReject(BACnetNPDU):
    pass

class BACnetAbort(BACnetNPDU):
    pass

class EInvalidTrendData(MpxException):
    pass

class BACnetRpmRarError(BACnetException):
    pass
