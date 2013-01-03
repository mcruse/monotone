"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.lib.configure import parse_xml, Iterator
from mpx.lib.node import as_node_url, as_internal_node
import mpx
from mpx.lib import msglog

faillist = []

def _load(cd, verbosity=0):
    node = mpx.lib.factory(cd['module'])
    if cd.has_key('node_id'):
        # Override the 'default' node id.
        node.__node_id__ = cd['node_id']
    else:
        # If there is no __node_id__, add the factory.
        # This doesn't make sense here, in 1.4 all this
        # moves into mpx.lib.factory().
        node.__factory__ = cd['module']
    return node

def load_xml(parent, path):
    legal_controlling_authority = parent.as_node_url()
    msglog.log(legal_controlling_authority,msglog.types.INFO,
               'Stage 1:  Parsing configuration file: %s' % (path,))
    root = parse_xml(path) #this would be a replacement rznet_peer node but we will throw it away
    return load_root(root, parent)

def load_root(root, parent): #parent is the control service node or a com port
    legal_controlling_authority = parent.as_node_url()
    print 'load_root: legal_controlling_authority = ',legal_controlling_authority
    cd = root.get_config()
    name = cd['name'] #application name
    print 'load_root: name = ',name
    cd['parent'] = legal_controlling_authority
    msglog.log(legal_controlling_authority,msglog.types.INFO,
           'Stage 2.0:  Prune existing RZ protocol nodes.')
    node = None
    if parent.has_child(name): #prune the existing drawings and templates
        node = parent.get_child(name) #pre-existing application node
        print 'load_root: ',legal_controlling_authority, ' has child: ', name, ' grand children: ', node.children_names()
        for c in node.children_nodes(): #drawings, etc
            print 'load root: prune(1): ', c.as_node_url()
            c.prune(1) #prune all the children of the old rznp or rzhp node
        #only if the rzhost slave port or mediator lan_address has changed do we want to restart the app node
        try:
            if (node.rzhost_slave_port != int(cd.get('rzhost_slave_port',0))) or \
               (node.rznet_addr != int(cd.get('rznet_addr',0))):
                print 'load_root: something changed: ',node.rzhost_slave_port, int(cd.get('rzhost_slave_port',0)), node.rznet_addr, int(cd.get('rznet_addr',0))
                node.prune()
                node = None #since things have changed, create a new node.  This will cause any phwin connection to break
            else:
                msglog.log(legal_controlling_authority,msglog.types.INFO,
                           'Stage 2.1:  Reuse the existing RZ application node.')

        except:
            msglog.exception()
            node = None
    if node is None:
        msglog.log(legal_controlling_authority,msglog.types.INFO,
                   'Stage 2.1:  Configuring new RZ application node.')
        node = _load(cd)
        node.configure(cd)

    #since we are skipping the root(rznet_peer) and just want the children....
    parent_url = parent.as_node_url() + '/'
    anchors = []
    # Sort the namespace anchors according to their priority.
    for a in root.children:
        anchors.append(a)

    msglog.log(legal_controlling_authority,msglog.types.INFO,
               'Stage 3:  Configuring Application children.')
    n = 0
    for a in anchors:
        n += 1
        ai = Iterator(a)
        # The while, try, while construct minimizes constructing try/except
        # blocks which is an expensive operation.
        while ai is not None and ai.has_more():
            config = a
            state = 'none'
            try:
                while ai.has_more():
                    previous_config = config
                    state = 'lookup'
                    config = ai.get_next_node()
                    state = 'decode'
                    cd = config.get_config()
                    cd['parent']=parent_url + cd['parent']
                    state = 'load'
                    node = _load(cd)
                    state = 'configure'
                    node.configure(cd)
                    state = 'next'
            except:
                # @fixme Add children, partial configure (name and parent).
                msg = ''
                if state == 'lookup':
                    msg = '%s%r%s' % (
                        'Internal failure fetching the node after ',
                        previous_config.get_url(),
                        ' in the configuration.  Aborting configuration.')
                    # We're toast, give up.
                    ai = None
                elif state == 'decode':
                    msg = (
                        'Internal failure decoding %r\'s configuration data.' %
                        config.get_url()
                        )
                elif state == 'load':
                    msg = 'Failed to create node described by %r' % cd
                    faillist.append({'name':cd['name'],'parent':cd['parent'],
                                     'type':'load'})
                elif state == 'configure':
                    msg = 'Failed to configure node %r with %r' % (
                        (config.get_url(), cd))
                    faillist.append({'name':cd['name'],'parent':cd['parent'],
                                     'type':'config'})
                else:
                    msg = 'Internal failure in %r state' % state
                msglog.log(legal_controlling_authority, msglog.types.ERR, msg)
                msglog.exception(msglog.types.ERR)
                if ai is not None:
                    ai.remove_children()
                    msglog.log('control service', msglog.types.WARN,
                               'Unable to create/configure node %s, %s' %
                               (config.get_url(), 'skipping children'))

    msglog.log(legal_controlling_authority,msglog.types.INFO,
               'Stage 4:  Configuration complete.')

