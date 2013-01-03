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
from mpx.service.data.xml_formatter import XMLFormatter

class TCSFormatter(XMLFormatter):
    def start(self):
        self._devices = {}
        devices = self.parent.parent.parent.devices()
        for device in devices:
            self._devices[device.name] = {'type':device.type,
                                          'address':device.address}
        XMLFormatter.start(self)
    def output_callback(self,stream):
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
            timestamp = time.strftime(self.timestamp_format, ts)
            del(entry['timestamp'])
            formatter.open_tag('entry',timestamp=timestamp)
            for device,points in entry.items():
                type = self._devices[device]['type']
                address = self._devices[device]['address']
                formatter.open_tag('device',type=type,address=address)
                for name in points.keys():
                    type = points[name]['type']
                    value = points[name]['value']
                    formatter.open_tag('value',type=type,name=name)
                    formatter.add_text(str(value))
                    formatter.close_tag('value')
                formatter.close_tag('device')
            formatter.close_tag('entry')
            output = formatter.output()
            count = stream.write(output)
            stream.set_meta('index',i+1)
            if count != len(output):
                stream.set_meta('remaining',output[count:])
                return None
        return None