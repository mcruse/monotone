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
"""
_test_case_gdconnection.py
"""

import os
import sys
import time
import syslog
import socket
import array

from mpx.lib.threading import Thread

import gdconnection as gc

from mpx_test import DefaultTestFixture, main

localhost = '127.0.0.1'
local_dev = 'lo'

def dump_buffer(buffer):
    str = ''
    for x in buffer:
        str = '%s0x%02X ' % (str, x)
    str = str[:-1]
    return str

# Code largely borrowed from mpx/lib/tracer100/portmocker.py
class MockSerialPortNode:
    def __init__(self, _debug = 0):
        self.port_buffer = array.array('B')
        self.debug = _debug

    def get_buffer(self):
        return self.port_buffer

    def get_buffer_str(self):
        return dump_buffer(self.port_buffer)

    def read(self, buffer, length, timeout):
        try:
            a = self.port_buffer[0]
            if self.debug:
                print "In PortMocker: read() with length of %d, timeout of %d, returning 0x%02X" % (length, timeout, a)
            self.port_buffer.remove(a)
            buffer.append(a)
        except:
            raise ETimeout

    def read_including(self, buffer, list, timeout):
        if self.debug:
            print "In read_including with list %s and timeout %d." % (list, timeout)
        amnotdone = 1
        while (amnotdone):
            tmp_buffer = array.array('B')
            self.read(tmp_buffer, 1, timeout)
            try: 
                c = tmp_buffer[0]
                buffer.append(c)
                amin = chr(c) in list
                if amin:
                    amnotdone = 0
                    if self.debug:
                        print "%s in %s" % (c, list)
                else:
                    amnotdone = 1
                    if self.debug:
                        print "%s not in %s" % (c, list)
            except:
                break
        if self.debug:
            print "read_including returning %s." % dump_buffer(buffer)

    def write(self, buffer):
        if self.debug:
            print "In PortMocker: write() with buffer of %s." % buffer

    def addbuffer(self, byte):
        if self.debug:
            print "In PortMocker: addbuffer() with 0x%02X" % byte
        self.port_buffer.append(byte)

    def __init(self):
        if self.debug:
            print "In PortMocker: init()."

    def open(self):
        if self.debug:
            print "In PortMocker: open()."

    def drain(self):
        if self.debug:
            print "In PortMocker: drain()."
        return array.array('c')

    def flush(self):
        if self.debug:
            print "In PortMocker: flush()."

    def close(self):
        if self.debug:
            print "In PortMocker: close()."

    def _set_serial(self):
        if self.debug:
            print "In PortMocker: _set_serial()."

    def is_open(self):
        if self.debug:
            print "In PortMocker: is_open()."
        return 1


# A Simple TCP Connection thread.  Accepts the connection, then
class TCPConnectionThread(Thread):
    def __init__(self, parent, sock, client_ip):
        self.parent = parent
        self.sock = sock
        self.clientip = client_ip
        self.should_run = 1
        #
        Thread.__init__(self)
        #
        syslog.syslog('Got a new connection.')
        #mstr = 'From: %s' % str(socket.inet_ntoa(client_ip))
        mstr = 'From: %s' % str(client_ip)
        syslog.syslog(mstr)
    #
    def run(self):
        syslog.syslog('In server thread run.')

        while self.should_run:
            syslog.syslog('b4 read')
            c = self.sock.read(1)
            syslog.syslog('after read')
            syslog.syslog('Got character: %s' % c)
        #
        self.sock.shutdown()
        self.sock.close()
    #
    def stop(self):
        self.should_run = 0
    

        #syslog.syslog('Before doing read of %d bytes.' % len(self.expected_data))
       # 
        #received_data = s.read(len(self.expected_data))
#
 #       if received_data == self.expected_data:
 #           self.got_expected_data = 1
#
 #       self.got_data = 1
        
class TCPReaderServerThread(Thread):
    def __init__(self, conn, expected_data):
        self.conn = conn
        self.expected_data = expected_data
        self.got_data = 0
        self.got_expected_data = 0

        Thread.__init__(self)
    #
    def run(self):
        syslog.syslog('In server thread run.')
        
        s.open()

        syslog.syslog('Before doing read of %d bytes.' % len(self.expected_data))
        
        received_data = s.read(len(self.expected_data))

        if received_data == self.expected_data:
            self.got_expected_data = 1

        self.got_data = 1
        

class TestCase(DefaultTestFixture): 
    def test_create_client_connection(self):
        x = gc.ClientTCPSocketConnection(localhost, 8090)

    def test_create_server_connection(self):
        x = gc.ServerTCPSocketConnection(local_dev, 8090)

    def test_open_client_with_no_server(self):
        x = gc.ClientTCPSocketConnection(localhost, 8090)
        didcatch = 0
        try:
            x.open()
        except:
            didcatch = 1
        if not didcatch:
            # Should have caught an exception, but did not.  Either we have
            # a failure in our code, or we got very unlucky with some server
            # running on the port we tried for our test.
            raise "Did not catch exception when expected"

    def test_simple_client_connection_to_server(self):
        c = gc.ClientTCPSocketConnection(localhost, 8091)
        #s = gc.ServerTCPSocketConnection(local_dev, 8091)

        sobj = gc.TCPServer(local_dev, 8091, TCPConnectionThread)
        sobj.open()

        # Tell the server to get ready to accept a connection.
        #s.open()

        # Now we should be able to open a client connection.
        c.open()

        time.sleep(10)

        # Apparently we didn't get any exceptions, cool.  Call it good.
        c.close()
        sobj.close()

    def _test_simple_client_write_to_server(self):
        syslog.openlog('test_simple_client_write_to_server')
        #
        c = gc.ClientTCPSocketConnection(localhost, 8092)
        s = gc.ServerTCPSocketConnection(local_dev, 8092)

        test_data = '*' * 5

        sthread = TCPReaderServerThread(s, test_data)
        sthread.start()

        # Wait a little while for server to come up.
        time.sleep(.1)

        syslog.syslog('Before server open')
        
        # Tell the server to get ready to accept a connection.
        s.open()

        syslog.syslog('Before client open')

        # Now we should be able to open a client connection.
        c.open()

        c.write(test_data, len(test_data))

        syslog.syslog('After client write')

        # Wait for a while until the data has been received.
        while 1:
            if sthread.got_data:
                print 'Got data!'
                break
            time.sleep(.05)

        # Apparently we didn't get any exceptions, cool.  Call it good.
        c.close()
        s.close()
    #
    def test_simple_serial_port(self):
        s = MockSerialPortNode()

        for x in 'abcdef':
            s.addbuffer(ord(x))
        
        pw = gc.FrameworkSerialPortWrapper(s)

        data = pw.read(4, 100)

        assert data == "abcd", "Expected abcd, go %s" % str(data)

        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
        
