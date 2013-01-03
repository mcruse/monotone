"""
Copyright (C) 2001 2002 2004 2010 2011 Cisco Systems

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
##
#

# TODO:
# 2.  Need to recover from tracebacks better.  Some sort of reset on the dev?
#
import select

import mpx.lib
from mpx.lib import threading
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, set_attributes, \
     get_attribute, get_attributes
from mpx.lib import msglog

##
# Class for AVR module's ION.
#
class AVR(CompositeNode):
    # Thread-safe lock.  Should be extended to be process independant.
    _lock = threading.Lock()

    def __init__(self):
        CompositeNode.__init__(self)
        self.debug = 0

    ##
    # @see mpx.ion.host.Host#configure
    #
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'ncounters', REQUIRED, config, int)
        set_attribute(self, 'nDIs', REQUIRED, config, int)
        set_attribute(self, 'nrelays', REQUIRED, config, int)
        set_attribute(self, 'ndallas_busses', REQUIRED, config, int)
        set_attribute(self, 'nGPIOs', REQUIRED, config, int)

        # Open the avr devices.
        self.avr = None
        self.avroob = None
        try:
            self.avr = open("/dev/avr", "r+")
            self.avroob = open("/dev/avroob", "r")
            self.p = select.poll()
            self.p.register(self.avroob, select.POLLIN)
            avr_maj_ver = ord(self.invoke_message('\x17\x00\x00')[0])
            if (avr_maj_ver < 2) and (self.nGPIOs > 0):
                self.nGPIOs = 0
                msglog.log('mpx',msglog.types.ERR,'No GPIOs created; AVR version is %s; should be 2.x or greater.' \
                           % self.version())
            # Attach the counters, relays and dallas busses to the AVR.
            config_list = (('mpx.ion.host.avr.counter', 'counter',
                            self.ncounters),
                           ('mpx.ion.host.avr.di', 'DI', self.nDIs),
                           ('mpx.ion.host.avr.relay', 'relay', self.nrelays),
                           ('mpx.ion.host.avr.dallasbus', 'dallas',
                            self.ndallas_busses),
                           ('mpx.ion.host.avr.gpio', 'gpio', self.nGPIOs))
            for module,prefix,count in config_list:
                for i in range(1,count+1):
                    name = prefix + str(i)
                    config = {'name':name, 'id':i, 'avr':self, 'parent':self}
                    ion = mpx.lib.factory(module)
                    ion.configure(config)
        except:
            msglog.log('broadway',msglog.types.ERR,"Failed to open avr device.")
            msglog.exception()
            self.p = select.poll()
            if self.avr:
                self.avr.close()
                self.avr = None
            if self.avroob:
                self.avroob.close()
                self.avroob = None
            pass

        return

    # Actual AVR code.

    ##
    # Lock AVR for safe access.
    #
    def lock(self):
        self._lock.acquire()
        return

    ##
    # Unlock AVR to allow access.
    #
    def unlock(self):
        self._lock.release()
        return

    ##
    # Print msg.
    #
    # @param msg  Message to be printed.
    #
    def dump(self, msg):
        for b in msg:
            print "%02x" % (ord(b)),
        print
        
    ##
    # Get the version of the AVR module.
    #
    # @return AVR Version number.
    #
    def version(self):
        rsp = self.invoke_message('\x17\x00\x00')
        return "%d.%d" % (ord(rsp[0]), ord(rsp[1]))

    def wait_for_oob(self):
        # Only used by the AVR event thread.
        self.p.poll()
        return

    ##
    # Send message to AVR.
    #
    # @param msg  Message to send.
    # @return  Response sent back from AVR.
    #
    def invoke_message(self, msg):
        self.lock()
        try:
            if self.debug:
                print '> ',
                self.dump(msg)
            self.avr.write(msg)
            hdr = self.avr.read(3)
            rsp = self.avr.read(ord(hdr[2]))
            if self.debug:
                print '< ',
                self.dump(rsp)
        finally:
            self.unlock()
            pass
        return rsp

def factory():
    return AVR()
