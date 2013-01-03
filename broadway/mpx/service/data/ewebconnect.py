"""
Copyright (C) 2003 2010 2011 Cisco Systems

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

class EWebConnectFormatter(Formatter):
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self,'line_one', '"ACDIAG"\n', config)
        set_attribute(self,'line_two', '"Diagnostics"\n', config)
        set_attribute(self,'line_three', '"Average"\n\n\n', config)
        set_attribute(self,'line_four', 'begindata\n', config)
        set_attribute(self,'line_five', '', config)
        set_attribute(self,'line_six', '', config)
        set_attribute(self,'line_seven', '', config)
        set_attribute(self,'line_eight', '', config)
        set_attribute(self,'line_nine', '', config)
        set_attribute(self,'line_ten', '', config)
        set_attribute(self,'date_format', '"%m/%d/%y"', config)
        set_attribute(self,'time_format', '"%H:%M:%S"', config) 
        set_attribute(self,'value_format', '"%14.3f"', config) 
        set_attribute(self,'max_value_length', 16, config, int)
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'line_one', config)
        get_attribute(self, 'line_two', config)
        get_attribute(self, 'line_three', config)
        get_attribute(self, 'line_four', config)
        get_attribute(self, 'line_five', config)
        get_attribute(self, 'line_six', config)
        get_attribute(self, 'line_seven', config)
        get_attribute(self, 'line_eight', config)
        get_attribute(self, 'line_nine', config)
        get_attribute(self, 'line_ten', config)
        get_attribute(self, 'date_format', config)
        get_attribute(self,'time_format',config)
        get_attribute(self,'value_format',config)
        get_attribute(self,'max_value_length',config, str)
        return config
    def start(self):
        self.prefix = ''
        for line in ('line_one','line_two','line_three',
                     'line_four','line_five','line_six',
                     'line_seven','line_eight','line_nine','line_ten'):
            self.prefix += string.replace(getattr(self,line),'\\n','\n')
        Formatter.start(self)
    def format(self, data):
        if self.debug:
            msglog.log('broadway',msglog.types.DB,
                       'Format called on %s.' % self.name)
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('data', data)
        stream.set_meta('index', 0)
        stream.set_meta('remaining', '')
        if self.prefix:
            stream.write(self.prefix)
        self._write_header(stream)
        return stream
    def _write_header(self,stream):
        data = stream.get_meta_value('data')
        columns = self.parent.log.get_column_names()[:]
        columns.remove('timestamp')
        entry = data[0]
        names = entry.keys()
        names.remove('timestamp')
        names.sort()
        if len(names) != len(columns):
            columns = names
        else:
            for name in names:
                if name not in columns:
                    columns = names
                    break
        stream.write('"Date","Time"')
        for column in columns:
            stream.write(',"%s"' % column)
        stream.write('\n')
        stream.write(',,' + ('"Raw Value",' * (len(columns)))[0:-1] + '\n')
        stream.set_meta('columns',['timestamp'] + columns)
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
                stream.close()
                return
            if not entry.has_key('timestamp'):
                raise EIncompatiableFormat()
            if len(entry.keys()) != len(columns):
                if i != index:
                    # Raise exception next time so all data read.
                    return
                raise EBreakupTransfer(entry,'Different number of columns')
            ts = self.parent.time_function(entry['timestamp'])
            date = time.strftime(self.date_format, ts)
            timestamp = time.strftime(self.time_format, ts)
            values = [date,timestamp]
            for column in columns[1:]:
                if not entry.has_key(column):
                    if i != index:
                        return
                    raise EBreakupTransfer(entry,'Different columns')
                if entry[column] is None:
                    values.append('None')
                else:
                    values.append(self.value_format % entry[column])
                if (self.max_value_length > 0 and 
                    len(values[-1]) > self.max_value_length):
                    msglog.log('EWebConnect Log Formatter',msglog.types.WARN,
                               'Len of %s > max_value_length' % values[-1])
            line = string.join(values,',') + '\n'
            count = stream.write(line)
            stream.set_meta('index',i+1)
            if count != len(line):
                stream.set_meta('remaining',line[count:])
                return
        return None

