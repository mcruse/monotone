"""
Copyright (C) 2006 2010 2011 Cisco Systems

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

import sys
import socket
from mpx.lib.node import as_node
from mpx.service.configuration import SOFT_EXIT, HARD_EXIT

if '--host' in sys.argv:
    index = sys.argv.index('--host')
    host = sys.argv[index + 1]
    del(sys.argv[index : index + 1])
else:
    host = socket.gethostbyname(socket.gethostname())
if '--port' in sys.argv:
    index = sys.argv.index('--port')
    port = sys.argv[index + 1]
else:
    port = '5150'
config_service = as_node('mpx://' + host + ':' + port + '/services/configuration')

def read():
    print config_service.read()

def read_len():
    print len(config_service.read())

def write():
    file = sys.stdin

    if '--file' in sys.argv:
        index = sys.argv.index('--file')
        filename = sys.argv[index + 1]
        file = open(filename, 'r')

    xml = file.read()

    return config_service.write(xml, 'soft')

def write_runtime():
    return config_service.write_runtime()

def read_runtime():
    print config_service.read_runtime()

def exit():
    exit_type = SOFT_EXIT
    if '--type' in sys.argv:
        index = sys.argv.index('--type')
        if sys.argv[index + 1] == 'hard':
            exit_type = HARD_EXIT
    return config_service.exit(exit_type)

if __name__ == '__main__':
    eval(sys.argv[1] + '()')
