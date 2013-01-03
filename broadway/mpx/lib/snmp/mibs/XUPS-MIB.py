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
# XUPS-MIB:  Defines XUPS-MIB (Powerware's proprietary PowerMIB)
#
# ============================================================================
# Created manually using smidump and RZ's custom version of libsmi2pysnmp
# which was part of /home/mevans/source/pysnmp-experiments/ at the time of
# execution.  Essentially::
#   $ cd /home/mevans/source/pysnmp-experiments/Powerware
#   $ smidump -f smiv2 MIBs/XUPS.MIB >XUPS-MIB.smidump.smiv2
#   $ smidump -f python XUPS-MIB.smidump.smiv2 >XUPS-MIB.smidump.py
#   $ cat XUPS-MIB.smidump.py | ../libsmi2pysnmp >XUPS-MIB.py
#
# ==========================================================================
#
# From the XUPS.MIB comments:
#
# -- Title XUPS MIB - POWERMIB
# -- Date January 19, 1993
# -- By: Brian Hammill - Exide Electronics
# -- Copyright 1992-98 by Exide Electronics
# -- Copyright 1999+ by Powerware Corporation
# -- May not be used without permission from Powerware Corporation
#
# -- Revised February 25, 1993 Kevin Debruhl, Brian Hammill
# -- Revised June 21, 1993 Brian Hammill
# -- Revised (Variable types of ) August 5, 1993 Brian Hammill
# -- Revised August 16, 1993 Dale Langer - added units of measure
#
# -- Added Event History to Alarm Group and get/set time/date.
# -- 8/20/93 Brian Hammill
# -- Cleanup for final release.  9/3/93 Brian Hammill
#
# -- Release Version 0.91 9/17/93
# -- Release Version 1.00 11/16/93 Kevin DeBruhl
#
# -- Changes for Release Version 2.00  9/7/94  Tom Brennan
# -- 1) Renamed UPS-MIB to XUPS-MIB and all names from upsVariable
# --    to xupsVariable to avoid conflicts with RFC 1628 Standard UPS MIB names
# -- 2) Renamed all traps from upsName to xupstName to avoid conflicts with
# --      similar alarm names
# -- 3) Added well known alarms and traps:
# --      BreakerOpen, AlarmEntryAdded, AlarmEntryRemoved
# -- 4) Deprecated xupsControlOutputOnTrapDelay
# -- 5) Added xupsTrapControl group
# -- 6) enumerated the value startTest for xupsTestBattery
# -- 7) Defined oid values to use for sysObjectId
#
# -- Changes for Release Version 2.10  11/1/94  Tom Brennan
# -- 1) Corrected type of xupsAlarms, xupsAlarmNumEvents (Gauge)
# -- 2) Defined three trap sources, which differ in their descriptions
# --      of trap variables (none, Defined, defined plus Port N Interface vars)
# -- 3) Clarified AlarmEvent order and numbering
#
# -- Changes for Release Version 2.11  3/30/95  Tom Brennan
# -- 1) Removed references to version 2.00 MIB files
# -- 2) Added range declarations for appropriate objects
# -- 3) Added Object IDs for new products
#
# -- Changes for Release Version 2.20  8/29/96  Tom Brennan
# -- 1) Corrected upper Integer range from 2147483648 to 2147483647
# -- 2) Added xupsEnvironment group and its objects and alarm
# --    xupsAmbientTempBad
# -- 3) Added xupsBatteryAbmStatus to monitor Advanced Battery Management
# --    status
# -- 4) Added well-known alarms from RFC 1628 which weren't previously
# --    supported:
# --    xupsAlarmBatteryBad, xupsOutputOffAsRequested,
# --    xupsDiagnosticTestFailed, xupsCommunicationsLost,
# --    xupsUpsShutdownPending, xupsAlarmTestInProgress
# -- 5) Added Defined and PortN (but not Basic) type traps for above alarms
# -- 6) Added xupsControlToBypassDelay to allow Go To Bypass command.
#
# -- Changes for Release Version 2.21  5/19/99  Tom Brennan
# -- Renaming from Exide Electronics to Powerware Corporation
#
# -- Changes for Release Version 3.00 3-Apr-02 Connectivity Systems Group, 
# --		Power Systems Division, Invensys
# -- 1) Rolled in Receptacle Control extensions from separate file
# -- 2) Added Topology group objects
# -- 3) Added new var xupsOutputSource, which extends upsOutputSource
# -- 4) Added new var xupsAlarmEventMsg to replace the other deprecated
# --    xAEEntry vars
#
# --
# -- Customer Support: direct questions to info@psd.invensys.com
# --      or call Tech Support:        
# --	     Single Phase: (800) 365-4892 or (919) 870-3149
# --	     Three Phase:  (800) 843-9433 or (919) 871-1800
# --	  or techsupt@psd.invensys.com
# --
# ==========================================================================
# PySNMP SMI module. Autogenerated from smidump -f python XUPS-MIB
# by libsmi2pysnmp-0.0.7-alpha-rz2 at Mon Feb 25 11:31:16 2008,
# Python version (2, 2, 3, 'final', 0)
# --------------------------------------------------------------------------
# MIBs/XUPS.MIB:1305: object `xupsTrapMessage' of notification
#     `xupstdControlOff' must not be `not-accessible'
# MIBs/XUPS.MIB:1314: object `xupsTrapMessage' of notification
#     `xupstdControlOn' must not be `not-accessible'
# MIBs/XUPS.MIB:1323: object `xupsTrapMessage' of notification
#     `xupstdOnBattery' must not be `not-accessible'
# MIBs/XUPS.MIB:1332: object `xupsTrapMessage' of notification
#     `xupstdLowBattery' must not be `not-accessible'
# MIBs/XUPS.MIB:1341: object `xupsTrapMessage' of notification
#     `xupstdUtilityPowerRestored' must not be `not-accessible'
# MIBs/XUPS.MIB:1350: object `xupsTrapMessage' of notification
#     `xupstdReturnFromLowBattery' must not be `not-accessible'
# MIBs/XUPS.MIB:1359: object `xupsTrapMessage' of notification
#     `xupstdOutputOverload' must not be `not-accessible'
# MIBs/XUPS.MIB:1369: object `xupsTrapMessage' of notification
#     `xupstdInternalFailure' must not be `not-accessible'
# MIBs/XUPS.MIB:1380: object `xupsTrapMessage' of notification
#     `xupstdBatteryDischarged' must not be `not-accessible'
# MIBs/XUPS.MIB:1389: object `xupsTrapMessage' of notification
#     `xupstdInverterFailure' must not be `not-accessible'
# MIBs/XUPS.MIB:1398: object `xupsTrapMessage' of notification
#     `xupstdOnBypass' must not be `not-accessible'
# MIBs/XUPS.MIB:1406: object `xupsTrapMessage' of notification
#     `xupstdBypassNotAvailable' must not be `not-accessible'
# MIBs/XUPS.MIB:1414: object `xupsTrapMessage' of notification
#     `xupstdOutputOff' must not be `not-accessible'
# MIBs/XUPS.MIB:1423: object `xupsTrapMessage' of notification
#     `xupstdInputFailure' must not be `not-accessible'
# MIBs/XUPS.MIB:1432: object `xupsTrapMessage' of notification
#     `xupstdBuildingAlarm' must not be `not-accessible'
# MIBs/XUPS.MIB:1440: object `xupsTrapMessage' of notification
#     `xupstdShutdownImminent' must not be `not-accessible'
# MIBs/XUPS.MIB:1448: object `xupsTrapMessage' of notification
#     `xupstdOnInverter' must not be `not-accessible'
# MIBs/XUPS.MIB:1457: object `xupsTrapMessage' of notification
#     `xupstdBreakerOpen' must not be `not-accessible'
# MIBs/XUPS.MIB:1465: object `xupsTrapMessage' of notification
#     `xupstdAlarmEntryAdded' must not be `not-accessible'
# MIBs/XUPS.MIB:1475: object `xupsTrapMessage' of notification
#     `xupstdAlarmEntryRemoved' must not be `not-accessible'
# MIBs/XUPS.MIB:1484: object `xupsTrapMessage' of notification
#     `xupstdAlarmBatteryBad' must not be `not-accessible'
# MIBs/XUPS.MIB:1492: object `xupsTrapMessage' of notification
#     `xupstdOutputOffAsRequested' must not be `not-accessible'
# MIBs/XUPS.MIB:1500: object `xupsTrapMessage' of notification
#     `xupstdDiagnosticTestFailed' must not be `not-accessible'
# MIBs/XUPS.MIB:1508: object `xupsTrapMessage' of notification
#     `xupstdCommunicationsLost' must not be `not-accessible'
# MIBs/XUPS.MIB:1517: object `xupsTrapMessage' of notification
#     `xupstdUpsShutdownPending' must not be `not-accessible'
# MIBs/XUPS.MIB:1525: object `xupsTrapMessage' of notification
#     `xupstdAlarmTestInProgress' must not be `not-accessible'
# MIBs/XUPS.MIB:1535: object `xupsTrapMessage' of notification
#     `xupstdAmbientTempBad' must not be `not-accessible'
# MIBs/XUPS.MIB:1554: object `xupsTrapMessage' of notification
#     `xupstpControlOff' must not be `not-accessible'
# MIBs/XUPS.MIB:1564: object `xupsTrapMessage' of notification
#     `xupstpControlOn' must not be `not-accessible'
# MIBs/XUPS.MIB:1574: object `xupsTrapMessage' of notification
#     `xupstpOnBattery' must not be `not-accessible'
# MIBs/XUPS.MIB:1584: object `xupsTrapMessage' of notification
#     `xupstpLowBattery' must not be `not-accessible'
# MIBs/XUPS.MIB:1594: object `xupsTrapMessage' of notification
#     `xupstpUtilityPowerRestored' must not be `not-accessible'
# MIBs/XUPS.MIB:1604: object `xupsTrapMessage' of notification
#     `xupstpReturnFromLowBattery' must not be `not-accessible'
# MIBs/XUPS.MIB:1614: object `xupsTrapMessage' of notification
#     `xupstpOutputOverload' must not be `not-accessible'
# MIBs/XUPS.MIB:1625: object `xupsTrapMessage' of notification
#     `xupstpInternalFailure' must not be `not-accessible'
# MIBs/XUPS.MIB:1637: object `xupsTrapMessage' of notification
#     `xupstpBatteryDischarged' must not be `not-accessible'
# MIBs/XUPS.MIB:1647: object `xupsTrapMessage' of notification
#     `xupstpInverterFailure' must not be `not-accessible'
# MIBs/XUPS.MIB:1657: object `xupsTrapMessage' of notification
#     `xupstpOnBypass' must not be `not-accessible'
# MIBs/XUPS.MIB:1666: object `xupsTrapMessage' of notification
#     `xupstpBypassNotAvailable' must not be `not-accessible'
# MIBs/XUPS.MIB:1675: object `xupsTrapMessage' of notification
#     `xupstpOutputOff' must not be `not-accessible'
# MIBs/XUPS.MIB:1685: object `xupsTrapMessage' of notification
#     `xupstpInputFailure' must not be `not-accessible'
# MIBs/XUPS.MIB:1695: object `xupsTrapMessage' of notification
#     `xupstpBuildingAlarm' must not be `not-accessible'
# MIBs/XUPS.MIB:1704: object `xupsTrapMessage' of notification
#     `xupstpShutdownImminent' must not be `not-accessible'
# MIBs/XUPS.MIB:1713: object `xupsTrapMessage' of notification
#     `xupstpOnInverter' must not be `not-accessible'
# MIBs/XUPS.MIB:1723: object `xupsTrapMessage' of notification
#     `xupstpBreakerOpen' must not be `not-accessible'
# MIBs/XUPS.MIB:1732: object `xupsTrapMessage' of notification
#     `xupstpAlarmEntryAdded' must not be `not-accessible'
# MIBs/XUPS.MIB:1743: object `xupsTrapMessage' of notification
#     `xupstpAlarmEntryRemoved' must not be `not-accessible'
# MIBs/XUPS.MIB:1753: object `xupsTrapMessage' of notification
#     `xupstpAlarmBatteryBad' must not be `not-accessible'
# MIBs/XUPS.MIB:1762: object `xupsTrapMessage' of notification
#     `xupstpOutputOffAsRequested' must not be `not-accessible'
# MIBs/XUPS.MIB:1771: object `xupsTrapMessage' of notification
#     `xupstpDiagnosticTestFailed' must not be `not-accessible'
# MIBs/XUPS.MIB:1780: object `xupsTrapMessage' of notification
#     `xupstpCommunicationsLost' must not be `not-accessible'
# MIBs/XUPS.MIB:1790: object `xupsTrapMessage' of notification
#     `xupstpUpsShutdownPending' must not be `not-accessible'
# MIBs/XUPS.MIB:1799: object `xupsTrapMessage' of notification
#     `xupstpAlarmTestInProgress' must not be `not-accessible'
# MIBs/XUPS.MIB:1810: object `xupsTrapMessage' of notification
#     `xupstpAmbientTempBad' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1563: missing MODULE-IDENTITY clause in SMIv2 MIB
# XUPS-MIB.smidump.smiv2:1123: object `xupsTrapMessage' of notification
#     `xupstdControlOff' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1131: object `xupsTrapMessage' of notification
#     `xupstdControlOn' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1139: object `xupsTrapMessage' of notification
#     `xupstdOnBattery' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1147: object `xupsTrapMessage' of notification
#     `xupstdLowBattery' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1155: object `xupsTrapMessage' of notification
#     `xupstdUtilityPowerRestored' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1162: object `xupsTrapMessage' of notification
#     `xupstdReturnFromLowBattery' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1169: object `xupsTrapMessage' of notification
#     `xupstdOutputOverload' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1177: object `xupsTrapMessage' of notification
#     `xupstdInternalFailure' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1186: object `xupsTrapMessage' of notification
#     `xupstdBatteryDischarged' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1193: object `xupsTrapMessage' of notification
#     `xupstdInverterFailure' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1200: object `xupsTrapMessage' of notification
#     `xupstdOnBypass' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1207: object `xupsTrapMessage' of notification
#     `xupstdBypassNotAvailable' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1214: object `xupsTrapMessage' of notification
#     `xupstdOutputOff' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1221: object `xupsTrapMessage' of notification
#     `xupstdInputFailure' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1229: object `xupsTrapMessage' of notification
#     `xupstdBuildingAlarm' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1236: object `xupsTrapMessage' of notification
#     `xupstdShutdownImminent' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1243: object `xupsTrapMessage' of notification
#     `xupstdOnInverter' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1251: object `xupsTrapMessage' of notification
#     `xupstdBreakerOpen' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1258: object `xupsTrapMessage' of notification
#     `xupstdAlarmEntryAdded' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1267: object `xupsTrapMessage' of notification
#     `xupstdAlarmEntryRemoved' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1275: object `xupsTrapMessage' of notification
#     `xupstdAlarmBatteryBad' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1282: object `xupsTrapMessage' of notification
#     `xupstdOutputOffAsRequested' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1289: object `xupsTrapMessage' of notification
#     `xupstdDiagnosticTestFailed' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1296: object `xupsTrapMessage' of notification
#     `xupstdCommunicationsLost' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1304: object `xupsTrapMessage' of notification
#     `xupstdUpsShutdownPending' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1311: object `xupsTrapMessage' of notification
#     `xupstdAlarmTestInProgress' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1319: object `xupsTrapMessage' of notification
#     `xupstdAmbientTempBad' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1330: object `xupsTrapMessage' of notification
#     `xupstpControlOff' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1339: object `xupsTrapMessage' of notification
#     `xupstpControlOn' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1348: object `xupsTrapMessage' of notification
#     `xupstpOnBattery' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1357: object `xupsTrapMessage' of notification
#     `xupstpLowBattery' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1366: object `xupsTrapMessage' of notification
#     `xupstpUtilityPowerRestored' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1374: object `xupsTrapMessage' of notification
#     `xupstpReturnFromLowBattery' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1382: object `xupsTrapMessage' of notification
#     `xupstpOutputOverload' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1391: object `xupsTrapMessage' of notification
#     `xupstpInternalFailure' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1401: object `xupsTrapMessage' of notification
#     `xupstpBatteryDischarged' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1409: object `xupsTrapMessage' of notification
#     `xupstpInverterFailure' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1417: object `xupsTrapMessage' of notification
#     `xupstpOnBypass' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1425: object `xupsTrapMessage' of notification
#     `xupstpBypassNotAvailable' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1433: object `xupsTrapMessage' of notification
#     `xupstpOutputOff' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1441: object `xupsTrapMessage' of notification
#     `xupstpInputFailure' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1450: object `xupsTrapMessage' of notification
#     `xupstpBuildingAlarm' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1458: object `xupsTrapMessage' of notification
#     `xupstpShutdownImminent' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1466: object `xupsTrapMessage' of notification
#     `xupstpOnInverter' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1475: object `xupsTrapMessage' of notification
#     `xupstpBreakerOpen' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1483: object `xupsTrapMessage' of notification
#     `xupstpAlarmEntryAdded' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1493: object `xupsTrapMessage' of notification
#     `xupstpAlarmEntryRemoved' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1502: object `xupsTrapMessage' of notification
#     `xupstpAlarmBatteryBad' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1510: object `xupsTrapMessage' of notification
#     `xupstpOutputOffAsRequested' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1518: object `xupsTrapMessage' of notification
#     `xupstpDiagnosticTestFailed' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1526: object `xupsTrapMessage' of notification
#     `xupstpCommunicationsLost' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1535: object `xupsTrapMessage' of notification
#     `xupstpUpsShutdownPending' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1543: object `xupsTrapMessage' of notification
#     `xupstpAlarmTestInProgress' must not be `not-accessible'
# XUPS-MIB.smidump.smiv2:1552: object `xupsTrapMessage' of notification
#     `xupstpAmbientTempBad' must not be `not-accessible'
# smidump: module `XUPS-MIB.smidump.smiv2' contains errors, expect flawed
#     output
# ==========================================================================

# Imported just in case new ASN.1 types would be created
from pyasn1.type import constraint, namedval

# Imports

( Integer, ObjectIdentifier, OctetString, ) = mibBuilder.importSymbols('ASN1', 'Integer', 'ObjectIdentifier', 'OctetString')
( ifDescr, ifIndex, ) = mibBuilder.importSymbols('RFC1213-MIB', 'ifDescr', 'ifIndex')
( Bits, Counter32, Counter64, Gauge32, Integer32, IpAddress, MibIdentifier, NotificationType, MibScalar, MibTable, MibTableRow, MibTableColumn, Opaque, TimeTicks, Unsigned32, enterprises, ) = mibBuilder.importSymbols('SNMPv2-SMI', 'Bits', 'Counter32', 'Counter64', 'Gauge32', 'Integer32', 'IpAddress', 'MibIdentifier', 'NotificationType', 'MibScalar', 'MibTable', 'MibTableRow', 'MibTableColumn', 'Opaque', 'TimeTicks', 'Unsigned32', 'enterprises')
( DisplayString, ) = mibBuilder.importSymbols('SNMPv2-TC', 'DisplayString')

# Objects

powerware = MibIdentifier((1, 3, 6, 1, 4, 1, 534))
xups = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1))
xupsNull = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 0))
xupsTrapBasic = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 0, 0))
xupsIdent = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 1))
xupsIdentManufacturer = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 1, 1), DisplayString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 31))).setMaxAccess('readonly').setDescription('The UPS Manufacturer Name (e.g. Powerware Corporation).')
xupsIdentModel = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 1, 2), DisplayString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 63))).setMaxAccess('readonly').setDescription('The UPS Model (e.g. Powerware Plus Model 18).')
xupsIdentSoftwareVersion = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 1, 3), DisplayString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 63))).setMaxAccess('readonly').setDescription('The firmware revision level(s) of the UPS microcontroller(s).')
xupsIdentOemCode = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 1, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 255))).setMaxAccess('readonly').setDescription('A binary code indicating who the UPS was manufactured or labeled for.  \n0 or 255 indicates Powerware itself.')
xupsBattery = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 2))
xupsBatTimeRemaining = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 2, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('Battery run time in seconds before UPS turns off due\nto low battery.')
xupsBatVoltage = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 2, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('Battery voltage as reported by the UPS meters.')
xupsBatCurrent = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 2, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-2147483648L, 2147483647L))).setMaxAccess('readonly').setDescription('Battery Current as reported by the UPS metering.\nCurrent is positive when discharging, negative\nwhen recharging the battery.')
xupsBatCapacity = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 2, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 100))).setMaxAccess('readonly').setDescription('Battery percent charge.')
xupsBatteryAbmStatus = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 2, 5), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(1,5,2,4,3,)).subtype(namedValues=namedval.NamedValues(('batteryCharging', 1), ('batteryDischarging', 2), ('batteryFloating', 3), ('batteryResting', 4), ('unknown', 5), ))).setMaxAccess('readonly').setDescription('Gives the status of the Advanced Battery Management;\nbatteryFloating(3) status means that the charger is temporarily \ncharging the battery to its float voltage; batteryResting(4) is the \nstate when the battery is fully charged and none of the other actions \n(charging/discharging/floating) is being done.')
xupsInput = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 3))
xupsInputFrequency = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 3, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The utility line frequency in tenths of Hz.')
xupsInputLineBads = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 3, 2), Counter32()).setMaxAccess('readonly').setDescription('The number of times the Input was out of tolerance\nin voltage or frequency.')
xupsInputNumPhases = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 3, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 6))).setMaxAccess('readonly').setDescription('...')
xupsInputTable = MibTable((1, 3, 6, 1, 4, 1, 534, 1, 3, 4)).setDescription('The Aggregate Object with number of entries equal to\nNumPhases and including the xupsInput group.')
xupsInputEntry = MibTableRow((1, 3, 6, 1, 4, 1, 534, 1, 3, 4, 1)).setIndexNames((0, 'XUPS-MIB', 'xupsInputPhase')).setDescription('The input table entry containing the current,\nvoltage, etc.')
xupsInputPhase = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 3, 4, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 6))).setMaxAccess('readonly').setDescription('The number of the phase.  Serves as index for input table.')
xupsInputVoltage = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 3, 4, 1, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured input voltage from the UPS meters in volts.')
xupsInputCurrent = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 3, 4, 1, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured input current from the UPS meters in amps.')
xupsInputWatts = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 3, 4, 1, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured input real power in watts.')
xupsOutput = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 4))
xupsOutputLoad = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 4, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 200))).setMaxAccess('readonly').setDescription('The UPS output load in percent of rated capacity.')
xupsOutputFrequency = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 4, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured UPS output frequency in tenths of Hz.')
xupsOutputNumPhases = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 4, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 6))).setMaxAccess('readonly').setDescription('The number of metered output phases, serves as the table\nindex.')
xupsOutputTable = MibTable((1, 3, 6, 1, 4, 1, 534, 1, 4, 4)).setDescription('The Aggregate Object with number of entries equal to NumPhases\nand including the xupsOutput group.')
xupsOutputEntry = MibTableRow((1, 3, 6, 1, 4, 1, 534, 1, 4, 4, 1)).setIndexNames((0, 'XUPS-MIB', 'xupsOutputPhase')).setDescription('Output Table Entry containing voltage, current, etc.')
xupsOutputPhase = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 4, 4, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 6))).setMaxAccess('readonly').setDescription('The number {1..3} of the output phase.')
xupsOutputVoltage = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 4, 4, 1, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured output voltage from the UPS metering in volts.')
xupsOutputCurrent = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 4, 4, 1, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured UPS output current in amps.')
xupsOutputWatts = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 4, 4, 1, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured real output power in watts.')
xupsOutputSource = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 4, 5), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(2,3,5,8,7,1,10,4,9,6,)).subtype(namedValues=namedval.NamedValues(('other', 1), ('highEfficiencyMode', 10), ('none', 2), ('normal', 3), ('bypass', 4), ('battery', 5), ('booster', 6), ('reducer', 7), ('parallelCapacity', 8), ('parallelRedundant', 9), ))).setMaxAccess('readonly').setDescription('The present source of output power.  The enumeration\nnone(2) indicates that there is no source of output\npower (and therefore no output power), for example,\nthe system has opened the output breaker.')
xupsBypass = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 5))
xupsBypassFrequency = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 5, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The bypass frequency in tenths of Hz.')
xupsBypassNumPhases = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 5, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 6))).setMaxAccess('readonly').setDescription('The number of lines in the UPS bypass table.')
xupsBypassTable = MibTable((1, 3, 6, 1, 4, 1, 534, 1, 5, 3)).setDescription('...')
xupsBypassEntry = MibTableRow((1, 3, 6, 1, 4, 1, 534, 1, 5, 3, 1)).setIndexNames((0, 'XUPS-MIB', 'xupsBypassPhase')).setDescription('Entry in the XUPS bypass table.')
xupsBypassPhase = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 5, 3, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 6))).setMaxAccess('readonly').setDescription('The Bypass Phase, index for the table.')
xupsBypassVoltage = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 5, 3, 1, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The measured UPS bypass voltage in volts.')
xupsEnvironment = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 6))
xupsEnvAmbientTemp = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 6, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-100, 200))).setMaxAccess('readonly').setDescription('The reading of the ambient temperature in the vicinity of the UPS.')
xupsEnvAmbientLowerLimit = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 6, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-100, 200))).setMaxAccess('readwrite').setDescription('The Lower Limit of the ambient temperature; if xupsEnvAmbientTemp \nfalls below this value, the xupsAmbientTempBad alarm will occur.')
xupsEnvAmbientUpperLimit = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 6, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-100, 200))).setMaxAccess('readwrite').setDescription('The Upper Limit of the ambient temperature; if xupsEnvAmbientTemp \nrises above this value, the xupsAmbientTempBad alarm will occur.\nThis value should be greater than xupsEnvAmbientLowerLimit.')
xupsAlarm = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7))
xupsAlarms = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 7, 1), Gauge32()).setMaxAccess('readonly').setDescription('The current number of alarm conditions.')
xupsAlarmTable = MibTable((1, 3, 6, 1, 4, 1, 534, 1, 7, 2)).setDescription('...')
xupsAlarmEntry = MibTableRow((1, 3, 6, 1, 4, 1, 534, 1, 7, 2, 1)).setIndexNames((0, 'XUPS-MIB', 'xupsAlarmID')).setDescription('...')
xupsAlarmID = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 2, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(1, 2147483647L))).setMaxAccess('readonly').setDescription('A unique identifier for an alarm condition.')
xupsAlarmDescr = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 2, 1, 2), ObjectIdentifier()).setMaxAccess('readonly').setDescription('A reference to an alarm description object.  The object\nreferenced should not be accessible, but rather be used to\nprovide a unique description of the alarm condition.')
xupsAlarmTime = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 2, 1, 3), TimeTicks()).setMaxAccess('readonly').setDescription('The value of the MIB-II variable sysUpTime when the alarm\ncondition occurred.')
xupsOnBattery = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 3))
xupsLowBattery = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 4))
xupsUtilityPowerRestored = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 5))
xupsReturnFromLowBattery = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 6))
xupsOutputOverload = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 7))
xupsInternalFailure = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 8))
xupsBatteryDischarged = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 9))
xupsInverterFailure = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 10))
xupsOnBypass = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 11))
xupsBypassNotAvailable = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 12))
xupsOutputOff = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 13))
xupsInputFailure = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 14))
xupsBuildingAlarm = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 15))
xupsShutdownImminent = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 16))
xupsOnInverter = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 17))
xupsAlarmNumEvents = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 7, 18), Gauge32()).setMaxAccess('readonly').setDescription('The number of entries in the UPS event history queue.')
xupsAlarmEventTable = MibTable((1, 3, 6, 1, 4, 1, 534, 1, 7, 19)).setDescription('A table of the UPS internal event history queue.')
xupsAlarmEventEntry = MibTableRow((1, 3, 6, 1, 4, 1, 534, 1, 7, 19, 1)).setIndexNames((0, 'XUPS-MIB', 'xupsAlarmEventID')).setDescription('One of the entries in the UPS event history queue.')
xupsAlarmEventID = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 19, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(1, 400))).setMaxAccess('readonly').setDescription('A unique number that reflects the order in which the event\noccurred. The oldest event in the queue will be number 1.\nSubsequent events will be numbered 2, 3, 4, etc.')
xupsAlarmEventDateAndTime = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 19, 1, 2), DisplayString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 22))).setMaxAccess('readonly').setDescription('The time and date that an event occurred as recorded in the UPS\ninternal event queue.  This string will reflect the time and\ndate as set in the UPS itself and will not be referenced to\nsysUpTime.  The format is MM/DD/YYYY:HH:MM:SS.  Time is 24 hour                 standard.')
xupsAlarmEventKind = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 19, 1, 3), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(3,2,1,)).subtype(namedValues=namedval.NamedValues(('occurred', 1), ('cleared', 2), ('unknown', 3), ))).setMaxAccess('readonly').setDescription('Enumerated value that tells whether the event is an\noccurrence of an alarm condition or a clearing of an\nalarm condition.')
xupsAlarmEventDescr = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 19, 1, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription("A description of the event stored in the UPS event queue.  \nThis description will be a sixteen bit integer value \nrepresenting one of the defined alarms in the Powerware Binary \nComputer Mode communication specification; for example,\na value of 0 represents the 'Inverter AC Over Voltage'\nalarm (byte 1, bit 0 in the BCM Alarm Map).")
xupsAlarmEventMsg = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 7, 19, 1, 5), DisplayString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 80))).setMaxAccess('readonly').setDescription('A text string describing each entry in the Event Log.  The format of this\ntext message is free (not fixed) for the operator to read; good contents \nwould be a time & date stamp, the event type, and a description of the event.')
xupsBreakerOpen = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 20))
xupsAlarmEntryAdded = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 21))
xupsAlarmEntryRemoved = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 22))
xupsAlarmBatteryBad = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 23))
xupsOutputOffAsRequested = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 24))
xupsDiagnosticTestFailed = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 25))
xupsCommunicationsLost = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 26))
xupsUpsShutdownPending = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 27))
xupsAlarmTestInProgress = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 28))
xupsAmbientTempBad = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 7, 29))
xupsTest = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 8))
xupsTestBattery = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 8, 1), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(1,)).subtype(namedValues=namedval.NamedValues(('startTest', 1), ))).setMaxAccess('readwrite').setDescription('Setting this variable to startTest initiates the\nbattery test.  All other set values are invalid.')
xupsTestBatteryStatus = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 8, 2), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(7,3,6,2,1,4,5,)).subtype(namedValues=namedval.NamedValues(('unknown', 1), ('passed', 2), ('failed', 3), ('inProgress', 4), ('notSupported', 5), ('inhibited', 6), ('scheduled', 7), ))).setMaxAccess('readonly').setDescription('Reading this enumerated value gives an indication of the\nUPS Battery test status.')
xupsControl = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 9))
xupsControlOutputOffDelay = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 9, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readwrite').setDescription('Setting this value to other than zero will cause the UPS\noutput to turn off after the number of seconds.\nSetting it to 0 will cause an attempt to abort a pending\nshutdown.')
xupsControlOutputOnDelay = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 9, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readwrite').setDescription('Setting this value to other than zero will cause the UPS\noutput to turn on after the number of seconds.\nSetting it to 0 will cause an attempt to abort a pending\nstartup.')
xupsControlOutputOffTrapDelay = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 9, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readwrite').setDescription('When xupsControlOutputOffDelay reaches this value, a trap will\nbe sent.')
xupsControlOutputOnTrapDelay = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 9, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readwrite').setDescription('When xupsControlOutputOnDelay reaches this value, a\nxupsOutputOff trap will be sent.')
xupsControlToBypassDelay = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 9, 5), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readwrite').setDescription('Setting this value to other than zero will cause the UPS\noutput to go to Bypass after the number of seconds.\n\t If the Bypass is unavailable, this may cause the UPS\n\t to not supply power to the load.\nSetting it to 0 will cause an attempt to abort a pending\nshutdown.')
xupsConfig = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 10))
xupsConfigOutputVoltage = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 10, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The nominal UPS Output voltage per phase in volts.')
xupsConfigInputVoltage = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 10, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The nominal UPS Input voltage per phase in volts.')
xupsConfigOutputWatts = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 10, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The nominal UPS available real power output in watts.')
xupsConfigOutputFreq = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 10, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647L))).setMaxAccess('readonly').setDescription('The nominal output frequency in tenths of Hz.')
xupsConfigDateAndTime = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 10, 5), DisplayString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 22))).setMaxAccess('readwrite').setDescription('Date and time information for the UPS.  Setting this variable\nwill initiate a set UPS date and time to this value.  Reading\nthis variable will return the UPS time and date.  This value\nis not referenced to sysUpTime.  It is simply the clock value\nfrom the UPS real time clock.\nFormat is as follows: MM/DD/YYYY:HH:MM:SS.')
xupsTrapControl = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 11))
xupsMaxTrapLevel = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 11, 1), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(4,1,2,3,)).subtype(namedValues=namedval.NamedValues(('none', 1), ('critical', 2), ('major', 3), ('allTraps', 4), ))).setMaxAccess('readwrite').setDescription('The level of severity of traps which will be sent to the\nrequesting host; individual trap receivers will have\nindividual values for this variable.  Values are:\n(1) none: no traps will be sent to this host;\n(2) critical: only traps for Critical alarm conditions will\n   be sent to this host;\n(3) major: Critical and Major traps will be sent;\n(4) allTraps: all Traps will be sent to this host\n   (Critical, Major, Minor, Informational).')
xupsSendTrapType = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 11, 2), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(3,2,1,4,)).subtype(namedValues=namedval.NamedValues(('stnd', 1), ('xups', 2), ('stndPlus', 3), ('xupsPlus', 4), ))).setMaxAccess('readwrite').setDescription('The type of traps which will be sent to the\nrequesting host; individual trap receivers will have\nindividual values for this variable.  The additional\nvariables in types (3) and (4) are useful for determining\nwhich UPS is the source on multi-port network adapters,\nand for getting additional descriptive information.\nTypes (1) through (4) are all SNMP version 1 trap PDUs.\nValues are:\n(1) stnd: Traps as defined in the Standard UPS MIB (RFC1628)\n   and Generic (MIB II) traps as defined in RFC 1215.\n(2) xups: xupsTrapDefined Traps as defined in the PowerMIB\n   and Generic (MIB II) traps as defined in RFC 1215.\n(3) stndPlus: same as stnd plus variables from the interface\n   group and, where appropriate, xupsTrapMessage.\n(4) xupsPlus: xupsTrapPortN Traps (same as xups plus \n   variables from the interface group) and, \n   for authFail, xupsTrapMessage.')
xupsTrapMessage = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 11, 3), DisplayString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 79))).setMaxAccess('noaccess').setDescription('A descriptive message which may be sent with traps to\nfurther explain the reason for the trap.')
xupsTrapSource = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 11, 4))
xupsTrapDefined = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1))
xupsTrapPortN = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2))
xupsRecep = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 12))
xupsNumReceptacles = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 12, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 64))).setMaxAccess('readonly').setDescription('The number of independently controllable Receptacles, as described in the \nxupsRecepTable.')
xupsRecepTable = MibTable((1, 3, 6, 1, 4, 1, 534, 1, 12, 2)).setDescription('The Aggregate Object with number of entries equal to\nNumReceptacles and including the xupsRecep group.')
xupsRecepEntry = MibTableRow((1, 3, 6, 1, 4, 1, 534, 1, 12, 2, 1)).setIndexNames((0, 'XUPS-MIB', 'xupsRecepIndex')).setDescription('The Recep table entry, etc.')
xupsRecepIndex = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 12, 2, 1, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(1, 64))).setMaxAccess('readonly').setDescription('The number of the Receptacle. Serves as index for Receptacle table.')
xupsRecepStatus = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 12, 2, 1, 2), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(1,3,2,5,4,)).subtype(namedValues=namedval.NamedValues(('on', 1), ('off', 2), ('pendingOff', 3), ('pendingOn', 4), ('unknown', 5), ))).setMaxAccess('readonly').setDescription('The Recep Status 1=On/Close, 2=Off/Open, 3=On w/Pending Off, \n4=Off w/Pending ON, 5=Unknown.')
xupsRecepOffDelaySecs = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 12, 2, 1, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-1, 2147483647L))).setMaxAccess('readwrite').setDescription('The Delay until the Receptacle is turned Off.  Setting \nthis value to other than -1 will cause the UPS output to \nturn off after the number of seconds (0 is immediately).  \nSetting it to -1 will cause an attempt to abort a pending shutdown.\nWhen this object is set while the UPS is On Battery, it is not necessary\nto set xupsRecepOnDelaySecs, since the outlet will turn back on \nautomatically when power is available again.')
xupsRecepOnDelaySecs = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 12, 2, 1, 4), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-1, 2147483647L))).setMaxAccess('readwrite').setDescription(' The Delay until the Receptacle is turned On.  Setting \nthis value to other than -1 will cause the UPS output to \nturn on after the number of seconds (0 is immediately).  \nSetting it to -1 will cause an attempt to abort a pending restart.')
xupsRecepAutoOffDelay = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 12, 2, 1, 5), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-1, 32767))).setMaxAccess('readwrite').setDescription('The delay after going On Battery until the Receptacle is \nautomatically turned Off.  A value of -1 means that this Output should \nnever be turned Off automatically, but must be turned Off only by command.\nValues from 0 to 30 are valid, but probably innappropriate.\nThe AutoOffDelay can be used to prioritize loads in the event of a prolonged \npower outage; less critical loads will turn off earlier to extend battery \ntime for the more critical loads. If the utility power is restored before the \nAutoOff delay counts down to 0 on an outlet, that outlet will not turn Off.')
xupsRecepAutoOnDelay = MibTableColumn((1, 3, 6, 1, 4, 1, 534, 1, 12, 2, 1, 6), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(-1, 32767))).setMaxAccess('readwrite').setDescription('Seconds delay after the Outlet is signaled to turn On before the Output is\nAutomatically turned ON. A value of -1 means that this Output should never\nbe turned On automatically, but only when specifically commanded to do so.\nA value of 0 means that the Receptacle should come On immediately\nat power-up or for an On command.')
xupsTopology = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 1, 13))
xupsTopologyType = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 13, 1), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 32767))).setMaxAccess('readonly').setDescription("Value which denotes the type of UPS by its power topology.  Values are the\nsame as those described in the XCP Topology block's Overall Topology field.")
xupsTopoMachineCode = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 13, 2), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 32767))).setMaxAccess('readonly').setDescription("ID Value which denotes the Powerware model of the UPS for software.  Values \nare the same as those described in the XCP Configuration block's Machine Code \nfield.")
xupsTopoUnitNumber = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 13, 3), Integer32().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 64))).setMaxAccess('readonly').setDescription("Identifies which unit and what type of data is being reported.\nA value of 0 means that this MIB information comes from the top-level system \nview (eg, manifold module or system bypass cabinet reporting total system \noutput).  Standalone units also use a value of 0, since they are the 'full \nsystem' view.\nA value of 1 or higher indicates the number of the module in the system\nwhich is reporting only its own data in the PowerMIB objects.")
xupsTopoPowerStrategy = MibScalar((1, 3, 6, 1, 4, 1, 534, 1, 13, 4), Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(3,1,4,2,)).subtype(namedValues=namedval.NamedValues(('highAlert', 1), ('standard', 2), ('enableHighEfficiency', 3), ('immediateHighEfficiency', 4), ))).setMaxAccess('readwrite').setDescription('Value which denotes which Power Strategy is currently set for the UPS.\nThe values are:\nhighAlert(1) - The UPS shall optimize its operating state to maximize its \n\t\tpower-protection levels.  This mode will be held for at most 24 hours.\nstandard(2) - Balanced, normal power protection strategy. UPS will not enter \n\t\tHE operating mode from this setting.\nenableHighEfficiency(3) - The UPS is enabled to enter HE operating mode to \n\t\toptimize its operating state to maximize its efficiency, when \n\t\tconditions change to permit it (as determined by the UPS).\nforceHighEfficiency(4) - If this value is permitted to be Set for this UPS,\n\t\tand if conditions permit, requires the UPS to enter High Efficiency \n\t\tmode now, without delay (for as long as utility conditions permit).\n\t\tAfter successfully set to forceHighEfficiency(4), \n\t\txupsTopoPowerStrategy changes to value enableHighEfficiency(3).\nxupsOutputSource will indicate if the UPS status is actually operating in \nHigh Efficiency mode.')
xupsObjectId = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2))
powerwareEthernetSnmpAdapter = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2, 1))
powerwareNetworkSnmpAdapterEther = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2, 2))
powerwareNetworkSnmpAdapterToken = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2, 3))
onlinetDaemon = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2, 4))
connectUPSAdapterEthernet = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2, 5))
powerwareNetworkDigitalIOEther = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2, 6))
connectUPSAdapterTokenRing = MibIdentifier((1, 3, 6, 1, 4, 1, 534, 2, 7))

# Augmentions

# Notifications

xupstbAlarmEntryAdded = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 21)).setObjects()
xupstdUtilityPowerRestored = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 5)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbUtilityPowerRestored = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 5)).setObjects()
xupstpBuildingAlarm = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 15)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpInverterFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 10)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdControlOff = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 1)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpInputFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 14)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdAlarmEntryAdded = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 21)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpOnBypass = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 11)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdCommunicationsLost = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 26)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbOutputOverload = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 7)).setObjects()
xupstbInternalFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 8)).setObjects()
xupstpOnBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 3)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpAmbientTempBad = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 29)).setObjects(('XUPS-MIB', 'xupsEnvAmbientLowerLimit'), ('XUPS-MIB', 'xupsAlarmDescr'), ('RFC1213-MIB', 'ifDescr'), ('RFC1213-MIB', 'ifIndex'), ('XUPS-MIB', 'xupsTrapMessage'), ('XUPS-MIB', 'xupsEnvAmbientUpperLimit'), ('XUPS-MIB', 'xupsEnvAmbientTemp'), ('XUPS-MIB', 'xupsAlarmID'), )
xupstdInverterFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 10)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdLowBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 4)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdAlarmEntryRemoved = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 22)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdShutdownImminent = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 16)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbBreakerOpen = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 20)).setObjects()
xupstbControlOff = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 1)).setObjects()
xupstdOnBypass = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 11)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdBuildingAlarm = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 15)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpOutputOff = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 13)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpReturnFromLowBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 6)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdAmbientTempBad = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 29)).setObjects(('XUPS-MIB', 'xupsEnvAmbientLowerLimit'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), ('XUPS-MIB', 'xupsEnvAmbientUpperLimit'), ('XUPS-MIB', 'xupsEnvAmbientTemp'), ('XUPS-MIB', 'xupsAlarmID'), )
xupstpLowBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 4)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpAlarmBatteryBad = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 23)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpOutputOffAsRequested = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 24)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdInputFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 14)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpControlOff = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 1)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpDiagnosticTestFailed = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 25)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpCommunicationsLost = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 26)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpControlOn = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 2)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdDiagnosticTestFailed = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 25)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdOutputOff = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 13)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbInputFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 14)).setObjects()
xupstpBypassNotAvailable = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 12)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdOnInverter = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 17)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbOnBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 3)).setObjects()
xupstdBatteryDischarged = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 9)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpBreakerOpen = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 20)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbBypassNotAvailable = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 12)).setObjects()
xupstdBypassNotAvailable = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 12)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpShutdownImminent = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 16)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdAlarmTestInProgress = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 28)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpAlarmEntryAdded = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 21)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbOnInverter = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 17)).setObjects()
xupstdUpsShutdownPending = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 27)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbAlarmEntryRemoved = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 22)).setObjects()
xupstbOnBypass = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 11)).setObjects()
xupstdAlarmBatteryBad = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 23)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbInverterFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 10)).setObjects()
xupstpUpsShutdownPending = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 27)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbBatteryDischarged = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 9)).setObjects()
xupstbReturnFromLowBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 6)).setObjects()
xupstpBatteryDischarged = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 9)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdOnBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 3)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbBuildingAlarm = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 15)).setObjects()
xupstpOutputOverload = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 7)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbOutputOff = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 13)).setObjects()
xupstpAlarmTestInProgress = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 28)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdOutputOverload = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 7)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpInternalFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 8)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpUtilityPowerRestored = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 5)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstpAlarmEntryRemoved = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 22)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdReturnFromLowBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 6)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbShutdownImminent = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 16)).setObjects()
xupstdOutputOffAsRequested = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 24)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbLowBattery = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 4)).setObjects()
xupstdInternalFailure = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 8)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdControlOn = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 2)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstbControlOn = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 0, 0, 0, 2)).setObjects()
xupstpOnInverter = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 2, 0, 17)).setObjects(('RFC1213-MIB', 'ifIndex'), ('RFC1213-MIB', 'ifDescr'), ('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )
xupstdBreakerOpen = NotificationType((1, 3, 6, 1, 4, 1, 534, 1, 11, 4, 1, 0, 20)).setObjects(('XUPS-MIB', 'xupsAlarmID'), ('XUPS-MIB', 'xupsAlarmDescr'), ('XUPS-MIB', 'xupsTrapMessage'), )

# Exports

# Objects
mibBuilder.exportSymbols('XUPS-MIB', powerware=powerware, xups=xups, xupsNull=xupsNull, xupsTrapBasic=xupsTrapBasic, xupsIdent=xupsIdent, xupsIdentManufacturer=xupsIdentManufacturer, xupsIdentModel=xupsIdentModel, xupsIdentSoftwareVersion=xupsIdentSoftwareVersion, xupsIdentOemCode=xupsIdentOemCode, xupsBattery=xupsBattery, xupsBatTimeRemaining=xupsBatTimeRemaining, xupsBatVoltage=xupsBatVoltage, xupsBatCurrent=xupsBatCurrent, xupsBatCapacity=xupsBatCapacity, xupsBatteryAbmStatus=xupsBatteryAbmStatus, xupsInput=xupsInput, xupsInputFrequency=xupsInputFrequency, xupsInputLineBads=xupsInputLineBads, xupsInputNumPhases=xupsInputNumPhases, xupsInputTable=xupsInputTable, xupsInputEntry=xupsInputEntry, xupsInputPhase=xupsInputPhase, xupsInputVoltage=xupsInputVoltage, xupsInputCurrent=xupsInputCurrent, xupsInputWatts=xupsInputWatts, xupsOutput=xupsOutput, xupsOutputLoad=xupsOutputLoad, xupsOutputFrequency=xupsOutputFrequency, xupsOutputNumPhases=xupsOutputNumPhases, xupsOutputTable=xupsOutputTable, xupsOutputEntry=xupsOutputEntry, xupsOutputPhase=xupsOutputPhase, xupsOutputVoltage=xupsOutputVoltage, xupsOutputCurrent=xupsOutputCurrent, xupsOutputWatts=xupsOutputWatts, xupsOutputSource=xupsOutputSource, xupsBypass=xupsBypass, xupsBypassFrequency=xupsBypassFrequency, xupsBypassNumPhases=xupsBypassNumPhases, xupsBypassTable=xupsBypassTable, xupsBypassEntry=xupsBypassEntry, xupsBypassPhase=xupsBypassPhase, xupsBypassVoltage=xupsBypassVoltage, xupsEnvironment=xupsEnvironment, xupsEnvAmbientTemp=xupsEnvAmbientTemp, xupsEnvAmbientLowerLimit=xupsEnvAmbientLowerLimit, xupsEnvAmbientUpperLimit=xupsEnvAmbientUpperLimit, xupsAlarm=xupsAlarm, xupsAlarms=xupsAlarms, xupsAlarmTable=xupsAlarmTable, xupsAlarmEntry=xupsAlarmEntry, xupsAlarmID=xupsAlarmID, xupsAlarmDescr=xupsAlarmDescr, xupsAlarmTime=xupsAlarmTime, xupsOnBattery=xupsOnBattery, xupsLowBattery=xupsLowBattery, xupsUtilityPowerRestored=xupsUtilityPowerRestored, xupsReturnFromLowBattery=xupsReturnFromLowBattery, xupsOutputOverload=xupsOutputOverload, xupsInternalFailure=xupsInternalFailure, xupsBatteryDischarged=xupsBatteryDischarged, xupsInverterFailure=xupsInverterFailure, xupsOnBypass=xupsOnBypass, xupsBypassNotAvailable=xupsBypassNotAvailable, xupsOutputOff=xupsOutputOff, xupsInputFailure=xupsInputFailure, xupsBuildingAlarm=xupsBuildingAlarm, xupsShutdownImminent=xupsShutdownImminent, xupsOnInverter=xupsOnInverter, xupsAlarmNumEvents=xupsAlarmNumEvents, xupsAlarmEventTable=xupsAlarmEventTable, xupsAlarmEventEntry=xupsAlarmEventEntry, xupsAlarmEventID=xupsAlarmEventID, xupsAlarmEventDateAndTime=xupsAlarmEventDateAndTime, xupsAlarmEventKind=xupsAlarmEventKind, xupsAlarmEventDescr=xupsAlarmEventDescr, xupsAlarmEventMsg=xupsAlarmEventMsg, xupsBreakerOpen=xupsBreakerOpen, xupsAlarmEntryAdded=xupsAlarmEntryAdded, xupsAlarmEntryRemoved=xupsAlarmEntryRemoved, xupsAlarmBatteryBad=xupsAlarmBatteryBad, xupsOutputOffAsRequested=xupsOutputOffAsRequested, xupsDiagnosticTestFailed=xupsDiagnosticTestFailed, xupsCommunicationsLost=xupsCommunicationsLost, xupsUpsShutdownPending=xupsUpsShutdownPending, xupsAlarmTestInProgress=xupsAlarmTestInProgress, xupsAmbientTempBad=xupsAmbientTempBad, xupsTest=xupsTest, xupsTestBattery=xupsTestBattery, xupsTestBatteryStatus=xupsTestBatteryStatus, xupsControl=xupsControl, xupsControlOutputOffDelay=xupsControlOutputOffDelay, xupsControlOutputOnDelay=xupsControlOutputOnDelay, xupsControlOutputOffTrapDelay=xupsControlOutputOffTrapDelay, xupsControlOutputOnTrapDelay=xupsControlOutputOnTrapDelay, xupsControlToBypassDelay=xupsControlToBypassDelay, xupsConfig=xupsConfig, xupsConfigOutputVoltage=xupsConfigOutputVoltage, xupsConfigInputVoltage=xupsConfigInputVoltage, xupsConfigOutputWatts=xupsConfigOutputWatts, xupsConfigOutputFreq=xupsConfigOutputFreq, xupsConfigDateAndTime=xupsConfigDateAndTime, xupsTrapControl=xupsTrapControl, xupsMaxTrapLevel=xupsMaxTrapLevel, xupsSendTrapType=xupsSendTrapType, xupsTrapMessage=xupsTrapMessage, xupsTrapSource=xupsTrapSource, xupsTrapDefined=xupsTrapDefined, xupsTrapPortN=xupsTrapPortN, xupsRecep=xupsRecep, xupsNumReceptacles=xupsNumReceptacles, xupsRecepTable=xupsRecepTable, xupsRecepEntry=xupsRecepEntry, xupsRecepIndex=xupsRecepIndex, xupsRecepStatus=xupsRecepStatus, xupsRecepOffDelaySecs=xupsRecepOffDelaySecs, xupsRecepOnDelaySecs=xupsRecepOnDelaySecs, xupsRecepAutoOffDelay=xupsRecepAutoOffDelay, xupsRecepAutoOnDelay=xupsRecepAutoOnDelay, xupsTopology=xupsTopology, xupsTopologyType=xupsTopologyType, xupsTopoMachineCode=xupsTopoMachineCode, xupsTopoUnitNumber=xupsTopoUnitNumber, xupsTopoPowerStrategy=xupsTopoPowerStrategy, xupsObjectId=xupsObjectId, powerwareEthernetSnmpAdapter=powerwareEthernetSnmpAdapter)
mibBuilder.exportSymbols('XUPS-MIB', powerwareNetworkSnmpAdapterEther=powerwareNetworkSnmpAdapterEther, powerwareNetworkSnmpAdapterToken=powerwareNetworkSnmpAdapterToken, onlinetDaemon=onlinetDaemon, connectUPSAdapterEthernet=connectUPSAdapterEthernet, powerwareNetworkDigitalIOEther=powerwareNetworkDigitalIOEther, connectUPSAdapterTokenRing=connectUPSAdapterTokenRing)

# Notifications
mibBuilder.exportSymbols('XUPS-MIB', xupstbAlarmEntryAdded=xupstbAlarmEntryAdded, xupstdUtilityPowerRestored=xupstdUtilityPowerRestored, xupstbUtilityPowerRestored=xupstbUtilityPowerRestored, xupstpBuildingAlarm=xupstpBuildingAlarm, xupstpInverterFailure=xupstpInverterFailure, xupstdControlOff=xupstdControlOff, xupstpInputFailure=xupstpInputFailure, xupstdAlarmEntryAdded=xupstdAlarmEntryAdded, xupstpOnBypass=xupstpOnBypass, xupstdCommunicationsLost=xupstdCommunicationsLost, xupstbOutputOverload=xupstbOutputOverload, xupstbInternalFailure=xupstbInternalFailure, xupstpOnBattery=xupstpOnBattery, xupstpAmbientTempBad=xupstpAmbientTempBad, xupstdInverterFailure=xupstdInverterFailure, xupstdLowBattery=xupstdLowBattery, xupstdAlarmEntryRemoved=xupstdAlarmEntryRemoved, xupstdShutdownImminent=xupstdShutdownImminent, xupstbBreakerOpen=xupstbBreakerOpen, xupstbControlOff=xupstbControlOff, xupstdOnBypass=xupstdOnBypass, xupstdBuildingAlarm=xupstdBuildingAlarm, xupstpOutputOff=xupstpOutputOff, xupstpReturnFromLowBattery=xupstpReturnFromLowBattery, xupstdAmbientTempBad=xupstdAmbientTempBad, xupstpLowBattery=xupstpLowBattery, xupstpAlarmBatteryBad=xupstpAlarmBatteryBad, xupstpOutputOffAsRequested=xupstpOutputOffAsRequested, xupstdInputFailure=xupstdInputFailure, xupstpControlOff=xupstpControlOff, xupstpDiagnosticTestFailed=xupstpDiagnosticTestFailed, xupstpCommunicationsLost=xupstpCommunicationsLost, xupstpControlOn=xupstpControlOn, xupstdDiagnosticTestFailed=xupstdDiagnosticTestFailed, xupstdOutputOff=xupstdOutputOff, xupstbInputFailure=xupstbInputFailure, xupstpBypassNotAvailable=xupstpBypassNotAvailable, xupstdOnInverter=xupstdOnInverter, xupstbOnBattery=xupstbOnBattery, xupstdBatteryDischarged=xupstdBatteryDischarged, xupstpBreakerOpen=xupstpBreakerOpen, xupstbBypassNotAvailable=xupstbBypassNotAvailable, xupstdBypassNotAvailable=xupstdBypassNotAvailable, xupstpShutdownImminent=xupstpShutdownImminent, xupstdAlarmTestInProgress=xupstdAlarmTestInProgress, xupstpAlarmEntryAdded=xupstpAlarmEntryAdded, xupstbOnInverter=xupstbOnInverter, xupstdUpsShutdownPending=xupstdUpsShutdownPending, xupstbAlarmEntryRemoved=xupstbAlarmEntryRemoved, xupstbOnBypass=xupstbOnBypass, xupstdAlarmBatteryBad=xupstdAlarmBatteryBad, xupstbInverterFailure=xupstbInverterFailure, xupstpUpsShutdownPending=xupstpUpsShutdownPending, xupstbBatteryDischarged=xupstbBatteryDischarged, xupstbReturnFromLowBattery=xupstbReturnFromLowBattery, xupstpBatteryDischarged=xupstpBatteryDischarged, xupstdOnBattery=xupstdOnBattery, xupstbBuildingAlarm=xupstbBuildingAlarm, xupstpOutputOverload=xupstpOutputOverload, xupstbOutputOff=xupstbOutputOff, xupstpAlarmTestInProgress=xupstpAlarmTestInProgress, xupstdOutputOverload=xupstdOutputOverload, xupstpInternalFailure=xupstpInternalFailure, xupstpUtilityPowerRestored=xupstpUtilityPowerRestored, xupstpAlarmEntryRemoved=xupstpAlarmEntryRemoved, xupstdReturnFromLowBattery=xupstdReturnFromLowBattery, xupstbShutdownImminent=xupstbShutdownImminent, xupstdOutputOffAsRequested=xupstdOutputOffAsRequested, xupstbLowBattery=xupstbLowBattery, xupstdInternalFailure=xupstdInternalFailure, xupstdControlOn=xupstdControlOn, xupstbControlOn=xupstbControlOn, xupstpOnInverter=xupstpOnInverter, xupstdBreakerOpen=xupstdBreakerOpen)

