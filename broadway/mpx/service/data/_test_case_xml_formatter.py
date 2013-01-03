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
import os
import time

from mpx_test import DefaultTestFixture, main

from mpx import properties
from xml_formatter import XMLFormatter
from mpx.service.data import EIncompatiableFormat

class _Parent:
    def __init__(self):
        self.time_function = time.gmtime
    def _add_child(self,node):
        pass

class TestCase(DefaultTestFixture):
    TEMP_DIR = properties.get('TEMP_DIR')
    FILE_COUNT = 0
    def temp_file_name(self):
        TestCase.FILE_COUNT += 1
        return os.path.join(self.TEMP_DIR,
                            '_test_case_xml_formatter.%d.%d' % \
                            (os.getpid(), self.FILE_COUNT))
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.data = []
        for x in range(1,20):
            entry = {}
            entry['timestamp'] = time.time()
            entry['column-A'] = x
            self.data.append(entry)
        return
    def test_Valid_1(self):
        tmp_file = None
        tmp_file = self.temp_file_name()
        f = open(tmp_file,'w')
        formatter = XMLFormatter()
        formatter.configure({'name':'xmlformatter','parent':_Parent()})
        stream = formatter.format(self.data)
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
    def get_dtd(self):
        dtd = '<?xml version="1.0" encoding="UTF-8"?> '
        dtd += '<!ELEMENT data (entry*)> '
        dtd += '<!ATTLIST data '
        dtd += 'info CDATA #IMPLIED >'
        dtd += '<!ELEMENT entry (value*)> '
        dtd += '<!ATTLIST entry '
        dtd += 'timestamp CDATA #REQUIRED> '
        dtd += '<!ELEMENT value (#PCDATA)> '
        dtd +=  '<!ATTLIST value '
        dtd +=  'name CDATA #REQUIRED>'
        return dtd
        
    def test_DTD_1(self):
        try:
            tmp_file = None
            tmp_file = self.temp_file_name()
            tmp_file2 = self.temp_file_name()
            f2 = open(tmp_file2,'w')
            f2.write(self.get_dtd())
            f2.close()
            f = open(tmp_file,'w')
            formatter = XMLFormatter()
            formatter.configure({'name':'xmlformatter','parent':_Parent()})
            stream = formatter.format(self.data)
            output = ''
            data = stream.read(1024)
            while data:
                output += data
                data = stream.read(1024)
            f.write(output)
            f.close()
            command = 'xmllint -dtdvalid ' + str(tmp_file2) + ' ' + str(tmp_file)
            stdin, stdout,stderr = os.popen3(command)
            out  = stdout.readlines()
            err = stderr.readlines()
            if err:
                error = ''
                for e in err:
                    error += e + '\n'
                    
                self.fail('File does not conform to the DTD:\n' + error)
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file)
                except:
                    pass
            if tmp_file2:
                try:
                    os.unlink(tmp_file2)
                except:
                    pass
    def test_timestamp_exception(self):
        formatter = XMLFormatter()
        formatter.configure({'name':'xmlformatter','parent':_Parent()})
        data =[]
        for x in range(1,10):
            entry = {}
            entry['column-A'] = x
            data.append(entry)
        try:
            xml = formatter.format(data)
            while xml.read(100):
                pass
            self.fail('If no timestamp field it should throw an EIncompatiableFormat')
        except EIncompatiableFormat:
            pass
        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
