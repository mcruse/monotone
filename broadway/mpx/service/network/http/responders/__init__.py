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
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.service.network.http import producers
from mpx.service.network.http.responders import status

class undefined(object):
    def __str__(self):
        return "%s()" % type(self).__name__
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))
    def __eq__(self, other):
        return isinstance(other, type(self))
    def __nonzero__(self):
        return False

Undefind = undefined()

def createheader(item):
    return '%s: %s' % item

class Responder(CompositeNode):
    def isumbrella(self):
        """
            Return True if the handler should be added to the 
            back of the handler list; otherwise return False.
            
            Handlers are added to the back of the list when 
            they are umbrella handlers.  They respond to a 
            wide range of requests.
        """
        return False
    def match(self, code):
        """
            Returns True is responder handles responses of
            return code 'code'.
        """
        raise TypeError("match() must be overridden")
    def handle_response(self, request):
        """
            Generate response producer using information 
            associated with Request instance 'request.'
        """
        request.out = self.create_response(request)
        request.response_handled()
    def create_response(self, request):
        """
            Generate response producer using information 
            associated with Request instance 'request.'
        """
        raise TypeError("create_response() must be overridden")

class RequestResponder(Responder):
    """
        Generic Responder type which provides catch all 
        response generation functionality equivalent to 
        what was previously provided by the Request class.
    """
    def isumbrella(self):
        return True
    def match(self, code):
        return True
    def build_header(self, request):
        headers = ['%s: %s' % item for item in 
                   request.response_headers.items()]
        cookies  = [cookie.output() for cookie in request.response_cookies]
        headers.extend(cookies)
        return "\r\n".join([request._response(request.reply_code)] + headers)
    def create_response(self, request):
        connection = request.get_header('connection')
        if connection:
            connection = connection.lower()
        if not request.has_key("Content-Length"):
            if request.response_length is not None:
                request['Content-Length'] = request.response_length
        close_it = 0
        wrap_in_chunking = 0
        if request._version == '1.0':
            if connection == 'keep-alive':
                if not request.has_key('Content-Length'):
                    close_it = 1
                else:
                    request['Connection'] = 'Keep-Alive'
            else:
                close_it = 1
        elif request._version == '1.1':
            if connection == 'close':
                close_it = 1
            elif not request.has_key('Content-Length'):
                if request.has_key('Transfer-Encoding'):
                    if not request['Transfer-Encoding'] == 'chunked':
                        close_it = 1
                elif request.use_chunked:
                    request['Transfer-Encoding'] = 'chunked'
                    wrap_in_chunking = 1
                else:
                    close_it = 1
        elif request._version is None:
            ##
            # Sometimes developers do not type a version when debugging
            # a server from telnet.  This is to support such requests.
            close_it = 1
        if close_it:
            request['Connection'] = 'close'
        header = self.build_header(request)
        header_producer = producers.SimpleProducer(header + "\r\n\r\n")
        body_producer = request.outgoing_producers
        request.outgoing_producers = None
        body_producer = producers.CompositeProducer(body_producer)
        if wrap_in_chunking:    
            body_producer = producers.ChunkedProducer(body_producer)
        outgoing_fifo = asynchat.fifo([header_producer, body_producer])
        outgoing = producers.CompositeProducer(outgoing_fifo)
        outgoing = producers.HookedProducer(outgoing, request.log)
        outgoing = producers.GlobbingProducer(outgoing)
        if close_it:
            request._channel.close_when_done()
        return outgoing
