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
from mpx.lib.node import as_node, as_node_url
from mpx.lib.neode import tools, node

root = as_node('/')
ias = as_node('/services/Interactive Service')
ns = node.NodeSpace()
ns.integrate_nodespace(root)
assert ns.as_node('/services/Interactive Service') is ias, 'Failed to lookup service'

ias.prune()
try: node = ns.as_node('/services/Interactive Service')
except: pass
else:
    raise Exception('NodeSpace should not have entry for "/services/Interactive Service"')

assert ias.url != '/services/Interactive Service', 'Failed to reset URLs'

config = ias.configuration()
config['parent'] = '/services'
ias.configure(config)
assert ns.as_node('/services/Interactive Service') is ias, 'Failed to lookup service'
assert ias.url == '/services/Interactive Service', 'Failed to set URLs'

ias.prune()
try: node = ns.as_node('/services/Interactive Service')
except: pass
else:
    raise Exception('NodeSpace should not have entry for "/services/Interactive Service"')

assert ias.url != '/services/Interactive Service', 'Failed to reset URLs'

config = ias.configuration()
config['parent'] = '/services'
ias.configure(config)
assert ns.as_node('/services/Interactive Service') is ias, 'Failed to lookup service'
assert ias.url == '/services/Interactive Service', 'Failed to set URLs'

toriginal = tools.timeit(as_node, (ias.url,), 5000)
tnodespace = tools.timeit(ns.as_node, (ias.url,), 5000)
print 'Nodespace.as_node is %s times faster than original as_node' % (toriginal/tnodespace)

toriginal = tools.timeit(as_node_url, (ias,), 5000)
tnodespace = tools.timeit(ns.as_node_url, (ias,), 5000)
print 'Nodespace.as_node_url is %s times faster than original as_node_url' % (toriginal/tnodespace)

