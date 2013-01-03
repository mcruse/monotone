"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
##
# @fixme I don't know how to determine the source of a v2c notification.
# @fixme I don't currently have a way to add v3 notifications.
# @fixme Socket is bound in init and is not closed/reopened on reincarnate.  It
#        would be more robust to do so, but it is not obvious given how buried
#        that is in PySNMP.

import time

from pysnmp.carrier.asynsock import dispatch
from pysnmp.entity import engine, config
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

from pysnmp.proto.proxy.rfc2576 import __sysUpTime as _sysUpTime
from pysnmp.proto.proxy.rfc2576 import __snmpTrapOID as _snmpTrapOID
from pysnmp.proto.proxy.rfc2576 import __snmpTrapEnterprise as \
     _snmpTrapEnterprise
from pysnmp.proto.proxy.rfc2576 import __snmpTrapAddress as _snmpTrapAddress
# _sysUpTime = (1,3,6,1,2,1,1,3)
# _snmpTrapOID = (1,3,6,1,6,3,1,1,4,1,0)
# _snmpTrapEnterprise = (1,3,6,1,6,3,1,1,4,3,0)
# _snmpTrapAddress = (1,3,6,1,6,3,18,1,3,0)
_sysUpTime0 = (1,3,6,1,2,1,1,3,0)

from mpx.lib import socketmap
from mpx.lib.threading import EKillThread
from mpx.lib.threading import ImmortalThread

from mpx.lib.node import as_node
from mpx.lib.node import CompositeNode

from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.configure import REQUIRED

from mpx.lib.exceptions import EInvalidMessage

import SNMP
from trap_view import MibViewProxy

def _hex_str(text, sep=''):
    return sep.join(map(lambda b: "%02X" % b, map(ord,text)))

class TrapThread(ImmortalThread):
    def __init__(self, group=None, target=None, name=None, args=(),
                 kwargs=None, verbose=None, *vargs, **keywords):
        ImmortalThread.__init__(self, group, target, name, args, kwargs,
                                verbose, *vargs, **keywords)
        self.__one_time_init()
        self.__every_time_init()
        return
    def __one_time_init(self):
        self.listen_address = '0.0.0.0' # Set by TrapEngine
        self.listen_port = 162          # Set by TrapEngine
        self.owner = None               # Set by TrapEngine
        self.trap_view = None           # Set by TrapEngine
        self.trap_log = None            # Set by TrapEngine
        self.socket_map = socketmap.SocketMap()
        self.snmpEngine = engine.SnmpEngine()
        transportDispatcher = dispatch.AsynsockDispatcher()
        transportDispatcher.setSocketMap(self.socket_map)
        self.snmpEngine.registerTransportDispatcher(transportDispatcher)
        # @note As of PySNMP 4.1.9a, receipt of a V3 notification with out
        #       any registerred V3 users results in a traceback.
        self.addV3User('\0',
                       config.usmNoAuthProtocol, '\0'*8,
                       config.usmNoPrivProtocol, '\0'*8)
        def cbFun(snmpEngine,
                  contextEngineId,
                  contextName,
                  varBinds,
                  trap_thread):
            trap_thread._TrapThread__callback(contextEngineId, contextName,
                                              varBinds)
            return
        self.receiver = ntfrcv.NotificationReceiver(self.snmpEngine,
                                                    cbFun, self)
        # Setup transport endpoint
        config.addSocketTransport(
            self.snmpEngine,
            udp.domainName,
            udp.UdpSocketTransport().openServerMode((self.listen_address,
                                                     self.listen_port))
            )
        return
    def __every_time_init(self):
        return
    def __restart_clean_up(self):
        #config.delSocketTransport(
        #    self.snmpEngine,
        #    udp.domainName
        #    )
        return
    ##
    # Callback function for receiving notifications
    def __callback(self, contextEngineId, contextName, varBinds):
        # V1 looks like this:
        #   _sysUpTime = (1,3,6,1,2,1,1,3)
        #   _snmpTrapOID = (1,3,6,1,6,3,1,1,4,1,0)
        #   _snmpTrapEnterprise = (1,3,6,1,6,3,1,1,4,3,0)
        #   _snmpTrapAddress = (1,3,6,1,6,3,18,1,3,0)
        # V2 looks like 
        #   _sysUpTime0 = (1,3,6,1,2,1,1,3,0)
        #   _snmpTrapOID = (1,3,6,1,6,3,1,1,4,1,0)
        #   [varbinds...]
        if len(varBinds) < 2:
            # @fixme Log the malformed trap to the message log.
            raise EInvalidMessage(
                "SNMP trap must contain at least the time-stamp/sysUpTime "
                "and the trap/snmpTrapOID"
                )
        #
        # When we processed the trap for logging.
        #
        logtime = time.time()
        version = '2c' # Assumption until proven otherwise.
        context_engine_id = _hex_str(contextEngineId)
        context_name = str(contextName)
        #
        # varBinds[0] extract sysUpTime:
        #
        sysUpTimeVarBind = varBinds.pop(0)
        if sysUpTimeVarBind[0] == _sysUpTime:
            # Inserted by PySNMP 4.1.9a.
            version = '1'
        elif sysUpTimeVarBind[0] == _sysUpTime0:
            # As per RFC 3416, what about v3?
            version = '2c'
        else:
            raise EInvalidMessage(
                "Expected sysUpTime OID of %r, or %r, received %r"
                % (_sysUpTime, _sysUpTime0, sysUpTimeVarBind[0])
                )
        # @note It seems that v1toV2 uses _sysUpTime and that true v2 uses
        #       _sysUpTime0
        sysUpTimePrettyName, sysUpTimePrettyValue = (
            self.trap_view.getPrettyOidVal(*sysUpTimeVarBind)
            )
        #
        # varBinds[1] extract the snmpTrap.
        #
        snmpTrapNameVarBind = varBinds.pop(0)
        if snmpTrapNameVarBind[0] != _snmpTrapOID:
            raise EInvalidMessage(
                "Expected snmpTrapOID OID of %r, received %r"
                % (_snmpTrapOID, snmpTrapNameVarBind[0])
                )
        try:
            snmpTrapName, snmpTrapValue = self.trap_view.getPrettyOidVal(
                *snmpTrapNameVarBind
                )
        except:
            snmpTrapName = ".".join(map(str,snmpTrapNameVarBind[0]))
            snmpTrapValue = ".".join(map(str,snmpTrapNameVarBind[1]))
        #
        # varBinds[2] MIGHT BE the snmpTrapAddress, if this was an
        # "upconverted" V1 Trap-PDU.
        #
        snmpTrapEnterpriseValue = ''
        if varBinds:
            snmpTrapEnterpriseVarBind = varBinds[0]
            if snmpTrapEnterpriseVarBind[0] == _snmpTrapEnterprise:
                varBinds.pop(0)
                try:
                    snmpTrapEnterpriseName, snmpTrapEnterpriseValue = (
                        self.trap_view.getPrettyOidVal(
                            *snmpTrapEnterpriseVarBind
                            )
                        )
                except:
                    snmpTrapEnterpriseName = (
                        ".".join(map(str,snmpTrapNameVarBind[0]))
                        )
                    snmpTrapEnterpriseValue = (
                        ".".join(map(str,snmpTrapNameVarBind[1]))
                        )
        #
        # varBinds[2|3] MIGHT BE the snmpTrapAddress, if this was an
        # "upconverted" V1 Trap-PDU, or the it is a "custom" trap
        # using the snmpTrapAddress-Hack to set the logged source
        # address.
        #
        snmpTrapAddressValue = ''
        if varBinds:
            snmpTrapAddressVarBind = varBinds[0]
            if snmpTrapAddressVarBind[0] == _snmpTrapAddress:
                varBinds.pop(0)
                try:
                    snmpTrapAddressName, snmpTrapAddressValue = (
                        self.trap_view.getPrettyOidVal(
                            *snmpTrapAddressVarBind
                            )
                        )
                except:
                    snmpTrapAddressName = (
                        ".".join(map(str,snmpTrapNameVarBind[0]))
                        )
                    snmpTrapAddressValue = (
                        ".".join(map(str,snmpTrapNameVarBind[1]))
                        )
        #
        # Accumulate the remaining varBinds for logging.
        #
        convertedVarBinds = []
        while varBinds:
            varName, varValue = varBinds.pop(0)
            try:
                # Try to make it pretty.
                varName, varValue = self.trap_view.getPrettyOidVal(varName,
                                                                   varValue)
            except:
                varName = ".".join(map(str,varName))
                varValue = ".".join(map(str,varValue))
            convertedVarBinds.append((varName,varValue,))
        self.trap_log.log_trap(version, context_engine_id, context_name,
                               snmpTrapAddressValue, sysUpTimePrettyValue,
                               snmpTrapValue, snmpTrapEnterpriseValue,
                               convertedVarBinds, logtime)
        return
    def reincarnate(self):
        self.__restart_clean_up()
        self.__every_time_init()
        return
    def run(self):
        # From pysnmp/v4/carrier/asynsock/dispatch:
        #        AsynsockDispatcher.runDispatcher()
        #
        # def runDispatcher(self, timeout=0.0):
        #     while self.jobsArePending() or self.transportsAreWorking():
        #         poll(self.timeout, self.__sockMap)
        #         self.handleTimerTick(time())
        snmpEngine = self.snmpEngine
        transportDispatcher = self.snmpEngine.transportDispatcher
        while self.is_immortal():
            self.socket_map.poll3(None)
            transportDispatcher.handleTimerTick(time.time())
        return
    def shutdown(self):
        self.should_die()
        self.socket_map.wakeup()
        self.join(10.0)
        assert not self.isAlive(), 'shutdown failed'
        return
    ##
    # @fixme As far as I can tell, as of PySNMP 4.1.9a recieving a V1 trap is
    #        completely unaffected by addV1System configuration...
    def addV1System(self, securityName, communityName,
                    contextEngineId=None, contextName=None,
                    transportTag=None):
        config.addV1System(self.snmpEngine, securityName, communityName,
                           contextEngineId, contextName, transportTag)
        return
    ##
    # @fixme As far as I can tell, as of PySNMP 4.1.9a recieving a V1 trap is
    #        completely unaffected by addV1System configuration...
    def delV1System(self, snmpEngine, securityName):
        config.delV1System(self.snmpEngine, securityName, communityName)
        return
    ##
    # @fixme At least when using snmptrap to test, only the securityName seems
    #        to effect accepting the notification.  This makes no sense since
    #        we shouldn't even be able to decode it...  Most likely snmptrap
    #        does not honor the authProtocol/privProtocol.
    def addV3User(self, securityName,
                  authProtocol=config.usmNoAuthProtocol, authKey=None,
                  privProtocol=config.usmNoPrivProtocol, privKey=None,
                  contextEngineId=None):
        config.addV3User(self.snmpEngine, securityName,
                         authProtocol, authKey, privProtocol, privKey,
                         contextEngineId)
        return
    def delV3User(self, securityName, contextEngineId=None):
        config.delV3User(self.snmpEngine, securityName, contextEngineId)
        return

class TrapEngine(CompositeNode):
    __node_id__ = 'a36027ed-ebf3-4e79-b095-28f4672e86c6'
    def __init__(self):
        super(TrapEngine, self).__init__()
        self.__thread = None
        self.port = 162
        self.trap_log = REQUIRED
        self.snmp_service = None
        return
    def start(self):
        super(TrapEngine,self).start()
        self.trap_log = as_node(self.trap_log)
        self.snmp_service = self.parent
        while not isinstance(self.snmp_service, SNMP.SNMP):
            self.snmp_service = self.snmp_service.parent
        if self.__thread is None:
            self.__thread = TrapThread(name='SNMP Trap Thread')
            # @fixme Really shouldn't listen on all adapters.  This should be
            #        configurable ('lo', 'eth0', 'eth1', and 'all')
            self.__thread.listen_address = '0.0.0.0'
            self.__thread.listen_port = self.port
            self.__thread.owner = self
            self.__thread.trap_view = self.snmp_service.new_mib_view_proxy(
                MibViewProxy
                )
            self.__thread.trap_log = self.trap_log
            self.__thread.start()
        return
    def stop(self):
        super(TrapEngine,self).stop()
        if self.__thread is not None:
            t = self.__thread
            self.__thread = None
            t.shutdown()
        return
    def configure(self, cd):
        super(TrapEngine, self).configure(cd)
        # set_attribute(self, 'adapter', 'all', cd)
        set_attribute(self, 'port', 162, cd, int)
        set_attribute(self, 'trap_log', '/services/logger/SNMP+Trap+Log', cd,
                      str)
        return
    def configuration(self):
        cd = super(TrapEngine, self).configuration()
        # get_attribute(self, 'adapter', cd)
        cd['adapter'] = 'all'
        get_attribute(self, 'port', cd, str)
        get_attribute(self, 'trap_log', cd, str)
        return cd

"""
# V2 generated Trap.
snmptrap -M /usr/share/snmp/mibs:. -m PowerNet-MIB -v 2c -c public democase-6 '' PowerNet-MIB::upsOverload PowerNet-MIB::mtrapargsString s 'test'
# =====
# V1 generated trap.
snmptrap -M /usr/share/snmp/mibs:. -m PowerNet-MIB -v 1 -c public democase-6 PowerNet-MIB::apc 192.168.16.3 6 2 '' PowerNet-MIB::mtrapargsString s 'test'
# V3 generated trap
snmptrap -M /usr/share/snmp/mibs:. -m PowerNet-MIB -v 3 -a MD5 -A authkey1 -x DES -X privkey1 -u test-user -E 800000020109840301 -n Mediator democase-6 '' PowerNet-MIB::upsOverload PowerNet-MIB::mtrapargsString s 'test'
# notes auth/priv arguments don't seem to matter...
# =====
# V1 generated trap.
snmptrap -M /usr/share/snmp/mibs:. -m PowerNet-MIB -v 1 -c public democase-6 PowerNet-MIB::apc 192.168.16.3 2 0 '' ifIndex i 2 ifAdminStatus i 1 ifOperStatus i 1
# =====
# V2 generated Trap.
snmptrap -M /usr/share/snmp/mibs:. -m PowerNet-MIB -v 2c -c public democase-6 '' .1.3.6.1.6.3.1.1.5.3 ifIndex i 2 ifAdminStatus i 1 ifOperStatus i 1
"""
