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
# PySNMP SMI module. Autogenerated from smidump -f python ENTITY-MIB
# by libsmi2pysnmp-0.0.8-alpha at Wed Jan 28 13:40:24 2009,
# Python version (2, 3, 4, 'final', 0)

# Imported just in case new ASN.1 types would be created
from pyasn1.type import constraint, namedval

# Imports

( Integer, ObjectIdentifier, OctetString, ) = mibBuilder.importSymbols("ASN1", "Integer", "ObjectIdentifier", "OctetString")
( SnmpAdminString, ) = mibBuilder.importSymbols("SNMP-FRAMEWORK-MIB", "SnmpAdminString")
( ModuleCompliance, NotificationGroup, ObjectGroup, ) = mibBuilder.importSymbols("SNMPv2-CONF", "ModuleCompliance", "NotificationGroup", "ObjectGroup")
( Bits, Integer32, ModuleIdentity, MibIdentifier, NotificationType, MibScalar, MibTable, MibTableRow, MibTableColumn, TimeTicks, mib_2, ) = mibBuilder.importSymbols("SNMPv2-SMI", "Bits", "Integer32", "ModuleIdentity", "MibIdentifier", "NotificationType", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "TimeTicks", "mib-2")
( AutonomousType, RowPointer, TAddress, TDomain, TextualConvention, TimeStamp, TruthValue, ) = mibBuilder.importSymbols("SNMPv2-TC", "AutonomousType", "RowPointer", "TAddress", "TDomain", "TextualConvention", "TimeStamp", "TruthValue")

# Types

class PhysicalClass(Integer):
    subtypeSpec = Integer.subtypeSpec+constraint.SingleValueConstraint(5,3,2,6,9,11,1,7,4,8,10,)
    namedValues = namedval.NamedValues(("other", 1), ("port", 10), ("stack", 11), ("unknown", 2), ("chassis", 3), ("backplane", 4), ("container", 5), ("powerSupply", 6), ("fan", 7), ("sensor", 8), ("module", 9), )
    pass

class PhysicalIndex(Integer32):
    subtypeSpec = Integer32.subtypeSpec+constraint.ValueRangeConstraint(1,2147483647L)
    pass

class SnmpEngineIdOrNone(OctetString):
    subtypeSpec = OctetString.subtypeSpec+constraint.ValueSizeConstraint(0,32)
    pass


# Objects

entityMIB = ModuleIdentity((1, 3, 6, 1, 2, 1, 47)).setRevisions(("1999-12-07 00:00","1996-10-31 00:00",))
entityMIBObjects = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 1))
entityPhysical = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 1, 1))
entPhysicalTable = MibTable((1, 3, 6, 1, 2, 1, 47, 1, 1, 1))
entPhysicalEntry = MibTableRow((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1)).setIndexNames((0, "ENTITY-MIB", "entPhysicalIndex"))
entPhysicalIndex = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 1), PhysicalIndex()).setMaxAccess("noaccess")
entPhysicalDescr = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 2), SnmpAdminString()).setMaxAccess("readonly")
entPhysicalVendorType = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 3), AutonomousType()).setMaxAccess("readonly")
entPhysicalContainedIn = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess("readonly")
entPhysicalClass = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 5), PhysicalClass()).setMaxAccess("readonly")
entPhysicalParentRelPos = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 6), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-1, 2147483647L))).setMaxAccess("readonly")
entPhysicalName = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 7), SnmpAdminString()).setMaxAccess("readonly")
entPhysicalHardwareRev = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 8), SnmpAdminString()).setMaxAccess("readonly")
entPhysicalFirmwareRev = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 9), SnmpAdminString()).setMaxAccess("readonly")
entPhysicalSoftwareRev = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 10), SnmpAdminString()).setMaxAccess("readonly")
entPhysicalSerialNum = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 11), SnmpAdminString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 32))).setMaxAccess("readwrite")
entPhysicalMfgName = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 12), SnmpAdminString()).setMaxAccess("readonly")
entPhysicalModelName = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 13), SnmpAdminString()).setMaxAccess("readonly")
entPhysicalAlias = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 14), SnmpAdminString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 32))).setMaxAccess("readwrite")
entPhysicalAssetID = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 15), SnmpAdminString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 32))).setMaxAccess("readwrite")
entPhysicalIsFRU = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 16), TruthValue()).setMaxAccess("readonly")
entityLogical = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 1, 2))
entLogicalTable = MibTable((1, 3, 6, 1, 2, 1, 47, 1, 2, 1))
entLogicalEntry = MibTableRow((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1)).setIndexNames((0, "ENTITY-MIB", "entLogicalIndex"))
entLogicalIndex = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(1, 2147483647L))).setMaxAccess("noaccess")
entLogicalDescr = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 2), SnmpAdminString()).setMaxAccess("readonly")
entLogicalType = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 3), AutonomousType()).setMaxAccess("readonly")
entLogicalCommunity = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 4), OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 255))).setMaxAccess("readonly")
entLogicalTAddress = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 5), TAddress()).setMaxAccess("readonly")
entLogicalTDomain = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 6), TDomain()).setMaxAccess("readonly")
entLogicalContextEngineID = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 7), SnmpEngineIdOrNone()).setMaxAccess("readonly")
entLogicalContextName = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 2, 1, 1, 8), SnmpAdminString()).setMaxAccess("readonly")
entityMapping = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 1, 3))
entLPMappingTable = MibTable((1, 3, 6, 1, 2, 1, 47, 1, 3, 1))
entLPMappingEntry = MibTableRow((1, 3, 6, 1, 2, 1, 47, 1, 3, 1, 1)).setIndexNames((0, "ENTITY-MIB", "entLogicalIndex"), (0, "ENTITY-MIB", "entLPPhysicalIndex"))
entLPPhysicalIndex = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 3, 1, 1, 1), PhysicalIndex()).setMaxAccess("readonly")
entAliasMappingTable = MibTable((1, 3, 6, 1, 2, 1, 47, 1, 3, 2))
entAliasMappingEntry = MibTableRow((1, 3, 6, 1, 2, 1, 47, 1, 3, 2, 1)).setIndexNames((0, "ENTITY-MIB", "entPhysicalIndex"), (0, "ENTITY-MIB", "entAliasLogicalIndexOrZero"))
entAliasLogicalIndexOrZero = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 3, 2, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess("noaccess")
entAliasMappingIdentifier = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 3, 2, 1, 2), RowPointer()).setMaxAccess("readonly")
entPhysicalContainsTable = MibTable((1, 3, 6, 1, 2, 1, 47, 1, 3, 3))
entPhysicalContainsEntry = MibTableRow((1, 3, 6, 1, 2, 1, 47, 1, 3, 3, 1)).setIndexNames((0, "ENTITY-MIB", "entPhysicalIndex"), (0, "ENTITY-MIB", "entPhysicalChildIndex"))
entPhysicalChildIndex = MibTableColumn((1, 3, 6, 1, 2, 1, 47, 1, 3, 3, 1, 1), PhysicalIndex()).setMaxAccess("readonly")
entityGeneral = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 1, 4))
entLastChangeTime = MibScalar((1, 3, 6, 1, 2, 1, 47, 1, 4, 1), TimeStamp()).setMaxAccess("readonly")
entityMIBTraps = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 2))
entityMIBTrapPrefix = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 2, 0))
entityConformance = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 3))
entityCompliances = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 3, 1))
entityGroups = MibIdentifier((1, 3, 6, 1, 2, 1, 47, 3, 2))

# Augmentions

# Notifications

entConfigChange = NotificationType((1, 3, 6, 1, 2, 1, 47, 2, 0, 1)).setObjects()

# Groups

entityMappingGroup = ObjectGroup((1, 3, 6, 1, 2, 1, 47, 3, 2, 3)).setObjects(("ENTITY-MIB", "entAliasMappingIdentifier"), ("ENTITY-MIB", "entLPPhysicalIndex"), ("ENTITY-MIB", "entPhysicalChildIndex"), )
entityLogicalGroup = ObjectGroup((1, 3, 6, 1, 2, 1, 47, 3, 2, 2)).setObjects(("ENTITY-MIB", "entLogicalDescr"), ("ENTITY-MIB", "entLogicalCommunity"), ("ENTITY-MIB", "entLogicalType"), ("ENTITY-MIB", "entLogicalTAddress"), ("ENTITY-MIB", "entLogicalTDomain"), )
entityPhysicalGroup = ObjectGroup((1, 3, 6, 1, 2, 1, 47, 3, 2, 1)).setObjects(("ENTITY-MIB", "entPhysicalParentRelPos"), ("ENTITY-MIB", "entPhysicalVendorType"), ("ENTITY-MIB", "entPhysicalClass"), ("ENTITY-MIB", "entPhysicalName"), ("ENTITY-MIB", "entPhysicalContainedIn"), ("ENTITY-MIB", "entPhysicalDescr"), )
entityPhysical2Group = ObjectGroup((1, 3, 6, 1, 2, 1, 47, 3, 2, 6)).setObjects(("ENTITY-MIB", "entPhysicalSoftwareRev"), ("ENTITY-MIB", "entPhysicalHardwareRev"), ("ENTITY-MIB", "entPhysicalAlias"), ("ENTITY-MIB", "entPhysicalSerialNum"), ("ENTITY-MIB", "entPhysicalIsFRU"), ("ENTITY-MIB", "entPhysicalFirmwareRev"), ("ENTITY-MIB", "entPhysicalAssetID"), ("ENTITY-MIB", "entPhysicalModelName"), ("ENTITY-MIB", "entPhysicalMfgName"), )
entityGeneralGroup = ObjectGroup((1, 3, 6, 1, 2, 1, 47, 3, 2, 4)).setObjects(("ENTITY-MIB", "entLastChangeTime"), )
entityLogical2Group = ObjectGroup((1, 3, 6, 1, 2, 1, 47, 3, 2, 7)).setObjects(("ENTITY-MIB", "entLogicalTDomain"), ("ENTITY-MIB", "entLogicalType"), ("ENTITY-MIB", "entLogicalContextEngineID"), ("ENTITY-MIB", "entLogicalTAddress"), ("ENTITY-MIB", "entLogicalDescr"), ("ENTITY-MIB", "entLogicalContextName"), )
entityNotificationsGroup = ObjectGroup((1, 3, 6, 1, 2, 1, 47, 3, 2, 5)).setObjects(("ENTITY-MIB", "entConfigChange"), )

# Exports

# Module identity
mibBuilder.exportSymbols("ENTITY-MIB", PYSNMP_MODULE_ID=entityMIB)

# Types
mibBuilder.exportSymbols("ENTITY-MIB", PhysicalClass=PhysicalClass, PhysicalIndex=PhysicalIndex, SnmpEngineIdOrNone=SnmpEngineIdOrNone)

# Objects
mibBuilder.exportSymbols("ENTITY-MIB", entityMIB=entityMIB, entityMIBObjects=entityMIBObjects, entityPhysical=entityPhysical, entPhysicalTable=entPhysicalTable, entPhysicalEntry=entPhysicalEntry, entPhysicalIndex=entPhysicalIndex, entPhysicalDescr=entPhysicalDescr, entPhysicalVendorType=entPhysicalVendorType, entPhysicalContainedIn=entPhysicalContainedIn, entPhysicalClass=entPhysicalClass, entPhysicalParentRelPos=entPhysicalParentRelPos, entPhysicalName=entPhysicalName, entPhysicalHardwareRev=entPhysicalHardwareRev, entPhysicalFirmwareRev=entPhysicalFirmwareRev, entPhysicalSoftwareRev=entPhysicalSoftwareRev, entPhysicalSerialNum=entPhysicalSerialNum, entPhysicalMfgName=entPhysicalMfgName, entPhysicalModelName=entPhysicalModelName, entPhysicalAlias=entPhysicalAlias, entPhysicalAssetID=entPhysicalAssetID, entPhysicalIsFRU=entPhysicalIsFRU, entityLogical=entityLogical, entLogicalTable=entLogicalTable, entLogicalEntry=entLogicalEntry, entLogicalIndex=entLogicalIndex, entLogicalDescr=entLogicalDescr, entLogicalType=entLogicalType, entLogicalCommunity=entLogicalCommunity, entLogicalTAddress=entLogicalTAddress, entLogicalTDomain=entLogicalTDomain, entLogicalContextEngineID=entLogicalContextEngineID, entLogicalContextName=entLogicalContextName, entityMapping=entityMapping, entLPMappingTable=entLPMappingTable, entLPMappingEntry=entLPMappingEntry, entLPPhysicalIndex=entLPPhysicalIndex, entAliasMappingTable=entAliasMappingTable, entAliasMappingEntry=entAliasMappingEntry, entAliasLogicalIndexOrZero=entAliasLogicalIndexOrZero, entAliasMappingIdentifier=entAliasMappingIdentifier, entPhysicalContainsTable=entPhysicalContainsTable, entPhysicalContainsEntry=entPhysicalContainsEntry, entPhysicalChildIndex=entPhysicalChildIndex, entityGeneral=entityGeneral, entLastChangeTime=entLastChangeTime, entityMIBTraps=entityMIBTraps, entityMIBTrapPrefix=entityMIBTrapPrefix, entityConformance=entityConformance, entityCompliances=entityCompliances, entityGroups=entityGroups)

# Notifications
mibBuilder.exportSymbols("ENTITY-MIB", entConfigChange=entConfigChange)

# Groups
mibBuilder.exportSymbols("ENTITY-MIB", entityMappingGroup=entityMappingGroup, entityLogicalGroup=entityLogicalGroup, entityPhysicalGroup=entityPhysicalGroup, entityPhysical2Group=entityPhysical2Group, entityGeneralGroup=entityGeneralGroup, entityLogical2Group=entityLogical2Group, entityNotificationsGroup=entityNotificationsGroup)