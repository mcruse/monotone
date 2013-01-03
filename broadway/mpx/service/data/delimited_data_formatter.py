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
import time
import string
from mpx.service.data import Formatter
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog
from mpx.service.data import EIncompatiableFormat
from mpx.lib.exceptions import EBreakupTransfer
from mpx.lib import msglog
from mpx.lib.stream import StreamWithCallback

class DelimitedDataFormatter(Formatter):
    MIME_TYPE='text/plain'
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self,'data_delimiter', ',', config)
        set_attribute(self,'header_delimiter', self.data_delimiter, config, str)
        set_attribute(self,'prefix', '', config)
        set_attribute(self,'suffix', '', config)
        set_attribute(self, 'timestamp_format', '%Y-%m-%dT%H:%M:%S', config)
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'timestamp_format', config)
        get_attribute(self,'header_delimiter',config)
        get_attribute(self,'data_delimiter',config)
        get_attribute(self,'prefix',config)
        get_attribute(self,'suffix',config)
        return config
    def format(self, data):
        if self.debug:
            msglog.log('broadway',msglog.types.DB,
                       'Format called on %s.' % self.name)
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('data', data)
        stream.set_meta('index', 0)
        stream.set_meta('remaining', '')
        if self.prefix:
            stream.write(self.prefix + '\n')
        self._write_header(stream)
        return stream
    def _write_header(self,stream):
        data = stream.get_meta_value('data')
        columns = self.parent.log.get_column_names()
        if data != ():
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
            stream.write(string.join(columns,self.header_delimiter) + '\n')
            stream.set_meta('columns',columns)
        else:
            stream.write(string.join(columns,self.header_delimiter) + '\n')
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
            ts = self.parent.time_function(entry['timestamp'])
            timestamp = time.strftime(self.timestamp_format, ts)
            values = [timestamp]
            for column in columns[1:]:
                if not entry.has_key(column):
                    if i != index:
                        return
                    raise EBreakupTransfer(entry,'Different columns')
                values.append(str(entry[column]))
            entry = string.join(values,self.data_delimiter) + '\n'
            count = stream.write(entry)
            stream.set_meta('index',i+1)
            if count != len(entry):
                stream.set_meta('remaining',entry[count:])
                return
        return None

def factory():
    return DelimitedDataFormatter()
