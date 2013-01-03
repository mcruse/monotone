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
import os
import time

from mpx_test import DefaultTestFixture, main

from mpx import properties
from mpx.lib.node import Node
from mpx.lib.node import as_internal_node

from metermail_formatter import MeterMailFormatter
from metermail_nodes import MeterMailColumnDecorator

from mpx.service.data import EIncompatiableFormat

class BogusLogger(Node):
    pass

class BogusLog(Node):
    pass

class BogusColumns(Node):
    pass

class BogusColumn(Node):
    pass

class BogusExporters(Node):
    pass

class BogusPeriodicExporter(Node):
    def __init__(self):
        self.gm_time = 1
        self.time_function = time.gmtime

class TestCase(DefaultTestFixture):
    TEMP_DIR = properties.get('TEMP_DIR')
    FILE_COUNT = 0
    def temp_file_name(self):
        TestCase.FILE_COUNT += 1
        return os.path.join(self.TEMP_DIR,
                            '_test_case_xml_formatter.%d.%d' %
                            (os.getpid(), self.FILE_COUNT))
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.data = []
        ts = float(15*int(time.time()/15))
        for x in range(1,20):
            entry = {}
            entry['timestamp'] = ts
            entry['column-A'] = x
            self.data.append(entry)
            ts += 15
        return
    def new_column_a_log(self):
        self.new_node_tree()
        logger = BogusLogger()
        logger.configure({'name':'logger',
                          'parent':as_internal_node('/services')})
        log = BogusLog()
        log.configure({'name':'bogus_log', 'parent':logger})
        columns = BogusColumns()
        columns.configure({'name':'columns', 'parent':log})
        timestamp_column = BogusColumn()
        timestamp_column.configure({'name':'timstamp', 'parent':columns})
        column_a = BogusColumn()
        column_a.configure({'name':'column-A', 'parent':columns})
        column_a_decorator = MeterMailColumnDecorator()
        column_a_decorator.configure({'name':'metermail_column_decorator',
                                      'parent':column_a,
                                      'mmafmt_channel_id':'column-A',
                                      'mmafmt_channel_label':'kW a',
                                      })
        exporters = BogusExporters()
        exporters.configure({'name':'exporters', 'parent':log})
        periodic_exporter = BogusPeriodicExporter()
        periodic_exporter.configure({'name':'periodic_exporter',
                                     'parent':exporters})
        formatter = MeterMailFormatter()
        formatter.configure({'name':'metermail_formatter',
                             'parent':periodic_exporter,
                             'device_name':'device_name',
                             'data_recorder_id':'data_recorder_id',
                             'data_recorder_label':'data_recorder_label',
                             })
        return
    def test_valid_xml(self):
        self.new_column_a_log()
        tmp_file = None
        tmp_file = self.temp_file_name()
        f = open(tmp_file, 'w')
        as_internal_node('/').start()
        stream = as_internal_node(
            '/services/logger/bogus_log/exporters/periodic_exporter/'
            'metermail_formatter'
            ).format(self.data)
        output = ''
        data = stream.read(1024)
        while data:
            output += data
            data = stream.read(1024)
        f.write(output)
        f.close()
        command = 'xmllint ' + str(tmp_file)
        stdin, stdout,stderr = os.popen3(command)
        out  = stdout.readlines()
        err = stderr.readlines()
        if err:
            error = ''
            for e in err:
                error += e + '\n'
                pass
            self.fail('File is not a valid XML file:\n' + error)
        return
    def test_timestamp_exception(self):
        self.new_column_a_log()
        as_internal_node('/').start()
        formatter = as_internal_node(
            '/services/logger/bogus_log/exporters/periodic_exporter/'
            'metermail_formatter'
            )
        data =[]
        for x in range(1,10):
            entry = {}
            entry['column-A'] = x
            data.append(entry)
        try:
            xml = formatter.format(data)
            while xml.read(100):
                pass
            self.fail(
                'If no timestamp field it should throw an EIncompatiableFormat'
                )
        except EIncompatiableFormat:
            pass
        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
