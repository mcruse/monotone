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
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import CompositeNode, as_node

from mpx.lib import msglog
from mpx.lib.msglog.types import INFO, WARN, ERR

import mpx.lib.genericdriver.gdconnection as gdconn
import mpx.lib.genericdriver.gdlinehandler as gdlh
import mpx.lib.genericdriver.examples.simpleregister as sr

class SimpleRegisterProtocolClient(CompositeNode):
    def __init__(self):
        self.lh = None
        self.conn = None
        self.request_obj = sr.setregister()
        self.response_obj = sr.setregisterresponse()
        self.value = 0

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
    ##
    # Log's the specified message with the specified type.
    #
    def _logMsg(self, type, msg):
        msglog.log('simple_register_client', type, msg)
    #
    def start(self):
        self._logMsg(INFO, 'In start().')
        #
        self.conn = gdconn.FrameworkSerialPortWrapper(self.parent)
        self.lh = gdlh.SimpleLineHandler(self.conn)
    #
    def stop(self):
        self._logMsg(INFO, 'In stop().')
        #
        self.lh.disconnect()
        
    def set(self, newval):
        self._logMsg(INFO, "In set() with %s" % str(newval))
        #
        self.req_regno_obj.setValue(0x01)
        self.req_value_obj.setValue(newval)
        #
        res = None
        try:
            res = self.lh.send_request_with_response(self.request_obj, self.response_obj, 30)
        except:
            self._logMsg(WARN, "Got exception trying to send request")
            msglog.exception()
        # No exception, so we must have gotten a response, check it out.
        if not res:
            # Did not get a matching response.
            self._logMsg(WARN, "Did not receive a matching response.")
        else:
            # Check to see if we got a matching and successful response.
            resp_code_value = self.resp_code_obj.getValue()
            #
            self._logMsg(INFO, "Got response code: %s" % str(resp_code_value))
        #
        self.value = newval
    #
    def get(self, skipCache=0):
        return self.value

##      
# creates and returns an instance of the SimpleRegisterClientProtocol class.
#
def factory():
    return SimpleRegisterProtocolClient()
