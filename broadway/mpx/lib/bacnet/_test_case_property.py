"""
Copyright (C) 2002 2003 2006 2010 2011 Cisco Systems

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
# Test cases to exercise the property classes.
#

from mpx_test import DefaultTestFixture, main

import struct
import time
import array
import types

from mpx.lib.exceptions import EOverflow
from mpx.lib.exceptions import EInvalidValue

from mpx.lib import pause, msglog
from mpx.lib.bacnet import property, data, tag

from mpx.lib.bacnet._exceptions import *

from mpx.lib.bacnet import sequence, tag, data
from mpx.lib.bacnet import _data as data2

class TestCase(DefaultTestFixture):
    def test_BACnetCharacterString(self):
        try:
            a = property.BACnetCharacterString()
            a.as_tags()
        except:
            self.fail(
                'Failed to detect encode with None data object'
                )
        a = property.BACnetCharacterString('test')
        try:
            t = a.as_tags()
            if t[0].encoding != 'u\x05\x00test':
                self.fail(
                    'BACnetCharacterString failed to encode properly'
                    )
        except:
            self.fail(
                'BACnetCharacterString failed to encode'
                )
        try:
            a = property.BACnetCharacterString(decode=t)
            if a.value != 'test':
                self.fail(
                    'BACnetCharacterString failed to decode TAGS properly'
                    )
        except:
            self.fail(
                'BACnetCharacterString failed to decode TAGS properly'
                )
        try:
            a = property.BACnetCharacterString(decode=t[0].encoding)
            if a.value != 'test':
                self.fail(
                    'BACnetCharacterString failed to decode from STRING'
                    ' properly'
                    )
        except:
            self.fail(
                'BACnetCharacterString failed to decode STRING properly'
                )
            
        pass
    def test_BACnetEngineeringUnits(self):
        try:
            a = property.BACnetEngineeringUnits()
            a.as_tags()
        except:
            self.fail(
                'Failed to detect encode with None data object during get_tags'
                )
        try:
            a = property.BACnetEngineeringUnits(555)
        except EInvalidValue:
            pass
        else:
            self.fail(
                'Failed to detect bad data upon creation'
                )
        try:
            a = property.BACnetEngineeringUnits()
            a.value = 555
        except EInvalidValue:
            pass
        else:
            self.fail(
                'Failed to detect bad data assigment'
                )
        try:
            a = property.BACnetEngineeringUnits()
            a.value = -1
        except EInvalidValue:
            pass
        else:
            self.fail(
                'Failed to detect negative value assigment'
                )
        a = property.BACnetEngineeringUnits()
        a.value = 55
        t = a.as_tags()
        if t[0].encoding != '\x917':
            self.fail(
                'Failed to encode properly'
                )
        a.value = 0
        a.decode_from_string('\x91!')
        if a.value != 33:
            self.fail(
                'Failed to decode string properly'
                )
        if str(a) != 'feet':
            self.fail(
                'Failed to __str__ properly'
                )
        if type(float(a)) != types.FloatType:
            self.fail(
                'Failed to "float"'
                )
        if float(a) != 33.0:
            self.fail(
                'Float conversion failed'
                )
        if type(int(a)) != types.IntType:
            self.fail(
                'Failed to "Int"'
                )
        if int(a) != 33:
            self.fail(
                'Int comversion failed'
                )
        
        pass
    #def test_BACnetAction(self):
        #pass
    #def test_BACnetObjectType(self):
        #pass
    #def test_BACnetDeviceStatus(self):
        #pass
    #def test_BACnetSegmentation(self):
        #pass
    #def test_BACnetVTClass(self):
        #pass
    #def test_BACnetEventState(self):
        #pass
    #def test_BACnetEventType(self):
        #pass
    #def test_BACnetFileAccessMethod(self):
        #pass
    #def test_BACnetLifeSafetyMode(self):
        #pass
    #def test_BACnetLifeSafetyOperation(self):
        #pass
    #def test_BACnetLifeSafetyState(self):
        #pass
    #def test_BACnetMaintenance(self):
        #pass
    #def test_BACnetSilencedState(self):
        #pass
    #def test_BACnetNotifyType(self):
        #pass
    #def test_BACnetPolarity(self):
        #pass
    #def test_BACnetProgramRequest(self):
        #pass
    #def test_BACnetProgramState(self):
        #pass
    #def test_BACnetProgramError(self):
        #pass
    #def test_BACnetReliability(self):
        #pass
    #def test_BACnetBinaryPV(self):
        #pass
    def test_BACnetPropertyIdentifier(self):
        p=property.BACnetPropertyIdentifier(85)
        t=p.as_tags()
        #print p, t
    #def test_BACnetEventTransitionBits(self):
        #pass
    #def test_BACnetDaysOfWeek(self):
        #pass
    #def test_BACnetStatusFlags(self):
        #pass
    #def test_BACnetServicesSupported(self):
        #pass
    #def test_BACnetResultsFlags(self):
        #pass
    #def test_BACnetLimitEnable(self):
        #pass
    #def test_BACnetLogStatus(self):
        #pass
    #def test_BACnetObjectTypesSupported(self):
        #pass
    #def test_BACnetActionCommand(self):
        #pass
    #def test_BACnetAddressBinding(self):
        #pass
    #def test_BACnetActionList(self):
        #pass
    #def test_BACnetSpecialEvent(self):
        #pass
    #def test_BACnetVTSession(self):
        #pass
    #def test_BACnetDailySchedule(self):
        #pass
    #def test_BACnetAddress(self):
        #pass
    #def test_BACnetLimitEnable(self):
        #pass
    #def test_BACnetEventParameters(self):
        #pass
    #def test_BACnetRecipient(self):
        #pass
    #def test_BACnetDestination(self):
        #pass
    #def test_BACnetSetpointReference(self):
        #pass
    #def test_BACnetReadAccessSpecification(self):
        #pass
    #def test_BACnetSessionKey(self):
        #pass
    #def test_BACnetPriorityArray(self):
        #pass
    #def test_BACnetARRAY(self):
        #pass
    #def test_BACnetUnsigned(self):
        #pass
    #def test_BACnetInteger(self):
        #pass
    #def test_BACnetBoolean(self):
        #pass
    #def test_BACnetReal(self):
        #pass
    #def test_BACnetClientCOV(self):
        #pass
    #def test_BACnetTimeStamp(self):
        #pass
    #def test_BACnetLogRecord(self):
        #pass
    #def test_BACnetDeviceObjectPropertyReference(self):
        #pass
    #def test_BACnetCOVSubscription(self):
        #pass
    #def test_BACnetDeviceObjectReference(self):
        #pass
    def test_BACnetObjectPropertyReference(self):
        i=property.BACnetObjectIdentifier(3,6)
        p=property.BACnetPropertyIdentifier(85)
        r=property.BACnetObjectPropertyReference(i,p)
        rt=r.as_tags()
        #print r, rt
    #def test_BACnetDateRange(self):
        #pass
    #def test_BACnetError(self):
        #pass
    #def test_WritePropertyRequest(self):
        #pass
    def test_BACnetDate(self):
        s=property.BACnetDate(1987, 6, 5)
        t=s.as_tags()
        if str(s) != '06/05/87':
            self.fail(
                'Failed to Str date properly'
                )
        x = property.BACnetDate(decode=t)
        if str(x) != '06/05/87':
            self.fail(
                'Failed to decode date properly'
                )
        n = 1028154232.6032749
        s=property.BACnetDate(n)
        if str(s) != '07/31/02':
            self.fail(
                'Failed to create BACnetDate from Float'
                )
        t=s.as_tags()
        x = property.BACnetDate(decode=t)
        if str(x) != '07/31/02':
            self.fail(
                'Failed to decode floated date properly'
                )
        s=property.BACnetDate(time.localtime(n))
        if str(s) != '07/31/02':
            self.fail(
                'Failed to create BACnetDate from Tuple'
                )
        t=s.as_tags()
        x = property.BACnetDate(decode=t)
        if str(x) != '07/31/02':
            self.fail(
                'Failed to decode Tuple date properly'
                )
        if s.year != 2002:
            self.fail(
                'Failed to produce year'
                )
        if s.month != 7:
            self.fail(
                'Failed to produce month'
                )
        if s.day != 31:
            self.fail(
                'Failed to produce day'
                )
        s.year = 2001
        s.day = 30
        s.month = 6
        t=s.as_tags()
        x = property.BACnetDate(decode=t)
        if str(x) != '06/30/01':
            self.fail(
                'Failed to decode assigned date properly: %s' % str(x)
                )
        
        #print s,t
        pass
    def test_BACnetTime(self):
        pass
    def test_BACnetDateTime(self):
        p=property.BACnetDateTime(2002,6,18,13,30,0,0)
        t=p.as_tags()
        pass
    def test_BACnetDateRange(self):
        s=property.BACnetDate(2001, 6, 18)
        e=property.BACnetDate(2002, 6, 24)
        a=property.BACnetDateRange(s,e)
        b=a.as_tags()
        #print a, b
    def test_BACnetWeekNDay(self):
        pass
    def test_BACnetCalendarEntry(self):
        s=property.BACnetDate(2001, 6, 18)
        e=property.BACnetDate(2002, 6, 24)
        a=property.BACnetDateRange(s,e)
        c=property.BACnetCalendarEntry(date_range=a)
        d=c.as_tags()
        #print c, d
        pass
    def test_BACnetObjectIdentifier(self):
        i=property.BACnetObjectIdentifier(3,6)
        t=i.as_tags()
        #print i, t
        pass
    #def test_BACnetPropertyAction(self):
        #pass
    #def test_BACnetPropertyActionText(self):
        #pass
    #def test_BACnetPropertyAckedTransitions(self):
        #pass
    #def test_BACnetPropertyActiveText(self):
        #pass
    #def test_BACnetPropertyActiveVtSessions(self):
        #pass
    #def test_BACnetPropertyAlarmValue(self):
        #pass
    #def test_BACnetPropertyAlarmValues(self):
        #pass
    #def test_BACnetPropertyApduSegmentTimeout(self):
        #pass
    #def test_BACnetPropertyApduTimeout(self):
        #pass
    #def test_BACnetPropertyApplicationSoftwareVersion(self):
        #pass
    #def test_BACnetPropertyChangeOfStateCount(self):
        #pass
    #def test_BACnetPropertyChangeOfStateTime(self):
        #pass
    #def test_BACnetPropertyNotificationClass(self):
        #pass
    #def test_BACnetPropertyCovIncrement(self):
        #pass
    #def test_BACnetPropertyDateList(self):
        #pass
    #def test_BACnetPropertyDaylightSavingsStatus(self):
        #pass
    #def test_BACnetPropertyDeadband(self):
        #pass
    #def test_BACnetPropertyDescription(self):
        #pass
    #def test_BACnetPropertyDeviceAddressBinding(self):
        #pass
    #def test_BACnetPropertyDeviceType(self):
        #pass
    #def test_BACnetPropertyElapsedActiveTime(self):
        #pass
    #def test_BACnetPropertyEventEnable(self):
        #pass
    #def test_BACnetPropertyEventState(self):
        #pass
    #def test_BACnetPropertyExceptionSchedule(self):
        #pass
    #def test_BACnetPropertyFaultValues(self):
        #pass
    #def test_BACnetPropertyFeedbackValue(self):
        #pass
    #def test_BACnetPropertyFirmwareVersion(self):
        #pass
    #def test_BACnetPropertyHighLimit(self):
        #pass
    #def test_BACnetPropertyInactiveText(self):
        #pass
    #def test_BACnetPropertyLimitEnable(self):
        #pass
    #def test_BACnetPropertyListOfSessionKeys(self):
        #pass
    #def test_BACnetPropertyListOfGroupMembers(self):
        #pass
    #def test_BACnetPropertyListOfObjectPropertyReferences(self):
        #pass
    #def test_BACnetPropertyListOfSessionKeys(self):
        #pass
    #def test_BACnetPropertyLocalDate(self):
        #pass
    #def test_BACnetPropertyLocalTime(self):
        #pass
    #def test_BACnetPropertyLocation(self):
        #pass
    #def test_BACnetPropertyLowLimit(self):
        #pass
    #def test_BACnetPropertyMaxAPDULengthSupported(self):
        #pass
    #def test_BACnetPropertyMaxPresValue(self):
        #pass
    #def test_BACnetPropertyMinPresValue(self):
        #pass
    #def test_BACnetPropertyModelName(self):
        #pass
    #def test_BACnetPropertyNotifyType(self):
        #pass
    #def test_BACnetPropertyNumberOfApduRetries(self):
        #pass
    #def test_BACnetPropertyObjectIdentifier(self):
        #pass
    #def test_BACnetPropertyObjectList(self):
        #pass
    #def test_BACnetPropertyObjectName(self):
        #pass
    #def test_BACnetPropertyObjectPropertyReference(self):
        #pass
    #def test_BACnetPropertyObjectType(self):
        #pass
    #def test_BACnetPropertyOutOfService(self):
        #pass
    #def test_BACnetPropertyPolarity(self):
        #pass
    #def test_BACnetPropertyPresentValue(self):
        #pass
    #def test_BACnetPropertyPriority(self):
        #pass
    #def test_BACnetPropertyPriorityArray(self):
        #pass
    #def test_BACnetPropertyProtocolConformanceClass(self):
        #pass
    #def test_BACnetPropertyProtocolObjectTypesSupported(self):
        #pass
    #def test_BACnetPropertyProtocolServicesSupported(self):
        #pass
    #def test_BACnetPropertyProtocolVersion(self):
        #pass
    #def test_BACnetPropertyRecipient(self):
        #pass
    #def test_BACnetPropertyRecipientList(self):
        #pass
    #def test_BACnetPropertyReliability(self):
        #pass
    #def test_BACnetPropertyResolution(self):
        #pass
    #def test_BACnetPropertySegmentationSupported(self):
        #pass
    #def test_BACnetPropertyStatusFlags(self):
        #pass
    #def test_BACnetPropertySystemStatus(self):
        #pass
    #def test_BACnetPropertyTimeDelay(self):
        #pass
    #def test_BACnetPropertyTimeOfActiveTimeReset(self):
        #pass
    #def test_BACnetPropertyTimeOfStateCountReset(self):
        #pass
    #def test_BACnetPropertyTimeSynchronizationRecipients(self):
        #pass
    #def test_BACnetPropertyUnits(self):
        #pass
    #def test_BACnetPropertyUpdateInterval(self):
        #pass
    #def test_BACnetPropertyUtcOffset(self):
        #pass
    #def test_BACnetPropertyVendorIdentifier(self):
        #pass
    #def test_BACnetPropertyVendorName(self):
        #pass
    #def test_BACnetPropertyVtClassesSupported(self):
        #pass
    #def test_BACnetPropertyWeeklySchedule(self):
        #pass
       

#device_identifier=BACnetObjectIdentifier(8,1)
#object_identifier=BACnetObjectIdentifier(4,2)
#property_identifier=BACnetPropertyIdentifier(85)
#property_array_index=None
#property_value=BACnetBinaryPV(1)
#priority=None
#post_delay=None
#quit_on_failure=1
#write_successful=1

#ac = BACnetActionCommand(device_identifier, object_identifier, property_identifier,\
                 #property_array_index, property_value, priority, post_delay, \
                 #quit_on_failure, write_successful)
#act = ac.as_tags()
#print act
#for i in act:
    #s = []
    #for y in i.encoding:
        #s.append(hex(ord(y)))
    #print s

#property_value=BACnetBinaryPV(0)
#ac2 = BACnetActionCommand(device_identifier, object_identifier, property_identifier,\
                 #property_array_index, property_value, priority, post_delay, \
                 #quit_on_failure, write_successful)
#acl = [ac, ac2]
#bal = BACnetActionList(acl)
#balt = bal.as_tags()
#print balt
#t=[]
#for i in balt:
    #s = []
    #for y in i.encoding:
        #s.append(hex(ord(y)))
        #t.extend(y)
    #print s

##t=tag.decode(t)

#ba = BACnetAddress(1, [1,2,3,4])
#bat = ba.as_tags()
#for i in bat:
    #print i.encoding

#bab = BACnetAddressBinding(object_identifier, ba)
#babt = bab.as_tags()
#print babt
#for i in babt:
    #print i.encoding
#p = BACnetEngineeringUnits(1,0,1)
#p.value = 1
#p1 = p.object_identifier
#print p1
#p2 = p.write_property_request()
#print p2
#p3 = p2.encoding
#print p3

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
