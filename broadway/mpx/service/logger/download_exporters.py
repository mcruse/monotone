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
import time
import string
import bisect

from mpx.service.data import Formatter
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog
from mpx.service.data import EIncompatiableFormat
from mpx.lib.exceptions import EBreakupTransfer
from mpx.lib.stream import StreamWithCallback
from mpx.lib.rna import NodeFacade

class DelimitedDataFormatter(Formatter):
    MIME_TYPE='text/plain'
    def __init__(self, log_node,
                 data_delimiter=',',
                 header_delimiter=',',
                 prefix='',
                 suffix='',
                 eol='\r\n'):
        self.log = log_node
        # default, no timezone based conversion performed.
        self.tz_range = {0:{'tz_offsets':(0, 0), 'is_dst':0}}
        try:
            # log_info may be a dict or <'mpx.service.logger.log.LogNodeInfo'>, 
            # depending on if it's local or remote.  repr -> eval used here is so 
            # that we don't have to worry about it - it's now a dict.
            log_info = eval(repr(self.log.get_info()))
            tzinfo_range = log_info['tzinfo_range']
            if tzinfo_range:
                for tzi in tzinfo_range:
                    sample_time = tzi['sample_time']
                    tz_offsets = tzi['tz_offsets']
                    is_dst = tzi['is_dst']
                    self.tz_range[sample_time] = \
                        {'tz_offsets':tz_offsets, 'is_dst':is_dst}
        except:
            pass
        self.data_delimiter = data_delimiter
        self.header_delimiter = header_delimiter
        self.prefix = prefix
        self.suffix = suffix
        self.eol=eol
        self.timestamp_format='%Y-%m-%dT%H:%M:%S'
        return
    def format(self, data):
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('data', data)
        stream.set_meta('index', 0)
        stream.set_meta('remaining', '')
        if self.prefix:
            stream.write(self.prefix + self.eol)
        if data:
            self._write_header(stream)
        else:
            columns = self.log.get_column_names()
            stream.write(string.join(columns,self.header_delimiter) + self.eol)
            stream.set_meta('columns',columns)
        return stream
    def _write_header(self,stream):
        data = stream.get_meta_value('data')
        columns = self.log.get_column_names()
        entry = data[0]
        names = entry.keys()
        names.remove('timestamp')
        names.sort()
        names.insert(0,'timestamp')
        if len(names) != len(columns):
            columns = names
        else:
            for name in names:
                if name not in columns:
                    columns = names
                    break
        #Bug fix starts
        columns.remove('timestamp')
        #columns.insert(2,'Timestamp (GMT)')
        columns.insert(0,'Timestamp (Local time)')#Cheating
        stream.write(string.join(columns,self.header_delimiter) + self.eol)
        columns.remove('Timestamp (Local time)')#Cheating again
        #columns.remove('Timestamp (GMT)')
        columns.insert(0,'timestamp')
        #Bug fix ends. Thanks for watching'''
        stream.set_meta('columns',columns)
    def output_callback(self, stream):
        data = stream.get_meta_value('data')
        index = stream.get_meta_value('index')
        remaining = stream.get_meta_value('remaining')
        columns = stream.get_meta_value('columns')
        if remaining:
            remaining = remaining[stream.write(remaining):]
            stream.set_meta('remaining',remaining)
            if remaining:
                return
        for i in range(index,index+10):
            try:
                entry = data[i]
            except IndexError:
                stream.write(self.suffix)
                stream.close()
                return
            if not entry.has_key('timestamp'):
                raise EIncompatiableFormat()
            if len(entry.keys()) != len(columns):
                if i != index:
                    # Raise exception next time so all data read.
                    return
                stream.write(self.suffix)
                raise EBreakupTransfer(entry,'Different number of columns')
            ts_utc = entry['timestamp']
            ts_tuple_utc = time.gmtime(ts_utc)
            ts_str_utc = time.strftime(self.timestamp_format, ts_tuple_utc)
            values = [self._calc_local_strftime(ts_utc)]
            for column in columns[1:]:
                if not entry.has_key(column):
                    if i != index:
                        return
                    raise EBreakupTransfer(entry,'Different columns')
                values.append(str(entry[column]))
#            values.append(time_stamp)
            entry = ""
            for value in values:
                entry = entry + '"' + value + '"' + self.data_delimiter;
            entry = entry + self.eol
            count = stream.write(entry)
            stream.set_meta('index',i+1)
            if count != len(entry):
                stream.set_meta('remaining',entry[count:])
                return
        return None
    def _calc_local_strftime(self, ts_utc):
        sample_times = self.tz_range.keys()
        sample_times.sort()
        index = bisect.bisect(sample_times, ts_utc) - 1
        offset = 0
        tzr = self.tz_range.get(sample_times[index])
        if tzr:
            is_dst = tzr.get('is_dst', 0)
            offset = tzr.get('tz_offsets')[int(is_dst)]
        ts_local = time.gmtime(ts_utc - offset)
        ts_str_local = time.strftime(self.timestamp_format, ts_local)
        return ts_str_local

class CSVFormatter(DelimitedDataFormatter):
    def __init__(self, log_node):
        DelimitedDataFormatter.__init__(self, log_node)
        return

def exporter_factory(format, log):
    if format.lower() == 'csv':
        return CSVFormatter(log)
    raise EInvalidValue('format', format, 'format must be csv')
