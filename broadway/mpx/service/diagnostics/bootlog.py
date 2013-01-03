"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import re
import os
import sys

from test import Test

from ion import Factory

class BootlogWarning(object):
    WARNING = re.compile("^.*(warning\s*.*?)", re.IGNORECASE)

class BootlogError(object):
    ERROR = re.compile("^.*(error\s*.*?)", re.IGNORECASE)

###
# We always see these non-fatal errors from the IDE driver:
#    hda: task_no_data_intr: status=0x51 { DriveReady SeekComplete Error }
#    hda: task_no_data_intr: error=0x04 { DriveStatusError }
# This RE allows us to ignore them.
class BootlogIsHDA:
    ISHDA = re.compile("^hda.*", re.IGNORECASE)
    
class BootlogTester(Test):
    def __init__(self, **kw):
        self.filename = '/var/log/boot.log'
        super(BootlogTester, self).__init__(**kw)
        self._test_name = 'BootlogTester'
        return
        
    def _parse_line(self, line, lineno = None):
        result = BootlogError.ERROR.search(line)
        if result:
            result = BootlogIsHDA.ISHDA.match(line)
            if not result:
                self.log('ERROR in boot log: %s' % line)
                self._nerrors += 1
        result = BootlogWarning.WARNING.search(line)
        if result:
            self.log('WARNING in boot log: %s' % line)
            self._nwarnings += 1
        return
        
    def runtest(self):
        if not os.path.exists(self.filename):
            raise Exception(
                'Error, missing the dmesg log file [%s]' % self.filename
            )
        self.log('Examining system boot log for errors and warnings.')
        try:
            f = open(self.filename, "r+")
            for line in f.xreadlines():
                self._parse_line(line)
        finally:
            f.close()
        self.log('Boot log, found %d errors and %d warnings.' % \
            (self._nerrors, self._nwarnings))
        return self.passed()
        
f = Factory()
f.register('BootlogTester', (BootlogTester,))

