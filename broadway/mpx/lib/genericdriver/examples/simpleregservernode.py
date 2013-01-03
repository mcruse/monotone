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
import time, os
import types

from mpx import properties
from mpx.lib import msglog
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import CompositeNode, as_node
from mpx.lib import threading
from mpx.lib.exceptions import ETimeout

from mpx.lib import msglog
from mpx.lib.msglog.types import INFO, WARN, ERR

import mpx.lib.genericdriver.gdconnection as gdconn
import mpx.lib.genericdriver.gdlinehandler as gdlh
import mpx.lib.genericdriver.examples.simpleregister as sr
import mpx.lib.genericdriver.gdutil as gdutil

class SimpleRegisterServerProtocol(CompositeNode):
    def __init__(self):
        self.lh = None
        self.conn = None
        self.request_obj = sr.setregister()
        self.response_obj = sr.setregisterresponse()
        self._start_thread_instance = None
        self.value = 0
    ##
    # Log's the specified message with the specified type.
    #
    def _logMsg(self, type, msg):
        msglog.log('simple_register_server', type, msg)
    #
    def start(self):
        self._logMsg(INFO, 'In start().')
        #
        self.conn = gdconn.FrameworkSerialPortWrapper(self.parent)
        self.lh = gdlh.SimpleLineHandler(self.conn)
        #
        # Find the relevant protocol child objects ahead of time to
        # be more efficient.
        self.req_cmd_obj = self.request_obj.findChildByName('cmd')
        self.req_regno_obj = self.request_obj.findChildByName('regno')
        self.req_value_obj = self.request_obj.findChildByName("value")
        #
        self.resp_cmdecho_obj = self.response_obj.findChildByName("cmdecho")
        self.resp_regno_obj = self.response_obj.findChildByName("regno")
        self.resp_value_obj = self.response_obj.findChildByName("value")
        self.resp_code_obj = self.response_obj.findChildByName("responsecode")
        #
        self._start_thread_instance = threading.Thread(None,self._start_thread)
        self._start_thread_instance.start()
    #
    def stop(self):
        self._logMsg(INFO, 'In stop().')
        #
        self.lh.disconnect()
        
    def set(self, newval):
        self._logMsg(INFO, "In set() with %s" % str(newval))
        #
        regno_obj = self.request_obj.findChildByName('regno')
        value_obj = self.request_obj.findChildByName('value')

        regno_obj.setValue(0x01)
        value_obj.setValue(newval)

        try:
            self.lh.send_request_with_response(self.request_obj, self.response_obj, 10)
        except:
            self._logMsg(WARN, "Got exception trying to sending request")
            msglog.exception()
        #
        self.value = newval
    #
    def get(self, skipCache=0):
        return self.value
    #
    def _start_thread(self):
        self._go = 1
        while self._go:
            # Just wait for a request.  When it comes in, deal with it.
            ret = 0
            try:
                ret = self.lh.receive_response(self.request_obj, 60)
            except Exception,e:
                if e.__class__ == gdutil.GDTimeoutException:
                    # Just a timeout, these are expected.
                    print 'Got a timeout.'
                elif e.__class__ == ETimeout:
                    # Just a timeout, these are expected.
                    print 'Got a timeout.'
                else:
                    self._logMsg(INFO, "Got an exception waiting for a request")
                    msglog.exception()
            if not ret:
                continue
            # OK, we must have gotten a request.
            self._logMsg(INFO, "Got a request: %s" % str(self.request_obj))

            cmd_value = self.req_cmd_obj.getValue()
            regno_value = self.req_regno_obj.getValue()
            value_value = self.req_value_obj.getValue()

            mstr = "Got cmd of %s, regno of %s and value of %s" % (str(cmd_value),
                                                                   str(regno_value),
                                                                   str(value_value))
            self._logMsg(INFO, mstr)
            #
            self.value = self.req_value_obj.getValue()
            #
            # Set up the response appropriately.
            self.resp_cmdecho_obj.setValue(int(cmd_value) + 0x80)
            self.resp_regno_obj.setValue(regno_value)
            self.resp_value_obj.setValue(value_value)
            #
            # For now, always report everything is OK.
            self.resp_code_obj.setValue(0)
            #
            # Send the response.
            self.lh.send_request_without_response(self.response_obj, 10)
            
        return

##      
# creates and returns an instance of the SimpleRegisterServerProtocol class.
#
def factory():
    return SimpleRegisterServerProtocol()
