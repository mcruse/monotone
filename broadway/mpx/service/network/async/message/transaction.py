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
import asynchat
import threading
from mpx.lib import msglog
from mpx.lib.scheduler import scheduler

class Transaction(object):
    def __init__(self, request = None, timeout = None):
        self._transaction_state = None
        self._transaction_timeout = None
        self._state_lock = threading.Lock()
        self._transaction_complete = threading.Event()
        self.set_request(request)
        self.set_timeout(timeout)
    def set_request(self, request):
        if request and self.request is not None:
            raise Exception('Cannot change request.')
        self.request = request
    def set_timeout(self, timeout):
        self.timeout = timeout
    def has_request(self):
        return self.get_request() is not None
    def has_response(self):
        return self.has_request() and self.get_request().has_response()
    def get_request(self):
        return self.request
    def get_response(self, default = None):
        response = default
        if self.has_response():
            response = self.get_request().get_response()
        return response
    def build_request(self, url, data=None, headers={}, version='HTTP/1.1'):
        request = Request(url, data, headers, version)
        self.set_request(request)
        return request

