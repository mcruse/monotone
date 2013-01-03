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
import time, sys
from mpx.lib.exceptions import *
from mpx.ion import Result
from mpx.lib.exceptions import EBadBatch, Exception, MpxException,ETimeout
from mpx.lib import msglog
from mpx.lib import Callback

debug = 0

##
# A BatchManager represents a single thread of requests, batches are requested sequentially within a batch manager
class BatchManagerMixin:
    def get_batch(self, batch, *args, **keywords):
        return batch.get(self, *args, **keywords)
    ##
    #answer an array of Batches that get multiple values as a group, in modbus that matches up with a 'cache'
    #map is dictionary of id:node_reference of nodes
    #that use this batch manager
    #called from subscription manager when setting up the subscriptions and batches
    def create_batches(self, map):
        def _f(i): return (map[i].cache == cache) #filter for registers from the same cache
        answer = []
        ids = map.keys()
        #sort by object instances to collect multiple properties of an object together in sequential order
        ids.sort(lambda x,y: cmp(map[x].register,map[y].register)) 
        b = None
        flag = 0

        while(ids):
            try:
                while(ids):
                    id = ids[0] #get the first id in the key list
                    sid = id
                    cache = map[id].cache
                    sids = filter(_f, ids) #filter for just registers that are part of the same cache
                    for sid in sids: #add each one to a batch and remove it from the key list
                        if b is None:
                            b = Batch(cache, map)
                        b.add_id(sid)
                        ids.remove(sid)
                    if b:
                        answer.append(b)
                        b = None #force new batch
            except:
                if debug: msglog.exception()
                flag = 1
                n = map[sid]
                n.set_batch_manager(None)
                if sid in ids:
                    if debug:
                        print 'remove sid: %s' % (map[sid].as_node_url(),)
                    ids.remove(sid)
        if flag: 
            print 'raise EBadBatch'
            raise EBadBatch()
        self.__batches = answer #local copy for debuging
        if debug:
            print "Batch Manager create_batches: "
            for b in answer:
                print "  ", b
        return answer
    ##
    # name and instance attributes are set from mixed in class or explicitly (bacnet object ion)
    def _debug_get_batches(self, **keywords):
        answer = []
        for b in self.__batches:
            answer.append(self.get_batch(b, **keywords))
        return answer
##
# A Batch represent compatible requests joined together
#
class Batch(object):
    def __init__(self, cache, map):
        self.map = map #all points in all batches for the owning batchmanager
        self.ids = []
        self.cache = cache
        self.last_get_time = 0.0
        self._error_counter = 0

    def add_id(self, id):
        self.ids.append(id)
        
    def get(self, manager, **keywords):
        if debug: print 'Start of Batch:%s' % (self.properties)
        now = time.time()
        self.last_get_time = now
        answer = {} #return a dictionary of ids and results
        cache = self.cache
        cache.lock.acquire()
        try:
            try:
                if (cache.response is None) or \
                   ((cache.timestamp + cache.ttl) < time.time()):
                    cached = 0
                    cache._refresh()
                else:
                    cached = 1
                for id in self.ids:
                    ion = self.map[id]
                    result = Result()
                    result.timestamp = cache.timestamp
                    result.cached = cached
                    result.value = apply(ion.read, [cache.response,
                                                     ion.offset,
                                                     cache.start,
                                                     ion.orders])
                    answer[id]=result
                self._error_counter = 0
            except ETimeout, e:
                return e #subscription manager will re-raise the timeout, not cause for bad batch
            except:
                msglog.exception()
                self._error_counter += 1
                if self._error_counter > 15: #catch run away thrashing
                    for id in self.ids:
                        nr = self.map[id]
                        nr.set_batch_manager(None) #none of these points can batch
                    raise EBadBatch('bacnet', self, 'error threshold exceeded')
        finally:
            cache.lock.release()
        return answer

    def size(self):
        return len(self.ids)

    def __str__(self):
        answer = '  BATCH:\n'
        answer += '  ids:        %s\n' % (self.ids,)
        answer += '  nodes:\n'
        for i in self.ids:
            answer += '     %s' % (self.map[i],)
        answer += '  rpm errors: %s\n' % (self._error_counter)
        return answer

