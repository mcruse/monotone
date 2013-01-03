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
import time, os
import types
import string
import array

from mpx import properties
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.exceptions import EInvalidValue, ETimeout
from mpx.lib import EnumeratedDictionary
from mpx.lib import msglog
from mpx.lib.msglog.types import INFO, WARN, ERR

import mpx.lib.genericdriver.gdconnection as gdconn
import mpx.lib.genericdriver.gdlinehandler as gdlh
import mpx.ion.usap.usapmsg as usapm

command = EnumeratedDictionary({0:'DACT', 1:'ACTI'})

class UsapDevice(CompositeNode):
    """ This class is used to define USAP device. Its primary role is to interact with USAP device over RS-232 medium."""

    def __init__(self):
        CompositeNode.__init__(self)
        self.debug = 0
        self.enabled = 1
        self.legacy_operating_code = 1
        self.lh = None
        self.conn = None
        self.request_obj = usapm.UsapRequest()
        self.response_obj = usapm.UsapResponse()
        self.req_startCode_obj = None
        self.req_vData_obj = None
        self.req_crc_obj = None
        self.resp_startCode_obj = None
        self.resp_vData_obj = None
        self.resp_crc_obj = None
        self.value = 'Room.Section.Preset.Command'
        self.unison_v1_9_0_or_prior = 1
    #
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'enabled', self.enabled, config, as_boolean)
        set_attribute(self, 'unison_v1_9_0_or_prior', self.unison_v1_9_0_or_prior, config, as_boolean)
        set_attribute(self, 'debug', self.debug, config, as_boolean)

    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'enabled', config)
        get_attribute(self, 'unison_v1_9_0_or_prior', config)
        get_attribute(self, 'debug', config)
        return config

    def start(self):
        msglog.log('USAP', INFO, 'Device: In start().')
        if self.enabled:
            self.conn = gdconn.FrameworkSerialPortWrapper(self.parent)
            self.lh = gdlh.SimpleLineHandler(self.conn)
        # Find the relevant protocol child objects ahead of time to
        # be more efficient.
        self.req_startCode_obj = self.request_obj.findChildByName("startCode")
        self.req_vData_obj = self.request_obj.findChildByName("vData")
        self.req_crc_obj = self.request_obj.findChildByName("crc")
        #
        self.resp_startCode_obj = self.response_obj.findChildByName("startCode")
        self.resp_vData_obj = self.response_obj.findChildByName("vData")
        self.resp_crc_obj = self.response_obj.findChildByName("crc")
        CompositeNode.start(self)
        #
    #
    def stop(self):
        msglog.log('USAP', INFO, 'Device: In stop().')
        self.lh.disconnect()
        CompositeNode.stop(self)

    def set(self, newval):
        #
        cmd = (str(newval).rsplit('.', 1)[1]).split('=', 1)[0]
        msglog.log('USAP', INFO, "Device:set() with %s (cmd=%s)" % (str(newval), str(cmd)))
        vData = string.join(['\x00\x00\x40', str(newval)], '')
        self.req_vData_obj.setValue(vData)
        #
        res = None
        needResponse = 0
        if cmd == 'bACT' or cmd == 'bAAP':
            needResponse = 1
	#
        self.lh.connection.drain()
        if self.unison_v1_9_0_or_prior == 1 and needResponse == 0:
            try:
                self.lh.send_request_without_response(self.request_obj, 30)
                self.value = str(newval)
                time.sleep(1)
            except Exception, e:
                msglog.log('USAP', WARN, "Device:set() - Got exception trying to send request")
                msglog.exception()
                raise ETimeout('Error sending USAP request')
        else:
            try:
                res = self.lh.send_request_with_response(self.request_obj, self.response_obj, 30)
            except Exception, e:
                msglog.log('USAP', WARN, "Device:set() - Got exception trying to send request")
                msglog.exception()
                raise ETimeout('Error sending USAP request')
            # No exception, so we must have gotten a response, check it out.
            if not res:
                # Did not get a matching response.
                msglog.log('USAP', WARN, "Device:set() - Did not receive a matching response.")
            else:
                # Check to see if we got a matching and successful response.
                resp_startCode_value = self.resp_startCode_obj.getValue()
                resp_vData_value = self.resp_vData_obj.getValue()
                resp_crc_value = self.resp_crc_obj.getValue()
			#
                if resp_startCode_value != 0xEE or resp_crc_value != 0x0000:
                    msglog.log('USAP', WARN, "Device:set() - Received invalid response frame with startCode = %02X and CRC = %04X." % ( resp_startCode_value, resp_crc_value ))
                # Get the USAP command
                resp_code_value = resp_vData_value[3:]
                error = resp_code_value.count('?')
                if error == 0:
                    msglog.log('USAP', INFO, "Device:set() - Got response code: %s" % (str(resp_code_value)))
                    self.value = resp_code_value
                    time.sleep(1)
                else:
                    msglog.log('USAP', WARN, "Device:set() - Got ERROR response code: %s" % str(resp_code_value))
                    raise EInvalidValue('Got ERROR response code: %s' % str(resp_code_value))

    #
    def get(self, skipCache=0):
        msglog.log('USAP', INFO, "Device:get()")
        #
        return self.value

class Room(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.debug = 0
        self.enabled = 1
        self.room = 1

    def configure(self,config):
        CompositeNode.configure(self,config)
        self.debug = self.parent.debug
        self.enabled = self.parent.enabled

    def configuration(self):
        config = CompositeNode.configuration(self)
        return config

class Section(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.debug = 0
        self.enabled = 1
        self.room = 0

    def configure(self,config):
        CompositeNode.configure(self,config)
        self.debug = self.parent.debug
        self.enabled = self.parent.enabled

    def configuration(self):
        config = CompositeNode.configuration(self)
        return config

class Object(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.debug = 0
        self.enabled = 1
        self.lh = None
        self.request_obj = None
        self.response_obj = None
        self.req_startCode_obj = None
        self.req_vData_obj = None
        self.req_crc_obj = None
        self.resp_startCode_obj = None
        self.resp_vData_obj = None
        self.resp_crc_obj = None
        self.path = ''
        self.value = command['DACT']
        self.unison_v1_9_0_or_prior = 1
    #
    def configure(self,config):
        CompositeNode.configure(self,config)
        self.debug = self.parent.debug
        self.enabled = self.parent.enabled
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        return config
    #
    def start(self):
        if self.parent.room == 1:
            msglog.log('USAP', INFO, 'Object:start() - %s --> %s --> %s' % (self.parent.parent.name, self.parent.name, self.name))
            self.path = string.join([self.parent.name, self.name], '.')
            self.lh = self.parent.parent.lh
            self.request_obj = self.parent.parent.request_obj
            self.response_obj = self.parent.parent.response_obj
            self.unison_v1_9_0_or_prior = self.parent.parent.unison_v1_9_0_or_prior
        else:
            msglog.log('USAP', INFO, 'Object:start() - %s --> %s --> %s --> %s' % (self.parent.parent.parent.name, self.parent.parent.name, self.parent.name, self.name))
            self.path = string.join([self.parent.parent.name, \
                                     self.parent.name, self.name], '.')
            self.lh = self.parent.parent.parent.lh
            self.request_obj = self.parent.parent.parent.request_obj
            self.response_obj = self.parent.parent.parent.response_obj
            self.unison_v1_9_0_or_prior = self.parent.parent.parent.unison_v1_9_0_or_prior

        # Find the relevant protocol child objects ahead of time to
        # be more efficient.
        self.req_startCode_obj = self.request_obj.findChildByName("startCode")
        self.req_vData_obj = self.request_obj.findChildByName("vData")
        self.req_crc_obj = self.request_obj.findChildByName("crc")
        #
        self.resp_startCode_obj = self.response_obj.findChildByName("startCode")
        self.resp_vData_obj = self.response_obj.findChildByName("vData")
        self.resp_crc_obj = self.response_obj.findChildByName("crc")
        #
        CompositeNode.start(self)
    #
    def stop(self):
        msglog.log('USAP', INFO, 'Object: In stop().')
        CompositeNode.stop(self)
    #
    def set(self, newval):
        #
        newval = str(newval).split('.', 1)[0]
        if newval.isdigit():
            newval = int(newval)
        
        if not command.has_key(newval):
            msglog.log('USAP', WARN, "Object:set() with invalid command - %s" % str(newval))
            raise EInvalidValue('Invalid Command', str(newval),
                                'Valid commands are \'0:DACT\' or \'1:ACTI\'.')

        if self.value == command[newval]:
            msglog.log('USAP', INFO, "Object:set() - Current value is same as new value \'%s\', so no action required." % str(command[newval]))
            return;

        vData = string.join(['\x00\x00\x40', self.path, '.', str(command[newval])], '')
        msglog.log('USAP', INFO, "Object:set() - newval = %s, vData(%d) = %s" % (str(command[newval]), len(vData), str(vData)))
        self.req_vData_obj.setValue(vData)
        #
        res = None
	#
        self.lh.connection.drain()
        if self.unison_v1_9_0_or_prior == 1:
            try:
                self.lh.send_request_without_response(self.request_obj, 30)
                time.sleep(1)
            except Exception, e:
                msglog.log('USAP', WARN, "Object:set() - Got exception trying to send request")
                msglog.exception()
                raise ETimeout('Error sending USAP request')
        else:
            try:
                res = self.lh.send_request_with_response(self.request_obj, self.response_obj, 30)
            except Exception, e:
                msglog.log('USAP', WARN, "Object:set() - Got exception trying to send request")
                msglog.exception()
                raise ETimeout('Error sending USAP request')
            # No exception, so we must have gotten a response, check it out.
            if not res:
                # Did not get a matching response.
                msglog.log('USAP', WARN, "Object:set() - Did not receive a matching response.")
            else:
                # Check to see if we got a matching and successful response.
                resp_startCode_value = self.resp_startCode_obj.getValue()
                resp_vData_value = self.resp_vData_obj.getValue()
                resp_crc_value = self.resp_crc_obj.getValue()
			#
                if resp_startCode_value != 0xEE or resp_crc_value != 0x0000:
                    msglog.log('USAP', WARN, "Object:set() - Received invalid response frame with startCode = %02X and CRC = %04X." % ( resp_startCode_value, resp_crc_value ))
                # Get the USAP command
                resp_code_value = resp_vData_value[3:]
                error = resp_code_value.count('?')
                if error == 0:
                    self.value = command[newval]
                    msglog.log('USAP', INFO, "Object:set() - Got response code: %s with value: %s" % (str(resp_code_value), str(self.value)))
                    time.sleep(1)
                else:
                    msglog.log('USAP', WARN, "Object:set() - Got ERROR response code: %s" % str(resp_code_value))
                    raise EInvalidValue('Got ERROR response code: %s' % str(resp_code_value))

    #
    def get(self, skipCache=0):
        vData = string.join(['\x00\x00\x40', self.path, '.', 'bACT'], '')
        self.req_vData_obj.setValue(vData)
        msglog.log('USAP', INFO, "Object:get() - Sending request: %s" % (str(vData)))
        #
        res = None
	#
        self.lh.connection.drain()
        try:
            res = self.lh.send_request_with_response(self.request_obj, self.response_obj, 30)
        except Exception, e:
            msglog.log('USAP', WARN, "Object:get() - Got exception trying to send request")
            msglog.exception()
            raise ETimeout('Error sending USAP request')
        # No exception, so we must have gotten a response, check it out.
        if not res:
            # Did not get a matching response.
            msglog.log('USAP', WARN, "Object:get() - Did not receive a matching response.")
        else:
            # Check to see if we got a matching and successful response.
            resp_startCode_value = self.resp_startCode_obj.getValue()
            resp_vData_value = self.resp_vData_obj.getValue()
            resp_crc_value = self.resp_crc_obj.getValue()
			#
            if resp_startCode_value != 0xEE or resp_crc_value != 0x0000:
                msglog.log('USAP', WARN, "Object:get() - Received invalid response frame with startCode = %02X and CRC = %04X." % ( resp_startCode_value, resp_crc_value ))
            else:
                # Get the USAP command
                resp_code_value = resp_vData_value[3:]
                error = resp_code_value.count('?')
                if error == 0:
                    value = resp_code_value.rsplit('=', 1)[1]
                    if command.has_key(int(value)):
                        self.value = command[int(value)]
                        msglog.log('USAP', INFO, "Object:get() - Got response: %s, self.value = %s" % (str(resp_code_value), str(self.value)))
                    else:
                        msglog.log('USAP', INFO, "Object:get() - Got invalid value as: %s" % str(value))
                        raise EInvalidValue('Got invalid value as: %s' % str(value))
                else:
                    msglog.log('USAP', WARN, "Object:get() - Got ERROR response code: %s" % str(resp_code_value))
                    raise EInvalidValue('Got ERROR response code: %s' % str(resp_code_value))
    #
        return self.value

