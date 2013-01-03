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
import xml.sax
import urllib
from mpx.service import ServiceNode
from mpx.lib.node import as_node,as_node_url
from mpx.lib import pause, msglog, threading
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node.browser import _holistic_conversion
from mpx.lib.configure import as_boolean
commands = []

def _holistic_conversion(value):
    try:
        return int(value)
    except:
        pass
    try:
        return float(value)
    except:
        pass    
    return value


class ContentHandler(xml.sax.ContentHandler):
    def __init__(self, debug=0):
        self.debug = debug
        xml.sax.ContentHandler.__init__(self)

    def startDocument(self):
        global commands
        if self.debug:
            print "Processing command list"
        commands = []

    def startElement(self, name, attrs):
        if name == 'Command':
            if self.debug:
                print 'Processing command'
            self.point = None
            self.value = None
            self.sequence = None
            self.variant = ''
        self.state = name
        if self.debug:
            print 'State = ' + name

    def endElement(self, name):
        global commands
        if name == 'Command':
            commands.append([self.point, self.value, self.sequence, self.variant])

    def characters(self, content):
        if self.state == 'PointID':
            self.point = str(content)
        elif self.state == 'Param1':
            self.value = float(content)
        elif self.state == 'Param2':
            if self.debug:
                print "Param2 = " + content
        elif self.state == 'SeqNum':
            self.sequence = str(content)
        elif self.state == 'varParam':
            self.variant = str(content)
        elif self.state == 'Error':
            msglog.log('sie', msglog.types.ERR, str(content))

class CommandService(ServiceNode):
    def __init__(self):
        self._running = 0
        ServiceNode.__init__(self)
    def configure(self, config):
        ServiceNode.configure(self, config)
        set_attribute(self, 'server_url', REQUIRED, config)
        set_attribute(self, 'node', REQUIRED, config)
        set_attribute(self, 'period', 30, config, int)
        set_attribute(self,'connection','/services/network',config,as_node)
        set_attribute(self,'timeout',60,config,int)
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self, 'server_url', config)
        get_attribute(self, 'node', config)
        get_attribute(self, 'period', config, str)
        get_attribute(self,'connection',config,as_node_url)
        get_attribute(self,'timeout',config,str)
        return config
    def start(self):
        if not self._running:
            t = threading.Thread(target=self._run,args=())
            self._running = 1
            t.start()
    def stop(self):
        if self._running:
            self._running = 0
            # more stop stuff.
    def _run(self):
        global commands
        x = xml.sax.make_parser()
        x.setContentHandler(ContentHandler(self.debug))
        
        while self._running:
            # all in try statement/catch-all so that
            #  service continues to run indefinately.
            try:
                if self.connection.acquire(self.timeout):
                    try:
                        server_url = self.server_url
                        command_url = server_url + 'get?nodeid=' + self.node
                        if self.debug:
                            print "Executing %s" % command_url
                        x.parse(command_url)
                        for c in commands:
                            if self.debug:
                                print "Setting %s to %f with seq %s" % (c[0], c[1], c[2])
                            try:
                                node = as_node(c[0])
                                node.set(_holistic_conversion(c[1]))
                            except(KeyError):
                                msglog.log('sie', msglog.types.ERR, 'Point %s does not exist.' % c[0])
                            
                            if self.debug:
                                print "Acknowledging setting point %s to %d with sequence %s" % \
                                      (c[0], c[1], c[2])
                            encoded_name = urllib.quote_plus(c[0])
                            encoded_param = urllib.quote_plus(c[3])
                            ack_url = server_url + 'ack?PointID=%s&SeqNum=%s&varParam=%s' % \
                                      (encoded_name, c[2], encoded_param)
                            if self.debug:
                                print "Acknowledging with %s" % ack_url
                            # uses the parser's ability to retrieve url content
                            #  so we dont have to put http logic here.
                            x.parse(ack_url)
                    finally:
                        self.connection.release()
            except:
                msglog.exception()
            pause(self.period)

def factory():
    return CommandService()
