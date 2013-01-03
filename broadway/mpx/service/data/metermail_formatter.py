"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
#
# @fixme Could SGML be part of some sort of 'stream'?  Right now the entire
#        export is built into a string.  At least support some sort of max size
#        and instant export of the next chunk...
# @fixme Better support for log file reconfigurations.

import time

from mpx.lib import msglog
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.configure import stripped_str
from mpx.lib.sgml_formatter import SGMLFormatter
from mpx.lib.stream import StreamWithCallback
from mpx.lib.uuid import UUID

from mpx.service.data import EIncompatiableFormat
from mpx.service.data import Formatter

from metermail_nodes import MeterMailColumn
from metermail_nodes import MeterMailDeltaColumn

from metermail_time import DST_BIAS
from metermail_time import W3CDateTime
from metermail_time import dst_range

##
# Class that inherents from the base mpx.service.data.Formatter
# Pass in a list of dictionary of values to the format method
# which will then return XML of that data
class MeterMailFormatter(Formatter):
    MIME_TYPE='text/xml'
    ##
    # @param config
    # @key generated_by blah, blah, blah,...
    def configure(self, config):
        Formatter.configure(self, config)
        #
        # Usually hardcoded/calculated at runtime.
        #
        set_attribute(self, 'generated_by', '', config, stripped_str)
        if not self.generated_by:
            self.generated_by = 'Mediator MMA File v1.x'
        set_attribute(self, 'generated_by_namespace', '', config, stripped_str)
        if not self.generated_by_namespace:
            self.generated_by_namespace = 'Mediator Generated File'
        set_attribute(self, 'device_namespace', '', config, stripped_str)
        if not self.device_namespace:
            self.device_namespace = 'IONEnterprise'
        set_attribute(self, 'device_type', '', config, stripped_str)
        if not self.device_type:
            self.device_type = 'presumed downstream device'
# Not required according to Stephan Jones
#         set_attribute(self, 'timezone_bias', '', config, stripped_str)
#         if not self.timezone_bias:
#             self.timezone_bias = mma_timezone.bias_text()
#         set_attribute(self, 'timezone_dst_bias', '', config, stripped_str)
#         if not self.timezone_dst_bias:
#             self.timezone_dst_bias = mma_timezone.dst_bias_text()
#         set_attribute(self, 'timezone_dst_start', '', config, stripped_str)
#         if not self.timezone_dst_start:
#             self.timezone_dst_start = mma_timezone.dst_start_text()
#         set_attribute(self, 'timezone_dst_end', '', config, str)
#         if not self.timezone_dst_end:
#             self.timezone_dst_end = mma_timezone.dst_end_text()
# Now programmatically calculated:
#         set_attribute(self, 'device_timezone_bias', '', config, stripped_str)
#         if not self.device_timezone_bias:
#             self.device_timezone_bias = mma_timezone.bias_text()
#         set_attribute(self, 'device_timezone_dst_bias', '',
#                       config, stripped_str)
#         if not self.device_timezone_dst_bias:
#             self.device_timezone_dst_bias = mma_timezone.dst_bias_text()
#         set_attribute(self, 'device_timezone_dst_start', '',
#                       config, stripped_str)
#         if not self.device_timezone_dst_start:
#             self.device_timezone_dst_start = mma_timezone.dst_start_text()
#         set_attribute(self, 'device_timezone_dst_end', '', config, str)
#         if not self.device_timezone_dst_end:
#             self.device_timezone_dst_end = mma_timezone.dst_end_text()
        #
        # Optional
        #
        set_attribute(self, 'generated_by_type', '', config, stripped_str)
        set_attribute(self, 'generated_by_signature', '', config, stripped_str)
        set_attribute(self, 'device_signature', '', config, str)
        set_attribute(self, 'device_configuration_template', '', config, str)
        set_attribute(self, 'device_configuration_owner', '', config, str)
        set_attribute(self, 'device_configuration_tag1', '', config, str)
        set_attribute(self, 'device_configuration_tag2', '', config, str)
        set_attribute(self, 'device_configuration_revision', '', config, str)
        set_attribute(self, 'data_recorder_handle', '', config, str)
        set_attribute(self, 'add_smtp_envelope', '1', config, int)
        
# Not required according to Stephan Jones
#         set_attribute(self, 'configuration_template', 'none', config, str)
#         set_attribute(self, 'configuration_owner', 'unknown', config, str)
#         set_attribute(self, 'configuration_tag1', 'n/a', config, str)
#         set_attribute(self, 'configuration_tag2', 'n/a', config, str)
#         set_attribute(self, 'configuration_revision', '2.0', config, str)
        #
        # REQUIRED
        #
        set_attribute(self, 'device_name', REQUIRED, config, str)
        set_attribute(self, 'data_recorder_id', REQUIRED, config, str)
        set_attribute(self, 'data_recorder_label', REQUIRED, config, str)
        return
    ##
    # @returns returns the configuratation
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'generated_by', config, str)
        get_attribute(self, 'generated_by_namespace', config, str)
        get_attribute(self, 'generated_by_type', config, str)
        get_attribute(self, 'generated_by_signature', config, str)
# Not required according to Stephan Jones
#         get_attribute(self, 'configuration_template', config, str)
#         get_attribute(self, 'configuration_owner', config, str)
#         get_attribute(self, 'configuration_tag1', config, str)
#         get_attribute(self, 'configuration_tag2', config, str)
#         get_attribute(self, 'configuration_revision', config, str)
#         get_attribute(self, 'timezone_bias', config, str)
#         get_attribute(self, 'timezone_dst_bias', config, str)
#         get_attribute(self, 'timezone_dst_start', config, str)
#         get_attribute(self, 'timezone_dst_end', config, str)
        get_attribute(self, 'device_name', config, str)
        get_attribute(self, 'device_namespace', config, str)
        get_attribute(self, 'device_signature', config, str)
        get_attribute(self, 'device_type', config, str)
        get_attribute(self, 'device_configuration_template', config, str)
        get_attribute(self, 'device_configuration_owner', config, str)
        get_attribute(self, 'device_configuration_tag1', config, str)
        get_attribute(self, 'device_configuration_tag2', config, str)
        get_attribute(self, 'device_configuration_revision', config, str)
# Now programmatically calculated:
#         get_attribute(self, 'device_timezone_bias', config, str)
#         get_attribute(self, 'device_timezone_dst_bias', config, str)
#         get_attribute(self, 'device_timezone_dst_start', config, str)
#         get_attribute(self, 'device_timezone_dst_end', config, str)
        get_attribute(self, 'data_recorder_id', config, str)
        get_attribute(self, 'data_recorder_label', config, str)
        get_attribute(self, 'data_recorder_handle', config, str)
        set_attribute(self, 'add_smtp_envelope', config, int)
        return config
    def start(self):
        # self._PDO = PersistentDataObject(self,dmtype=GC_NEVER)
        # self._PDO.exception_log_last_time = 0.0
        # self._PDO.load()

        # Scan subtree of grandparent logger for channel (column) 'fsg_attrs'
        # nodes containing info required for FSG Demo, so that we don't have
        # to do the scan every time format() is called:
        self._channel_map = {}
        columns_node = self.parent.parent.parent.get_child('columns')
        column_nodes = columns_node.children_nodes()
        for column_node in column_nodes:
            if column_node.name == 'timestamp':
                continue
            for mmafmt_channel_attribute in ('mmafmt_channel_id',
                                             'mmafmt_channel_label',
                                             'mmafmt_channel_pos'):
                assert hasattr(column_node, mmafmt_channel_attribute), (
                    'MMA formatter requires a %r attribute on column'
                    ' %r on log %r.'
                    '  Please add a MeterMailColumnDecorator child.'
                    % (mmafmt_channel_attribute, column_node.name,
                       self.parent.parent.parent.name)
                    )
            self._channel_map[column_node.name] = column_node
        #self._exception_log = None
        #try:
        #    self._exception_log = as_node(self.exception_log_url)
        #except ENoSuchName:
        #    pass
        return

    ##
    # @param data list of dictionary values to be converted in to XML format.
    # @note timestamp MUST be one of the dictionary keys.
    # @trhows EIncompatiableFormat if timestamp is not a key in a dictionary
    #         entry. 
    def format(self, data):
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('data',data)
        stream.set_meta('index',0)
        formatter = SGMLFormatter()
        stream.set_meta('formatter',formatter)
        stream.set_meta('remaining', '')
        #
        #
        #
        stream.write('<?xml version="1.0" encoding="utf-8"?>\n')
        if self.add_smtp_envelope:
            #
            # <Envelope>
            #
            formatter.open_tag(
                'Envelope', **{
                'xmlns:xsd':'http://www.w3.org/2001/XMLSchema',
                'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance',
                }
                )
            #
            # <Header/>
            #
            formatter.open_close_tag(
                'Header', xmlns="http://schemas.xmlsoap.org/soap/envelope/"
                )
            #
            # <Body>
            #
            formatter.open_tag(
                'Body', xmlns="http://schemas.xmlsoap.org/soap/envelope/"
                )
            #
            # <Process>
            #
            formatter.open_tag(
                'Process',
                xmlns=("http://rddl.xmlinside.net/PowerMeasurement/data/ion/" +
                       "pushmessaging/service/1/")
                )
        #
        # <Data>
        #
        attributes = {
            'id':self.data_id(),
            'xmlns':(
                "http://rddl.xmlinside.net/PowerMeasurement/data/ion/" +
                "pushmessaging/2/"
                ),
            'xmlns:ident':(
                "http://rddl.xmlinside.net/PowerMeasurement/data/ion/" +
                "identity/1/"
                ),
            }
        formatter.open_tag('Data', **attributes)
        #
        # <ident:GeneratedBy/>
        #
        attributes = {
            'ident:name':self.generated_by,
            'ident:namespace':self.generated_by_namespace,
            'ident:dateTime':W3CDateTime().as_string_local(),
            }
        if self.generated_by_type:
            attributes['ident:type'] = self.generated_by_type,
        if self.generated_by_signature:
            attributes['ident:signature'] = self.generated_by_signature,
        formatter.open_close_tag('ident:GeneratedBy', **attributes)
# Not required according to Stephan Jones
#         formatter.open_tag(
#             'Configuration', **{
#             'ident:template':self.configuration_template,
#             'ident:owner':self.configuration_owner,
#             'ident:tag1':self.configuration_tag1,
#             'ident:tag2':self.configuration_tag2,
#             'ident:revision':self.configuration_revision,
#             'xmlns:ident':('http://rddl.xmlinside.net/PowerMeasurement' +
#                           '/data/ion/identity/1/'),
#             'xmlns':('http://rddl.xmlinside.net/PowerMeasurement/data' +
#                      '/ion/identity/1/')
#             }
#             )
#         formatter.open_tag('ident:Timezone')
#         formatter.open_tag('ident:Bias')
#         formatter.add_text(self.timezone_bias)
#         formatter.close_tag('ident:Bias', True)
#         formatter.open_tag('ident:DSTBias')
#         formatter.add_text(self.timezone_dst_bias)
#         formatter.close_tag('ident:DSTBias', True)
#         formatter.open_tag('ident:DSTStart')
#         formatter.add_text(self.timezone_dst_start)
#         formatter.close_tag('ident:DSTStart', True)
#         formatter.open_tag('ident:DSTEnd')
#         formatter.add_text(self.timezone_dst_end)
#         formatter.close_tag('ident:DSTEnd', True)
#         formatter.close_tag('ident:Timezone')
#         formatter.close_tag('Configuration')
        #
        # <Device>
        #
        attributes = {
            'ident:name':self.device_name,
            'ident:namespace':self.device_namespace,
            'ident:type':self.device_type,
            }
        if self.device_signature:
            attributes['ident:signature'] = self.device_signature,
        formatter.open_tag('Device', **attributes)
        #
        # <ident:Configuration>
        #
        attributes = {}
        if self.device_configuration_template:
            attributes['ident:template'] = self.device_configuration_template
        if self.device_configuration_owner:
            attributes['ident:owner'] = self.device_configuration_owner
        if self.device_configuration_tag1:
            attributes['ident:tag1'] = self.device_configuration_tag1
        if self.device_configuration_tag2:
            attributes['ident:tag2'] = self.device_configuration_tag2
        if self.device_configuration_revision:
            attributes['ident:revision'] = self.device_configuration_revision
        formatter.open_tag('ident:Configuration', **attributes)
        #
        # <ident:Timezone>
        #
        formatter.open_tag('ident:Timezone')
        #
        # <ident:Bias>
        #
        formatter.open_tag('ident:Bias')
        formatter.add_text(DST_BIAS.bias_text())
        #
        # </ident:Bias>
        #
        formatter.close_tag('ident:Bias', True)
        dst_bias_text = DST_BIAS.dst_bias_text()
        if dst_bias_text:
            #
            # <ident:DSTBias>
            #
            formatter.open_tag('ident:DSTBias')
            formatter.add_text(dst_bias_text)
            #
            # </ident:DSTBias>
            #
            formatter.close_tag('ident:DSTBias', True)
        this_year = time.localtime().tm_year
        last_year = this_year - 1
        for year in (last_year, this_year):
            dst_range_object = dst_range(year)
            dst_start = dst_range_object.dst_start_text()
            dst_end = dst_range_object.dst_end_text()
            if dst_start:
                #
                # <ident:DSTStart>
                #
                formatter.open_tag('ident:DSTStart')
                formatter.add_text(dst_start)
                #
                # </ident:DSTStart>
                #
                formatter.close_tag('ident:DSTStart', True)
                if dst_end:
                    #
                    # <ident:DSTEnd>
                    #
                    formatter.open_tag('ident:DSTEnd')
                    formatter.add_text(dst_end)
                    #
                    # </ident:DSTEnd>
                    #
                    formatter.close_tag('ident:DSTEnd', True)
        #
        # </ident:Timezone>
        #
        formatter.close_tag('ident:Timezone')
        #
        # </ident:Configuration>
        #
        formatter.close_tag('ident:Configuration')
        #
        # <DataRecorder>
        #
        attributes = {
            'id':self.data_recorder_id,
            'label':self.data_recorder_label,
            }
        if self.data_recorder_handle:
            attributes['handle'] = self.data_recorder_handle
        formatter.open_tag('DataRecorder', **attributes)
        #
        # <Channels>
        #
        formatter.open_tag('Channels')
        channel_list = self._channel_map.values()
        def cmp_channel_list(c1, c2):
            return cmp(c1.mmafmt_channel_id, c2.mmafmt_channel_id)
        channel_list.sort(cmp_channel_list)
        for column_node in channel_list:
            #
            # <Channel/>
            #
            attributes = {
                'id':column_node.mmafmt_channel_id,
                'label':column_node.mmafmt_channel_label,
                }
            if column_node.mmafmt_channel_pos:
                attributes['pos'] = column_node.mmafmt_channel_pos
            formatter.open_close_tag('Channel', **attributes)
        #
        # </Channels>
        #
        formatter.close_tag('Channels')
        #
        # <DataRecords>
        #
        formatter.open_tag('DataRecords')
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
                #
                # </DataRecords>
                #
                formatter.close_tag('DataRecords')
                #
                # </DataRecorder>
                #
                formatter.close_tag('DataRecorder')
                #
                # </Device>
                #
                formatter.close_tag('Device')
                #
                # </Data>
                #
                formatter.close_tag('Data')

                if self.add_smtp_envelope:
                    #
                    # </Process>
                    #
                    formatter.close_tag('Process')
                    #
                    # </Body>
                    #
                    formatter.close_tag('Body')
                    #
                    # </Envelope>
                    #
                    formatter.close_tag('Envelope')
                stream.write(formatter.output())
                stream.close()
                return None
            if not entry.has_key('timestamp'):
                raise EIncompatiableFormat()
            ts = W3CDateTime(entry['timestamp'])
            if self.parent.gm_time:
                ts = ts.as_string_utc()
            else:
                ts = ts.as_string_local()
            del(entry['timestamp'])
            attribute_pairs=[("ts",ts),]
            channel_pairs=[]
            keys = entry.keys()
            for key in keys:
                value = entry[key]
                if value is None:
                    # Do not include error values in the DR's attributes.
                    continue
                if not self._channel_map.has_key(key):
                    # Survive deleted columns.
                    continue
                channel_pairs.append(
                    (self._channel_map[key].mmafmt_channel_id,value)
                    )
            channel_pairs.sort()
            attribute_pairs.extend(channel_pairs)
            formatter.open_close_tag_ex('DR', attribute_pairs)
            output = formatter.output()
            count = stream.write(output)
            stream.set_meta('index',i+1)
            if count != len(output):
                stream.set_meta('remaining',output[count:])
                return None
        return None
    def data_id(self):
        return UUID()
