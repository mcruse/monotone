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
from mpx_test import DefaultTestFixture, main

import time
import random
import string

from csv_formatter import CSVFormatter
from mpx.service.data import EIncompatiableFormat
from mpx.lib.exceptions import EBreakupTransfer

class _DataHolder:
    def __init__(self):
        self._data = []
    def configure(self,names):
        self._names = names
    def add_entry(self,values):
        entry = {}
        for i in range(0,len(values)):
            entry[self._names[i]] = values[i]
        self._data.append(entry)
    def append(self,entry):
        self._data.append(entry)
    def get_column_names(self):
        return self._names
    def get_data(self):
        return self._data
    def __getitem__(self,index):
        return self._data[index]
class _ParentHolder:
    def __init__(self,parent):
        self.time_function = time.gmtime
        self.parent = parent
    def _add_child(self,node):
        pass

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.data = _DataHolder()
        self.data.configure(['timestamp','column-A'])
        for x in range(1,20):
            self.data.add_entry([time.time(),x])
        exporters = _ParentHolder(self.data)
        exporter = _ParentHolder(exporters)
        exporter.log = self.data
        self.formatter = CSVFormatter()
        self.formatter.configure({'name':'csvformatter','parent':exporter})
    def test_1(self):
        columns = ''
        formatter = self.formatter
        stream = formatter.format(self.data)
        csv = ''
        data = stream.read(1024)
        while data:
            csv += data
            data = stream.read(1024)
        list = string.split(csv)
        columns = string.split(list[0],',')  
        if 'timestamp' in columns:
            if len(columns) > 2:
                self.fail('first line has to much information:\n ' +
                          string.join(columns,','))            
        else:
            self.fail('timestamp column was not found on the first line')
    def test_2(self):
        columns = ''
        formatter = self.formatter
        stream = formatter.format(self.data)
        csv = ''
        data = stream.read(1024)
        while data:
            csv += data
            data = stream.read(1024)
        list = string.split(csv)
        values = string.split(list[1],',')    
        if len(values) == 2:
            t = time.strptime(values[0],'%Y-%m-%dT%H:%M:%S')
        else:
            self.fail('wrong number of values in line #2')
    def test_3(self):
        columns = ''
        formatter = self.formatter
        stream = formatter.format(self.data)
        csv = ''
        data = stream.read(1024)
        while data:
            csv += data
            data = stream.read(1024)
        list = string.split(csv)
        values = string.split(list[1],',')
        for v in list[2:]:
            if len(string.split(v,',')) != 2:
                self.fail('wrong number of values in line')
    def test_EInconsistantFormat(self):
        formatter = self.formatter
        data = self.data
        for x in range(1,100):
            entry = {}
            entry['timestamp'] = time.time()
            entry['column-TEST'] = x
            data.append(entry)
        try:
            stream = formatter.format(self.data)
            csv = ''
            data = stream.read(1024)
            while data:
                csv += data
                data = stream.read(1024)
            raise 'test_2 failed, did not raise EBreakupTransfer'
        except EBreakupTransfer,e:
            pass
        except:
            raise 'test_2 failed, did not raise EBreakupTransfer'
    def test_column_order(self):
        formatter = self.formatter
        data = self.data
        stream = formatter.format(data)
        data = ''
        while '\n' not in data:
            data += stream.read(1024)
        columns = data[0:data.index('\n')]
        should = string.join(self.data.get_column_names(),',')
        self.failUnless(columns == should,'Columns not in right order')
##
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
