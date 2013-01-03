"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx

import array

import mpx
import mpx.ion
import mpx.lib
import mpx.lib.node
from mpx.lib.debug_print import debug_print

from mpx.ion.capstone.micro_turbine import command
from mpx.ion.capstone.micro_turbine import response

m = mpx.lib.factory('mpx.ion.mpxs1')
m.configure({'name':'ion','parent':'/'})
p = mpx.lib.node.as_node('/ion/port2')
p.configure({'baud':57600,'bits':8,'stop_bits':1,'parity':'none'})
l = mpx.lib.factory('mpx.ion.capstone.micro_turbine.line_handler')
l.configure({'name':'capstone','parent':p})
c = mpx.lib.factory('mpx.ion.capstone.micro_turbine.personality')
c.configure({'name':'micro_turbine','parent':l, 'turbine':0})

def dump(c):
    for i in c.children_names():
        print i, c.get_child(i).get()

r = l.command(command.ALLDAT())

for sr in r._line_map.keys():
    print r._get_response(sr)

r = l.command(command.PSSWRD(0,'USR123P'))
print 'protect mode', r.is_protect()

r = l.command(command.USRSTR()) # Checks user-start.
print 'can start', r.can_start()

r = l.command(command.STRCMD()) # Starts/stops the turbine (if USRSTR allows).
print 'will start', r.will_start()

r = l.command(command.LOGOFF())
print 'reset', r.reset()

def start(line_handler, turbine=0):
    l = line_handler
    r = l.command(command.PSSWRD(turbine,'USR123P'))
    print 'protect mode', r.is_protect()
    r = l.command(command.UTLCON(turbine,2)) # Set grid connect mode?
    print 'utility connection number', r.utility_connection_value()
    r = l.command(command.MEDBTU(turbine,1))
    print 'mode', r.mode()
    r = l.command(command.AUTRST(turbine,1))
    print 'auto restart', r.auto_restart()
    #r = l.command(command.WFRAMP(turbine,5)) # ?
    #print 'can start', r.can_start()
    r = l.command(command.STRCMD(turbine,1)) # Starts/stops the turbine (if USRSTR allows).
    print 'will start', r.will_start()

def stop(line_handler, turbine=0):
    r = l.command(command.PSSWRD(turbine,'USR123P'))
    print 'protect mode', r.is_protect()
    r = l.command(command.STRCMD(turbine,0)) # Stop the turbine.
    print 'will start', r.will_start()



