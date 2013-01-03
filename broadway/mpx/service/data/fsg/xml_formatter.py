"""
Copyright (C) 2006 2011 Cisco Systems

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
from mpx.lib.exceptions import EInvalidValue, ENoSuchName
from mpx.lib.node import as_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog
from mpx.lib.stream import StreamWithCallback
from mpx.service.data import EIncompatiableFormat
from mpx.lib.configure import as_boolean
from mpx.lib.sgml_formatter import SGMLFormatter
from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GC_NEVER

from fsg_nodes import ChannelAttrsColumn
from fsg_nodes import ChannelAttrsDeltaColumn
from fsg_nodes import FsgComparisonTrigger

import sys

def DEBUG(fmt, *args):
    if args:
        msg = fmt % args
    else:
        msg = fmt
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    return

##
# Class that inherents from the base mpx.service.data.Formatter
# Pass in a list of dictionary of values to the format method
# which will then return XML of that data
class XMLFormatter(Formatter):
    MIME_TYPE='text/xml'
    def __init__(self):
        Formatter.__init__(self)
        self._channels = {} # {name:{uom:,meastype:,Delta:,Totalized:,key:}}
        self._exception_log = None
        # NEVER CREATE A PDO BEFORE THE NODE IS INSERTED IN THE NODE TREE!
        self._PDO = None
        return
    ##
    # @param config
    # @key timestamp_format the timestamp format string example: Y-%m-%dT%H:%M:%S.
    # @key info the information that will be placed in the info attribute of the 
    # data tag
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self, 'debug_lvl', 0, config, int)
        set_attribute(self, 'timestamp_format', '%Y-%m-%dT%H:%M:%S', config)
        set_attribute(self, 'pretty_format',0,config,as_boolean)
        set_attribute(self, 'location_info','DefaultLocationInfo',config)
        set_attribute(self, 'location_key','DefaultLocationKey',config)
        set_attribute(self, 'panel_info','DefaultPanelInfo',config)
        set_attribute(self, 'panel_key','DefaultPanelKey',config)
        set_attribute(self, 'capture_period',24.0,config,float) # capture period preceding data transmission time (hrs)
        set_attribute(self, 'exception_log_url','/services/logger/fsg_exception_log',config)
    ##
    # @returns returns the configuratation
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'debug_lvl', config, int)
        get_attribute(self, 'timestamp_format', config)
        get_attribute(self, 'pretty_format',config,str)
        get_attribute(self, 'location_info',config)
        get_attribute(self, 'location_key',config)
        get_attribute(self, 'panel_info',config)
        get_attribute(self, 'panel_key',config)
        get_attribute(self, 'capture_period',config,float) # capture period preceding data transmission time (hrs)
        get_attribute(self, 'exception_log_url',config)
        return config
    
    def start(self):
        self._PDO = PersistentDataObject(self,dmtype=GC_NEVER)
        self._PDO.exception_log_last_time = 0.0
        self._PDO.load()
        # Scan subtree of grandparent logger for channel (column) 'fsg_attrs'
        # nodes containing info required for FSG Demo, so that we don't have
        # to do the scan every time format() is called:
        self._channels = {}
        columns_node = self.parent.parent.parent.get_child('columns')
        column_nodes = columns_node.children_nodes()
        for column_node in column_nodes:
            if column_node.name == 'timestamp':
                continue
            assert isinstance(column_node, ChannelAttrsColumn) \
                   or isinstance(column_node, ChannelAttrsDeltaColumn), \
                   'Column %s should be class ChannelAttrsColumn, but is class %s' \
                   % (column_node.name, column_node.__class__.__name__)
            self._channels[column_node.name] = {
                'channel_node':column_node,'values':[]

                }
            
        self._exception_log = None
        try:
            self._exception_log = as_node(self.exception_log_url)
        except ENoSuchName:
            pass
        return
    ##
    # cancel():
    # Called by exporter if attempted transport fails, to clear out pre-formatted
    # data waiting in self._channels value dicts. Else, the pre-formatted data
    # in self._channels is still present at next attempt, and will cause transport
    # of multiple copies of same data:
    #
    def cancel(self):
        for channel_dict in self._channels.values():
            channel_dict['values'] = []
        return
    ##
    # @param data list of dictionary values to be converted in to XML format.
    # @param pretty_format 0,1 optional parameter to return pretty xml, xml that has
    # carriage returns in it
    # @default 0
    # @note timestamp MUST be on of the dictionary keys.
    # @trhows EIncompatibleFormat if timestamp is not a key in a dictionary entry.
    def format(self, data, pretty_format=None):
        # Organize all log data (list of time-based dicts) into a dict of 
        # point-based lists. (Dict of lists could get REALLY large; may 
        # need to do only one point at a time...
        # self._channels:K=col_name,V=col_dict
        # col_dict:K='column_node':,'values':list_of_2tuples
        # list_of_2tuples: [(timestamp,value),]
        # Only want records for preceding self.capture_period-hr period:
        end_time = time.time()
        start_time = self.parent.last_time() # ASSUME that parent is a periodic exporter...
        # Comment out line below, in favor of line above, because FSG tends to
        # disable their FTP server (effectively) for days at a time, but still
        # want all the data gathered during those blackout periods to go to the
        # FTP server when the server reappears with respect to the Mediator. 
        # This change means that the FTP server recvs table-formatted data all 
        # the way back to the last successful export, regardless of the
        # actual size of that data:
        #start_time = end_time - (self.capture_period * 3600.0)
        data_to_send = 0
        data = data[:]
        self.debug_print('Data: %s' % data,None,1)
        removed_channels = []
        for log_rec_dict in data:
            timestamp = log_rec_dict['timestamp']
            if (timestamp < start_time) \
               or (timestamp > end_time):
                continue
            for channel_name in log_rec_dict.keys():
                if channel_name == 'timestamp':
                    continue
                if not self._channels.has_key(channel_name):
                    if not channel_name in removed_channels:
                        msglog.log('fsg:xml_formatter',msglog.types.ERR, \
                                   'Channel %s has been removed from the configuration.' \
                                   % channel_name)
                        removed_channels.append(channel_name)
                    continue
                data_to_send = 1
                self._channels[channel_name]['values'].append((timestamp,log_rec_dict[channel_name],))
        channel_names = self._channels.keys() # it's a list
        # Organize all data from exception log, if any:
        exception_dicts = {} # K:trigger name, V:time-sorted list of  2tuples
                             # (timestamp, message)
        if not self._exception_log is None:
            if self._PDO.exception_log_last_time > start_time:
                start_time = self._PDO.exception_log_last_time + 0.00001 # do not re-send already-sent data
            exception_data = self._exception_log.get_range('timestamp',start_time,end_time)
            for log_rec_dict in exception_data:
                trigger_node_url = log_rec_dict['trigger_node_url']
                trigger_node = as_node(trigger_node_url)
                assert isinstance(trigger_node, FsgComparisonTrigger), \
                       'Node %s should be FsgComparisonTrigger, is %s' \
                       % (trigger_node.name, trigger_node.__class__)
                timestamp = log_rec_dict['timestamp']
                trigger_node_msg = log_rec_dict['trigger_node_msg']
                if not exception_dicts.has_key(trigger_node_url):
                    exception_dicts[trigger_node_url] = {'trigger_node_url':trigger_node_url,'timestamps':[(timestamp,trigger_node_msg,)]}
                else:
                    exception_dicts[trigger_node_url]['timestamps'].append((timestamp,trigger_node_msg,))
                self._PDO.exception_log_last_time = timestamp
                self._PDO.save()
        if (data_to_send == 0) and (len(exception_dicts) == 0):
            msglog.log('fsg:xml_formatter',msglog.types.INFO,'No data or exceptions to send.')
            return None # nothing to send
        # Create an output stream to minimize the combined size of the XML
        # file and the remaining point_dicts contents during formatting:
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('channel_names',channel_names)
        stream.set_meta('exception_data',exception_dicts.values()) # pass in a list of "values" (dicts), to allow easy iteration
        stream.set_meta('index',0) # number of point time-value lists written to XML output stream
        formatter = SGMLFormatter()
        # Write opening tags:
        formatter.open_tag('data', 
                           info=self.location_info,
                           key=self.location_key
                           )
        formatter.open_tag('device', 
                           info=self.panel_info,
                           key=self.panel_key
                           )
        output = formatter.output()
        self.debug_print(output,None,1)
        stream.write(output)
        stream.set_meta('formatter',formatter)
        stream.set_meta('remaining', '')
        data_mode = 'channels'
        if data_to_send == 0:
            data_mode = 'exceptions' # no data for channels, so skip 'em
        stream.set_meta('data_mode',data_mode)
        return stream
    def output_callback(self, stream):
        remaining = stream.get_meta_value('remaining')
        if remaining:
            count = stream.write(remaining)
            remaining = remaining[count:]
            stream.set_meta('remaining',remaining)
            if remaining:
                return None
            data_mode = stream.get_meta_value('data_mode')
            if data_mode == 'close':
                stream.close()
                return
        del remaining
        index = stream.get_meta_value('index')
        formatter = stream.get_meta_value('formatter')
        data_mode = stream.get_meta_value('data_mode')
        if data_mode == 'channels':
            channel_names = stream.get_meta_value('channel_names')
            for i in range(index,index+5): # try writing 5 channel time-value lists at a time
                channel_dict = {}
                try:
                    channel_dict = self._channels[channel_names[i]]
                except IndexError: # no more data available; move on to exceptions
                    data_mode = 'exceptions'
                    stream.set_meta('data_mode', data_mode)
                    break
                channel_node = channel_dict['channel_node']
                formatter.open_tag('channel',name=channel_node.channel_name,
                                   uom=channel_node.uom,
                                   meastype=channel_node.meastype,
                                   Delta=channel_node.Delta,
                                   Totalized=channel_node.Totalized,
                                   key=channel_node.key,)
                stream.set_meta('index',i+1)
                for timestamp,value in channel_dict['values']:
                    ts = self.parent.time_function(timestamp)
                    ts_str = time.strftime(self.timestamp_format, ts)
                    formatter.open_tag('value',timestamp=ts_str)
                    formatter.add_text(str(value))
                    formatter.close_tag('value')
                formatter.close_tag('channel')
                output = formatter.output()
                self.debug_print(output,None,1)
                channel_dict['values'] = [] # save memory: data is now in stream or remaining
                count = stream.write(output)
                if count != len(output):
                    stream.set_meta('remaining',output[count:])
                    return None
        if data_mode == 'exceptions':
            exception_data = stream.get_meta_value('exception_data')
            for i in range(0,5): # try writing 5 exception lists at a time
                exception_dict = {}
                try:
                    exception_dict = exception_data[i]
                except IndexError: # no more exceptions available; close out XML file
                    try:
                        formatter.close_tag('device')
                        formatter.close_tag('data')
                        output = formatter.output()
                        self.debug_print(output,None,1)
                        count = stream.write(output)
                        if count != len(output):
                            stream.set_meta('remaining',output[count:])
                            data_mode = 'close'
                            stream.set_meta('data_mode', data_mode)
                            return None
                        stream.close()
                        return None
                    except:
                        msglog.exception()
                        return None
                trigger_node_url = exception_dict['trigger_node_url']
                trigger_node = as_node(trigger_node_url)
                formatter.open_tag('exception',name=trigger_node.name,
                                  key=trigger_node.key,)
                stream.set_meta('index',i+1)
                for exc_timestamp,msg in exception_dict['timestamps']:
                    ts = self.parent.time_function(exc_timestamp)
                    ts_str = time.strftime(self.timestamp_format, ts)
                    formatter.open_tag('value',timestamp=ts_str)
                    formatter.add_text(msg)
                    formatter.close_tag('value')
                formatter.close_tag('exception')
                output = formatter.output()
                self.debug_print(output,None,1)
                count = stream.write(output)
                if count != len(output):
                    stream.set_meta('remaining',output[count:])
                    return None
            del exception_data[0:5] # save memory: exception data is now in XML output stream
        return None
    def debug_print(self, msg_fmt_str, msg_value_tuple=None, msg_lvl=1):
        if msg_lvl <= self.debug_lvl:
            if msg_value_tuple is None:
                prn_msg = 'FsgXmlFmttr: ' + msg_fmt_str
            else:
                prn_msg = 'FsgXmlFmttr: ' + (msg_fmt_str % msg_value_tuple)
            print prn_msg
            self.parent.msglog(prn_msg)
        return
        

##
# @return an instantiated XMLFormatter class
def factory():
    return XMLFormatter()
