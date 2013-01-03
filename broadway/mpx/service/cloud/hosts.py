"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
from __future__ import with_statement
import os
import new
import time
import threading
from urllib import quote_plus
from contextlib import contextmanager
from mpx.lib import msglog
from mpx.lib import Result
from mpx.lib.url import ParsedURL
from mpx.lib.exceptions import ERNATimeout
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.exceptions import EConfiguration
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.node import as_node
from mpx.lib.node import CompositeNode
from mpx.lib.scheduler import scheduler
from mpx.lib.thread_pool import ThreadPool
from mpx.lib.threading import Lock
from mpx.lib.network.icmplib import ping
from mpx.lib.rna import NodeFacade
from mpx.lib.rna import RNA_CLIENT_MGR
from mpx.lib.node.interfaces import ICompositeNode
from mpx.componentry import implements
from moab.linux.lib import uptime
Undefined = object()
THREADPOOLSIZE = 5

class EResourceUnavailable(ERNATimeout):
    pass

class ManagedNodeFacade(NodeFacade):
    implements(ICompositeNode)
    def __init__(self, host, path, service, protocol):
        self.host = host
        self._path = path
        self._service = service
        self._protocol = protocol
        super(ManagedNodeFacade, self).__init__(path, service, protocol)
    @property
    def parent(self):
        path = self.as_remote_path()
        if path == "/":
            return self.host
        elif path.endswith("/"):
            msglog.warn("Path ends with '/': %r" % path)
            path = path[0: -1]
        head,sep,tail = path.rpartition("/")
        ppath = head if head else "/"
        return self.host.as_remote_node(ppath)
    def has_child(self, name):
        try:
            return super(ManagedNodeFacade, self).has_child(name)
        except EResourceUnavailable:
            # if the remote host if offline return False - this allows
            # as_deferred_node to still work if the host is offline the first
            # time this is called.
            return False
    def get_child(self, name):
        if not self.has_child(name):
            raise ENoSuchName(name, self)
        path = os.path.join(self.as_remote_path(), quote_plus(name))
        return self.host.as_remote_node(path)
    def as_remote_path(self):
        """
            Get local path of remote node.
        """
        return self._service
    def children_nodes(self):
        return [self.get_child(name) for name in self.children_names()]
    def as_node_url(self):
        """
            Generate node URL based on Managed Host location.
        """
        return self.host.as_node_url() + self.as_remote_path()
    def get_batch_manager(self):
        """
            Override default batch manager creation method to 
            replace NodeFacade 'manager' reference used by BM 
            with ManagedNodeFacade instance.
            
            Somewhat of a hack based on knowledge of BM internals.
        """
        bm = super(ManagedNodeFacade, self).get_batch_manager()
        if not isinstance(bm.manager, ManagedNodeFacade):
            host = self.host
            bm.manager = host.as_remote_node("/services/Subscription Manager")
            msglog.debug("Replaced BM %s SM proxy with Managed Proxy." % bm)
        return bm
    def invoke_remote_method(self, name, *args):
        """
            Invoke remote method named 'name' with arguments 'args'.
            
            Invocation takes place with gated availability context 
            of remote FW resource.  If resource is unavailable, 
            raise EResourceUnavailable exception immediately.
            If invocation results in in ERNATimeout, resource 
            context notifies resource automatically.
        """
        with self.host.fw_node.available():
            result = self._protocol.rmi(self._service, name, *args)
        return result
    def get_remote_method(self, name):
        """
            Get reference to bound managed proxy method.
            
            Invoking returned callable automatically invokes 
            proxy's 'invoke_remote_method' method, providing 
            name 'name'.
        """
        def method(self, *args):
            return self.invoke_remote_method(name, *args)
        method.__name__ = name
        return new.instancemethod(method, self, type(self))
    _NodeFacade__remote_method = get_remote_method
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))
    def __str__(self):
        typename = type(self).__name__
        return "%s(%r)" % (typename, self.as_node_url())

class NBMManager(CompositeNode):
    """
    NBMManager is the class used to manage remote hosts (NBM's).  Operations that
    are queued on it are delegated to a threadpool for execution.  A typical
    operation would be to ping or to check if the framework is running on the 
    remote host.  The NBMManager can also be used to obtain a (rna) reference to
    a remote NBM.  This is an inherent service running on the NBM-Manager.
    """
    def __init__(self):
        self._hosts = {}
        self._running = False
        self._scheduled = None
        # Default value for Managed Hosts 
        # to use Managed Proxies.
        self.manage_proxies = True
        self._tp = ThreadPool(THREADPOOLSIZE, name='NBMManagerThread')
        super(NBMManager, self).__init__()
        
    def configure(self, config):
        set_attribute(self, 'manage_proxies', True, config, as_boolean)
        return super(NBMManager, self).configure(config)
    
    def configuration(self):
        config = super(NBMManager, self).configuration()
        get_attribute(self, 'manage_proxies', config, str)
        return config
        
    def start(self):
        for host in self.children_nodes():
            self._hosts[host.name] = host
        self._running = True
        return super(NBMManager, self).start()
    
    def stop(self):
        self._running = False
        return super(NBMManager, self).stop()
        
    def get_host(self, hostname):
        host = self._hosts.get(hostname, None)
        if host is None and self.has_child(hostname):
            host = self.get_child(hostname)
            self._hosts[host.name] = host
        else:
            for h in self._hosts.values():
                if h.host == hostname:
                    host = h
                    break
        if host is None:
            err_msg = 'Invalid configuration: NBM Manager is missing host %s' \
                % hostname
            raise EConfiguration(err_msg)
        return host
        
    def queue(self, callback, args=()):
        self._tp.queue_noresult(callback, *args)
    
    def schedule(self, delay, callback, args=()):
        return scheduler.after(delay, self.queue, (callback, args))

class ManagedHost(CompositeNode, EventProducerMixin):
    """
    ManagedHost is the class used to represent a remote NBM that should be
    monitored by the NBMManager service.
    """
    def __init__(self):
        self.host = None
        self.period = 30
        self.last_update = 0
        self.last_refresh = 0
        self.manage_proxies = None
        self.last_state_change = 0
        self.__proxy = None
        self.__fw_node = None
        self.__net_node = None
        self.__lic_node = None
        self.__manager = None
        self._scheduled = None
        self.__entity_root = '/'
        self.__scheme = None
        self._cached_result = None
        self.__cached_remotes = FixedSizeDict()
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
    
    def refreshed(self, touch=False):
        last_refresh = self.last_refresh
        if touch:
            self.last_refresh = uptime.secs()
        return last_refresh
    
    def updated(self, touch=False):
        last_update = self.last_update
        if touch:
            self.last_update = uptime.secs()
        return last_update
    
    def state_changed(self, touch=False):
        last_state_change = self.last_state_change
        if touch:
            self.last_state_change = uptime.secs()
        return last_state_change
    
    def since_update(self):
        return uptime.secs() - self.updated()
    
    def since_refresh(self):
        return uptime.secs() - self.refreshed()
    
    def _reset_result(self):
        result = Result({"net": None, "framework": None}, 0, 1, 0)
        self.last_update = 0
        self.last_refresh = 0
        self._cached_result = result
    
    def start(self):
        if self.manage_proxies is None:
            self.manage_proxies = self.parent.manage_proxies
        self.__cached_remotes.clear()
        scheduled = self._scheduled
        if scheduled:
            scheduled.cancel()
        self._reset_result()
        self.schedule_refresh(30)
        return CompositeNode.start(self)
    
    def stop(self):
        scheduled = self._scheduled
        if scheduled:
            scheduled.cancel()
        self.__cached_remotes.clear()
        self._scheduled = None
        self._reset_result()
        return CompositeNode.stop(self)
    
    def configure(self, cd):
    	# reset the scheme
    	self.__scheme = None
        set_attribute(self, 'host', REQUIRED, cd)
        set_attribute(self, 'security_level', 'NoSec', cd)
        set_attribute(self, 'manage_proxies', None, cd, as_boolean)
        return CompositeNode.configure(self, cd)
    
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'host', cd)
        get_attribute(self, 'security_level', cd)
        get_attribute(self, 'manage_proxies', cd, str)
        return cd
    
    def get_child(self, name):
        if name in set(["aliases", "interfaces", "services"]):
            return self.as_remote_node("/%s" % name)
        return CompositeNode.get_child(self, name)
            
    def has_cov(self):
        return True
    
    def get_proxy(self):
        return self.proxy
    
    def get(self, asyncok=True):
        return self.get_result().value
        
    def get_result(self, skipcache=0):
        if skipcache or not self._cached_result:
            self.refresh_children()
        return self._cached_result
        
    def schedule_refresh(self, delay):
        scheduled = self._scheduled
        if scheduled and scheduled.executable():
            scheduled.cancel()
        self._scheduled = self.parent.schedule(delay, self.refresh_children)
        return self._scheduled
    
    def refresh_children(self):
        # See CSCtq56038 re: assumptions to reduce network chattiness.
        communicating = False
        present_value = self.get().values()
        was_online = present_value[0] and present_value[1]
        for node in [self.lic_node, self.fw_node, self.net_node]:
            try:
                communicating = node.refresh_value()
            except:
                msglog.warn("Failed to refresh host information: %s" % node)
            if communicating and was_online:
                # we can break early, remains online.
                break
        self.refreshed(True)
        if not self._scheduled or not self._scheduled.executable():
            self.schedule_refresh(self.period)
        self.update_cache()
    
    def update_cache(self):
        self.updated(True)
        fwstatus = self.fw_node.get()
        netstatus = int(bool(self.net_node.get()))
        value = {"net": netstatus, "framework": fwstatus}
        if self._cached_result:
            previous = self._cached_result.value
            if value == previous:
                return
            changes = self._cached_result.changes + 1
        else:
            changes = 1
            previous = None
        self._cached_result = Result(value, self.refreshed(), 1, changes)
        event = ChangeOfValueEvent(self, previous, value, time.time())
        self.event_generate(event)
        self.state_changed(True)
    
    def event_subscribe(self, *args):
        result = EventProducerMixin.event_subscribe(self, *args)
        event = ChangeOfValueEvent(self, self.get(), self.get(), time.time())
        self.event_generate(event)
        return result
    
    def as_remote_node(self, path):
        node = self.__cached_remotes.get(path)
        if not node:
            facade = self.create_facade(path)
            # Atomic set-default eliminates race-condition by 
            # ensuring returned node-facades are always the cached one.
            node = self.__cached_remotes.setdefault(path, facade)
        return node
    
    def create_facade(self, path):
        if path.startswith('/'):
            uripath = path[1:]
        else:
            uripath = path
        url = '%s://%s/%s' % (self.scheme, self.host, uripath)
        if self.manage_proxies:
            cd = {"host": self.host}
            protocol = RNA_CLIENT_MGR.getSimpleTextProtocol(cd, self.scheme)
            facade = ManagedNodeFacade(self, url, path, protocol)
        else:
            facade = as_node(url)
        return facade
    
    def set_entity_root(self, path):
        self.__entity_root = path
        
    def get_entity_root(self):
        return self.__entity_root
    
    def skip_cache(self):
        for child in self.children_nodes():
            child.skip_cache()
        self._cached_result = None
            
    def get_fw_node(self):
        return self.fw_node
    
    def _get_proxy(self):
        if self.__proxy is None:
            uri = 'mpx://%s/' % self.host
            self.__proxy = as_node(uri)
        return self.__proxy
    
    proxy = property(_get_proxy)
    
    def _get_manager(self):
        if self.__manager is None:
            self.__manager = self.parent
        return self.__manager
    
    manager = property(_get_manager)
    
    def _get_fw_node(self):
        if self.__fw_node is None:
            for child in self.children_nodes():
                if isinstance(child, RemoteFWStatus):
                    self.__fw_node = child
                    break
        if self.__fw_node is None:
            err_msg = 'Invalid configuration: Missing remote framework status detector.'
            raise EConfiguration(err_msg)
        return self.__fw_node
    
    fw_node = property(_get_fw_node)
    
    def _get_net_node(self):
        if self.__net_node is None:
            for child in self.children_nodes():
                if isinstance(child, RemoteNetworkStatus):
                    self.__net_node = child
                    break
        if self.__net_node is None:
            err_msg = 'Invalid configuration: Missing remote network status detector.'
            raise EConfiguration(err_msg)
        return self.__net_node
    
    net_node = property(_get_net_node)
    
    def _get_lic_node(self):
        if self.__lic_node is None:
            for child in self.children_nodes():
                if isinstance(child, LicenseDetailsContainer):
                    self.__lic_node = child
                    break
        if self.__lic_node is None:
            err_msg = 'Invalid configuration: Missing remote license management node.'
            raise EConfiguration(err_msg)
        return self.__lic_node
    
    lic_node = property(_get_lic_node)
    
    def _get_scheme(self):
    	if self.__scheme is None:
        	self.__scheme = {
                'Auth-Only':'mpxao', 
                'Full-Enc':'mpxfe'}.get(self.security_level, 'mpx')
        return self.__scheme
    
    scheme = property(_get_scheme)
    
class Status(CompositeNode, EventProducerMixin):
    """
    Status is the base class used by different host management services.  It's 
    primary role is to serve as an event producer and interact with the NBMManager
    class in a consistent manner.  Classes derived from Status will implement the
    _get_status method to determine (i.e ping) the course of action that should
    be taken to interact with the remote NBM.
    """
    def __init__(self):
        self._last_rcvd = 0
        self._subscribers = 0
        self._scheduled = None
        self._skip_cache = False
        self._cached_result = None
        self._exec_delay = _Buffer(5)
        self._subscription_lock = Lock()
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'ttl', 300, cd, int)
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'ttl', cd)
        return cd
    
    # _get_status must be implemented by derived classes
    def _get_status(self):
        raise ENotImplemented()
    
    def has_cov(self):
        return 1
        
    def event_has_subscribers(self):
        return bool(self._subscribers)
    
    def event_subscribe(self, *args):
        self._subscription_lock.acquire()
        try:
            already_subscribed = self.event_has_subscribers()
            result = EventProducerMixin.event_subscribe(self, *args)
            self._subscribers += 1
        finally:
            self._subscription_lock.release()
        if not already_subscribed and self._cached_result:
            value = self._cached_result.value
            self._trigger_cov(value, value, time.time())
        return result

    def event_unsubscribe(self, *args):
        self._subscription_lock.acquire()
        try:
            EventProducerMixin.event_unsubscribe(self, *args)
            self._subscribers = max(0, self._subscribers - 1)
        finally:
            self._subscription_lock.release()
       
    def skip_cache(self):
        # forces an update if there are consumers.
        self._cached_result = None    
    
    def refresh_value(self):
        status = self._get_status()
        self.update_value(status)
        return bool(status)
        
    def update_value(self, value):
        if self._cached_result:
            previous = self._cached_result.value
            if value == previous:
                return False
            changes = self._cached_result.changes + 1
        else:
            changes = 1
            previous = None
        self._cached_result = Result(value, uptime.secs(), 1, changes)
        self._trigger_cov(previous, value, time.time())
        return True
    
    def get(self, asyncok=True):
        return self.get_result().value
    
    def get_result(self, skipCache=0):
        if not self._cached_result or skipCache:
            self.refresh_value()
        return self._cached_result

    def _trigger_cov(self, old_value, new_value, timestamp=None):
        if not timestamp:
            timestamp = time.time()
        cov = ChangeOfValueEvent(self, old_value, new_value, timestamp)
        self.event_generate(cov)
        
    # compensate for the average delay in future scheduling considerations.
    def _get_exec_delay(self):
        avg_delay = 0
        for delay in self._exec_delay:
            avg_delay += delay
        if avg_delay:
            avg_delay = avg_delay / len(self._exec_delay)
        return avg_delay
    exec_delay = property(_get_exec_delay)
    
class RemoteNetworkStatus(Status):
    """
        Class used to execute ICMP echo requests to 
        see if a remote NBM is online.
    """
    def configure(self, cd):
        super(RemoteNetworkStatus, self).configure(cd)
        set_attribute(self, 'count', 1, cd, int)
    def configuration(self):
        cd = super(RemoteNetworkStatus, self).configuration()
        get_attribute(self, 'count', cd, str)
        return cd
    def _get_status(self):
        return ping(self.parent.host, self.count)

class Resource(Status):
    """
        Node representation of resource which which 
        has "available" and "unavailble" states.
        
        Provides context-manager/object to easily leverage 
        and update availability data.
        
        Used as a context-manager directly, execution of the 
        context-suite may automatically catch failures indicating 
        unavailability, and update resource status accordingly.
        
        Using the context-expression "available()", callers can 
        leverage Resource's current status to gate entry into 
        context-suite.  If the resource is current unavailable, 
        the context-expression raises an exception and the context 
        is never entered.  Once entered, the normal Resource context 
        benefits apply: automatic modification of availability.
    """
    def lock(self, blocking=True):
        """
            Stub for context-manager based status nodes 
            which require locking around status query and 
            update operations.
            
            Subclasses requiring locking should override this method.            
        """
        return True
    def unlock(self):
        """
            Stub for context-manager based status nodes 
            which require locking around status query and 
            update operations.
            
            Subclasses requiring locking should override this method.            
        """
        pass
    def locked(self):
        """
            Stub for context-manager based status nodes 
            which require locking around status query and 
            update operations.
            
            Subclasses requiring locking should override this method.            
        """
        return False
    def is_available(self):
        """
            Is resource this node represents currently available?
        """
        return bool(self.get())
    def notify_unavailable(self):
        """
            Notify resource node that resource is not available.
            
            Invoked asynchronously by clients of resource when attempts 
            to interact with resource fail due to unavailability.
        """
        if self.update_value(0):
            self.parent.update_cache()
    def notify_available(self):
        """
            Notify resource node that resource is available.
            
            Invoked asynchronously by clients of resource when attempts 
            to interact with resource succeed, indicating availability.
        """
        if self.update_value(1):
            self.parent.update_cache()
    def available(self):
        """
            Get Resource context object if resource is available.
            
            If resource is unavailable: raise EResourceUnavailable.
        """
        if not self.is_available():
            raise EResourceUnavailable(self.as_node_url())
        return self
    def __enter__(self):
        """
            Stub context object entry method.  Locks resource.
        """
        self.lock()
    def __exit__(self, type, error, traceback):
        """
            Stub context object exit method.  Unlocks resource.
            
            Errors thrown by with-suite will be reraised upon exit.
            
            Empty return emphasizes non-true return to reraise errors.
        """
        self.unlock()
        return

class RemoteFWStatus(Resource):
    """
        Class that utilizes RNA to see if a remote NBM's 
        framework is online.
        
        Extends Resource with automatic timeout functionality, 
        triggering a change to "unavailable" state 15 seconds 
        after starting an attempt to refresh.
    """
    def __init__(self):
        self.status_proxy = None
        super(RemoteFWStatus, self).__init__()
    def __exit__(self, type, error, traceback):
        """
            Catch ERNATimeout type exceptions and automatically 
            set resource status to unavailable; else, set status 
            to available.
            
            RNA commands invoked within Resource context are 
            leveraged to update resource availability.
        """
        try:
            if isinstance(error, ERNATimeout):
                msglog.warn("Resource %s operation timed out." % self)
                self.notify_unavailable()
            else:
                self.notify_available()
        finally:
            self.unlock()
    def get_status_node(self):
        if not self.status_proxy:
            self.lock()
            try:
                if not self.status_proxy:
                    services = self.parent.proxy.get_child("services")
                    self.status_proxy = services.get_child("status")
            finally:
                self.unlock()
        return self.status_proxy
    def _get_status(self):
        is_running = True
        try:
            self.get_status_node().get()
        except:
            is_running = False
        return int(is_running)

class _Buffer(object):
    """
        A class used to provide a configurable, fixed size, 
        circular buffer that can be used for collecting data.
    """
    class Iterator:
        def __init__(self, data):
            self.data = data[:]
            self.data.reverse()
        
        def __iter__(self):
            return self
            
        def next(self):
            if not self.data:
                raise StopIteration
            return self.data.pop()
            
    def __init__(self, length):
        self._data = []
        self._full = 0
        self._max = length
        self._cur = 0

    def append(self, x):
        if self._full == 1:
            for i in range (0, self._cur - 1):
                self._data[i] = self._data[i + 1]
            self._data[self._cur - 1] = x
        else:
            self._data.append(x)
            self._cur += 1
            if self._cur == self._max:
                self._full = 1

    def clear(self):
        self._data = []
        self._cur = 0
        self._full = 0

    def __len__(self):
        return self._cur

    def __iter__(self):
        return _Buffer.Iterator(self._data)

#@fixme - should be LRU.
class FixedSizeDict(dict):
    """
        A class used to provide a fixed size dictionary.
    """
    def __init__(self, size=100):
        dict.__init__(self)
        self._maxsize = size
        self._stack = []

    def __setitem__(self, name, value):
        if len(self._stack) >= self._maxsize:
            self.__delitem__(self._stack[0])
            del self._stack[0]
        if name in self._stack:
            self._stack.remove(name)
        self._stack.append(name)
        return dict.__setitem__(self, name, value)


