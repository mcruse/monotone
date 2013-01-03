"""
Copyright (C) 2002 2003 2004 2005 2006 2007 2010 2011 Cisco Systems

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
# @fixme Add subscribe on consumer as well.
import weakref
import inspect

from mpx.lib.exceptions import *
from mpx.lib import UniqueToken

from mpx.lib.threading import Lock
from mpx.lib import Result

def msglog():
    # Defer import because logging can generate events.  Reentrancy issues?
    from mpx.lib import msglog as _msglog
    return _msglog

class EDestroyed(Exception):
    pass

class DeReferenceable:
    def __init__(self,obj):
        self._obj = obj
    def __call__(self):
        return self._obj
class CallbackMixin:
    debug = 1
    class Registrant:
        def __init__(self,identifier,unregister,
                     callback,consumer,args,keywords):
            self._identifier = identifier
            self._unregister = unregister
            self._callback = callback
            self._consumer = consumer
            self._destroyed = []
            if consumer is not None:
                self._consumer = weakref.ref(consumer,self._destroyed.append)
            self._args = args
            self._keywords = keywords
            self._filters = []
            self._rid = id(self)
            self.__rid_only = 0
        def callback(self):
            return self._callback
        def rid_only(self,rid_only=None):
            if rid_only is not None:
                self.__rid_only = rid_only
            return self.__rid_only
        def rid(self):
            return self._rid
        def identifier_mro(self):
            if not inspect.isclass(self.identifier()): return None
            return inspect.getmro(self.identifier())
        def identifier(self): return self._identifier
        def filters(self): return self._filters
        def consumer(self):
            if not self._consumer: return None
            return self._consumer()
        def validated_consumer(self):
            consumer = self.consumer()
            if self._consumer and not consumer:
                raise EDestroyed(self)
            return consumer
        def __eq__(self,other):
            return isinstance(other,self.__class__) and (
                    self.identifier() is other.identifier() and 
                    self.consumer() is other.consumer() and
                    self.callback() is other.callback())
        def has_consumer(self,consumer):
            if not self.consumer(): return None
            return self.consumer() is consumer
        def remove_filter(self,filter):
            return self._filters.remove(filter)
        def has_filter(self,filter):
            return filter in self._filters
        def is_target(self,object,filter=None):
            if self._destroyed:
                raise EDestroyed(self)
            if filter is not None and filter not in self._filters:
                return 0
            return (object is self.identifier() or 
                    object == self.identifier() or 
                    isinstance(object,self.identifier()))
        def is_registration(self,identifier,consumer):
            return (identifier is self.identifier()) and (
                    consumer is self.consumer())
        def add_filter(self,filter):
            if filter not in self._filters:
                self._filters.append(filter)
        def destroy(self,*args):
            self._unregister(self.rid())
            self._destoyed.append(True)
        def __call__(self,*args,**keywords):
            if self._destroyed:
                raise EDestroyed(self)
            args = list(args + self._args)
            keywords = keywords and dict(keywords)
            if self._consumer: args.insert(0,self.validated_consumer())
            if self._keywords: keywords.update(self._keywords)
            return self._callback(*args,**keywords)
    def __init__(self):
        self.__lock = Lock()
        self.__rids = {}
        self.__identifiers = {}
        self.__rid_filters = {}
        self.__class_cache = {}
        self.__consumers = weakref.WeakKeyDictionary()
        self.__pending = []
    def db(self,level):
        return level <= self.debug
    def output(self,message):
        msglog().log('broadway',msglog().types.DB,'%s: %s' % (self,message))
    def listen_for_isinstance(self,identifier,callback,*args,**keywords):
        raise ENotImplemented(self.listen_for_instance)
    def listen_for_issubclass(self,identifier,callback,*args,**keywords):
        raise ENotImplemented(self.listen_for_instance)
    def listen_for_value(self,identifier,callback,*args,**keywords):
        raise ENotImplemented(self.listen_for_value)
    def listen_for_id(self,identifier,callback,*args,**keywords):
        raise ENotImplemented(self.listen_for_id)
    def listen_for_rid(self,callback,*args,**keywords):
        self._commit_pending(1)
        consumer,callback = self.__breakup_callback(callback)
        registrant = self.Registrant(None,self.unregister,
                                     callback,consumer,args,keywords)
        registrant.rid_only(1)
        self.__pending.append((self.__add_registrant,(registrant,)))
        self._commit_pending(0)
        return registrant.rid()
    def listen_for_like(self,identifier,callback,*args,**keywords):
        self._commit_pending(1)
        consumer,callback = self.__breakup_callback(callback)
        registrant = self.Registrant(identifier,self.unregister,
                                     callback,consumer,args,keywords)
        rids = self.registrant_ids()
        for rid in rids:
            if self.registrant(rid) == registrant:
                raise Exception('Registrant must be unique')
        self.__pending.append((self.__add_registrant,(registrant,)))
        self._commit_pending(0)
        return registrant.rid()
    register = listen_for_like
    def __breakup_callback(self,callback):
        consumer = None
        if inspect.ismethod(callback):
            if callback.im_self is not None:
                consumer = callback.im_self
                callback = callback.im_func
            elif args and isinstance(args[0],callback.im_class):
                consumer = args[0]
                args = args[1:]
                callback = callback.im_func
        return (consumer,callback)
    def _commit_pending(self,wait=0):
        if self.__pending and self.__lock.acquire(wait):
            try:
                while self.__pending:
                    action,args = self.__pending.pop(0)
                    try: action(*args)
                    except:
                        msglog().exception(prefix='Handled')
            finally: self.__lock.release()
        return len(self.__pending)
    def __add_registrant(self,registrant,rid_only=0):
        rid = registrant.rid()
        self.__rids[rid] = registrant
        if not registrant.rid_only():
            identifier = registrant.identifier()
            if not self.__identifiers.has_key(identifier):
                self.__identifiers[identifier] = []
            self.__identifiers[identifier].append(rid)
            mro = registrant.identifier_mro()
            if mro is not None:
                for classobj in mro:
                    if not self.__class_cache.has_key(classobj):
                        self.__class_cache[classobj] = []
                    if rid not in self.__class_cache[classobj]:
                        self.__class_cache[classobj].append(rid)
            consumer = registrant.consumer()
            if consumer:
                if not self.__consumers.has_key(consumer):
                    self.__consumers[consumer] = []
                self.__consumers[consumer].append(rid)
        self.registrant_added(rid)
    def __remove_registrant(self,rid):
        registrant = self.registrant(rid)
        if registrant is None:
            msglog().log('broadway',msglog().types.INFO,
                       'RID "%s" does not exist.  Nothing removed.' % (rid,))
            return
        actions = [(self.__rids.pop,(registrant.rid(),))]
        if not registrant.rid_only():
           actions.append((self.__clear_from_identifiers,(registrant,)))
           actions.append((self.__clear_from_consumers,(registrant,)))
           actions.append((self.__clear_from_filters,(registrant,)))
           actions.append((self.__clear_from_caches,(registrant,)))
        for action,args in actions:
            try:
                action(*args)
            except:
                msglog().exception(prefix='Handled')
        self.registrant_removed(rid)
    def __clear_from_identifiers(self,registrant):
        rid = registrant.rid()
        identifier = registrant.identifier()
        if identifier is not None and self.__identifiers.has_key(identifier):
            if rid in self.__identifiers[identifier]:
                if len(self.__identifiers[identifier]) == 1:
                    del(self.__identifiers[identifier])
                else: self.__identifiers[identifier].remove(rid)
    def __clear_from_filters(self,registrant):
        rid = registrant.rid()
        for filter in registrant.filters():
            if (self.__rid_filters.has_key(filter) and 
                rid in self.__rid_filters[filter]):
                try: 
                    if len(self.__rid_filters[filter]) == 1:
                        del(self.__rid_filters[filter])
                    else: self.__rid_filters[filter].remove(rid)
                except:
                    msglog().exception(prefix='Handled')
    def __clear_from_caches(self,registrant):
        mro = registrant.identifier_mro()
        if mro is None: return
        rid = registrant.rid()
        for classobj in mro:
            if (self.__class_cache.has_key(classobj) and 
                rid in self.__class_cache[classobj]):
                self.__class_cache[classobj].remove(rid)
                if not len(self.__class_cache[classobj]): 
                    del(self.__class_cache[classobj])
        return
    def __clear_from_consumers(self,registrant):
        rid = registrant.rid()
        consumer = registrant.consumer()
        if consumer is not None and self.__consumers.has_key(consumer):
            if rid in self.__consumers[consumer]: 
                self.__consumers[consumer].remove(rid)
            if not self.__consumers[consumer]: del(self.__consumers[consumer])
    def registrant_count(self,filter=None):
        self._commit_pending(0)
        if filter is not None:
            if self.__rid_filters.has_key(filter):
                return len(self.__rid_filters[filter])
            return 0
        return len(self.__rids)
    def registrant_added(self,rid):
        return
    def registrant_removed(self,rid):
        return
    def registrant_ids(self,filter=None):
        self._commit_pending(0)
        if filter is not None:
            if not self.__rid_filters.has_key(filter): return []
            else: return self.__rid_filters[filter]
        return self.__rids.keys()
    def clear(self):
        self._commit_pending(1)
        rids = self.registrant_ids()
        for rid in rids:
            self.unregister(rid,0)
        if rids: self._commit_pending(0)
    def unregister(self,rid,commit=1):
        self.__pending.append((self.__remove_registrant,(rid,)))
        if commit: self._commit_pending(0)
    def unregister_consumer(self,consumer,filter=None):
        unregister = []
        self._commit_pending(1)
        registrant_ids = self.registrant_ids(filter)
        rids = self.__consumers[consumer]
        if filter is not None:
            if self.__rid_filters.has_key(filter):
                rids = list(set(rids).intersection(self.__rid_filters[filter]))
            else: rids = []
        for rid in rids: self.unregister(rid,0)
        if rids: self._commit_pending(0)
        else: 
            msglog().log('broadway',msglog().types.DB,
                       'No RIDs unregistered for consumer: %s' % (consumer,))
    def registrant(self,rid,raise_exc=0):
        if isinstance(rid,self.Registrant): return rid
        if type(rid) is not int: raise ValueError(rid,'Must be int.')
        self._commit_pending(0)
        if self.__rids.has_key(rid): return self.__rids[rid]
        elif raise_exc: raise ValueError(rid)
        else: return None
    def registrants(self,rids,raise_exc=0):
        return map(self.registrant,rids)
    def rid(self,registrant):
        return self.registrant(registrant).rid()
    def rids(self,registrants):
        return map(self.rid,registrants)
    def associated_registrants(self,filter,raise_exc=0):
        self._commit_pending(0)
        if not raise_exc and not self.__rid_filters.has_key(filter):
            return []
        return self.__rid_filters[filter]
    def create_association(self,filter,rid,single=0):
        self._commit_pending(1)
        registrant = self.registrant(rid,1)
        if self.__rid_filters.has_key(filter):
            raise ValueError(filter,'Must be unique')
        self.__pending.append((registrant.add_filter,(filter,)))
        value = ([rid],(rid,))[single]
        self.__pending.append((self.__rid_filters.update,({filter:value},)))
        self._commit_pending(0)
    def create_single_association(self,filter,rid):
        return self.create_association(filter,rid,1)
    def add_association(self,filter,rid):
        if not self.__rid_filters.has_key(filter):
            self.create_association(filter,rid,0)
        elif rid not in self.__rid_filters[filter]:
            self._commit_pending(1)
            registrant = self.registrant(rid,1)
            self.__pending.append((registrant.add_filter,(filter,)))
            self.__pending.append((self.__rid_filters[filter].append,(rid,)))
            self._commit_pending(0)
    def remove_association(self,filter,rid,raise_exc=0):
        self._commit_pending(1)
        registrant = self.registrant(rid,raise_exc)
        if registrant is None: return
        if registrant.has_filter(filter):
            self.__pending.append((registrant.remove_filter,(filter,)))
        if self.__rid_filters.has_key(filter) and rid in self.__rid_filters[filter]:
            if len(self.__rid_filters[filter]) == 1:
                self.__pending.append((self.__rid_filters.pop,(filter,)))
            else: self.__pending.append((self.__rid_filters[filter].remove,(rid,)))
        self._commit_pending(0)
    def distribute_filtered(self,instance,filter=None,*args,**keywords):
        return self._distribute(instance,filter,*args,**keywords)
    distribute = distribute_filtered
    def distribute_unfiltered(self,instance,*args,**keywords):
        return self._distribute(instance,None,*args,**keywords)
    def notify_rids(self,rids,*args,**keywords):
        for rid in rids: self.notify_rid(rid,*args,**keywords)
    def notify_rid(self,rid,*args,**keywords):
        try: self.__notify_rid(rid,args,keywords)
        except EDestroyed: self.unregister(rid)
        else: return 1
        return 0
    def __notify_rid(self,rid,args,keywords,raise_exc=0):
        registrant = self.registrant(rid,raise_exc)
        return registrant and registrant(*args,**keywords)
    def _distribute(self,instance,filter,*args,**keywords):
        self._commit_pending(1)
        args = args or (instance,)
        rids,classobj,loop_targets = [],None,True
        if self.__identifiers.has_key(instance):
            rids = self.__identifiers[instance]
            loop_targets = False
        elif hasattr(instance,'__class__'):
            classobj = instance.__class__
            rids = self.__class_cache.setdefault(classobj,[])
            if rids: loop_targets = False
        remove = []
        if loop_targets:
            for rid in self.registrant_ids():
                registrant = self.registrant(rid)
                if registrant and not registrant.rid_only():
                    try:
                        if registrant.is_target(instance):
                            rids.append(rid)
                    except EDestroyed: remove.append(rid)
                    except:
                        self.output('Error. Removing RID(%s)' % rid)
                        msglog().exception()
                        remove.append(rid)
        if filter is not None:
            rids = list(set(self.registrant_ids(filter)).intersection(rids))
        total,succeeded,removed,failed = len(rids),0,0,0
        execute = rids[:]
        for rid in execute:
            try:
                self.__notify_rid(rid,args,keywords)
                succeeded += 1
            except EDestroyed: remove.append(rid)
            except:
                failed += 1
                msglog().exception(prefix='Handled')
        if remove:
            self.db(2) and self.output(
                'distribute() unregistering Rids: %s' % (remove,))
            for rid in remove:
                try:
                    self.unregister(rid)
                except:
                    msglog().exception(prefix='Handled')
                else: removed += 1
        return {'Total':total,'Successful':succeeded,
                'Failures':failed,'Removed':removed}
    # Here for compatibility with EventProducerMixin
    def event_subscribe(self,consumer,event_class,**keywords):
        self.register(event_class,consumer.event_handler,isinstance,**keywords)
    def event_unsubscribe(self,consumer,event_class,**keywords):
        self._commit_pending(1)
        for rid in self.registration_ids():
            registrant = self.registrant(rid)
            if registrant.is_registration(event_class,consumer):
                return self.unregister(rid)
    def event_generate(self,event):
        self.distribute(event)

##
# The bases for a simple event subscription and delivery system for the
# framework.

class EEvent(MpxException):
    ##
    # @param event The Event object associated with the exception.
    # @default None
    # @param uid The UID of the Event object associated with the exception.
    # @default None
    # @para *args  Passed up to <code>MpxException</code>'s contructor.
    # @default None
    # @keywords    Passed on to <code>MpxException</code>'s contructor.
    # @default None
    def __init__(self, *args, **keywords):
        if len(args) and isinstance(args[0],Event):
            self.event = args[0]
            args = args[1:]
        else:
            self.event = None # No event that I'm aware of...
        if len(args) and isinstance(args[0],UniqueToken):
            self.uid = args[0]
            args = args[1:]
        else:
            self.uid = None # No UID that I'm aware of...
        MpxException.__init__(self, *args, **keywords)
    def __str__(self):
        if not len(self.args) and (self.event is not None
                                   or self.uid is not None):
            self.args = []
            if self.event is not None:
                self.args.append(self.event)
            if self.uid is not None:
                self.args.append(self.uid)
        return MpxException.__str__(self)

##
# An attempt was made to insert a duplicate subscription in the subscription
# queue.
# @param consumer
# @default None
class EEventCollision(EEvent):
    def __init__(self, *args, **keywords):
        if (len(args)
            and hasattr(args[0], 'event_handler')
            and hasattr(args[0], 'event_exception')):
            self.consumer = args[0]
            args = args[1:]
        else:
            self.consumer = None # No consumer that I'm aware of...
        EEvent.__init__(self, *args, **keywords)
    def __str__(self):
        if len(self.args):
            return EEvent.__str__(self)
        if self.event is not None:
            return ('The %s Event instance is already in the' +
                    ' subscribtion list.') % self.event
        if self.uid is not None:
            return ('An Event with the same UID (%s) is already' +
                    ' in the subscribtion list.') % self.event
        return ('An Event with either the same instance id or' +
                ' unique id (UID) is already in the subscribtion list.')

class EEventNotInQ(EEvent):
    def __str__(self):
        if len(self.args):
            return EEvent.__str__(self)
        if not self.event:
            return ('Event not in the subscribtion list.')
        elif isinstance(self.event, Event):
            return 'The %s Event not in the subscribtion list.' % self.event
        return ("No Event in the subscribtion list has %s as it's" +
                'the unique id') % self.event

##
# The base Event class from which all events should be derived.
class Event(object):
    EVERYBODY = UniqueToken('EVERYBODY')
    NOBODY = UniqueToken('EVERYBODY')
    UNIDENTIFIED = UniqueToken('UNIDENTIFIED')
    def __init__(self, **keywords):
        self.source = None
        if keywords.has_key('source'):
            self.source = keywords['source']
        return
    def __str__(self):
        attributes = self.__dict__.keys()
        attributes.sort()
        text = "%s:" % self.__class__.__name__
        for key in attributes:
            if len(key) and key[0] != '_':
                text = "%s\n  %s:\t%s" % (text,
                                          key, repr(self.__dict__[key]))
        return text
    def _repr_args(self):
        if self.source is not None:
            return ([], {'source':self.source})
        return None

class NetworkEvent(Event):
    pass

class ConnectionEvent(NetworkEvent):
    class C_TYPE:		# c_type constants:
        DIALIN="DIALIN"		#     ConnectionEvent.C_TYPE.DIALIN
        DIALOUT="DIALOUT"	#     ConnectionEvent.C_TYPE.DIALOUT
    class STATE:		# state constants:
        UP="UP"			#     ConnectionEvent.STATE.UP
        DOWN="DOWN"		#     ConnectionEvent.STATE.DOWN
    def __init__(self, src, state, c_type):
        NetworkEvent.__init__(self, source=src)
        self.state = state
        self.c_type = c_type

class AlarmTriggerEvent(Event):
    def __init__(self,src,id,timestamp,critical,values,message=None,
                 subject=None):
        self.id = id
        self.timestamp = timestamp
        self.critical = critical
        self.values = values
        self.message = message
        self.subject = subject
        Event.__init__(self, source=src)
    def __str__(self):
        return (('%s triggered at %s, critical value = %s, ' +
                'values= %s: subject= %s, msg= %s') % (self.source.name,
                                    self.timestamp,
                                    self.critical,
                                    self.values,
                                    self.subject,
                                    self.message))
    def dictionary(self):
        return {'alarm':self.source.name,'timestamp':self.timestamp,
                'critical':self.critical,'values':self.values,
                'message':self.message,'id':self.id, 'subject':self.subject}
        
class AlarmClearEvent(Event):
    def __init__(self,src,id,timestamp,critical,values,message=None):
        self.id = id
        self.timestamp = timestamp
        self.critical = critical
        self.values = values
        self.message = message
        Event.__init__(self, source=src)
    def __str__(self):
        return (('%s cleared at %s, critical value = %s, ' +
                'values= %s: %s') % (self.source.name,
                                    self.timestamp,
                                    self.critical,
                                    self.values,
                                    self.message))
class ScheduleChangedEvent(Event):
    def __init__(self,client,new_schedule):
        self.new_schedule = new_schedule
        Event.__init__(self,source=client)
        
class ScheduleCreatedEvent(Event):
    def __init__(self,source,schedule):
        self.schedule = schedule
        Event.__init__(self,source=source)
        
class ScheduleRemovedEvent(Event):
    def __init__(self,source,schedule_url):
        self.schedule_url = schedule_url
        Event.__init__(self,source=source)

class ScheduleMovedEvent(Event):
    def __init__(self, source, schedule, from_url, to_url):
        self.schedule = schedule
        self.from_url = from_url
        self.to_url = to_url
        Event.__init__(self,source=source)

class ChangeOfValueEvent(Event):
    def __init__(self,source,old_value,new_value,timestamp=None):
        self.old_value = old_value
        self.value = new_value
        self.timestamp = timestamp
        Event.__init__(self,source=source)
    def as_result(self):
        answer = self.value
        if not isinstance(answer, Result):
            answer = Result(answer, self.timestamp)
        return answer
    def __str__(self):
        s = '%s(source=%s,old=%s,new=%s,timestamp=%s)'
        return s % (self.__class__.__name__,self.source,
                    self.old_value,self.value,self.timestamp)
        
class ChangingCovEvent(Event):
    def __init__(self,source,value,timestamp=None):
        self.value = value
        self.timestamp = timestamp
        Event.__init__(self,source=source)
    def __str__(self):
        s = '%s(source=%s,value=%s,timestamp=%s)'
        return s % (self.__class__.__name__,self.source,
                    self.value,self.timestamp)

class ResourceChangeEvent(Event):
    def __init__(self,src,oldvalue,newvalue):
        self.old_value = oldvalue
        self.value = newvalue
        Event.__init__(self,source=src)
        
class USBChangeEvent(Event):
    def __init__(self,src,type):
        self.type = type
        Event.__init__(self,source=src)
        
class NewRecordEvent(Event):
    def __init__(self,_src,_filename, _guid, _type):
        self.filename = _filename
        self.guid = _guid
        self.type = _type
        Event.__init__(self,source=_src)

# In the future this event could hold discrete values from parsing the output
class FaultReportEvent(Event):
    def __init__(self, result, output):
        self.result = result  # one line string
        self.output = output  # multi line string
        Event.__init__(self)


## removed 
#class ChangeOfValue(Event):
    #def __init__(self,value,timestamp,count):
        #self.value = value
        #self.timestamp = timestamp
        #self.count = count

##
# This class defines the EventConsumerInterface.
#
# The EventConsumerInterface is invoked by object's that implement the
# EventProducerInterface.
#
# @note This class may be used as an
# abstract base class, but typically using <code>EventConsumerMixin</code>
# or <code>EventConsumer</code> is easier, since they take care of a lot of
# house keeping.
class EventConsumerInterface:
    ##
    # Invoked when an Event of interest to this Consumer is generated by the
    # Producer.
    def event_handler(self, event):
        raise EAbstract(self.event_handler,self,event)
    ##
    # Invoked when event_handler raises an exception.
    # Producer.
    def event_exception(self, exc, event):
        raise EAbstract(self.event_exception,self, exc, event)

##
# Class to extend to be an EventConsumer.
# @implements EventConsumerInterface
class EventConsumerAbstract:
    ##
    #
    def __init__(self):
        self.__exception_count = 0
        self.__exception_threshold = 1
    ##
    # Manages the logging threshold.
    # @param indicator A clue on how to adjust the threshold.  Greater than 0
    #        increases the logging threshold, less than 0 reduces the
    #        threshold.
    def _adjust_threshold(self, indicator):
        if indicator > 0:
            self.__exception_threshold *= 2
        elif indicator == 0:
            pass
        else:
            self.__exception_threshold /= 2
            if self.__exception_threshold < 1:
                self.__exception_threshold = 1
        return
    ##
    # Default exceptions handler for <code>event_handler</code>.  Simply
    # logs the exception to the <code>msglog</msglog> and then increases the
    # threshold (count of exceptions) required before the next exception is
    # logged.
    #
    # 'valid [line number] "exact, quoted, warning" reason_it_is_valid...
    # @valid .+3 "Parameter (exc) not used"
    #            The fallback method has no need to reference exc, it is
    #            implicitly logged in the call to msglog().exception().
    def event_exception(self, exc, event):
        self.__exception_count += 1
        if self.__exception_count >= self.__exception_threshold:
            msglog().exception(msglog().types.WARN)
            self._adjust_threshold(1)
            if self.__exception_threshold > (self.__exception_count+1):
                msglog().log(msglog().types.WARN,
                           ('Exception logging of %s by %s ' +
                            'is being disabled for %d exceptions.') %
                           (event, self, self.__exception_threshold -
                            self.__exception_count))
    def event_handler(self,event):
        raise ENotImplemented(EventConsumerAbstract.event_handler)

##
# Class to mixin to include support the EventConsumerInterface on class.
#
# This class implements the EventConsumerInterface as a Mixin.  The derivative
# class needs to invoke EventConsumerMixin.__init__() to properly initialize
# this class.  See the constructor for more details.
# @see <code>EventConsumerInterface</code>
# @implements EventConsumerInterface
class EventConsumerMixin(EventConsumerAbstract):
    ##
    # Add the methods required for an object to implement the
    # EventConsumerInterface, specifically hooks for:
    # <code>event_handler</code> and <code>event_exception</code>.
    # @param noitify_func A callable object that accepts one argument, the
    #                     subsribed Event that occurred.
    # @param exception_func A callable object that accepts two arguments, the
    #                       exception generated by the event handler
    #                       and the Event the event handler was
    #                       processing.
    # @default None
    def __init__(self, noitify_func=None, exception_func=None):
        EventConsumerAbstract.__init__(self)
        self._event_handler = noitify_func
        self._exception_handler = exception_func
    def event_handler(self, event):
        self._event_handler(event)
        return
    def event_exception(self, exc, event):
        if self._exception_handler is not None:
            try:
                self._exception_handler(exc)
                return
            except Exception,exc:
                EventConsumerAbstract.event_exception(self,exc,event)
        else:
            EventConsumerAbstract.event_exception(self, exc, event)

class EventProducerInterface:
    ##
    # Invoked by a <code>consumer</code> to register interest in a class of
    # <code>event</code>'s.  The <code>event</code> is a class of the
    # Mediator <code>Event</code> hierarchy.  Any event generated by this
    # producer that is the same class or a sub-class of the <code>event</code>
    # will result in the consumer's <code>event_handler</code> method
    # being invoked.
    #
    # @param consumer An object that implements the EventConsumerInterface.
    # @param event The event to be notified of.
    # @keyword uid A unique identifier for an event handler.  This will allow
    #             for simple event filtering, modification, and insertion.
    # @default Event.UNIDENTIFIED  The notification will occur after all the
    #                              filters are applied.
    # @keyword before
    # @default Event.NOBODY
    # @keyword after
    # @default Event.EVERYBODY
    def event_subscribe(self, consumer, event, **keywords):
        raise EAbstract(self.event_subscribe)
    ##
    # Typically called by the class that includes (derives from) the
    # EventMixin.
    def event_generate(self, event):
        raise EAbstract(self.event_generate)

##
# Provides a class with the basic Framework Event mechanism.
#
# @todo In depth re-factor to eliminate UID concept and simplify.
class EventProducerMixin:
    ##
    # Private container for events in the subscribtion list.
    # @fixme Contain all of a consumers events of interest?
    class Subscription:
        KEYWORDS = {'uid':Event.UNIDENTIFIED,
                    'before':Event.NOBODY,
                    'after':Event.EVERYBODY}
        def __init__(self, consumer, event_class, keywords):
            self.consumer = consumer
            self.event_class = event_class
            keywords = keywords.copy()
            for key in self.KEYWORDS.keys():
                if keywords.has_key(key):
                    setattr(self,key,keywords[key])
                    del(keywords[key])
                else:
                    setattr(self,key,self.KEYWORDS[key])
            if keywords:
                raise EInvalidValue('keywords',keywords,
                                    'Remaining keys are not recognized.')
            # @todo implement and validate before/after relationship...
            if self.before != Event.NOBODY:
                raise ENotImplemented('before keyword')
            if self.after != Event.EVERYBODY:
                raise ENotImplemented('after keyword')
            return
    def __init__(self):
        self.__event_lock = Lock()
        self.__subscribers = []
    ##
    # Only EventMixin and it's direct decendants should ever call this.
    def _event_begin_critical_section(self):
        self.__event_lock.acquire()
    ##
    # Only EventMixin and it's direct decendants should ever call this.
    def _event_end_critical_section(self):
        self.__event_lock.release()
    ##
    # Typically called by the class that includes (derives from) the
    # EventMixin.
    def event_generate(self, event):
        if event.source is None:
            event.source = self
        event_consumers = []
        self._event_begin_critical_section()
        try:
            for subscription in self.__subscribers:
                if isinstance(event, subscription.event_class):
                    consumer = subscription.consumer()
                    if consumer is not None:
                        event_consumers.append(consumer)
                    else:
                        self.__subscribers.remove(subscription)
        finally:
            self._event_end_critical_section()
        for consumer in event_consumers:
            try:
                consumer.event_handler(event)
            except Exception,exc:
                try:
                    consumer.event_exception(exc,event)
                except:
                    msglog().exception()
        return
    ##
    # @param consumer An object that implements the EventConsumerInterface.
    # @param event The event to be notified of.
    # @keyword uid A unique identifier for an event handler.  This will allow
    #             for simple event filtering, modification, and insertion.
    # @default Event.UNIDENTIFIED  The notification will occur after all the
    #                              filters are applied.
    # @keyword before
    # @default Event.NOBODY
    # @keyword after
    # @default Event.EVERYBODY
    def event_subscribe(self, consumer, event, **keywords):
        self._cleanup_subscriptions()
        subscription = self.Subscription(weakref.ref(consumer),event,keywords)
        self._event_begin_critical_section()
        try:
            for subscriber in self.__subscribers:
                if (subscription.uid is not Event.UNIDENTIFIED
                    and subscription.uid is subscriber.uid):
                    raise EEventCollision(subscription.uid)
                if (subscriber.consumer() is consumer
                    and subscription.event_class is subscriber.event_class):
                    msglog().log('broadway',msglog().types.WARN,
                               ('Object %r subscribed for Event '
                                '%r already.  Ignoring subscription' %
                                (consumer,event)))
                    return
            self.__subscribers.append(subscription)
        finally:
            self._event_end_critical_section()
        return
    def event_unsubscribe(self,consumer,event,**keywords):
        self._cleanup_subscriptions()
        self._event_begin_critical_section()
        try:
            for subscription in self.__subscribers:
                if (subscription.consumer() is consumer and 
                    subscription.event_class is event):
                    self.__subscribers.remove(subscription)
                    return
        finally:
            self._event_end_critical_section()
        msglog().log('broadway',msglog().types.WARN,
                   ('Consumer %r tried to unsubscribe for '
                    'non-subscribed Event %r' % (consumer,event)))
        return
    ##
    # @note Not thrilled with this.  Could lead to race conditions.
    #       Probably callbacks on the subscribe/unsubscribe methods
    #       would be better...
    def event_class_consumer_count(self, event):
        n_event_class_consumers = 0
        self._event_begin_critical_section()
        try:
            for subscription in self.__subscribers:
                if subscription.event_class is event:
                    n_event_class_consumers += 1
        finally:
            self._event_end_critical_section()
        return n_event_class_consumers
    ##
    # @note Not thrilled with this.  Could lead to race conditions.
    #       Probably callbacks on the subscribe/unsubscribe methods
    #       would be better...
    def event_has_subscribers(self):
        self._event_begin_critical_section()
        try:
            has_subscribers = len(self.__subscribers) != 0
        finally:
            self._event_end_critical_section()
        return has_subscribers
    def _cleanup_subscriptions(self):
        self._event_begin_critical_section()
        try:
            for subsription in self.__subscribers:
                if subsription.consumer() is None:
                    self.__subscribers.remove(subsription)
        finally:
            self._event_end_critical_section()
##
# Examples/tests using Events.
if __name__ == '__main__':
    from mpx.lib.threading import Thread
    class E(Event):
        pass
    class Esub(E):
        pass
    class P(Thread, EventProducerMixin):
        def __init__(self):
            Thread.__init__(self, None, None, 'EventProducer Test')
            EventProducerMixin.__init__(self)
        def run(self):
            for i in range(0,100):
                for e in (Event(), E(), Esub()):
                    self.event_generate(e)
    class C(EventConsumerAbstract):
        def event_handler(self, event):
            print "C: Got %s!" % event
    uid=UniqueToken('TestIt!')
    c = C()
    p = P()
    p.setDaemon(0)
    p.event_subscribe(c, E, uid=uid)
    p.start()
    p.join()
