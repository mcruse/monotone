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
from mpx.lib import xmlrpclib
from mpx.lib import msglog

from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.threading import Lock

from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response

from mpx.lib.exceptions import MpxException
from mpx.lib.exceptions import EProtocol

import sys
import string
import re
import traceback

class BrivoDispatcher(RequestHandler):
    def __init__(self):
        self.observers = {}
        self.data = None
        self.running = False
        self._ob_lock = Lock()
        super(BrivoDispatcher, self).__init__()
        return
        
    def configure(self, cd):
        set_attribute(self, 'request_path', '/brivo', cd)
        set_attribute(self, 'debug', 0, cd)
        super(BrivoDispatcher, self).configure(cd)
        return

    def configuration(self):
        cd = super(BrivoDispatcher, self).configuration()
        get_attribute(self, 'request_path', cd)
        return config

    def start(self):
        self.running = True
        super(BrivoDispatcher, self).start()
        return

    def stop(self):
        self.observers = {}
        self.running = False
        super(BrivoDispatcher, self).stop()
        return

    def listens_for(self):
        return [self.request_path]

    def match(self, path):
        p = '^%s$' % self.request_path
        if re.search(p,path):
            return 1
        return 0

    def handle_request(self, request):
        print 'handle_request'
        if not self.running:
            return request.error(503) #service unavailable
        try:
            self.data = data = request.get_data().read_all()
            if not data:
                raise EProtocol('could not get DATA parameter from posted data')
            ## process xmlrpc, getting the name of the method
            ## and parameters
            params, method = xmlrpclib.loads(data)
            return

            object_alias = ''
            method_name = ''
            ## get the name of the object
            ## and the name of method
            ## They are delimited by a colon.

        except:
            msglog.exception()
            raise MpxException('Error occurred while processing Brivo XMLRPC command')
        # XML-RPC Call was successful.
        # Send back the XML result to client
        reply = Response(request)
        reply.set_header('Content-Length', len(response))
        reply.set_header('Content-Type', 'text/xml')
        reply.send(response)
        return
            
    def register(self, observer, device_id):
        self._ob_lock.acquire()
        try:
            ob_list = self.observers.get(device_id)
            if ob_list is not None:
                if not ob_list.count(observer):
                    # observer does not yet exist, add it
                    ob_list.append(observer)
            else:
                self.observers[device_id] = [observer]
        finally:
            self._ob_lock.release()
            
    def unregister(self, observer, device_id):
        self._ob_lock.acquire()
        try:
            ob_list = self.observer.get(device_id)
            if ob_list is not None: 
                # should always exist
                ob_list.remove(observer)
        finally:
            self._ob_lock.release()
        
    ##
    # distribute event to registered observers
    def distribute(self, evt):
        obs = self.observers.get(evt.get('device_id'))
        if obs:
            for ob in obs:
                ob.update(evt)
        return
