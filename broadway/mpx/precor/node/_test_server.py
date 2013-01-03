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
import struct
from mpx.lib import socket

listen_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
linger = struct.pack("ii", 1, 0) # prevent skt from jabbering with empty pkts after closure
listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
skt_address = ('', 8080)
print 'A'
listen_skt.bind(skt_address)
try:
   listen_skt.listen(1)
except Exception, e:
   print 'Call to socket.listen() failed: %s' % str(e)
while 1:
   print 'B'
   conn, addr = listen_skt.accept()
   print 'C'
   conn.setblocking(1)
   conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
   linger = struct.pack("ii", 1, 0) # prevent skt from jabbering with empty pkts after closure
   conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
   try:
      while 1:
         data = conn.recv(1024, 3.0)
         print data
   except:
      conn.close()
   

   
   