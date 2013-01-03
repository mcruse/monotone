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
# Ripped off from pysnmp_apps(.v4).cli.mibview
#
#
# @fixme In general string quoting seems weak.  Why not use repr() everywhere?
#
import string
from pyasn1.type import univ
from pysnmp.proto import rfc1902

class UnknownSyntax:
    def prettyOut(self, val):
        return str(val)
unknownSyntax = UnknownSyntax()

#  Proxy MIB view

class MibViewProxy:
    # Defaults
    defaultOidPrefix = (
        'iso', 'org', 'dod', 'internet', 'mgmt', 'mib-2', 'system'
        )

    # MIB output options
    buildModInfo = 1
    buildObjectDesc = 1
    buildNumericName = 0
    buildAbsoluteName = 0
    buildNumericIndices = 0
    buildTypeInfo = 0
    buildEscQuotes = 0
    buildSquareBrackets = 0
    buildHexVals = 0
    buildRawVals = 0
    buildRawTimeTicks = 0
    buildGuessedStringVals = 1
    buildValueOnly = 0
    buildUnits = 1

    def __init__(self, mibViewController, lock):
        self.__lock = lock
        self.__oidValue = univ.ObjectIdentifier()
        self.__intValue = univ.Integer()
        self.__timeValue = rfc1902.TimeTicks()
        self.__mib_view = mibViewController
        return

    def __getPrettyOid(self, oid, prefix, label, suffix, modName, nodeDesc):
        mvc = self.__mib_view
        mb = mvc.mibBuilder

        oid_str = ''
        # object name
        if not self.buildValueOnly:
            if self.buildModInfo:
                oid_str = '%s::' % modName
            if self.buildObjectDesc:
                oid_str = oid_str + nodeDesc
            else:
                if self.buildNumericName:
                    name = prefix
                else:
                    name = label
                if not self.buildAbsoluteName:
                    name = name[len(self.defaultOidPrefix):]
                oid_str = oid_str + string.join(map(lambda x: str(x), name),
                                                '.')
            if suffix:
                if suffix == (0,):
                    oid_str = oid_str + '.0'
                else:
                    m, n, s = mvc.getNodeLocation(prefix[:-1])
                    rowNode, = mb.importSymbols(m, n)
                    if self.buildNumericIndices:
                        oid_str = oid_str+'.'+string.join(
                            map(lambda x: str(x), suffix), '.'
                            )
                    else:
                        try:
                            for i in rowNode.getIndicesFromInstId(suffix):
                                if self.buildEscQuotes:
                                    oid_str = (oid_str + '.\\\"%s\\\"' %
                                               i.prettyOut(i))
                                elif self.buildSquareBrackets:
                                    oid_str = (oid_str + '.[%s]' %
                                               i.prettyOut(i))
                                else:
                                    oid_str = (oid_str + '.\"%s\"' %
                                               i.prettyOut(i))
                        except AttributeError:
                            oid_str = oid_str + '.' + string.join(
                                map(lambda x: str(x), suffix), '.'
                                )
        return oid_str
    def getPrettyOidVal(self, oid, val):
        mvc = self.__mib_view
        mb = mvc.mibBuilder

        self.__lock.acquire()
        try:
            prefix, label, suffix = mvc.getNodeName(oid)
            modName, nodeDesc, _suffix = mvc.getNodeLocation(prefix)
            oid_str = self.__getPrettyOid(oid, prefix, label, suffix, modName,
                                          nodeDesc)
        finally:
            self.__lock.release()

        # Value
        if val is None:
            return oid_str, None

        val_str = ''
        self.__lock.acquire()
        try:
            mibNode, = mb.importSymbols(modName, nodeDesc)
        finally:
            self.__lock.release()
        if hasattr(mibNode, 'syntax'):
            syntax = mibNode.syntax
        else:
            syntax = val
        if syntax is None: # lame Agent may return a non-instance OID
            syntax = unknownSyntax
        if self.buildTypeInfo:
            val_str = val_str + '%s: ' % syntax.__class__.__name__
        if self.buildRawVals:
            val_str = val_str + str(val)
        elif self.buildHexVals: # XXX make it always in hex?
            if self.__intValue.isSuperTypeOf(val):
                val_str = val_str + repr(int(val))
            elif self.__oidValue.isSuperTypeOf(val):
                val_str = val_str + repr(tuple(val))
            else:
                val_str = val_str + repr(str(val))
        elif self.__timeValue.isSameTypeWith(val):
            if self.buildRawTimeTicks:
                val_str = val_str + str(int(val))
            else: # TimeTicks is not a TC
                val = int(val)
                d, m = divmod(val, 8640000)
                if d == 1:
                    val_str = val_str + '%d day ' % d
                else:
                    val_str = val_str + '%d days ' % d
                d, m = divmod(m, 360000)
                val_str = val_str + '%02d:' % d
                d, m = divmod(m, 6000)
                val_str = val_str + '%02d:' % d
                d, m = divmod(m, 100)
                val_str = val_str + '%02d.%02d' % (d, m)
        elif self.__oidValue.isSuperTypeOf(val):
            #oid, label, suffix = mvc.getNodeName(val)
            #val_str = val_str + string.join(
            #    tuple(map(lambda x: str(x), label+suffix)), '.'
            #    )
            self.__lock.acquire()
            try:
                prefix, label, suffix = mvc.getNodeName(val)
                modName, nodeDesc, _suffix = mvc.getNodeLocation(prefix)
                val_str = val_str + self.__getPrettyOid(val, prefix, label,
                                                        suffix, modName,
                                                        nodeDesc)
            finally:
                self.__lock.release()
        else:
            val_str = val_str + syntax.prettyOut(val)

        if self.buildUnits:
            if hasattr(mibNode, 'getUnits'):
                unit_str = mibNode.getUnits()
                if unit_str:
                    val_str = val_str + ' %s' % unit_str
        return oid_str, val_str
