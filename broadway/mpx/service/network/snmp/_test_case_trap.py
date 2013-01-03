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
import time

from mpx_test import DefaultTestFixture

#
# SequenceStati helper functions
#
def last_save(seq_pdo):
    return seq_pdo._SequenceStati__last_save
def changed(seq_pdo):
    return seq_pdo._SequenceStati__changed()

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        return
    def tearDown(self):
        try:
            pass
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_0_modules(self):
        import SNMP
        import remote_agent
        import smtp_formatter
        import trap_engine
        import trap_exporter
        import trap_log
        import trap_view
        return
    def test_seq_pdo_initial_state(self):
        import trap_exporter
        seq_pdo = trap_exporter.TrapExporter.SequenceStati('/bogus')
        # Confirm initial state:
        self.failIf(last_save(seq_pdo),
                    "New PDO should have {} for last_saved")
        self.failUnless(changed(seq_pdo),
                        "New PDO should be changed() do to empty last_save")
        return
    def test_seq_pdo_process_one_sequence(self):
        import trap_exporter
        seq_pdo = trap_exporter.TrapExporter.SequenceStati('/bogus')
        # Process single seq:
        seq_pdo.queue_pending(1)
        self.assert_comparison("seq_pdo.max_seq", "==", "1")
        next_seq = seq_pdo.sequence_to_process()
        self.assert_comparison("next_seq", "==", "1")
        self.assert_comparison("seq_pdo.pending_seqs", "==", "[]")
        self.assert_comparison("seq_pdo.inprocess_seqs", "==", "[1]")
        self.failUnless(changed(seq_pdo),
                        "PDO should be changed() since it has an outstanding "
                        "sequence.")
        seq_pdo.sequence_processed(next_seq)
        self.failIf(changed(seq_pdo),
                    "PDO should be NOT changed() since it has processed "
                    "the only outstanding sequence.")
        next_seq = seq_pdo.sequence_to_process()
        self.assert_comparison("seq_pdo.inprocess_seqs", "==", "[]")
        self.assert_comparison("next_seq", "==", "None")
        return
    def test_seq_pdo_load_test_1(self):
        import trap_exporter
        seq_pdo = trap_exporter.TrapExporter.SequenceStati('/bogus')
        # Process single seq:
        seq_pdo.queue_pending(1)
        next_seq = seq_pdo.sequence_to_process()
        seq_pdo.sequence_processed(next_seq)
        del seq_pdo
        # Reload PDO:
        seq_pdo = trap_exporter.TrapExporter.SequenceStati('/bogus')
        # Check assorted state information:
        self.failIf(changed(seq_pdo),
                    "Loaded PDO should NOT be changed()")
        self.assert_comparison("seq_pdo.pending_seqs", "==", "[]")
        self.assert_comparison("seq_pdo.inprocess_seqs", "==", "[]")
        self.assert_comparison("seq_pdo.max_seq", "==", "1")
        next_seq = seq_pdo.sequence_to_process()
        self.assert_comparison("next_seq", "==", "None")
        return
    def test_seq_pdo_process_multiple_sequence_1(self):
        import trap_exporter
        seqs_source = (1, 10, 5, 7, 3, 2, 4, 6, 8, 9,)
        seqs_sorted = list(seqs_source)
        seqs_sorted.sort()
        seq_pdo = trap_exporter.TrapExporter.SequenceStati('/bogus')
        # Queue seqs 1-10 out of order:
        for seq in seqs_source:
            seq_pdo.queue_pending(seq)
        # pending [] logically simulates seq_pdo.pending_seqs
        pending = list(seqs_sorted)
        self.assert_comparison("seq_pdo.pending_seqs", "==", "seqs_sorted")
        # inprocess [] logically simulates seq_pdo.inprocess
        inprocess = []
        for i in range(1,6):
            next_seq = seq_pdo.sequence_to_process()
            self.assert_comparison("i", "==", "next_seq")
            inprocess.append(next_seq)
            pending.remove(next_seq)
        self.assert_comparison("seq_pdo.inprocess_seqs", "==", "inprocess")
        # processed [] represents the seqs that have been sequence_processed()
        processed = []
        # Proces an out of order seq (4,5):
        next_seq = inprocess.pop(-1)
        seq_pdo.sequence_processed(next_seq)
        processed.append(next_seq)
        next_seq = inprocess.pop(-1)
        seq_pdo.sequence_processed(next_seq)
        processed.append(next_seq)
        self.failUnless(seq_pdo.inprocess_seqs == inprocess,
                        "Logic Failed: Expected inprocess_seqs(%r) == [%r]" %
                        (seq_pdo.inprocess_seqs, inprocess))
        self.assert_comparison("seq_pdo.inprocess_seqs", "==", "inprocess")
        # Should have persisted:
        del seq_pdo
        seq_pdo = trap_exporter.TrapExporter.SequenceStati('/bogus')
        # This test will fail if recover_pending is integrated with
        # instanciation.
        self.assert_comparison("seq_pdo.inprocess_seqs", "==", "inprocess")
        # OK, 4 and 5 were processed.  Process 10 out of order as well:
        seq_pdo.sequence_processed(10)
        pending.remove(10)
        processed.append(10)
        self.assert_comparison("seq_pdo.pending_seqs", "==", "pending")
        # OK, pretend we are reloading the PDO, all unconfirmed seqs UPTO the
        # current Log's _seq must be assumed to be pending (NOT exported):
        del seq_pdo
        seq_pdo = trap_exporter.TrapExporter.SequenceStati('/bogus')
        seq_pdo.recover_pending(15)
        # All inprocess seqs must be assumed NOT exported:
        while inprocess:
            pending.append(inprocess.pop())
        # All Log _seqs > max_seq MUST be assumed NOT exported:
        pending.extend(range(11,15+1))
        pending.sort()
        # pending = [1, 2, 3,   : 4 and 5 processed after sequence_to_process()
        #            6, 7, 8, 9,: 10 processed without sequence_to_process()
        #            11, 12, 13, 14, 15] : 11-15 added by recover_pending(15)
        self.assert_comparison("seq_pdo.inprocess_seqs", "==", "inprocess")
        self.assert_comparison("seq_pdo.pending_seqs", "==", "pending")
        return
    def test_log(self):
        import _test_lib
        log = _test_lib.trap_log_factory()
        log.start()
        log.stop()
        return
    def test_exporter_v1(self):
        import _test_lib
        log = _test_lib.trap_log_factory()
        exporter = _test_lib.trap_exporter_factory(parent=log)
        log.start()
        self.assert_comparison("tuple(self.msglog_object[:])", "==", "()")
        version='1'
        context_engine_id='bogus-id'
        context_name='bogus-context'
        address='192.168.1.1'
        sysUpTime='1 day 03:04:05.06'
        trap='Test-MIB::logTestTrap'
        trap_enterprise='Test-MIB::RZ'
        varBinds=(('Test-MIB::Payload', 0),)
        logtime=time.time()
        log.log_trap(version, context_engine_id, context_name, address,
                     sysUpTime, trap,
                     trap_enterprise,
                     varBinds,
                     logtime)
        from mpx.lib import pause
        pause(1)
        log.stop()
        self.assert_comparison("tuple(self.msglog_object[:])", "==", "()")
        return
