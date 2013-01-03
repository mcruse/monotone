"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
from moab.linux.lib.servicemgr import InittabManager

from mpx.lib.node import as_node_url
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.service import ServiceNode

class WebDEV(ServiceNode):
    def configure(self, cd):
        ServiceNode.configure(self, cd)
        set_attribute(self, "allow_ftp", "1", cd, int)
        return
    def configuration(self):
        cd = ServiceNode.configuration(self)
        get_attribute(self, "allow_ftp", cd, str)
        return cd
    def start(self):
        self._configure_webdev_ftp(self.enabled and self.allow_ftp)
        return
    def stop(self):
        self._configure_webdev_ftp(0)
        return
    def _configure_webdev_ftp(self, enable_webdev_user):
        my_node_url = as_node_url(self)
        inittab = InittabManager()
        assert inittab.has_key("MPX_FTPD"), (
            "inittab must contain an MPX_FTPD group, run " +
            "moab/linux/broadway.moab.linux.install from it's local directory."
            )
        daemon_name = 'ftpd'
        group = inittab["MPX_FTPD"]
        nodes = group.subset("REQUIRED_BY")
        has_my_node = nodes.has_item(my_node_url)
        docommit = 0
        if enable_webdev_user:
            if not has_my_node:
                nodes.add_item(my_node_url)
                docommit = 1
        else:
            if has_my_node:
                nodes.remove_item(my_node_url)
                docommit = 1
        is_already_enabled = group.is_daemon_enabled(daemon_name)
        
        if nodes.num_items() > 0:
            # There are nodes requiring MPX_FTPD.  Enable it, if it wasn't
            # already.
            if not is_already_enabled:
                group.enable_daemon(daemon_name)
                docommit = 1
        else:
            # No nodes require MPX_FTPD.  Disable it, if it wasn't already.
            if is_already_enabled:
                group.disable_daemon(daemon_name)
                docommit = 1
        if docommit:
            inittab.commit()
        return
