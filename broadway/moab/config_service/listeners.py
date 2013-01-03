"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import sys
import time
import string
import struct
import os
import socket
import random
import thread
import SocketServer
import xmlrpclib
import BaseHTTPServer

from _config_service import ConfigurationService, ConfigServiceRequest
from _config_service import ConfigServiceResponse, configuration_service

debug = 0

##
# Interface IConfigServiceListener defines how ourside services
# communicate with the configuration service
class IConfigServiceListener:
    def __init__(self):
        if debug:
            print ('Starting ConfigurationService listener: %s' %
                   self.__class__)
        return
    ##
    # Send the request and get a response
    # @param request a ConfigServiceRequest object
    # @returns a ConfigServiceResponse object
    # @throws Exception on any error
    #
    def send_request(self, request):
        pass

##
# Implementation of IConfigService to listen for TCP requests
#
class ConfigServiceListenerXMLRPC(IConfigServiceListener):
    def __init__(self, port=81):
        IConfigServiceListener.__init__(self)
        self.port = port
        server = SocketServer.TCPServer(('', self.port),
                                        ConfigServiceListenerXMLRPC_Handler)
        if debug:
            print 'ConfigServiceListenerXMLRPC listening on port: %d' % port
        # Start the server listener in seperate thread
        thread.start_new_thread(server.serve_forever, ())
        return

class ConfigServiceListenerXMLRPC_Handler(
    BaseHTTPServer.BaseHTTPRequestHandler):
    ##
    #
    def log_message(self, format, *args):
        pass    
    ##
    #
    def do_POST(self):
        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            params, method = xmlrpclib.loads(data)
            if debug:
                print "method:", repr(method)
                print "params:", repr(params)
            # generate response
            try:
                response = self.call(method, params)
                if debug:
                    print 'call response: %r' % response
                if type(response) != type(()):
                    response = (response,)
            except:
                # report exception back to server
                response = xmlrpclib.dumps(
                    xmlrpclib.Fault(1, "%s:%s" % (sys.exc_type,
                                                  sys.exc_value)))
            else:
                response = xmlrpclib.dumps(response,
                                           methodresponse=1)
        except Exception, e:
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            # shut down the connection (from Skip Montanaro)
            self.wfile.flush()
            self.connection.shutdown(1)
        return
    ##
    #
    def call(self, method, params):
        # override this method to implement RPC methods
        if params == ():
            params = ('OK')
        if debug:
            print "ConfigServiceTCP", method, params
        
        request = method
        user = params[1]
        password = user.split('/')[1]
        user = user.split('/')[0]
        data = ''
        if len(params) > 2:
            data = params[2].split('\n')
        request = ConfigServiceRequest(method, user, password, data,
                                       configuration_service.get_target(), 0)
        if debug:
            print 'ConfigServiceListenerXMLRPC Processing request'
        response = configuration_service.process_request(request)
        return response.get_response()

# Arbitrary group
igmp_port = 5160
igmp_rport = 5161

# Try to pick an uncommon group, 234,M,P,X
igmp_group = '234.77.80.88'

## Implementation of IConfigService to listen for IGMP (multi-cast)
#
class ConfigServiceListenerIGMP(IConfigServiceListener):
    def __init__(self):
        IConfigServiceListener.__init__(self)

        # Prepare the mreq structure taking byte order into account
        self.group = struct.unpack('!l', socket.inet_aton(igmp_group))[0]
        self.ifaddr = socket.INADDR_ANY
        self.mreq = struct.pack('!ll', self.group, self.ifaddr)        

        # Open the socket and bind it to our particular port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((igmp_group, igmp_port))        
        self._join_group()

        thread.start_new_thread(self._start_listening, ())        
        return
    ##
    # Listen for multicast requests.  If this request is a directed request
    # then only process if it is directed to us.  Otherwise, pass through to
    # configuration service and return results
    #
    def _start_listening(self):
        while 1:
            try:
                data, sender = self.sock.recvfrom(1500)
    
                ## parse commands into required tokens
                request = self._parse_request(data)                    
                
                ## Should this command be processed?
                process_flag = 0
                if debug:
                    print 'Request: %s  Target: %s' % (request.get_command(),
                                                       request.get_target())

                if request.get_target():   # is directed
                    if (request.get_target() ==
                        configuration_service.get_target()):
                        process_flag = 1
                else:
                    process_flag = 1

                if process_flag:
                    if debug:
                        print 'ConfigServiceListenerIGMP Processing request'
                    response = configuration_service.process_request(request)
                    result = None
                    if response.is_error():
                        result = response.get_message()
                    else:
                        result = response.get_response()
                    if result != None:
                        self.sock.sendto(result, (igmp_group, igmp_rport))
                if debug:
                    print 'Done  ..'    
            except Exception, e:
                self.sock.sendto(str(e), (igmp_group, igmp_rport))   
                if debug:
                    print ('Error while reading from mulitcast socket: %s' %
                           str(e))
        return
    ##
    # Join the muliticast group.  If an error occurres while joining
    #  then wait and try again.  Wait forever, until a successful join.
    def _join_group(self):
        # Add ourselves to the group
        while 1:
            try:
                self.sock.setsockopt(socket.IPPROTO_IP,
                                     socket.IP_ADD_MEMBERSHIP, self.mreq)
                if debug:
                    print 'Joined Group!'                   
                break
            except:
                if debug:
                    print 'Could not join group ... will try again...'
                time.sleep(5)
        return
    ##
    # Handle the parsing of the incomming request.  Break up command
    # into command, data, user and password and identification
    #  
    # BASIC FORMAT is:
    # COMMAND\n
    # IDENTIFICATION\n (what box is this for)
    # USER/PASSWORD\n
    # COMMAND DATA (data assocated with command)
    #
    # Configure
    # 00:80:e4:00:00:4e   
    # mpxadmin/e922bb6dea48cfe0614be1426021c2c9
    #
    #
    # [host]
    # gateway = 0.0.0.0
    # domain_name = envenergy.com
    # proxyserver = 
    # ...
    def _parse_request(self, data):
        commands = string.split(data, '\n')
        command = commands[0]
        target = None
        command_data = None
        user = None
        p = None
        key = None
        if len(commands) > 1:
            target = commands[1]
            command_data = commands[2:]
            if command_data > 0:
                d = command_data[0]
                try:
                    usr = command_data[0].split('/')
                    if len(usr) == 2:
                        user = usr[0]
                        p = usr[1]
                    command_data = command_data[1:]  # strip off usr/pass
                except:
                    print 'Could not get user and password'
        if not command:
            raise Exception('Invalid command requested')        
        return ConfigServiceRequest(command, user, p, command_data,
                                    target, key)
