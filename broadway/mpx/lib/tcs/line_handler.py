"""
Copyright (C) 2003 2011 Cisco Systems

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
from mpx.lib.exceptions import *
from mpx.lib.tcs import frame, response, command
from mpx.lib.threading import Lock
from mpx.lib import msglog
import device

import time

debug = 0

class TCSLineHandler:
    def __init__(self, port):
        self.lock = Lock()    
        self.port = port
        self.units = {}
        self.connected = 0
        if not port.is_open():
            port.open()

    def discover_children(self, start, stop):
        if debug: print 'discover TCS devices'
        count = 0
        self.units = {}
        for unit in range(start, stop): #make range configurable
            count += 1
            if unit == 248: #special address to skip
                continue
            d = device.TCSDevice(unit, self)
            try:
                d.get_type(1)
                d.get_version(1)
                self.units[unit] = d #save this puppy
                if debug:
                    print str(unit), ' ',
            except ETimeout:
                if debug:
                    print '.',
                    if count > 20:
                        print ' '
                        count = 0
                    if debug > 1:
                        print 'timeout on : ', str(unit)
                pass
            except EInvalidResponse:
                if debug:
                    print 'invalid response from: ', str(unit)
                pass
            except:
                if debug:
                    print 'some other error occured during discovery'
                pass
        if debug:
            print ' '
            print 'discovered: ', str(self.units)
        return self.units
        
    # This is the basic transaction between the mpx and the tcs controller
    def send_request_with_response(self, cmd, unitnum, numretries=3):
        if debug > 2: print 'In TCS-LineHandler with %s' % cmd

        curtries = 0
        while (1):
            curtries += 1

            self.lock.acquire()
            try:
                frame.send_frame(cmd, unitnum, self.port)
                r = frame.receive_frame(self.port)
                if debug > 2: print 'TCSLineHandler received frame: ' + str(r)
                rsp = None
                if cmd.response_class:
                    rsp = cmd.response_class(r, cmd)
               
                self.lock.release()
                return rsp
            except:
                self.lock.release()
                if debug > 1:
                    msglog.log('tcs',msglog.types.INFO,'Caught exception trying to send_request_with_response.')
                    msglog.exception()
                if (curtries >= numretries):
                    raise ETimeout('ETimeout',str(unitnum))                # Re-raise the last exception we got
        
    def send_request_without_response(self, cmd, unitnum, numretries=1):
        if debug > 1: print 'In TCS-LineHandler with %s' % cmd

        curtries = 0
        while (1):
            curtries += 1

            self.lock.acquire()
            try:
                frame.send_frame(cmd, unitnum, self.port)
                r = frame.receive_ack(self.port)
                if debug > 2: print 'TCSLineHandler received ack: ' + str(r)
                self.lock.release()
                return r
            except:
                self.lock.release()
                if debug > 1:
                    msglog.log('tcs',msglog.types.INFO,'Caught exception trying to send_request_without_response.')
                    msglog.exception()
                if (curtries >= numretries):
                    raise                  # Re-raise the last exception we got
        
