"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
# LENEL-MIB:  MIB from lenel-2003.mib.
#
# ============================================================================
# Created manually using smidump and RZ's custom version of libsmi2pysnmp
# which was part of /home/mevans/source/pysnmp-experiments/ at the time of
# execution.  Essentially::
#   $ smidump -f smiv2 lenel-2003.mib >lenel.smidump.smiv2
#   $ smidump -f python lenel.smidump.smiv2 >lenel.smidump.py
#   $ cat lenel.smidump.py | ../libsmi2pysnmp >LENEL-MIB.py
#
# @note The MIB is named LENEL-MIB because that is the internal name in
#       lenel-2003.mib.
# --------------------------------------------------------------------------
# lenel-2003.mib:15: TRAP-TYPE macro is not allowed in SMIv2
# lenel-2003.mib:20: TRAP-TYPE macro is not allowed in SMIv2
# lenel-2003.mib:33: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:34: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:42: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:43: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:53: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:54: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:60: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:61: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:69: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:70: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:76: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:77: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:83: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:84: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:90: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:91: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:97: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:98: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:104: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:105: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:113: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:114: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:122: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:123: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:130: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:131: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:137: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:138: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:144: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:145: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:151: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:152: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:159: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:160: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:169: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:170: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:176: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:177: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:183: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:184: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:190: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:191: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:199: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:200: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:207: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:208: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:216: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:217: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:224: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:225: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:231: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:232: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:240: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:241: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:247: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:248: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:254: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:255: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:261: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:262: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:271: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:272: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:281: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:282: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:288: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:289: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:295: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:296: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:304: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:305: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:311: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:312: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:318: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:319: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:325: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:326: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:332: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:333: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:341: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:342: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:349: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:350: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:356: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:357: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:364: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:365: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:372: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:373: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:382: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:383: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:389: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:390: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:396: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:397: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:405: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:406: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:412: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:413: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:421: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:422: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:428: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:429: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:437: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:438: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:444: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:445: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:453: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:454: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:460: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:461: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:469: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:470: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:476: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:477: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:485: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:486: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:492: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:493: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:501: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:502: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:508: ACCESS is SMIv1 style, use MAX-ACCESS in SMIv2 MIBs instead
# lenel-2003.mib:509: invalid status `optional' in SMIv2 MIB
# lenel-2003.mib:513: missing MODULE-IDENTITY clause in SMIv2 MIB
# smidump: module `lenel-2003.mib' contains errors, expect flawed output
# lenel.smidump.smiv2:596: missing MODULE-IDENTITY clause in SMIv2 MIB
# smidump: module `lenel.smidump.smiv2' contains errors, expect flawed output
# ==========================================================================
# PySNMP SMI module. Autogenerated from smidump -f python LENEL-MIB
# by libsmi2pysnmp-0.0.7-alpha-rz2 at Wed Apr 23 11:48:42 2008,
# Python version (2, 2, 3, 'final', 0)

# Imported just in case new ASN.1 types would be created
from pyasn1.type import constraint, namedval

# Imports

( Integer, ObjectIdentifier, OctetString, ) = mibBuilder.importSymbols('ASN1', 'Integer', 'ObjectIdentifier', 'OctetString')
( Bits, Counter32, Counter64, Gauge32, Integer32, IpAddress, MibIdentifier, NotificationType, ObjectIdentity, MibScalar, MibTable, MibTableRow, MibTableColumn, Opaque, TimeTicks, Unsigned32, enterprises, ) = mibBuilder.importSymbols('SNMPv2-SMI', 'Bits', 'Counter32', 'Counter64', 'Gauge32', 'Integer32', 'IpAddress', 'MibIdentifier', 'NotificationType', 'ObjectIdentity', 'MibScalar', 'MibTable', 'MibTableRow', 'MibTableColumn', 'Opaque', 'TimeTicks', 'Unsigned32', 'enterprises')

# Objects

lenel = MibIdentifier((1, 3, 6, 1, 4, 1, 15714))
onGuard = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1))
event = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1))
unknownEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 1))
previousEventData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 1, 1), OctetString()).setMaxAccess('readonly').setDescription('Previous data from an unknown OnGuard event. This \nvariable contains the reported property and value in the\nfollowing format:\t<Property>: <Value>')
currentEventData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 1, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from an unknown OnGuard event. This variable\ncontains the reported property and value in the \nfollowing format:\t<Property>: <Value>')
hardwareEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2))
eventDescription = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 1), OctetString()).setMaxAccess('readonly').setDescription('A human readable, brief description of this event.')
datetime = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 2), OctetString()).setMaxAccess('readonly').setDescription('The time when this event occured.')
securityEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3))
serialNumber = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 1), Integer32()).setMaxAccess('readonly').setDescription('A number that uniquely identifies the instance of the event for a particular panel.')
panelID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 2), Integer32()).setMaxAccess('readonly').setDescription('The ID of the panel where this event originated.')
deviceID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 3), Integer32()).setMaxAccess('readonly').setDescription('The ID of the device where this event originated.')
secondaryDeviceID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 4), Integer32()).setMaxAccess('readonly').setDescription('The ID of the secondary device where this event originated.')
id = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 5), Integer32()).setMaxAccess('readonly').setDescription('The ID that uniquely identifies the type of this event.')
segmentID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 6), Integer32()).setMaxAccess('readonly').setDescription('The ID of the segment that the panel is in.')
accessEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7))
accessResult = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 1), Integer32()).setMaxAccess('readonly').setDescription("The level of access that was granted that resulted from reading \nthe card. Possible values include 'Other', 'Unknown', 'Granted',\n'Denied', and 'Not Applicable'.")
cardholderEntered = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 2), Integer32()).setMaxAccess('readonly').setDescription('Boolean value indicating whether entry was made by the \ncardholder.\tNon-zero value indicates true.')
cardNumber = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 3), Integer32()).setMaxAccess('readonly').setDescription('The badge ID for the card that was read, if available.')
issueCode = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 4), Integer32()).setMaxAccess('readonly').setDescription('The issue code for the card that was read, if available.')
facilityCode = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 5), Integer32()).setMaxAccess('readonly').setDescription('The facility code for the card that was read, if available.')
duress = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 6), Integer32()).setMaxAccess('readonly').setDescription('Boolean value indicating whether this card access indicates \nan under duress/emergenct state. Non-zero value indicates true.')
isReadableCard = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 7), Integer32()).setMaxAccess('readonly').setDescription('Boolean value indicating whether the card could be read. Non-zero\nvalue indicates true. If it could not be read (due to an invalid \ncard format or damage to the card), the other properties of this \nclass relating to the card information will be null.')
areaEnteredID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 8), Integer32()).setMaxAccess('readonly').setDescription('The ID of the area that was entered, if any.')
areaExitedID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 9), Integer32()).setMaxAccess('readonly').setDescription('The ID of the area that was exited, if any.')
floor = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 10), Integer32()).setMaxAccess('readonly').setDescription('The floor at which the card access event was generated, if any.')
assetID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 7, 11), OctetString()).setMaxAccess('readonly').setDescription('The ID of the asset related to this event, if any.')
intercomEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 8))
intercomData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 8, 1), Integer32()).setMaxAccess('readonly').setDescription('Intercom data associated with this event, such as the station \nID for the station that was called.')
lineNumber = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 8, 2), Integer32()).setMaxAccess('readonly').setDescription('Line number associated with this event')
videoEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 9))
channel = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 9, 1), Integer32()).setMaxAccess('readonly').setDescription('The physical channel the camera is connected to that is creating\nthis event.')
endTime = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 9, 2), OctetString()).setMaxAccess('readonly').setDescription('The time that the video event ended.')
startTime = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 9, 3), OctetString()).setMaxAccess('readonly').setDescription('The time that the video event started.')
transmitterEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 10))
transmitterID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 10, 1), Integer32()).setMaxAccess('readonly').setDescription('The ID of the transmitter that generated this event.')
transmitterBaseID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 10, 2), Integer32()).setMaxAccess('readonly').setDescription('The base ID of the transmitter that generated this event.')
transmitterInputID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 10, 3), Integer32()).setMaxAccess('readonly').setDescription('The ID associated with the transmitter input.')
verifiedAlarm = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 10, 4), Integer32()).setMaxAccess('readonly').setDescription('Boolean value indicating whether the transmitter message is known\nto be verified (R signal received by an RF receiver).')
fireEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 11))
troubleCode = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 11, 1), Integer32()).setMaxAccess('readonly').setDescription('Trouble code for this event. Set to -1 if there is no trouble\ncode associated with this event.')
statusChangeEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 12))
newStatus = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 12, 1), Integer32()).setMaxAccess('readonly').setDescription('New status of the device.')
oldStatus = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 12, 2), Integer32()).setMaxAccess('readonly').setDescription('Old status of the device.')
communicationsStatus = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 12, 3), Integer32()).setMaxAccess('readonly').setDescription('Communication status for device.')
functionExecEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 13))
functionID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 13, 1), Integer32()).setMaxAccess('readonly').setDescription('Function ID.')
functionInputArguments = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 13, 2), Integer32()).setMaxAccess('readonly').setDescription('Input arguments to the function.')
initiatingEventID = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 13, 3), Integer32()).setMaxAccess('readonly').setDescription('Event identifier that caused the function to be initiated.')
type = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 14), Integer32()).setMaxAccess('readonly').setDescription('The type identifier for the event.')
eventText = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 3, 15), OctetString()).setMaxAccess('readonly').setDescription('The event text associated with the event.')
alarm = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 4))
alarmDescription = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 4, 1), OctetString()).setMaxAccess('readonly').setDescription('A human readable brief description of the alarm associated\twith\nthe event.')
priority = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 4, 2), Integer32()).setMaxAccess('readonly').setDescription('The priority configured for the alarm associated with this event.')
mustAcknowledge = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 4, 3), Integer32()).setMaxAccess('readonly').setDescription('Boolean value indicating whether or not this alarm must be \nacknowledged. A value of 1 means the alarm must be Acknowledged.')
isActive = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 4, 4), Integer32()).setMaxAccess('readonly').setDescription('Boolean value that indicates if this is an active alarm. A value\nof 1 indicates that the alarm is active.')
eventParameterDescription = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 2, 4, 5), OctetString()).setMaxAccess('readonly').setDescription('A human readable brief description of the event parameter.')
softwareEvent = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3))
instanceCreation = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 1), OctetString()).setMaxAccess('readonly').setDescription('The specified object has just been created.')
instanceModification = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 2), OctetString()).setMaxAccess('readonly').setDescription('The specified object has just been modified.')
instanceDeletion = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 3), OctetString()).setMaxAccess('readonly').setDescription('The specified object has just been deleted.')
element = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4))
previousElementData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 1), OctetString()).setMaxAccess('readonly').setDescription('Data from a previous instance of a element.')
currentElementData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from the current instance of a element.')
person = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3))
previousPersonData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 1), OctetString()).setMaxAccess('readonly').setDescription('Data from a previous instance of a person.')
currentPersonData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from the current instance of a person.')
cardholder = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 3))
previousCardholderData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 3, 1), OctetString()).setMaxAccess('readonly').setDescription('Data from a previous instance of a cardholder.')
currentCardholderData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 3, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from the current instance of a cardholder.')
visitor = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 4))
previousVisitorData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 4, 1), OctetString()).setMaxAccess('readonly').setDescription('Data from a previous instance of a visitor.')
currentVisitorData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 3, 4, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from the current instance of a visitor.')
badge = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 4))
previousBadgeData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 4, 1), OctetString()).setMaxAccess('readonly').setDescription('Data from a previous instance of a badge.')
currentBadgeData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 4, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from the current instance of a badge.')
account = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 5))
previousAccountData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 5, 1), OctetString()).setMaxAccess('readonly').setDescription('Data from a previous instance of a account.')
currentAccountData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 5, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from the current instance of a account.')
multimediaObject = MibIdentifier((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 6))
previousMediaObjectData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 6, 1), OctetString()).setMaxAccess('readonly').setDescription('Data from a previous instance of a multimedia object.')
currentMediaObjectData = MibScalar((1, 3, 6, 1, 4, 1, 15714, 1, 1, 3, 4, 6, 2), OctetString()).setMaxAccess('readonly').setDescription('Data from the current instance of a multimedia object.')

# Augmentions

# Notifications

onGuardHardwareEvent = NotificationType((1, 3, 6, 1, 4, 1, 15714, 0, 1)).setObjects()
onGuardSoftwareEvent = NotificationType((1, 3, 6, 1, 4, 1, 15714, 0, 2)).setObjects()

# Exports

# Objects
mibBuilder.exportSymbols('LENEL-MIB', lenel=lenel, onGuard=onGuard, event=event, unknownEvent=unknownEvent, previousEventData=previousEventData, currentEventData=currentEventData, hardwareEvent=hardwareEvent, eventDescription=eventDescription, datetime=datetime, securityEvent=securityEvent, serialNumber=serialNumber, panelID=panelID, deviceID=deviceID, secondaryDeviceID=secondaryDeviceID, id=id, segmentID=segmentID, accessEvent=accessEvent, accessResult=accessResult, cardholderEntered=cardholderEntered, cardNumber=cardNumber, issueCode=issueCode, facilityCode=facilityCode, duress=duress, isReadableCard=isReadableCard, areaEnteredID=areaEnteredID, areaExitedID=areaExitedID, floor=floor, assetID=assetID, intercomEvent=intercomEvent, intercomData=intercomData, lineNumber=lineNumber, videoEvent=videoEvent, channel=channel, endTime=endTime, startTime=startTime, transmitterEvent=transmitterEvent, transmitterID=transmitterID, transmitterBaseID=transmitterBaseID, transmitterInputID=transmitterInputID, verifiedAlarm=verifiedAlarm, fireEvent=fireEvent, troubleCode=troubleCode, statusChangeEvent=statusChangeEvent, newStatus=newStatus, oldStatus=oldStatus, communicationsStatus=communicationsStatus, functionExecEvent=functionExecEvent, functionID=functionID, functionInputArguments=functionInputArguments, initiatingEventID=initiatingEventID, type=type, eventText=eventText, alarm=alarm, alarmDescription=alarmDescription, priority=priority, mustAcknowledge=mustAcknowledge, isActive=isActive, eventParameterDescription=eventParameterDescription, softwareEvent=softwareEvent, instanceCreation=instanceCreation, instanceModification=instanceModification, instanceDeletion=instanceDeletion, element=element, previousElementData=previousElementData, currentElementData=currentElementData, person=person, previousPersonData=previousPersonData, currentPersonData=currentPersonData, cardholder=cardholder, previousCardholderData=previousCardholderData, currentCardholderData=currentCardholderData, visitor=visitor, previousVisitorData=previousVisitorData, currentVisitorData=currentVisitorData, badge=badge, previousBadgeData=previousBadgeData, currentBadgeData=currentBadgeData, account=account, previousAccountData=previousAccountData, currentAccountData=currentAccountData, multimediaObject=multimediaObject, previousMediaObjectData=previousMediaObjectData, currentMediaObjectData=currentMediaObjectData)

# Notifications
mibBuilder.exportSymbols('LENEL-MIB', onGuardHardwareEvent=onGuardHardwareEvent, onGuardSoftwareEvent=onGuardSoftwareEvent)

