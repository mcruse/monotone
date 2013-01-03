"""
Copyright (C) 2011 Cisco Systems

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
from mpx.service.data import EIncompatiableFormat
from mpx.service.data.csv_formatter import CSVFormatter

from mpx.lib.exceptions import EBreakupTransfer

from mpx.lib import msglog
from mpx.lib.node import as_node
from columns import ChannelAttrsColumn
from columns import ChannelAttrsDeltaColumn

import time
import string

debug = 1

class EnernocV2Formatter(CSVFormatter):
    dimensions = ['host_id', 
                  'primary_key']
    def __init__(self):
        self._channels = {}
        super(EnernocV2Formatter, self).__init__()
        return
    
    def configure(self, config):
        # override timestamp format to meet Enernoc's specific
        # requirements.
        config['timestamp_format'] = '%Y-%m-%dT%H:%M:%S.%%0.3d%%s:%%s'
        super(EnernocV2Formatter, self).configure(config)
        return
    
    def start(self):
        columns_node = self.parent.parent.parent.get_child('columns')
        for col in columns_node.children_nodes():
            if col.name == 'timestamp':
                continue
            assert isinstance(col, ChannelAttrsColumn) \
                   or isinstance(col, ChannelAttrsDeltaColumn), \
                   'Column %s should be class ChannelAttrsColumn, but is class %s' \
                   % (col.name, col.__class__.__name__)
            self._channels[col.name] = {}
            self._channels[col.name]['host_id'] = getattr(col, 'host_id',
                                                  as_node('/services/status/hostname').get())
            self._channels[col.name]['primary_key'] = col.get_source_node_url()
        super(EnernocV2Formatter, self).start()
        return
    
    def _write_header(self, stream):
        pass
        
    def output_callback(self, stream):
        data = stream.get_meta_value('data')
        index = stream.get_meta_value('index')
        remaining = stream.get_meta_value('remaining')
        columns = self.parent.log.get_column_names()
        if remaining:
            remaining = remaining[stream.write(remaining):]
            stream.set_meta('remaining', remaining)
            if remaining:
                return
        for i in range(index, index+10):
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
            
            ts = self.parent.time_function(entry['timestamp'])
            timestamp = time.strftime(self.timestamp_format, ts)
            # hack - strftime does not provide millisecond support
            ms = int((entry['timestamp'] * 1000) % 1000)
            utc_offset = time.strftime('%z', ts)
            
            timestamp = timestamp % (ms,utc_offset[0:3], utc_offset[3:])
            strbuff = ''
            for column in columns[1:]:
                if not entry.has_key(column):
                    if i != index:
                        return
                    raise EBreakupTransfer(entry,'Different columns')
                value = str(entry[column])
                strbuff += self._build_buff(column, value, timestamp)
            count = stream.write(strbuff)
            stream.set_meta('index', i+1)
            if count != len(strbuff):
                if debug:
                    msg = 'enernoc_formatter, data remains (%d,%d)' %\
                        (count, len(strbuff))
                    msglog.log('broadway', msglog.types.INFO, msg)
                stream.set_meta('remaining',strbuff[count:])
                return
        return
    
    def _build_buff(self, column, value, timestamp):
        ch = self._channels
        cols = [ch[column]['host_id'],
                ch[column]['primary_key'],
                timestamp,
                value]
        
        return string.join(cols, self.data_delimiter) + '\n'
    
    dimensions = ['host_id', 
                  'primary_key']

def factory():
    return EnernocV2Formatter()
