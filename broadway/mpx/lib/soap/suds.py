"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
import httplib
import xml.dom
import socket
import mimetools
import struct
import select

from mpx.lib.exceptions import ETimeout, EInvalidValue
from mpx.lib.exceptions import *

domI = xml.dom.getDOMImplementation()
dom = xml.dom.minidom
debug = 0 #1 basic printouts, 2 tracing connection, 3 tcp dump
max_wait_time = 30

from mpx.lib.threading import currentThread as _currentThread
class _HTTPResponse(httplib.HTTPResponse):
    def begin(self):
        if self.msg is not None:
            # we've already started reading the response
            return
        if debug: print 'begin:',
        while 1:
            if debug: print '1',
            r,w,exc = select.select([self.fp.fileno()],[],[],max_wait_time)
            if len(r) == 0: #timeout
                if debug: print 'select timeout'
                self.close()
                raise ETimeout(self)
            line = self.fp.readline()
            if debug: print '+',
            if self.debuglevel > 0:
                if debug: print "reply:", repr(line)
            try:
                [version, status, reason] = line.split(None, 2)
            except ValueError:
                if debug: print '-',
                try:
                    [version, status] = line.split(None, 1)
                    reason = ""
                except ValueError:
                    if debug: print 'x',
                    version = "HTTP/0.9"
                    status = "200"
                    reason = ""
            if version[:5] != 'HTTP/':
                if debug: print 'bad status line'
                self.close()
                raise BadStatusLine(line)

            # The status code is a three-digit number
            try:
                self.status = status = int(status)
                if status < 100 or status > 999:
                    raise BadStatusLine(line)
            except ValueError:
                raise BadStatusLine(line)
            if status != 100:
                if debug: print '2',
                break

            # Skip the rest of the "Continue" headers.
            while line:
                if debug: print '3',
                r,w,exc = select.select([self.fp.fileno()],[],[],max_wait_time)
                if len(r) == 0: #timeout
                    if debug: print 'select timeout'
                    self.close()
                    raise ETimeout(self)
                line = self.fp.readline().strip()
        if debug: print '5',
        self.reason = reason.strip()

        if version == 'HTTP/1.0':
            self.version = 10
        elif version.startswith('HTTP/1.'):
            self.version = 11   # use HTTP/1.1 code for HTTP/1.x where x>=1
        elif version == 'HTTP/0.9':
            self.version = 9
        else:
            raise UnknownProtocol(version)
        if debug: print '6',
        if self.version == 9:
            self.msg = mimetools.Message(StringIO())
            return
        if debug: print '7',
        self.msg = mimetools.Message(self.fp, 0)
        if self.debuglevel > 0:
            for hdr in self.msg.headers:
                if debug: print "header:", hdr,

        # don't let the msg keep an fp
        self.msg.fp = None

        # are we using the chunked-style of transfer encoding?
        tr_enc = self.msg.getheader('transfer-encoding')
        if tr_enc:
            if tr_enc.lower() != 'chunked':
                raise UnknownTransferEncoding()
            self.chunked = 1
            self.chunk_left = None
        else:
            self.chunked = 0

        # will the connection close at the end of the response?
        conn = self.msg.getheader('connection')
        if conn:
            if debug: print '8',
            conn = conn.lower()
            # a "Connection: close" will always close the connection. if we
            # don't see that and this is not HTTP/1.1, then the connection will
            # close unless we see a Keep-Alive header.
            self.will_close = conn.find('close') != -1 or \
                              ( self.version != 11 and \
                                not self.msg.getheader('keep-alive') )
        else:
            if debug: print '9',
            # for HTTP/1.1, the connection will always remain open
            # otherwise, it will remain open IFF we see a Keep-Alive header
            self.will_close = self.version != 11 and \
                              not self.msg.getheader('keep-alive')

        # do we have a Content-Length?
        # NOTE: RFC 2616, S4.4, #3 says we ignore this if tr_enc is "chunked"
        length = self.msg.getheader('content-length')
        if length and not self.chunked:
            try:
                self.length = int(length)
            except ValueError:
                self.length = None
        else:
            self.length = None

        # does the body have a fixed length? (of zero)
        if (status == 204 or            # No Content
            status == 304 or            # Not Modified
            100 <= status < 200):       # 1xx codes
            self.length = 0

        # if the connection remains open, and we aren't using chunked, and
        # a content-length was not provided, then assume that the connection
        # WILL close.
        if not self.will_close and \
           not self.chunked and \
           self.length is None:
            if debug: print 'A',
            self.will_close = 1
        if debug: print 'B',

class _HTTPConnection(httplib.HTTPConnection):
    response_class = _HTTPResponse
    _total_continuations = 0
    def __init__(self, *args, **kw):
        httplib.HTTPConnection.__init__(self, *args, **kw)
        self._tq = []
        return
    def _trace(self, msg):
        if debug:
            if len(self._tq) > 500:
                self._tq = self._tq[-400:]
            self._tq.append({'thread':_currentThread(),'msg':msg})
        return
    def connect(self):
        httplib.HTTPConnection.connect(self)
        linger = struct.pack("ii", 1, 0) # prevent skt from jabbering with empty pkts after closure
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)

    # Scary HACK to trace what's up...
    def getresponse(self):
        "Get the response from the server."

        # check if a prior response has been completed
        if self._HTTPConnection__response and self._HTTPConnection__response.isclosed():
            self._HTTPConnection__response = None

        #
        # if a prior response exists, then it must be completed (otherwise, we
        # cannot read this response's header to determine the connection-close
        # behavior)
        #
        # note: if a prior response existed, but was connection-close, then the
        # socket and response were made independent of this HTTPConnection
        # object since a new request requires that we open a whole new
        # connection
        #
        # this means the prior response had one of two states:
        #   1) will_close: this connection was reset and the prior socket and
        #                  response operate independently
        #   2) persistent: the response was retained and we await its
        #                  isclosed() status to become true.
        #
        if self._HTTPConnection__state != httplib._CS_REQ_SENT or self._HTTPConnection__response:
            raise ResponseNotReady()
        self._trace('pre-self.response_class()')
        if self.debuglevel > 0:
            response = self.response_class(self.sock, self.debuglevel)
        else:
            response = self.response_class(self.sock)
        self._trace('post-self.response_class()')
        self._trace({'response=': response})
        self._trace('pre: response.begin()')
        response.begin()
        if debug: print ' end-begin'
        self._trace('post: response.begin()')
        self._HTTPConnection__state = httplib._CS_IDLE

        if response.will_close:
            # this effectively passes the connection to the response
            self._trace('pre-self.close()')
            self.close()
            self._trace('post-self.close()')
        else:
            # remember this, so we can tell when it is complete
            self._HTTPConnection__response = response

        return response

#_module_lock = Lock()
##
# host = URL of host sans http://
# post = host relative URL of soap server document
# action = full URL of SOAPAction 
# request = xml encoded soap request
def send_request(host, post, action, soap_request, conn=None):
    header = {'SOAPAction':action,
              'Content-Type':'text/xml; charset=utf-8'}
    i = host.find('http://')
    if i >= 0:
        host = host[i+7:] #remove leading http if present
    if host[-1] == '/':
        host = host[:-1]
    if post[0] != '/': #make sure post starts with /
        post = '/' + post
    if post[-1] == '/':
        post = post[:-1]
    #if debug: print host, post, action, soap_request
    close_conn = 0
    if conn is None:
        conn = _HTTPConnection(host)
        close_conn = 1
    conn._trace('instantiated')
    conn._continuations = 0
    if conn is None:
        if debug: print 'host not found'
        raise ETimeout('host not found', (host, post, action, soap_request))
    try:
        if debug > 2: conn.set_debuglevel(1)
        conn._trace('pre-request')
        conn.request('POST', post, soap_request, header)
        conn._trace('post-request')
        while 1:
            conn._trace('pre-getresponse')
            r = conn.getresponse()
            if debug: print r.status, r.reason
            conn._trace('post-getresponse')
            if r.status != 100:
                break
            _HTTPConnection._total_continuations += 1
            conn._continuations += 1
            # 2000-12-30 djf -- drop bogus 100 response
            # by kludging httplib
            conn._HTTPConnection__state = httplib._CS_REQ_SENT
            conn._HTTPConnection__response = None
        if r.status != 200:
            raise EInvalidResponse(str(r.status),'expecting OK response', (host, post, action, soap_request))
        conn._trace('pre: r.read()')
        response = r.read()
        conn._trace('post: r.read()')
        if response is None:
            raise EInvalidValue('expecting SOAP server response', (host, post, action, soap_request))
        return response
    finally:
        try:
            if close_conn:
                conn._trace('pre.close()')
                conn.close()
                conn._trace('post.close()')
            else:
                conn._trace('keep open')
        except:
            pass
        pass
_abort_list = []
##
# abort the current http request if it is taking too long
#
def _abort_request(*args):
    try:
        if debug: print 'Soap request aborted'
        conn = args[0]
        conn.close()
        global _abort_list
        _abort_list.append(args[0])
    except:
        if debug: print 'Soap error during abort close'
        pass

##
# answer a map of point values contained in the response xml
# map is keyed by point name
def parse_response(xml_string):
    if xml_string is None:
        raise EInvalidValue('must be xml string')
    ps = dom.parseString(xml_string)
    de = ps.documentElement
    elements = de.getElementsByTagName('PointData') #this produces a list of DOM elements
    points = {}
    for point in elements: #make a map of point vs their attributes and values
        point_map = {}
        for n in point.childNodes:
            value = point.getElementsByTagName(n.tagName)[0].firstChild.nodeValue
            point_map[str(n.tagName)] = str(value) # @fixme convert unicode to str
            #if debug: print str(n.tagName), str(value)
        points[point_map['Name']] = point_map
    return points
##
# build a xml request from a list of lists of lists
# each point list element contains key/value pairs such as
# ['Name','Differential Pressure 1']
# ['Type','analog']
# dictionary was not used because key order is random
def build_point_request(list): #from a list of maps build request
    answer = """
<Request>
  <DataRequest>
"""
    for point in list:
        answer = answer + """    <Request>
"""
        for pair in point:
            answer = answer + "      <" + pair[0] + '>' + pair[1] + '</' + pair[0] + """>
"""
        answer = answer + """    </Request>
"""
    return answer + """  </DataRequest>
</Request>
"""

def build_and_send_request(host, post, action_server, action, list, conn=None):
    request = build_point_request(list)
    if action_server.find('http://') < 0: #make sure action_server starts with http://
        action_server = 'http://' + action_server
    if action_server[-1] != '/':
        action_server = action_server + '/'
    envelope_start = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <""" + action + ' xmlns="' + action_server + '" >'
    envelope_end = """
        </""" + action + """>
      </soap:Body>
    </soap:Envelope>
    """
# @fixme until I know otherwise I want to make sure only one request at a time goes out
    try:
        rsp = send_request(host, post, action_server + action, envelope_start + request + envelope_end, conn)
    except Exception, e:
        if conn: conn.close()
        if debug: print 'Unhandled Soap error occured during request'
        rsp = e
        raise
    return parse_response(rsp)

