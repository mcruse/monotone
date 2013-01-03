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
import urllib
import time
import string
from mpx.lib import msglog
from mpx.lib.stream import StreamWithCallback
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.service.data import Formatter

class PowerWebFormatter(Formatter):
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self, 'timestamp_format', '%Y/%m/%d %H:%M:%S', config)
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'timestamp_format', config)
        return config
    def start(self):
        content = 'application/x-www-form-urlencoded'
        self.parent.transporter.content_type = content
        Formatter.start(self)
    def format(self, data):
        if self.debug:
            msglog.log('broadway',msglog.types.DB,
                       'Format called on %s.' % self.name)
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('data', data)
        stream.set_meta('index', 0)
        stream.set_meta('remaining', '')
        return stream
    def output_callback(self, stream):
        data = stream.get_meta_value('data')
        index = stream.get_meta_value('index')
        remaining = stream.get_meta_value('remaining')
        if remaining:
            remaining = remaining[stream.write(remaining):]
            stream.set_meta('remaining',remaining)
            if remaining:
                return
        ordered = self.parent.parent.parent.get_column_names()
        sorted = ordered[:]
        sorted.sort()
        for i in range(index,index+10):
            output = ''
            names = ordered[:]
            try:
                entry = data[i]
            except IndexError:
                stream.close()
                return
            if not entry.has_key('timestamp'):
                raise EIncompatiableFormat()
            keys = entry.keys()
            keys.sort()
            if keys != sorted:
                names = keys
            ts = self.parent.time_function(entry['timestamp'])
            timestamp = time.strftime(self.timestamp_format, ts)
            del(entry['timestamp'])
            names.remove('timestamp')
            entries = []
            for name in names:
                line = (('timestamp[]=%s&asset[]=%s&' +
                         'value[]=%s') % (timestamp,name,entry[name]))
                entries.append(line)
            output = '&'
            if i == index:
                output = ''
            output += urllib.quote_plus(string.join(entries,'&'),'=&')
            count = stream.write(output)
            stream.set_meta('index',i+1)
            if count != len(output):
                stream.set_meta('remaining',output[count:])
                break
        return
