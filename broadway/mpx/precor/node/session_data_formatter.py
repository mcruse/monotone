"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
import time, StringIO
from mpx.lib import msglog
from mpx.precor.node import _xml
from mpx.service.data._exporter import Formatter
from mpx.lib.stream import StreamWithCallback
from mpx.service.data import EIncompatiableFormat
from mpx.lib.sgml_formatter import SGMLFormatter

##
#
class SessionDataFormatter(Formatter):
    MIME_TYPE='text/xml'
    def __init__(self, ics_serial_id):
        Formatter.__init__(self)
        self._ics_serial_id = ics_serial_id
        return
    #def format(self, ws_dicts):
        #wss = _xml.WorkoutSessions()
        #wss.msg_time = time.time()
        #wss.ics_serial_id = self._ics_serial_id
        #for ws_dict in ws_dicts:
            #ws = _xml.WorkoutSession(ws_dict)
            #wss.workout_sessions.append(ws)
        #sgml = SGMLFormatter()
        #wss.get_xml(sgml)
        #output = _xml._xml_prolog + sgml.output_complete()
        ##print 'output:\n',output
        #stream = StringIO.StringIO(output)
        #stream.seek(0)
        #return stream
    ##
    # @param data list of dictionary values to be converted in to XML format.
    # @param pretty_format 0,1 optional parameter to return pretty xml, xml that has
    # carriage returns in it
    # @default 0
    # @note timestamp MUST be on of the dictionary keys.
    # @trhows EIncompatiableFormat if timestamp is not a key in a dictionary entry.
    def format(self, ws_dicts, pretty_format = None):
        stream = StreamWithCallback(self.output_callback)
        stream.set_meta('data', ws_dicts)
        stream.set_meta('index',0)
        formatter = SGMLFormatter()
        # Insert overall open tag, plus top-level data tags:
        formatter.add_text(_xml._xml_prolog)
        formatter.open_tag('workout-sessions')
        formatter.open_tag('msg-time')
        formatter.add_text(_xml._convert_utc_sec_to_date_time_str(time.time()))
        formatter.close_tag('msg-time')
        formatter.open_tag('ics-serial-id')
        formatter.add_text(str(self._ics_serial_id))
        formatter.close_tag('ics-serial-id')
        stream.set_meta('formatter',formatter)
        stream.set_meta('remaining', '')
        return stream
    def output_callback(self, stream):
        ws_dicts = stream.get_meta_value('data')
        index = stream.get_meta_value('index')
        formatter = stream.get_meta_value('formatter')
        remaining = stream.get_meta_value('remaining')
        if remaining:
            remaining = remaining[stream.write(remaining):]
            stream.set_meta('remaining',remaining)
            if remaining:
                return None
        for i in range(index, index + 10):
            try:
                ws_dict = ws_dicts[i]
            except IndexError:
                formatter.close_tag('workout-sessions')
                stream.write(formatter.output())
                stream.close()
                msglog.log('mpx',msglog.types.INFO,'Sent %u workout sessions to InSite server.' \
                           % len(ws_dicts))
                return None
            if not ws_dict.has_key('timestamp'):
                raise EIncompatiableFormat()
            ws = _xml.WorkoutSession(ws_dict)
            ws.get_xml(formatter)
            output = formatter.output()
            count = stream.write(output)
            stream.set_meta('index', i + 1)
            if count != len(output):
                stream.set_meta('remaining',output[count:])
                return None
        return None
        
