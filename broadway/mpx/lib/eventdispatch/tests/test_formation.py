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
from mpx.lib.node import as_node
cm = as_node('/services/Cloud Manager')
cm.update_formation(['172.16.32.110', '172.16.32.111', '172.16.32.113', '172.16.32.115', '172.16.32.117', '172.16.32.119'])

cm.update_formation(['172.16.32.110', '172.16.32.111', '172.16.32.112', '172.16.32.113'])
cm.update_formation(['172.16.32.110', '172.16.32.111'])


from mpx.service.cloud import manager
reload(cloud)
cm.__class__ = cloud.CloudManager

import time
def run(count, sleep = .5):
    for i in range(0,count):
        print time.time()
        time.sleep(sleep)
