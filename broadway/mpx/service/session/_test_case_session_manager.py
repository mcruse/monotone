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
import sys
import time
import random

from mpx_test import DefaultTestFixture, main

from mpx.service.session import SessionManager, ESessionDenied
from mpx.lib import pause

# Testing hook...
# @note Set the passwd file to our test file.
SessionManager.PASSWD_FILE='moab/user/passwd'

class TestCase(DefaultTestFixture):
    VERBOSE = 0
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        self.session_manager = None
        return
    def _new(self, ttl=3600):
        self.session_manager = SessionManager()
        self.session_manager.configure({'name':'SessionManager',
                                        'parent':None,
                                        'ttl':ttl})
        self.session_manager.start()
        return
    def _del(self):
        if self.session_manager is not None:
            self.session_manager.stop()
            self.session_manager = None
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self._new()
        return
    def tearDown(self):
        try:
            self._del()
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def progress(self, fmt, *args):
        if self.VERBOSE:
            sys.stderr.write(fmt % args)
            sys.stderr.flush()
        return
    def test_create_session(self):
        sid = self.session_manager.create('mpxadmin','mpxadmin',1)
        return
    def test_deny_session(self, quite=0):
        try:
            self.session_manager.create('mpxadmin','mpxy')
        except ESessionDenied:
            return
        raise 'Failed to deny an invalid session.'    
    def test_validate(self, quite=0):
        session_id = self.session_manager.create('mpxadmin','mpxadmin',1)
        valid = self.session_manager.validate(session_id)
        if valid == 0:
            raise 'Failed to validate session'
        return
    def test_restore(self, quite=0):
        sids = []
        for i in range(0,10):
            sids.append(self.session_manager.create('mpxadmin','mpxadmin',1))
        self._del()
        self._new()
        for sid in sids:
            assert self.session_manager.validate(sid), (
                "Failed to validate restored session: %r" % sid)
        return
    def test_destroy(self, quite=0):
        total = 10
        valid_sids = []
        invalid_sids = []
        all_sids = []
        for i in range(0,total):
            valid_sid = self.session_manager.create('mpxadmin','mpxadmin',1)
            valid_sids.append(valid_sid)
            all_sids.append(valid_sid)
        invalidate = range(0,total,2)
        invalidate.reverse()
        for i in invalidate:
            invalid_sid = valid_sids.pop(i)
            self.session_manager.destroy(invalid_sid)
            invalid_sids.append(invalid_sid)
        for sid in all_sids:
            is_valid = self.session_manager.validate(sid)
            if is_valid:
                assert sid in valid_sids, (
                    "%r is valid, but should be invalid." % sid)
            else:
                assert sid in invalid_sids, (
                    "%r is invalid, but should be valid." % sid)
        return
    def test_ttl_collect(self, quite=0):
        # Delete the current SessionManager.
        self._del()
        # Instantiate a new SessionManager, setting ttl to 2 seconds.
        ttl=2.0
        self._new(ttl=ttl)
        total = 10
        fresh_sids = []
        stagnant_sids = []
        all_sids = []
        # Instantiate <code>total</code> (10) new sessions.
        for i in range(0,total):
            fresh_sid = self.session_manager.create('mpxadmin','mpxadmin',1)
            fresh_sids.append(fresh_sid)
            all_sids.append(fresh_sid)
        # Select half the sessions for expiration.
        stagnate = range(0,total,2)
        stagnate.reverse()
        for i in stagnate:
            stagnant_sid = fresh_sids.pop(i)
            stagnant_sids.append(stagnant_sid)
        # Wait for half of the session expiration time.
        pause(ttl/2.0)
        # "Touch" the sessions NOT selected for expiration.
        for fresh_sid in fresh_sids:
            # Validate and touch.
            is_valid = self.session_manager.validate(fresh_sid, touch=1)
            assert is_valid, ("validate(%r) unexpectedly failed." % fresh_sid)
        # Wait "just over" the expiration time for the "untouched" sessions.
        pause(ttl/2.0+0.1)
        # Confirm that the correct sessions are valid/stale.
        for sid in all_sids:
            is_valid = self.session_manager.validate(sid)
            if is_valid:
                assert sid in fresh_sids, (
                    "%r is fresh, but should be stagnant." % sid)
            else:
                assert sid in stagnant_sids, (
                    "%r is stagnant, but should be fresh." % sid)
        # Force the SessionManager to collect "stale" sessions.
        count = self.session_manager.collect()
        assert count == total/2, (
            "Excepted to collect %d expired sessions, not %d." % (total/2,
                                                                  count)
            )
        # Wait for the all the original sessions to expire.
        pause(ttl/2.0+0.1)
        # Create enough new sessions to force a background collection.
        configuration = self.session_manager.configuration()
        for i in range(0,int(configuration['_collection_threshold'])+1):
            self.session_manager.create('mpxadmin','mpxadmin',1)
        # Ensure that any pending background collection finishes.
        for i in range(0,10):
            if self.session_manager._collection_action is not None:
                # Allow the background collection to get scheduled.
                pause(0.1)
            else:
                break
        # Confirm that all the expired sessions were already collected.
        count = self.session_manager.collect()
        assert count == 0, (
            "Crossing the _collection_threshold did not cause the expected"
            " background collection.")
        return
