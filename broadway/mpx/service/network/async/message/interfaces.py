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
from mpx.componentry import Interface
from mpx.componentry import Attribute

class ITransaction(Interface):
    """
        Represents a full HTTP transaction.  A transaction consists of 
        a request and a response.  This container object associates 
        requests and responses to simplify interaction with HTTP 
        servers.  It facilitates transaction tracking, timeout, 
        expiration, etc.
    """

class IHeader(Interface):
    """
        Object representation of Message Header.
    """
    def set_name(name):
        """
            Set the name of the header.
            
            NOTE: name may be initiazed using first param to constructor.
        """
    def set_value(value):
        """
            Set the value of the header.
            
            NOTE: value may be initiazed using first param to constructor.
        """
    def to_tuple():
        """
            Return (name, value) tuple representation.
        """
    def to_dict():
        """
            Return {name: value} dict representation.
        """
    def to_string():
        """
            Return 'name: value' string representation.
        """
    def from_tuple(headertuple):
        """
            - CLASSMETHOD -
            
            Build from (name, value) tuple.
        """
    def from_dict(headerdict):
        """
            - CLASSMETHOD -
            
            Build from {name: value} dict.
        """
    def from_string(header):
        """
            - CLASSMETHOD -
            
            Build from 'name: value' string.
        """

class IHeaderCollection(Interface):
    """
        Collection of Header objects.  Is list type object.
        
        NOTE: list methods append, extend, remove, etc., can 
        all be used to work with Header type objects directly.
    """
    def add_header(self, header):
        """
        """
    def get_header(self, name, default = None):
        """
        """
    def get_header_value(self, name, default = None):
        """
        """
    def get_headers(self):
        """
        """
    def get_header_values(self):
        """
        """
    def get_header_names(self):
        """
        """
    def has_header(self, header):
        """
        """
    def has_header_named(self, name):
        """
        """
    def remove_header(self, header):
        """
        """
    def remove_header_named(self, name):
        """
        """
    def to_name_header_tuples(self):
        """
        """
    def to_name_value_tuples(self):
        """
            Return [(name, value), (name, value), ...] representation 
            of all headers.
        """
    def to_name_header_dict(self):
        """
        """
    def to_name_value_dict(self):
        """
            Return {name: value, name:value, ...} dict represtation 
            of all headers.
        """
    def to_strings():
        """
            Return ["name: value", "name: value", ...] representation 
            of all headers.
        """
    def to_string():
        """
            Return 'name: value\r\n
                    name: value'
            representation of all headers.
        """
    def to_message_header():
        """
            Return 'name: value\r\n
                    name: value\r\n
                    \r\n'
            representation of all headers.
            
            NOTE: this returns string formatted for inclusion directly 
            in HTTP message.
        """
    def from_headers(klass, headers):
        """
            - CLASSMETHOD -
        """
    def from_name_header_tuples(klass, headertuples):
        """
            - CLASSMETHOD -
        """
    def from_name_value_tuples(klass, headertuples):
        """
            - CLASSMETHOD -
            Build from [(name, value), (name, value), ...] representation.
        """
    def from_name_header_dict(klass, headersdict):
        """
            - CLASSMETHOD -
        """
    def from_name_value_dict(self, headersdict):
        """
            - CLASSMETHOD -
            Build from {name: value, name: value, ...} representation.
        """
    def from_strings(headerstrings):
        """
            - CLASSMETHOD -
            Build from ['name: value', 
                        ' value continuation', 
                        'name: value', ...] representation.
        """
    def from_string(headerstring):
        """
            - CLASSMETHOD -
            Build from 'name: value\r\n
                        name: value\r\n
                          additional value\r\n
                        name: value\r\n'
            representation.
            
            NOTE: this method will convert header from HTTP message 
            as sent.
        """
    def from_message_header(headerstring):
        """
            - CLASSMETHOD -
            Build from 'name: value\r\n
                        name: value\r\n
                          additional value\r\n
                        name: value\r\n
                        \r\n'
            representation.
            
            NOTE: this method will convert header from HTTP message 
            as sent.
        """


class IMessage(Interface):
    """
        Base class for HTTP messages.  Shared concepts 
        are implemented here.
    """
    def is_persistent():
        """
            Returns True message header are configured to allow 
            TCP connection to recipient to remain open.
            
            For HTTP/1.0 this means the "Connection" header must 
            be set to "keep-alive," otherwise the connection should 
            be used for a single-transaction.
            
            For HTTP/1.1 this means that the "Connection" header is 
            *not* set to "close."  The default TCP connection behaviour 
            for 1.1 is to be persistent.
        """
    
    def get_version():
        """
            Get the HTTP version of this message.  The version 
            will be returned as string value as it is included 
            in messages themselves.  For example, HTTP/1.1
        """
    
    def has_header(name):
        """
            Returns true if header with name 'name' is defined 
            in this message.
        """
    
    def get_header(name, default = None):
        """
            Return value of header named 'name' if it exists, 
            otherwise, return default.
        """
    
    def get_content():
        """
            Return file-like object for reading message body, 
            or None if there is no body.
        """
    
    def get_transfer_encoding():
        """
            Get transfer encoding of message.  This will 
            either be chunked, or None.  Encoding can be 
            applied to both incoming and outgoing messages.
        """


class IRequest(Interface):
    def __init__(url, data = None, headers = {}, version = 'HTTP/1.1'):
        """
            Initialize request object.
        """
    def is_persistent():
        """
            Returns True message header are configured to allow 
            TCP connection to recipient to remain open.
            
            For HTTP/1.0 this means the "Connection" header must 
            be set to "keep-alive," otherwise the connection should 
            be used for a single-transaction.
            
            For HTTP/1.1 this means that the "Connection" header is 
            *not* set to "close."  The default TCP connection behaviour 
            for 1.1 is to be persistent.
        """
    def get_version():
        """
        """
    def get_port():
        """
        """
    def get_host():
        """
        """
    def get_method():
        """
        """
    def has_response():
        """
        """
    def get_response():
        """
        """
    def has_header(name):
        """
        """
    def get_header(name, default = None):
        """
        """
    def get_debuglevel():
        """
        """
    def get_outgoing_producer():
        """
        """
    def will_close():
        """
        """
    def add_header(name, value):
        """
        """
    def add_cookie(cookie):
        """
        """
    def set_data(data):
        """
        """
    def set_debuglevel(level):
        """
        """
    def set_response(response):
        """
        """
    def is_readonly():
        """
        """
    def is_modifiable():
        """
        """
    def log(bytes):
        """
        """

class IResponse(Interface):
    def __init__(version, status, reason, headers):
        """
        """
    def read(bytes = -1):
        """
        """
    def getvalue():
        """
        """
    def await_completion(timeout = None):
        """
        """
    def get_reader():
        """
        """
    def is_complete():
        """
        """
    def will_close():
        """
        """
    def get_terminator():
        """
        """
    def get_header(name, default = None):
        """
        """
    def has_header(name):
        """
        """
    def collect_incoming_data(data):
        """
        """
    def found_terminator():
        """
        """

