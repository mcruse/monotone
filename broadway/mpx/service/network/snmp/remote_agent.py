"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

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

from time import time as now

from pyasn1.type import base

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto.error import ProtocolError

from mpx.lib import Result
from mpx.lib import msglog
from mpx.lib import thread_pool

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.exceptions import EAbstract
from mpx.lib.exceptions import EInternalError
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import EUnreachableCode

from mpx.lib.node import CompositeNode

from mpx.lib.scheduler import scheduler

import SNMP
import batching

class SNMPvConfiguration(CompositeNode):
    def _auth_data(self):
        raise EAbstract()
    def start(self):
        assert self.name == self.__class__.__name__
        super(SNMPvConfiguration, self).start()
        return

class SNMPv1or2c(SNMPvConfiguration):
    __node_id__ = 'b46fcc98-48b8-41b4-99a7-7614f2f38c6e'
    def __init__(self):
        super(SNMPv1or2c, self).__init__()
        self.security_name = 'default'
        self.community_name = REQUIRED
        self.version = REQUIRED
        return
    def configure(self, cd):
        super(SNMPv1or2c, self).configure(cd)
        set_attribute(self, 'security_name', 'default', cd)
        set_attribute(self, 'community_name', REQUIRED, cd)
        set_attribute(self, 'version', REQUIRED, cd, str)
        return
    def configuration(self):
        cd = super(SNMPv1or2c, self).configuration()
        get_attribute(self, 'security_name', cd)
        get_attribute(self, 'community_name', cd)
        get_attribute(self, 'version', cd)
        return cd
    def start(self):
        assert self.version in ('1', '2c')
        super(SNMPv1or2c, self).start()
        return
    def _auth_data(self):
        if self.version == '1':
            return cmdgen.CommunityData(self.security_name,
                                        self.community_name,
                                        0)
        elif self.version == '2c':
            return cmdgen.CommunityData(self.security_name,
                                        self.community_name,
                                        1)
        raise EInvalidValue('self.version', self.version)

class SNMPv1(SNMPv1or2c):
    __node_id__ = '5c2acb7d-ea90-4328-8acb-559d9e5e22d5'
    version_constant = '1'
    def configure(self, cd):
        set_attribute(self, 'version', self.version_constant, cd, str)
        super(SNMPv1, self).configure(cd)
        return
    def configuration(self):
        cd = super(SNMPv1, self).configuration()
        del cd['version']
        return cd
    def start(self):
        assert self.version == self.version_constant
        super(SNMPv1, self).start()
        return

class SNMPv2c(SNMPv1):
    __node_id__ = '0b09a7b7-24f7-4624-a593-592a6ad646e6'
    version_constant = '2c'

class SNMPv3(SNMPvConfiguration):
    __node_id__ = 'b3b2f4b8-00b0-489b-ac72-b1495e7910b7'
    AUTHENTICATION_PROTOCOLS = {
        # Literal cmdgen names
        'usmHMACMD5AuthProtocol':cmdgen.usmHMACMD5AuthProtocol,
        'usmHMACSHAAuthProtocol':cmdgen.usmHMACSHAAuthProtocol,
        'usmNoAuthProtocol':cmdgen.usmNoAuthProtocol,
        # Slightly more human readable
        'MD5':cmdgen.usmHMACMD5AuthProtocol,
        'SHA':cmdgen.usmHMACSHAAuthProtocol,
        'No Authentication':cmdgen.usmNoAuthProtocol,
        }
    PRIVACY_PROTOCOLS = {
        # Literal cmdgen names
        'usmDESPrivProtocol':cmdgen.usmDESPrivProtocol,
        'usmAesCfb128Protocol':cmdgen.usmAesCfb128Protocol,
        'usmNoPrivProtocol':cmdgen.usmNoPrivProtocol,
        # Slightly more human readable
        'DES':cmdgen.usmDESPrivProtocol,
        'Aes':cmdgen.usmAesCfb128Protocol,
        'No Privacy':cmdgen.usmNoPrivProtocol,
        }
    def __init__(self):
        super(SNMPv3, self).__init__()
        self.username = REQUIRED
        self.authentication_key = ''
        self.privacy_key = ''
        self.authentication_protocol = 'usmNoAuthProtocol'
        self.privacy_protocol = 'usmNoPrivProtocol'
        self.version = '3'
        self.__authentication_protocol = None
        self.__privacy_protocol = None
        return
    def configure(self, cd):
        super(SNMPv3, self).configure(cd)
        set_attribute(self, 'username', REQUIRED, cd)
        set_attribute(self, 'authentication_key', '', cd)
        set_attribute(self, 'privacy_key', '', cd)
        set_attribute(self, 'authentication_protocol', 'usmNoAuthProtocol', cd)
        set_attribute(self, 'privacy_protocol', 'usmNoPrivProtocol', cd)
        return
    def configuration(self):
        cd = super(SNMPv3, self).configuration()
        set_attribute(self, 'username', cd)
        get_attribute(self, 'authentication_key', cd)
        get_attribute(self, 'privacy_key', cd)
        get_attribute(self, 'authentication_protocol', cd)
        get_attribute(self, 'privacy_protocol', cd)
        return cd
    def start(self):
        valid_authentication_protocols = self.AUTHENTICATION_PROTOCOLS.keys()
        valid_privacy_protocols = self.PRIVACY_PROTOCOLS.keys()
        assert self.authentication_protocol in valid_authentication_protocols
        self.__authentication_protocol = (
            self.AUTHENTICATION_PROTOCOLS[self.authentication_protocol]
            )
        assert self.privacy_protocol in valid_privacy_protocols
        self.self.__privacy_protocol = (
            self.PRIVACY_PROTOCOLS[self.privacy_protocol]
            )
        super(SNMPv3, self).start()
        return
    def _auth_data(self):
        return cmdgen.UsmUserData(self.username,
                                  self.authentication_key,
                                  self.privacy_key,
                                  self.__authentication_protocol,
                                  self.__privacy_protocol)

##
# An Oid node is just a place holder in the tree.  At some point we may want to
# differentiate the types of nodes, especially for table manipulation.  But
# not today.
class Oid(CompositeNode):
    __node_id__ = 'e41e2921-5d50-44dc-864e-aadc5e7f8122'
    def __init__(self, parent=None, info=None):
        super(Oid, self).__init__()
        self.oid_element = REQUIRED
        # @note PySNMP caches the SMI, so it's pretty effecient for each
        #       Oid node to reference it's SMI.
        # @note It is rarely used though and there are a TON of Oids so maybe
        #       we should just look it up.
        self.__smi = None
        # Both parent and info must be None, or both must not be None
        assert (parent is None) == (info is None)
        if parent is not None:
            self.__cfg_from_info(parent, info)
        return
    def __cfg_from_info(self, parent, info):
        # @note PySNMP caches the SMI, so it's pretty effecient for each
        #       Oid node to reference it's SMI.
        # @note It is rarely used though and there are a TON of Oids so maybe
        #       we should just look it up.
        self.__smi = info.smi
        self.configure({
            'parent':parent,
            'name':info.oid_name,
            'oid_element':info.oid[-1]
            })
        return
    ##
    # @note There are a TON of Oids and 'Managed Objects' is rarely used (only
    #       for discovery) so it's better not to have it as an attribute
    #       methinks.
    # @fixme Break out into a helper function, no need to be on the class.
    def __find_managed_objects(self):
        ancestor = self.parent
        while True:
            if isinstance(ancestor, Oid):
                pass
            elif isinstance(ancestor, ManagedObjects):
                return ancestor
            else:
                raise EInternalError(
                    "Invalid class %r in Oid node tree at %s" %
                    (ancestor.__class__.__name__, ancestor.as_node_url())
                    )
            ancestor = ancestor.parent
        raise EUnreachableCode()
    def describe_oid(self):
        ancestor = self.parent
        my_oid = (int(self.oid_element),)
        while True:
            if isinstance(ancestor, Oid):
                my_oid = (int(ancestor.oid_element),) + my_oid
            elif isinstance(ancestor, RemoteAgent):
                return ancestor.describe_oid(my_oid)
            elif isinstance(ancestor, ManagedObjects):
                pass
            else:
                raise EInternalError(
                    "Invalid class %r in Oid node tree at %s" %
                    (ancestor.__class__.__name__, ancestor.as_node_url())
                    )
            ancestor = ancestor.parent
        raise EUnreachableCode()
    def configure(self, cd):
        super(Oid, self).configure(cd)
        set_attribute(self, 'oid_element', REQUIRED, cd, int)
        return
    def configuration(self):
        cd = super(Oid, self).configuration()
        get_attribute(self, 'oid_element', cd)
        return cd
    def start(self):
        super(Oid, self).start()
        if self.__smi is None and self.oid_element is not REQUIRED:
            # @note PySNMP caches the SMI, so it's pretty effecient for each
            #       Oid node to reference it's SMI.
            self.__smi = self.describe_oid().smi
        return
    ##
    # @fixme Change to match existing discover hooks.
    def discover(self):
        self.__find_managed_objects().batch_all_from(self.__smi.name,True)
        return
    def getSMI(self):
        return self.__smi
    def getLabel(self):
        return self.__smi.getLabel()
    def getName(self):
        return self.__smi.getName()

##
# Leaf-node that provides access to an SNMP variable on a device.  Someday we
# may want to sub-class by access and or data type.
class ScalarInstance(CompositeNode):
    __node_id__ = 'd62752e5-c1c5-4bfc-9fa4-111823c5b180'
    def __init__(self, parent=None, info=None):
        super(ScalarInstance, self).__init__()
        self.__cache_ttl = -1
        self.__agent = None
        self.__smi = None
        self.__var_name = None
        # By using a valid, but expired __cached_result the number of checks
        # can be reduced.
        self.__cached_result = Result(None, 0, 0, 0)
        self.index = REQUIRED
        # Both parent and info must be None, or both must NOT be None
        assert (parent is None) == (info is None)
        if parent is not None:
            self.__cfg_from_info(parent, info)
        return
    ##
    # @fixme Break out into a helper function, no need to be on the class.
    def __find_agent(self):
        agent = self.parent
        while True:
            if isinstance(agent, RemoteAgent):
                return agent
            agent = agent.parent
        raise EUnreachableCode()
    def __cfg_from_info(self, parent, info):
        self.__smi = info.smi
        self.configure({
            'parent':parent,
            # @fixme Name might have other encodings (like readable strings,
            #        Hex-Strings, etc...
            'name':'.'.join(map(str, info.index)),
            # @note Configurable index is ALWAYS in decimal-dot form.
            'index':'.'.join(map(str, info.index)),
            })
        return
    def __find_smi(self):
        ancestor = self.parent
        var_name = tuple(map(int, self.index.split('.')))
        while True:
            if isinstance(ancestor, Oid):
                var_name = (int(ancestor.oid_element),) + var_name
            elif isinstance(ancestor, RemoteAgent):
                return ancestor.describe_oid(var_name).smi
            elif isinstance(ancestor, ManagedObjects):
                pass
            else:
                raise EInternalError(
                    "Invalid class %r in Oid node tree at %s" %
                    (ancestor.__class__.__name__, ancestor.as_node_url())
                    )
            ancestor = ancestor.parent
        raise EUnreachableCode()
    def is_writable(self):
        return self.getMaxAccess().lower() in ('readwrite', 'readcreate')
    def is_readable(self):
        return self.getMaxAccess().lower() != 'noaccess'
    def start(self):
        super(ScalarInstance, self).start()
        if self.__smi is None and self.index is not REQUIRED:
            self.__smi = self.__find_smi()
        if self.__smi is not None and self.index is not REQUIRED:
            self.__var_name = (
                self.__smi.name + tuple(map(int, self.index.split('.')))
                )
        if self.__agent is None:
            self.__agent = self.__find_agent()
        if self.__agent is not None:
            if self.cache_ttl < 0:
                # A cache_ttl of -1 means to use the agent's cache_ttl.
                self.__cache_ttl = self.__agent.cache_ttl
            else:
                self.__cache_ttl = self.cache_ttl
        if (not hasattr(self.__smi, 'getMaxAccess') and
            self.getDescription is not self.__emptyStub):
            # @fixme self.__smi is probably a MibIdentifier because there is
            #        not in a loaded MIB.
            msglog.log(
                "SNMP", msglog.types.INFO,
                "ScalarInstance %r is of unknown type." % (self.as_node_url(),)
                )
            self.getDescription = self.__emptyStub
            self.getMaxAccess = self.__emptyStub
            self.getReference = self.__emptyStub
            self.getStatus = self.__emptyStub
            self.getSyntax = self.__emptyStub
            self.getUnits = self.__emptyStub
        else:
            if self.is_writable():
                self.set = self._set
            else:
                if hasattr(self, 'set'):
                    del self.set
        return
    def stop(self):
        super(ScalarInstance, self).stop()
        if self.is_writable():
            if hasattr(self, 'set'):
                del self.set
        return
    def configure(self, cd):
        super(ScalarInstance, self).configure(cd)
        set_attribute(self, 'index', REQUIRED, cd)
        set_attribute(self, 'cache_ttl', -1, cd, int)
        return
    def configuration(self):
        cd = super(ScalarInstance, self).configuration()
        get_attribute(self, 'cache_ttl', cd, str)
        get_attribute(self, 'index', cd)
        return cd
    ##
    # @fixme Change to match existing discover hooks.
    def discover(self):
        # Always a leaf node...
        return
    def _update_cached_value(self, value):
        self.__cached_result = Result(value, now(), 1,
                                      self.__cached_result.changes+1)
        return
    def get(self, skipCache=0):
        return self.get_result(skipCache).value
    def get_result(self, skipCache=0, **keywords):
        if not skipCache:
            dt = now() - self.__cached_result.timestamp
            if dt > self.__cache_ttl:
                skipCache = 1
        if skipCache:
            value = self.__agent.snmp_get(self.__var_name)[1]
            result = Result(value, now(), 0, self.__cached_result.changes+1)
            self.__cached_result = Result(result.value, result.timestamp,
                                         1, result.changes)
            return result
        return self.__cached_result
    def _set(self, value, asyncOK=0):
        self.__cached_result = Result(None, 0, 0, 0)
        if not isinstance(value, base.Asn1Item):
            asn1_value = self.__smi.syntax.clone(value)
        else:
            asn1_value = value
        self.__agent.snmp_set(self.__var_name, asn1_value)
        return
    def __emptyStub(self):
        return ''
    def getSMI(self):
        return self.__smi
    def getDescription(self):
        return self.__smi.getDescription()
    def getLabel(self):
        return self.__smi.getLabel()
    def getMaxAccess(self):
        return self.__smi.getMaxAccess()
    def getName(self):
        return self.__smi.getName()
    def getReference(self):
        return self.__smi.getReference()
    def getStatus(self):
        return self.__smi.getStatus()
    def getSyntax(self):
        return self.__smi.getSyntax()
    def getUnits(self):
        return self.__smi.getUnits()
    def as_oid(self):
        return self.__var_name
    def get_batch_manager(self):
        return self.__agent

class ManagedObjects(CompositeNode):
    __node_id__ = '52ef9e29-bb72-423b-b7b0-b949cfe7542f'
    FALSE = 0
    TRUE = 1
    MAYBE = 2
    def __init__(self):
        super(CompositeNode, self).__init__()
        self.__agent = None
        self.__supports_bulk = self.MAYBE
        return
    def start(self):
        super(ManagedObjects, self).start()
        self.__agent = self.parent
        #
        # Use node_from_oid to pre-populate the standard SMTP tree.
        #
        # iso.org.dod.internet.mgmt
        self.node_from_oid((1,3,6,1,2,), True)
        # iso.org.dod.internet.private.enterprises
        self.node_from_oid((1,3,6,1,4,1), True)
        if self.__agent.snmp_version() > '1':
            # iso.org.dod.internet.snmpV2
            self.node_from_oid((1,3,6,1,6,), True)
            # iso.org.dod.internet.mgmt.mib-2
            self.node_from_oid((1,3,6,1,2,1), True)
            for oid in range(1,8) + range(10,12):
                # iso.org.dod.internet.mgmt.mib-2.*
                self.node_from_oid((1,3,6,1,2,1,oid,), True)
        return
    ##
    # @fixme Change to match existing discover hooks.
    def discover(self):
        self.batch_all_from((1,3,),True)
        return
    def node_from_oid(self, oid, create=False):
        info = self.__agent.describe_oid(oid)
        full_path = os.path.join(
            self.as_node_url(), *(
                info.matched_label + ('.'.join(map(str,info.index)),)
                )
            )
        if create:
            try:
                return self.as_node(full_path)
            except ENoSuchName:
                pass
            parent = self.parent
            child = self
            oid_stack = list(info.matched_oid)
            label_stack = list(info.matched_label)
            oid_path = []
            while len(oid_stack):
                label_element = label_stack.pop(0)
                oid_element = oid_stack.pop(0)
                oid_path.append(oid_element)
                child_name = label_element
                if child.has_child(child_name):
                    parent = child
                    child = child.get_child(child_name)
                    continue
                # OK, create the sucker.
                child_info = self.__agent.describe_oid(tuple(oid_path))
                assert not len(child_info.index), (
                    "Failure to match oid in MIB."
                    )
                parent = child
                child = Oid(parent, child_info)
                child.start()
            parent = child
            if len(info.index):
                # Create the scalar leaf.
                child = ScalarInstance(parent, info)
                child.start()
            return child
        return self.as_node(full_path)
    def batch_all_from(self, oid, create=False):
        if self.__supports_bulk is self.MAYBE:
            try:
                result = self.__agent.snmp_getbulk(0, 50, oid)
                self.__supports_bulk = self.TRUE
            except ProtocolError, e:
                result = self.__agent.snmp_getnext(oid)
                self.__supports_bulk = self.FALSE
        elif self.__supports_bulk is self.TRUE:
            result = self.__agent.snmp_getbulk(0, 50, oid)
        else:
            result = self.__agent.snmp_getnext(oid)
        while len(result):
            try:
                while len(result):
                    managed_tuple = result.pop()
                    scalar = self.node_from_oid(managed_tuple[0], create)
                    scalar._update_cached_value(managed_tuple[1])
            except ENoSuchName:
                if not create:
                    continue
                raise
        return

class NodeBrowserAction(CompositeNode):
    __node_id__ = '35d425b9-3432-4808-ab75-527ab17b50ba'
    class HtmlObject(object):
        def __init__(self, o):
            self.__object = o
            return
        def __str__(self):
            return str(self.__object)
        def __repr__(self):
            return repr(self.__object)
    def __init__(self):
        self.get_text = REQUIRED
        return
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'get_text', REQUIRED, cd,
                      NodeBrowserAction.HtmlObject)
        return
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'get_text', cd, str)
        return cd
    def get(self, skipCache=0):
        return self.get_text

class RemoteAgents(CompositeNode):
    __node_id__ = '13df33f2-1f46-48fa-9b44-2bbfcca4325f'

class RemoteAgent(CompositeNode):
    __node_id__ = '43b9b1c9-4348-4e14-8a90-0fa84541a3ea'
    MANAGED_OBJECTS = "Managed Objects"
    NODEBROWSER_DISCOVER = "Node Browser Discover"
    NODEBROWSER_CACHED_REPORT = "Node Browser Cached Report"
    def __init__(self):
        super(RemoteAgent, self).__init__()
        self.snmp_service = None
        self.address = REQUIRED
        self.port = 161
        self.mib_table = []
        self.cache_ttl = 60.0
        self.discover_at_start = 0
        self.max_batch_size = 0
        self.__cfg = None
        self.__auth_data = None
        self.__transport = None
        self.__managed_objects = None
        self.__discover_event = None
        self.__discover_attempts = 0
        self.__discover_delays = (
            0, 15, 30, 60,
            300, 300, 300,
            600, 600, 600, 600, 600, 600,
            900
            )
        return
    def __schedule_discover(self):
        delay = self.__discover_delays[min(self.__discover_attempts,
                                           len(self.__discover_delays)-1)]
        msglog.log("SNMP", msglog.types.INFO,
                   "Discover of %r scheduled in %r seconds." %
                   (self.as_node_url(), delay))
        self.__discover_event = scheduler.after(delay, self.__queue_discover)
        return
    def __queue_discover(self):
        # @fixme There are not many LOW threads, so this is not a great
        #        solution for more than one or two SNMP devices.  Creating
        #        a transient thread would likely be better...
        thread_pool.LOW.queue_noresult(self.__discover)
        return
    def __discover(self):
        self.__discover_event = None
        try:
            msglog.log("SNMP", msglog.types.INFO,
                       "Starting discovery of %r." % self.as_node_url())
            self.__discover_attempts += 1
            self.__managed_objects.discover()
            msglog.log("SNMP", msglog.types.INFO,
                       "Completed discovery of %r." % self.as_node_url())
        except:
            msglog.exception()
            msglog.log("SNMP", msglog.types.ERR, "Discover of %r failed." %
                       self.as_node_url())
            self.__schedule_discover()
        return
    def configure(self, cd):
        super(RemoteAgent, self).configure(cd)
        set_attribute(self, 'address', REQUIRED, cd)
        set_attribute(self, 'port', 161, cd, int)
        set_attribute(self, 'mib_table', [], cd)
        set_attribute(self, 'cache_ttl', 60.0, cd, float)
        set_attribute(self, 'discover_at_start', 0, cd, as_boolean)
        set_attribute(self, 'max_batch_size', 0, cd, int)
        return
    def configuration(self):
        cd = super(RemoteAgent, self).configuration()
        get_attribute(self, 'address', cd)
        get_attribute(self, 'port', cd, str)
        get_attribute(self, 'mib_table', cd)
        get_attribute(self, 'cache_ttl', cd, str)
        get_attribute(self, 'discover_at_start', cd, as_boolean)
        get_attribute(self, 'max_batch_size', cd, str)
        return cd
    def start(self):
        self.__cfg = None
        for cfg_name in ('SNMPv1','SNMPv2c','SNMPv3','SNMPv1or2c',):
            if self.has_child(cfg_name):
                assert self.__cfg is None
                __cfg = self.get_child(cfg_name)
                if __cfg.enabled:
                    self.__cfg = __cfg
        assert self.__cfg is not None
        self.__auth_data = self.__cfg._auth_data()
        self.__transport = cmdgen.UdpTransportTarget(
            (self.address, self.port)
            )
        self.snmp_service = self.parent
        while not isinstance(self.snmp_service, SNMP.SNMP):
            self.snmp_service = self.snmp_service.parent
        for mib_row in self.mib_table:
            mib_name = mib_row['name']
            if mib_name:
                self.snmp_service.load_mib(mib_name)
        if not self.has_child(self.MANAGED_OBJECTS):
            managed_objects = ManagedObjects()
            managed_objects.configure({'parent':self,
                                       'name':self.MANAGED_OBJECTS})
            managed_objects.start()
        self.__managed_objects = self.get_child(self.MANAGED_OBJECTS)
        if not self.has_child(self.NODEBROWSER_DISCOVER):
            nodebrowser_discover = NodeBrowserAction()
            nodebrowser_discover.configure({
                'parent':self,
                'name':self.NODEBROWSER_DISCOVER,
                'get_text':(
                "<a href=/nodebrowser%(url)s"
                "?action=invoke&method=discover&Content-Type=text/plain>"
                "Invoke discover() via nodebrowser"
                "</a>"
                ) % {
                'url':self.as_node_url(),
                }
                })
            nodebrowser_discover.start()
        if not self.has_child(self.NODEBROWSER_CACHED_REPORT):
            nodebrowser_cached_report = NodeBrowserAction()
            nodebrowser_cached_report.configure({
                'parent':self,
                'name':self.NODEBROWSER_CACHED_REPORT,
                'get_text':(
                "<a href=/nodebrowser%(url)s"
                "?action=invoke&method=cached_report&Content-Type=text/plain>"
                "Invoke cached_report() via nodebrowser"
                "</a>"
                ) % {
                'url':self.as_node_url(),
                }
                })
            nodebrowser_cached_report.start()
        super(RemoteAgent, self).start()
        if self.discover_at_start:
            self.__schedule_discover()
        return
    def __format_result(self, result):
        text = "repr: %r, str: %r" % (result.value, str(result.value))
        try: text += ", int: %r" % int(result.value)
        except: pass
        try: text += ", float: %r" % float(result.value)
        except: pass
        return text
    def __format_instance(self, n):
        text = ""
        all_empty = True
        for m in (
            'getMaxAccess',
            #'getLabel',
            #'getName',
            #'getReference',
            'getStatus',
            'getSyntax',
            'getUnits',
            ):
            if hasattr(n,m):
                if text:
                    text += '; '
                v = getattr(n,m)()
                all_empty = all_empty and not v
                text += "%s: %r" % (m, v)
        if all_empty:
            text = "NOT FOUND IN MIB: "
            text += '.'.join(map(str,n.getSMI().getName()))
            text += '.' + n.name
        return text
    def __format_description(self, label, description):
        if not description:
            return ''
        text = '\n' + label
        indent = len(label.split('\n'))
        dlist = description.split('\n')
        text += repr(dlist.pop(0))[1:-1] # Quote contents, strip outer quotes.
        while dlist:
            # Quote contents, strip outer quotes.
            text += repr(dlist.pop(0))[1:-1]
        return text
    def __cached_report_walk(self, n, report):
        new_report = report
        if hasattr(n, '_ScalarInstance__cached_result'):
            result = n._ScalarInstance__cached_result
            new_report += n.as_node_url()
            if hasattr(n, 'getDescription'):
                new_report += self.__format_description(
                    '    getDescription: ', n.getDescription()
                    )
            new_report += '\n    '
            new_report += self.__format_instance(n)
            new_report += '\n    '
            new_report += self.__format_result(result)
            new_report += '\n'
            new_report += '\n'
        for c in n.children_nodes():
            new_report = self.__cached_report_walk(c, new_report)
        return new_report
    def cached_report(self):
        report = (
            "%(name)s %(address)s:%(port)s\n\n" % self.configuration()
            )
        report = self.__cached_report_walk(self.__managed_objects,
                                           report)
        return report
    def snmp_version(self):
        return self.__cfg.version
    def snmp_set(self, object_name, object_value):
        assert isinstance(object_value, base.Asn1Item)
        return self.snmp_set_multiple(((object_name, object_value,),))
    def snmp_set_multiple(self, var_binds):
        return self.snmp_service.snmp_set_multiple(self.__auth_data,
                                                   self.__transport,
                                                   var_binds)
    def snmp_get(self, object_name):
        return self.snmp_service.snmp_get_multiple(self.__auth_data,
                                                   self.__transport,
                                                   object_name)[0]
    def snmp_get_multiple(self, *object_names):
        return self.snmp_service.snmp_get_multiple(self.__auth_data,
                                                   self.__transport,
                                                   *object_names)
    def snmp_getnext(self, object_name):
        return self.snmp_getnext_multiple(object_name)
    def snmp_getnext_multiple(self, *object_names):
        return self.snmp_service.snmp_getnext_multiple(self.__auth_data,
                                                       self.__transport,
                                                       *object_names)
    def snmp_getbulk(self, non_repeaters, max_repetitions, object_name):
        return self.snmp_getbulk_multiple(non_repeaters, max_repetitions,
                                          object_name)
    def snmp_getbulk_multiple(self, non_repeaters, max_repetitions,
                              *object_names):
        return self.snmp_service.snmp_getbulk_multiple(self.__auth_data,
                                                       self.__transport,
                                                       non_repeaters,
                                                       max_repetitions,
                                                       *object_names)
    def describe_oid(self, oid):
        result = self.snmp_service.describe_oid(oid)
        return result
    ##
    # @fixme Change to match existing discover hooks.
    def discover(self):
        self.__managed_objects.discover()
        return
    def create_batches(self, sm_node_map):
        return batching.create_batches(self, sm_node_map,
                                       max_batch_size=self.max_batch_size)
    def get_batch(self, batch):
        return batch.get_batch()
