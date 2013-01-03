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
##
# Test cases to exercise exception memory use.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib import msglog
from mpx.lib import ELoadingDisabled

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.msglog_object = msglog.log_object()
        msglog.log("_test_case_testing", msglog.types.INFO, "setUp")
        return
    def test_exception_after_unload(self):
        self.msglog_object._ReloadableSingleton__unrealize()
        self.msglog_object.singleton_set_loadable_state(False)
        try:
            1/0
        except:
            msglog.exception()
        return
    def test_realize_when_unloadable(self):
        self.msglog_object._ReloadableSingleton__unrealize()
        self.msglog_object.singleton_set_loadable_state(False)
        try:
            self.msglog_object.singleton_load()
        except ELoadingDisabled:
            return
        self.fail("singleton_load() did not raise ELoadingDisable")
        return
    def test_log_when_unloadable(self):
        self.msglog_object._ReloadableSingleton__unrealize()
        self.msglog_object.singleton_set_loadable_state(False)
        msglog.log("_test_case_testing", msglog.types.INFO,
                   "test_log_when_unloadable")
        try:
            for entry in self.msglog_object:
                raise "I shouldn't get here."
        except ELoadingDisabled:
            return
        self.fail(
            "Attempt to 'automatically' realize did not raise ELoadingDisable"
            )
        return
