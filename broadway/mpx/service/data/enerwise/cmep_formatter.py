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
import array
import time
import string
from mpx.service.data import Formatter
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute

_field_index = {'record_type': 0,
                'record_version': 1,
                'sender_id': 2,
                'sender_customer_id': 3,
                'receiver_id': 4,
                'receiver_customer_id': 5,
                'timestamp': 6,
                'meter_id': 7,
                'purpose': 8,
                'commodity': 9,
                'units': 10,
                'calculation_constants': 11,
                'interval': 12,
                'count': 13, 
                'interval_data': 14}

_fields = ['MEPMD01', '19970819', 'Envenergy', '', '', '', '', \
              '', 'OK', '', '', '1.0', '', '', '']

class CMEPFormatter(Formatter):
    def configure(self, config):
        Formatter.configure(self, config)
        self.period = self.parent.log.period
        set_attribute(self, 'sender_id', 'Envenergy', config)
        set_attribute(self, 'customer_id', '', config)
        set_attribute(self, 'receiver_id', 'Enerwise', config)
        set_attribute(self, 'commodity', 'E', config)
        set_attribute(self, 'timestamp_format', '%Y%m%d%H%M', config)
        set_attribute(self, 'max_count', 48, config, int)
    
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'customer_id', config)
        get_attribute(self, 'sender_id', config)
        get_attribute(self, 'receiver_id', config)
        get_attribute(self, 'commodity', config)
        get_attribute(self, 'timestamp_format', config)
        get_attribute(self, 'max_count', config, str)
        return config
    
    def format(self, data):
        points = {}
        # build dictionary 'points' where key is point_name
        #  and value is a list of values for that point.
        for entry in data:
            for point in entry.keys():
                if points.has_key(point):
                    points[point].append(entry[point])
                else:
                    points[point] = [entry[point]]
        timestamps = points['timestamp']
        point_names = points.keys()
        point_names.remove('timestamp')
        point_names.sort()
        lines = []
        for point_name in point_names:
            units = ''
            meter_id = point_name
            if ',' in point_name:
                units = string.strip(point_name[string.index(point_name, ',') + 1:])
                meter_id = point_name[0:string.index(point_name, ',')]
            lines.extend(self._format_data(self.parent.scheduled_time(), timestamps, meter_id, units, points[point_name]))
        return string.join(lines, '\r\n')

    def _format_data(self, start_time, timestamps, meter_id, units, values):
        retlist = []
        fields = _fields[:]
        file_timestamp = time.strftime(self.timestamp_format, time.gmtime(start_time))
        fields[_field_index['units']] = units
        fields[_field_index['commodity']] = self.commodity
        fields[_field_index['meter_id']] = meter_id
        fields[_field_index['receiver_id']] = self.receiver_id
        fields[_field_index['sender_customer_id']] = self.customer_id
        fields[_field_index['sender_id']] = self.sender_id
        fields[_field_index['timestamp']] = file_timestamp
        # interval put into "MMDDHHMM" with MMDD = 0000
        fields[_field_index['interval']] = '0000%02d%02d' % (self.period / 3600, (self.period % 3600) / 60)
        value_index = 0
        # loop until we have finished with all values.
        while value_index < len(values):
            value_sets = []
            value_timestamp = time.strftime(self.timestamp_format, time.gmtime(timestamps[value_index]))
            # loop until we have reached the max_count, or finished with all values.
            while len(value_sets) < self.max_count and value_index < len(values):
                value = values[value_index]
                value_index += 1
                # assuming that '' for bad values is correct.
                try:
                    value = '%f' % value
                    protocol_text = ''
                except TypeError:
                    protocol_text = 'N'
                    value = ''
                value_set = (value_timestamp, protocol_text, value)
                value_sets.append(string.join(value_set, ','))
                value_timestamp = ''
            fields[_field_index['count']] = str(len(value_sets))
            fields[_field_index['interval_data']] = string.join(value_sets, ',')
            retlist.append(string.join(fields, ','))
        return retlist

def factory():
    return CMEPFormatter()
