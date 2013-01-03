"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
import time
import string
import urlparse
import Cookie
import socket
import threading
import cStringIO
from mpx.lib import msglog
from mpx.lib import httplib
from mpx.lib.thread_pool import NORMAL
from mpx.lib.scheduler import scheduler
from mpx.lib.neode.node import CompositeNode

def client_cookie(response):
    cookiesets = response.msg.getheaders('Set-Cookie')
    cookies = map(Cookie.SimpleCookie, cookiesets)
    cookiestrings = []
    for cookie in cookies:
        morsels = ["%s=%s" % (name, morsel.value) 
                   for (name, morsel) in cookie.items()]
        cookiedata = string.join(morsels, '; ')
        cookiestrings.append(cookiedata)
    cookiestring = string.join(cookiestrings, '; ')
    return cookiestring

class RequestGetter(CompositeNode):
    """
        Service that will retrieve commands that would have normally been 
        POSTed to the Mediator's web-server, and then runs those commands
        as they would have been run if POSTed directly.  The results are 
        then returned via POST on a follow-up request.
    """
    def __init__(self, *args):
        self.request_url = ''
        self.period = 15
        self.timeout = 15
        self.debug = 0
        self._host = ''
        self._request_path = ''
        self._port = 80
        self.scheduled = None
        self.polls_initiated = 0
        self.polls_completed = 0
        self._running = threading.Event()
        super(RequestGetter, self).__init__(*args)
    def configure(self, config):
        super(RequestGetter, self).configure(config)
        self.request_url = config.get('request_url', self.request_url)
        self.period = int(config.get('period', self.period))
        self.timeout = int(config.get('timeout', self.timeout))
        self.debug = int(config.get('debug', self.debug))
    def configuration(self):
        config = super(RequestGetter, self).configuration()
        config['request_url'] = self.request_url
        config['period'] = str(self.period)
        config['timeout'] = str(self.timeout)        
        config['debug'] = str(self.debug)
        return config
    def start(self):
        if self._running.isSet():
            raise Exception('Request Service already running.')
        request_url = self.request_url
        if not request_url.lower().startswith('http'):
            request_url = 'http://' + request_url
        url_tuple = urlparse.urlsplit(request_url)
        self._host = string.split(url_tuple[1],':')[0]
        if ':' in url_tuple[1]:
            self._port = int(string.split(url_tuple[1],':')[1])
        else: self._port = 80
        self._request_path = urlparse.urlunsplit(('','') + url_tuple[2:])
        
        protocol = url_tuple[0].lower()
        if protocol == 'https':
            self._connection_factory = httplib.HTTPSConnection
        elif protocol == 'http':
            self._connection_factory = httplib.HTTPConnection
        else:
            raise Exception('Protocol %s not supported.' % protocol)
        self._running.set()
        self.polls_initiated = 0
        self.polls_completed = 0
        self.schedule_polling()
        return super(RequestGetter, self).start()
    def stop(self):
        if self.scheduled:
            self.scheduled.cancel()
        self.scheduled = None
        self._running.clear()
        return super(RequestGetter, self).stop()
    def schedule_polling(self):
        if self.scheduled and not self.scheduled.cancelled():
            raise TypeError("attempting to schedule multiple poll sessions")
        self.scheduled = scheduler.every(self.period, self.initiate_poll)
    def initiate_poll(self):
        if self.polls_initiated > self.polls_completed:
            msglog.log("broadway", msglog.types.WARN, 
                       "Request Service skipping poll "
                       "because previous poll still processing")
            return
        self.polls_initiated += 1
        NORMAL.queue_noresult(self.poll_server)
    def poll_server(self):
        self.debug_message('initiating poll')
        try: 
            self._request_data()
        except: 
            msglog.exception(prefix="handled")
        self.polls_completed += 1
    def _request_data(self):
        self.debug_message(
            'GET %s from %s:%s' % (self._request_path, self._host, self._port))
        connection = self._connection_factory(self._host, self._port, 
                                              timeout=self.timeout)
        try: 
            self._conversate(connection)
        finally:
            connection.close()
    def _conversate(self, connection):
        connection.request('GET', self._request_path)
        response = connection.getresponse()
        requestdata = response.read()
        while requestdata:
            if not self._running.isSet():
                error = 'Request Service not running.  Exiting conversation'
                raise Exception(error)
            self.debug_message(
                'response code %s.  Data included.' % (response.status))
            if response.status >= 400:
                error = '%s request returned error code %s, reason "%s"'
                error = error % (self.name, response.status, response.reason)
                msglog.log('broadway', msglog.types.ERR, error)
                raise TypeError(error)
            elif not (requestdata.startswith('GET') or 
                      requestdata.startswith('POST')):
                error = 'Request service retrieved invalid command: %s'
                raise TypeError(error % requestdata)
            else:
                result = self._forward_request(requestdata).read()
                headers = {'Cookie': client_cookie(response)}
                self.debug_message('POSTing: ' + result)
                connection.request('POST', self._request_path, result, headers)
                response = connection.getresponse()
                requestdata = response.read()
        self.debug_message('response code %s' % response.status)
    def _forward_request(self, requestdata):
        connection = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        connection.connect(('localhost', 80))
        while requestdata:
            requestdata = requestdata[connection.send(requestdata):]
        bytesread = -1
        sioresponse = cStringIO.StringIO()
        while (bytesread < sioresponse.tell()):
            bytesread = sioresponse.tell()
            sioresponse.write(connection.recv(1024))
        else:
            sioresponse.seek(0)
        connection.close()
        return sioresponse
    def debug_message(self, dbmessage):
        if self.debug: 
            message = 'Request Service: %s' % dbmessage
            msglog.log('broadway',msglog.types.DB, message)
