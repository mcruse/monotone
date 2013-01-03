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
from time import time as now
##
# Skeletal structure for the Node-based representation of SNMP.
#
# Proper node tree configuration:
#
#   /services/
#     |
#     +- network/
#         |
#         +- SNMP/
#             |
#             +- Default Trap Engine/
#             |
#             +- Remote Agents/
#                 |
#                 +- "agent"/
#                     |
#                     +- (SNMPv1|SNMPv2c|SNMPv3|SNMPv1or2c)
#                     |
#                     +- Managed Objects/
#                         |
#                         +- iso/org/dod/internet/
#                                         +- mgmt/
#                                         +- private/
#                                         +- snmpv2/
#                                         +- etc ...
#
# The Node.name of the "agent" is user configurable.  Virtually everything
# else is hardcoded.

from pyasn1.type import univ

from pysnmp import debug
from pysnmp.carrier.asynsock import dispatch
from pysnmp.entity import engine
from pysnmp.entity.rfc3413 import mibvar
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import error
from pysnmp.smi import builder
from pysnmp.smi import view

from mpx.lib import msglog
from mpx.lib.exceptions import MpxException
from mpx.lib.node import CompositeNode
from mpx.lib.threading import Lock

# @note Voodoo to set the path to automatically load MIBS.  This may actually
#       be extrainious.  It looks like we could directly manage the load path
#       on a MibBuilder instance (loadModules returns self as a convenience,
#       it DOES NOT create a new instance.)
# @fixme BETTER module management...  /var/mpx/snmp/mibs or some such.
import mpx.lib.snmp.mibs

class OidInfo(object):
    def __init__(self, describe_oid, mib_builder, mib_view,
                 oid, matched_oid, matched_label, index,
                 mib_name, oid_name, smi):
        self.__describe_oid=describe_oid
        self.__mib_builder = mib_builder
        self.__mib_view = mib_view
        self.oid=oid
        self.matched_oid=matched_oid
        self.matched_label=matched_label
        self.index=index
        self.mib_name=mib_name
        self.oid_name=oid_name
        self.smi=smi
        return
    ##
    # @note Assumes that the OID is complete.  Partial OIDs will cause
    #       confusion.
    def is_var(self):
        return len(self.index) > 0
    def node_name(self):
        if not self.is_var():
            return self.oid_name
        #======================================================================
        # @fixme See fixmes in commented out block
        """
        mibSymbols = self.__mib_builder.mibSymbols
        MibTableColumn = mibSymbols['SNMPv2-SMI']['MibTableColumn']
        MibTableRow = mibSymbols['SNMPv2-SMI']['MibTableRow']
        if isinstance(self.smi, MibTableColumn):
            # # This is a column 'instance', get the actual column reference.
            # column = self.__describe_oid(self.matched_oid).smi
            # assert isinstance(column, MibTableColumn)
            #
            # Now get the row.
            row = self.__describe_oid(self.matched_oid[:-1]).smi
            assert isinstance(row, MibTableRow)
            index_names = row.getIndexNames()
            if len(index_names) == 1:
                huh, mib_name, oid_name = index_names[0]
                syntax = mibSymbols[mib_name][oid_name].syntax
                # @fixme Well, with the syntax object for the index I should
                #        be able to figure out the best way to display the
                #        name...
                pass
            else:
                # @fixme I don't know how to decode multiple indices...
                pass
        """
        #======================================================================
        # Default naming is appending the octets as decimal integers separated
        # with "." (period).
        return '.'.join(map(str, self.index))
    def __str__(self):
        return (
            "OidInfo: oid = %r\n"
            "         matched_oid = %r\n"
            "         matched_label = %r\n"
            "         index = %r\n"
            "         mib_name = %r\n"
            "         oid_name = %r\n"
            "         smi = %r\n") % (
            self.oid,
            self.matched_oid,
            self.matched_label,
            self.index,
            self.mib_name,
            self.oid_name,
            self.smi,
            )

class SNMPException(MpxException):
    def __str__(self):
        if not len(self.keywords):
            return MpxException.__str__(self)
        keys = self.keywords.keys()
        keys.sort()
        key = keys.pop(0)
        result = key + "=" + str(self.keywords[key])
        for key in keys:
            result += ", " + key + "=" + str(self.keywords[key])
        return result

class SNMP(CompositeNode):
    __node_id__ = '9e2a4bbf-d4cd-40c6-80ba-95edb94214ed'
    def __init__(self):
        super(SNMP, self).__init__()
        self.__lock = Lock()
        self.__mib_builder = None
        self.__mib_view = None
        self.__loaded_mibs = []
        snmpEngine = engine.SnmpEngine()
        transportDispatcher = dispatch.AsynsockDispatcher()
        transportDispatcher.setSocketMap({})
        snmpEngine.registerTransportDispatcher(transportDispatcher)
        self.__dispatcher = snmpEngine.transportDispatcher.runDispatcher
        self.__generator = cmdgen.AsynCommandGenerator(snmpEngine)
        self.__engine = snmpEngine
        return
    def start(self):
        self.__lock.acquire()
        try:
            self.__mib_builder = builder.MibBuilder()
            self.__mib_view = view.MibViewController(self.__mib_builder)
        finally:
            self.__lock.release()
        # Load some common MIBs:
        self.load_mib('SNMP-COMMUNITY-MIB')
        self.load_mib('SNMP-VIEW-BASED-ACM-MIB')
        self.load_mib('IF-MIB')
        super(SNMP,self).start()
        return
    def load_mib(self, mib_name, force=False):
        self.__lock.acquire()
        try:
            if force or (mib_name not in self.__loaded_mibs):
                self.__mib_builder.loadModules(mib_name)
                self.__loaded_mibs.append(mib_name)
        finally:
            self.__lock.release()
        return
    def describe_oid(self, oid):
        self.__lock.acquire()
        try:
            assert isinstance(oid, (tuple, univ.ObjectIdentifier))
            matched_oid, matched_label, suffix = (
                self.__mib_view.getNodeNameByOid(oid)
                )
            mib_name, oid_name, empty = (
                self.__mib_view.getNodeLocation(matched_oid)
                )
            assert matched_label[-1] == oid_name
            assert empty == ()
            matched_smi = self.__mib_builder.mibSymbols[mib_name][oid_name]
            return OidInfo(
                self.describe_oid, self.__mib_builder, self.__mib_view,
                oid, matched_oid, matched_label, suffix,
                mib_name, oid_name, matched_smi
                )
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def simple_varbinds_result(self, cbCtx):
        errorIndication = cbCtx['errorIndication']
        errorStatus = cbCtx['errorStatus']
        errorIndex = cbCtx['errorIndex']
        varBinds = cbCtx['varBinds']
        if errorIndication is not None or errorStatus:
            raise SNMPException(
                errorIndication=errorIndication,
                errorStatus=errorStatus,
                errorIndex=errorIndex,
                varBinds=varBinds
                )
        return varBinds
    classmethod(simple_varbinds_result)
    def multi_varbinds_result(klass, cbCtx):
        varBindHead, varBindTotalTable, appReturn = cbCtx
        errorIndication = appReturn['errorIndication']
        errorStatus = appReturn['errorStatus']
        errorIndex = appReturn['errorIndex']
        varBindTable = appReturn['varBindTable']
        if errorIndication is not None or errorStatus:
            raise SNMPException(
                errorIndication=errorIndication,
                errorStatus=errorStatus,
                errorIndex=errorIndex,
                varBindTable=varBindTable
                )
        varBinds = []
        for sublist in varBindTable:
            varBinds.extend(sublist)
        return varBinds
    classmethod(multi_varbinds_result)
    def simple_callback(klass, sendRequestHandle, errorIndication,
                        errorStatus, errorIndex, varBinds, cbCtx):
        cbCtx['errorIndication'] = errorIndication
        cbCtx['errorStatus'] = errorStatus
        cbCtx['errorIndex'] = errorIndex
        cbCtx['varBinds'] = varBinds
        # We are done, no more queries:
        return False
    classmethod(simple_callback)
    def multi_callback(klass, sendRequestHandle,
                       errorIndication, errorStatus, errorIndex,
                       varBindTable, cbCtx):
        varBindHead, varBindTotalTable, appReturn = cbCtx
        if errorIndication or errorStatus:
            appReturn['errorIndication'] = errorIndication
            appReturn['errorStatus'] = errorStatus
            appReturn['errorIndex'] = errorIndex
            appReturn['varBindTable'] = varBindTable
            # No more SNMP requests required:
            return False
        else:
            varBindTotalTable.extend(varBindTable) # XXX out of table 
                                                   # rows possible
            varBindTableRow = varBindTable[-1]
            for idx in range(len(varBindTableRow)):
                name, val = varBindTableRow[idx]
                if val is not None and varBindHead[idx].isPrefixOf(name):
                    break
            else:
                appReturn['errorIndication'] = errorIndication
                appReturn['errorStatus'] = errorStatus
                appReturn['errorIndex'] = errorIndex
                appReturn['varBindTable'] = varBindTotalTable
                # No more SNMP requests required:
                return False
        # Continue table retrieval:
        return True
    classmethod(multi_callback)
    def snmp_get_multiple(self, auth_data, transport, *object_names):
        self.__lock.acquire()
        try:
            cbCtx = {}
            self.__generator.asyncGetCmd(auth_data, transport, object_names,
                                         (self.simple_callback, cbCtx))
            self.__dispatcher()
            var_binds = self.simple_varbinds_result(cbCtx)
            return var_binds
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def snmp_set_multiple(self, auth_data, transport, var_binds):
        self.__lock.acquire()
        try:
            cbCtx = {}
            self.__generator.asyncSetCmd(auth_data, transport, var_binds,
                                         (self.simple_callback, cbCtx))
            self.__dispatcher()
            self.simple_varbinds_result(cbCtx)
            return
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def snmp_getbulk_multiple(self, auth_data, transport,
                              non_repeaters, max_repetitions, *object_names):
        self.__lock.acquire()
        try:
            appReturn = {}
            varBindHead = map(lambda (x,y): univ.ObjectIdentifier(x+y),
                              map((lambda x,g=self.__generator:
                                   mibvar.mibNameToOid(g.mibViewController,x)),
                                  object_names))
            varBindTotalTable = []
            cbCtx = (varBindHead, varBindTotalTable, appReturn)
            self.__generator.asyncBulkCmd(
                auth_data, transport, non_repeaters, max_repetitions,
                object_names, (self.multi_callback, cbCtx)
                )
            self.__dispatcher()
            return self.multi_varbinds_result(cbCtx)
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def snmp_getnext_multiple(self, auth_data, transport, *object_names):
        self.__lock.acquire()
        try:
            appReturn = {}
            varBindHead = map(lambda (x,y): univ.ObjectIdentifier(x+y),
                              map((lambda x,g=self.__generator:
                                   mibvar.mibNameToOid(g.mibViewController,x)),
                                  object_names))
            varBindTotalTable = []
            cbCtx = (varBindHead, varBindTotalTable, appReturn)
            self.__generator.asyncNextCmd(auth_data, transport, object_names,
                                          (self.multi_callback, cbCtx))
            # Work around Eaton Powerare UPS's incorrect end-of-getnext packet.
            try:
                self.__dispatcher()
            except error.ProtocolError, e:
                # Some Eaton Powerware UPS SNMP stacks respond with an out
                # of range error-index (2) for the final getnext response
                # of NoSuchName.
                if not varBindTotalTable:
                    msglog.log("SNMP", msglog.types.WARN,
                               "Caught ProtocolError with empty"
                               " varBindTotalTable, re-raising.")
                    msglog.log("SNMP", msglog.types.DB, "cbCtx: %r" % cbCtx)
                    raise
                msglog.exception()
                msglog.log("SNMP", msglog.types.WARN,
                           "Ignoring protocol error to allow (partial)"
                           " discovery.")
                appReturn['errorIndication'] = None
                appReturn['errorStatus'] = None
                appReturn['errorIndex'] = 0
                appReturn['varBindTable'] = varBindTotalTable
            return self.multi_varbinds_result(cbCtx)
        finally:
            self.__lock.release()
        raise EUnreachableCode()
    def new_mib_view_proxy(self, proxy_class):
        return proxy_class(self.__mib_view, self.__lock)
