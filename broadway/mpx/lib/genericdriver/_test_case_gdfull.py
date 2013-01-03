"""
Copyright (C) 2011 Cisco Systems

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
_test_case_gdfull.py
"""

import os
import sys
import time
import syslog
import socket

from mpx.lib.threading import Thread

import gdconnection as gc
import gdlinehandler as gdlh
import gdutil as gu

from _test_case_gdconnection import MockSerialPortNode
from mpx import properties
from protocompiler import ProtoCompiler


from mpx_test import DefaultTestFixture, main

localhost = '127.0.0.1'
local_dev = 'lo'

debug = 0

def add_path(newpath):
    # Ensure that newpath is in the system path so that import will find it
    # to facilitate testing our newly generated classes.
    if not newpath in sys.path:
        sys.path.append(newpath)

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        add_path(properties.TEMP_DIR)
    #
    def test_get_fixed_width_object_from_serial_port(self):
        pn = MockSerialPortNode()

        #pn.debug = 5

        # Initialize some data to be 'read' from our mock serial port node.
        for x in chr(0xAA) + chr(0x03) + chr(0xFF):
            pn.addbuffer(ord(x))

        #print pn.get_buffer_str()
        
        conn = gc.FrameworkSerialPortWrapper(pn)

        lines = "" \
                "# Single byte Class\n" \
                "class singlebyte {\n" \
                "   uint8 preamble = 0xAA;\n" \
                "   uint8 data;\n" \
                "   uint8 postamble = 0xFF;\n" \
                "}\n"

        lines = lines.split('\n')

        pc = ProtoCompiler()

        pc.parseLines(lines)

        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "singlebyte.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import singlebyte

        request_obj = singlebyte.singlebyte()
        response_obj = singlebyte.singlebyte()

        req_data_obj = request_obj.findChildByName('data')
        #
        resp_data_obj = response_obj.findChildByName('data')
        
        lh = gdlh.SimpleLineHandler(conn)

        req_data_obj.setValue(0x01)

        res = lh.send_request_with_response(request_obj, response_obj, 30)

        #print res
        
        os.remove(pyfilename)
    #
    def test_get_variable_width_object_from_serial_port(self):
        pn = MockSerialPortNode()

        #pn.debug = 5

        # Initialize some data to be 'read' from our mock serial port node.
        for x in chr(0x03) + chr(0xAA) + chr(0x03) + chr(0xFF):
            pn.addbuffer(ord(x))

        #print pn.get_buffer_str()
        
        conn = gc.FrameworkSerialPortWrapper(pn)

        lines = "" \
                "# Variable Buffer 1 Class\n" \
                "class testvbuffer1 {\n" \
                "   vbuffer1 vbuffer01;\n" \
                "}\n"


        lines = lines.split('\n')

        pc = ProtoCompiler()

        pc.parseLines(lines)

        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "testvbuffer1.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testvbuffer1

        request_obj = testvbuffer1.testvbuffer1()
        response_obj = testvbuffer1.testvbuffer1()

        req_vbuffer_obj = request_obj.findChildByName('vbuffer01')
        #
        resp_vbuffer_obj = response_obj.findChildByName('vbuffer01')
        
        lh = gdlh.SimpleLineHandler(conn)

        req_vbuffer_obj.setValue("abc")

        res = lh.send_request_with_response(request_obj, response_obj, 30)

        assert res == 1, "send_request_with_response() should have returned 1."

        assert resp_vbuffer_obj.getValue() == chr(0xAA) + chr(0x03) + chr(0xFF), "Did not get expected value."
        
        os.remove(pyfilename)


#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
        
