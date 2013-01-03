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
import copy

from mpx.lib import msglog

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.event import EventConsumerMixin

from mpx.lib.exceptions import EBreakupTransfer
from mpx.lib.exceptions import EIOError
from mpx.lib.exceptions import ENoData
from mpx.lib.exceptions import EUnreachableCode

from mpx.lib.log import LogAddEntryEvent

from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url

from mpx.lib.persistent import PersistentDataObject

from mpx.lib.threading import Lock
from mpx.lib.threading import Thread

from mpx.service.data import Exporter

##
# Could be the basis for an event driven exporter that only relies on the
# sequence (not timestamp)
class TrapExporter(Exporter,EventConsumerMixin):
    __node_id__ = '285ce258-af22-4a07-98d7-acecc2e33712'
    ##
    # @note Layers upon layers of locks is a bit annnoying.  Some day a nice
    #       layerred api with locking hints/keywords would be so nice...
    class SequenceStati(PersistentDataObject):
        def __init__(self, node):
            self.__lock = Lock()
            self.__last_save = {}
            self.max_seq = -1
            self.pending_seqs = []
            self.inprocess_seqs = []
            PersistentDataObject.__init__(self, node, auto_load=True)
            return
        def __snapshot(self, attrs):
            self.__last_save = {}
            for attr in attrs:
                self.__last_save[attr] = copy.copy(getattr(self,attr))
            return
        def __changed(self):
            if not self.__last_save:
                return True
            for attr in self.__last_save.keys():
                if not self.__last_save.has_key(attr):
                    return True
                if self.__last_save[attr] != getattr(self,attr):
                    return True
            return False
        def __load(self):
            result = PersistentDataObject.load(self)
            self.__snapshot(self.loaded())
            return result
        ##
        # @note Referrers should not call this method as the state is best
        #       maintained via the sequence processing methods:
        #       QUEUE_PENDING(), SEQUENCE_TO_PROCESS(), SEQUENCE_PROCESSED(),
        #       and SEQUENCES_PROCESSED().
        def load(self):
            self.__lock.acquire()
            try:
                return self.__load()
            finally:
                self.__lock.release()
            raise EUnreachableCode()
        def __save(self):
            result = PersistentDataObject.save(self)
            self.__snapshot(self.saved())
            return result
        ##
        # @note Referrers should not call this method as the state is best
        #       maintained via the sequence processing methods:
        #       QUEUE_PENDING(), SEQUENCE_TO_PROCESS(), SEQUENCE_PROCESSED(),
        #       and SEQUENCES_PROCESSED().
        def save(self):
            self.__lock.acquire()
            try:
                return self.__save()
            finally:
                self.__lock.release()
            raise EUnreachableCode()
        def __too_stale(self):
            return self.__changed() and True
        def __save_if_stale(self, force_save=False):
            if not force_save:
                force_save = self.__too_stale()
            if force_save:
                self.__save()
            return
        def save_if_stale(self):
            self.__lock.acquire()
            try:
                return self.__save_if_stale()
            finally:
                self.__lock.release()
            raise EUnreachableCode()
        ##
        # Add a sequence number to the pending queue.
        def __queue_pending(self, seq):
            if seq not in self.pending_seqs:
                self.pending_seqs.append(seq)
                self.pending_seqs.sort()
                if seq > self.max_seq:
                    self.max_seq = seq
            return
        ##
        # Add a sequence number to the pending queue.
        def queue_pending(self, seq):
            self.__lock.acquire()
            try:
                self.__queue_pending(seq)
            finally:
                self.__lock.release()
            return
        ##
        # Return (pop) the first sequence number from the pending queue,
        # and add it to the in-process queue.
        def sequence_to_process(self):
            self.__lock.acquire()
            try:
                if self.pending_seqs:
                    seq = self.pending_seqs.pop(0)
                    if seq not in self.inprocess_seqs:
                        self.inprocess_seqs.append(seq)
                    return seq
            finally:
                self.__lock.release()
            return None
        ##
        # Sequence was successfully processed (exported).
        def __sequence_processed(self, seq):
            if seq in self.pending_seqs:
                self.pending_seqs.remove(seq)
                pass # @fixme log weirdness.
            if seq not in self.inprocess_seqs:
                pass # #fixme Log wierdness.
            else:
                self.inprocess_seqs.remove(seq)
            return
        ##
        # Sequence was successfully processed (exported).
        # @note This commits changed to the PDO.
        def sequence_processed(self, seq):
            self.__lock.acquire()
            try:
                self.__sequence_processed(seq)
                self.__save_if_stale()
            finally:
                self.__lock.release()
            return
        ##
        # Sequences were successfully processed (exported).
        # @note This commits changed to the PDO.
        def sequences_processed(self, seqs):
            self.__lock.acquire()
            try:
                for seq in seqs:
                    self.__sequence_processed(seq)
                self.__save_if_stale()
            finally:
                self.__lock.release()
            return
        ##
        # Simulate pending sequence numbers for all sequence numbers that do
        # not appear to have been exported.
        # @note Consumer must deal with sequence numbers that they don't have
        #       in there event queue by looking them up in the Log.  In the
        #       case of looking up a sequence, consumers should call
        #       sequence_processed() if the sequence does not exist so this
        #       object knows not to simulate that number again.
        def __recover_pending(self, upto=-1):
            inprocess = self.inprocess_seqs
            self.inprocess_seqs = []
            self.pending_seqs.extend(inprocess)
            self.pending_seqs.sort()
            start_seq = self.max_seq + 1
            if self.pending_seqs:
                start_seq = max(start_seq, self.pending_seqs[-1]+1)
            for seq in range(start_seq, upto+1):
                self.__queue_pending(seq)
            return
        ##
        # Simulate pending sequence numbers for all sequence numbers that do
        # not appear to have been exported.
        def recover_pending(self, upto=-1):
            self.__lock.acquire()
            try:
                self.__recover_pending(upto)
            finally:
                self.__lock.release()
            return
        pass
    def __init__(self):
        self.running = 0
        self.log = None
        Exporter.__init__(self)
        EventConsumerMixin.__init__(self,self.handle_entry,self.handle_error)
    def debug_information(self,message):
        if self.debug:
            debug = '%s Exporter => %s' % (self.name,message)
            msglog.log('broadway',msglog.types.DB,debug)
    def handle_entry(self,event):
        self.debug_information('Log entry event caught.')
        self.debug_information('Going to start export thread.')
        self._seq_stati.queue_pending(event.seq)
        thread = Thread(name=self.name, target=self.go,args=(event,))
        thread.start()
        return
    def handle_error(self,exc):
        msglog.exception(exc)
        return
    def configure(self, config):
        set_attribute(self,'timeout',60,config,int)
        set_attribute(self,'connection_node','/services/network',config)
        set_attribute(self,'connection_attempts',3,config,int)
        set_attribute(self,'log_path','../..',config,
                      self.as_node_url)
        Exporter.configure(self, config)
    def configuration(self):
        config = Exporter.configuration(self)
        get_attribute(self,'connection_node',config)
        get_attribute(self,'connection_attempts',config)
        get_attribute(self,'timeout',config,int)
        get_attribute(self,'log_path',config,self.as_node_url)
        return config
    def start(self):
        Exporter.start(self)
        if not self.running:
            self.log = self.as_node(self.log_path)
            self.running = 1
            self.connection = as_node(self.connection_node)
            self._seq_stati = self.SequenceStati(self)
            self._seq_stati.load()
            self.log.event_subscribe(self, LogAddEntryEvent)
        else: 
            raise EAlreadyRunning
    def stop(self):
        self.running = 0
    def go(self, event):
        self.debug_information('Exporting.')
        self._export(event)
        self.debug_information('Done Exporting.')
        return
    def _export(self,event):
        attempts = 0
        connected = 0
        while attempts < self.connection_attempts:
            self.debug_information('Acquiring connection...')
            try:
                connected = self.connection.acquire()
            except:
                msglog.exception()
            if connected:
                self.debug_information('Connection acquired.')
                break
            self.debug_information('Failed to acquire.')
            attempts += 1
        else:
            self.debug_information('Connection failed, aborting.')
            raise EConnectionError('Failed to connect %s times' % attempts)
        try:
            #self.debug_information('Getting data from %s to %s.' 
            #                       % (start_time,end))
            # data = self.log.get_range('timestamp',start_time,end)
            names = self.log.get_column_names()
            assert len(names) == len(event.values)
            row = {}
            # row['_seq'] = event.seq
            i = 0
            for name in names:
                row[name] = event.values[i]
                i += 1
            data = (row,)
            self.debug_information('Calling format.')
            output = self.formatter.format(data)
            self.debug_information('Calling transport.')
            self.transporter.transport(output)
            self._seq_stati.sequence_processed(event.seq)
            self.debug_information('Done transporting.')
        finally:
            if connected:
                self.connection.release()
        return
