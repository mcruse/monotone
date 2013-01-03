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
#to fix something about cache_life

import time
from mpx.ion.omni import format_address
from mpx.lib.node import CompositeNode
from mpx.lib import msglog
from mpx.lib.msglog.types import INFO, WARN, ERR
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.threading import Lock

class OmniDevice(CompositeNode):
    """Base class for Omni Meters

    """

    __node_id__ = '8e222603-73cd-49ad-833d-2fa01c140553'
    def __init__(self):
        self.address = '000000000000'
	#don't pay attention to the value of bin_addr, it's randomly chosen
        self.bin_addr = '\x74\x60\x01\x43\x61\x09'
        self.last_updated = 0
        self.lock = Lock()
        super(OmniDevice, self).__init__()

    def configure(self, config):
        set_attribute(self, 'building_no', '0' , config, str)
        set_attribute(self, 'unit_no', '0' , config, str)
        set_attribute(self, 'address', REQUIRED, config, str)
        set_attribute(self, 'debug', 0, config, as_boolean)
        self.bin_addr = format_address(self.address)
        if self.debug:
            msglog.log('omnimeter', msglog.types.INFO, 
                       "OMNIMETER:%s" % (self.address))
        super(OmniDevice, self).configure(config)

    def configuration(self):
        config = super(OmniDevice, self).configuration()
        get_attribute(self, 'building_no', config)
        get_attribute(self, 'unit_no', config)
        get_attribute(self, 'address', config)
        return config
 
    def start(self):
        #is it ok?
        if self.is_running():
            raise EAlreadyRunning()
        self.debug = self.parent.debug
        self.cache_life = self.parent.cache_life
        self.retry_count = self.parent.retry_count
        self.reply_timeout = self.parent.reply_timeout
        super(OmniDevice, self).start()

    def _send_request(self, request_obj,
                      response_obj, wait_time=None, numretries=None):
        """Method to send request and get response back
        request and response packets need to be passed to it.
        It would send these packets through its parent's send_request method
        
        redundant now
        its job was to catch the exception and give the calling function 
        cleaner interface, but now it's not catching anything
        """
        if self.debug:
            msglog.log('omnimeter', msglog.types.INFO, 
                       'meter address in request object %s' 
                       %str(request_obj.findChildByName('addr').getValue()))
            msglog.log('omnimeter', msglog.types.INFO, 
                       'cs in request_object %s' 
                       %str(request_obj.findChildByName('cs').getValue()))

        self.parent.send_request(request_obj,
                                 response_obj, wait_time, numretries)

    def update_value(self, value):
        """Updates the meter's reading and notes down the time of update
        """
        self.value = value
        self.last_updated = time.time()

    def is_value_stale(self):
        """Checks whether the value is stale or fresh

        """
        return ((time.time() - self.last_updated) > self.cache_life)
