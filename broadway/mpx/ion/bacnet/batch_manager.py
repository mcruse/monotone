"""
Copyright (C) 2005 2006 2007 2008 2010 2011 Cisco Systems

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
from mpx.lib.bacnet._bacnet import _read_property_multiple_g3 as rpm
from mpx.lib.bacnet._exceptions import *
from mpx.ion import Result
from mpx.lib.bacnet.network import device_accepts_rpm
from mpx.lib.bacnet import sequence
from mpx.lib.bacnet.data import BACnetObjectIdentifier
from mpx.lib.exceptions import EBadBatch, Exception, MpxException,ETimeout
from mpx.lib import msglog
from mpx.lib.bacnet.sequence import _OPTIONAL as OPTIONAL
from mpx.lib import Callback

debug = 0

BATCH_MAX_SIZE = 32


##
# A BatchManager represents a single thread of requests
class BatchManagerMixin:
    def get_batch(self, batch, *args, **keywords):
        return batch.get(self, *args, **keywords)
    ##
    #map is dictionary of id:node_reference of nodes
    #that use this batch manager
    def create_batches(self, map):
        def _f(i): return (map[i]._comm3segment() == segment) and (map[i].get_obj_instance() == obj_instance)
        answer = []
        self.array_batches = {}
        ids = map.keys()
        #sort by object instances to collect multiple properties of an object together in sequential order
        ids.sort(lambda x,y: cmp(map[x].get_obj_instance(),map[y].get_obj_instance())) 
        b = None
        flag = 0

        while(ids):
            try:
                while(ids):
                    id = ids[0] #get the first id in the key list
                    sid = id
                    segment = map[id]._comm3segment() #get it's segment number
                    obj_instance = map[id].get_obj_instance()
                    timeout = 6.0
                    if segment:
                        timeout = 12.0
                    if self.device_info and self.device_info.vendor_id == 2: #Trane
                        sids = filter(_f, ids) #filter for just matching segment numbers for trane
                    else:
                        sids = ids[:]
                    for sid in sids: #add each one to a batch and remove it from the key list
                        if hasattr(map[sid], 'is_array') and map[sid].is_array(): #array property that uses rpm only (like trane)
                            ba = self.get_array_batch_for(map[sid], map, timeout)
                            ba.add_id(sid)
                            #answer.append(ba)  handled later
                            ids.remove(sid)
                        elif hasattr(map[sid], 'is_array_element_of') and map[sid].is_array_element_of():
                            ba = self.get_array_batch_for(map[sid].is_array_element_of(), map, timeout)
                            ba.add_id(sid)
                            ids.remove(sid)
                            
                        else: #handle regular non-array type node
                            if b is None:
                                b = Batch(self.instance, map, timeout)
                            b.add_id(sid)
                            ids.remove(sid)
                            if b.size() > BATCH_MAX_SIZE:
                                answer.append(b)
                                b = None
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
        answer.extend(self.array_batches.values())  #add all the BatchArray objects
        for b in answer:
            b._init_props()
        self._batches = answer #local copy for debuging
        if debug:
            print "Batch Manager create_batches: "
            for b in answer:
                print "  ", b
        return answer
    def get_array_batch_for(self, node, map, timeout):
        if self.array_batches.has_key(node):
            return self.array_batches[node]
        ba = BatchArray(self.instance, map, timeout)
        self.array_batches[node] = ba
        return ba
            
        
    ##
    # name and instance attributes are set from mixed in class or explicitly (bacnet object ion)
    def _debug_get_batches(self, **keywords):
        answer = []
        for b in self._batches:
            answer.append(self.get_batch(b, **keywords))
        return answer
##
# A Batch represent compatible requests joined together
#
class Batch(object):
    def __init__(self, device, map, timeout):
        self.map = map
        self.properties = []
        self.device = None
        self.prop2id = {}
        self.ids = []
        self.device = device
        self.timeout = timeout
        self.total_rpm_error_counter = 0
        self.last_get_time = 0.0
        self.refresh_enabled = 0

    def add_id(self, id):
        self.ids.append(id)
        
    def _init_props(self):
        self.prop2id = {}
        for id in self.ids:
            nr = self.map[id]
            self.prop2id[nr.get_property_tuple()] = id
        props = {}
        for p in self.prop2id.keys():
            k = p[:2] #k = type, object.instance,
            if not props.has_key(k):
                props[k]=[] #add a list object to hold the properties from this object
            props[k].append(p[2]) #add a property to the list for one object
        self.properties = []
        for p in props.keys():
            self.properties.append(p+(tuple(props[p]),)) #ex: (151, 1,(85, 87,))
        if debug:
            print str(self.properties)

    def get(self, manager, **keywords):
        if debug: print 'Start of Batch:%s' % (self.properties)
        now = time.time()
        self.last_get_time = now
        callback = None
        if keywords.has_key('callback'):
            keywords['callback'].callback(self.rpm_callback)
        try:
            #print 'Calling read property multiple'   
            rars = rpm(self.device, self.properties, self.timeout, **keywords)
            if isinstance(rars, Callback):
                return rars #if we are in callback mode
            #print 'RPM TIME:%s' % (time.time()-now,)
        except BACnetException, e:
            if len(self.ids) == 1: #single propety rpms throw exceptions at this level
                return {self.ids[0]: e} #simply return exception as the result
            self.total_rpm_error_counter += 1
            if self.total_rpm_error_counter > 0: #catch run away thrashing
                for id in self.ids:
                    nr = self.map[id]
                    nr.set_batch_manager(None) #none of these points can batch
                raise EBadBatch('bacnet', self, 'error threshold exceeded')
            #at this point this is a multiple property read that failed
            msglog.exception()
            if debug: print 'rpm failed, trying rp', str(self.properties)
            answer = {}
            for id in self.ids:
                nr = self.map[id]
                result = nr.get_result()
                answer[id] = result
                if isinstance(result.value.value, BACnetError):
                    nr.set_batch_manager(None) #turn off rpm for the offending property
                    msglog.log('bacnet', nr.as_node_url(), 'cannot get multiple')
                    if debug: msglog.exception()
            raise EBadBatch('bacnet', self, 'rpm failed')
        except:
            msglog.exception()
            self.total_rpm_error_counter += 1
            if self.total_rpm_error_counter > 0: #catch run away thrashing
                for id in self.ids:
                    nr = self.map[id]
                    nr.set_batch_manager(None) #none of these points can batch
                raise EBadBatch('bacnet', self, 'error threshold exceeded')
            raise #whatever the actual error was

        self.total_rpm_error_counter = 0 #one good read resets thrashing counter
        answer = {}
        for ps in self.properties: #[(obj type, instance, (pids,)),]
            rar = rars.pop(0)
            lrs = rar.list_of_results
            for p in ps[2]: #pids tuple
                id = None
                nr = None
                try:
                    lr = lrs.pop(0)
                    pe = lr.property_access_error
                    self.pe = pe #take this out
                    pv = lr.property_value
                    self.pv = pv #same here
                    id = self.prop2id[ps[:2] + (p,)]
                    nr = self.map[id]
                    value = None
                    if not isinstance(pv, OPTIONAL):
                        value = nr.decoder().decode(pv)
                    elif not isinstance(pe, OPTIONAL):
                        if debug: msglog.log('bacnet', nr.as_node_url(), str(pe))
                        value = BACnetRpmRarError('batch', nr.as_node_url(), str(pe))
                    else:
                        raise EUnreachableCode
                except Exception, e:
                    if debug: 
                        msglog.exception()
                        msglog.log('bacnet', nr.name, 'exception doing rpm response list')
                    value = e
                if id:
                    if nr.hasattr('is_binary_pv'):
                        if nr.is_binary_pv():
                            value = int(value)
                    elif nr.hasattr('_is_binary_type'):
                        if nr._is_binary_type():
                            value = int(value)
                    answer[id] = Result(value, now)
        #print 'Answer:%s' % (str(answer),)
        if debug: print 'Batch Time:%s %s' % (self.properties, time.time() - self.last_get_time,) 
        return answer
    def rpm_callback(self, rars):  #called all the way from the TSM callback upon completion
        try:
            now = time.time()
            if isinstance(rars, Exception):
                raise rars
            self.total_rpm_error_counter = 0 #one good read resets thrashing counter
            answer = {}
            for ps in self.properties: #[(obj type, instance, (pids,)),]
                rar = rars.pop(0)
                lrs = rar.list_of_results
                for p in ps[2]: #pids tuple
                    id = None
                    nr = None
                    try:
                        lr = lrs.pop(0)
                        pe = lr.property_access_error
                        self.pe = pe #take this out
                        pv = lr.property_value
                        self.pv = pv #same here
                        id = self.prop2id[ps[:2] + (p,)]
                        nr = self.map[id]
                        value = None
                        if not isinstance(pv, OPTIONAL):
                            value = nr.decoder().decode(pv) #use bacnet_property to decode
                        elif not isinstance(pe, OPTIONAL):
                            if debug: msglog.log('bacnet', nr.as_node_url(), str(pe))
                            value = BACnetRpmRarError('batch', nr.as_node_url(), str(pe))
                        else:
                            return EUnreachableCode()
                    except Exception, e:
                        if debug: 
                            msglog.exception()
                            msglog.log('bacnet', nr.as_node_url(), 'exception doing rpm response list')
                        value = e
                    if id:
                        if nr.hasattr('is_binary_pv'):
                            if nr.is_binary_pv():
                                value = int(value)
                        elif nr.hasattr('_is_binary_type'):
                            if nr._is_binary_type():
                                value = int(value)
                        answer[id] = Result(value, now)                        
            #print 'Answer:%s' % (str(answer),)
            if debug: print 'Batch Callback Time:%s %s' % (self.properties, time.time() - self.last_get_time,) 
            return answer
        except BACnetException, e:  #total rpm exception
            try:
                if isinstance(e,BACnetError):
                    if e.npdu.data[1] == 5 and e.npdu.data[3] == 0:
                        return ETimeout("Missing comme device")
            except Exception,ERROR:
                msglog.exception()
                pass
            if len(self.ids) == 1: #single propety rpms throw exceptions at this level
                return {self.ids[0]: e}
            self.total_rpm_error_counter += 1
            #at this point this is a multiple property read that failed
            #msglog.exception()
            if debug: print 'rpm failed, trying rp', str(self.properties)
            answer = {}
            for id in self.ids:
                nr = self.map[id]
                nr.set_batch_manager(None) #turn off rpm for the offending property
                msglog.log('bacnet', nr.as_node_url(), 'cannot get multiple')
                if debug: msglog.exception()
            return EBadBatch('bacnet', self, 'rpm failed')
        except Exception, e: #any other exception
            if debug: msglog.exception()
            return e
        except:
            return Exception(sys.exc_info()[0])

    def size(self):
        return len(self.ids)
    def __str__(self):
        answer = '  BATCH:\n'
        answer += '  properties: %s\n' % (self.properties,)
        answer += '  device:     %s\n' % (self.device,)
        answer += '  ids:        %s\n' % (self.ids,)
        answer += '  nodes:\n'
        for i in self.ids:
            answer += '     %s' % (self.map[i],)
        answer += '  rpm errors: %s\n' % (self.total_rpm_error_counter)
        return answer

class BatchArray(Batch):
    def _init_props(self):
        nr = self.map[self.ids[0]]
        self.array_node = nr
        if hasattr(nr, 'is_array') and nr.is_array(): return
        if hasattr(nr, 'is_array_element_of') and nr.is_array_element_of():
            self.array_node = nr.is_array_element_of()
        #survive this even if array_node is bogus, catch it in the get

    def get(self, manager, **keywords):
        if debug: print 'Start of Batch:%s' % (self.array_node.as_node_url())
        now = time.time()
        self.last_get_time = now
        answer = {}
        if not self.array_node.is_array():
            #mark all ids bad and throw exception
            for id in self.ids:
                nr = self.map[id]
                nr.set_batch_manager(None) #turn off rpm for the offending property
            raise EBadBatch('bacnet', self.array_node.name, 'array node is NOT an array')

        if keywords.has_key('callback'):
            keywords['callback'].callback(self.rpm_callback)
            keywords['T_OUT'] = self.timeout
        try:            
            array_value = self.array_node.get_result(1, **keywords)
            if isinstance(array_value, Callback):
                return array_value #if we are in callback mode
        except Exception, e:
            if debug: msglog.exception()
            for id in self.ids:
                answer[id] = Result(e, now)
            return answer
        
        if isinstance(array_value,Result):
            if isinstance(array_value.value,Exception):
                for id in self.ids:
                    answer[id] = Result(array_value.value, now)
                return answer
      
        for id in self.ids:
            nr = self.map[id]
            try:
                if nr.is_array():
                    answer[id] = Result(array_value.value, array_value.timestamp) #should just be one of these
                else:
                    answer[id] = Result(array_value.value[nr.index], array_value.timestamp)
            except Exception, e:
                answer[id] = Result(e, now)
        if debug: print 'Batch Time:%s %s' % (self.array_node.as_node_url(), time.time() - self.last_get_time,) 
        return answer

    def rpm_callback(self, array_value):
        #if debug: print 'batch array callback entry: %s' % (self,)
        now = time.time()
        try:
            answer = {}
            if isinstance(array_value, Exception):  #if we enter with an exception, disperse it to all the array elements
                for id in self.ids:
                    answer[id] = Result(array_value, now)
                return answer
            if isinstance(array_value,Result):
                if isinstance(array_value.value,Exception):
                    for id in self.ids:
                        answer[id] = Result(array_value.value, now)
                    return answer
            for id in self.ids:
                nr = self.map[id]
                try:
                    if nr.is_array():                   
                        answer[id] = Result(array_value.value, array_value.timestamp) #should just be one of these
                    else:
                        answer[id] = Result(array_value.value[nr.index], array_value.timestamp)
                except Exception, e:
                    answer[id] = Result(e, now)
            if debug: print 'Batch Callback Time:%s %s' % (self.array_node.as_node_url(), time.time() - self.last_get_time,) 
            return answer
        except BACnetError,e:
            try:
                if e.npdu.data[1] == 5 and e.npdu.data[3] == 0:
                    return ETimeout("Missing comme device")
            except:
                pass
            return e
        except Exception, e: #any other exception
            if debug: msglog.exception()
            return e
        except:
            if debug: print 'batch array unknown exception'
            return Exception(sys.exc_info()[0])
    def __str__(self):
        answer = Batch.__str__(self)
        return ' ARRAY' + answer