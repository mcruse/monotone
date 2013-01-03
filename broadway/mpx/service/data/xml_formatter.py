"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
# Module that provides our XMLFormatter class

import time
import string
from mpx.service.data import Formatter
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog
from mpx.lib.stream import StreamWithCallback
from mpx.service.data import EIncompatiableFormat
from mpx.lib.configure import as_boolean
from mpx.lib.sgml_formatter import SGMLFormatter
##
# Class that inherents from the base mpx.service.data.Formatter
# Pass in a list of dictionary of values to the format method
# which will then return XML of that data
class XMLFormatter(Formatter):
    MIME_TYPE='text/xml'
    ##
    # @param config
    # @key timestamp_format the timestamp format string example: Y-%m-%dT%H:%M:%S.
    # @key info the information that will be placed in the info attribute of the 
    # data tag
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self, 'timestamp_format', '%Y-%m-%dT%H:%M:%S', config)
        set_attribute(self, 'info', '', config)
        set_attribute(self, 'pretty_format',0,config,as_boolean)
  
    ##
    # @returns returns the configuratation
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'timestamp_format', config)
        get_attribute(self, 'info', config)
        get_attribute(self, 'pretty_format',config,str)
        return config
    
    ##
    # @param data list of dictionary values to be converted in to XML format.
    # @param pretty_format 0,1 optional parameter to return pretty xml, xml that has
    # carriage returns in it
    # @default 0
    # @note timestamp MUST be on of the dictionary keys.
    # @trhows EIncompatiableFormat if timestamp is not a key in a dictionary entry.
    def format(self, data,pretty_format = None):
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('data',data)
        stream.set_meta('index',0)
        formatter = SGMLFormatter()
        formatter.open_tag('data',info=self.info)
        stream.set_meta('formatter',formatter)
        stream.set_meta('remaining', '')
        return stream
    def output_callback(self, stream):
        data = stream.get_meta_value('data')
        index = stream.get_meta_value('index')
        formatter = stream.get_meta_value('formatter')
        remaining = stream.get_meta_value('remaining')
        if remaining:
            remaining = remaining[stream.write(remaining):]
            stream.set_meta('remaining',remaining)
            if remaining:
                return None
        for i in range(index,index+10):
            try:
                entry = data[i]
            except IndexError:
                formatter.close_tag('data')
                stream.write(formatter.output())
                stream.close()
                return None
            if not entry.has_key('timestamp'):
                raise EIncompatiableFormat()
            ts = self.parent.time_function(entry['timestamp'])
            ts = time.strftime(self.timestamp_format, ts)
            del(entry['timestamp'])
            formatter.open_tag('entry',timestamp=ts)
            for key,value in entry.items():
                formatter.open_tag('value', name=key)
                formatter.add_text(str(value))
                formatter.close_tag('value')
            formatter.close_tag('entry')
            output = formatter.output()
            count = stream.write(output)
            stream.set_meta('index',i+1)
            if count != len(output):
                stream.set_meta('remaining',output[count:])
                return None
        return None
        

##
# @return an instantiated XMLFormatter class
def factory():
    return XMLFormatter()
