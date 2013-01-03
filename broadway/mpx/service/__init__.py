"""
Copyright (C) 2001 2002 2003 2005 2007 2010 2011 Cisco Systems

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
# Package containing classes, interfaces, and functions
# associated with services.  Services are nodes that perform
# actions.  An example of typical services are the logger which enables
# both the logging and retrieving of information from log files; and
# the http_server, which listens on a port for http connections
# and enables http interaction with the MPX like file serving and
# node browsing, which are also services.
#

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.node import ConfigurableNodePublicInterface
from mpx.lib.node import PublicInterface
from mpx.lib.node import ServiceInterface
from mpx.lib.node import ServiceNode
from mpx.lib.node import SubServiceNode
from mpx.lib.configure import as_boolean

# influence start order by influencing the manner in which
# children_*() returns its results.  Host Manager must start first and
# the garbage_collector last.
def service_sort(a, b):
    start_map = {'Host Manager':0, 'Entity Manager':70,
                 'control':75, 'Alarm Manager':77, 'Schedule Manager':80, 
                 'Query Manager': 100, 'logger':105, 'garbage_collector':110}
    if hasattr(a, 'name'):
        a = a.name
    if hasattr(b, 'name'):
        b = b.name
    return cmp(start_map.get(a, 50), start_map.get(b, 50))
##
# The anchor object for the '/services' namespace.
class _Anchor(ServiceNode):
    def __init__(self):
        ServiceNode.__init__(self)
        # Instantiate implicit children.
        from mpx.service.interactive import InteractiveService
        InteractiveService().configure({'name':'Interactive Service',
                                        'parent':self,'debug':0,
                                        'port':9666,'interface':'localhost'})
        from mpx.service.time import Time
        Time().configure({'name':'time','parent':self})
        from mpx.service.session import SessionManager
        SessionManager().configure({'name':'session_manager', 'parent':self})
        from mpx.service.user_manager import UserManager
        UserManager().configure({'name':'User Manager', 'parent':self})
        from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER
        SUBSCRIPTION_MANAGER.configure({'name':'Subscription Manager',
                                        'parent':self})
        # Guarantee that /services/garbage_collector will exist, whether or not
        # there is an entry in the XML file.
        from mpx.service.garbage_collector import GARBAGE_COLLECTOR
        # @todo Make ReloadableSingleton!
        GARBAGE_COLLECTOR.configure({'name':'garbage_collector',
                                     'parent':self})

    def configure(self, config):
        if not getattr(self, 'parent', None):
            config.setdefault('parent', '/')
        self.setattr('secured', as_boolean(config.get('secured', True)))
        ServiceNode.configure(self, config)
    
    def configuration(self):
        config = ServiceNode.configuration(self)
        config['secured'] = self.secured
        return config
    
    # override the childen_nodes and children_names method so that
    # we can control the order in which the results are presented.
    # This is an interim solution that allows use to resolve some 
    # start order dependencies within the "services" branch.  These
    # issues, as of June '10, do not prevent functionality, but 
    # produce an extremely noisy msglog. It also makes sense to, for 
    # example, not start the control service before the points (such
    # as BACnet) it might be acting on are available.
    def children_nodes(self, **options):
        children = ServiceNode.children_nodes(self, **options)
        children.sort(service_sort)
        return children
    
    def children_names(self, **options):
        children = ServiceNode.children_names(self, **options)
        children.sort(service_sort)
        return children
        

##
# @return The node of the '/services' ion.
def factory():
    return _Anchor()
