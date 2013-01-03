"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import time
import mpx.ion
import mpx.lib
from mpx.lib.node import as_node

# Get a basic MPX ION.
mpx_ion = as_node('/interfaces')

# Get the port for the Modbus LineHandler.  NOTE: CPP also uses port3
port_name = 'com2'
port_ion = mpx_ion.get_child(port_name)

# Configure the port and open it.
port_ion.configure({'baud':4800,     # NOTE:  CPP is 9600.
                    'bits':8,        # DG50 only supports 8 bits.
                    'parity':'none', # 0=None, 1=Even, 2=Odd.
                    'stop_bits':2,   # NOTE:  CPP is NOW 1.
                    'debug':0})

# Bind a Modbus Line Handler to the port.
lh_ion = mpx.lib.factory('mpx.ion.modbus')
lh_ion.configure({'name':'modbus',
                  'parent':port_ion})

# Set the DG50's slave address, instanciate it, and bind it to the
# Modbus LineHandler.
slave_address = 1	# NOTE:  This is NOW 3 at CPP.
dg50_ion = mpx.lib.factory('mpx.ion.modbus.dg50.dg50')
dg50_ion.configure({'name':'DG50', 'parent':lh_ion, 'address':slave_address})

def dump_ions(ions):
    print 'Dumping IONs\' values.  <Ctl>C to quit.'
    # Print all ions' values.
    for i in ions:
        print i.name, i.get()


ions = dg50_ion.children_nodes()
while 1:
    try:
        print
        print 'Sleeping one second.'
        time.sleep(1)
        # Print all registers' values.
        dump_ions(ions)
    except KeyboardInterrupt:
        print 'Exiting due to <Ctl>C.'
        break
    except:
        pass
