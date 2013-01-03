"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
#todo should status get reset the counters???


from mpx import properties
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute, get_attributes, set_attributes
from mpx.ion.host.port import Port, parity_to_int, int_to_parity, int_to_flowctl, flowctl_to_int
from mpx.lib import threading
import time
from mpx.lib.exceptions import ETimeout, ENoData, EIOError, EInvalidValue, EConnectionError
from mpx.lib.exceptions import *
import array, struct
import select
from mpx.lib.event import EventProducerMixin, ChangeOfValueEvent
from mpx.lib import EnumeratedDictionary, msglog

from mpx.lib.aerocomm import aero
from mpx.ion.aerocomm import feu
import types

bypass_who_is = 0
debug = 0
TransceiverState = EnumeratedDictionary({ 
    0:'stopped',
    1:'transceiver_not_responding',
    2:'transceiver_responding',
    3:'exception_in_xmit'
    })

class AerocommServer(CompositeNode, AutoDiscoveredNode, EventProducerMixin):
    ##
    # @todo Fix this ugliness: All necy info is in nodedefs, but not really available to MFW code...
    _inherent_child_names = [ \
                           'eeprom_params',
                           'server_status',
                           ]
    def __init__(self):
        self._running = 0
        self.driver = None
        self.mac_address = None
        self.discovery_mode = 'None'
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        EventProducerMixin.__init__(self)
        self.device_map = {} #keyed by mac address of clients; value=Child node
        self._out_q = [] #request queue
        self._out_q_cv = threading.Condition()
        self._mutex = threading.Lock() #prevent multiple access to outbound commands
        self._registered_clients = {}
        self.transceiver_state = TransceiverState[0]
        self.cov = ChangeOfValueEvent(self, None, self.transceiver_state)
        self.debug = debug
        self.timeout = 10 #seconds
        self.who_is_interval = 10 #seconds
        self.default_discovered_protocol_module = None
        # @todo
        # initailize this through configuration
        self.default_discovered_protocol_module = feu
        self.transceiver_state = 0
        self.relay_node = '/interfaces/relay1'  #this is temporary, should be None
        self.active_devices = {}
        self.status = None

    ##
    # Configure a Aercomm Server instance.
    #
    # @param config The server's configuration dictionary.
    # @key 'name' The name to associate with the Port.
    # @required
    # @key 'parent' The parent ION ( a comm port).
    # @required
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'discovery_mode', self.discovery_mode, config, str)
        set_attribute(self, 'timeout', self.timeout, config, str)
        set_attribute(self, 'debug', self.debug, config, int)
        set_attribute(self, 'relay_node', self.relay_node, config, str)
    ##
    # Returns a dictionary of the port's attributes
    #
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'mac_address', config, str)
        get_attribute(self, 'discovery_mode', config, str)
        get_attribute(self, 'timeout', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'relay_node', config, str)
        try:
            self.status = self.get_status()
        except Exception, e:
            self.status = str(e)
        get_attribute(self, 'status', config, str)
        try:
            self.devices = self.get_devices()
        except Exception, e:
            self.device = str(e)
        get_attribute(self, 'devices', config, str)
        
        return config

    def start(self):
        if not self._running:
            self._running = 1
            #self.parent.debug = 1
            if not self.parent.is_open():
                self.parent.open(0)
            self.driver = aero.aero(self.parent)
            if self.debug: print 'Starting receiver thread'
            self.driver.start()

            self._in_thread = threading.ImmortalThread(target=self._run_in,args=())
            self._in_thread.start()

            self._who_is_thread = threading.ImmortalThread(target=self._run_who_is,args=())
            self._who_is_thread.start()
            if self.debug: print '***started new thread'
        else:
            raise EAlreadyRunning
        CompositeNode.start(self)
        self.update_state(TransceiverState[1])

    def stop(self):
        self._in_thread.should_die()
        self.update_state(TransceiverState[0])

    def _discover_children(self):
        answer = {}
        # Need to synch creation of children by Aerocomm Protocol vs. 
        # by thread using config from Enterprise:
        self._mutex.acquire() 
        try:
            if self._running and (self.discovery_mode != 'None'):
                found_devices = self.get_devices()
                if self.debug > 1: print 'found devices: ', str(found_devices)
                existing_devices = self._child_devices()
                if self.debug > 1: print 'existing devices: ', str(existing_devices)
                for d in found_devices: #list of tuples with device info
                    if d not in existing_devices:  #continuous discovery of new nodes
                        if self.debug: print 'create new Aerocomm client: ', str(d)
                        new_device = AerocommClient(d)  #this will need to be generalized
                        new_device.from_discovery = self.active_devices[d][1][0]
                        new_device.from_config = self.active_devices[d][1][1]
                        answer[new_device.default_name()] = new_device
        finally:
            self._mutex.release()
        return answer

    #answer a list of device types and address currently defined
    def _child_devices(self):
        answer = []
        for n in self._get_children().values():
            if n.__class__ == AerocommClient:
                answer.append(n.mac_address) #mac address
        return answer

    def get_devices(self):
        return self.active_devices.keys()
        #if bypass_who_is:
            #if len(self.driver.devices) == 0:
                #self.driver.devices = [aero.MacAddress('\x00Pg\x0f\xfd='), aero.MacAddress('\x00Pg\x0f&\xc2'), aero.MacAddress('\x00Pg\x0f\x06s')]
        #return self.driver.devices
    def add_device(self, device_mac, src='from_discovery'):
        self._mutex.acquire()
        try:
            flags = [0,0]
            if self.active_devices.has_key(device_mac):
                flags = self.active_devices[device_mac][1]
            if src == 'from_discovery':
                flags[0] = 1
            else:
                flags[1] = 1
            self.active_devices[device_mac] = [time.time(), flags]
        finally:
            self._mutex.release()
        return
    def get_status(self, reset=1):
        self._mutex.acquire()
        try:
            self.status = self.driver.status(reset)
            return self.status
        finally:
            self._mutex.release()
    def update_device_list(self):
        self._mutex.acquire()
        try:
            self.driver.update_device_list()
            return self.get_devices()
        finally:
            self._mutex.release()
    ##
    # update event consumer of change in state of the tranceiver
    #
    def update_state(self, new_state):
        if self.transceiver_state != new_state:
            try:
                new_state = TransceiverState[new_state]
            except:
                pass
            if self.debug: print 'update state, old state:', self.transceiver_state, 'new state:', new_state
            self.cov.old_value = self.transceiver_state
            self.transceiver_state = new_state
            self.cov.value = new_state
            self.event_generate(self.cov)
    def get(self, skip_cache=0):
        return self.transceiver_state

    def register(self, mac, file):
        self._registered_clients[mac] = file #atomic?  ask mark
    def unregister(self, mac):
        try:
            del self._registered_clients[mac] #atomic?
        except:
            print 'aerocomm unregister failed'
            pass #this should be a very rare event
    ##
    # client nodes call this on their own thread to place outgoing messages in the queue
    #
    def put(self, message):
        self.send(message) #go to blocking single threaded scheme
        
        #if self.transceiver_state > 1: #only place client commands in the queue if we are talking ok
            #self._out_q_cv.acquire()
            #try:
                #self._out_q.append(message)
                #self._out_q_cv.notify()
            #finally:
                #self._out_q_cv.release()
        #else:
            #raise EIOError('Aerocomm Server not ready', str(self.transceiver_state), str(message))

    def send(self, message):
        if message is None: return
        self._mutex.acquire()
        client_mac = None
        try:
            for i in range(3):  #try three times to send the data
                try:
                    destination = message[0]
                    if destination.__class__ == aero.MacAddress: #accept either a string or a MacAddress
                        destination = destination.value
                    result = self.driver.sendto(destination, self.mac_address.value, message[1])
                    #print 'aerocomm send result ', result
                    client_mac = aero.MacAddress(destination)
                    if client_mac in self._registered_clients.keys():
                        if result:
                            if self.debug: print 'transceiver state = bad'
                            state = TransceiverState[1] #bad
                        else:
                            state = TransceiverState[2] #good
                        self._registered_clients[client_mac].last_send_status(state) #0=acked ok, 1= no rsp from client error
                    return #successful send, at least the server transceiver is responding
                except ETimeout, e:
                    print 'aerocomm server send message timeout', i
                    continue
                except:
                    self.update_state(TransceiverState[3])
                    raise
                pass
            if self.debug: print 'aerocomm server send message failed'
            self.update_state(TransceiverState[1])
            raise ETimeout('aerocomm server', str(client_mac), str(message[1]))
        finally:
            self._mutex.release()
    def _run_in(self):
        if self.debug: print 'starting aerocomm server input thread'
        while self._running:
            mac, message = self.driver.recv() #blocks in here while waiting for data
            self.update_state(TransceiverState[2])
            if self.debug: print 'received _run_in message', mac, self.driver.hexdump(message)
            self.add_device(mac) #time stamp last received data, add previously unseen devices to table
            if mac in self._registered_clients.keys():
                if self.debug: print 'put to registered client'
                if len(message) > 3: #smallest packet f1 hh hh f2
                    self._registered_clients[mac].put(message)
            else:
                if self.debug: print 'aerocomm message for unknown client', str(mac)
        else:
            self._in_thread.should_die()
    def _run_who_is(self):
        print 'starting aerocomm server who is message thread'
        if self.transceiver_state != 2:
            self._reset_aerocomm_transceiver()
        time.sleep(5)
        self.send((self.driver.all, self._who_is_message(),))
        if self.transceiver_state != 2:
            raise EInvalidValue('transceiver_state',self.transceiver_state, \
                                'Transceiver not responding. Restart whois thread.') # force thread to restart
        time.sleep(10)
        self.send((self.driver.all, self._who_is_message(),))
        counter = 0
        bad_state_counter = 0
        while self._running:
            try:
                if counter > 30: # 5 minutes
                    counter = 0 
                    if self.debug: print 'send who is'
                    self.send((self.driver.all, self._who_is_message(),))
                else:
                    counter += 1
                if self.transceiver_state == 2:
                    bad_state_counter = 0 #things is good
                else:
                    print 'aerocomm server transceiver status not good'
                    bad_state_counter += 1
                    if bad_state_counter > 2:
                        raise EConnectionError('aerocomm server transceiver status not good') #force thread to restart
            except Exception, e:
                print '**** aerocomm whois message exception ****', str(e)
                time.sleep(5)
                raise
            time.sleep(self.who_is_interval)
    def _who_is_message(self):
        try:
            return self.default_discovered_protocol_module.who_is_message()
        except:
            return ''
        
    def _cycle_aerocomm_power(self):
        if self.relay_node:
            try:
                relay = as_node(self.relay_node)
                if self.debug: print 'turn relay off'
                relay.set(0) #turn off the relay
                time.sleep(6) #allow enough time for the clients to see we are gone
                if self.debug: print 'turn relay on'
                relay.set(1) #turn on the relay
                time.sleep(2) #let the device reboot
            except:
                if self.debug: print 'unable to toggle relay'
        return
    ##
    # get the attention of the transceiver and restart it
    #
    def _reset_aerocomm_transceiver(self):
        # turn off the relay, wait, turn it on, wait and then....
        print 'resetting aerocomm transceiver'
        # Pause the competition for the Port mutex, so that the init_radio()
        # method call can get the Port mutex to further its own devious ends:
        feu.feu_poll_thread.pause()
        self._mutex.acquire()
        print '_reset_aerocomm_transceiver: Got the mutex.'
        try:
            self.update_state(1) #not responding, prevent clients from outputting
            self._cycle_aerocomm_power()
            if self.driver.init_radio() != 0:
                self._cycle_aerocomm_power() # force use of new params
                msglog.log('mpx',msglog.types.INFO,'Aerocomm radio has been set to API serial mode.')
            if self.debug: print 'Resetting the transceiver'
            self.driver.timeout = self.timeout
            self.driver.reset()
            time.sleep(1)
            if self.debug: print 'Enabling the transceiver'
            self.driver.rf_enable()
            time.sleep(8)
            self.mac_address = self.driver.get_ee_parameter('address')
            if self.debug: print 'Aerocomm wireless address %s' % str(self.mac_address)
            time.sleep(1)
            self.update_state(2) #responding
        finally:
            print '_reset_aerocomm_transceiver: Releasing the mutex...'
            self._mutex.release()
        # Now that Aerocomm Server Radio should be running again, let 
        # feu_poll_thread and its thread pool start running again:
        feu.feu_poll_thread.unpause()
        return
class EEPromParametersGroup(CompositeNode):
    ##
    # @todo Fix this ugliness: All necy info is in nodedefs, but not really available to MFW code...
    _inherent_child_names = [ \
                           '485_rts',
                           'RTS_enable',
                           'address',
                           'auto_destination',
                           'baud_rate_double',
                           'broadcast_attempts',
                           'channel',
                           'destination_mac',
                           'in_range_select',
                           'interface_timeout',
                           'limit_rf_buffer',
                           'mixed_mode',
                           'mode',
                           'modem_mode',
                           'power_down',
                           'range_refresh',
                           'read_switches',
                           'rf_priority',
                           'rxmode',
                           'serial_mode',
                           'serial_speed',
                           'sleep_time',
                           'system_id',
                           'transmit_attempts',
                           'turbo_mode',
                           'txmode',
                           'version',
                           'wait_time',
                           ]
class EEPromParameter(CompositeNode):
    def start(self): #bind to the correct driver functions based on the node name
        self.driver = self.parent.parent.driver
        self._mutex = self.parent.parent._mutex
        if self.name in self.driver.eeprom_parameters.keys():
            addr, length, rw, type, _range, desc = self.driver.eeprom_parameters[self.name]
            if rw:
                self.set = self._set
        CompositeNode.start(self)
    def get(self, skipCache = 0):
        self._mutex.acquire()
        try:
            return self.driver.get_ee_parameter(self.name)
        finally:
            self._mutex.release()
    def _set(self, value):
        self._mutex.acquire()
        try:
            self.driver.set_ee_parameter(self.name, value)
        finally:
            self._mutex.release()
##
# group the status report points and give a node value for the transceiver status for conveinence
#
class StatusGroup(CompositeNode):
    ##
    # @todo Fix this ugliness: All necy info is in nodedefs, but not really available to MFW code...
    _inherent_child_names = [ \
                           'count',
                           'devices',
                           'rxfail',
                           'rxretry',
                           'time',
                           'txfail',
                           'txretry',
                           ]
    def __init__(self):
        CompositeNode.__init__(self)
        self.last_status_update_time = time.time()
        self.ttl = 3 #seconds
    def get(self, skipCache=0):
        return self.parent.transceiver_state
    def set(self, value):
        #don't actually set anything, just update the status struct with the RESET counters option
        self.parent.get_status(0)
    def _update_status(self): #give a timed cache to make sure status is up to date
        if (self.parent.status is None) or ((self.last_status_update_time + self.ttl) < time.time()):
            self.last_status_update_time = time.time()
            self.parent.get_status()
##
# expand the Aerocomm status structure into nodes
# this is the same info as the configuration variable 'status'
#
class StatusPoint(CompositeNode):
    def start(self):
        CompositeNode.start(self)
        if self.name == 'devices':  #the only settable status point
            self.set = self._set
    def get(self, skipCache = 0):
        self.parent._update_status() #freshen the status if needed
        if self.name == 'devices':
            devices = self.parent.parent.get_devices()
            answer = []
            for d in devices: #a list of mac addresses
                answer.append(str(d)) #append mac address string
            return answer
        return self.parent.parent.status[self.name]
    def _set(self, value):
        #only for devices, accept one or more mac addresses as a string or sequence of strings
        if (type(value) == types.StringType) or (type(value) == types.StringTypes): #mac address as string
            value = eval(value)
        if (type(value) == types.ListType) or (type(value) == types.TupleType): #mac address as list of numbers
            #self.parent.parent.active_devices = {} # no need: want union of configured and discovered devices in this table
            for d in value:
                self.parent.parent.add_device(aero.MacAddress(d),'from_config')
        else:
            self.parent.parent.add_device(aero.MacAddress(value),'from_config')

class AerocommClient(Port, AutoDiscoveredNode, EventProducerMixin):
#@todo
#put in mac address as node
#put in time since last good comm time as node
    def __init__(self, mac_address=None):
        self.running = 0
        self._children_have_been_discovered = 0
        Port.__init__(self)
        AutoDiscoveredNode.__init__(self)
        EventProducerMixin.__init__(self)
        if mac_address:
            self.mac_address = mac_address
        else:
            self.mac_address = REQUIRED
        self.in_range = None
        self.debug = debug
        self.transceiver_state = TransceiverState[0]
        self.cov = ChangeOfValueEvent(self, None, self.transceiver_state)
        self.from_discovery = 0 # 1: remote xcvr assoc'd with this node was discovered by Aerocomm Protocol code
        self.from_config = 0 # 1: remote xcvr assocd with this node was specified in config recvd from Client App
    def default_name(self):
        s = ''
        for byte in self.mac_address.value:
            s += '%2.2x_' % ord(byte)
        return s[:-1]
        
    ##
    # Emulates a Port instance.
    #
    # @param config The port's configuration dictionary.  Most values are ignored.
    # @key 'name' The name to associate with the Port.
    # @required
    # @key 'parent' The parent ION (typically '/ion').
    # @required
    # @key 'dev' The MAC address string of the client transceiver
    # @required
    def configure(self,config):
        set_attribute(self, 'mac_address', self.mac_address, config) #mac address of client
        self.mac_address = aero.MacAddress(self.mac_address)
        self.dev = self.mac_address.value
        Port.configure(self,config)
        set_attribute(self, 'parity', parity_to_int('none'), 
                      config, parity_to_int)
        set_attribute(self, 'baud', 9600, config, str)
        if self.baud == 'Custom':
            self.baud = -1 # flag for later processing of custom_baud
        else:
             self.baud = int(self.baud) # normal path  
        set_attributes(self, (('bits',8), ('stop_bits',1),
                          ('dump_cpl',16)), config, int)
        set_attribute(self, 'custom_baud', 76800, config, int)
        set_attribute(self, 'flow_control', flowctl_to_int('none'), 
                      config, flowctl_to_int)
        set_attribute(self, 'lock_directory', properties.get('VAR_LOCK'), config, str)
        set_attribute(self, 'debug', self.parent.debug, config, int)
        
        #self._devlock = None #DeviceLock(self.dev, self.lock_directory)
        

    ##
    # Returns a dictionary of the port's attributes
    #
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'mac_address', config, str) #mac address string
        # the following paramters are ignored
        get_attribute(self, 'parity', config, int_to_parity)
        get_attribute(self, 'flow_control', config, int_to_flowctl)
        get_attributes(self, ('baud', 'bits', 'stop_bits',
                              'debug', 'dump_cpl'), config, str)
        get_attribute(self, 'custom_baud', config, int)
        get_attribute(self, 'lock_directory', config)
        return config

    def start(self):
        Port.start(self)
        self.running = 1

    def _discover_children(self):  #cheat and 'discover' the csafe device
        if self.debug: print 'asd io group discover children'
        if self.running and not self._children_have_been_discovered: #empty
            self._children_have_been_discovered = 1 #discovery only runs once for this type of node
            answer = {}
            default_module = self.parent.default_discovered_protocol_module
            if default_module:
                new_child = default_module.factory()
                new_name = 'protocol'
                if hasattr(new_child, 'default_name'):
                    new_name = new_child.default_name()
                answer[new_name] = new_child   
            #add some inherent children to display status
            answer['mac_address'] = _PropAttr()
            answer['transceiver_state'] = _PropAttr()
            answer['last_recv_timestamp'] = _PropAttr()
            return answer
        return self._nascent_children

    def open(self, blocking=0):
        if self.is_open():
            raise EAlreadyOpen
        #self._create_lock_file()
        self._blocking = 1 #blocking # save user's desired blocking mode
        
        # A file object is used as a convenience, especially for array's tofile
        # and fromfile methods.  A buffer size of 0 should disable all C FILE
        # buffering.
        self.file = PollingFileEmulator(self.mac_address, self.parent, self) 
        self.poll = self.file._pollin
        self.file.open()

    ##
    # Close the port, disallowing read/write access.
    #
    def close(self):
        if not self.is_open():
            raise ENotOpen
        #self._delete_lock_file()
        self.file.close() #this is unregister the input stream
        self.file = None
        self.poll = None

    def flush(self):
        self.file.flush() #do nothing

    def sendbreak(self,duration=0):
        pass
    ##
    # Disregard all queued input bytes.
    #
    # @return buffer containing disregarded queued bytes.
    #
    def drain(self):
        buffer = self._safe_apply(self._drain)
        if self.debug:
            self.dump(buffer, 'D< ')
        return buffer
    
    def _write(self, buffer):
        self.file.write(buffer)

    def update_state(self, new_state):
        if self.transceiver_state != new_state:
            try:
                new_state = TransceiverState[new_state]
            except:
                pass
            if self.debug: print 'update state, old state:', self.transceiver_state, 'new state:', new_state
            self.cov.old_value = self.transceiver_state
            self.transceiver_state = new_state
            self.cov.value = new_state
            self.event_generate(self.cov)

    def get(self, skip_cache=0):
        return self.transceiver_state
        
## Emulates the interface of the file and select.poll objects
#  this object uses a queue protected by a condition variable
#  to transfer messages (strings) from the AerocommServer read thread
#  to the AerocommClient port emulator.  
    def _get_attr_value(self, name, skipCache=0):
        if name == 'mac_address':
            return self.mac_address
        if name == 'transceiver_state':
            return self.transceiver_state
        if name == 'last_recv_timestamp':
            if self.file:
                ts = self.file.last_recv_timestamp
                if ts:
                    return time.time() - ts
            return None
        raise EInvalidValue('get_attr_value with wrong name', 'name', str(self.name))

from mpx.lib.stream import CrossThreadStream
class PollingFileEmulator(CrossThreadStream):
    def __init__(self, mac, server, owner):
        CrossThreadStream.__init__(self)
        self.mac = mac
        self.server = server
        self.owner = owner #used to report link status
        self.last_recv_timestamp = None
    # register with the server to receive messages from the input stream
    def open(self):
        self.server.register(self.mac, self)
    # stop receiving messages from the imput stream
    def close(self):
        self.server.unregister(self.mac)
        CrossThreadStream.close(self)
    # read strings from the input queue
    # return all available characters in a string
    def read(self): #return the all available data as a string
        answer = ''
        try:
            while 1:
                answer += CrossThreadStream.read(self, 1024, 0)
        except ETimeout:
            pass
        return answer

    # place the data string in the servers output queue along with our mac address
    def write(self, data):
        self.server.put((self.mac, data.tostring(),))
    def flush(self):
        pass

    # called from server thread and places strings in the input queue
    def put(self, data): #called by server
        if debug: print 'server put to client:', str(data)
        self.last_recv_timestamp = time.time()
        CrossThreadStream.write(self, data)

    def last_send_status(self, state): #update owner regarding last send
        if self.owner:
            self.owner.update_state(state)
"""
"['\\x00Pg\\x0f\\xfd=', '\\x00Pg\\x0f&\\xc2', '\\x00Pg\\x0f\\x06s']"
"""
class _PropAttr(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.last_value = None
        self.last_get_time = None
    def get(self, skipCache=0):
        answer = None
        try:
            answer = self.parent._get_attr_value(self.name, skipCache)
            if self.parent.debug: print 'PropAttr %s: exit get(): %s' % (self.name, str(answer))
        except EInvalidValue:
            print '_PropAttr Property invalid name: ', self.name
            pass
        return answer
    def _set(self, value):
        raise ENotImplemented  #self.parent._set_attr_value(self.name, value)

