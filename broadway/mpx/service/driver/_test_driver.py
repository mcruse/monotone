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
from mpx.lib.node import as_node
try: vpoint = as_node('/interfaces/virtuals/value')
except: pass
else: vpoint.prune()

try: dmanager = as_node('/services/Value Drivers')
except: pass
else: dmanager.prune()

try: mopd1 = as_node('/services/Value Drivers/MOPD1')
except: pass
else: mopd1.prune()

from mpx.lib.node import simple_value
#reload(simple_value)
vpoint = simple_value.SimpleValue()
vpoint.configure({'name': 'value', 'parent': '/interfaces/virtuals'})
vpoint.start()
vpoint.set(0)

r1 = as_node('/interfaces/relay1')
r2 = as_node('/interfaces/relay2')
r1.set(0)
r2.set(0)

from mpx.service import driver
from mpx.service.driver import interfaces
#reload(interfaces)
#reload(driver)

dmanager = driver.PeriodicDriverManager()
dmanager.configure({'name':'Value Drivers','parent': '/services'})
dmanager.start()

mopd1 = driver.ValueDriver()
mopd1.configure({'name': 'MOPD1', 
                'parent': dmanager, 
                'input': '/interfaces/virtuals/value', 
                'outputs': ['/interfaces/relay1','/interfaces/relay2']})
mopd1.debug = 1
mopd1.start()

print 'R1: %s, R2: %s, Simple Value: %s' % (r1.get(), r2.get(), vpoint.get())
vpoint.set(not vpoint.get())
print 'R1: %s, R2: %s, Simple Value: %s' % (r1.get(), r2.get(), vpoint.get())