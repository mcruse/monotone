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

_fields = ['MEPMD01', '19970819', 'Envenergy', '', 'ABB', '', '', \
              '', 'OK', '', '', '1.0', '', '', '']

class CMEPFormatter(Formatter):
    def configure(self, config):
        Formatter.configure(self, config)
        self.period = self.parent.parent.parent.period
        set_attribute(self, 'customer_name', REQUIRED, config)
        set_attribute(self, 'account_name', REQUIRED, config)
        set_attribute(self, 'commodity', 'E', config)
    
    def configuration(self):
        config = Formatter.configuration(self)
        get_attribute(self, 'customer_name', config)
        get_attribute(self, 'account_name', config)
        get_attribute(self, 'commodity', config)
        return config
    
    def format(self, data):
        points = {}
        for entry in data:
            for point in entry.keys():
                if points.has_key(point):
                    points[point].append(entry[point])
                else:
                    points[point] = [entry[point]]
        timestamps = points['timestamp']
        timestamp = timestamps[0]
        point_names = points.keys()
        point_names.remove('timestamp')
        point_names.sort()
        lines = []
        for point_name in point_names:
            units = ''
            name = point_name
            # @note Column name should be in meter_name,units format.
            if ',' in point_name:
                units = string.strip(point_name[string.index(point_name, ',') + 1:])
                name = point_name[0:string.index(point_name, ',')]
            lines.append(self._format_data(self.parent.scheduled_time(), timestamp, name, units, points[point_name]))
        return string.join(lines, '\r\n')

    def _format_data(self, start_time, timestamp, name, units, values):
        fields = _fields[:]
        file_timestamp = time.strftime('%Y%m%d%H%M',time.gmtime(start_time))
        value_timestamp = time.strftime('%Y%m%d%H%M',time.gmtime(timestamp))
        fields[_field_index['units']] = units
        fields[_field_index['commodity']] = self.commodity
        meter_id = name + '|1'
        if units:
            meter_id += '/%s' % units
        fields[_field_index['meter_id']] = meter_id
        fields[_field_index['receiver_id']] = ''
        fields[_field_index['receiver_customer_id']] = self.customer_name + '|' + self.account_name
        fields[_field_index['timestamp']] = file_timestamp
        # interval put into "MMDDHHMM" with MMDD = 0000
        fields[_field_index['interval']] = '0000%02d%02d' % (self.period / 3600, (self.period % 3600) / 60)
        fields[_field_index['count']] = str(len(values))
        value_sets =  []
        for value in values:
            try:
                value = '%f' % value
                protocol_text = ''
            except ValueError:
                value = ''
                protocol_text = 'N'
            value_set = (value_timestamp, protocol_text, value)
            value_sets.append(string.join(value_set, ','))
            value_timestamp = ''
        fields[_field_index['interval_data']] = string.join(value_sets, ',')
        return string.join(fields, ',')

def factory():
    return CMEPFormatter()
