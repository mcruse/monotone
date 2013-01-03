"""
Copyright (C) 2007 2009 2010 2011 Cisco Systems

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
import asyncore
import urlparse
import string
import socket
import cPickle
from cStringIO import StringIO 
from errno import EWOULDBLOCK
from collections import defaultdict
from mpx import properties
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.threading import gettid
from mpx.lib.scheduler import scheduler
from mpx.lib.eventdispatch import Event
from interfaces import ICloudManager
from interfaces import ICloudEvent
from mpx.componentry import implements
from mpx.componentry import register_utility
from mpx.componentry.interfaces import IPickles
from mpx.lib.eventdispatch.dispatcher import Dispatcher
from mpx.lib.eventdispatch.adapters import EventSource
from mpx.lib.neode.node import CompositeNode
from mpx.lib.persistent import PersistentDataObject
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from mpx.service.network.async.connection.monitor import ChannelMonitor
from mpx.service.network.async.connection.trigger import CallbackTrigger
from mpx.service.network.utilities.counting import Counter
from mpx.lib.node import as_node
from errno import EISCONN
from errno import EINPROGRESS
from errno import EALREADY
from errno import EWOULDBLOCK
from errno import EINTR
from errno import ENOTCONN
from errno import ECONNRESET
from errno import ESHUTDOWN
from errno import errorcode
#
# REDUSA_SOCKET_MAP HACK:
#
# Use the Redusa specific socket_map since that was what was previously
# happening...
from mpx.service.network.http._http import REDUSA_SOCKET_MAP

class Formation(list):
    implements(IPickles)
    def __call__(self): return self
    formation = property(__call__)


class utils:
    @staticmethod
    def valid_ip_address(ip_address):
        if(ip_address == None):
            return(False)
        
        ip_address_parts = string.split(ip_address, '.')
        if len(ip_address_parts) != 4:
            return False
        for x in ip_address_parts:
            try:
                x = int(x)
            except ValueError:
                return False
            else:
                if x < 0 or x > 255:
                    return False
        return True
    @staticmethod
    def get_ip_addr(host):
        if(utils.valid_ip_address(host)):
            return(host)
        
        try:
            ip=socket.gethostbyname(host)
        except socket.error ,msg :
            msglog.log('CloudManager', msglog.types.WARN, 'Unable to resolve the hostname=%s Error message=%s' %(host,msg))
            return(host)    
        return(ip)
    @staticmethod
    def same_host(h1,h2):
        if(utils.valid_ip_address(h1)):
            ip_h1=h1
        else:
            ip_h1=utils.get_ip_addr(h1)
            
        if(utils.valid_ip_address(h2)):
            ip_h2=h2
        else:
            ip_h2=utils.get_ip_addr(h2)
        
        if(ip_h1 == ip_h2):
            return(True)
        else:
            return(False)
 
class NFormation(object):
    def __init__(self,formation_list,peer):
        self.formation=formation_list[:]
        self.peer=peer
        self.portal=None

    def set_portal(self,portal):
        self.portal=portal
        
    def get_portal(self):
        return(self.portal) 
    
    def normalize_formation(self,formation):
        norm_formation=[]
        for h in formation:
            if(utils.valid_ip_address(h)):
                ip=h
            else:
                ip=utils.get_ip_addr(h)
            norm_formation.append(ip)
        return(norm_formation)
            
            
            
    def compute_excludes(self,new_formation_arg):
        excludes=[]
        no_of_excluded_peers=0
        previous = self.normalize_formation(self.formation[:])
        new_formation=self.normalize_formation(new_formation_arg)
        if previous == new_formation:
            #msglog.log('broadway', msglog.types, message)
            return(no_of_excluded_peers,excludes)
        else:
            for peer in previous:
                if peer not in new_formation:
                    excludes.append(peer)
        no_of_excluded_peers=len(excludes)
        excludes=[self.peer]+excludes
        return(no_of_excluded_peers,excludes)               
    
    def get_formation(self):
        return(self.formation[:])
    def compute_targets(self):
        formation=self.normalize_formation(self.formation)
        index = formation.index(self.peer)
        targets = formation[index:] + formation[0:index]
        return(targets)
    def set_formation(self,new_formation):
        self.formation = new_formation[:]
    def compute_dispatch_info(self):
        formation=self.normalize_formation(self.formation)
        dispatch=False
        delay=0
        formation_len=len(formation)
        if(self.portal != None):
            formation_len +=1    
        if formation_len > 1:
            delay = 5 * (formation_len - formation.index(self.peer))
            dispatch=True
        return(dispatch,delay)         
    def get_targets(self, formation_arg, from_peer_arg):
        formation=self.normalize_formation(formation_arg)
        from_peer=utils.get_ip_addr(from_peer_arg)
        from_index = formation.index(from_peer)
        base = from_index * 2 + 1
        indexes = []
        for i in range(0, 2):
            index = base + i
            if index < len(formation):
                indexes.append(index)
            else: 
                #msg='Get targets skipping %s, beyond formation.' % index
                #msglog.log('CloudConfigurator', msglog.types.DB,msg)
                pass
            
        targets = []
        for index in indexes:
            targets.append(formation[index])
        '''
        Changes - Add the portal into targets if from_peer is also 
        the first in formation
        '''
        #msg='formation=%s from_peer=%s targets=%s \n' %(formation,from_peer,targets)
        #msglog.log('CloudFormation', msglog.types.INFO,msg)    
        if((self.portal != None ) and (utils.same_host(formation[0],from_peer) == True) ) :
            #msg='Local event being propogated to the Portal %s ' % self.portal
            #msglog.log('CloudFormation', msglog.types.DB,msg)
            portal=utils.get_ip_addr(self.portal)
            targets.append(portal)
        
        return targets
    

class FormationUpdated(Event): pass

class NotificationFailure(Event):
    implements(IPickles)
    __safe_for_unpickling__ = True
    def __init__(self, cloudevent, target, origin = None, guid = None):
        self.target = target
        super(NotificationFailure, self).__init__(IPickles(cloudevent)())
    def __getinitargs__(self): return (IPickles(self.source), self.target)
    def __reduce__(self): return (self.__class__, self.__getinitargs__())

class CloudEvent(Event):
    implements(ICloudEvent)
    def __init__(self, source, origin, targets, portal,topics, event, guid = None):
        super(CloudEvent, self).__init__(source, origin, guid)
        self.targets = targets
        self.topics = topics
        self.portal=portal
        self.__data = None
        self.event = IPickles(event)
    def set_data(self, data):
        self.__data = data
    def get_data(self):
        return self.__data
    def has_data(self):
        return self.__data is not None
    def __str__(self):
        data = super(CloudEvent, self).__str__()
        details = '\n\ttargets %s, \n\ttopics %s, \n\t portal=%s \n\tevent %s.'
        details = details % (self.targets, self.topics, self.portal, str(self.event))
        return data + details
    def __call__(self):
        return self.event()

class CloudManager(CompositeNode):
    implements(ICloudManager)
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, *args):
        super(CloudManager, self).__init__(*args)
        self.dispatcher = Dispatcher('Cloud Manager:Dispatcher')
        register_utility(self, ICloudManager, 'Cloud Manager')
        self.peer = Event.LOCALORIGIN
        self.formation = []
        self._scheduled = None
        self.unreachable = {}
        self.subscription = None
        if((as_node('/services/network/https_server')).is_enabled()):
            self.secure_http = True
        else:
            self.secure_http = False
        self.channel_monitor = ChannelMonitor()
        self.channel_monitor.trigger = CallbackTrigger(self.channel_monitor)
    def stop(self):
        if self.subscription:
            self.remove_listener(self.subscription)
        if self.channel_monitor.is_running():
            self.channel_monitor.stop_monitor()
        self.subscription = None
        super(CloudManager, self).stop()

    def is_event_valid(self,cloudevent):
        portal = self.nformation.get_portal()
        topic=cloudevent.topics[0]
        if(topic == 'EventResend' ):
            if( (portal != None ) and utils.same_host(cloudevent.origin,portal) ):
                return(True)
        elif(topic == 'Alarm Manager' ):
            #if (self.is_peer_in_formation(cloudevent.origin) == True):
            return(True)
        elif(topic == 'CloudFormation' ):
            return(True)

        return(False)


    def handle_remote_event(self, data):
        cloudevent = IPickles(cPickle.loads(data))()
        self.message('Handling remote event from : %s topic=%s ' %(cloudevent.origin,cloudevent.topics))
        cloudevent.set_data(data)
        if(self.is_event_valid(cloudevent) == False ):
            self.message('Dropping the remote event from : %s topic=%s ' 
                           %(cloudevent.origin,cloudevent.topics),msglog.types.WARN)
            return
            
        self.dispatcher.dispatch(cloudevent, cloudevent.topics)
        if(not ('CloudFormation' in cloudevent.topics) ):
            return
        '''
        Dont propogate an event if we are Portal
        '''
        if((cloudevent.portal != None )and (utils.same_host(self.peer,cloudevent.portal)) ):
            self.message('Not Propagating remote event, since I am getting it as a portal:')
            return
        
        
        self.propogate(cloudevent)

    def send_event_to_portal(self,event,topic,target):
        cloudevent = CloudEvent(
            self, self.peer, [target], self.nformation.get_portal(),topic, event)

        protocol = "https" if self.secure_http else "http"
        notifier = CloudNotifier(self.channel_monitor,target, protocol,'/cloud', self.debug)
        notifier.cloudevent = cloudevent
        if not cloudevent.has_data():
            cloudevent.set_data(cPickle.dumps(IPickles(cloudevent)))
        clouddata = cloudevent.get_data()
        notifier.notify(clouddata, self.handle_send_failure_portal,self.handle_send_success_portal)

    def handle_send_failure_portal(self, notifier):
        cloudevent = notifier.cloudevent
        target_peer = notifier.peer
        self.message('Unable to send alarm events to portal=%s ' % (target_peer),msglog.types.WARN)

    def handle_send_success_portal(self,notifier):
        cloudevent = notifier.cloudevent
        target_peer = notifier.peer
        self.message('Succesfully sent alarm events to portal=%s ' % (target_peer))



    def handle_local_event(self, event, topics = []):
        cloudevent = CloudEvent(
            self, self.peer, self.target_formation, self.nformation.get_portal(),topics, event)
        self.propogate(cloudevent)
    
    def is_peer_in_formation(self,peer,formation=None):
        if not formation:
            formation = self.get_formation()
        peer_ip=utils.get_ip_addr(peer)
        return any(utils.same_host(peer_ip, ip) for ip in formation)
    
    def is_host_the_portal(self,host):
        portal = self.nformation.get_portal()
        if not portal:
            return False
        return utils.same_host(portal, host)
    
    def is_host_in_formation(self, host):
        if self.is_host_the_portal(host):
            return True
        if self.is_peer_in_formation(host):
            return True
        return False

    def handle_formation_update(self, cloudevent):
        '''
        Don't take any action like updating Cloud formation or Portal etc, 
        if you have got this event as a portal. The alarms are shown in the event manager
        by a different mechanism. 
        '''
        if((cloudevent.portal != None ) and (utils.same_host(self.peer,cloudevent.portal))):
            self.message('Received the event as a Portal, so not going to take any action %s' % str(cloudevent))
            self.message('handle_formation_update doing nothing, no change.')
            return
        
        formation = cloudevent()
        if (self.is_peer_in_formation(self.peer,formation) == False):
            formation = [self.peer]
            self.message('Setting Cloud Formation to self.peer; no longer in Cloud.',msglog.types.INFO)
        
        self._setup_formation(formation,cloudevent.portal)

    
    def _setup_formation(self, formation,portal):
        scheduled, self._scheduled = self._scheduled, None
        if scheduled is not None:
            try: scheduled.cancel()
            except: pass
            else: self.message('Canceled pending dispatch of formation update.')
        self.nformation.set_portal(portal)
        self.nformation.set_formation(formation)
        self.target_formation = self.nformation.compute_targets()
        self.message('Resetting unreachables during Cloud setup.')
        self.reset_unreachables()
        (dispatch,delay)=self.nformation.compute_dispatch_info()
        if (dispatch):
            self._scheduled = scheduler.after(delay, self.dispatcher.dispatch, (FormationUpdated(self),))
            self.message('Scheduled dispatch in %s seconds.' % delay)
        else: self.message('Formation of one peer, no Updated event generated.')
        
        # Save the PDO, if the formation or portal has changed
        if((self._pdo.formation != formation) or (self._pdo.portal != portal) or (self._pdo.peer != self.peer)):
            self.message('New formation/portal found , hence pickling. New Formation is :%s portal is %s' %(str(formation),portal))
            self._pdo.formation=formation[:]
            self._pdo.portal=portal
            self._pdo.peer=self.peer
            tstart = time.time()
            self._pdo.save()
            tend = time.time()
            self.message('New formation pickled and saved in %s seconds.' % (tend - tstart))
        else:
            self.message('Formation/Portal has not changed. Not pickling it. ' )

    
    def update_formation(self, new_formation,portal):
        (no_of_excluded_peers,excludes)=self.nformation.compute_excludes(new_formation)
        if no_of_excluded_peers:
            self.message( 'Notifying removed participants: %s' % (excludes,))
            excludedevent = CloudEvent(self, self.peer, excludes,self.nformation.get_portal(),['CloudFormation'], new_formation)
            self.propogate(excludedevent)
        else: 
            self.message( 'All current Cloud member in new Cloud Formation.')
        self._setup_formation(new_formation,portal)
        self.handle_local_event(new_formation, ['CloudFormation'])

    def handle_propogation_failure(self, notifier):
        cloudevent = notifier.cloudevent
        target_peer = notifier.peer
        # TODO: generate comm failure error to propogate as well.
        # Progpogate event to Cloud Managers target_peer would have notified.
        
        '''
        The target_peer can be portal or a peer.
        If it is a portal then we will not put it in unreachables and also 
        we do not propogate the event.
        Log if we are not connecting to the portal 
        '''
        portal=self.nformation.get_portal()
        if((portal != None ) and (utils.same_host(target_peer,portal))):
            msg='Portal %s is not reachable .' % portal
            self.message(msg)
            return
            
        
        scheduled = self.unreachable.get(target_peer)
        if scheduled is not None:
            scheduled.cancel()
            self.message('Host %s already listed unreachable, reset scheduled retry.' % target_peer)
        self.unreachable[target_peer] = scheduler.after(5 * 60, self._remove_from_unreachable, (target_peer,))
        self.message('Host %s added to list of unreachable peers.' % target_peer)
        self.propogate(cloudevent, target_peer)

    def _remove_from_unreachable(self, peer):
        if self.unreachable.has_key(peer):
            del(self.unreachable[peer])
            self.message('Removed "%s" from unreachable to retry.' % peer)
        else: self.message('Host "%s" not in unreachable, ignoring remove.' % peer)

    def reset_unreachables(self):
        message = 'Resetting unreachables:\n'
        unreachables = self.unreachable.items()
        self.unreachable.clear()
        for peer, entry in unreachables:
            entry.cancel()
            message += '\t- removed "%s" from unreachables;\n' % peer
        message += '\t%s peers cleared from unreachables.' % len(unreachables)
        self.message(message)
        return len(unreachables)

    def add_listener(self, callback, topic):
        return self.dispatcher.register_for_topic(callback, topic)

    def remove_listener(self, guid):
        return self.dispatcher.unregister(guid)

    def propogate(self, cloudevent, from_peer = None):
        '''
        No Changes - Just make sure ...
        '''
        if not isinstance(cloudevent, CloudEvent):
            raise TypeError('Argument must be instance of CloudEvent')
        if from_peer is None: from_peer = self.peer
        self.message('Propogating as %s:\n\t%s...' % (from_peer, str(cloudevent)))
        target_formation = cloudevent.targets

        notifiers = []
        targets = self.nformation.get_targets(target_formation, from_peer)
        for target in targets:
            if not target.strip():
                self.message('Not notifying "%s" because not valid, adding its targets.' % target)
                targets.extend(self.nformation.get_targets(target_formation, target))
            elif not self.unreachable.has_key(target):
                protocol = "https" if self.secure_http else "http"
                notifier = CloudNotifier(self.channel_monitor, target, 
                                         protocol, '/cloud', self.debug)
                notifier.cloudevent = cloudevent
                notifiers.append(notifier)
            else:
                self.message('Host "%s" unreachable, adding its targets.' % target)
                targets.extend(self.nformation.get_targets(target_formation, target))
        if not cloudevent.has_data():
            cloudevent.set_data(cPickle.dumps(IPickles(cloudevent)))
        clouddata = cloudevent.get_data()
        notified = []
        for notifier in notifiers:
            notifier.notify(clouddata, self.handle_propogation_failure)
            notified.append(notifier.peer)
        if(len(notified) > 0 ):
            self.message('Propogate notified: %s' % (notified,))
        return notified

    

    def message(self, message, mtype = msglog.types.DB):
        if mtype != msglog.types.DB or self.debug:
            message = 'CloudManager(%s) - %s' % (self.peer, message)
            msglog.log('broadway', mtype, message)

    security.protect('add_peer', 'Configure')
    def add_peer(self,peer):
        formation=self.nformation.get_formation()
        formation.append(peer)
        portal=self.nformation.get_portal()
        self.update_formation(formation,portal)
        return

    def get_formation(self):
        formation=self.nformation.get_formation()
        return(formation)
    
    def get_portal(self):
        portal=self.nformation.get_portal()
        return(portal)

    security.protect('set_portal', 'Configure')
    def set_portal(self,portal):
        formation=self.nformation.get_formation()
        self.update_formation(formation,portal)

    security.protect('remove_peer', 'Configure')
    def remove_peer(self,peer):
        formation = self.nformation.get_formation()
        formation.remove(peer)
        portal=self.nformation.get_portal()
        self.update_formation(formation,portal)
    
    def start(self):
        # Bad self IP Address 
        if(self.peer == '127.0.0.1' ):
            msg='Cloud facility will not function properly because of local IP address being 127.0.0.1'
            self.message(msg,msglog.types.WARN)
            return 
        if not self.channel_monitor.is_running():
            self.channel_monitor.start_monitor()
        self._pdo=PersistentDataObject(self)
        self.message('The Cloud Manager Persistent Object is in the file :%s' %str(self._pdo.filename()),msglog.types.INFO)
        migration=False
        if(os.path.exists(self._pdo.filename())):
            # Already Migrated
            self._pdo.formation=[self.peer]
            self._pdo.portal=None
            self._pdo.peer=self.peer
            self._pdo.load()
        else:
            # We save a 'default' formation and expect the Cloud Configurator to 
            # update the _pdo.formation via update_information API.
            # The _setup_formation gets called internally from update_information
            self._pdo.portal=None
            self._pdo.formation=[self.peer]
            self._pdo.peer=self.peer
            self._pdo.save()
            self._pdo.load()
            migration=True
        
        #Bad formation/peer in the PDO
        if( not self._pdo.peer in self._pdo.formation ):
            #Bad formation/peer
            self.message('The Cloud Manager PDO in the file :%s is corrupted. Defaulting to safe configuration' %str(self._pdo.filename()),msglog.types.WARN)
            self._pdo.portal=None
            self._pdo.formation=[self.peer]
            self._pdo.peer=self.peer
            self._pdo.save()
            self._pdo.load()
        
        self.message('Hosts are :%s portal=%s self=%s' %(str(self._pdo.formation),self._pdo.portal,self._pdo.peer),msglog.types.INFO)
        self.nformation=NFormation(self._pdo.formation,self.peer)
        self.nformation.set_portal(self._pdo.portal)
        
        # IP Address Change Case
        if(not utils.same_host(self.peer,self._pdo.peer)):
            self.message('Self address change detected old=%s new=%s. Fixing the Cloud Formation accordingly' %(str(self._pdo.peer),self.peer),msglog.types.INFO)
            formation = self.nformation.get_formation()
            norm_form=self.nformation.normalize_formation(formation)
            # IP Address Swap
            self_index=norm_form.index(self._pdo.peer)
            formation.pop(self_index)
            formation.insert(0,self.peer)
            self.nformation.set_formation(formation)
               
        '''
        In the Case of Migration, the update_formation() API is called
        by the Cloud Configurator. In the already migrated case, we call the
        update_formation() with the PDO formation and Portal
        '''
        
        self.target_formation = self.nformation.compute_targets()
        
        if(migration == False):
            self.update_formation(self.nformation.get_formation(), self.nformation.get_portal())
        
        if self.subscription is None:
            self.subscription = self.add_listener(
                self.handle_formation_update, 'CloudFormation')

        # Send Cloud Event to all the Hosts for re-sending the alarm events 
        # over to the Portal again - if we are nbmm
        if(self.is_host_nbmm()):
            scheduler.after(10, self.request_for_resending_alarm_events)

        super(CloudManager, self).start()

    def is_host_nbmm(self):
        devices=as_node('/interfaces').children_names()
        if('relay1' in devices ):
            return(False)
        else:
            return(True)

    def get_hosts_list(self):
        hosts_list=[]
        all_hosts=as_node('/services/Host Manager').children_nodes()
        for h in all_hosts:
            hosts_list.append(h.host)
        return(hosts_list)

    def request_for_resending_alarm_events(self):
        hosts_list=self.get_hosts_list()
        for host in hosts_list:
            cloudevent = CloudEvent(self, self.peer, [host],None,['EventResend'],[host])
            cloudevent.set_data(cPickle.dumps(IPickles(cloudevent)))
            self.send_req_for_alarm_events(host,cloudevent)

    def handle_send_failure(self, notifier):
        cloudevent = notifier.cloudevent
        target_peer = notifier.peer
        self.message('Unable to notify %s to send alarm events again ' % (target_peer),msglog.types.WARN)

    def handle_send_success(self,notifier):
        cloudevent = notifier.cloudevent
        target_peer = notifier.peer
        self.message('succesfully notified %s to send alarm events again ' % (target_peer))

    def send_req_for_alarm_events(self,target,cloudevent):
        from_peer=self.peer
        protocol = "https" if self.secure_http else "http"
        notifier = CloudNotifier(self.channel_monitor,target, protocol,'/cloud', self.debug)
        notifier.cloudevent = cloudevent
        clouddata = cloudevent.get_data()
        notifier.notify(clouddata, self.handle_send_failure,self.handle_send_success)




class CloudNotifier(asyncore.dispatcher):
    counter = Counter(0)
    in_buffer_size = 1 << 12
    out_buffer_size = 1 << 12
    def __init__(self, monitor, peer, protocol, path, debug=False):
        self.number = self.counter.increment()
        self.ssl = None
        self.peer = peer
        self.monitor = monitor
        self.protocol = protocol
        if(protocol.upper() == 'HTTPS'):
            port=443
            self._using_ssl=True
        else:
            port=80
            self._using_ssl=False
        self._fileno = None
        self.port = port
        self.path = path
        self.debug = debug
        self.ac_out_buffer = ""
        self.sio_in_buffer = StringIO()
        self.scheduled_timeout = None
        self.partial_header  = 'POST %s HTTP/1.1\r\n' % path
        self.partial_header += 'Host: %s:%s\r\n' % (peer, port)
        self.partial_header += 'Content-Type: text/xml\r\n'
        self.partial_header += 'Connection: close\r\n'
        self.partial_header += 'Authorization: Basic bXB4YWRtaW46bXB4YWRtaW4=\r\n'
        self.content_length = 'Content-Length: %s\r\n\r\n'
        asyncore.dispatcher.__init__(self, map=monitor)
    def handle_read(self):
        self.sio_in_buffer.write(self.recv(self.in_buffer_size))
    def handle_write(self):
        sent = self.send(self.ac_out_buffer[0: self.out_buffer_size])
        self.ac_out_buffer = self.ac_out_buffer[sent:]
    def readable(self):
        return True
    def writable(self):
        return not self.connected or len(self.ac_out_buffer)
    def notify(self, data, on_fail=None, on_success=None):
        self.data = data
        if on_success is not None:
            self.success = on_success
        if on_fail is not None:
            self.failure = on_fail
        buffer = self.partial_header
        buffer += self.content_length % len(data)
        self.monitor.trigger.trigger_event(self.propagate, buffer + data)
    def propagate(self, data):
        """
            To be called by asyncore-polling loop.  Use 
            notify to trigger the propagate event.
        """
        self.message("%s propagate creating socket." % self)
        self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
        self.message("%s propagate connecting %s:%d" % (self, self.peer, self.port))
        self.connect((self.peer,self.port))
        self.scheduled_timeout = scheduler.after(30, self.handle_timeout)
        self.ac_out_buffer = data
    def create_socket(self, family, stype):
        self.message("%s create-socket %r, %r." % (self, family, stype))
        asyncore.dispatcher.create_socket(self, family, stype)
    def connect(self, address):
        self.message("%s connect %r." % (self, address))
        asyncore.dispatcher.connect(self, address)
    def connect_ssl(self, address):
        """
            Deprecated: trying to fix other issue by pulling 
            SSL wrapping out of handle-connect.  Left here in 
            case it's useful.
        """
        self.connected = False
        self.socket.setblocking(1)
        try:
            self.socket.connect(address)
        except:
            msglog.warn("%s connect failed.")
            self.handle_error()
        else:
            self.addr = address
            self.ssl = socket.ssl(self.socket)
            self.message("%s set up SSL wrapper: %s." % (self, self.ssl))
            self.handle_connect()
        finally:
            self.socket.setblocking(0)
    def handle_close(self):
        self.close()
        incomplete = self.writable()
        if self.scheduled_timeout:
            self.scheduled_timeout.cancel()
            self.scheduled_timeout = None
        self.sio_in_buffer.seek(0)
        status = self.sio_in_buffer.readline()
        if incomplete or status.find('200') == -1:
            output = 'Notifier failed.'
            if status:
                output += '  Response: '
                output += '\n' + ('*' * 25) + '\n'
                output += status + self.sio_in_buffer.read()
                output += '\n' + ('*' * 25)
            self.message(output)
            self.failure(self)
        else:
            self.message('Notification succeeded, status: %s' % status.rstrip())
            self.success(self)
    def handle_timeout(self):
        self.message('Attempt to notify %s timed out.' % self.peer)
        self.handle_close()
    def handle_error(self):
        try:
            msglog.warn("%s handling error. Please check whether the peer is up and supports the %s protocol" % (self, self.protocol))
            msglog.exception(prefix="handled")
            msglog.inform("%s closing due to error." % self)
        finally:
            self.close()
    def close(self):
        self.message("%s closing socket." % self)
        asyncore.dispatcher.close(self)
        self.ssl = None
    def send(self, data):
        try:
            if self._using_ssl:
                bytes = self.ssl.write(data)
                self.message("Wrote %d/%d bytes over SSL." % (bytes, len(data)))
            else:
                bytes = self.socket.send(data)
                self.message("Sent %d/%d bytes." % (bytes, len(data)))
        except socket.sslerror,error:
            if error[0] == socket.SSL_ERROR_WANT_READ:
                self.message("Write got SSL-WANT-READ.")
                return 0
            if error[0] == socket.SSL_ERROR_WANT_WRITE:
                self.message("Write got SSL-WANT-WRITE.")
                return 0
            raise
        except socket.error,error:
            if error[0] == EWOULDBLOCK:
                return 0
            raise
        return bytes
    def recv(self, count):
        try:
            if self._using_ssl:
                data = self.ssl.read(count)
                self.message("Read %d/%d bytes over SSL." % (len(data),count))
            else:
                data = self.socket.recv(count)
                self.message("Received %d/%d bytes." % (len(data),count))
        except socket.sslerror,error:
            if error[0] == socket.SSL_ERROR_WANT_READ:
                self.message("Read got SSL-WANT-READ.")
                return ""
            if error[0] == socket.SSL_ERROR_WANT_WRITE:
                self.message("Read got SSL-WANT-WRITE.")
                return ""
            if error[0] == socket.SSL_ERROR_ZERO_RETURN:
                self.message("Closing chanel: SSL ZERO RETURN.")
                self.handle_close()
                return ""
            if error[0] == socket.SSL_ERROR_EOF:
                self.message("Closing chanel: SSL EOF.")
                self.handle_close()
                return ""
            raise
        except socket.error,error:
            if error[0] in [ECONNRESET,ENOTCONN,ESHUTDOWN]:
                self.message("Closing chanel: %r." % error[0])
                self.handle_close()
                return ""
            raise
        else:
            if not data:
                self.message("Closing chanel: recieved ''.")
                self.handle_close()
                return ""
        return data
    def handle_read_event(self):
        # Pulled from asyncore to delegate setting of 
        # 'connect' flag to handle-connect method, and 
        # to skip invoking handle-read if not connected.
        if self.accepting:
            # for an accepting socket, getting a read implies
            # that we are connected
            if not self.connected:
                self.connected = True
            self.handle_accept()
        else:
            if not self.connected:
                self.handle_connect()
            if self.connected:
                self.handle_read()
    def handle_connect(self, *args):
        self.message("%s handling connect." % self)
        if self._using_ssl:
            self.socket.setblocking(1)
            try:
                self.ssl = socket.ssl(self.socket)
            finally:
                self.socket.setblocking(0)
            self.message("%s set up SSL wrapper: %s." % (self, self.ssl))
        self.connected = True
        self.message("%s handled connect." % self)
    def success(self, *args): 
        pass
    def failure(self, *args): 
        pass
    def __str__(self):
        name = self.__class__.__name__
        return "%s[%d]('%s:%d')" % (name, self.number, self.peer, self.port)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))
    def message(self, message, mtype = msglog.types.DB):
        if mtype != msglog.types.DB or self.debug:
            message = '%s - %s' % (self, message)
            msglog.log('broadway', mtype, message)
    def add_channel (self, map=None):
        return asyncore.dispatcher.add_channel(self, self.monitor)
    def del_channel (self, map=None):
        return asyncore.dispatcher.del_channel(self, self.monitor)
