"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
"""module rzhost_node.py: Defines class RzhostNode. A given Port node may have up to
one instance of RzhostNode as a child. RznetNode encapsulates 
MFW access to value and config data for rznet points.
"""
import string, types
from mpx import _properties
from mpx.lib import msglog, thread
from mpx.lib.node import CompositeNode, ConfigurableNode, as_internal_node, as_node
from mpx.lib.configure import set_attribute, get_attribute, as_boolean, as_onoff, REQUIRED
from mpx.lib.exceptions import *

from mpx.lib.rz.rzhost_line_handler import RzhostThread
from mpx.lib.rz.rznet_line_handler import RznetThread
from mpx.ion.rz.points import PointNode, PointGroupNode
from mpx.ion.rz.InterfaceRouteNode import ComIfRouteNode
from mpx.ion.rz.load_xml import load_xml

#debug bit map
#1 = initialization, one time stuff
#2= packets from phwin
#4 = packets to phwin
#8 = add subscribed point AML
#16 = remove subscribed point CML
#32 = incoming  value point
#64 = outgoing bound point values
#128 = all sent bytes
#256 = all received bytes
#512 = state transistions
#1024 = events on incoming phwin
#2048 = events on incomming rzhost
#4096 = packets from rzhost modem server
#8192 = packets to rzhost modem server
#16384 = byte by byte parsing and state info of incoming packets
#32768 = unrecognized packet
#65535-512
Debug = 0

class RzhostNode(CompositeNode):
    """class RzhostNode: Encapsulates node operations for 
    an rzhost-protocol serial port interface. Instanciated as ONLY child 
    of a Port node. (@fixme: Enforce the ONLY part...)
    """
    version = '0.0'
    
    def __init__(self):
        CompositeNode.__init__(self)
        self.running = 0
        self.discover = 0
        self.line_handler = None
        self._pnts_map = {}
        self.debug_lvl = 0 #16383 # should be valid immediately after ctor, NOT just after configure()
        self.__status = None
        self.connection_type = 'rs-485'
    def configure(self, config):
        self.debug_print(1, 'RzNode: configure()')
        CompositeNode.configure(self, config)
        #set_attribute(self, 'discover', 0, config, as_boolean)
        config_dir = _properties.properties.CONFIGURATION_DIR
        self.xml_file_path = config_dir + '/services/control/' + self.name + '.xml' # HARDCODED - rmv from nodedefs!
        set_attribute(self, 'rzhost_slave_port', 6005, config, int) # potl conn to PhWin, via skt; points file datum overrides
        #set_attribute(self, 'rzhost_master_path', '', config)  # potl RZHostMaster conn to Ext Modem Server, via COMx
        set_attribute(self, 'rznet_addr', 100000, config, int)  # rznet addr; '0' = let ldisc determine it
        set_attribute(self, 'def_max_dev_subscrs', 256, config, int)  # max subscrs allowed TOTAL
        #todo  set_attribute(self, '__node_id__', '120077', config)  # allows dyn node creation; not presently used for RznetNode
        set_attribute(self, 'debug_lvl', Debug, config, int)
        set_attribute(self, 'com_port_path', REQUIRED, config, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug_lvl', config, int)
        #get_attribute(self, 'discover', config, as_onoff)
        get_attribute(self, 'rzhost_slave_port', config, int)
        get_attribute(self, 'rznet_addr', config, int)  # rznet addr; '0' = let ldisc determine it
        get_attribute(self, 'def_max_dev_subscrs', config, int)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'xml_file_path', config)
        get_attribute(self, 'com_port_path', config)
        get_attribute(self, 'connection_type', config)
        return config

    def start(self):
        self.debug_print(1, 'start()')
        if not self.running:
            self.running = 1
            self.__status = -1
            # Discover kids in start() rather than in configure, because
            # creating nodes in configure could conceivably confuse the
            # framework (ie should it attempt to config the new nodes?).
            # discover_children() explicitly configs each child node.
            #if self.discover:
                #self.discover_children()
            # Create/init thread that runs the whole shootin' match. Pass in
            # desired rznet_addr:
            if self.com_port_path in ('/interfaces/com3',
                                      '/interfaces/com4',
                                      '/interfaces/com5',
                                      '/interfaces/com6',):
                self.line_handler = RznetThread(as_node(self.com_port_path),
                                                self.rzhost_slave_port, None,
                                                0, self.rznet_addr,
                                                self)
                self.connection_type = 'rs-485'
            else: #since it must be a rs-232 protocol, either local com port or virtual via tunnel....
                self.line_handler = RzhostThread(as_node(self.com_port_path),
                                                self.rzhost_slave_port,
                                                self.rznet_addr,
                                                self)
                self.connection_type = 'rs-232'
            # applies to ALL devices
            self.line_handler.def_max_dev_subscrs = self.def_max_dev_subscrs
            #next, start the line handler thread
            self.line_handler.start();  # opens RS485 file object, and slave and
                                        # cmd sockets
            # @fixme HACK to wait for the line_handler thread to init.
            self.line_handler._internal_lock.acquire()
            self.line_handler._internal_lock.release()
            # @fixme END HACK to wait for the line_handler thread to init.
            
            self.rznet_addr = self.line_handler.get_addrs()[0] # get actual addr from ldisc:
            self.debug_print(1, 'ldisc has addr %d.', self.rznet_addr)
            CompositeNode.start(self)
            self.line_handler.broadcast_update_request() #send this out AFTER all bound_proxies are started
        else:          
            msglog.log('RznetNode', msglog.types.INFO,
                    'Allready started.  Attempt to start any children')
            CompositeNode.start(self)
        return
    def stop(self):
        self.debug_print(1, 'stop()')
        if self.line_handler:
            self.line_handler.stop(); # closes RS485 file object
        self.running = 0
        return
    def prune(self): #tell line handler to really go away
        if self.line_handler:
            self.line_handler.prune()
        CompositeNode.prune(self)
    def get_line_handler(self):
        return self.line_handler

    def clear_subscr(self, targets=None):
        if self.line_handler is None:
            return
        if (type(targets) == types.ListType):
            targets0_type = type(targets[0])
            if (targets0_type == types.TupleType):
                pass
            elif (targets0_type == types.StringType):
                new_targets = []
                for node_URL in targets:
                    node = None
                    try:
                        node = as_node(node_URL)
                    except ENoSuchName:
                        msglog.exception()
                        continue
                    new_targets.append((node.lan_address,node.id_number,))
                if len(new_targets) == 0:
                    return
                targets = new_targets
            else:
                raise EInvalidValue('targets',targets,'Should be None, int, ' \
                                    'or list of 2-tuples (dev_id, obj_id) or ' \
                                    'a list of node URL strings.')
        self.line_handler.clear_subscr(targets)
        return
    def discover_children(self):
        #read xml file and set up all the children
        try:
            load_xml(self, self.xml_file_path)
        except:
            if self.debug: msglog.exception()
            msglog.log('RzhostNode', msglog.types.WARN,
                       'IOError: Failed to load xml file: %s.' %
                       (self.xml_file_path,))
    # Rtns 'passive' if Mediator is just listening, 'active' if Mediator has joined
    # token passing:
    def get(self, skipCache=0):
        if self.connection_type == 'rs-485':
            if self.__status:
                status_str = 'passive'
                addrs = self.line_handler.get_addrs()
                if addrs[0] != addrs[1]: # if our and next addrs differ, then we're passing token
                    status_str = 'active'
                return status_str
            if self.__status is None:
                return 'not started'
            if self.__status == -1:
                return 'error during startup'
            return 'license not found'
        if self.__status: #started
            try:
                if as_node(self.com_port_path).is_connected():
                    return 'connected'
                else:
                    return 'not connected'
            except:
                pass
            return 'started'            
        if self.__status is None:
            return 'not started'
        if self.__status == -1:
            return 'error during startup'
        return 'license not found'
        
        
    ##
    # returns current nodes on rzlan. to be called via
    # /interfaces/com#/rznet_peer?action=invoke&method=get_token_list
    def get_token_list(self):
        self.line_handler._internal_lock.acquire()
        try:
            self.line_handler._get_node_list()
            return self.line_handler._nodes_list
        finally:
            self.line_handler._internal_lock.release()

    def debug_print(self, msg_lvl, msg, *args):
        if msg_lvl <= self.debug_lvl:
            if args:
                msg = msg % args
            prn_msg = 'RznetThread: ' + msg
            print prn_msg
        return
    def find_template_named(self, name):
        try:
            node = self.as_node(name) #this will find nodes in the app or sister apps but not rznp apps
            return node
        except:
            return None

    
    
