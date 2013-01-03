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
from mpx.lib import msglog
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import map_to_attribute, map_from_attribute
from mpx.lib.exceptions import EInvalidValue, EInvalidResponse, ETimeout

from mpx.lib.threading import Queue, Lock
from mpx.lib.threading import Thread
from mpx.ion.dallas.temperature import Temperature
from mpx.ion.dallas.device import address_to_asciihex, asciihex_to_address
from mpx.ion.dallas.crc import crc_of
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib import pause

from node import ARMNode
from array import *
from struct import *

import time
from moab.linux.lib.uptime import secs as uptime_secs

family_name = {0x28:'DS18B20', 0x10:'DS18S20', 0x12:'DS2406', 0x26:'DS2438'}
_models = {'DS18B20':16,
           'DS18S20':2}

# TODO:
# 1.  Use lock/unlock for thread safety with non-temp sensors.
# 2.  Add 'key' child ION to support event binding (and possibly get).

##
# Class for DallasBus ION's.
#
class DallasBus(ARMNode, AutoDiscoveredNode):

    # Cached commands that are independant of the bus.
    getkey_cmd = '\x15\x00\x01\xb0'

    def __init__(self):
        ARMNode.__init__(self)
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
        self.is_arm = True

    def lock(self):
        self._lock.acquire()
    def unlock(self):
        self._lock.release()

    def configuration(self):
        self.devices, self.device_addresses = self.findall()
        self._been_discovered = 0
        config = ARMNode.configuration(self)
        get_attribute(self, 'devices', config)
        return config
        

    ##
    # start temperature conversions
    #
    def start(self):
        ARMNode.start(self)
        self.running = 1
        thread = Thread(name=self.name,target=self._scan_sensors,args=())
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
            if not self.device_addresses:
                self.devices, self.device_addresses = self.findall()
            # get a list of addresses in existing children
            existing = self.children_nodes(auto_discover=0)
            # filter out any non-dallas nodes, like calculators or periodic drivers
            existing = filter(lambda dev : hasattr(dev,'address'), existing)
            existing = [dev.address for dev in existing]
            for addr in self.device_addresses:
                if addr not in existing and not self._nascent_children.get(address_to_asciihex(addr), None):
                    # look for temperature sensors
                    if ord(addr[0]) in (0x28,0x10): # need to add new types
                        # add a new instance to the _nascent children
                        t = Temperature()
                        t.address = addr
                        t.model = _models[family_name[ord(addr[0])]]
                        self._nascent_children[address_to_asciihex(addr)] = t
            # self._been_discovered = 1 #disabled to allow new objects to be discovered
        return self._nascent_children
    ##
    # Do a search on the bus to find what devices are attached
    #
    # @return array of addresses and an array of formatted entries for the nodebrowser
    #
    def findall(self):
        devices = '<ol>'
        device_addresses = []
        try:
            channel = self.id
            if channel < 1 or channel > 2:
                raise Exception('channel must be between 1 and 2')
            command = 'dallas %d\r' % (channel,)
            dict = self.read_response(command)
            if dict['command'] != 'dallas':
                raise Exception('command mismatch: %s' % (dict['command'],))
            if dict['channel'] != channel:
                raise Exception('channel mismatch: %s %d' % (str(dict['channel']), channel,))
            addresses = dict['device_ids'].keys()
            addresses.sort() # long long unsigned ints
            print 'Dallas %d: ' % channel, addresses
            for d in addresses:
                device_address = pack('<Q', d)
                device_addresses.append(device_address)
                device = '%s ' % (family_name.get(int(d & 0xFF), 'unknown'))
                #device += '%016X' % d
                for i in range(8):
                    device += '%2.2X' % ord(device_address[i])
                device += ' '
                devices += '<li>' + device + '</li>'
        except:
            if self.debug:
                msglog.exception()
        devices += '</ol>'
        return devices, device_addresses
    ##
    def _scan_sensors(self):
        self.children_nodes() # trigger autodiscovery to get the ball rolling
        while 1:
            try:
                while self.running:
                    sensors = self.children_nodes(auto_discover=0)[:]
                    for sensor in sensors:
                        # add a little pause based on number of sensors
                        delay = 11.0 / len(sensors) # roughly one sensor per sec
                        if delay < 0.5:
                            delay = 0.5
                        pause(delay)
                        try:
                            if not self.running: break
                            sensor.result = self._read_temperature_for(sensor)
                            if sensor.bad_crc_count > 10: #was logged as bad
                                msglog.log('DallasBus', 'information', 'Resumed: %s' % \
                                        as_node_url(sensor))
                            sensor.bad_crc_count = 0
                            # update the scan_period that shows up in configuration
                            t = uptime_secs()
                            sensor.scan_period = t - sensor._last_read_time
                            sensor._last_read_time = t
                        except:
                            if sensor.bad_crc_count < 11:
                                sensor.bad_crc_count += 1
                                if sensor.bad_crc_count == 10:
                                    sensor.result = None #return ETimeout to gets
                                    msglog.log('DallasBus', 'information', 'Failed: %s' % \
                                               as_node_url(sensor))
                    if not sensors: pause(17) # slow down if no dallas bus
            except:
                if self.debug: msglog.exception()
            pause(30)
            
        
    def _read_temperature_for(self, device):
        channel = self.id
        if channel < 1 or channel > 2:
            raise Exception('channel must be between 1 and 2')
        d = unpack('<Q', device.address)[0]
        command = 'dallas %d %d\r' % (channel, d)
        #t1 = time.time()
        dict = self._read_response(command)
        if dict['command'] != 'dallas':
            raise Exception('command mismatch: %s' % (dict['command'],))
        #if dict['channel'] != channel:
            #raise Exception('channel mismatch: %s %d' % (str(dict['channel']), channel,))
        # 0xBEAA004B46FFFF0C1087  of which AA00 is the temp in reverse order and 10 is the device type
        # isolate the temperature from the loooong  result
        raw_value = dict['device_ids'].values()[0]  # big honking interger
        if self.debug: print 'raw response value: %0X' % raw_value
        crc = raw_value & 0xFF
        scratchpad = pack('>Q', (raw_value >> 8) & 0xffffffffffffffff) # strip off BE and crc
        #print repr(scratchpad), crc
        crc2 = crc_of(scratchpad)
        if self.debug: print "crc: ",crc, crc2
        if crc2 != crc:
            raise ETimeout('dallas crc error')
        if self.debug: print 'sratchpad: ', repr(scratchpad)
        if scratchpad == '\x00\x00\x00\x00\x00\x00\x00\x00':
            raise ETimeout('dallas crc error')
        result = unpack('<h', scratchpad[:2])[0] # get temp
        return float(result)

    # copied from moab.linux.lib.megatron to deal with a firmware error message
    # once the firmware is updated, remove this
    def _read_response(self, command, timeout = 10, retries=3, *args): #read until a full response is received
        cp = self.coprocessor._coprocessor
        debug = self.debug
        try:
            cp.lock()
            for tries in range(retries):
                # clear left overs
                limit = 0
                cp.pieces = []
                while cp.readline(0):
                    #print 'leftover'
                    limit += 1
                    if limit > 100:
                        print 'coprocessor readline limit exceeded'
                        break
                #self.wait(0.1)
                cp.write(command)
                if debug: print 'command: ', repr(command)
                #self.wait(0.2)
                answer = ''
                cp.pieces = []
                tend = time.time() + timeout
                # skip echo of command
                while True: #read and discard until we see a { character
                    read_buf = cp.readline(timeout) #.tostring()
                    if read_buf.find('{') >= 0:
                        answer = read_buf[read_buf.find('{'):]
                        pre = read_buf[:read_buf.find('{')]
                        if pre:
                            if debug: print 'pre: ', repr(pre)
                        break
                    if read_buf and debug: print repr(read_buf),
                    if time.time() > tend:
                        break # timeout and try again
                if len(answer): # { character received, get the rest of the response
                    # once the first { received, read through end of line
                    tend = time.time() + 15
                    if debug: print 'answer: ', repr(answer)
                    try:
                        if answer.find('\x00') >= 0:
                            if debug: print '**********************null char in response*******************'
                            raise EInvalidResponse('null char')
                        x = answer.find("'device_ids':{") + 14
                        answer = answer[:x] + '0x' + answer[x:]
                        x = answer.find("ERROR: temperature conversion was not complete\r\n")
                        if x > 0:
                            if debug: print 'bad answer :', answer
                            answer = answer[:x] + cp.readline(timeout)
                        if debug: print 'new answer: ', answer
                        dict = eval(answer[:answer.find('\r')])
                        error = dict.get('error')
                        if error:
                            raise EInvalidResponse(str(dict['error']))
                        return dict
                    except:
                        cp.command_retries += 1
                        cp.wait(0.3)
                        limit = 0
                        while cp.readline(0.5):
                            limit += 1
                            if limit > 1000:
                                raise EInvalidResponse('coprocessor port streaming garbage')
                        cp.last_bad_response = repr(answer)
                        if debug: print 'response exception'
            if debug: 
                print '*** Coprocessor Response eval error: ', repr(answer)
                print repr(cp.pieces), cp.command_retries
            raise ETimeout('no response from coprocessor')
        finally:
            cp.unlock()

###
## TEMPORARY PATCH FOR MOAB/LINUX/LIB/MEGATRON.PY FOR WALGREENS UPDATE OF 4/25/2011
##
#from moab.linux.lib.megatron import get_coprocessor
#cp = get_coprocessor()
#
#def lock():
#    cp._lock.acquire()
#    try:
#        # maintain pool of locks to avoid constant creation but create
#        # new ones as needed
#        if not cp._lock_pool: 
#            cp._lock_pool.append(Lock())
#        # get a lock from the pool, acquire it and place it at the end of queue
#        fifo_lock = cp._lock_pool.pop()
#        # next thread will have to wait for this lock to be release
#        fifo_lock.acquire() 
#        cp._fifo_locks.append(fifo_lock) 
#        # get the lock set up from the previous thread
#        fifo_lock = cp._fifo_locks[-2] 
#    finally:
#        cp._lock.release()
#    # now wait for previous thread to release the lock, if still locked.
#    # by the time this lock is released, it will be at the beginning of the
#    # queue
#    fifo_lock.acquire()
#    return
#
###
## Unlock coprocessor to allow access.
##
#def unlock():
#    cp._lock.acquire()
#    try:
#        # take the lock we acquired, release it and place it back in pool
#        fifo_lock = cp._fifo_locks.pop(0)
#        fifo_lock.release()
#        cp._lock_pool.append(fifo_lock) # to be recycled
#        # release the lock blocking next waiting thread
#        cp._fifo_locks[0].release()
#    finally:
#        cp._lock.release()
#    return
#
#def patch_moab_megatron():
#    # change the lock in the coprocessor code
#    try:
#        cp._lock.acquire()
#        try:
#            cp._lock_pool = []
#            cp._fifo_locks = [Lock(),] # start with one released lock
#            # change method attributes to call here instead
#            cp.lock = lock
#            cp.unlock = unlock
#        finally:
#            cp._lock.release()
#        msglog.log('dallas', 'information','patched moab.linux.lib.megatron')
#    except:
#        msglog.exception()
#
#patch_moab_megatron()
# 
###  END OF TEMPORARY PATCH FOR WAGS 4/25/2011 
    
def factory():
    return DallasBus()
