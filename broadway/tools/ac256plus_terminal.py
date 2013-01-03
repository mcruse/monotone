"""
Copyright (C) 2001 2006 2010 2011 Cisco Systems

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
import thread

host = '127.0.0.1'
port = 5151

def print_help():
    print sys.argv[0], '[hostname [port]]'

def parse_args():
    global host
    global port
    for arg in sys.argv:
        if arg == '-h' or \
           arg == '-?':
            print_help()
    if len(sys.argv) > 3:
        print_help()
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    if len(sys.argv) > 1:
        host = sys.argv[1]

def connect(host,port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host,port))
    return s

def recv(s):
    global connected
    while connected:
        try:
            msg = s.recv(1024)
        except socket.error, data:
            if 104 in data:
                connected = 0
                msg = ''
            else:
                raise socket.error, data
        if msg:
            sys.stdout.write(msg)
            sys.stdout.flush()
        else:
            connected = 0

def send(s):
    global connected
    while connected:
        command = ''
        try:
            command = raw_input()
        except(EOFError):
            command = chr(4)
        s.send(command)
        s.send('\r')

# main()
parse_args()
s = connect(host,port)
connected = 1
thread.start_new_thread(send,(s,))
recv(s)
