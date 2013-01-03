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
from mpx.service.control.graphical import ApplicationNode
from mpx.lib.node import as_node_url, as_internal_node
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

def load_root(root, parent):
    legal_controlling_authority = parent.as_node_url()
    cd = root.get_config()
    name = cd['name']
    msglog.log(legal_controlling_authority,msglog.types.INFO,
           'Stage 2.0:  Prune existing Application nodes.')
    if parent.has_child(name): #prune the existing child
        parent.get_child(name).prune()
    
    msglog.log(legal_controlling_authority,msglog.types.INFO,
               'Stage 2.1:  Configuring the Application node.')
    cd['parent'] = legal_controlling_authority
    node = _load(cd)
    node.configure(cd)

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
                    cd['parent']=parent.as_node_url() + '/' + cd['parent']
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

