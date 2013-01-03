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

from mpx.lib import msglog
from mpx.lib import msglog

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.exceptions import EBreakupTransfer

from mpx.lib.stream import StreamWithCallback

from mpx.service.data import EIncompatiableFormat
from mpx.service.data import Formatter

def format_varbinds(varBinds):
    text_lines = ['']
    for var, val in varBinds:
        text_lines.append('  %s: %s' % (var, val))
    return string.join(text_lines,'\n')

class TrapFormatter(Formatter):
    __node_id__ = ''
    MIME_TYPE='text/plain'
    ROW_FORMAT_MAP = {
        "version":str,
        "context_engine_id":str,
        "context_name":str,
        "address":str,
        "sysUpTime":str,
        "trap":str,
        "trap_enterprise":str,
        "varBinds":format_varbinds,
        "logtime":time.ctime,
        }
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self,'prefix', '', config)
        set_attribute(self,'suffix', '', config)
        return
    def configuration(self):
        config = Formatter.configuration(self)
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
        columns = self.parent.log.get_column_names()
        stream.set_meta('columns',columns)
        return stream
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
            if len(entry.keys()) != len(columns):
                if i != index:
                    # Raise exception next time so all data read.
                    return
                stream.write(self.suffix)
                raise EBreakupTransfer(entry,'Different number of columns')
            text_lines = ['']
            for column in columns:
                if not entry.has_key(column):
                    if i != index:
                        return
                    raise EBreakupTransfer(entry,'Different columns')
                text_lines.append(
                    "%s: %s" % (column,
                                self.ROW_FORMAT_MAP[column](entry[column]))
                    )
            text_lines.append('')
            entry = string.join(text_lines,'\n')
            count = stream.write(entry)
            stream.set_meta('index',i+1)
            if count != len(entry):
                stream.set_meta('remaining',entry[count:])
                return
        return None
