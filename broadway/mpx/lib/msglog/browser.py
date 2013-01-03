"""
Copyright (C) 2002 2003 2011 Cisco Systems

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
##
# @fixme All pages should have a simple navigation tool at the top and bottom.
#        Basically a link for each level in the path:
#        <u>/</u> <u>ion</u> / <u>port2</u> / <u>modbus</u> / <u>dg50</u> / start
import string
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute,as_boolean
from mpx.service.network.http.request_handler import RequestHandler
from mpx.lib.log import trimming_log
from _formatters import HTMLFormatter
from mpx.lib import msglog
from mpx.service.network.http.response import Cookie, Response
from mpx import properties
from mpx.lib import thread, threading
import re
import urllib
import os
import time



class _MsglogEntry:
    
    ##
    # @fixme checking to see if the child has
    # the application attribute.  Old log files 
    # didn't have the application field
    # put in in 01/14/02
    def __init__(self, entry):
        self.children = []
        self.timestamp = entry['timestamp']
        self.seqnum = entry['_seq']
        self.message = entry['message']
        self.type = entry['type']
        if entry.has_key('application'):
            self.application = entry['application']
        else:
            self.application = 'unknown'
            
    def feed(self, entries,index,increment):
        return index

    def get_children(self):
        return self.children

class _UnknownEntry(_MsglogEntry):
    pass

class _ErrorEntry(_MsglogEntry):
    def feed(self, entries,index,increment):
        if index > len(entries):
            return None
        if entries[index]['type'] == msglog.types.EXC:
            entry = entries[index]
            index += increment
            child = entry_factory(entry)
            index = child.feed(entries,index,increment)
            self.children.append(child)
        return index

class _ExceptionEntry(_MsglogEntry):
    def feed(self, entries,index,increment):
        if index > len(entries):
            return None
        type = entries[index]['type']
        if type == msglog.types.TB or type == msglog.types.PRV:
            entry = entries[index]
            index += increment
            child = entry_factory(entry)
            index = child.feed(entries,index,increment)
            self.children.append(child)
        return index

_entry_dictionary = {msglog.types.ERR: _ErrorEntry,
                     msglog.types.WARN: _MsglogEntry,
                     msglog.types.INFO: _MsglogEntry,
                     msglog.types.FATAL: _MsglogEntry,
                     msglog.types.EXC: _ExceptionEntry,
                     msglog.types.TB: _MsglogEntry,
                     msglog.types.DB: _MsglogEntry}

##
# Retrieves correct class for <code>entry<code>
# and instatiates it.
# 
# @return Object for entry.
#
def entry_factory(entry):
    if _entry_dictionary.has_key(entry['type']):
        return _entry_dictionary[entry['type']](entry)
    else:
        return _UnknownEntry(entry)

class _Handler: 
    def __init__(self,parent):      
        self.parent = parent
    
    def match(self,path):
        if re.match(self.match_path,path):
            return 1

        return 0
    def replace_tokens(self,text,tokens=None):
        if tokens is None:
            tokens = {}
        all_tokens = re.findall('\$\$\w*\$\$',text)         
        for token in all_tokens:
            token = token[2:-2]
            if tokens.has_key(token):
                text = re.sub('\$\$' + str(token) + '\$\$',str(tokens[token]),text) 
        return text
    
    
class RedirectHandler(_Handler):
    def __init__(self,parent):
        self.match_path = '^/msglog[/]?$'
        _Handler.__init__(self,parent)

    def handle(self,request):
        response = Response(request)
        html = '<html><head>'
        html += '<META http-equiv="Refresh" content="0; Url=/msglog/index.html" >'
        html += '</head><body></body></html>'        
        response.send(html)
  
class GetRecordsFileHandler(_Handler):
    def __init__(self,parent):
        self.match_path = '^/msglog/get_records.html$'
        _Handler.__init__(self,parent)
          
    def get_data(self,qd):
        _data = [] 
        msg_log = trimming_log('msglog')               
        seq_num = int(qd['seq_num'])        
        data = msg_log[seq_num + 1:]
        increment = 1
        index = 0
        end = len(data)        
        if string.lower(qd['sort_order']) == 'descending':
            increment = -1
            index = len(data)-1
            end = -1
                    
        type = 'all'
        application = 'all'
        if qd.has_key('type'):
            type = qd['type']
        if qd.has_key('application'):
            application = qd['application']
        
        while index != end:            
            if type == 'all' and application == 'all':
                _data.append(data[index])
            elif type == 'all' and application != 'all':
                if re.match(application,data[index]['application']):
                    _data.append(data[index])
            elif application == 'all' and type != 'all':
                if re.match(type,data[index]['type']):
                    _data.append(data[index])
            elif application != 'all' and type != 'all':
                if re.match(application,data[index]['application']) and re.match(type,data[index]['type']):
                    _data.append(data[index])
            index += increment
            
        return _data
        
    def handle(self,request):
        response = Response(request)
        qd = request.get_query_dictionary()
        data = self.get_data(qd)   
        request_path = urllib.unquote(string.lower(request.get_path()))
        file_path = os.path.join(self.parent.http_published_root, request_path[1:])
        if os.path.isfile(file_path):
            html = open(file_path).read()
            tokens = {}
            tokens['RECORDS'] = self.get_html(data)
            html = self.replace_tokens(html,tokens)
            response.send(html)
        else:
            response.send_error(404)
        
    
    def get_html(self,data):
        html = ''
        index = 0
        for d in data:
            html += 'records[' + str(index) + '] ='
            timestamp = time.strftime('%H:%M:%S %m/%d/%y',time.localtime(d['timestamp']))
            ts = '%.10f' % d['timestamp']
            seq = '%s' % d['_seq']
            html += 'new Record(\'' + seq  +'\',\'' + timestamp + '\','
            html += '\'' + d['application'] + '\','
            html += '\'' + d['type'] + '\','
            
            message = string.lstrip(string.replace(str(d['message']),'\n','<br>'))
            message = string.replace(message,"'",'"')
            html += '\'' + message + '\');\n'
            
            index += 1
           
        return html


class DefaultHandler(_Handler):
   
       
    def match(self,path):
        return 1
    
    def handle(self,request):       
        self.parent.parent.send_to_file_handler(request)
        
class MsgLogHandler(_Handler):
    def __init__(self,parent):
        self.match_path = '^/msglog/msglog$'
        _Handler.__init__(self,parent)
        
    def handle(self,request):
        msg_log = trimming_log('msglog')
        sort_order = 'descending'
        column = '_seq'
        end = len(msg_log)
        start = end - 25
        type = 'all'
        application = 'all'
        parameters = {}
        response = Response(request)
        parameters = request.get_query_dictionary()
        if parameters:
            if parameters.has_key('column'):
                column = parameters['column']
            if parameters.has_key('start'):
                start = parameters['start']
            if parameters.has_key('end'):
                end = parameters['end']
            if parameters.has_key('type'):
                type = parameters['type'] 
            if parameters.has_key('application'):
                application = parameters['application']
            if parameters.has_key('sort_order'):
                sort_order = parameters['sort_order']
        
        data = msg_log.get_range(column, float(start), float(end), 1)
        children = []
        index = 0
        increment = 1
        end = len(data)
        if column == '_seq':            
            if string.upper(sort_order) == 'DESCENDING':
                increment = -1
                index = len(data) -1
                end = -1
        while index != end:
            current_index = index            
            child = entry_factory(data[index])        
            index = child.feed(data,index,increment)
            if current_index == index:
                index += increment                            
            children.append(child)
        formatter = HTMLFormatter(children)
        response.send(formatter.output(type,application,sort_order))
 
class GenerateError(_Handler):
    def __init__(self,parent):
        self.match_path = '^/msglog/error$'
        _Handler.__init__(self,parent)
    def handle(self,request):
        x = 10
        qd = request.get_query_dictionary()
        if qd.has_key('num'):
            x = int(qd['num'])
        
        response = Response(request)
        response.send('<html><body>Generating error</body></html>')
        for index in range(0,x):
            msglog.log('msglog',msglog.types.DB,'logging error: ' + str(index + 1))
##
# Web viewer for msglog.
#
# @implements mpx.service.network.http.RequestHandlerInterface
#
class Browser(RequestHandler):
    ##
    # Configures HTTP handler.
    #
    # @param config  Dictionary containing parameters and values from
    #                the configuration tool.
    # @key request_path  Regular expression for url requests that
    #                    should be forwarded to this handler.
    # @default /nodebrowser
    #
    # @see mpx.lib.service.RequestHandler#configure
    #
    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', '^/msglog/.*|^/msglog$', config)
        RequestHandler.configure(self, config)
        self.http_published_root = properties.HTTP_ROOT 
        self.handlers = []
        self.install_handlers()  
        
    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.RequestHandler#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        return config
    
    def match(self, path):
        reg_ex = re.compile(self.request_path)
        match = reg_ex.match(path)
        if match:
            if match.group() == path:
                return 1
        return 0

    def install_handlers(self):   
        self.handlers.append(GenerateError(self))
        self.handlers.append(RedirectHandler(self))
        self.handlers.append(GetRecordsFileHandler(self))
        self.handlers.append(MsgLogHandler(self))
        self.handlers.append(DefaultHandler(self))
    
    def find_handler(self,request):
        handler = None
        try:
            path = request.get_path()
            for h in self.handlers:
                if h.match(path):
                    handler = h
                    break
        except Exception,e:
            msglog.log('broadway',msglog.types.WARN,str(e))
        return handler
    
    ##
    # Called by http_server each time a request comes in whose url mathes one of
    # the paths this handler said it was interested in. 
    #
    # @param request  <code>Request</code> object from the http_server.  To send
    #                  resonse call <code>request.send(html)</code> where
    #                  <code>html</code> is the text response you want to send.
    # @fixme Handle exceptions gracefully and report them back to the client.
    # @fixme Don't convert the incoming values (as soon as we refactor the core
    #        ions).
    # @fixme After override, load the parent page instead of displaying the message.
    def handle_request(self, request):
        response = Response(request)
        try:
            h = self.find_handler(request)
            h.handle(request)
        except Exception,e:
            msglog.exception()
            response.send_error(500)
    
    def get_msglog(self, last_seq, size):
        msg_log = trimming_log("msglog")
        start = last_seq
        if last_seq == 0:
            start = msg_log.get_first_record()["_seq"]        
        end = start + size
        _data = msg_log.get_range("_seq", start, end, 1)
        data = []
        for d in _data:
            data.append(d)
        return data
    
##
# Intaciates and returns RequestHandler.  Allows
# for uniform instaciation of all classes defined
# in framwork.
#
# @return Instance of RequestHandler defined in this module.
#
def factory():
    return Browser()

