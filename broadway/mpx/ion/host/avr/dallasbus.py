"""
Copyright (C) 2001 2002 2005 2010 2011 Cisco Systems

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
from mpx.lib import msglog
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import map_to_attribute, map_from_attribute
from mpx.lib.exceptions import EInvalidValue, EInvalidResponse

from mpx.lib.threading import Queue, Lock
from mpx.lib.threading import Thread
from mpx.ion.dallas.temperature import Temperature, _read_temperature_sensors_for
from mpx.ion.dallas.device import address_to_asciihex, asciihex_to_address
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib import pause

from node import AVRNode
from array import *


family_name = {0x28:'DS18B20', 0x10:'DS18S20', 0x12:'DS2406', 0x26:'DS2438'}
_models = {'DS18B20':16,
           'DS18S20':2}

# TODO:
# 1.  Use lock/unlock for thread safety with non-temp sensors.
# 2.  Add 'key' child ION to support event binding (and possibly get).

##
# Class for DallasBus ION's.
#
class DallasBus(AVRNode, AutoDiscoveredNode):

    # Cached commands that are independant of the bus.
    getkey_cmd = '\x15\x00\x01\xb0'

    def __init__(self):
        AVRNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self._lock = Lock()
        self.conversion_list = {}
        self._queue = Queue()
        self.debug = 0
        self.running = 0
        self._start_called = 0
        self.devices = ''
        self.device_addresses = []
        self._been_discovered = 0

    def lock(self):
        self._lock.acquire()
    def unlock(self):
        self._lock.release()

    ##
    # @see node.AVRNode#configure
    #
    def configure(self,config):
        AVRNode.configure(self,config)
        id_chr = chr(self.id)

        # Commands cached in their entirety
        self.reset_cmd = '\x15\x00\x02\x10' + id_chr
        self.scan_cmd = '\x15\x00\x02\xc0' + id_chr
        self.unscan_cmd = '\x15\x00\x02\xd0' + id_chr
        self.convert_cmd = '\x15\x01\x04\x70' + id_chr + '\x01\x44'
        self.readscratch_cmd = '\x15\x00\x04\x70' + id_chr + '\x01\xbe'
        self.readrom_cmd = '\x15\x00\x04\x70' + id_chr + '\x01\x33'
        self.findfirst_cmd = '\x15\x00\x02\x80' + id_chr
        self.findfamily_cmd = '\x15\x00\x02\x81' + id_chr
        self.findnext_cmd = '\x15\x00\x03\x82' + id_chr + '\x00'
        # The beginning of commands of known length.
        self.matchrom_base = '\x15\x00\x0c\x70' + id_chr + '\x09\x55'
        self.skiprom_cmd = '\x15\x00\x04\x70' + id_chr + '\x01\xcc'
        self.readbits_base = '\x15\x00\x03\x40' + id_chr
        self.readbytes_base = '\x15\x00\x03\x50' + id_chr
        # Cached command codes + bus id.
        self.writebits_id = '\x60' + id_chr
        self.writebytes_id = '\x70' + id_chr
        return
    
    def configuration(self):
        self.devices, self.device_addresses = self.findall()
        self._been_discovered = 0
        config = AVRNode.configuration(self)
        get_attribute(self, 'devices', config)
        return config
        

    def _add_child(self, node):
        AVRNode._add_child(self, node)
        if not self.running and self._start_called:
            self.start()

    ##
    # start temperature conversions
    #
    def start(self):
        AVRNode.start(self)
        self._start_called = 1
        self.devices, self.device_addresses = self.findall()
        if self.running:
            raise EAlreadyRunning()

        # Inform in msglog the number of devices on the dallas bus and their addresses (CSCtl81599)
        if(self.devices == None ):
            no_of_devices=0
        else:
            no_of_devices=len(self.device_addresses)
        msglog.log('broadway',msglog.types.INFO,'There are %d devices found on "%s" bus' %(no_of_devices, self.name))
        if no_of_devices:
            addr_str=''
            for addr in self.device_addresses:
                dallas_bus_addr=address_to_asciihex(addr)
                addr_str=addr_str+' '+dallas_bus_addr
            msglog.log('broadway',msglog.types.INFO,'The device addresses on "%s" bus : %s\n' %(self.name,addr_str))
        
        # Start the thread to read the dallas bus irrespective for whether the devices are
        # present or not (CSCtl81599)
        self.running = 1
        thread = Thread(name=self.name,target=self._queue_thread,args=())
        self.request(self._convert_temperature_sensor_list)
        thread.start()            

    def stop(self):
        self.running = 0

    ##
    # discover and create object instances
    #
    def _discover_children(self, force=0):
        if force:
            self._been_discovered = 0
        if self.running == 1 and not self._been_discovered:
            # do a find_all irrespective of whether there are ny devices found previously (CSCtl81599)
            self.devices, self.device_addresses = self.findall()
            # get a list of addresses in existing children
            existing = self.children_nodes(auto_discover=0)
            existing = filter(lambda dev : hasattr(dev,'address'), existing)
            existing = [dev.address for dev in existing]
            for addr in self.device_addresses:
                if addr not in existing and not self._nascent_children.get(address_to_asciihex(addr), None):
                    if ord(addr[0]) in (0x28,0x10): # need to add new types
                        # add a new instance to the _nascent children
                        
                        t = Temperature()
                        t.address = addr
                        t.model = _models[family_name[ord(addr[0])]]
                        self._nascent_children[address_to_asciihex(addr)] = t
            # self._been_discovered = 1 #disabled to allow new objects to be discovered
        return self._nascent_children
    ##
    # Create a dallas message for a cmd and flags.
    #
    # @param cmd  The command turn into a message.
    # @param flags  Flags to send with message.
    # @return Dallas_message representing <code>cmd</code>
    #         with <code>flags</code>.
    #
    def dallas_message(self, cmd, flags):
        if flags:
            hdr = '\x15' + chr(flags)
        else:
            hdr = '\x15\x00'
        return hdr + chr(len(cmd)) + cmd

    ##
    # Send a command on dallas_bus.
    #
    # @param cmd  The dallas_command to send.
    # @param flags  Flags to send with command.
    # @default 0
    # @return Dallas bus response.
    #
    def invoke_command(self, cmd, flags=0):
        return self.avr.invoke_message(self.dallas_message(cmd, flags))

    ##
    # Read specified number of bits from dallas_bus.
    #
    # @param n  The number of bits to read.
    # @return <code>n</code> bits from dallas bus.
    #
    def readbits(self, n):
        msg = self.readbits_base + chr(n)
        return self.avr.invoke_message(msg)

    ##
    # Read specified number of bytes from dallas bus.
    #
    # @param n  Number of bytes to read.
    # @return <code>n</code> bytes from dallas bus.
    #
    def readbytes(self, n):
        msg = self.readbytes_base + chr(n)
        return self.avr.invoke_message(msg)

    ##
    # Write specified bits to dallas bus.
    #
    # @param n  Number of bits to write.
    # @param bits  Bits to write to dallas bus.
    # @return Dallas bus response.
    #
    def writebits(self, n, bits):
        msg = self.writebits_id + chr(n) + bits
        msg = self.dallas_message(msg, 0)
        return self.avr.invoke_message(msg)

    ##
    # Write specified bytes to dallas bus.
    #
    # @param n  Number of bytes to write.
    # @param bytes  Bytes to write.
    # @param flags  Flags to include with the message.
    # @return Dallas bus response.
    #
    def writebytes(self, n, bytes, flags):
        msg = self.writebytes_id + chr(n) + bytes
        msg = self.dallas_message(msg, flags)
        return self.avr.invoke_message(msg)

    ##
    # Send Get key command to dallas bus.
    #
    # @return Dallas bus response.
    #
    def getkey(self):
        return self.avr.invoke_message(self.getkey_cmd)

    ##
    # Wait for dallas key to be connected then
    # call <code>getkey</code>
    # @see #getkey
    #
    def waitforkey(self):
        self.avr.wait_for_oob()
        return self.getkey()

    ##
    # Tell avr to scan dallas bus for devices that get
    # connected.
    #
    # @return Dallas bus response.
    #
    def scan(self):
        return self.avr.invoke_message(self.scan_cmd)[0]

    ##
    # Tell avr to stop scanning dallas bus.
    #
    # @return Dallas bus response.
    #
    def unscan(self):
        return self.avr.invoke_message(self.unscan_cmd)[0]

    ##
    # Reset dallas bus.
    #
    # @return Dallas bus response.
    #
    def reset(self):
        return self.avr.invoke_message(self.reset_cmd)[0]

    ##
    # Issue matchrom command to dallas bus.
    #
    # @param address  The address of a specific
    #                 device.
    # @return Dallas bus response.
    # @throws EInvalidValue  If the <code>address</code>
    #                        sent in was invalid.
    #
    def matchrom(self, address):
        if len(address) != 8:
            raise EInvalidValue, ('address', address)
        return self.avr.invoke_message(self.matchrom_base + address)[0]

    ##
    # Issue skiprom command to dallas bus.
    #
    # @param None.
    # @return Dallas bus response.
    #
    def skiprom(self):
        return self.avr.invoke_message(self.skiprom_cmd)[0]

    ##
    # Tell device to do conversion.
    #
    # @return Dallas bus response.
    # @note Convertion is done by device whose
    #       address was previously matched.
    #
    def convert(self):
        return self.avr.invoke_message(self.convert_cmd)[0]

    ##
    # Tell device to read scratch onto dallas bus.
    #
    # @return dallas bus response.
    #
    def readscratch(self):
        return self.avr.invoke_message(self.readscratch_cmd)

    ##
    # Tell device to read ROM onto dallas bus.
    #
    # @return ROM of device.
    #
    def readrom(self):
        self.lock()
        try:
            self.reset()
            self.avr.invoke_message(self.readrom_cmd)
            result = self.readbytes(8)
        finally:
            self.unlock()
        return result
    ##
    # Do a search on the bus to find what devices are attached
    #
    # @return array of addresses and an array of formatted entries for the nodebrowser
    #
    def findall(self):
        devices = '<ol>'
        device_addresses = []
        self.lock()
        if not ord(self.reset()):
            self.unlock()
            return None, 'No devices attached'
        self.avr.invoke_message(self.findfirst_cmd)
        while 1:
            d = self.avr.invoke_message(self.findnext_cmd)
            if not ord(d[8]):
                break
            device_addresses.append(d[:8])
            device = '%s ' % (family_name[ord(d[0])])
            for i in range(8):
                device += '%2.2x' % ord(d[i])
            device += ' '
            devices += '<li>' + device + '</li>'
            self.reset()
        devices += '</ol>'
        self.unlock()
        return devices, device_addresses
    ##
    # Use a queue to control access to the channel
    #
    # Send a request in the form of a callback object with params
    #
    def request(self, target, *args):
        if self.debug:
            print "DALLASBUS:  Add Request to queue", target
        self._queue.put((target,args,))
    def _queue_thread(self):
       while self.running:
           try:
               while 1:
                   request = self._queue.get()
                   if self.debug:
                       print "DALLASBUS: just received request: ", request
                   if type(request) is tuple:
                       if len(request) == 2:
                           apply(request[0], request[1])
           except EInvalidResponse, e:
               msglog.log('Dallas Bus', 'information', str(e))
               if self.debug: msglog.exception()
           except:
               msglog.exception()
           if self.debug: 
                msglog.log('broadway',msglog.types.INFO,'Dallas queue restarting\n')
       pass
    def _convert_temperature_sensor_list(self):
        try:
            if len(self.conversion_list):
                if self.debug:
                    print "DALLASBUS: _read_temperature_sensors_for", self
                _read_temperature_sensors_for(self)
            else:
                if self.debug:
                    print "DALLASBUS: sleep for one second because there are no sensors", self
                pause(4)
        finally:
            self.request(self._convert_temperature_sensor_list)
    

def factory():
    return DallasBus()
