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
    ##
    # @param config
    # @key timestamp_format the timestamp format string example: Y-%m-%dT%H:%M:%S.
    # @key info the information that will be placed in the info attribute of the 
    # data tag
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self, 'timestamp_format', '%m/%d/%Y %I:%M:%S %p', config)
        set_attribute(self, 'info', '', config)
        set_attribute(self, 'pretty_format',0,config,as_boolean)
        set_attribute(self, 'prefix', 'do_method=notify&cdvalues=', config)
        set_attribute(self, 'suffix', '', config)
        set_attribute(self, 'station_code', '4', config)
        set_attribute(self, 'time_base', REQUIRED, config)
        set_attribute(self, 'status1', '', config)
        set_attribute(self, 'status2', '', config)
        set_attribute(self, 'status3', '', config)
        set_attribute(self, 'status4', '', config)
        set_attribute(self, 'status5', '', config)
        set_attribute(self, 'status6', '', config)
        set_attribute(self, 'status7', '', config)
        set_attribute(self, 'status8', '', config)
  
    ##
    # @returns returns the configuratation
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'timestamp_format', config)
        get_attribute(self, 'info', config)
        get_attribute(self, 'pretty_format',config,str)
        get_attribute(self, 'prefix',config,str)
        get_attribute(self, 'suffix',config,str)
        get_attribute(self, 'station_code', config)
        get_attribute(self, 'time_base', config)
        get_attribute(self, 'status1', config)
        get_attribute(self, 'status2', config)
        get_attribute(self, 'status3', config)
        get_attribute(self, 'status4', config)
        get_attribute(self, 'status5', config)
        get_attribute(self, 'status6', config)
        get_attribute(self, 'status7', config)
        get_attribute(self, 'status8', config)
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
        stream.write(self.prefix + '<?xml version="1.0" encoding="UTF-8"?>')
        formatter = SGMLFormatter()
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
        if index == 0:
            formatter.open_tag('root')
        for i in range(index,index+10):
            try:
                entry = data[i]
            except IndexError:
                formatter.close_tag('root')
                stream.write(formatter.output(self.pretty_format))
                stream.write(self.suffix)
                stream.close()
                return None
            if not entry.has_key('timestamp'):
                raise EIncompatiableFormat()
            ts = time.strftime(self.timestamp_format, 
                               time.gmtime(entry['timestamp']))
            del(entry['timestamp'])
            formatter.open_tag('Tbl_analog_data',
                               STA_StationCode=self.station_code)
            formatter.add_attribute('STA_TimeBase',self.time_base)
            formatter.add_attribute('Date_Time',ts)
            for x in range(0,len(entry.keys())):
                value = entry['Value%s' % (x+1)]
                status = getattr(self, 'status%s' % (x+1))
                formatter.add_attribute('Value%s' % (x+1),value)
                formatter.add_attribute('Status%s' % (x+1),status)
            formatter.close_tag('Tbl_analog_data')
            output = formatter.output(self.pretty_format)
            count = stream.write(output)
            stream.set_meta('index',index+i+1)
            if count != len(output):
                stream.set_meta('remaining',output[count:])
                return None
        return None

##
# @return an instantiated XMLFormatter class
def factory():
    return XMLFormatter()
