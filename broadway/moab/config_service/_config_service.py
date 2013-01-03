"""
Copyright (C) 2002 2003 2006 2010 2011 Cisco Systems

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

# Mediator Configuration Service 

import os
import random
import socket
import string
import struct
import sys
import time
import thread
from mpx import properties
from md5 import new as _MD5

from fcntl import ioctl
from socket import *
from struct import pack, unpack

##
# Local copy of moab.lib.linux.zoneinfo
# @fixme Need more elegant way to bundle shared files...
from zoneinfo import get_time, set_time

##
# Local copy of mpx.lib.ifconfig
# @fixme mpx.lib.ifconfig should use a moab equivalent and so should we...
import ifconfig

##
# Local copy of moab.lib.linux.process
# @fixme Need more elegant way to bundle shared files...
import process

##
# Local copy of moab.user.manager
# @fixme Need more elegant way to bundle shared files...
import manager

debug = 0

## Communication is down through this FIFO socket
NAMED_PIPE='/tmp/fifo_config'

## The file that contains all the configuration information
configfile = properties.MPXINIT_CONF_FILE

class ConfigurationService:    
    def __init__(self):
        if debug:
            print 'Staring Configuration Service'
        # Extract a couple of relevant running values so the config tool
        # can connect.
        self.hwaddr = _get_hwaddr('mac0')
        self.serial = _get_serial()
        self.ipaddr = _get_ipaddr('eth0')
        self.hwmodel = _get_hardward_model()
        self.hostname = _get_hostname()
        # Create a security key that must accompany each request
        self.security_key = random.randint(1000,9999)
        return
    ##
    # @return the target identifier for this Mediator
    def get_target(self):
        return self.hwaddr
    ##
    # Listen for the next configuration request
    # @param request A ConfigServiceRequest that identifies
    #                the request
    # @return ConfigServiceResponse that holds the results of request
    #
    def process_request(self, request):
        oresult = ConfigServiceResponse()
        if debug:
            print ('Command: %s received from %s' %
                   (request.get_command(), request.get_target()))
            print 'Data (%s): %s' % (type(request.get_data()),
                                     request.get_data())
        try:
            result = None
            if request.get_command() == 'Hello': 
                result = self.do_hello()
            elif request.get_command() == 'Status':
                result = self.do_status()
            else:
                # All of these commands are secure
                # and will require a valid username/password
                raise Exception('Service not available')
            if debug:
                print 'Result: %s' % result
            oresult.set_response(result)
            oresult.set_error(0)
        except Exception, e:
            raise Exception('ConfigurationService error: ' + str(e))
        return oresult
    ##
    # Read next command from NAMED PIPE and place 
    # in a ConfigServerRequest object
    # @returns ConfigServiceRequest
    # @throws Exception on parse error
    #
    def _get_request(self):
        f = None
        try:
            try:
                f = open(NAMED_PIPE,'r')
                d = f.read()
                return ConfigServiceRequest(d)
                
            except Exception, e:
                raise Exception('Error while reading command from PIPE: ' +
                                str(e))
        finally:
            if f:
                f.close()      
        return
    ##
    # Validate the user and password from the Uxix password database
    # @param u User name
    # @param p Password
    # @throws Exception if not match or no entry for user
    def _validate_request(self, request):
        u = request.get_user()
        p = request.get_password()
        # @fixme Is the request security key used?  I've seen
        #        0 and None as values...
        security_key = request.get_security_key()
        passwd = manager.PasswdFile()
        passwd.load()
        if u in passwd:
            entry = passwd[u]
            if len(p) == 32:
                # This could be a Config Service Secure Key.
                metadata = entry.gecos()
                for key_value in metadata.split(','):
                    result = key_value.split('=')
                    if len(result) == 2:
                        key,value = result
                        if key == "CSIK":
                            security_token = _MD5(value)
                            security_token.update(str(self.security_key))
                            security_token = security_token.hexdigest()
                            if p == security_token:
                                # We have a match!
                                return
            # Try a plain-text password.
            if entry.password_matches_crypt(p):
                return
        raise Exception('Could not validate user')
        
    ## Need generic property file reader!!!
    def _get_proxy_server(self):
        file = '/etc/mpxinit.conf'
        try:
            try:
                f=open(file)
                props = f.read()
                
                lines = props.split('\n')
                for line in lines:
                    if not line or len(line) == 0 or line[0] == '#':
                        continue
                    prop = line.split('=',1)
                    if(len(prop) == 2):
                        if prop[0] == 'proxyserver':
                            return prop[1]
                        
                    else:
                        pass
            except:
                ## print 'Could not load properties file: %s' % file
                pass
                    
        finally:
            if f != None:
                f.close()
                                                     
    def do_status(self):
        status = process.status_from_name('broadway').state
        
        if status == 'EXISTS':
            status = 'OK'
        elif status == 'DOESNOTEXIST':
            status = 'Application not running'
        else:
            status = 'Offline: ' + status
            
        return status
           
    ##
    # Do the hello command.  This will gather needed information about this MPX
    # and send it to the caller in a single response.
    #
    def do_hello(self):
            
        msg = 'config_service_port=81\n'
                
        # The random number needed for secure transfer
        msg += 'rident=%d\n' % self.security_key
        
        # The MPX Model type      
        msg += 'model = %s\n' % self.hwmodel          
        
        # MAC address
        msg += 'hwaddr = %s\n' % self.hwaddr
    
        # Serial number
        msg += 'serial = %s\n' % self.serial
    
        # IP addr
        msg += 'ip_default = %s\n' % self.ipaddr
        
        # Hostname
        msg += 'hostname = %s\n' % self.hostname
    
        # Time
        msg += 'time = %s\n' % time.strftime('%m/%m/%y %H:%M:%S') 
    
        # Broadway version
        try:
            fd = open('/usr/lib/broadway/BROADWAY')
            msg += 'broadway = %s\n' % string.strip(fd.readline())
            fd.close()
        except:
            msg += 'broadway = not installed\n'
        
        # Image version
        try:
            fd = open('/etc/motd')
            sysimage = fd.read()
            fd.close()
            n = string.find(sysimage, 'Environment')
            m = string.find(sysimage, '\x1b', n)
            sysimage = string.split(sysimage[n:m])[1]
            msg += 'image = %s\n' % sysimage
        except:
            msg += 'image = unknown\n'
    
        # End of header
        msg += '\n'
    
        # Config file content
        if os.path.exists(configfile):
            fd = open(configfile)
            data = fd.read()
            fd.close()
            msg += data
        
        return msg

##
# Get the MAC address for a network interface
# Read this information from the proc filesystem
# @param interface The name of the interface to read
# @return The address of the request interface
# @throw Exception on any error
# @fixme Use moab/ifconfig combo...
def _get_hwaddr(interface):
    file = '/proc/mediator/%s' % interface
    if os.path.isfile(file) and os.access(file, os.R_OK):
        # Mediator specific lookup.
        return _read_from_proc('mediator/%s' % interface)
    else:
        try:
            return ifconfig.mac_address(interface)
        except:
            try:
                # try eth0 or eth1 instead of mac0 or mac1
                return ifconfig.mac_address('eth' + interface[-1])  
            except:
                 return 'Unknown'

##
# Return the IP address for an interface.
# @param interface A string representing the name of the interface.
# @value all 0.0.0.0
# @value lo The loopback device.
# @value eth0-eth255 An ethernet adapter.
# @value ppp0-ppp255 A PPP connection.
# @return A string representation of the interface's IP address.
# @fixme Use moab/ifconfig combo...
def _get_ipaddr(interface):
    try:
        return ifconfig.ip_address(interface)
    except:
        return '0.0.0.0'

##
# @return Then model currently in use.
# @note The model is determined by checking for the
# existence of a file in /tmp.  If the file .s1 exists, 
# then check for .s2, then check for .s3
# @fixme Use/move to moab/ifconfig combo...
def _get_hardward_model():
    file = '/proc/mediator/model'
    try:
        if os.path.isfile(file) and os.access(file, os.R_OK):
            return _read_from_proc('mediator/model')
        else:
            return properties.HARDWARE_MODEL
    except:
        # @fixme Check out the mac address before giving up?
        return 'Unknown'

##
# @return The current host name.
# @fixme H/W specific, belongs in moab.linux.xxx
def _get_hostname():
    try:
        return _read_from_proc('sys/kernel/hostname')
    except:
        # Default to the classic name
        return 'mediator'

##
# @return The serial number.
# @fixme H/W specific, belongs in moab.linux.xxx
def _get_serial():
     file = '/proc/mediator/serial'
     try:
        if os.path.isfile(file) and os.access(file, os.R_OK):
            return _read_from_proc('mediator/serial')
        else:
            return properties.SERIAL_NUMBER
     except:
        # Compatibility with older proc file system.
        return 'Unknown'

##
# @fixme H/W specific, belongs in moab.linux.xxx
def _read_from_proc(s):
    f = open('/proc/%s' % s ,'r')
    try:
        return f.read().rstrip()  ## remove new line
    finally:
        if f: f.close()


##
# Class to encapsulate a single configuration service request
#  All communication is done via this class and the ConfigServiceResponse
#
class ConfigServiceRequest:
    def __init__(self, command, user, p, command_data, target, key):
        self.curr_command = command
        self.curr_user = user
        self.curr_pass = p
        self.curr_command_data = command_data
        self.curr_target = target
        self.curr_key = key
        return
    ##
    # @return the Name of the configuration command
    def get_command(self):
        return self.curr_command
    ##
    # @return The user who invoked this command
    def get_user(self):
        return self.curr_user
    ##
    # @return
    def get_password(self):
        return self.curr_pass
    ##
    # @return the data associated with this command
    def get_data(self):
        return self.curr_command_data
    ##
    # @return the table machine for this request
    def get_target(self):
        return self.curr_target
    ##
    #
    def get_security_key(self):
        return self.curr_key

## Class to encapsulate a single configuration service response
class ConfigServiceResponse:        
    def __init__(self):
        self.response = None
        self.message = None
        self.error_flag = 1
        return

    def set_response(self, d):
        self.response = d
        return
    def get_response(self):
        return self.response
    
    def get_message(self):
        return self.message

    def set_error(self, e):
        self.error_flag = e
        return

    def get_error(self):
        return self.error_flag
    
    def is_error(self):
        return self.error_flag == 1

## Create singleton
configuration_service = ConfigurationService()
