"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
from mpx.lib.exceptions import EIOError

class EModbus(EIOError):
    pass

class EModbusCRC(EModbus):
    def __str__(self):
        try:
            return 'Bad crc slave_address %d; function %d' % (
                self.slave_address, self.function
                )
        except:
            pass
        return 'Bad crc'
    ##
    # @fixme Need to standardize on exception arguments, or enforce explicit
    #        use.  Right now it's a mish-mash.
    def __init__(self, header=None):
        EModbus.__init__(self)
        self.buffer = header
        self.slave_address = None
        self.function = None
        try:
            self.slave_address = header[0]
        except:
            pass
        try:
            self.function = header[1] & 0x7F
        except:
            pass
        return

class EModbusResponse(EModbus):
    known_codes = {1:'1 - Illegal Function',
                   2:'2 - Illegal Data Address',
                   3:'3 - Illegal Data Value',
                   4:'4 - Slave Device Failure',
                   5:'5 - Acknowledge',
                   6:'6 - Slave Device Busy',
                   7:'7 - Negative Acknowledge',
                   8:'8 - Memory Parity Error'}

    def __str__(self):
        if self.known_codes.has_key(self.code):
            error = self.known_codes[self.code]
        else:
            error = '%d - Unknown Exception Code' % self.code
        message = 'EModbusResponse: slave_address %d; function %d; error %s' \
                  % (self.slave_address, self.function, error)
        return message

    def __init__(self,header):
        EModbus.__init__(self,header)
        self.buffer = header
        self.slave_address = header[0]
        self.function = header[1] & 0x7F
        self.code = header[2]

class EModbusMismatch(EModbus):
    pass

def factory(line,header):
    n = 5 - len(header)
    if n:
        line.port.read(header,n,10)
    if line.crc(header):
        raise EModbusCRC, header
    return EModbusResponse(header)
