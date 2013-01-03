"""
Copyright (C) 2003 2004 2006 2007 2008 2009 2010 2011 Cisco Systems

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
"""module rznet_node.py: Defines class RznetNode. A given Port node may have up to
one instance of RznetNode as a child. RznetNode encapsulates RS485 port driver 
config, and MFW access to value and config data for rznet points.
"""
import string, types
from mpx import _properties
from mpx.lib import msglog, thread
from mpx.lib.node import CompositeNode, ConfigurableNode, as_internal_node, as_node
from mpx.lib.configure import set_attribute, get_attribute, as_boolean, as_onoff, REQUIRED
from mpx.lib.exceptions import EAlreadyRunning, ETimeout, EInvalidValue, ENoSuchName, ENameInUse, ENotFound
from mpx.lib.rz.rznet_line_handler import RznetThread
from mpx.ion.rz.points import PointNode, PointGroupNode

from mpx.ion.rz.InterfaceRouteNode import ComIfRouteNode

from mpx.ion.rz.load_xml import load_xml


class RznetNode(CompositeNode):
    """class RznetNode: Encapsulates node operations for 
    an rznet-protocol serial port interface. Instanciated as ONLY child 
    of a Port node. (@fixme: Enforce the ONLY part...)
    """
    version = '0.0'
    
    def __init__(self):
        CompositeNode.__init__(self)
        self.running = 0
        self.line_handler = None
        self._pnts_map = {}
        self.debug_lvl = 0 # should be valid immediately after ctor, NOT just after configure()
        self.__status = None
    def configure(self, config):
        self.debug_print(1, 'RznetNode: configure()')
        CompositeNode.configure(self, config)
        #set_attribute(self, 'discover', 0, config, as_boolean)
        config_dir = _properties.properties.CONFIGURATION_DIR
        self.x_points_file_path = config_dir + '/xpoints_' + self.parent.name + '.net' # HARDCODED - rmv from nodedefs!
        self.debug_print(1, self.x_points_file_path)
        self.xml_file_path = config_dir + '/rznp_' + self.parent.name + '.xml' # HARDCODED - rmv from nodedefs!
        set_attribute(self, 'rzhost_slave_port', 6005, config, int) # potl conn to PhWin, via skt; points file datum overrides
        set_attribute(self, 'rzhost_master_path', '', config)  # potl RZHostMaster conn to Ext Modem Server, via COMx
        set_attribute(self, 'QA', 0, config, as_boolean)  # 1: disables Int Modem Server, enables pass-through
        set_attribute(self, 'rznet_addr', 100000, config, int)  # rznet addr; '0' = let ldisc determine it
        set_attribute(self, 'def_max_dev_subscrs', 256, config, int)  # max subscrs allowed per device
        set_attribute(self, '__node_id__', '120077', config)  # allows dyn node creation; not presently used for RznetNode
        set_attribute(self, 'debug_lvl', 0, config, int)
        self.com_port_path = self.parent.as_node_url()
        return
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug_lvl', config, int)
        #get_attribute(self, 'discover', config, as_onoff)
        get_attribute(self, 'x_points_file_path', config)
        get_attribute(self, 'rzhost_slave_port', config, int)
        get_attribute(self, 'rzhost_master_path', config)
        get_attribute(self, 'QA', config, as_boolean)
        get_attribute(self, 'rznet_addr', config, int)  # rznet addr; '0' = let ldisc determine it
        get_attribute(self, 'def_max_dev_subscrs', config, int)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'com_port_path', config)
        try:
            self._token_list_ = self.get_token_list()
            get_attribute(self, '_token_list_', config)
        except:
            pass
        return config

    def start(self):
        self.debug_print(1, 'start()')
        if not self.running:
            self.running = 1
            self.__status = -1
            # If Config has disabled Internal Modem Server, try to get a ref to the 
            # ComIfRouteNode at the given rzhost_master_path (in nodetree):
            port_node = None
            self.debug_print(1, 'rzhost_master_path = %s',
                             self.rzhost_master_path)
            if self.QA != 0:
                try: 
                    com_if_node = as_internal_node(self.rzhost_master_path)
                except ENoSuchName, segment:
                    msglog.log('RznetNode',
                               msglog.types.ERR,
                               ('Failed to find'
                               ' InterfaceRouterNode object'
                               ' at %s, at segment %s!'
                               ' Pass-through will not run.')
                               % (self.rzhost_master_path,
                                   segment)
                               )
                else:
                    port_node = com_if_node.parent
            self.debug_print(1, 'port_node = %s', str(port_node))
            # Create/init thread that runs the whole shootin' match. Pass in
            # desired rznet_addr:
            self.line_handler = RznetThread(self.parent,
                                            self.rzhost_slave_port, port_node,
                                            self.QA, self.rznet_addr,
                                            self)
            # applies to ALL devices
            self.line_handler.def_max_dev_subscrs = self.def_max_dev_subscrs
            # Discover kids in start() rather than in configure, because
            # creating nodes in configure could conceivably confuse the
            # framework (ie should it attempt to config the new nodes?).
            # discover_children() explicitly configs each child node.
            if self.parent.as_node_url() != '/services/control': #under com
                self.discover_children() #need to kick start old style nodes
            #next, start the line handler thread
            self.line_handler.start(); # opens RS485 file object, and slave and
                                       # cmd sockets
            # @fixme HACK to wait for the line_handler thread to init.
            self.line_handler._internal_lock.acquire()
            self.line_handler._internal_lock.release()
            # @fixme END HACK to wait for the line_handler thread to init.
            
            self.rznet_addr = self.line_handler.get_addrs()[0] # get actual addr from ldisc:
            self.debug_print(1, 'ldisc has addr %d.', self.rznet_addr)
            CompositeNode.start(self)
            self.line_handler.broadcast_update_request() #send this out AFTER all bound_proxies are started
            self.__status = 1
        else:          
            raise EAlreadyRunning
        return
    def stop(self):
        self.debug_print(1, 'stop()')
        self.line_handler.stop(); # closes RS485 file object
        self.running = 0
        return
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
    def _open_points_file(self):
        #  Find xpoints.net file on Mediator (at path loaded during configure()).
        pnts_file = None
        try:
            pnts_file = file(self.x_points_file_path, 'r', 1) # use line buffering
        except IOError, instance:
            msglog.log('RznetNode', msglog.types.ERR,
                       'IOError: %d. %s. Failed to open file %s.' %
                       (instance.errno, instance.strerror,
                        self.x_points_file_path))
            msglog.exception()
        return pnts_file
    
    def _read_slave_port_num(self):
        self.debug_print(1, '_read_slave_port_num()')
        pnts_file = self._open_points_file()
        if pnts_file == None:
            return None
        
        tcp_port = None
        found_tcpport_sect = 0
        pnts_file.seek(0) # rtn file pos to start for new search
        for line in pnts_file: 
            if found_tcpport_sect:
                if string.find(line, '[') >= 0:
                    break # we encountered another section, so we're done
                line_tmp = string.strip(line)
                if len(line_tmp) < 4: # port num should be at least 4 characters long
                    continue # we encountered a "blank" line, so continue with next line
                tcp_port = int(line) # integer value of first non-trivial line after section start
                break
            elif string.find(line, '[tcpport]') >= 0:
                found_tcpport_sect = 1
        self.debug_print(1, 'Read tcp_port from file: %s', str(tcp_port))
        return tcp_port

    ##
    # nodes in rz parlance are devices on the RZNetPeer LAN
    #
    def _parse_nodes(self, pnts_file, nodes_map):
        found_nodes_sect = 0
        longest_key_len = 0
        pnts_file.seek(0) # rtn file pos to start for new search
        for line in pnts_file: 
            if found_nodes_sect:
                if string.find(line, '[') >= 0:
                    break # we encountered another section, so we're done
                line_tmp = string.strip(line)
                if len(line_tmp) < 5:
                    continue # we encountered a "blank" line, so continue with next line
                token_list0 = string.split(line_tmp, '=') # split "name=point" pair
                if len(token_list0) != 2:
                    self.debug_print(
                        0, 'Should be one \'=\' in node line %s in file %s.',
                        line, self.x_points_file_path)
                    continue
                key_str = string.strip(token_list0[0])
                node_str = string.strip(token_list0[1])
                try:
                    nodes_map[key_str] = int(node_str, 16) # add node and address to map
                except:
                    self.debug_print(
                        0, 'Bad node address %s in line %s in file %s',
                        node_str, line, self.x_points_file_path
                        )
                    continue
            elif string.find(line, '[nodes]') >= 0:
                found_nodes_sect = 1
                    
        if found_nodes_sect == 0:
            pnts_file.close()
            self.debug_print(
                0, 'Improperly formatted points file: %s\nNo [nodes] section '
                'found.', self.x_points_file_path
                )
            return -1
        
        self.debug_print(1, 'Loaded %d nodes from file: %s.',
                         len(nodes_map), self.x_points_file_path)
        return 0

    ##
    # a point in RZ parlance is similar to a Node
    
    def _parse_points(self, pnts_file, nodes_map):
        found_pnts_sect = 0
        longest_key_len = 0
        pnts_file.seek(0) # rtn file pos to start for new search
        for line in pnts_file: 
            if string.find(line, '[points]') >= 0:
                found_pnts_sect = 1
            elif found_pnts_sect:
                if string.find(line, '[') >= 0:
                    break # we encountered another section, so we're done
                line_tmp = string.strip(line)
                if len(line_tmp) < 5:
                    continue # we encountered a blank line, so continue with next line
                if line[0:3] == 'Rz.':
                    line_tmp = line[3:] # strip redundant leading "Rz" from point name 
                token_list0 = string.split(line_tmp, '=') # split "name=point" pair
                if len(token_list0) != 2:
                    self.debug_print(
                        0, 'Should be one \'=\' in point line %s in file %s.',
                        line, self.x_points_file_path
                        )
                    continue
                token_list1 = string.split(token_list0[1], ',') # split point "controller,obj_id" pair
                #if len(token_list1) != 2:
                    #self.debug_print('Should be one \',\' in point line %s in file %s.' % \
                                     #(line, self.x_points_file_path), 0)
                    #continue
                node_addr = None
                try:
                    node_addr = nodes_map[string.strip(token_list1[0])]
                except:
                    self.debug_print(0, 'Node \'%s\' not found!',
                                     string.strip(token_list1[0]))
                    continue # node not found, so go to next point line
                obj_id_str = string.strip(token_list1[1])
                obj_id = None
                try:
                    obj_id = int(obj_id_str, 16)
                except:
                    self.debug_print(0, 'Bad obj ID %s in line %s in file %s',
                                     obj_id_str, line, self.x_points_file_path)
                proxy_lan_address = 0
                proxy_obj_ref = 0
                if len(token_list1) == 5: #extended proxy info
                    try:
                        proxy_lan_address_str = string.strip(token_list1[3])
                        proxy_obj_ref_str = string.strip(token_list1[4])
                        proxy_lan_address = int(proxy_lan_address_str)
                        proxy_obj_ref = int(proxy_obj_ref_str)
                    except:
                        self.debug_print(
                            0, 'Bad proxy lan address: %s or ID: %s',
                            proxy_lan_address_str, proxy_obj_ref_str
                            )
                pnt_key_str = string.strip(token_list0[0])
                self._pnts_map[pnt_key_str] = (node_addr, obj_id, proxy_lan_address, proxy_obj_ref) # add point name, node addr, and obj_id to map
                if len(pnt_key_str) > longest_key_len:
                    longest_key_len = len(pnt_key_str)
        pnts_file.close()
        if found_pnts_sect == 0:
            self.debug_print(0, 'Improperly formatted points file: '
                             '%s\nNo [points] section found.',
                             self.x_points_file_path)
            return -1
        self.debug_print(1, 'Loaded %d points from file: %s.',
                         len(self._pnts_map), self.x_points_file_path)
        return 0
    
    def discover_children(self):
        #read xml file and set up all the children
        try:
            load_xml(self, self.xml_file_path)
        except:
            if self.debug: msglog.exception()
            msglog.log('RznetNode', msglog.types.WARN,
                       'IOError: Failed to load xml file: %s.  Will attempt to load xpoints.net file: %s' %
                       (self.xml_file_path,self.x_points_file_path))
            self.discover_children_xpoints()
    def discover_children_xpoints(self):
        slave_port_num = self._read_slave_port_num()
        if slave_port_num != None:
            self.rzhost_slave_port = slave_port_num

        self.debug_print(1, 'discover_children()')
        #  If interrogated snippet was saved in configTool - get rid of it.
        for kid in self.children_nodes(): 
            kid.prune() 
        #  Find xpoints.net file on Mediator (at path loaded during configure()).
        pnts_file = self._open_points_file()
        if pnts_file == None:
            return
        
        # Parse file section [nodes] into entries in a map:
        nodes_map = {}
        if self._parse_nodes(pnts_file, nodes_map) < 0:
            return
        
        # Parse section [points] into entries in self._pnts_map:
        if self._parse_points(pnts_file, nodes_map) < 0:
            return
        
        # Create RZNet node subtree from map of points:
        for k in self._pnts_map.keys():
            names = string.split(k,'.') # tokenize the point path at the periods
            node = self # this RznetNode is the top-level "point" node
            pg_names = names[:-1] # each pt_name (except last) in the key should be an PointGroupNode
            for pg_name in pg_names: # at exit: have full PointGroup tree, plus ref to lowest node in tree
                if not node.has_child(pg_name):
                    childDict = {}
                    childDict['name'] = pg_name
                    childDict['parent'] = node
                    childNode = PointGroupNode()                
                    childNode.configure(childDict)
                    node._add_child(childNode)
                node = node.get_child(pg_name)
                
            # Tree MAY have a node with name pt_name, but _add_child() deals with
            # preexisting child nodes anyway...
            pt_name = names[-1]
            childDict = {}
            childDict['name'] = pt_name
            childDict['parent'] = node
            childDict['lan_address'] = self._pnts_map[k][0]
            childDict['id_number'] = self._pnts_map[k][1]
            #proxy config
            mpx_get_index = string.find(k, 'MPX_GET')
            if mpx_get_index > 0:
                childDict['proxy_direction'] = 0
                link = k[mpx_get_index + 7:]
                childDict['link'] = link.replace('.','/')
                childDict['proxy_lan_addr'] = self._pnts_map[k][2]
                childDict['proxy_obj_ref'] = self._pnts_map[k][3]
            mpx_set_index = string.find(k, 'MPX_SET')
            if mpx_set_index > 0:
                childDict['proxy_direction'] = 1
                link = k[mpx_set_index + 7:]
                childDict['link'] = link.replace('.','/')
                childDict['proxy_lan_addr'] = self._pnts_map[k][2]
                childDict['proxy_obj_ref'] = self._pnts_map[k][3]
            #
            childNode = PointNode(self.line_handler)
            try:
                childNode.configure(childDict)
                node._add_child(childNode)
                self.debug_print(1, 'Added/configured %s', k)
            except ENameInUse, e:
                self.debug_print(0, 'Name In Use: %s', e)
                # Child node already exists, so just config it:
                exist_node = node._children[childNode.name]
                exist_node._line_handler = self.line_handler
                exist_node.configure(childDict)
                self.debug_print(1, 'Configured %s', k)
            except:
                msglog.log('RznetNode', msglog.types.ERR,
                            ('Failed to configure Node %s' % k))
        # Dealloc _pnts_map memory, since we no longer need it:
        self._pnts_map.clear()
        
        
    def save_file(self, file_str, file_type = None):
        """save_file(): Called by ConfigTool (or its proxy on the Mediator) to
        save a file from the ConfigTool's machine to the Mediator. In the case
        of RznetNode, the only file_type understood is 'None', which defaults
        to 'xpoints.net'. SO, this method MUST be called PRIOR to a call to
        discover_children(). Note that the created file includes a suffix that
        renders it's name unique across all RS485 ports."""
        if (file_type != None) and (file_type != 'xpoints.net'):
            return
        
        # Validate incoming string/file:
        if (string.find(file_str, '[points]') < 0):
            raise ENotFound('No [points] section in xpoints.net file!')
        elif (string.find(file_str, '[nodes]') < 0):
            raise ENotFound('No [nodes] section in xpoints.net file!')
        
        # Open/create local xpoints_XXXX.net file for read/write, write string, and close file:
        xpn_file = open(self.x_points_file_path, 'w+')
        xpn_file.write(file_str)
        xpn_file.close()
        

    # Rtns 'passive' if Mediator is just listening, 'active' if Mediator has joined
    # token passing:
    def get(self, skipCache=0):
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

"""
if __name__ == '__main__':
    print 'Starting rznet_node.py unit test...'
    
    from mpx.ion.host.port import Port

    rootNode = as_internal_node('/')
    dict0 = {'name':'com1', 'parent':rootNode, 'dev':'/dev/ttyS0'}
    comNode = Port()
    comNode.configure(dict0)
    
    rznode = RznetNode()
    rznode_dict = {'name':'rznet_peer',
                   'parent':comNode,
                   'protocol_type':'rznet_peer',
                   'x_points_file_path':'',
                   'rzhost_master_path':'/interfaces/com1/rzhost_master'}
    rznode.configure(rznode_dict)
    
    xpn_src_file = open('/home/spenner/xpoints.net', 'r+')
    #xpn_src_file = open('/home/spenner/minicom.cap', 'r+')
    src_str = xpn_src_file.read()
    #print src_str
    rznode.save_file(src_str)
    xpn_src_file.close()
    
    rznode.discover_children()
    
    n = rznode._read_slave_port_num()
    
    print 'rznet_node.py unit test completed.'
"""

    
