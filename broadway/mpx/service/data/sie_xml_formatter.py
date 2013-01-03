"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import array
from mpx.service.data import Formatter
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog

class _RecordSet:
    def __init__(self, debug):
        self.records = []
        self.debug = debug

    def add_record(self, id, value, timestamp, status = 0):
        record = {'PointID': id, 'TimeStamp': timestamp, 'Value': value, 'Status': status}
        self.records.append(record)

    def output_xml(self):
        if self.debug:
            msglog.log('sie', msglog.types.DB, 'Starting xml ouput')
        xml = array.array('c')
        xml.fromstring('<DataRecords>')
        for record in self.records:
            xml.fromstring('\n\t<Record>')
            for key in record.keys():
                xml.fromstring('\n\t\t<' + key + '>' + str(record[key]) + '</' + key + '>')
            xml.fromstring('\n\t</Record>')
        xml.fromstring('\n</DataRecords>')
        if self.debug:
            msglog.log('sie', msglog.types.DB, 'xml is %s chars long' % len(xml))
        return xml.tostring()

class XMLFormatter(Formatter):
    def configure(self, config):
        Formatter.configure(self, config)
        set_attribute(self, 'timestamp_format', '%Y-%m-%dT%H:%M:%S', config)
    
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'timestamp_format', config)
        return config
    
    def format(self, data):
        if self.debug:
            msglog.log('sie', msglog.types.DB, 'format data started')
        record_set = _RecordSet(self.debug)
        for entry in data:
            timestamp = time.strftime(self.timestamp_format, time.gmtime(entry['timestamp']))
            del(entry['timestamp'])
            for point in entry.keys():
                record_set.add_record(point, entry[point], timestamp)
        if self.debug:
            msglog.log('sie', msglog.types.DB, 'format data returning RecordSet.output_xml()')
        return record_set.output_xml()

def factory():
    return XMLFormatter()
