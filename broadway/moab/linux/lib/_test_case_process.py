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
from mpx_test import DefaultTestFixture, main

import os
import popen2

import process

class TestCase(DefaultTestFixture):
    VERBOSE = 0
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        return
    def progress_message(self, fmt, *args):
        if self.VERBOSE:
            print fmt % args
    def test_register_named_process(self, quite=0):
        if not quite: self.progress_message("\ntest_register_named_process:")
        process.register_named_process('test', os.getpid())
        return
    def test_reregister_named_process(self, quite=0):
        if not quite: self.progress_message("\ntest_reregister_named_process:")
        process.register_named_process('test', os.getpid())
        try:
            process.register_named_process('test', os.getpid())
        except process.EProcessRunning:
            return
        raise 'Did not detect self already running.'
    def test_status_from_nosuch_name(self, quite=0):
        if not quite: self.progress_message("\ntest_status_from_nosuch_name:")
        status = process.status_from_name('test')
        if status.name != 'test':
            raise 'Did not set the name correctly.'
        if status.pid != None:
            raise 'Found nonexistant named process id.'
        if status.state != process.StatusEnum.DOESNOTEXIST:
            raise 'Found nonexistant named process state.'
        return
    def test_status_from_name(self, quite=0):
        if not quite: self.progress_message("\ntest_status_from_name:")
        process.register_named_process('test', os.getpid())
        status = process.status_from_name('test')
        if status.name != 'test':
            raise 'Did not set the name correctly.'
        if status.pid !=  os.getpid():
            raise 'Self does not have my process id.'
        if status.state != process.StatusEnum.EXISTS:
            raise 'Self does not EXIST, using status_from_name.'
        return
    def test_terminate_named_process(self, quite=0):
        if not quite: self.progress_message("\ntest_terminate_named_process:")
        child = popen2.Popen4('bash -c "while true; do sleep 1; done"')
        process.register_named_process('child', child.pid)
        status = process.status_from_name('child')
        if status.name != 'child':
            raise 'Did not set the name correctly.'
        if status.pid != child.pid:
            raise 'Child does not have the correct pid.'
        if status.state != process.StatusEnum.EXISTS:
            raise 'Child does not EXIST.'
        exit_status = process.terminate_named_process('child')
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    TestCase.VERBOSE = 1
    main()
