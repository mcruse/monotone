"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

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
import _mpxhooks
import time, types, array
from mpx.lib import msglog
from mpx.lib import EnumeratedValue
from mpx.lib import thread_pool
from mpx.lib import Callback
from mpx.ion import Result

from socket import inet_aton
from struct import pack

from moab.linux.lib import uptime

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.event import ChangingCovEvent
from mpx.lib.event import EventProducerMixin
from mpx.lib.node import CompositeNode, as_node_url, as_internal_node, as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.node.proxy import ProxyAbstractClass
from mpx.lib.threading import ImmortalThread, Lock
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ECovNode
from mpx.lib.exceptions import ENonCovNode
from mpx.lib.scheduler import scheduler

from mpx.lib.bacnet import datatype
from mpx.lib.bacnet import network
from mpx.lib.bacnet import tag
from mpx.lib.bacnet._exceptions import *
from mpx.lib.bacnet._bacnet import write_property_g3, read_property_g3, \
    read_property_multiple_g3, _read_property_multiple_g3, \
    recv_callback_helper, send_device_time_syncronization, \
    send_addr_time_syncronization, cov_subscription_request
from mpx.lib.bacnet.bvlc import start_bbmd_service, get_bdt_for, \
     The_BBMD_Server, bbmd_status, enable_bbmd, disable_bbmd, \
     update_bbmds, validate_bbmds, get_bdt_from
from mpx.lib.bacnet.datatype import enum_2_class, BACnetObjectIdentifier, \
     BACnetDate, BACnetDailySchedule
from mpx.lib.bacnet.device import discover_children_boids
from mpx.lib.bacnet.network import _device_table as DeviceTable
from mpx.lib.bacnet.sequence import _OPTIONAL as OPTIONAL
from mpx.lib.bacnet.server import create_server_device
from mpx.lib.bacnet.tsstrings import tsenum, est, data_type_enum, \
     object_property_data as opd, property_ids, BACnetObjectTypeStr

from mpx.ion.bacnet.batch_manager import BatchManagerMixin

from mpx.service.schedule.interfaces import IScheduleHolderParent
from mpx.service.schedule.bacnet_scheduler import *

DEBUG = 0
debug = DEBUG
DEFAULT_WRITE_PRIORITY = 11

# Default values for now. svaidya-TODO: After scale/ 
# performance testing at EFT, fine tune the intervals and add 
# logic to increase delay in subsequent COV subscription
# attempts etc.
cov_subscription_refresh_interval = 900 # 15 mins
cov_subscription_lifetime = 3600 # 1 hour
cov_subscription_pid = 1 # default value for all COV subscriptions 
                         # Could use server device id instead
cov_enabled = None

PdoLock = Lock() #used for delayed saving of pdo objects

vendors = {

    }
class str_list(list):
    def __str__(self):
        return '['+(','.join([str(x) for x in self]))+']'

class BACnet(CompositeNode):
    _node_def_id = 'abd77674-a93b-4e12-8e25-59d59d2fa9e9'
    pass

class BACnetInterNetwork(CompositeNode):
    _node_def_id = '539e4a0e-ce38-4bc1-84f0-9ece0bf851da'
    def __init__(self):
        CompositeNode.__init__(self)
        self.running = 0
        self._interfaces = []
    def configure(self, config):
        global DEFAULT_WRITE_PRIORITY
        CompositeNode.configure(self, config)
        # provides a means in which to globally override the default
        # priority that values are written at.  Meant to be a "hidden" config. 
        # property....
        set_attribute(self, 'default_write_priority', 11, config, int)
        set_attribute(self, 'enable_router', 0, config, int)
        set_attribute(self, 'cov_enable', 0, config, int)
        set_attribute(self, 'debug', DEBUG, config, int)
        DEFAULT_WRITE_PRIORITY = self.default_write_priority
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'default_write_priority', config, str)
        get_attribute(self, 'enable_router', config, str)
        get_attribute(self, 'cov_enable', config, str)
        get_attribute(self, 'debug', config, int)
        return config
    def children_nodes(self, **options):
        answer = CompositeNode.children_nodes(self, **options)[:]
        #for a determinstic starting order, make sure the children are returned in the following order: configuration, services, devices, other
        answer.sort(self._sort_children_nodes) 
        return answer
    def _sort_children_nodes(self, a, b):
        if hasattr(a, '_sort_order'):
            if hasattr(b, '_sort_order'):
                return cmp(a._sort_order, b._sort_order)
            return -1 #any of the main three children sort before anything else
        return cmp(a, b)
    def start(self):
        #start order is forced by _sort_children_nodes method above
        CompositeNode.start(self)
        self.running = 1
        self.check_cov_enabled()
    def stop(self):
        self.running = 0
        self._interfaces = []  #invalidate interfaces when stopped to force new search
        CompositeNode.stop(self)
    def check_cov_enabled(self):
        global cov_enabled
        if self.cov_enable == 1:
            cov_enabled = True
        else:
            cov_enabled = False
    def interfaces(self): #return a list of active interfaces
        if self._interfaces:
            return self._interfaces
        try:
            c = self.get_child('Configuration')
            for n in c.children_nodes():
                ethx = n.children_nodes()
                for e in ethx:
                    if e.__class__ == BIN_port:
                        self._interfaces.append(e)
        except:
            msglog.exception()
            pass
        return self._interfaces
    def all_devices(self):  #returns device table info objects for all discovered devices
        all_devices = []
        for i in self.interfaces():
            all_devices.extend(i._all_descendant_devices())
        return all_devices
        
                    
class BIN_Devices(CompositeNode, AutoDiscoveredNode):
    _node_def_id = '8da89884-fb47-4d9b-a1a0-b299ba33e786'
    _sort_order = 3
    def __init__(self):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.running = 0
        self._discovery_mode = 0
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'static_device_table', [], config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'static_device_table', config)
        self.number_of_children = len(self.children_nodes(auto_discover=False))
        self.number_of_devices = len(network._device_table)
        get_attribute(self, 'number_of_children', config)
        get_attribute(self, 'number_of_devices', config)
        return config
    def start(self):
        if self.running: return
        CompositeNode.start(self)
        for d in self.static_device_table:
            try:
                self.add_static_device(**d)
            except:
                msglog.exception()
        self.running = 1
    def stop(self):
        self.running = 0
        CompositeNode.stop(self)
    ##
    # Discover any bacnet devices that are not part of the node tree
    #
    # @param None.
    # @return A dictionary of potential devices, keyed by instance number
    # @throws None
    # for each interface, get list of devices 
    def _discover_children(self): #find any new devices
        answer = {}
        if self.running == 1 and self._discovery_mode == 1:
            try:
                result = {} #start fresh
                if self.debug: print 'Discover services/network/bacnet/bin children'
                # get list of static devices
                static_devices = [int(sd['id']) for sd in self.static_device_table]
                # get list of truely found devices from the Device table
                found_devices = self.parent.all_devices()
                # filter found_devices from static_devices
                undiscovered_static_devices = filter(lambda sd: sd not in found_devices, static_devices)
                # attempt to communicate with remaining undiscovered static devices
                if undiscovered_static_devices:
                    # generate local table of undiscovered static devices
                    static_device_table = filter(lambda sd: int(sd['id']) in undiscovered_static_devices, self.static_device_table)
                    for d in static_device_table:
                        try:
                            self.add_static_device(**d)
                        except:
                            # during startup we already have error message related to missing device. don't need more
                            pass #msglog.exception()
                    # regenerate the found_devices
                    found_devices = self.parent.all_devices()
                existing_devices = self._child_device_instance_numbers()
                if self.debug: 
                    print 'found devices: ', found_devices
                    print 'existing devices: ', existing_devices
                for d in found_devices:  #I would iterate by keys (device instance) but we may change to a different key
                    if self.debug:
                        print 'see if device is existing: ', str(d)
                        print '   instance number: ', str(d.instance_number)
                    if d.instance_number not in existing_devices:
                        if self.debug: print 'new device found: ', str(d)
                        new_device = BINAliasDevice(d) #create new device node from this device
                        result[str(d.instance_number)] = new_device
                        continue #next found device
                answer = result
            except:
                msglog.exception()
                if self.debug: print 'error during services/network/bacnet network discover'
        if self.debug:
            print 'BIN discover result: ', str(answer)
        return answer
    def discover_child(self, name, **options):
        if self.running == 1:
            try:
                return AutoDiscoveredNode.discover_child(self, name, **options)
            except:
                d = network._device_info(int(name)) #this should trigger a focused who_is for the device
                if d is None: # device was not discovered, look in static table
                    for d_dict in self.static_device_table: 
                        if int(d_dict['id']) == int(name):
                            # could be static device that came online after start
                            try:
                                self.add_static_device(**d_dict)
                                d = network._device_info(int(name)) # try again
                            except:
                                pass #msglog.exception()
                            break # no reason to continue looking at other ids
                if d:
                    self._nascent_children[name] = BINAliasDevice(d)
                    return AutoDiscoveredNode.discover_child(self, name, **options)
                raise #enosuchname

    def _child_device_instance_numbers(self):
        answer = []
        for n in self._get_children().values(): # only get_children allready discovered
            try:
                answer.append(n.instance)  #get aliased node's instance variable
            except:
                msglog.exception()
        return answer

    def who_is(self): #can be triggered with ..../Devices?action=invoke&method=who_is
        network._who_are_devices()
        time.sleep(1)
        #return "Use the browser's Back button and refresh the page\n\nDevice Table: %s" % (str(DeviceTable.keys())) 
        return '''
<meta http-equiv="REFRESH" content="2;url=%s">
If not redirected back to Device list, use browser's Back button and refresh the page
<br><br>
Device Table: %s
''' % ('/nodebrowser' + self.as_node_url(),str(DeviceTable.keys()))
    def nodebrowser_handler(self, nb, path, node, node_url):
        block = [nb.get_default_view(node, node_url)]
        block.append('<div class="node-section node-commands">')
        block.append('<h2 class="section-name">Commands</h2>')
        s = 'Devices?action=invoke&method=who_is'
        block.append('<a href="%s">send Who-Is</a>' %(s,))
        block.append('<br>\n<br>\n')
        if self._discovery_mode:
            d = 'broad'
        else:
            d = 'directed'
        block.append('  Discovery mode is ')
        s = 'Devices?action=invoke&method=toggle_discovery_mode'
        block.append('<a href="%s">%s</a>' %(s,d))
        block.append("</div>")
        return "\n".join(block)
    def toggle_discovery_mode(self):
        if self._discovery_mode:
            self._discovery_mode = 0
            d = 'directed'
        else:
            self._discovery_mode = 1
            d = 'broad'
        return '''
<meta http-equiv="REFRESH" content="2;url=%s">
If not redirected back to Device list, use browser's Back button and refresh the page
<br><br>
Discovery mode is now: %s
''' % ('/nodebrowser' + self.as_node_url(),d)
    #@todo make persistent
    #@todo add form to devices nodebrowser web page
    #@todo support non-IP channels
    #can be used from nodebrowser: .../Devices?action=invoke&method=add_static_device&parameters=1&id=2000&addr=66.149.223.210&port=47808&networkID=1&mac=66.149.223.210&mac_networkID=1
    def add_static_device(self, id=None, addr=None, networkID=None, mac=None, mac_networkID=None, port=None, **keywords):
        id = keywords.get('id', id)
        addr = keywords.get('addr', addr)
        networkID = keywords.get('networkID', networkID)
        mac = keywords.get('mac', mac)
        mac_networkID = keywords.get('mac_networkID', mac_networkID)
        if port is None: # need to get port info from mac interface
            for i in self.parent.interfaces(): # all the active eth or com BIN_ports
                if i.parent.network == int(mac_networkID): #find the channel we need to send from 
                    port = i.parent.port
                    break
        port = keywords.get('port', port)
        print 'static device port: ', str(port)
        
        if int(id) not in DeviceTable:
            d = network._DeviceInfo()
            d.instance_number = int(id)
            d.node = None
            d.object_type = 8
            d.max_apdu_len = 1476
            d.can_recv_segments = 0
            d.can_send_segments = 0
            d.vendor_id = 0
            d.network = int(networkID)
            d.address = network.Addr(inet_aton(addr) + pack('!H', int(port)))
            d.readPropertyFallback = 0  
            d.mac_network = int(mac_networkID)
            d.mac_address = network.Addr(inet_aton(mac) + pack('!H', int(port)))
            #add this text device to the device table and attempt to access it
            DeviceTable[int(id)] = d
            try:
                tags = self._read_device_object_property(id, 62) #'Max Message Length Supported',
                d.max_apdu_len = datatype.BACnetUnsigned(decode=tags).value
                tags = self._read_device_object_property(id, 120) #BACnet Vendor ID',
                d.vendor_id = datatype.BACnetUnsigned(decode=tags).value
                tags = self._read_device_object_property(id, 107) #'Segmentation Supported',
                seg = datatype.BACnetSegmentation(decode=tags).value
                # 0:'segmented_both',
                # 1:'segmented_transmit',
                # 2:'segmented_receive',
                # 3:'no_segmentation',
                if int(seg) == 0:
                    d.can_recv_segments = 1
                    d.can_send_segments = 1
                elif int(seg) == 1:
                    d.can_send_segments = 1
                elif int(seg) == 2:
                    d.can_recv_segments = 1
            except:
                # msglog.exception()
                del(DeviceTable[int(id)])
                raise EDeviceNotFound('Static Device: %s not found' % id)
            print str(d)
        return str(d)
    def _read_device_object_property(self, did, pid):
        prop = (8, int(did), int(pid))
        r = read_property_g3(int(did), prop)
        tags = r.property_value #a list of tags
        return tags

class BIN_Services(CompositeNode):
    _node_def_id = '82268d47-20a7-4e1d-8fa6-27dfa8c10fc5'
    _sort_order = 2
    pass
class BIN_Schedules(CompositeNode): #, AutoDiscoveredNode): #sits under /services/network/bacnet/internetwork/services/
    _node_def_id = '2cc14a86-4f6d-4831-b384-92607deca5ab'
    #implements(IScheduleHolderParent)
    def __init__(self):
        CompositeNode.__init__(self)
        #AutoDiscoveredNode.__init__(self)
        self.running = 0
        self.discover_mode = 'never' #never numeric name name_and_numeric
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'source','broadway', cd, str)
        set_attribute(self, 'devices_link', '../../Devices', cd, str) #url of Devices node
        set_attribute(self, 'schedule_holders_parent', '/services/time/local/', cd, str)
        set_attribute(self, 'discover_mode', self.discover_mode, cd, str)
        set_attribute(self, '__node_id__',self._node_def_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'source', config)
        get_attribute(self, 'discover_mode', config)
        get_attribute(self, 'devices_link', config)
        get_attribute(self, 'schedule_holders_parent', config)
        return config
    def start(self):
        CompositeNode.start(self)
        self.running = 1
        scheduler.after(61,self._discover_schedules)
        
    def stop(self):
        self.running = 0
        CompositeNode.stop(self)
    def _discover_schedules(self, force=0):
        #search through bacnet devices for Schedule Objects
        #discover_mode: 0==none,  1==use numbers, 2==use name properties,  3==use both
        if self.discover_mode != 'never':
            if self.running == 1:
                try:
                    devices = self.as_node(self.devices_link).children_nodes(auto_discover=0) #this service does not force discovery
                    devices = filter(lambda d: not isinstance(d,ServerDevice), devices) #do not include Server Devices.  They are proxies to native schedules
                    devices = filter(lambda d: d.has_child('17'), devices) #only include devices that have schedules.  dah.
                    p = as_node(self.schedule_holders_parent)
                    existing = filter(lambda s: isinstance(s,Schedules) and s.device_link and s.device_link != 'None', p.children_nodes()) #get list of existing bacnet schedule holder nodes under the time node
                    existing = [as_node(s.device_link) for s in existing] #convert to list of bacnet device objects for existing schedules
                    #existing  = [as_node(c.device_link) for c in self.children_nodes(auto_discover=0)]
                    #existing += [as_node(c.device_link) for c in self._nascent_children.values()]
                    devices = filter(lambda d: d not in existing, devices) #filter out any existing devices
                    for d in devices: #only new devices at this point
                        name = d.name #default name will be the device ID
                        if self.discover_mode[:4] == 'name': #then we want name of device
                            try:
                                name = str(d.get_name_property())
                                if self.discover_mode == 'name_and_numeric': #use both ID and name
                                    name += ' (' + d.name + ')'
                            except:
                                pass #if name is not available, use ID only
                        s = Schedules()
                        config = {'name': 'BACnet_' + name,
                                  'parent' : p,
                                  'device_link' : d.as_node_url(),
                                  'discover_mode' : self.discover_mode,
                                  'source' : 'bacnet'}
                        try:
                            s.configure(config)
                            s.start()
                        except:
                            msglog.exception()
                        #s.device_link = d.as_node_url()
                        #s.discover_mode = self.discover_mode
                        #s.source = 'bacnet'
                        #self._nascent_children['RZSched_' + name]=s
                except:
                    msglog.exception()
                #self._been_discovered = 1 #disabled to allow new objects to be discovered
                scheduler.after(61, self._discover_schedules) #run about once a minute
        return #self._nascent_children
    def chidtype(self):
        return None #cannot add or remove bacnet Schedules
class BIN_Configuration(CompositeNode):
    _node_def_id = '6afa0ed2-de74-417a-ad8c-cb486c9327f3'
    _sort_order = 1
    def __init__(self):
        self._persistent_configuration = None
        #self.interface = None #lib.bacnet.network interface object set by Port object during start
        #self.carrier = None 
        self._interfaces = {}
        self._carriers = {}
        self.running = 0
        CompositeNode.__init__(self)
    def children_nodes(self):
        #filter out nodes that are not enabled to avoid warning messaages
        # in place of warnings about nodes not starting there is now an
        # information message for the node(s) that DO start.
        return filter(lambda n: n.is_enabled(), CompositeNode.children_nodes(self))
    def start(self):
        if self.running: return
        CompositeNode.start(self)
        self.running = 1
    def stop(self):
        self.running = 0
#        self.interface_node = None
        self.parent._interfaces = []
        self._interfaces = {}
        self._carriers = {}
        CompositeNode.stop(self)
    def get_carrier(self, network):
        return self._carriers.get(network, None)
    def get_interface(self, network):
        return self._interfaces.get(network, None)
# Holder of IP type interfaces

class BIN_Carrier(CompositeNode):
    def __init__(self):
        self.port = None
        self.addr = None
        self.interface = None
        self._interface_node = None
        self.network = 1
        self._default_device = None #an interface needs to have  device object singleton
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'network', self.network, config, int)
        set_attribute(self, 'discover_interval', 0, config, int)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'network', config, str)
        get_attribute(self, 'discover_interval', config, str)
        return config        
    def _get_device_table(self):
        #return dict(DeviceTable)
        #return devices under this interface
        answer = {}
        for k in DeviceTable.keys():
            if DeviceTable[k].mac_network == self.network:
                answer[k] = DeviceTable[k]
        return answer
    def set_interface_node(self, port):
        self._interface_node = port
    def default_device(self, device=None):
        if self._default_device is None:
            self._default_device = device #assign the default device only once
        else:
            if device is not None:
                raise EConfigurationInvalid('BACnet Carrier: more than one Server Device assigned to Interface network',self._default_device.as_node_url(),device.as_node_url())
        return self._default_device
    def start(self):
        # check parent for other enabled children with the same network number
        # throw exception and prevent start
        for n in self.parent.children_nodes():
            if (n is not self) and n.is_enabled():
                if n.network == self.network: #bad news
                    raise EInvalidValue('BACnet', str(self.network),
                        "Two interfaces with same network number: (%s,%s). BACNET NOT STARTED tarted" % \
                        (n.as_node_url(), self.as_node_url()))
        CompositeNode.start(self)
        
class BIN_IP(BIN_Carrier):
    _node_def_id = '73a5e278-ccf0-4bcb-85fc-7a23f8b707ee'
    def __init__(self):
        BIN_Carrier.__init__(self)
        self.port = 47808
        self.mtu = 1468 #1500 - 20 (IP header, sans options) - 8 (UDP header) - 4 (BVLC)
    def configure(self, config):
        BIN_Carrier.configure(self, config)
        set_attribute(self, 'port', self.port, config, int)
    def configuration(self):
        config = BIN_Carrier.configuration(self)
        get_attribute(self, 'port', config, str)
        return config
    def start(self):
        BIN_Carrier.start(self) #make sure port is started
        #since bbmd and this node may start in any order, make sure bbmd is started
        services = self.parent.parent.get_child('Services')
        if services.has_child('bbmd'):
            services.get_child('bbmd').start_bbmd()
    def _open_interface(self, port_node):
        self._interface_node = port_node
        self.interface = network.open_interface('IP', port_node.name, self.network, self.mtu, port=self.port)
        self.parent._interfaces[self.network] = self.interface
        self.parent._carriers[self.network] = self #this no longer limits us to single carriers
    def _close_interface(self):
        network.close_interface(self.interface)


# Holder of BACnet over Ethernet type interfaces
class BIN_Ethernet(BIN_Carrier):
    _node_def_id = 'b95ed0f3-f9b1-4e11-9b95-4ebbe8656c7e'
    def __init__(self):
        BIN_Carrier.__init__(self)
        self.mtu = 1497 #1500 - 3 (802-2 frame header which might still be used in old ethernet apps)
    def _open_interface(self, port_node):
        self._interface_node = port_node
        self.interface = network.open_interface('Ethernet', port_node.name, self.network, self.mtu)
        self.parent._interfaces[self.network] = self.interface
        self.parent._carriers[self.network] = self #this no longer limits us to single carriers
    def _close_interface(self):
        network.close_interface(self.interface)
# Holder of MSTP RS-485 interfaces
class BIN_MSTP(BIN_Carrier):
    _node_def_id = 'd59ea6fe-a54d-4493-8583-9024c59b0f58'
    def __init__(self):
        BIN_Carrier.__init__(self)
        self.addr = 1
        self.mtu = 501 #501
    def configure(self, config):
        BIN_Carrier.configure(self, config)
        set_attribute(self, 'addr', self.addr, config, int)
    def configuration(self):
        config = BIN_Carrier.configuration(self)
        get_attribute(self, 'addr', config, str)
        return config        
    def _open_interface(self, port_node):
        self._interface_node = port_node
        try:
            n = as_node('/interfaces/' + port_node.name)
            n.open(1)
            fileno = n.file.fileno()
        except:
            msglog.exception()
        self.interface = network.open_interface('MSTP', port_node.name, \
                                                self.network, self.mtu, \
                                                MACaddr=self.addr, \
                                                fd_mstp=fileno)
        self.parent._interfaces[self.network] = self.interface
        self.parent._carriers[self.network] = self #this no longer limits us to single carriers
    def _close_interface(self):
        network.close_interface(self.interface)
        
# an individual ethernet port. BACnet Ethernet or BACnetIP or Comm
# the organization of carrier/interface is reversed on the interface branch (interface/carrier)
class BIN_port(CompositeNode): #physical mediator port, not a bacnet port number
    _node_def_id = '0b922d49-1af1-4d10-abe9-b6e5ebb5a1da' #ip
    def __init__(self):
        CompositeNode.__init__(self)
        self.interface_node = None
        self._who_is_thread = None
    def start(self):
        self.running = 1
        msglog.log ('BACnet service', msglog.types.INFO,  'Start interface: %s %s' % (self.parent.name, self.name,))
        self.parent._open_interface(self)
        CompositeNode.start(self)
        if self._who_is_thread is None: #kick off who_is thread
            self.discover_interval = self.parent.discover_interval #pass it along
            if self.discover_interval: #only start thread if non-zero interval
                self._who_is_thread = _WhoIsThread(self)
                self._who_is_thread.start()
    def stop(self):
        self.running = 0
        if self._who_is_thread:
            self._who_is_thread.should_die()
        self.parent._close_interface()
        CompositeNode.stop(self)
    def _all_descendant_devices(self):  #called from Devices autodiscovery
        return self.parent._get_device_table().values() #lib.bacnet.network._device_table.values()
        #return self.locate_or_create_interface_node()._all_descendant_devices() #is i

class _PersistentBBMDTable(PersistentDataObject):
    def __init__(self, node):
        self.bbmd_table = None
        self.allow_external_edit = None
        self.enable_bbmd = None
        PersistentDataObject.__init__(self, node)
    def save(self):
        PersistentDataObject.save(self)
        msglog.log('interfaces....BBMD', msglog.types.INFO, 'Saved BBMD table to Persistent Storage')
class BIN_BBMD(CompositeNode):
    _node_def_id = 'a472fa57-1eab-4761-8ec7-29e4616366dd'
    def __init__(self):
        CompositeNode.__init__(self)
        self._persistent_table = None
        self._network = None
        self._interface = None
        self._bin_carrier = None
        self.debug = 0
        self._started = 0
        self.allow_external_table_editor = 1
        self.register_as_foreign_device = None
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'enabled', 1, config, int)
        set_attribute(self, 'bbmd_table', [], config) #a list of dictionarys
        set_attribute(self, 'register_as_foreign_device', self.register_as_foreign_device, config)
        set_attribute(self, 'allow_external_table_editor', self.allow_external_table_editor, config, int)
        if self.debug:
            print 'configure bbmd'
            print str(config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        dicts = []
        try:
            table = get_bdt_for(self.get_network())
            for b in table:
                dicts.append( {'ip':b[0], 'udp_port':b[1], 'mask':b[2] } )
        except:
            #must not be started yet
            pass
        self.bbmd_table = dicts
        get_attribute(self, 'bbmd_table', config)
        get_attribute(self, 'allow_external_table_editor', config, str)
        get_attribute(self, 'register_as_foreign_device', config)
        return config
    def start(self):
        if self.get_interface():
            if self.debug:
                print 'normal bbmd start'
            self._start_bbmd()
            if self.debug:
               if self._started: print 'bbmd is running'
               else: print 'bbmd is not running'
        CompositeNode.start(self)
    def _start_bbmd(self):
        enable = 0
        if self._started:
            if self.debug:
                print 'allready started'
            return
        if self.debug:
            print 'start bbmd'
            print self.bbmd_table
            print self.enabled
        if self.enabled and (self.get_interface() is not None): #this is 'node enable', not bbmd enable
            print 'bbmd is enabled'
            p_table = _PersistentBBMDTable(self)
            self._persistent_table = p_table
            p_table.load()
            if p_table.bbmd_table:
                table = p_table.bbmd_table
                enable = p_table.enable_bbmd
            else: #no persistent data, read config
                table = self._convert_bbmd_dict_to_table(self.bbmd_table)
                if len(table):
                    enable = 1
            if self.debug:
                print str(table)
                print 'start bbmd_service'
            start_bbmd_service(self.get_interface(), table, self, self.register_as_foreign_device)
            if enable:
                enable_bbmd(self.get_network())
            self._started = 1
    def start_bbmd(self):
        if self.debug:
            print 'external bbmd start'
        self._start_bbmd()
        if self.debug:
            if self._started: print 'bbmd is running'
            else: print 'bbmd is not running'
    def _convert_bbmd_dict_to_table(self, bbmd_table):
        print 'bbmd table: ', str(bbmd_table)
        table = [] #a list of threepls
        for b in bbmd_table:
            table.append((b['ip'], b['udp_port'], b['mask'],))
            if self.debug:
                print str(b)
        return table
    def stop(self):
        try:
            self._persistent_table = None
            self.disable_bbmd()
        except:
            msglog.exception()
        self._network = None
        CompositeNode.stop(self)
        self._started = 0
    def get_network(self):
        if self._network:
            return self._network
        try:
            self._network = self.bin_carrier.network
        except:
            msglog.log('BBMD', msglog.types.ERR, 'unable to obtain network number')
            msglog.exception()
        return self._network
    def get_interface(self):
        if self._interface:
            return self._interface
        try:
            self._interface = self.bin_carrier.interface
        except:
            msglog.log('BBMD', msglog.types.ERR, 'unable to obtain interface object')
            msglog.exception()
        return self._interface    
    def get(self, skip=0):
        return self.bbmd_status()
    def set(self, bbmd_table):
        self.update_bbmds(self._convert_bbmd_dict_to_table(eval(bbmd_table)))
    def start_bbmd_service(self):
        start_bbmd_service()
    def enable_bbmd(self):
        enable_bbmd(self.get_network())
    def disable_bbmd(self):
        disable_bbmd(self.get_network())
    def bbmd_status(self):
        return bbmd_status(self.get_network())
    def get_bdt_for(self):
        return get_bdt_for(self.get_network())
    def get_bdt_from(self, network, ip, port):
        if network is None:
            network = self.get_network()
        return get_bdt_from(int(network), ip, port)
    def update_bbmds(self, value):
        update_bbmds(self.get_network(), value)
    def validate_bbmds(self, value):
        return validate_bbmds(self.get_network(), value)
    def save_table(self, table): #called from BDT update when a BDT editor updates all the BBMDs
        if self.allow_external_table_editor:
            if self._persistent_table is None:
                self._persistent_table = _PersistentBBMDTable(self)
            p_table = self._persistent_table
            p_table.bbmd_table = table
            p_table.allow_external_edit = self.allow_external_table_editor
            p_table.save()
    # destroys the persistent data object containing the bbmd table
    # subsequint restarts will use info from the broadway.xml instead
    # can be invoked using ?action=invoke%method=destroy_table
    def destroy_table(self): #remove the persistent table from disk
        if self._persistent_table is None:
            self._persistent_table = _PersistentBBMDTable(self)
        self._persistent_table.destroy()
        self._persistent_table = None
    def save_enable_bbmd_flag(self, flag):
        if self._persistent_table is None:
            self._persistent_table = _PersistentBBMDTable(self)
        p_table = self._persistent_table
        p_table.enable_bbmd = flag
        p_table.save()
    def _get_bin_carrier(self):
        if self._bin_carrier is None:
            target = self.parent
            while(target.name != 'services'):
                if isinstance(target, BIN_Carrier):
                    self._bin_carrier = target
                    break
                target = target.parent
        return self._bin_carrier    
    bin_carrier = property(_get_bin_carrier)
    
##
# The BIN holds a branch of Alias nodes that over a deterministic view into the discovered BACnet
# tree under the interface
# 
# This shell may be replaced later by the actual gosh-darned bacnet nodes
#

class _BINDiscoveredAliasAbstractClass(CompositeNode, AutoDiscoveredNode):
    def __init__(self):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.running = 0
        self._been_discovered = 0
        self.debug = debug
    def start(self):
        CompositeNode.start(self)
        self.running = 1
    def stop(self):
        self.running = 0
        CompositeNode.stop(self)
    def nodecmp(self, y_url): #compare two nodes for sorting
        y = as_node(y_url)
        try:
            return cmp(int(self.name), int(y.name))
        except:
            return cmp(self.name, y.name) #incase someone got cute and renamed the node
    def is_array(self):
        return 0
class BINAliasDevice(_BINDiscoveredAliasAbstractClass, BatchManagerMixin):
    _node_def_id = '3d072537-2384-4ddc-aef3-637224fd9887'
    def __init__(self, device_info=None):
        _BINDiscoveredAliasAbstractClass.__init__(self)
        self.network = None
        self.vendor = None
        self.vendor_id = None
        self.opd = opd
        self.data_type_enum = data_type_enum
        self.enum_2_class = enum_2_class
        self.tsenum = tsenum
        self.property_ids = property_ids
        self.est = est
        self.device_info = device_info
        self._interface = None #lib.bacnet.network.interface object
        self._carrier = None #carrier node
        self._object_list = None
        self._rpm = None
        self._cov_support = None
        self._services_supported = None
    def configure(self, config):
        _BINDiscoveredAliasAbstractClass.configure(self, config)
        set_attribute(self, 'network', self.network, config, int)
        self.instance = self.device_instance()
    def configuration(self):
        config = _BINDiscoveredAliasAbstractClass.configuration(self)
        get_attribute(self, 'network', config, str)
        get_attribute(self, 'vendor_id', config, str)
        return config
    def start(self):
        if self.device_info is not None: #hook in vendor info to overlay on standard.
            self.vendor_id = self.device_info.vendor_id #device info overrides any config data.
            self.device_info.create_client_device(self)
        # else:
            # Could be our server device or pre-configured device
            # msglog.log("BACnet Service", msglog.types.INFO,
            #    "Adding NONE device %d" %(self.device_instance()))

        if self.vendor_id:
            self.vendor = vendors.get(self.vendor_id, None)
        if self.vendor: #load vendor specific data tables
            self.opd = self.vendor.get_opd()
            self.data_type_enum = self.vendor.get_data_type_enum()
            self.enum_2_class = self.vendor.get_enum_2_class()
            self.tsenum = self.vendor.get_tsenum()
            self.est = self.vendor.get_est()
            self.property_ids = self.vendor.get_property_ids()
        _BINDiscoveredAliasAbstractClass.start(self)
        self.get_network_number() #for clients, will get network number from _DeviceInfo object
    ##
    # discover what types of objects are used and create Groups to hold the instances
    #
    def _discover_children(self):
        if self.running == 1 and not self._been_discovered:
            try:
                boids = self.get_boids() #this causes read of ObjectList property which is slow in RZ-VAV-B's
                if boids:
                    existing_groups = self._existing_groups()
                    for n in boids:
                        if n.object_type not in existing_groups:
                            if n.object_type in self.opd.keys(): #limit discovery to known types
                                self._nascent_children[str(n.object_type)]=self.child_class()(n.object_type) #inherent filter via dict key
                    #self._been_discovered = 1 #disabled to allow new objects to be discovered
            except:
                msglog.exception()
                if self.debug: print 'error during BINAliasDevice object discover'
        return self._nascent_children
    def discover_child(self, name, **options):
        if self.running == 1:
            if self.vendor_id == 95: #might be RZ-VAV-B
                if self.device_info.max_apdu_len == 480 and self.device_info.can_send_segments == 0: #test for RZ-VAV-B
                    if not self._nascent_children.has_key(name):
                        self._nascent_children[name] = self.child_class()(int(name)) #avoids reading of boids
                    #print self.as_node_url(), name, ' is RZ-VAV-B'
            return AutoDiscoveredNode.discover_child(self, name, **options)
    def device_instance(self):
        return int(self.name)
    def device_cov_capable(self):
        if self._cov_support is not None:
           return self._cov_support
        try:
            services = self.device_proto_services() 
            # msglog.log('BACnet service', msglog.types.INFO,
            #      'Proto services %s ' % (services.__str__()))
            if services.get_bit('SubscribeCOV'):
                self._cov_support = 1 # Assume confirmed COV notif.
                                      # A value other than 1 to be used 
                                      # for unconfirmed notifictaions. 
            else:
                self._cov_support = 0 # COV notifications not supported
        except:
            msglog.exception()
            self._cov_support = 0
        return self._cov_support
    def device_proto_services(self):
        # may be too early to ask for: return self.as_node('8/'+self.name+'/97').get()
        # return the service supported in an array of True/False values
        if self._services_supported is None:
            tags = self.parent._read_device_object_property(self.device_instance(), 97) #get services supported
            self._services_supported = datatype.BACnetServicesSupported(decode=tags)
        return self._services_supported
    def get_name_property(self):
        return self.as_node('8/'+self.name+'/77').get()
    def get_network_number(self):
        if self.network is None:
            if DeviceTable.has_key(self.device_instance()):
                self.network = DeviceTable[self.device_instance()].network
        return self.network
    def get_interface(self):
        if self._interface:
            return self._interface
        try:
            self._interface = self.parent.parent.get_child('Configuration').get_interface(self.get_network_number())
        except:
            msglog.log('Device: ', msglog.types.ERR, 'unable to obtain interface object')
            msglog.exception()
        return self._interface        
    def get_carrier(self):
        if self._carrier:
            return self._carrier
        try:
            self._carrier = self.parent.parent.get_child('Configuration').get_carrier(self.get_network_number())
        except:
            msglog.log('Device: ', msglog.types.ERR, 'unable to obtain carrier node')
            msglog.exception()
        return self._carrier        
        
    #retrieve the object list from the actual device and save a local copy
    #set self._object_list to None and call this to freshen boid list
    def get_boids(self):
        if not self._object_list:
            self._object_list = discover_children_boids(self.device_instance())
        return self._object_list
    def clear_boids(self):
        self._object_list = None
    def _existing_groups(self):
        answer = []
        for n in self._get_children().values():
            if hasattr(n, 'type'):
                answer.append(n.type)
        return answer
    def child_class(self):
        return BINObjectTypeGroup
        
# bacnet objects are grouped according to type
    def is_proxy(self):
        return False
    def get_batch_manager(self, prop=None):
        if prop:
            c3 = prop._comm3segment() #special trane com3 handling
            if c3:
                if self._comm3_batch_manager is None:
                    bm = BatchManager() #make seperate batch manager for all comm3 devices
                    bm.name = self.name + '_comm3_page'
                    bm.instance = self.instance #bacnet device instance number
                    self._comm3_batch_manager = bm
                return self._comm3_batch_manager
        if self._rpm is None: 
            #we do not know about the rpm abilities. Find out
            self._rpm = 0
            try:
                if network.device_accepts_rpm(self.device_instance()):
                    services = self.device_proto_services()
                    self._rpm = services.get_bit('ReadPropertyMultiple') #[14] #rpm
            except:
                msglog.exception()
        if not self._rpm:
            return None
        return self #default batch manager is self
    def nodebrowser_handler(self, nb, path, node, node_url):
        block = [nb.get_default_view(node, node_url)]
        block.append('<div class="node-section node-commands">')
        block.append('<h2 class="section-name">Commands</h2>')
        s = ('%(name)s?action=invoke&method=show_object_names&parameters=yes&Content-Type=application/CSV'
             )% {
            'name':self.name,
            }
        block.append('<a href="%s">CSV file of Objects info</a>' %(s,))
        block.append("</div>")
        return "\n".join(block)
    
    def show_object_names(self,**parameters):
        csv = ''
        for c in self.children_nodes():
            csv += c.show_object_names(**parameters) 
        request=parameters['request']
        request['content-disposition']='attachment;filename=%s.csv'%(self.name)
        return csv
           
##
# This node represents a group of BACnet objects of a particular type.
# It must be named according to the type number of the objects.  Analog Input
# objects are grouped under one of these nodes with the name '0'.  Binary Inputs
# would all be grouped under a ...Group named '4'.
# Children nodes are individual BACnet objects and must be named by their
# instance number
class BINObjectTypeGroup(CompositeNode, AutoDiscoveredNode):
    _node_def_id = '4dd5223b-eac6-4eab-b72b-20cf7d30715f'
    def __init__(self, type=None):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.type = type
        self._been_discovered = 0
        self.running = 0
        self._ids = None
    def configure(self, config):
        CompositeNode.configure(self,config)
        self.device = self.parent
        self.type = self.get_obj_type()
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'type', config, str)
        return config
    def start(self):
        CompositeNode.start(self)
        self.running = 1
    def stop(self):
        self.running = 0
        CompositeNode.stop(self)
    ##
    # discover and create object instances
    #
    def _discover_children(self, force=0):
        if self.name == '8': #this is the device properties object
            if not self.has_child(self.parent.name, auto_discover=0):
                if not self._nascent_children.has_key(self.parent.name):
                    self._nascent_children[self.parent.name]=BINObjectInstance
        if force:
            self._been_discovered = 0
        if self.running == 1 and not self._been_discovered:
            if force:
                try:
                    if self._ids is None:
                        boids = self.parent.get_boids()
                        boids = filter(lambda bid : bid.object_type == self.type, boids)
                        self._ids = [id.instance_number for id in boids]
                    for n in self._ids:
                        if not self.has_child(str(n), auto_discover=0):
                            self._nascent_children['%d' % (n,)]=BINObjectInstance #() #%02d
                except:
                    msglog.exception()
                    if self.debug: print 'error during BINObjectTypeGroup object discover'
            self._been_discovered = 1 #disabled to allow new objects to be discovered
        return self._nascent_children
    def discover_child(self, name, **options):
        if self.running == 1:
            try:
                if self.device.vendor_id == 95: #might be RZ-VAV-B
                    if self.device.device_info.max_apdu_len == 480 and self.device.device_info.can_send_segments == 0: #test for RZ-VAV-B
                        if not self._nascent_children.has_key(name):
                            self._nascent_children[name] = BINObjectInstance #avoids reading of boids
                        #print self.as_node_url(), name, ' is RZ-VAV-B'
                return AutoDiscoveredNode.discover_child(self, name, **options)
            except:
                if self._been_discovered: #required properties have been discovered
                    boids = self.parent.get_boids()
                    boids = filter(lambda bid : bid.object_type == self.type, boids)
                    ids = [id.instance_number for id in boids]
                    if int(name) in ids: #the property exists in the table
                        self._nascent_children[name] = BINObjectInstance #add the new property and then discover it
                        return AutoDiscoveredNode.discover_child(self, name, **options)
                raise
    def force_discovery(self):
        self._discover_children(1)
        #return "Use the browser's Back button and refresh the page"
        return '''
<meta http-equiv="REFRESH" content="0;url=%s">
Use the browser's Back button and refresh the page if not automatically redirected
''' % ('/nodebrowser' + self.as_node_url(),)
    def _existing_instances(self):
        answer = []
        for n in self._get_children().values():
            answer.append(int(n.name)) #it's name is the instance number
        return answer
    def get_obj_type(self):
        if self.type is None:
            self.type = int(self.name)
        return self.type
    def get_batch_manager(self, prop=None):
        return self.parent.get_batch_manager(prop) 
    def show_object_names(self,**parameters):
        self._discover_children(1)
        request = parameters['request']
        request['content-disposition']='attachment;filename=%s.csv'%self.name
        csv = '"type","type_name","instance","name","value","description"\n'
        for c in self.children_nodes():
            try:
                name = c.get_child('77').get()
            except:
                name = 'UNKNOWN NAME'
            try:
                value = str(c._get_default())
            except:
                value = 'Value Not Available'
            try:
                description = c.get_child('28').get()
            except:
                description = 'OPTIONAL' 
                try:
                    c.get_child('28').prune()
                except:
                    pass
            csv += '"%d","%s","%d","%s","%s","%s"\n' % (self.get_obj_type(),
                    BACnetObjectTypeStr.get(self.get_obj_type(),'unknown'),
                    c.get_obj_instance(),
                    name,
                    value,
                    description)
        return csv
    
       
    def nodebrowser_handler(self, nb, path, node, node_url):
        block = [nb.get_default_view(node, node_url)]
        block.append('<div class="node-section node-commands">')
        block.append('<h2 class="section-name">Commands</h2>')
        s = self.name + '?action=invoke&method=force_discovery'
        block.append('<a href="%s">Discover object instances</a><br>\n' %(s,))
        s=('%(name)s?action=invoke&method=show_object_names&Content-Type=application/CSV'
          '&parameters=yes') % {
            'name':self.name,
            }
        block.append('<a href="%s">CSV file of Objects info</a>' %(s,))
        block.append("</div>")
        return "\n".join(block)

def int_or_None(value): # return an int or None for the value
    if value is None: return None
    if value == '*': return None
    return int(value)

class BINObjectInstance(_BINDiscoveredAliasAbstractClass, EventProducerMixin):
    _node_def_id = 'dbe29df0-5e6e-44e5-8ba1-bd5bce732d40'
    def __init__(self):
        _BINDiscoveredAliasAbstractClass.__init__(self)
        EventProducerMixin.__init__(self)
        self.__required_properties = None
        self.__optional_properties = None
        self.__pv_abstract_type = None
        self._has_priority_array = None
    def configure(self, config):
        _BINDiscoveredAliasAbstractClass.configure(self, config)
        self.group = self.parent
        self.instance = self.get_obj_instance()
    def start(self):
        _BINDiscoveredAliasAbstractClass.start(self)
        #set up default property for this object instance
        # _nb_get avoids licensing - called by nodebrowser
        # _get_*wrapper applies licensing the first time it is invoked
        if self._has_present_value():
            self.get = self._get
            #self.get = self._get_wrapper
            self.set = self._set
        elif self.is_device_object():
            self.get = self._get
            #self.get = self._get_wrapper
        elif self._is_binary_type():
            self.get = self._get_binary_pv
            #self.get = self._get_binary_pv_wrapper
        elif self._is_multistate_type():
            self.get = self._get_multistate
            #self.get = self._get_multistate_wrapper
    def _discover_children(self):
        if self.running == 1 and  not self._been_discovered:
            try:
                cs = self._required_properties() #required properties (usually)
                for id in cs:
                    if not self.has_child(str(id), auto_discover=0):
                        self._nascent_children[str(id)] = self.child_class() #pass class only() #yup, that's right
                self._been_discovered = 1 
            except:
                msglog.exception()
                if self.debug: print 'error during BINObjectInstance object discover'
        return self._nascent_children
    def discover_child(self, name, **options):
        if self.running == 1:
            try:
                return AutoDiscoveredNode.discover_child(self, name, **options)
            except:
                if self._been_discovered: #required properties have been discovered
                    opds = self._optional_and_required_properties()
                    if int(name) in opds: #the property exists in the table inldudes optional properties
                        self._nascent_children[name] = self.child_class() #add the new property and then discover it
                        return AutoDiscoveredNode.discover_child(self, name, **options)
                raise
    def get_obj_instance(self):
        return int(self.name)
    def _get(self, skipCache=0, **options):
        if self.is_proxy():
            #we should not be here, we should have been overloaded
            self.set_exception(ENotStarted)
            self._start_exception()  #this may be why
            raise EInvalidCommand('proxy should not use its own get method', self.name)
        if self.is_device_object():
            return self.get_child('112').get(skipCache, **options)
        return self.get_child('85').get(skipCache, **options)
    def _get_binary_pv(self, skipCache=0, **options):
        answer = self._get(skipCache, **options)
        v = answer.value
        if self.has_child('84', auto_discover=0): #polarity
            if self.get_child('84').get(0).value > 0:
                v = not v
        if v: #active
            if self.has_child('4', auto_discover=0):
                return EnumeratedValue(1, str(self.get_child('4').get(0)))
        else: #in_active
            if self.has_child('46', auto_discover=0):
                return EnumeratedValue(0, str(self.get_child('46').get(0)))
        return answer
    def _get_multistate(self, skipCache=0, **options):
        answer = self._get(skipCache, **options)
        if answer is None: return None
        answer = int(answer)
        if self.has_child('110', auto_discover=0):
            state_text = self.get_child('110').get(0)
            if answer < len(state_text):
                return EnumeratedValue(answer, state_text[answer].value)
        return answer
    def _is_commandable(self):
        if self._has_priority_array == None:
            try:
               priority_array_prop = self.get_child('87').get()
               if isinstance(priority_array_prop, BACnetError):    
                  self._has_priority_array = False
               else:
                  self._has_priority_array = True
            except ETimeout,e:
               self._has_priority_array = None #or pass and try again next time
            except:  # which includes ENoSuchName
               self._has_priority_array = False  # and never test it again
        return self._has_priority_array
    def changing_cov(self):
        if self.has_child('85'):
           pv = self.get_child('85')
           return pv._changing_cov
        else:
           return False
    def has_cov(self):
        if self.has_child('85'):
           return self.get_child('85').has_cov(True)
        else:
           return False
    def nb_get(self):
        return self.get()
    def _set(self, value, priority=None, **options):
        global DEFAULT_WRITE_PRIORITY
        pv = self.get_child('85')
        if priority is None:
            priority = DEFAULT_WRITE_PRIORITY
        if self._is_commandable():
            pv.override(value, int(priority), **options)
        else:
            pv.set(value, **options)
        return
    def _get_schedule_summary(self, skipCache=0, **options):
        if self.group.name == '17': # is Schedule Object, not Calendar
            return self._get_schedule_object_summary(skipCache, **options)
        # else must be calendar object
        if self.group.name == '6': # is Calendar
            return self._get_calendar_object_summary(skipCache, **options)
        raise EUnreachableCode("Wrong bacnet object type")
    def _get_calendar_object_summary(self, skipCache=0, **options):
        # return a calendar summary in the same format as a RZSched node
        self.__pv_abstract_type = bool
        #prepare regular weekly schedule for Schedule Objects (not Calendars)
        #a "convent" (bunch of Nones) get it?
        weekly_schedule = [None,None,None,None,None,None,None]  
        daily = self._convert_bacnet_2_schedule_daily(weekly_schedule)
        #prepare the exception schedule
        date_list = [] # date list property
        try:
            #exception schedule is array of BACnetCalendarEntry
            date_list = self.get_child('23').get() 
        except: #this is an option property
            if debug:
                msglog.log('date list retrieval error: ', 
                            self.as_node_url())
                msglog.exception()
        exceptions, excp_daily = self._convert_bacnet_calendar_2_schedule_exceptions( \
                                    date_list)
        # put in same format as regular schedule nodes that UI expects
        # always the same weekly schedule for bacnet
        weekly = [['weekly_schedule', ['monday', 'tuesday', 
                    'wednesday', 'thursday', 'friday', 'saturday','sunday']]]
        return [daily + excp_daily, weekly, [exceptions], 'exceptions']
    def _get_schedule_object_summary(self, skipCache=0, **options):
        # return a schedule summary in the same format as a RZSched node
        # prepare regular weekly schedule for Schedule Objects (not Calendars)
        # a "convent" (bunch of Nones), get it?
        weekly_schedule = [None,None,None,None,None,None,None]  
        try: 
            #weekly schedule array of 7 daily schedules
            weekly_schedule = self.get_child('123').get() 
        except:
            if debug:
                msglog.log('optional weekly schedule missing for: ', 
                            self.as_node_url())
                msglog.exception()
        daily = self._convert_bacnet_2_schedule_daily(weekly_schedule)
        #prepare the exception schedule
        exception_schedules = []
        try:
            #exception schedule is array of BACnetSpecialEvent
            exception_schedules = self.get_child('38').get() 
        except: #this is an option property
            if debug:
                msglog.log('optional exception schedule missing for: ', 
                            self.as_node_url())
                msglog.exception()
        exceptions, excp_daily = self._convert_bacnet_special_events_2_schedule_exceptions( \
                                    exception_schedules)
        #always the same weekly schedule for bacnet
        weekly = [['weekly_schedule', ['monday', 'tuesday', 
                    'wednesday', 'thursday', 'friday', 'saturday','sunday']]]
        return [daily + excp_daily, weekly, [exceptions], 'exceptions']
    def _convert_bacnet_2_schedule_daily(self, weekly_schedule):
        #conver  the bacnet datatype to the RZSched collection of list
        dow = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        daily = []
        for i in range(7):
            daily_schedule = weekly_schedule[i] #get one of the DailySchedules
            if daily_schedule:
                if isinstance(daily_schedule, BACnetDailySchedule):
                    ds = daily_schedule.get_summary()
                elif isinstance(daily_schedule, list):
                    ds = daily_schedule
                else:
                    ds = []
            else: #since no weekly schedule, need a place holder
                ds = []
            ds.insert(0, dow[i])
            daily.append(ds) #insert the name at the beginning of the list
        return daily
    def _convert_bacnet_special_events_2_schedule_exceptions(self, exception_schedules):
        # Convert the bacnet object's Special Event data into an mpx schedule's summary
        #BACnetSpecialEvent ::= SEQUENCE { 
        # period CHOICE { 
        #   calendarEntry  [0] BACnetCalendarEntry, 
        #   calendarReference [1] BACnetObjectIdentifier 
        #     }, 
        # listOfTimeValues [2] SEQUENCE OF BACnetTimeValue, 
        # eventPriority [3] Unsigned (1..16) 
        # }
        exceptions = []
        daily = []
        i = 0
        for ex in exception_schedules: #for each BACnetSpecialEvent
            i += 1
            tvs = ex.value[0]  #(time_values, event_priority, period)
            if tvs: #ignore empty exceptions
                period = ex.value[2] #BACnetCalendarEntry which means it can be a BACnetWeekNDay, BACnetDateRange or BACnetDate
                name = 'exception_'+str(i)
                if isinstance(period, datatype.BACnetCalendarEntry):
                    period_strs = list(period.get_summary_string()) #('date1','optional date2')
                    period_strs.insert(0, name) #name of this exception
                    period_strs.append(name) #name of schedule to use
                    exceptions.append(period_strs)
                    es = ex.get_summary()  #of Time Values
                    es.insert(0, name) #name of schedule
                    daily.append(es) #schedule to go with this exception 
                else: #must be object reference to a calendar which may have many date ranges
                    cal = self.group.device.as_node( 
                        '6/'+str(period.instance_number)+'/23')
                    #c.value = ((start.year, start.month, start.day), (end.year, end.month, end.day))
                    j = 0
                    for c in cal.get()[:1]: #cal returns list of CalendarEntries
                        j += 1
                        #[('start date','end date'),]
                        # provide a fixed date to follow the same format as individual events
                        period_strs = ['01/01/9999',''] #list(c.get_summary_string()) 
                        #the name 'calendar_' is used to indicate the 
                        #associated calendar object
                        # use Calendar Object's name?
                        entry_name = 'calendar_' + str(period.instance_number) #+ '_' + str(j)
                        period_strs.insert(0, entry_name) #name of this exception
                        period_strs.append(entry_name) ##name of schedule to use
                        exceptions.append(period_strs)
                        #@TODO:
                        ##currently expand the one TV sched into many for each
                        ##date or date_range
                        ##in the future we want to have only 1 TV sched for
                        ##all of the calender entries
                        ##the webapi/js/schedulesupport.js will need updating
                        es = ex.get_summary()  #of Time Values
                        es.insert(0, entry_name) #name of schedule
                        daily.append(es) #schedule to go with this exception 
                #print '**** ', period_strs
        exceptions.insert(0,'exceptions') #name of the node
        exceptions.append('weekly_schedule') #default source for schedule
        return (exceptions, daily)  
    def _convert_bacnet_calendar_2_schedule_exceptions(self, date_list):
        # Convert the bacnet Calendar object's Date List data into an mpx schedule's summary
        #BACnetCalendarEntry ::= CHOICE { 
        #   date  [0] Date, 
        #   dateRange [1] BACnetDateRange, 
        #   weekNDay [2] BACnetWeekNDay 
        exceptions = []
        daily = []
        j = 0
        for c in date_list: #cal returns list of CalendarEntries
            j += 1
            #[('start date','end date'),]
            period_strs = list(c.get_summary_string()) 
            #the name 'calendar_' is used to indicate the 
            #associated calendar object
            entry_name = 'calendar_' + str(self.instance) + '_' + str(j)
            period_strs.insert(0, entry_name) #name of this exception
            period_strs.append(entry_name) ##name of schedule to use
            exceptions.append(period_strs)
            #@TODO:
            ##currently expand the one TV sched into many for each
            ##date or date_range
            ##in the future we want to have only 1 TV sched for
            ##all of the calender entries
            ##the webapi/js/schedulesupport.js will need updating
            es = list() #ex.get_summary()  #of Time Values
            es.insert(0, entry_name) #name of schedule
            daily.append(es) #schedule to go with this exception 
        exceptions.insert(0,'exceptions') #name of the node
        exceptions.append('weekly_schedule') #default source for schedule
        return (exceptions, daily)  
    def _set_schedule_summary(self, value, datatype=None, force=None, **options):
        if self.group.name == '17': # is Schedule Object, not Calendar
            return self._set_schedule_object_summary(value, datatype, force, **options)
        # else must be calendar object
        if self.group.name == '6': # is Calendar
            return self._set_calendar_object_summary(value, **options)
        raise EUnreachableCode("Wrong bacnet object type")    
    def _set_schedule_object_summary(self, value, datatype, force, **options):
        # prepare to pass the conversion method for the abstract datatype
        # if the Scheduler node has a specific type use that type as a default
        datatypes =  {'integer':int, 'boolean':bool, 'real':float, 'enumerated':EnumeratedValue}
        conversion = datatypes.get(datatype, None) # if proper type not found, go automatic
        # if the Scheduler node has "force" active, the use that type, if not auto
        # the conversion was saved when last reading the schedule object
        # this gets passed all the way down to datatype.BACnetTimeValue.__init__
        if not force or conversion is None:
            conversion = self.pv_abstract_type
        else:
            self.pv_abstract_type = conversion
        if conversion is None:
            conversion = float
        options['time_value_abstract_type']=conversion
        # set the basic seven day weekly schedule
        try:
            weekly_schedule = self._convert_schedule_daily_2_bacnet(value)
            if weekly_schedule:
                if debug: print 'set weekly schedule: ', weekly_schedule
                self.get_child('123').override(weekly_schedule, **options)
        except:
            msglog.exception()
        # set the Special Events property
        try:
            exception_schedule = self._convert_schedule_exceptions_2_bacnet(value)
            if exception_schedule:
                #look for any calendar objects,
                #[(daily_schedule, priority, date[_range],name,)
                #filter them out and handle separately
                #non_cal_excps contains all exceptions that do not use a
                #Calendar objct
                non_cal_excps = filter(lambda x:
                    not (x[3].startswith('calendar_')), exception_schedule)
                #stip off name at end of tuple to match format expected
                non_cal_excps = [x[:3] for x in non_cal_excps]
                #collect calendar object based exceptions
                cal_excps = filter(lambda x:
                    x[3].startswith('calendar_'), exception_schedule)
                calendars = {} #dict of lists of CalendarEntry objects
                excpts = {} #dict of daily_scheds
                for c in cal_excps:
                    #name of exception entry is:
                    #calendar_instancenumber_indexnumber
                    instance_number = int(c[3].split('_')[1])
                    if calendars.get(instance_number,None) is None:
                        calendars[instance_number]=[] #new calendar discovered
                    calendars[instance_number].append(c[2]) #CalendarEntry
                    #collect (daily_schedule, priority, Object ID of Calendar)
                    #this entry will get overwritten for each CalendarEntry
                    #last one wins, "long" datatype is flag for bacnet ID
                    #(daily_schedule, priority,) + (cal_obj_ID)
                    excpts[instance_number] = c[:2] + \
                        (long(0x1800000 + instance_number),)
                cal_excps = excpts.values()
                ##for debugging, remove later
                self.non_cal_excps = non_cal_excps
                self.cal_excps = cal_excps
                self.calendars = calendars
                self.excpts = excpts
                ##end debug
                if debug: print 'set exceptions schedule: ', exception_schedule
                self.get_child('38').override(non_cal_excps + cal_excps, **options)
        except:
            msglog.exception()
    def _set_calendar_object_summary(self, value, **options):
        # set the Date List property on a Calendar Object
        try:
            exception_schedule = self._convert_calendar_exceptions_2_bacnet(value)
            #collect calendar object based exceptions
            cal_excps = exception_schedule # use all exceptions
            date_list = [] #lists of Date, Date-Range, Week-N-Day 
            #excpts = {} #dict of daily_scheds
            for c in cal_excps:
                #name of exception entry is not relavent here
                date_list.append(c[2]) #CalendarEntry
            ##for debugging, remove later
            self.cal_excps = cal_excps
            ##end debug
            self.get_child('23').override(date_list)
        except:
            msglog.exception()
    def _convert_schedule_daily_2_bacnet(self, value):
        daily, weekly, exceptions, dummy = value
        if daily:
            weekly_schedule_dict = {}
            for d in daily: #convert incoming daily schedule into fixed format bacnet weekly schedule
                weekly_schedule_dict[d[0]] = d[1:]
            weekly_schedule = []
            #sort into bacnet ordained order and reformat into a list of 
            #structures compatible with the datatypes used for this property
            #['sunday', ['1', '07:00:00', '1'], ['2', '16:01:00', '0']]
            for k in ['monday', 'tuesday', 'wednesday', 'thursday',
                      'friday', 'saturday','sunday']:
                daily_schedule_dict = {}
                daily_schedule = []
                if weekly_schedule_dict.has_key(k): #just in case.  The format *should* always include each day
                    for d in weekly_schedule_dict[k]:
                        daily_schedule_dict[d[0]] = d[1:] #use entry name as key
                    keys = daily_schedule_dict.keys()
                    keys.sort() #entries are named entry0, entry1, etc and this puts them in correct order
                    for k in keys:
                        daily_schedule.append(daily_schedule_dict[k])
                weekly_schedule.append(daily_schedule)
            return weekly_schedule
        return None
    def _convert_schedule_exceptions_2_bacnet(self, value, **options):
        #see service/schedule/scheduler.py get_summary for format        
        daily, weekly, exceptions, dummy = value
        priority = options.get('priority', 16) #default priority can be overridden by option
        #check for any exceptions & that they have one or more entries
        if exceptions and exceptions[0] and exceptions[0][1] and daily:
            weekly_schedule_dict = {}
            for d in daily: #convert incoming daily schedule into fixed format bacnet weekly schedule
                weekly_schedule_dict[d[0]] = d[1:] #d[0]=name, d[1:]=entries
            #weekly_schedule now holds all Daily scheds, even MTWTFS types
            #filter exceptiexceptions  list out of structure, 
            #  trim off the name 'exceptions' and the default schedule
            exceptions = exceptions[0][1:-1] #now have list of Date Ranges
            exception_schedule = [] #prepare answer list object
            exception_schedule_dict = {} #convert exception Date list to dict
            for ex in exceptions: #put together the exceptions values to set on the property
                exception_schedule_dict[ex[0]] = ex[1:] #dict[name]=date range
            exps = exception_schedule_dict.keys()
            exps.sort() #the names of the date[ranges] are alphabetical
            #x is name of the exception: exception_1, exception_2, etc
            for x in exps: #for each exception, by name
                #we are going to find the Daily sched that is used by exception
                daily_schedule_dict = {} 
                daily_schedule = []
                #get name of Daily sched.  It is last element in list
                daily_schedule_name = exception_schedule_dict[x][-1]
                #just in case.  The format *should* always include each day
                if weekly_schedule_dict.has_key(daily_schedule_name):
                    #loop through the daily schedule for the exception
                    for d in weekly_schedule_dict[daily_schedule_name]: 
                        daily_schedule_dict[d[0]] = d[1:] #use entry name as key
                    keys = daily_schedule_dict.keys()
                    keys.sort() #entries are named entry0, entry1, etc and this puts them in correct order
                    for k in keys: #place time - value entries in a list in the order of their names
                        daily_schedule.append(daily_schedule_dict[k])
                #get first date string and convert to BACnetDate format
                ds = exception_schedule_dict[x][0] #holiday date string, '08/20/2008' or '14/2/*/1' first tues of even months
                d = [int_or_None(i) for i in ds.split('/')] #[mm,dd,yyyy] or [mm, dow, yyyy, wom]
                #move year to front to match YYYY, MM, DD order for BACnetDate
                d.insert(0,d.pop(2)) 
                d = tuple(d)
                #if 2nd date string is present, then convert to BACnetDateRange format
                ds = exception_schedule_dict[x][1] #holiday date string, '08/20/2008'
                if ds: #length is greater than 0 so this must be a date range
                    d2 = [int_or_None(i) for i in ds.split('/')] #[mm,dd,yyyy]
                    d2.insert(0,d2.pop(2)) #move year to front to match YYYY, MM, DD order for BACnetDate
                    d = (d, tuple(d2)) #tuple of two tuples is how Calendar datetype determines CHOICE is date range
                #reformat summary structure into form compatible with bacnet
                #([('12:34:56', 73.0),('11:22:33', 74.0),],16,(2008, 8, 20))
                exception_schedule.append((daily_schedule, priority, d,x,))
            if debug: print 'set exceptions schedule: ', exception_schedule
            return exception_schedule
        return None
    def _convert_calendar_exceptions_2_bacnet(self, value, **options):
        # convert the schedule format to a date list        
        daily, weekly, exceptions, dummy = value
        #priority = 16 # ignored options.get('priority', 16) #default priority can be overridden by option
        #check for any exceptions & that they have one or more entries
        if exceptions and exceptions[0]: # and exceptions[0][1] and daily:
            #filter exceptions  list out of structure, 
            #  trim off the name 'exceptions' and the default schedule
            exceptions = exceptions[0][1:-1] #now have list of Date Ranges
            exception_schedule = [] #prepare answer list object
            exception_schedule_dict = {} #convert exception Date list to dict
            for ex in exceptions: #put together the exceptions values to set on the property
                exception_schedule_dict[ex[0]] = ex[1:] #dict[name]=date range
            exps = exception_schedule_dict.keys()
            exps.sort() #the names of the date[ranges] are alphabetical
            #x is name of the exception: exception_1, exception_2, etc
            for x in exps: #for each exception, by name
                #get first date string and convert to BACnetDate or Week-N-Day format
                ds = exception_schedule_dict[x][0] #holiday date string, '08/20/2008' or '11/4/*/4' (thanksgiving)
                d = [int_or_None(i) for i in ds.split('/')] #[mm,dd,yyyy] or [mm,dd,yyyy,wom]
                #move year to front to match YYYY, MM, DD order for BACnetDate
                d.insert(0,d.pop(2)) 
                d = tuple(d)
                #if 2nd date string is present, then convert to BACnetDateRange format
                ds = exception_schedule_dict[x][1] #holiday date string, '08/20/2008'
                if ds: #length is greater than 0 so this must be a date range
                    d2 = [int_or_None(i) for i in ds.split('/')] #[mm,dd,yyyy]
                    d2.insert(0,d2.pop(2)) #move year to front to match YYYY, MM, DD order for BACnetDate
                    d = (d, tuple(d2)) #tuple of two tuples is how Calendar datetype determines CHOICE is date range
                #reformat summary structure into form compatible with bacnet
                #([('12:34:56', 73.0),('11:22:33', 74.0),],16,(2008, 8, 20, 7))
                #exception_schedule.append((daily_schedule, priority, d,x,))
                exception_schedule.append((None, None, d,x,))
            if debug: print 'set exceptions schedule: ', exception_schedule
            return exception_schedule
        return None
    def _get_default(self): #used by parents show object names
        try: #I read that this is faster than a key lookup in a dict
            return self.get()
        except AttributeError:
            return 'N/A'
        except Exception, e:
            return str(e)
    def _required_properties(self): #if optional info is in table, then returns required properties only
        if self.__required_properties:
            return self.__required_properties
        answer = []
        opds = self.group.device.opd[self.group.type]
        for k in opds.keys():
            if len(opds[k]) > 5: #then it has the optional property flag
                if opds[k][5] == 0: #required property
                    answer.append(k)
            else:
                answer.append(k) #since we don't know, add it
        self.__required_properties = answer
        return answer
    def _optional_and_required_properties(self):
        if self.__optional_properties is None:
            self.__optional_properties = self.group.device.opd[self.group.type].keys()
        return self.__optional_properties # includes required properties too
    def _has_present_value(self):
        try:
            return 85 in self._required_properties()
        except:
            pass
        return False
    def _is_binary_type(self):
        return self.group.type in (3, 4, 5,)
    def _is_schedule_type(self):
        return self.group.type == 17
    def _is_multistate_type(self):
        return self.group.type in (13, 14, 19,)
    def is_proxy(self):
        return self.group.device.is_proxy()
    def child_class(self):
        return BINPropertyInstance
    def is_device_object(self):
        return self.group.get_obj_type() == 8
    ## batch manager support that is relayed to the present value property child for times when this node is subscribed
    def _get_batch_manager(self, prop=None):
        return self.parent.get_batch_manager(prop)
    def get_batch_manager(self, prop=None):
        return self.get_child('85').get_batch_manager()
    def set_batch_manager(self, bm):
        self.get_child('85').set_batch_manager(bm)
    def get_obj_identifier(self):
        return BACnetObjectIdentifier(self.group.type, self.instance)
    def get_property_tuple(self):
        return self.get_child('85').get_property_tuple()
    def get_result(self, skipcache=0, **keywords):
        return self.get_child('85').get_result(skipcache, **keywords)
    def decoder(self):
        return self.get_child('85').decoder()
    def is_array(self):
        return self.get_child('85').is_array()
    def _comm3segment(self):
        return self.get_child('85')._comm3segment()
    def _get_pv_abstract_type(self):
        if self.__pv_abstract_type is None:
            try:
                #first get the present value and store the abstract datatype
                #so we can be sure to send back the same type
                pv = self.get_child('85').get().value
                if isinstance(pv, float):
                    self.__pv_abstract_type = float
                elif isinstance(pv, EnumeratedValue):
                    self.__pv_abstract_type = EnumeratedValue
                elif isinstance(pv, int):
                    self.__pv_abstract_type = int
                elif isinstance(pv, bool):
                    self.__pv_abstract_type = bool
            except:
                if debug:
                    msglog.log('unable to determine abstract type for: ', 
                                self.as_node_url())
                    msglog.exception()
        return self.__pv_abstract_type
    def _set_pv_abstract_type(self, abstract_type):
        self.__pv_abstract_type = abstract_type
    pv_abstract_type = property(_get_pv_abstract_type, _set_pv_abstract_type)

class BINPropertyInstance(_BINDiscoveredAliasAbstractClass, EventProducerMixin):
    _node_def_id = 'fd37599b-5bc7-4c27-a009-1254f480d432'
    def __init__(self):
        _BINDiscoveredAliasAbstractClass.__init__(self)
        EventProducerMixin.__init__(self)
        self._batch_manager = None
        self._data_class = None
        self._array_limit = None
        self._is_array = False
        self._is_list = False
        self._array_limit = None
        self._array_length = None
        self._ucm_page = None
        self.enum_string_map = {}
        self.T_out = 3
        self._segmentation_error = 0 #used by array types
        self.ttl = 1 #one second default time to live for cache (mostly for array element access)
        self.last_result = None
        self._last_result = None
        self._vendor_id = None
        self._has_cov =  None
        self._changing_cov = True
        self._cov_refresh_scheduled = None
        self._cov_request_pending = False
        self.get_batch_manager = self._get_batch_manager
        self._is_obj_instance_referred = None
        self._is_pv_prop_referred = None
    def configure(self, config):
        _BINDiscoveredAliasAbstractClass.configure(self,config)
        self.object = self.parent
        self.id = self.get_property_id()
    def configuration(self):
        config = _BINDiscoveredAliasAbstractClass.configuration(self)
        self.property_id_str = self.object.group.device.property_ids[self.id]
        get_attribute(self, 'property_id_str', config, str)
        if self.enum_string_map is not None:
            get_attribute(self, 'enum_string_map', config, str)
        get_attribute(self,'_is_array',config,str)
        get_attribute(self,'_is_list',config,str)
        get_attribute(self,'_has_cov',config,str)
        return config        
    def start(self):
        type = self.object.group.type
        device = self.object.group.device
        data_type_id, self._array_limit, self._is_array, self._is_list, self._ucm_page = \
                    (device.opd[type][self.id])[:5]
        try:
            self._data_class = device.enum_2_class[device.data_type_enum[data_type_id]]
        except:
            msglog.log('BACnet service', msglog.types.WARN,'Unsupported data type: %d, property: %s' % (data_type_id, self.as_node_url()))
            self._data_class = datatype._data #try something
        aKey = (type,self.id,)
        if device.tsenum.has_key(aKey):
            self.enum_string_map = device.est[device.tsenum[aKey]] #table has priorty over class
        self._property_tuple = (type,self.object.instance, self.id,)
        if not self._is_array: #cannot directly set arrays, must be done in children
            self.set = self._set
        #certain properties get read one time only since they never change
        if aKey in ((8,97),(8,96),(8,107),(8,122),(8,76)): #services supported
            self.ttl = float('inf')
        _BINDiscoveredAliasAbstractClass.start(self)
        #need to create self.bacnet_property object
    def _array_element_class(self):
        return BINPropertyArrayElement
    # discover and create property aliases (aliai?)
    #
    def _discover_children(self):
        if not self._been_discovered:
            try:
                if self._is_array:
                    a = self._get_array_length() #this will throw an exception if device not ready
                    if a > 0:
                        #element 0 is length of array
                        if not self.has_child('0', auto_discover=0):
                            self._nascent_children['0'] = PropAttr('_get_array_length')
                        for i in range(a):
                            name = '%d' % (i+1) #index offset is 1
                            if not self.has_child(name, auto_discover=0):
                                self._nascent_children[name] = self._array_element_class() #(i) #was %02d
                self._been_discovered = 1 #do this just once
            except:
                # don't display the error unless in Debug
                if debug:
                    msglog.exception()
        return self._nascent_children
    # inner attribute access
    def is_commandable(self):
        return self.name == '85'  #add test for object/property type to really determine commandable
    def is_priority_array(self):
        return self.name == '87'
    def is_relinquish_default(self):
        return self.name == '104'
    def is_object_list(self):
        return self.name == '76'
    def get_obj_instance(self):
        return self.object.instance
    def get_property_id(self):
        return int(self.name)
    def is_binary_pv(self):
        return (self.id == 85) and (self.object.group.type in (3,4,5))
    def is_schedule_pv(self):
        return (self.id == 85) and (self.object.group.type in (17,))
    # reading from the device property
    def nb_get(self):
        return self.get()
    def get(self, skipcache=0, **keywords):
        rp = self.get_result(skipcache, **keywords)
        if isinstance(rp, Callback):
            return rp
        return rp.value
    def get_result(self, skipcache=0, **keywords):
        if (skipcache == 0) and self.last_result: #we've been here before
            if uptime.secs() < (self.last_result.timestamp + self.ttl):
                return self.last_result
        if keywords.has_key('T_OUT'):
            self.T_out = keywords['T_OUT']
        if self._is_array:
            self.last_result = self._get_array_result(skipcache, **keywords)
        else:
            self.last_result = self._get_result(skipcache, **keywords)
        return self.last_result
    def _get_result(self, skipcache=0, **keywords):
        #see if this a callback type request and add our layer to the cake
        if keywords.has_key('callback'):
            keywords['callback'].callback(self.get_result_callback)
        if self.has_cov() and skipcache == 0:
           return self._last_result
        try:
            rp = read_property_g3(self.object.group.device.instance, self._property_tuple, self.T_out, **keywords)
            if isinstance(rp, Callback):
                return rp #used as flag
            tags = rp.property_value
            value = self.decode(tags)
            # CSCte88469 - return simple data types for binary property values
            # @fixme Either all enumerated values should just be int's or we
            #        should remove this and rely on edtlib
            if self.is_binary_pv():
                value = int(value)
        except BACnetNPDU, e:
            value = e #return the exception object
        answer = Result()
        answer.value = value
        answer.timestamp = uptime.secs()
        self._last_result = answer
        return answer
    def get_result_callback(self, rp):  #called all the way from the TSM callback upon completion
        try:
            if isinstance(rp, Exception):
                raise rp
            tags = rp.property_value
            value = self.decode(tags)
        except Exception, e: #any other exception
            return e
        except:
            import sys
            return Exception(sys.exc_info()[0])
        answer = Result()
        answer.value = value
        answer.timestamp = uptime.secs()
        self._last_result = answer
        return answer
    def decode(self, tags):
        if self._is_array or self._is_list:
            return self._decode_array(tags)
        return self._data_class(decode=tags, string_map=self.enum_string_map) #, owner=self)
    # write to the device property
    def _set(self, value):
        self.override(value)
    def override(self, value, priority=None, **keywords): #override is different from set() on a regular property.  it is only for PV
        keywords['string_map']=self.enum_string_map
        # Conversion for BACnet schedule object present value may have to be detected at runtime.
        # Otherwise, set up a default conversion, which does nothing. 
        conversion = lambda x: x
        # note: self._data_class is *not* an instance, thus == instead of isinstance
        # is used..
        if self.is_schedule_pv() and self._data_class == datatype.BACnetAbstract:
            if not self.object.pv_abstract_type is None:
                conversion = self.object.pv_abstract_type
        if self._is_array or self._is_list:
            if type(value) == types.StringType:
                value = eval(value)
            if not(type(value) == tuple or type(value) == list):
                raise EInvalidValue("BACnet","ERROR",'attempt to write list or array datatype with non-iterable')
            data = [self._data_class(conversion(v), **keywords) for v in value]
            tags = []
            for d in data:
                tags.extend(d.as_tags())
        else: #non-array or list type
            data = self._data_class(conversion(value), **keywords) #, owner=self)
            tags = data.as_tags()
        answer =  write_property_g3(self.object.group.device.instance, self._property_tuple, tags, priority)
        self.get(1) 
        return answer
    # the following methods are helpers for the batch manager
    def _comm3segment(self): #trane spdcifig
        return self._ucm_page
    def get_property_tuple(self):
        return self._property_tuple
    def decoder(self):
        return self #used by batchmanager
    def _get_batch_manager(self):
        if self._batch_manager is None:
            # Do not set local batch manager here.  ALWAYS return parent's
            # unless the batch manager was directly overwritten by something
            # using set_batch_manager below
            return self.object._get_batch_manager(self)
        return self._batch_manager
    def _get_local_batch_manager(self, prop=None):
        return self._batch_manager
    def set_batch_manager(self, m):
        self._batch_manager = m
        self.get_batch_manager = self._get_local_batch_manager
    def _can_get_multiple(self):
        return 1
    def changing_cov(self):
        if (self.id == 85 or self.id == 111):
            return self._changing_cov
        else:
            return False
    def has_cov(self, obj_instance_referred = False):
        global cov_enabled
        if self.object.group.type in (0,1,2,3,4,5,13,14,19):
            if (self.id == 85 or self.id == 111) and obj_instance_referred is False:
                self._is_pv_prop_referred = True
            elif obj_instance_referred is True:
                self._is_obj_instance_referred = True
        if cov_enabled is False:
            return False
        elif cov_enabled is True:
            if self._has_cov is not None:
                # msglog.log('BACnet service', msglog.types.INFO,
                #      'Property has_cov: %d' % (self._has_cov)) 
                return self._has_cov
            if (self.id == 85 or self.id == 111) and \
               (self.object.group.type in (0,1,2,3,4,5,13,14,19)):
                # Subscription done per object for now, while
                # checking has_cov for present value property and 
                # status-flags. This can be extended to provide
                # per-property subscription.
                cov_cap = self.object.group.device.device_cov_capable()
                if cov_cap == 1:
                    self.make_cov_request()
                else:
                    self._has_cov = False
            else:
                self._has_cov = False
            # msglog.log('BACnet service', msglog.types.INFO, 
            #            'Property has_cov False')
            return False 
    def make_cov_request(self):
        # put into queue request
        if self._cov_request_pending:
            return
        self._cov_request_pending = True
        # Send COV subscription requests, give a few seconds for
        # initial BACnet read responses to get processed.
        self._cov_refresh_scheduled = scheduler.seconds_from_now_do(60, \
        self.schedule_cov_request)
    def schedule_cov_request(self):
        thread_pool.NORMAL.queue_noresult(self.send_cov_request)
    def send_cov_request(self):
        # msglog.log('BACnet service', msglog.types.INFO, 
        #            'Send cov subscription req')
        device = self.object.group.device
        if device.device_cov_capable() == 1: 
           subscription_type = True # confirmed notifications
        else:
           subscription_type = False # A value other than 1 can be used
                                     # for unconfirmed notifs later 
        try:
            rsp = cov_subscription_request(device.instance, \
                  self._property_tuple, subscription_type, \
                  cov_subscription_lifetime, cov_subscription_pid)
            # Successful subscription if no exception, assign 
            # value to _has_cov.
            old_cov = self._has_cov
            self._has_cov = True
            if old_cov is None or old_cov is False:
                value = 1 # ECovNode 
                if self._is_pv_prop_referred is True: 
                    cov_toggle = ChangingCovEvent(self, value, uptime.secs())
                    self.event_generate(cov_toggle)
                if self._is_obj_instance_referred is True:
                    cov_toggle_parent = ChangingCovEvent(self.parent, value, uptime.secs())
                    self.parent.event_generate(cov_toggle_parent)
            # Schedule periodic resubscribe messages to deal with
            # the case where the COV server reboots without saving
            # subscriptions.
            self._cov_refresh_scheduled = scheduler.after(3 * \
            cov_subscription_refresh_interval, self.schedule_cov_request)

        except:
            old_cov = self._has_cov
            self._has_cov = False
            if old_cov is True:
                value = 2 # ENonCovNode                 
                if self._is_pv_prop_referred is True: 
                    cov_toggle = ChangingCovEvent(self, value, uptime.secs())
                    self.event_generate(cov_toggle)
                if self._is_obj_instance_referred is True:
                    cov_toggle_parent = ChangingCovEvent(self.parent, value, uptime.secs())
                    self.parent.event_generate(cov_toggle_parent)
            # Mostly failure due to transient conditions, or temporary
            # resource constraints at remote device, try again.
            self._cov_refresh_scheduled = scheduler.after(2 * \
            cov_subscription_refresh_interval, self.schedule_cov_request)

        finally:
            self._cov_request_pending = False

    def cov_notif_processing(self, tags, pid, time_remaining):
        if self._has_cov is not True:
            # msglog.log('BACnet service', msglog.types.INFO,
            #     'cov notif proc ignored') 
            # Some devices may send unsolicited COV notifs
            # upon reboot or under normal conditions.
            # Ignoring for now.
            return

        # Ignoring pid for now.

        # Handle response from network thread that receives cov notifs 
        # We need a mechanism to throttle the point that receives
        # storms of COV notifications.
        value = self.decode(tags)
        if self.is_binary_pv():
            value = int(value)
        answer = Result()
        answer.value = value
        answer.timestamp = uptime.secs()
        if self._last_result == None:
          old_value = None
        else:
          old_value = self._last_result.value
        self._last_result = answer
        # Consider --- if (old_value != value):
        # msglog.log('BACnet service', msglog.types.INFO,
        #  'cov notif proc change in val %s' %(str(value)))
        # Change could be in present-value or status-flags
        # or both.
        if self._is_pv_prop_referred is True:
            cov_event = ChangeOfValueEvent(self, old_value, \
                                           value, uptime.secs())
            self.event_generate(cov_event)
        if self._is_obj_instance_referred is True:
            cov_event_parent = ChangeOfValueEvent(self.parent, old_value, \
                                                  value, uptime.secs())
            self.parent.event_generate(cov_event_parent)
            # Do we need to schedule a resubscription here,
            # time_remaining can be used to determine this.
            # if self._cov_refresh_scheduled:
            #    self._cov_refresh_scheduled = 
            #    scheduler.after(cov_subscription_refresh_interval, \
            #    self.schedule_cov_request)
    def is_array(self):
        return self._is_array
    # array and list helpers
    def _get_array_length(self): #client has to ask, server already knows
        if self._array_length is None: #should we only read this once?
            if self._array_limit: #fixed size array
                self._array_length = self._array_limit
            else: #variable size array
                l = read_property_g3(self.object.group.device.instance, \
                             self._property_tuple+(0,), self.T_out)
                self._array_length = l.property_value[0].value
        return self._array_length
    def _decode_array(self, tags):
        data = str_list() #[] #this helps the nodebrowser display better
        if self._data_class.can_decode_from_list: #class variable.  Needed for CONSTRUCTED (glued together Application tags) tags when used in array
            #print 'can decode lists'
            dt = self._data_class(string_map=self.enum_string_map) #create a blank one to call helper fucntion
            seqs = dt.decode_list_of(tags)
            #print 'did decode lists'
            for s in seqs:
                #print 'decoding a sequence'
                d = self._data_class(string_map=self.enum_string_map)
                try:
                    d.decode_from_sequence(s)
                except Exception, ex:
                    msglog.exception()
                    d = ex
                data.append(d)
        else: #if there is a one to one tag to data object relationship, this will work, otherwise the data_class needs to implement list handlers
            for t in tags:
               if debug: print 'decode array = ', str(t)
               d = self._data_class(decode=[t], string_map=self.enum_string_map)
               data.append(d)
        return data
    def _get_array_result(self,skipCache=0, **keywords):
        #first try the normal way to get all at once
        # if that fails do each element in an RPM
        # if that fails do each element seperately
        if not hasattr(self, '_segmentation_error'): self._segmentation_error = 0
        if self._segmentation_error == 0:
            if self._vendor_id != 2: #trane always uses rpm so skip trying to get it all at once
                try:
                    answer = self._get_result(skipCache, **keywords)
                    if isinstance(answer, BACnetException):
                        raise answer
                    if isinstance(answer.value, BACnetException):
                        raise answer.value
                    return answer
                except BACnetException, e:
                    #print 'bacnet exception'
                    pass
            self._segmentation_error = 1 #we have a bacnet error response to last request. fallback

        answer = []
        if self._segmentation_error == 1:    
            #get length of list.  We are currently ignoring the table and reading the length
            self._array_limit = self._get_array_length()
            self._segmentation_error = 2
        if self._segmentation_error == 2:
            #print 'start array method 2'
            #try rpm first
            #comm3 text strings are assumed to be static and we only read them one time per framework startup
            if self._ucm_page:
                if self._data_class == BACnetCharacterString:
                    if self.last_result is not None:
                        if keywords.has_key('callback'):
                            keywords['callback'].unwind_callbacks(self.last_result)
                            return keywords['callback']
                        return self.last_result
            try:
                pids = []
                pid = self._property_tuple[2]
                if self._array_limit > 1:
                    for i in range(1, self._array_limit+1):
                        pids.append((pid, i,))
                    props = (self._property_tuple[0], self._property_tuple[1], tuple(pids))
                    if keywords.has_key('callback'):
                        keywords['callback'].callback(self._get_array_result_callback)
                    rars = _read_property_multiple_g3(self.object.group.device.device_instance(), [props], self.T_out, **keywords)
                    if isinstance(rars, Callback):
                        return rars #used as flag to indcate callback method will be used
                    rar = rars.pop(0)
                    lrs = copy.copy(rar.list_of_results)
                    while(lrs):
                        lr = lrs.pop(0)
                        pe = lr.property_access_error
                        pv = lr.property_value
                        if not isinstance(pv, OPTIONAL):
                            answer.extend(pv)
                        elif not isinstance(pe, OPTIONAL):
                            raise pe
                    #print 'array method 2 completed'
            except Exception, e:
                #print 'try array method 3'
                #print str(e)
                if self._vendor_id != 2:
                    self._segmentation_error = 3 #last ditch effort to use RP on each element
                else:
                    raise e #trane arrays only use rpm method so don't bother with RP
        if self._segmentation_error == 3:
            for i in range(1, self._array_length+1):
                obj_tag = read_property_g3(self.object.group.device.device_instance(), self._property_tuple+(i,), self.T_out).property_value[0]
                answer.append(obj_tag)
            #print 'array method 3 completed'

        answer = self.decode(answer) #convert from tags to data objects
        self.last_result = Result()
        self.last_result.value = answer
        self.last_result.timestamp = uptime.secs()
        return self.last_result
    def _get_array_result_callback(self, rars):  #called all the way from the TSM callback upon completion
        answer = []
        try:
            if isinstance(rars, Exception):
                raise rars
            rar = rars.pop(0)
            lrs = copy.copy(rar.list_of_results)
            while(lrs):
                lr = lrs.pop(0)
                pe = lr.property_access_error
                pv = lr.property_value
                if not isinstance(pv, OPTIONAL):
                    answer.extend(pv)
                elif not isinstance(pe, OPTIONAL):
                    raise pe
            answer = self.decode(answer)
            self.last_result = Result()
            self.last_result.value = answer
            self.last_result.timestamp = uptime.secs()
            return self.last_result
        except Exception, e: #any other exception
            r = Result(e,uptime.secs())
            r.value = e
            r.timestamp = uptime.secs()
            return r
    def nodebrowser_handler(self, nb, path, node, node_url):
        block = [nb.get_default_view(node, node_url)]
        block.append('<div class="node-section node-commands">')
        block.append('<h2 class="section-name">Commands</h2>')
        s = self.name + '?action=invoke&method=refresh_cache'
        block.append('<a href="%s">Force refresh of cached property value</a>' %(s,))
        block.append("</div>")
        return "\n".join(block)
    def refresh_cache(self):
        return str(self.get(1))
#class BINPropertyMagnitude(CompositeNode):
class PropAttr(CompositeNode):
    def __init__(self, attribute_name=None, setable=0):
        CompositeNode.__init__(self)
        self._attribute_name = attribute_name
        if setable:
            self.set = self._set
    def get(self, skipcache=0):
        if self._attribute_name:
            try:
                attr = getattr(self.parent, self._attribute_name)
                if callable(attr):
                    return eval('self.parent.' + self._attribute_name + '()')
                return eval('self.parent.' + self._attribute_name)
            except Exception, e:
                return str(e)
        return None
    def _set(self, value):
        if self._attribute_name:
            attr = getattr(self.parent, self._attribute_name)
            if callable(attr):
                eval('self.parent.' + self._attribute_name + '(' + str(value) + ')')
                return
            eval('self.parent.' + self._attribute_name + '=' + str(value))
                
class BINPropertyArrayElement(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        #self.index = index #0 based index into array
        self._batch_manager = None
        self.__use_parent_batch_manager = True
        self._present_value_node = None
    def configure(self, config):
        CompositeNode.configure(self, config)
        self.index = int(self.name) - 1
    def get(self, skipCache=0):
        if self.name == '0': #return length of array
            return self.parent._get_array_length()
        answer = self.parent.get(0) #if we don't use timed cache, things slow WAY down
        if answer is None:
            return None
        return answer[self.index]
    def can_get_multiple(self):
        return self.parent.can_get_multiple()
    def _property_tuple(self):
        return self.parent.property_tuple() + (self.index + 1,)
    def _comm3segment(self):
        return self.parent._comm3segment()
    def set(self, value, priority=None, asyncOK=1):
        if self.name == '0':
            raise EImmutable(self.as_node_url()) #is this true for all arrays?
        if self.parent.is_priority_array():
            if self._present_value_node is None:
                self._present_value_node = self.parent.parent.get_child('85')
            self._present_value_node.override(value, self.index + 1)
            return
        if value == 'None' or value == 'none':
            value = None
        pt = self.parent.get_property_tuple() + (self.index + 1,) #add index to property tuple
        data = self.parent._data_class(value, string_map=self.parent.enum_string_map)
        return write_property_g3(self.parent.object.group.device.instance, pt, data.as_tags())
        # bp = self.parent.bacnet_property
        # value_list = bp.value
        # value_list[self.index] = value
        # bp.value = value_list
        # bp.set(self.parent.object.group.device.instance)
    def is_array_element_of(self):
        return self.parent
    def is_array(self):
        return False
    def get_batch_manager(self):
        if self._batch_manager is None:
            if self.__use_parent_batch_manager:
                return self.parent.get_batch_manager()
            return None
        return self._batch_manager
    def get_obj_instance(self):
        return self.parent.get_obj_instance()
    def set_batch_manager(self, n):
        self.__use_parent_batch_manager = False
        self._batch_manager = n
    def nodecmp(self, y_url): #compare two nodes for sorting
        y = as_node(y_url)
        try:
            return cmp(int(self.name), int(y.name))
        except:
            return cmp(self.name, y.name) #incase someone got cute and renamed the node

#
# This thread occasionally requests a who_is to find new devices.
#
class _WhoIsThread(ImmortalThread):
    def __init__(self, node):
        node_url = as_node_url(node)
        ImmortalThread.__init__(self, name='_WhoIsThread(%r)' % node_url)
        self.node = node
        self.debug = node.debug
        self.discover_interval = node.discover_interval
        if self.debug:
            print '%s.__init__()' % self.getName()
    def reincarnate(self):
        msglog.log('broadway',msglog.types.INFO,
                    '%s restarting' % self.getName())
        time.sleep(10)
        return
    def run(self):
        if self.node.running:
            if self.debug:
                print '%s.run()' % self.getName()
            self.listen()
        else:
            self.should_die()
    def listen(self): #called from immortal thread
        try:
            while self._continue_running:
                if self.debug:
                    print '%s.listen():  Broadcasting WHOIS' % self.getName()
                self.node._device_table_size = 0 #once a minute, force a full discovery
                network._who_are_devices()
                time.sleep(self.discover_interval)
        finally:
            if self.debug:
                print '%s.finally' % self.getName()

class ServerDevice(BINAliasDevice):
    _node_def_id = 'TBD'
    def __init__(self):
        BINAliasDevice.__init__(self)
        self.lib_device = None
        self.discovered = 0
        self.debug = debug
        self._object_list = {}
        self._as_tags_object_list = {}
    def configure(self, config):
        set_attribute(self, 'network', REQUIRED, config, int) #make this a required value for Server devices
        BINAliasDevice.configure(self, config)
        if self.debug: print 'just configured: ', self.as_node_url()
        
    def start(self):
        if self.debug: print 'start: ', self.as_node_url()
        self._object_list[(8, self.instance,)] = BACnetObjectIdentifier(8, self.instance)
        mtu = 1468 #default IP max npdu length
        if self.get_carrier():
            mtu = self._carrier.mtu
            if self._carrier.network == self.network: #since we should be the default device for the interface
                self._carrier.default_device(self) #if an exception is thrown here it is because more than one device is configured to be the default
        BINAliasDevice.start(self)
        try:
            mtu = min(mtu, int(self.get_device_property('62').get())) #Max APDU length
        except:
            msglog.exception()
            msglog.log('BACnet Server', msglog.types.INFO, 'Using default interface NPDU MTU Length for: %s' % (self.as_node_url(),))
            pass
        self.lib_device = create_server_device(self, self.network, mtu)
        # copy values from required properties into lib_device object
        self.lib_device.vendor_id = int(self.get_device_property('120').get()) #Vendor Indentifier
        #Segmentaion Supported
        seg = int(self.get_device_property('107').get()) #0=both, 1=xmit_only, 2=rcv_only, 3=none)
        if (seg & 2) == 2: #receive segmentation not supported
            self.lib_device.can_recv_segments = 0
        if (seg & 1) == 1: #xmit segmentation not supported
            self.lib_device.can_send_segments = 0
        self.lib_device.T_seg = int(self.get_device_property('10').get()) #APDU Segment Timeout
        self.lib_device.T_wait_for_seg = self.lib_device.T_seg * 4
        self.lib_device.T_out = int(self.get_device_property('11').get()) #APDU Timeout
        self.lib_device.N_retry = int(self.get_device_property('73').get()) #Number of APDU Retries
        #Protocol Service supported
        # @TODO allow selection of RPM/WPM support from broadway.xml
    def get_boids(self): #called by auto discovery
        #make sure that the minimum Device Properties are created if missing
        #nodes defined by broadway.xml don't need to be here
        return self._object_list.values()
    def get_cached_boids(self):
        return self._as_tags_object_list.values()
    def add_boid(self, type, instance):
        self._object_list[(type, instance,)] = BACnetObjectIdentifier(type, instance)
        self._as_tags_object_list[(type, instance,)] = BACnetObjectIdentifier(type, instance).encoding[0]
    def remove_boid(self, type, instance):
        try:
            del(self._object_list[(type, instance,)])
            del(self._as_tags_object_list[(type, instance,)])
        except KeyError:
            pass
    def get_device_property(self, name):
        return self.as_node('8/%s/%s' % (self.name, name))
    def child_class(self):
        return ServerObjectTypeGroup
    def find_bacnet_object(self, object_identifier):
        try:
            g = self.get_child(str(object_identifier.object_type))
            o = g.get_child(str(object_identifier.instance_number))
            return o  #answer the node representing the bacnet object
        except:
            if self.debug: print 'request for unknown object: ', \
               object_identifier.object_type, \
               object_identifier.instance_number
        return None

class ServerObjectTypeGroup(BINObjectTypeGroup):
    def _discover_children(self, force=0):
        #create a "device" object if one does not exist, force is ignored
        if self.running == 1 and not self._been_discovered:
            try:
                existing_instances = self._existing_instances()
                for n in self.parent.get_boids():
                    if n.object_type == self.type:
                        if n.instance_number not in existing_instances:
                            self._nascent_children['%d' % (n.instance_number,)]=ServerObjectInstance()
                self._been_discovered = 1
            except:
                msglog.exception()
                if self.debug: print 'error during BINObjectTypeGroup object discover'
        return self._nascent_children
class ServerObjectInstance(ProxyAbstractClass, BINObjectInstance):
    def __init__(self):
        BINObjectInstance.__init__(self)
        ProxyAbstractClass.__init__(self)
        self._last_exception = None #used to control "status" property
        self._status_flags = [0,0,0,0]
        self._reliability = None
        self._event_state = None
        self._priority_array_node = None
        self.set = None #proxy will supply this during start
        self.helper_task = None
        self.time_task = None
    def configure(self, cd):
        BINObjectInstance.configure(self, cd)
        set_attribute(self, 'link', self.link, cd, str) #do this so that proxy configure will know if it is a proxy
        ProxyAbstractClass.configure(self, cd)
        if self.link is None:  #if we are not a proxy node
            self.is_proxy = self._is_proxy #overload the .is_proxy function
        #print 'just configured: ', self.as_node_url()
    def configuration(self):
        cd = BINObjectInstance.configuration(self)
        return ProxyAbstractClass.configuration(self, cd)
    def start(self):
        if self.debug: print 'start: ', self.as_node_url()
        BINObjectInstance.start(self)
        self.group.device.add_boid(self.group.type, self.instance) #add to objectlist
        ProxyAbstractClass.start(self)  #follows start on children to prevent Proxy sets from happening during start
        #test for being schedule object.  If so, periodically send current value to any DeviceObjectPropergyReferences
        if self.parent.name == '17': #ScheduleObject
            self.helper_task = scheduler.after(60, self.trigger_update_device_object_property_refs)
        #test for being time syncronization service
        if self.parent.name == '8': #Time Synchronization Recipients
            self.time_task = scheduler.after(360, self.trigger_update_time_recipients)
    def stop(self):
        try: #stop updating schedule object dopr list
            ht,self.helper_task = self.helper_task,None
            if ht: ht.cancel()
        except:
            msglog.exception()
        try: #stop updating time recipients
            tt,self.time_task = self.time_task,None
            if tt: tt.cancel()
        except:
            msglog.exception()
        BINObjectInstance.stop(self)
        self.group.device.remove_boid(self.group.type, self.instance) #removce from objectlist
        ProxyAbstractClass.stop(self)
    def trigger_update_device_object_property_refs(self):
        thread_pool.NORMAL.queue_noresult(self._update_device_object_property_refs)
    def _update_device_object_property_refs(self):
        if self.helper_task is None: return
        #periodically update any dopr values
        #@TODO  Use COV with a slow background update
        try:
            #get the device/object/property references
            doprl = self.get_child('54').get()  
            #check effective period and make sure we should write to properties
            ep = self.get_child('32').get() #BACnetDateRange object
            if ep: #not None so test for proper date range
                if not ep.includes(BACnetDate(time.time())):
                    doprl = [] #don't update any objects
            cv = self.get() #current schedule value
            for dopr in doprl: #for each device object prop reference
                if self.helper_task is None: return
                try:
                    #property referernce may or many not have index
                    value = dopr.value #(device, type, inst, pid, [index])
                    device,type,obj,prop = value[:4]
                    if debug: print 'update ', device,type,obj,prop
                    index = None
                    if len(value) > 4:
                        index = value[4]
                    if device is None: 
                        #device not spec'd, the reference is to parent device
                        device = self.group.device.instance
                    #form url from paremeters given
                    devices_node = self.group.device.parent
                    n = devices_node.as_node('%d/%d/%d/%d' % \
                            (device, type, obj, prop))
                    if debug: print 'node=', n.as_node_url()
                    if prop == 85 and not hasattr(n,'_not_commandable'):
                        #handle present value
                        #could be either simple write or via priority array
                        try: #to send formal override with priority level
                            #88 is override priority
                            n.override(cv, self.get_child('88').get().value) 
                        except ETimeout: #do this first
                            pass #simple timeout will not affect write method
                        except BACnetException:
                            n.set(cv) #fallback to simple set
                            #remember this to save time
                            n._not_commandable = True
                    else: #any other kind of property
                        if index: #an index of an array
                            n = n.get_child(str(index))
                        n.set(cv)
                except:
                    #don't let failure of one dopr prevent writing to the others
                    msglog.exception() #debug
        except:
            msglog.exception()
        if self.helper_task:
            ht,self.helper_task = self.helper_task,scheduler.after(60, 
                self.trigger_update_device_object_property_refs)
            if ht is None: #just missed the stop() call
                ht,self.helper_task = self.helper_task,None
                if ht: ht.cancel()
    def trigger_update_time_recipients(self):
        thread_pool.NORMAL.queue_noresult(self._update_time_recipients)
    def _update_time_recipients(self):
        if self.time_task is None: return
        #periodically update any time recipients
        try:
            #get the list of time syncronization recipients
            #this line will throw an exception for any object other than
            #a server device instance that has the recipient list defined
            tsr = self.get_child('116', autodiscover=0).get()
            now = time.time() #Epoc UTC
            local = time.localtime(now)
            ld = local[:3] + (local[6]+1,)
            ld = datatype.BACnetDate(ld).as_tags()[0]
            lt = datatype.BACnetTime(local[3:6]).as_tags()[0]
            utc = time.gmtime(now)
            ud = utc[:3] + (utc[6]+1,)
            ud = datatype.BACnetDate(ud).as_tags()[0]
            ut = datatype.BACnetTime(utc[3:6]).as_tags()[0]
            for r in tsr: #if more than zero recipients
                try:
                    x = None
                    x = r.value #an int for BOID or a tuple for address mode
                    choice = r.choice_name
                    if choice == 'device':
                        #determine local or UTC sync mode ../8/#/97 is cached
                        mode = self.parent.parent.parent.as_node(
                            str(x)+'/8/'+str(x)+'/97').get()
                        if mode.get_bit('TimeSynchronization'):
                            send_device_time_syncronization(x, ld, lt)
                        elif mode.get_bit('UtcTimeSynchronization'):
                            send_device_time_syncronization(x, ud, ut, 1)
                        else:
                            raise EInvalidValue('device does not support '+
                                'time sync service: ', x)
                    elif choice == 'address': #x=(network#, [mac bytes])
                        n = x[0]
                        a = network.Addr(array.array('B',x[1]).tostring())
                        send_addr_time_syncronization(n, a, ld, lt)
                        send_addr_time_syncronization(n, a, ud, ut, 1)
                    else:
                        raise EInvalidData()
                except:
                    if x:
                        if hasattr(self,'_bad_time_sync_devices'):
                            if x in self._bad_time_sync_devices:
                                #only report a bad device once
                                continue
                        else:
                            self._bad_time_sync_devices = []
                        self._bad_time_sync_devices.append(x)
                    msglog.exception()
        except ENoSuchName:
            #this is how we filter out devices that do not have 116 defined
            self.time_task = None
            return #and never come back
        except:
            msglog.exception()
        if self.time_task:
            ht,self.time_task = self.time_task,scheduler.after(3601, 
                self.trigger_update_time_recipients)
            if ht is None: #just missed the stop() call
                ht,self.time_task = self.time_task,None
                if ht: ht.cancel()
    def _discover_children(self, force=0):
        self._been_discovered = 1
        self._nascent_children = {}
        return self._nascent_children
    def find_property(self, property_identifier):
        if debug: print 'look for property: ', property_identifier
        return self.get_child(str(property_identifier), auto_discover=0)
    def set_exception(self, exception):
        flag = 0
        if exception: flag = 1
        if self._last_exception != exception:
            self._last_exception = exception
            if flag: print "msglog.log('bacnet server', exception, 'set_exception')", self.name, repr(exception) #msglog.log('bacnet server', exception, 'set_exception')
    def _is_proxy(self):
        return 0
    def child_class(self):
        return ServerPropertyInstance
    def _get_status_flags(self, *args, **keywords):
        #12.1.7 Status_Flags
        #This property, of type BACnetStatusFlags, represents four Boolean flags that indicate the general "health" of an analog input.
        #Three of the flags are associated with the values of other properties of this object. A more detailed status could be determined
        #by reading the properties that are linked to these flags. The relationship between individual flags is not defined by the
        #protocol. The four flags are
        #{IN_ALARM, FAULT, OVERRIDDEN, OUT_OF_SERVICE}
        #where:
        #IN_ALARM Logical FALSE (0) if the Event_State property (see 12.1.8) has a value of NORMAL, otherwise
        #logical TRUE (1).
        #FAULT Logical TRUE (1) if the Reliability property (see 12.1.9) is present and does not have a value of
        #NO_FAULT_DETECTED, otherwise logical FALSE (0).
        #OVERRIDDEN Logical TRUE (1) if the point has been overridden by some mechanism local to the BACnet
        #Device. In this context "overridden" is taken to mean that the Present_Value and Reliability
        #properties are no longer tracking changes to the physical input.
        #OUT_OF_SERVICE Logical TRUE (1) if the Out_Of_Service property (see 12.1.10) has a value of TRUE, otherwise
        #logical FALSE (0).
        if self._last_exception is not None:
            if self.has_child('103', auto_discover=0):
                self._status_flags = [1,1,0,0]
            else:
                self._status_flags = [1,0,0,0]
        else:
            in_alarm = self._get_event_state()
            fault = 0
            if self.has_child('103', auto_discover=0):
                reliability = self.get_child('103').get()
                if reliability is not None:
                    reliability = int(reliability)
                fault = not (0 == reliability)
            out_of_service = 0
            if self.has_child('81', auto_discover=0):
                oos_value = self.get_child('81').get()
                if oos_value is not None:
                    oos_value = int(oos_value)
                out_of_service = 1 == oos_value
            self._status_flags = [in_alarm, fault, 0, out_of_service]
        return tuple(self._status_flags)
    def _get_event_state(self, *args, **keywords):
        #12.1.8 Event_State
        #The Event_State property, of type BACnetEventState, is included in order to provide a way to determine if this object has an
        #active event state associated with it. If the object supports intrinsic reporting, then the Event_State property shall indicate the
        #event state of the object. If the object does not support intrinsic reporting, then the value of this property shall be NORMAL.
        #If the Reliability property is present and does not have a value of NO_FAULT_DETECTED, then the value of the
        #Event_State property shall be FAULT. Changes in the Event_State property to the value FAULT are considered to be "fault"
        #events.
        #answer 1 if there is an active exception
        if self._last_exception is not None:
            return 1
        if self.has_child('103', auto_discover=0):
            reliability = self.get_child('103').get()
            if reliability is not None:
                reliability = int(reliability)
                return not (0 == reliability)        
        return 0
    def _get_reliability(self, *args, **keywords):
        #12.1.9 Reliability
        #The Reliability property, of type BACnetReliability, provides an indication of whether the Present_Value or the operation of
        #the physical input in question is "reliable" as far as the BACnet Device or operator can determine and, if not, why. The
        #Reliability property for this object type may have any of the following values:
        #{NO_FAULT_DETECTED, NO_SENSOR, OVER_RANGE, UNDER_RANGE, OPEN_LOOP,
        #SHORTED_LOOP, UNRELIABLE_OTHER}
        #@todo compare PV to min and max present value
        #answer 1 if there is an active exception
        if self._last_exception is not None:
            return 7  #Unreliable Other
        #the next two clauses apply only to analog I/O/V, not binary's
        if self.has_child('65', auto_discover=0): #max present value
            max = self.get_child('65').get()
            if max is not None:
                if float(self.get_child('85').get()) > float(max):
                    return 2 #over_range
        if self.has_child('69', auto_discover=0): #min present value
            min = self.get_child('69').get()
            if min is not None:
                if float(self.get_child('85').get()) < float(min):
                    return 3 #under_range
        #multi-value objects
        if self.has_child('39', auto_discover=0): #fault values
            faults = self.get_child('39').get()
            if faults is not None:
                if int(self.get_child('85').get()) in [int(i) for i in faults ]:
                    return 9 #multi value fault
        #schedule objects TODO
        return 0      #NO_FAULT_DETECTED
    def _write_commandable(self, tags, index, priority=16): #make sure this is commandable then check the priority array
        if self._priority_array_node is None: #since not commandable, do regular write
            self._present_value_node._write(tags, index)
            if self.is_proxy(): #update the proxied point
                self.set(self._present_value_node.last_result.value)
        else: #handle a commandable PV
            self._priority_array_node._write(tags, priority) #priority is the index for PA
            self._process_present_value()
    def _process_present_value(self):
        values = self._priority_array_node.get()
        if values is None: values = [] #in case no priority array defined
        for v in values: #search the priority array for an overrride
            if v.value is not None: #we have an override in effect
                self._present_value_node.last_result = Result(v, uptime.secs())
                break
        else: #since no overrides, get relinquish default
            self._present_value_node.last_result = self.get_child('104').get_result() #this may be None, which signals proxied node to clear override
        if self.is_proxy(): #update the proxied point
            if self.set is not None: #the proxy stuff has started
                self.set(self._present_value_node.last_result.value)
    def _get_present_value(self, pv, *args, **keywords):
        if self.is_proxy():
            value = self.get() #get from proxied node
            pv._as_result(value) #"set" the value into the present value node
            return pv.last_result
        return pv._get_result(*args, **keywords) #non proxy
    def nb_get(self):
        # These objects are licensed during parsine broadway file and do not
        # need special nb_get handler but they are a subclass of 
        # BINObjectInstance and need to just call normal get
        return self.get()
    
class _ServerPersistentPropertyValue(PersistentDataObject):
    def __init__(self, node):
        self.value = None
        PersistentDataObject.__init__(self, node)
        PersistentDataObject.load(self)

class ServerPropertyInstance(BINPropertyInstance):
    def __init__(self):
        BINPropertyInstance.__init__(self)
        self.get_result = self._get_result
        self.write = None
        self._pdo = None
        self._last_saved_value = None
        self._last_saved_time = uptime.secs()
        self.pdo_save_interval = 300 #5 min
        self._next_save_schedule = None
    def configure(self, config):
        BINPropertyInstance.configure(self, config)
        set_attribute(self, 'value', None, config)
        set_attribute(self, 'pdo_save_interval', self.pdo_save_interval, config, float)
        if self.is_commandable():
            self.object._present_value_node = self
        elif self.is_priority_array():
            self.object._priority_array_node = self
        elif self.is_relinquish_default():
            self.object._relinquish_default = self
        if self.debug: print 'just configured: ', self.as_node_url()
    def configuration(self):
        config = BINPropertyInstance.configuration(self)
        get_attribute(self, 'value', config, str)
        get_attribute(self, 'pdo_save_interval', config, str)
        if self._pdo:
            self.__pdo_filename__ = self._pdo._persistent.filename
            get_attribute(self, '__pdo_filename__', config, str)
        return config
    def start(self):
        if self.debug: print 'start: ', self.as_node_url()
        BINPropertyInstance.start(self)
        #tell the object who we are
        type = self.object.group.type
        if type in soprw.keys():
            if self.id in soprw[type].keys():
                r, w, v = soprw[type][self.id]
                if r is not None:
                    attr = soprw_function_enum[r]
                    if self.hasattr(attr):
                        #print 'server start read overload: %s %s' % (self.as_node_url(), attr)
                        self.get_result = eval('self.' + attr)
                if w is not None:
                    self.set = self._set
                    attr = soprw_function_enum[w]
                    if self.hasattr(attr):
                        #print 'server start write overload: %s %s' % (self.as_node_url(), attr)
                        self.write = eval('self.' + attr)
                if v is not None:
                    if self.value is None:
                        #default initail value if nothing is configured
                        self.value = v 
        #@todo: get pdo value and place in into value
        v = self.get_pdo()
        if v is not None: #use pdo to get initial value in place
            self._last_saved_value = v          
            self.value = v
        if self.value is not None:
            if not (self.object.is_proxy() and \
                (self.is_commandable() or self.is_handled_by_proxy())): 
                #don't set PV's of proxies, 
                #this is the responsiblity of the proxy
                self._set(self.value) #configured value rules unless pdo used
    def is_handled_by_proxy(self):
        #these are like proxy commandable properties, 
        #they should never be set by the pdo.
        return self.name in ('38','123')  #currently only schedule uses this
    def _array_element_class(self):
        return ServerPropertyArrayElement
    def get(self, skipcache=0, **options): #return BACnet Data object
        return self.get_result(skipcache).value
    def _get_result(self, skipcache=0):
        if self.last_result is None:
            answer = None
            if self._is_array or self._is_list:
                answer = str_list([self._data_class(None, 
                          string_map=self.enum_string_map) \
                          for i in range(self._array_limit)])
            self.last_result = Result(answer, uptime.secs())
        return self.last_result
    def _get_status_flags(self, *args, **keywords):
        flags = self.object._get_status_flags()
        return self._as_result(flags)
    def _as_result(self, value):
        if self._is_array or self._is_list:
            answer = []
            for v in value:
                answer.append(self._data_class(v, string_map=self.enum_string_map))
        else:
            answer = self._data_class(value, string_map=self.enum_string_map)
        return self._as_result_data(answer)
    def _as_result_data(self, dobj):
        self.last_result = Result(dobj, uptime.secs())
        return self.last_result
    def _get_event_state(self, *args, **keywords):
        state = self.object._get_event_state()
        return self._as_result(state)
    def _get_reliability(self, *args, **keywords):
        reliability = self.object._get_reliability()
        return self._as_result(reliability)
    def _get_present_value(self, *args, **keywords):
        return self.object._get_present_value(self, *args, **keywords)
    def _get_object_identifier(self, *args, **keywords):
        return self._as_result(self.object.get_obj_identifier())
    def _get_object_list(self, *args, **keywords):
        return self._as_result(self.object.group.device.get_boids())
    def _get_local_date(self, *args, **keywords):
        return self._as_result(time.time())
    def _get_local_time(self, *args, **keywords):
        y, m, d, h, m, s = time.localtime()[:6]
        return self._as_result_data(self._data_class(h, m, s, 0))
    def _get_daylight_savings_status(self, *args, **keywords):
        dst = time.localtime()[8]
        if dst < 0: dst = None #don't know
        return self._as_result(dst)
    def _get_utc_offset(self, *args, **keywords):        
        return self._as_result(int(time.timezone / 60))
    def _get_device_address_bindings(self, *args, **keywords):
        #generate from device table
        answer = []
        for d in network._device_table.values():
            net = d.network
            if net == self.object.group.device.network:
                net = 0
            answer.append(self._data_class(BACnetObjectIdentifier(8, d.instance_number), \
                net, d.mac_address.address))
        return self._as_result_data(answer)
    def _get_exception_schedule(self, *args, **keywords):
        answer = []
        if self.parent.is_proxy(): #only proxy schedules are meaningful
            try:
                sched = as_node(self.parent.link)
                value = sched.get_summary()
                answer = self.parent._convert_schedule_exceptions_2_bacnet(value)
                answer = [x[:-1] for x in answer] #strip exception names
            except:
                msglog.exception()
        return self._as_result(answer)
    def _set_exception_schedule(self, tags, index=None, priority=16, *args, **keywords):
        ## @TODO:  Needs to update DAILY schedule list as well as EXCEPTIONS
        self._write(tags, index, priority)
        exceptions, daily = self.parent._convert_bacnet_2_schedule_exceptions(self.last_result.value)
        sched = as_node(self.parent.link)
        value = sched.get_summary() # [daily, weekly, [exceptions], 'exceptions']
        ## NEED TO MERGE IN DAILY PORTION
        value[2] = [exceptions]
        sched.set_summary(value)
    def _get_weekly_schedule(self, *args, **keywords):
        answer = []
        if self.parent.is_proxy(): #only proxy schedules are meaningful
            try:
                sched = as_node(self.parent.link)
                value = sched.get_summary()
                answer = self.parent._convert_schedule_daily_2_bacnet(value)
            except:
                msglog.exception()
        return self._as_result(answer)
    def _set_weekly_schedule(self, tags, index=None, priority=16, *args, **keywords):
        self._write(tags, index, priority)
        daily = self.parent._convert_bacnet_2_schedule_daily(self.last_result.value)
        sched = as_node(self.parent.link)
        value = sched.get_summary() # [daily, weekly, [exceptions], 'exceptions']
        value[0] = daily
        sched.set_summary(value)
    def _get_array_length(self):
        return self._array_limit
    def _set(self, value):
        if self.debug: print 'server set: ', self.as_node_url(), str(value)
        if self._is_array or self._is_list:
            if type(value) in types.StringTypes:
                #we can be set with either python values or strings
                try:
                    value = eval(value)
                except: #fall back to passing raw strings
                    #allows use of string in context of Enumerated Values
                    value = value[1:-1].split(',')
            if self._is_array:
                if not (len(value) == self._get_array_length()):
                    raise EInvalidValue('BACnet Server', 
                        'attempt to set array of improper length.  '
                        'Should be: %d, was: %d' % \
                        (len(value), self._get_array_length(),), 
                        self.as_node_url())
            result = str_list() #[] #this helps the nodebrowser display better
            for v in value:
                if type(v) in types.StringTypes:
                    if v == 'None':
                        v = None
                result.append(self._data_class(v, 
                              string_map=self.enum_string_map))
            self.last_result = Result(result, uptime.secs())
        else:
            self.last_result = Result(self._data_class(value, string_map=self.enum_string_map), uptime.secs())
        if self.is_priority_array() or self.is_relinquish_default(): #need to do some special handling of the present value
            self.object._process_present_value()
        self._set_pdo(value)
    def _write(self, tags, index=None, priority=16): #called from lib.bacnet._bacnet.server_write_prop....
        #print tags.__class__
        if self.debug: print str(tags)
        value = self.decode(tags)
        if index is not None:
            if self.last_result is None: # never read
                self._get_result() # initialize the last_result list
            self.last_result.value[index - 1] = value[0] #self.decode assumes we are decoding a list of tags, not just one
            value = self.last_result.value
        self.last_result = Result(value, uptime.secs())
        if self.is_relinquish_default(): #need to do some special handling of the present value
            self.object._process_present_value()
        self._set_pdo(self.last_result.value)
    def _write_commandable(self, tags, index=None, priority=16): #for commandable properties
        self.object._write_commandable(tags, index, priority)
    #answer a list of tags for the bacnet data
    def as_tags(self, index=None): #called from lib.bacnet._bacnet.server_read_prop....
        if self.is_object_list():
            # use cache - encoding large object lists at runtime can lead to multi-second
            # delays
            obj_l = self.object.group.device.get_cached_boids()
            if index is None:
                return obj_l
            elif index == 0:
                return [tag.UnsignedInteger(len(obj_l))]
            else:
                return [obj_l[index-1]]
        dobj = self.get()
        if self._is_array or self._is_list:
            return self._array_as_tags(dobj, index)
        elif dobj is None:
            return [tag.Null()]
        else: #since bacnet data object type
            return dobj.as_tags()
    def _array_as_tags(self, dobj, index = None):
        #print index
        t = []
        if index is None:
            for d in dobj:
                t.extend(d.encoding)
            return t
        if index == 0:
            #print self.data
            #print len(self.data)
            #print tag.UnsignedInteger(len(self.data))
            return [tag.UnsignedInteger(len(dobj))]
        return dobj[index-1].as_tags()
    def _set_pdo(self, value):
        if self._pdo is not None:
            try:
                value = str(value) #make sure it's in string format
                PdoLock.acquire()
                try:
                    if value != self._last_saved_value:
                        self._last_saved_value = value
                        if self._next_save_schedule is None:
                            next_save_time = self._last_saved_time + \
                                self.pdo_save_interval
                            delay = next_save_time - uptime.secs()
                            if delay > 0: #need to wait
                                self._next_save_schedule = \
                                    scheduler.after(delay, 
                                        self._schedule_save_pdo)
                            else: #can do it now
                                self._queue_save_pdo()
                finally:
                    PdoLock.release()
            except:
                msglog.exception()
    def _save_pdo(self, value):
        self._pdo.value = value
        self._pdo.save()
        if debug: print 'saved pdo: %s value: %s' % \
            (self.as_node_url(),self._pdo.value,)
    def _queue_save_pdo(self): #only call while protected by PdoLock
        self._next_save_schedule = None
        self._last_saved_time = uptime.secs()
        thread_pool.LOW.queue_noresult(self._save_pdo, self._last_saved_value)
    def _schedule_save_pdo(self):
        PdoLock.acquire()
        try:
            self._queue_save_pdo()
        finally:
            PdoLock.release()
    def get_pdo(self):
        if self.write is not None: #means we allow set so could be persistent
            if self._pdo is None:
                if self.is_commandable() or self.is_handled_by_proxy():
                    #present value or other property that proxy object handles
                    if self.object.is_proxy():
                        #let the proxied node deal with saving it's state
                        return None 
                self._pdo = _ServerPersistentPropertyValue(self)
            if debug: print 'load pdo: %s value: %s' % \
                (self.as_node_url(),self._pdo.value,)
            return self._pdo.value
        return None
    def get_batch_manager(self):
        return None #not allowed for this service properties
class ServerPropertyArrayElement(BINPropertyArrayElement):
    def set(self, value, priority=None, asyncOK=1):
        #@TODO Lock ?
        value_list = self.parent.get() #an array of bacnet data objects
        value_list[self.index] = self.parent._data_class(value, string_map=self.parent.enum_string_map)
        self.parent.last_result = Result(value_list, uptime.secs())
        if self.parent.is_priority_array(): #need to do some special handling of the present value
            self.parent.object._process_present_value()
        self.parent._set_pdo(self.parent.last_result.value)

soprw_function_enum = {
    0 : "_get_result",
    1 : "_write",
    2 : "_write_commandable",
    3 : "_get_status_flags",
    4 : "_get_event_state",
    5 : "_get_out_of_service", #not implemented
    6 : "_get_reliability",
    7 : "_get_present_value",
    8 : "_get_object_identifier",
    9 : "_get_object_list",
    10: "_get_local_date",
    11: "_get_local_time",
    12: "_get_daylight_savings_status",
    13: "_get_utc_offset",
    14: "_get_device_address_bindings",
    15: "_get_exception_schedule",
    16: "_set_exception_schedule",
    17: "_get_weekly_schedule",
    18: "_set_weekly_schedule",
    }

# [object type][property id] (read function, write function,default_value)
#this table parallels the object_property_data table in lib.bacnet.tsstrings
#and controls how the server property performs reads and writes from the network
#any property not in this table shall attempt a normal _get_result/_write
soprw = {
    0 : { #Analog Input
        0  : (0, None, None), #Acked Transistions
        17 : (0, 1, None),    #Notification Class
        22 : (0, 1, None),    #COV Increment
        25 : (0, 1, None),    #Deadband
        28 : (0, 1, None),    #Description
        31 : (0, 1, None),    #Device Type
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        45 : (0, 1, None),    #High Limit
        52 : (0, 1, None),    #Limit Enable
        59 : (0, 1, None),    #Low Limit
        65 : (0, None, None), #Maximum Present Value
        69 : (0, None, None), #Minimum Present Value
        72 : (0, 1, None),    #Notify Type
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 0), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, 1, None),    #Present Value
        103 : (6, None, None),#Reliability
        106 : (0, 1, None),   #Resolution
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        117 : (0, 1, None),   #Units
        118 : (0, 1, None),   #Update Interval
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    1 : { #Analog Output
        0  : (0, None, None), #Acked Transistions
        17 : (0, 1, None),    #Notification Class
        22 : (0, 1, None),    #COV Increment
        25 : (0, 1, None),    #Deadband
        28 : (0, 1, None),    #Description
        31 : (0, 1, None),    #Device Type
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        45 : (0, 1, None),    #High Limit
        52 : (0, 1, None),    #Limit Enable
        59 : (0, 1, None),    #Low Limit
        65 : (0, None, None), #Maximum Present Value
        69 : (0, None, None), #Minimum Present Value
        72 : (0, 1, None),    #Notify Type
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 1), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, 2, None),    #Present Value
        87 : (0, 1, None),    #Priority Array
        103 : (6, None, None),#Reliability
        104 : (0, 1, None),   #Relinquish Default
        106 : (0, None, None),   #Resolution
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        117 : (0, 1, None),   #Units
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    2 : { #Analog Value
        0  : (0, None, None), #Acked Transistions
        17 : (0, 1, None),    #Notification Class
        22 : (0, 1, None),    #COV Increment
        25 : (0, 1, None),    #Deadband
        28 : (0, 1, None),    #Description
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        45 : (0, 1, None),    #High Limit
        52 : (0, 1, None),    #Limit Enable
        59 : (0, 1, None),    #Low Limit
        72 : (0, 1, None),    #Notify Type
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 2), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, 2, None),    #Present Value
        87 : (0, 1, None),    #Priority Array
        103 : (6, None, None),#Reliability
        104 : (0, 1, None),   #Relinquish Default
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        117 : (0, 1, None),   #Units
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    3 : { #Binary Input
        0  : (0, None, None), #Acked Transistions
        4  : (0, 1, None),    #Active Text
        6  : (0, 1, None),    #Alarm Value
        15 : (0, 1, None),    #Change of State Count
        16 : (0, None, None), #Change of State Time
        17 : (0, 1, None),    #Notification Class
        28 : (0, 1, None),    #Description
        31 : (0, 1, None),    #Device Type
        33 : (0, 1, None),    #Elapsed Active Time
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        46 : (0, 1, None),    #Inactive Text
        72 : (0, 1, None),    #Notify Type
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 3), #Object Type
        81 : (5, None, 0), #Out Of Service
        84 : (0, 1, 0),    #Polarity
        85 : (7, 1, 0),    #Present Value
        103 : (6, None, None),#Reliability
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        114 : (0, None, None),#Time Of Active Time Reset
        115 : (0, None, None),#Time Of State Count Reset
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    4 : { #Binary Output
        0  : (0, None, None), #Acked Transistions
        4  : (0, 1, None),    #Active Text
        15 : (0, 1, None),    #Change of State Count
        16 : (0, None, None), #Change of State Time
        17 : (0, 1, None),    #Notification Class
        28 : (0, 1, None),    #Description
        31 : (0, 1, None),    #Device Type
        33 : (0, 1, None),    #Elapsed Active Time
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        40 : (0, 1, None),    #Feedback Value
        46 : (0, 1, None),    #Inactive Text
        66 : (0, 1, None),    #Minimum Off Time
        67 : (0, 1, None),    #Minimum On Time
        72 : (0, 1, None),    #Notify Type
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 4), #Object Type
        81 : (5, None, 0), #Out Of Service
        84 : (0, 1, 0),    #Polarity
        85 : (7, 2, 0),    #Present Value
        87 : (0, 1, None),    #Priority Array
        103 : (6, None, None),#Reliability
        104 : (0, 1, None),   #Relinquish Default
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        114 : (0, None, None),#Time Of Active Time Reset
        115 : (0, None, None),#Time Of State Count Reset
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    5 : { #Binary Value
        0  : (0, None, None), #Acked Transistions
        4  : (0, 1, None),    #Active Text
        6  : (0, 1, None),    #Alarm Value
        15 : (0, 1, None),    #Change of State Count
        16 : (0, None, None), #Change of State Time
        17 : (0, 1, None),    #Notification Class
        28 : (0, 1, None),    #Description
        33 : (0, 1, None),    #Elapsed Active Time
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        46 : (0, 1, None),    #Inactive Text
        66 : (0, 1, None),    #Minimum Off Time
        67 : (0, 1, None),    #Minimum On Time
        72 : (0, 1, None),    #Notify Type
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None,5), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, 2, 0),    #Present Value
        87 : (0, 1, None),    #Priority Array
        103 : (6, None, None),#Reliability
        104 : (0, 1, None),   #Relinquish Default
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        114 : (0, None, None),#Time Of Active Time Reset
        115 : (0, None, None),#Time Of State Count Reset
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    6 : { #Calendar
        23 : (0, 1, None),    #Datelist
        28 : (0, 1, None),    #Description
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 6), #Object Type
        85 : (7, 2, None),    #Present Value
        168: (0, None, None), #Profile Name
        },
    8 : { #Device
        5  : (0, None, None), #Active VT Sessions
        10 : (0, 1, 2000),    #APDU Segment Timeout
        11 : (0, 1, 4000),    #APDU Timeout
        12 : (0, 1, None),    #Application Software Version
        24 : (12, 1, None),    #Daylight Savings Status
        28 : (0, 1, None),    #Description
        30 : (14, None, []), #Device Address Binding
        44 : (0, None, None), #Firmware revision
        55 : (0, None, []), #List of Session Keys
        56 : (10, 1, None),    #Local Date
        57 : (11, 1, None),    #Local Time
        58 : (0, 1, None),    #Location
        62 : (0, 1, 1468),    #Max APDU length
        63 : (0, 1, None),    #Max Info Frames
        64 : (0, 1, None),    #Max Master
        70 : (0, 1, None),    #Model Name
        73 : (0, 1, 3),    #Number of APDU Retries
        75 : (8, None, None), #Object Identifier
        76 : (9, None, None), #Object List
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 8), #Object Type
#        95 : (0, 1, None),
        96 : (0, None, (1,1,1,1,1,1,1,0,\
                        1,0,0,0,0,1,1,0,\
                        0,0,0,1,0,0,0)),    #Protocol Object Types supported
        97 : (0, None, (0,1,0,0,0,0,0,0,\
                        0,0,0,0,1,0,1,1,\
                        1,0,1,0,0,0,0,0,\
                        0,0,1,0,0,0,0,0,\
                        0,0,1,0,0,0,0,0)),    #Protocol Services supported
        # 97 : (0, None, (0,0,0,0,0,0,0,0,\
                        # 0,0,0,0,1,0,0,1,\
                        # 0,0,1,0,0,0,0,0,\
                        # 0,0,1,0,0,0,0,0,\
                        # 0,0,1,0,0,0,0,0)),    #Protocol Services supported  RPM and WPM disabled of ODS jobsite
        98 : (0, None, 1), #Protocol Version
        107: (0, None, 0), #Segmentaion Supported
        116: (0, 1, []), #Time Synchronization Recipients
        112: (0, None, 0), #System status
        119: (13, 1, None),    #UTC Offset
        120: (0, None, 95), #Vendor Indentifier
        121: (0, None, 'Cisco Systems, Inc'), #Vendor Name
        122: (0, None, None), #VT_Classes Supported
        139: (0, None, 1), #Protocol Revision
        152: (0, None, None), #Active COV Subscriptions
        153: (0, 1, None),    #Backup Failure Timeout
        154: (0, None, None), #Configuration Files
        155: (0, None, 1), #Database Revision
        157: (0, None, None), #Last Restore Time
        167: (0, None, None), #Max Segments Accepted
        168: (0, None, None),#Profile Name
        },
    13 : { #Multistate Input
        0  : (0, None, None), #Acked Transistions
        7  : (0, 1, None),    #Alarm Values
        17 : (0, 1, None),    #Notification Class
        28 : (0, 1, None),    #Description
        31 : (0, 1, None),    #Device Type
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        39 : (0, 1, None),    #Fault Values
        72 : (0, 1, None),    #Notify Type
        74 : (0, None, 1), #Number Of States
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 13), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, 1, None),    #Present Value
        103 : (6, None, None),#Reliability
        110 : (0, 1, ['state_text',]),   #State Text
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    14 : { #Multistate Output
        0  : (0, None, None), #Acked Transistions
        17 : (0, 1, None),    #Notification Class
        28 : (0, 1, None),    #Description
        31 : (0, 1, None),    #Device Type
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        40 : (0, 1, None),    #Feedback Value
        72 : (0, 1, None),    #Notify Type
        74 : (0, None, 1), #Number Of States
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 14), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, 2, None),    #Present Value
        87 : (0, 1, None),    #Priority Array
        103 : (6, None, None),#Reliability
        104 : (0, 1, None),   #Relinquish Default
        110 : (0, 1, ['state_text',]),   #State Text
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name
        },
    17 : { #Schedule Object
        28 : (0, 1, None),    #Description
        32 : (0, 1, None), #Effective_Period
        38 : (15, 16, []), #(502, 0, 1, 0, 0, 1), #Exception_Schedule
        54 : (0, 1, []), #(503, 0, 0, 1, 0, 0), #List_Of_Device_Object_Property_References
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 17), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, None, None),    #Present Value
        88 : (0, 1, 11), #Priority_For_Writing, default priority is 11
        103 : (6, None, None),#Reliability
        111 : (3, None, None),   #Status Flags
        123 : (17, 18, []), #(500, 7, 1, 0, 0, 1), #Weekly_Schedule
        168 : (0, None, None),#Profile Name
        174 : (0, 1, None), #Schedule_Default
        },
    19 : { #Multistate Value
        0  : (0, None, None), #Acked Transistions
        7  : (0, 1, None),    #Alarm Values
        17 : (0, 1, None),    #Notification Class
        28 : (0, 1, None),    #Description
        35 : (0, 1, None),    #Event Enable
        36 : (4, None, None), #Event State
        39 : (0, 1, None),    #Fault Values
        72 : (0, 1, None),    #Notify Type
        74 : (0, None, 1), #Number Of States
        75 : (8, None, None), #Object Identifier
        77 : (0, 1, None),    #Object Name
        79 : (0, None, 19), #Object Type
        81 : (5, None, 0), #Out Of Service
        85 : (7, 2, None),    #Present Value
        87 : (0, 1, None),    #Priority Array
        103 : (6, None, None),#Reliability
        104 : (0, 1, None),   #Relinquish Default
        110 : (0, 1, ['state_text',]),   #State Text
        111 : (3, None, None),   #Status Flags
        113 : (0, 1, None),   #Time Delay
        130 : (0, None, None),#Event Time Stamps
        168 : (0, None, None),#Profile Name

        },
}
# @TODO
# change timeouts from second to milliseconds in nodedefs
# port to trunk
# add secondary service devices
# test proxy
# cov?
# add new objects? accumulator, etc?
