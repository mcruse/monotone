"""
Copyright (C) 2011 Cisco Systems

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

from libewapi import *

from mpx.lib import msglog
from mpx.lib import factory as node_factory
from mpx.lib import Result
from mpx.lib.threading import RLock
from mpx.lib.threading import Lock

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.exceptions import EConfiguration
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENameInUse
from mpx.lib.exceptions import ENotRunning
from mpx.lib.exceptions import EUnreachableCode
from mpx.lib.exceptions import MpxException

from mpx.lib.node import Node
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url

from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GARBAGE_COLLECTOR
from mpx.service.trendmanager.trend import Trend

def new_trend(target,period):
    if target.debug:
        msglog.log('Energywise:', msglog.types.INFO,
            'Configuring trend points' )
    
    if target.trend_node:
        if target.period == period:
            msglog.log('Energywise:', msglog.types.INFO,
                'trend points already configured' )
            return
        else:
            msglog.log('Energywise:', msglog.types.INFO,
                'trend configured for different period' )
            target.trend_node.destroy()
            target.trend_node.prune() 
    if target.debug:
        msglog.log('Energywise:', msglog.types.INFO,
                   'Configuring trend points')
    manager = as_node('/services/Trend Manager/trends')
    # the name of top level domain will be domain name itself only
    if target.domain is '':
        name=target.name
    else:
        name = target.domain + '.' + target.name
    preferences ={'width':800,
                  'points':[{'color':16711680,'y-axis':1},
                            {'color':65280,'y-axis':1},
                            {'color':255,'y-axis':1},
                            {'color':16776960,'y-axis':1},
                            {'color':52224,'y-axis':1},
                            {'color':204,'y-axis':1},
                            {'color':13421568,'y-axis':1},
                            {'color':52428,'y-axis':1},
                            {'color':13369548,'y-axis':1}],
                  'title': name,
                  'background':{'color':2041901},
                  'y-axes':[{'to':'auto','map':{},'enable':1,
                             'type':'numeric','from':'auto'},
                            {'to':'auto','map':{},'enable':0,
                             'type':'binary','from':'auto'}],
                  'text':{'color':13686232,'fontname':'Verdona',
                          'fontsize':12},
                  'timespan':{'value':'1','unit':'hours'},
                  'height':600}
    config = {'name':name,
              'parent':manager,
              'description':"Trend logs for mib points",
              'period':period,
              'points':[{'name':'value','node':target.as_node_url()}],
              'preferences':preferences,
              'externally_managed': True
              }
    trend = Trend()
    trend.configure(config)
    trend.start()
    target.trend_node = manager.get_child(name)
    target.period = period
    if target.debug:
        msglog.log('Energywise:', msglog.types.INFO,
            'period configured %s' %str(period) )
    targetnode = as_node_url(target)
    target_filename = '/var/mpx/log/'+name+'.log.1'
    try:
        GARBAGE_COLLECTOR.register(targetnode, target_filename) #by default GC_ONDELETE
    except:
        msglog.log("EnergywiseManager",msglog.log.INFO,
                   "%r's logfile not registered with garbage_collector" %name)
        msglog.exception()
    return
     
def delete_trend(target):
    if target.trend_node:
        if target.debug:
            msglog.log('Energywise Manager :',msglog.types.INFO,
                       'deleting trend logging')
        target.trend_node.destroy()
        target.trend_node.prune()
        target.period = 0
    return

# By traversing reverse find domain for this switch
def _find_domain(target):
    if target.debug:
        msglog.log('Energywise:', msglog.types.INFO, 'Inside find_domain')

    from energywise_manager import EnergywiseManager
    list_name = []
    parent = target.parent
    while not isinstance(parent, EnergywiseManager):
        list_name.append(parent.name)
        parent = parent.parent
    list_name.reverse()
    str = ''
    size = len(list_name)
    for name in list_name:
        str += name
        size -= 1
        if size != 0:
            str += '.'
    return str   
class EnergywiseError(MpxException):
    pass

class ENoDomainSwitches(EnergywiseError):
    pass

class ESNMPNotEnabled(EnergywiseError):
    pass

class EnergywiseCommunicationFailure(EnergywiseError):
    pass

##
# An immutable dictionary.
class SwitchMap(dict):
    def __init__(self,*args,**kw):
        dict.__init__(self,*args,**kw)
        return
    def _raise_immutable_error(self,*args,**kw):
        raise TypeError("'SwitchMap' is immutable.")
    __setitem__ = _raise_immutable_error
    __delitem__ = _raise_immutable_error
    clear = _raise_immutable_error
    setdefault = _raise_immutable_error
    popitem = _raise_immutable_error
    update = _raise_immutable_error
    def __hash__(self):
        return hash(tuple(self.items()))

def _cpex_switch_cmp(s1,s2):
   return cmp(-int(s1.primary),
               -int(s2.primary))

class EnergywiseDomain(Node):
    def __init__(self):
        self._cpex_lock=RLock() # cpex switch list lock, used for setting/getting the "primary" cpex switch.
        self._cache_lock=Lock() # domain value cache lock.
        self._cpex_switch_map_lock = Lock() # lock for cpex switches cache data structure
        self._cache_value=None
        self._cache_time=0
        self._cpex_switch_map_cache=SwitchMap({})
        self._cpex_switch_map_time=0
        self.ttl=30
        self._reinit()
        return
    def _not_running(self, *args, **kw):
        raise ENotRunning("%r is not running." % self.as_node_url())
    def _empty_domain_usage(self, importance=100, skipCache=False):
        return 0.0
    def _reinit(self):
        self._cpex_switches = []
        self._snmp_switches = []
        self._all_switches = []
        self._all_domains = []
        self.domain = ''
        self.trend_node = None
        self.energywise_domain_usage = self._not_running
        return
    def configure(self, config):
         Node.configure(self, config)
         set_attribute(self, 'ttl', 30, config, int)
         return
    def configuration(self):
         config = Node.configuration(self)
         get_attribute(self, 'ttl', config, str)
         return config
    def start(self):
        self._cpex_lock.acquire()
        try:
            for child in self.children_nodes():
                if isinstance(child,EnergywiseSwitch):
                    if child.PROTOCOL_SNMP == child.protocol:
                        self._snmp_switches.append(child)
                    else:
                        self._cpex_switches.append(child)
                    self._all_switches.append(child)
                elif isinstance(child,EnergywiseDomain):
                    self._all_domains.append(child)
            # elif @fixme magic hook for reverse compatibility.
            if self._snmp_switches and self._cpex_switches:
                raise EConfiguration(
                    "All switches in a domain must be configurtion to use the"
                    " same protocol."
                    )
            self._cpex_switches.sort(_cpex_switch_cmp) 
        finally:
            self._cpex_lock.release()
        if not self.domain:
            self.domain = _find_domain(self)
        if self._snmp_switches:
            self.energywise_domain_usage = self.snmp_domain_usage
        elif self._cpex_switches:
            self.energywise_domain_usage = self.cpex_domain_usage
        else:
            self.energywise_domain_usage = self._empty_domain_usage
        Node.start(self)
        return
    def stop(self):
        self._reinit()
        Node.stop(self)
        return
    def cpex_domain_usage(self, importance=100, skipCache=False, max_attempts=3):
        self._cpex_lock.acquire()
        aggr_result = 0
        try:
            if not self._cpex_switches:
                raise ENoDomainSwitches(
                    "No switches are configured for the %r domain." % self.domain
                    )
            for switch in self._cpex_switches:
                for i in range(0, max_attempts):
                    try:
                        result = switch.cpex_domain_usage(importance)
                        if result:
                            aggr_result += result
                            break
                    except:
                        pass
        except ENoDomainSwitches:
            raise
        finally:
            self._cpex_lock.release()
        return aggr_result
    # caching for cpex switches under a domain
    # @return A dictionary of Energywise usage values keyed by switch address, possibly from cache.
    def cpex_switch_usage_map(self, importance=100, skipCache=False):
        self._cpex_switch_map_lock.acquire()
        try:
            if skipCache or self._is_cpex_switch_map_stale(time.time()):
                #fetch actual value
                usage_map = self._cpex_switch_usage_map(importance)
                self._update_cpex_switch_map(usage_map, time.time())
            return self._cpex_switch_map_cache
        finally:
            self._cpex_switch_map_lock.release()
        raise EUnreachableCode("Executed unreachable code!")
    ##
    # Call cpex_switch_usage_map on the primary cpex switch.
    # @return A dictionary of Energywise usage values keyed by switch address.
    def _cpex_switch_usage_map(self, importance=100, max_attempts=3):
        self._cpex_lock.acquire()
        aggr_result = {}
        try:
            if not self._cpex_switches:
                raise ENoDomainSwitches(
                    "No switches are configured for the %r domain." % self.domain
                    )
            for switch in self._cpex_switches:
                for i in range(0, max_attempts):
                    try:
                        result = switch.cpex_switch_usage_map(importance)
                        if result:
                            aggr_result.update(result)
                            break
                    except:
                        pass
        except ENoDomainSwitches:
            raise
        finally:
            self._cpex_lock.release()
        return aggr_result
    def snmp_domain_usage(self, importance=100, skipCache=False):
        result = 0
        for switch in self._snmp_switches:
            try:
                result += switch.snmp_switch_usage(importance, skipCache)
            except:
                msglog.exception()
                msglog.log("Energywise",msglog.types.ERR,
                           "Failed to get data from %r switch" %switch.name
                           )
        return result
    def _is_cpex_switch_map_stale(self, timestamp):
        return (self._cpex_switch_map_time + self.ttl) < timestamp
    def _update_cpex_switch_map(self, switch_map, timestamp):
        self._cpex_switch_map_cache = SwitchMap(switch_map)
        self._cpex_switch_map_time = timestamp
    def _is_domain_cache_stale(self,timestamp):
        assert self._cache_lock.locked()
        return (self._cache_time + self.ttl) < timestamp
    def _update_domain_cache(self,value, timestamp):
        self._cache_value = value
        self._cache_time = timestamp
    #caching the domain-usage
    def aggregate_domain_usage(self, importance=100, skipCache=False):
        self._cache_lock.acquire()
        try:
            if skipCache or self._is_domain_cache_stale(time.time()):
                    #fetch the actual value and update the cache
                try:
                    result = self.energywise_domain_usage(importance, skipCache)
                except:
                    msglog.exception()
                    result = 0
                for sub in self._all_domains:
                        result += sub.aggregate_domain_usage(importance, skipCache)
                self._update_domain_cache(result, time.time())
                return self._cache_value
            else:
                # use the cached value
                return self._cache_value
        finally:
            self._cache_lock.release()
        raise EUnreachableCode("Executed unreachable code!") 
    def new_trend(self,period):
        return new_trend(self,period)
    def delete_trend(self):
        return delete_trend(self)
    def get(self, skipCache=False):
        return self.aggregate_domain_usage()
    def get_result(self, skipCache=False):
        return Result(self.get(skipCache), time.time(), cached=False)

class EnergywiseSwitch(Node):
    SNMP_REMOTE_AGENTS_PATH = '/services/network/SNMP/Remote Agents'
    CEW_ENT_ENTRY_SUBPATH = (
        'Managed Objects/iso/org/dod/internet/private/enterprises/cisco/'
        'ciscoMgmt/ciscoEnergywiseMIB/ciscoEnergywiseMIBObjects/cewEntTable/'
        'cewEntEntry'
        )
    PROTOCOL_SNMP = 'SNMP'
    PROTOCOL_NATIVE = 'Native'
    _PROTOCOL_MAP = {'snmp':PROTOCOL_SNMP,'native':PROTOCOL_NATIVE}
   
    def get_cewEntEnergyUsage_node(self):
        usage_url = os.path.join(self.SNMP_REMOTE_AGENTS_PATH,
                                self.name,
                                self.CEW_ENT_ENTRY_SUBPATH,
                                'cewEntEnergyUsage')
        return as_node(usage_url)
    def get_cewEntEnergyUnits_node(self):
        units_url = os.path.join(self.SNMP_REMOTE_AGENTS_PATH,
                                 self.name,
                                 self.CEW_ENT_ENTRY_SUBPATH,
                                 'cewEntEnergyUnits')
        return as_node(units_url)
    def get_snmp_switch_agent_node(self):
        snmp_switch_url = os.path.join(self.SNMP_REMOTE_AGENTS_PATH,
                                       self.name)
        return as_node(snmp_switch_url)
    def _not_running(self, *args, **kw):
        raise ENotRunning("%r is not running." % self.as_node_url())

    def as_protocol_name(self,protocol):
        try:
            return self._PROTOCOL_MAP[protocol.lower()]
        except KeyError:
            raise EInvalidValue('protocol',protocol,
                                "%r is not a supported protocol for %r" 
                                %(protocol,self.as_node_url())
                                )
        
    #
    # Initialize all parameters for energywise switch
    def __init__(self):
        Node.__init__(self)
        self._cpex_connect_orig = self._cpex_connect
        self._cpex_connect = self._not_running
        self.running = 0
        self.domain = ''
        self.address = REQUIRED
        self.snmp_version = REQUIRED
        self.snmp_batch_size = 50
        self.community_name = REQUIRED
        self.security_name = None
        self.username = None
        self.authentication_protocol = None
        self.authentication_key = None
        self.privacy_protocol = None
        self.privacy_key = None
        self.remote_agent = None
        self.trend_node = None
        self.period = 60
        self.debug = 0
        self.shared_secret = REQUIRED
        self.cpex_port = CPEX_DEFAULT_PORT
        self.primary = False
        self.protocol = 'SNMP'
        self.cpex_connect_retry = 60
        self.cpex_timeout = 1 # 12
        self.get_switch_usage = self._not_running
        self.cewEntEnergyUsage_node = None
        self.cewEntEnergyUnits_node = None
        self.snmp_usage_map = None
        self.snmp_switch_agent_node = None
        self._snmp_cache_lock=Lock()
        self._snmp_cache_value=None
        self._snmp_cache_time=0
        self.ttl=30 
        return
    # on startup following parameters are passed.
    def configure(self, config):
        if self.debug:
            msg = 'Inside Configure api '
            msglog.log('Energywise:', msglog.types.INFO, msg )
            msg = 'sys path %s'
            msglog.log('Energywise:', msglog.types.INFO, msg %sys.path)
        Node.configure(self, config)
        set_attribute(self, 'ttl', 30, config, int)
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'address', REQUIRED, config)
        set_attribute(self, 'shared_secret', REQUIRED, config)
        set_attribute(self, 'cpex_port', 43440, config, int)
        set_attribute(self, 'primary', False, config, as_boolean)
        #SNMP is taken as default for reverse compatibility
        set_attribute(self, 'protocol', 'SNMP', config, 
                      self.as_protocol_name)
        set_attribute(self, 'snmp_batch_size', 50, config, int)
        if self.debug:
            msg = 'Configured address  %s '
            msglog.log('Energywise:', msglog.types.INFO, msg %self.address)
        if not self.domain:
            self.domain = _find_domain(self)
            if self.debug:
                msg = 'Configured CPEX domain %s '
                msglog.log('Energywise:', msglog.types.INFO, msg %self.domain)
        set_attribute(self,'snmp_version', REQUIRED, config)
        if self.debug:
            msg = 'Configured snmp_version %s'
            msglog.log('Energywise:', msglog.types.INFO, msg %self.snmp_version)
        set_attribute(self,'community_name',REQUIRED, config)
        if self.debug:
            msg = 'Configured community_name %s'
            msglog.log('Energywise:', msglog.types.INFO,
                                      msg %self.community_name)
        set_attribute(self,'security_name','default', config)
        if self.debug:
            msg = 'Configured security_name %s'
            msglog.log('Energywise:', msglog.types.INFO,
                                      msg %self.security_name)
        set_attribute(self,'user_name',' ', config)
        set_attribute(self,'authentication_protocol','usmNoAuthProtocol',
                      config)
        set_attribute(self,'authentication_key',' ', config)
        set_attribute(self,'privacy_protocol','usmNoPrivProtocol', config)
        set_attribute(self,'privacy_key', ' ',config)
        return
    def configuration(self):
        if self.debug:
            msg = 'Inside Configuration()'
            msglog.log('Energywise:', msglog.types.INFO, msg)
        config = Node.configuration(self)
        get_attribute(self, 'ttl', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'domain', config)
        get_attribute(self, 'address', config)
        get_attribute(self, 'snmp_version', config)
        get_attribute(self, 'snmp_batch_size', config, str)
        get_attribute(self, 'community_name', config)
        get_attribute(self, 'security_name', config)
        get_attribute(self, 'user_name', config)
        get_attribute(self, 'authentication_protocol', config)
        get_attribute(self, 'authentication_key', config)
        get_attribute(self, 'privacy_protocol', config)
        get_attribute(self, 'privacy_key', config)
        get_attribute(self, 'shared_secret', config)
        get_attribute(self, 'cpex_port', config)
        get_attribute(self, 'primary', config)
        get_attribute(self, 'protocol', config)
        return config
    def start(self):
        if self.debug:
            msg = 'Inside Start()'
            msglog.log('Energywise:', msglog.types.INFO, msg)
        if not self.running:
            if not (1024 < self.cpex_port < 65536):
                raise EConfiguration(
                    "Invalid port specified (%d). "
                    "Please enter values between 1025 and 65535 " 
                    % self.cpex_port
                    )
            self.running = 1
            self._cpex_connect = self._cpex_connect_orig
            Node.start(self)
            if self.PROTOCOL_SNMP == self.protocol:
                # Create SNMP node for this remote_agent
                self.createEnergywiseSNMPNodes()
                self.snmp_switch_agent_node = self.get_snmp_switch_agent_node()
                self.cewEntEnergyUsage_node = self.get_cewEntEnergyUsage_node()
                self.cewEntEnergyUnits_node = self.get_cewEntEnergyUnits_node()
                self.snmp_usage_map = {}
                for child in self.cewEntEnergyUsage_node.children_nodes():
                    self.snmp_usage_map[('usage', child.name)] = child
                for child in self.cewEntEnergyUnits_node.children_nodes():
                    self.snmp_usage_map[('units', child.name)] = child
                self.get_switch_usage = self.snmp_switch_usage
            else:
                self.get_switch_usage = self.cpex_switch_usage
        return
    def stop(self):
        if self.debug:
            msg = 'Inside Stop()'
            msglog.log('Energywise:', msglog.types.INFO, msg)
        if self.running:
            Node.stop(self)
            self.running = 0
            self.get_switch_usage = self._not_running
        return
    
    # Create all required mib and snmp nodes automatically for monitoring app.
    def createEnergywiseSNMPNodes(self):
        if self.debug:
            msglog.log('Energywise:',msglog.types.INFO,
                'Inside createEnergywiseSNMPNodes')
        try:
            # check SNMP node is present
            snmpRef = as_node("/services/network/SNMP")
        except:
            msglog.log('Energywise:',msglog.types.ERR,
                'Missing SNMP node under /services/network, please create it.')
        snmpNode = node_factory(
             "mpx.service.network.snmp.remote_agent.RemoteAgent")
        snmpNode.configure({
                'parent':"/services/network/SNMP/Remote Agents",
                'name': self.name,
                'address':self.address,
                'mib_table':[{'name':'CISCO-ENERGYWISE-MIB',
                          'value':"CISCO-ENERGYWISE-MIB"}],
                'port':161,
                'discover_at_start':0,
                'max_batch_size':self.snmp_batch_size,
                })
            # create SNMP version node under snmpNode
        if self.snmp_version == 'v1':
            version = '1'
            snmpVersionNode = node_factory(
                "mpx.service.network.snmp.remote_agent.SNMPv1"
                )
            parent_name = "/services/network/SNMP/Remote Agents/"
            parent_name += self.name
            snmpVersionNode.configure({
                'parent':parent_name,
                'name':"SNMPv1",
                'version':version,
                'community_name':self.community_name,
                'security_name':self.security_name
                })
        if self.snmp_version == 'v2c':
            version = '2c'
            snmpVersionNode = node_factory(
                "mpx.service.network.snmp.remote_agent.SNMPv2c")

            parent_name = "/services/network/SNMP/Remote Agents/"
            parent_name += self.name
            snmpVersionNode.configure({
                'parent':parent_name,
                'name':"SNMPv2c",
                'version':version,
                'community_name':self.community_name,
                'security_name':self.security_name
                })
        if self.snmp_version == 'v3':
            version = '3'
            snmpVersionNode = node_factory(
                "mpx.service.network.snmp.remote_agent.SNMPv3")

            parent_name = "/services/network/SNMP/Remote Agents/"
            parent_name += self.name
            snmpVersionNode.configure({
                'parent':parent_name,
                'name':"SNMPv3",
                'version':version,
                'username':self.username,
                'authentication_protocol':self.authentication_protocol,
                'authentication_key':self.authentication_key,
                'privacy_protocol':self.privacy_protocol,
                'privacy_key':self.privacy_key })
        snmpNode.start()
        # Start discovery of interested oids
        managedObjects = snmpNode.get_child(snmpNode.MANAGED_OBJECTS)
        seek_from = (1,3,6,1,4,1,9,9,683,1,3) # CISCO-ENERGYWISE::cewDomainName
        managedObjects.batch_all_from(seek_from,True)
        mib_node = parent_name
        mib_node += '/Managed Objects/iso/org/dod/internet/private/'\
            'enterprises/cisco/ciscoMgmt/ciscoEnergywiseMIB/'\
            'ciscoEnergywiseMIBObjects/cewDomainName/0'
        domainNode = as_node(mib_node)
        val = domainNode.get()
        if not str(val) == self.domain:
            raise EInvalidValue('self.domain',self.domain)
        if self.debug:
            msglog.log('Energywise:',msglog.types.INFO,
                'Energywise domain managed by this switch is %s'%str(val))
        seek_from = (1,3,6,1,4,1,9,9,683,1,6) # CISCO-ENERGYWISE::cewEntTable
        managedObjects.batch_all_from(seek_from,True)
        return
   
    def new_trend(self,period):
        return new_trend(self,period)
    def delete_trend(self):
        return delete_trend(self)
  
    def _cpex_connect(self):
        uuid = energywise_utl_createUuid()
        key = energywise_utl_composeKey(self.shared_secret, uuid)
        cpex_session = energywise_createSession(
            self.address, self.cpex_port, uuid, key, self.cpex_timeout
            )
        if cpex_session == 0:
            raise EConnectFailed(
                "Failed to create a session with %(address)s:%(cpex_port)d" %
                self.configuration()
                )
        return cpex_session
    def _cpex_disconnect(self, cpex_session):
        energywise_closeSession(cpex_session)
        return
    def cpex_domain_usage(self, importance=100):
        cpex_query = 0
        result_set = 0
        usage = 0
        cpex_session = self._cpex_connect()
        try:
            cpex_query = energywise_createSumQuery(self.domain, importance)
            energywise_addGetAttribute(cpex_query, EW_ATTRIBUTE_TYPE_UNITS)
            energywise_addGetAttribute(cpex_query, EW_ATTRIBUTE_TYPE_USAGE)
            energywise_execQuery(cpex_session, cpex_query)
            result_set = energywise_queryResults(cpex_session, cpex_query)
            if result_set == 0:
                raise EnergywiseCommunicationFailure(
                    "Domain sum query via %r failed." % self.address
                    )
            result_row = energywise_getNextRow(result_set)
            while result_row:
                units = energywise_getAttributeFromRowByType(
                    result_row, EW_ATTRIBUTE_TYPE_UNITS
                    ).value
                usage += energywise_getAttributeFromRowByType(
                    result_row, EW_ATTRIBUTE_TYPE_USAGE
                    ).value * 10**units
                result_row = energywise_getNextRow(result_set)
        finally:
            if result_set != 0:
                energywise_releaseResult(result_set)
            if cpex_query != 0:
                energywise_releaseQuery(cpex_query)
            self._cpex_disconnect(cpex_session)
        return usage
    def cpex_switch_usage_map(self, importance=100):
        cpex_query = 0
        result_set = 0
        usage_map = {}
        cpex_session = self._cpex_connect()
        try:
            cpex_query = energywise_createCollectQuery(self.domain, importance)
            energywise_addGetAttribute(cpex_query, EW_ATTRIBUTE_TYPE_USAGE)
            energywise_addGetAttribute(cpex_query, EW_ATTRIBUTE_TYPE_UNITS)
            energywise_execQuery(cpex_session, cpex_query)
            result_set = energywise_queryResults(cpex_session, cpex_query)
            if result_set == 0:
                raise EnergywiseCommunicationFailure(
                    "Failed to query switch usage for %r via %r" % (self.domain, self.address)
                    )
            result_row = energywise_getNextRow(result_set)
            while result_row:
                units = energywise_getAttributeFromRowByType(
                    result_row, EW_ATTRIBUTE_TYPE_UNITS
                    ).value
                usage = energywise_getAttributeFromRowByType(
                    result_row, EW_ATTRIBUTE_TYPE_USAGE
                    ).value * 10**units
                usage_map[self.address] = usage_map.get(self.address,0) + usage
                result_row = energywise_getNextRow(result_set)
        finally:
            if result_set != 0:
                energywise_releaseResult(result_set)
            if cpex_query != 0:
                energywise_releaseQuery(cpex_query)
            self._cpex_disconnect(cpex_session)
        return usage_map
    def cpex_switch_usage(self, importance=100, skipCache=False):
        try:
            return self.parent.cpex_switch_usage_map(importance, skipCache)[self.address]
        except KeyError:
            raise EnergywiseCommunicationFailure("Failed to get usage for switch %r." % self.address)
        raise EUnreachableCode("Executed unreachable code!")
    def _is_snmp_cache_stale(self,timestamp):
        return (self._snmp_cache_time+self.ttl) < timestamp
    def _update_snmp_cache(self,value, timestamp):
        self._snmp_cache_value = value
        self._snmp_cache_time = timestamp
    #caching for snmp switch
    def snmp_switch_usage(self, importance=100, skipCache=False):
        self._snmp_cache_lock.acquire()
        try:
            if skipCache or self._is_snmp_cache_stale(time.time()):
                #fetch actual value
                if self.PROTOCOL_SNMP != self.protocol:
                    raise ESNMPNotEnabled("SNMP is not enabled on %r" %
                                          self.as_node_url())
                batches = self.snmp_switch_agent_node.create_batches(
                    self.snmp_usage_map
                    )
                result = {}
                for batch in batches:
                    result.update(self.snmp_switch_agent_node.get_batch(batch))
                usage = 0
                for usage_key in filter((lambda k:k[0]=='usage'), result.keys()):
                    unit_key = ('units', usage_key[1])
                    usage_value = int(result[usage_key].value)
                    unit_value = int(result[unit_key].value)
                    usage += usage_value*10**unit_value
                self._update_snmp_cache(usage, time.time())
                return usage
            else:
                #use cached value
                return self._snmp_cache_value
        finally:
            self._snmp_cache_lock.release()
        raise EUnreachableCode("Executed unreachable code!")
    def get(self, skipCache=False):
        return self.get_switch_usage()
    def get_result(self, skipCache=False):
        return Result(self.get(skipCache), time.time(), cached=False)
