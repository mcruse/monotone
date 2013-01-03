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
import urllib
import M2Crypto
from xml.dom.minidom import parse, parseString
import string
import os
import time
from mpx.service.network.openadr import  OperationMode
from mpx.service.network.openadr import  EventStatus
from mpx.lib.exceptions import ETimeout, EInvalidResponse,  MpxException, EInvalidMessage

def clearEventStates(eventStates):
    pass 

#Parse DRAS EventState and update the eventStates of DRAS client
def parseDrasRESTful(drClient):
    try:
        es = parse(drClient.local_file_path)
    except:
        raise EInvalidResponse('Invlid XML File')

    res = True
    root = es.documentElement
    dr_status = None
    dr_mode = None
    dr_time = None
    dr_schedule = None
    dr_notification_time = None
    dr_start_time = None
    dr_end_time = None
    if len(root.childNodes):
        drClient.reinit_event_variables()
        for rootchild in root.childNodes:
            if rootchild.nodeName == 'p:eventStates':
                #Walk through the eventStates attributes update if a matching 
                #attribute is found
                for attr in drClient.eventStates['eventStatesAttr']:
                    if rootchild.hasAttribute(attr):
                        #Represent testEvent as number 
                        if attr == 'testEvent':
                            if str(rootchild.getAttribute(attr)) == 'True':
                                drClient.eventStates['eventStatesAttr'][attr] = 1
                            else:
                                drClient.eventStates['eventStatesAttr'][attr] = 0
                        else:
                            drClient.eventStates['eventStatesAttr'][attr] = str(rootchild.getAttribute(attr))
                # Retrieve eventStates attributes here
                for eventStateschild in rootchild.childNodes:
                    if eventStateschild.nodeName == 'p:simpleDRModeData':
                        for simplechild in eventStateschild.childNodes:
                            # Get the DR event status
                            if simplechild.nodeName == 'p:EventStatus':
                                if simplechild.hasChildNodes():
                                    vchild = simplechild.firstChild
                                    if vchild.nodeType == vchild.TEXT_NODE:
                                        #Get the proper mapping form the EventStatus since the 
                                        #perfecthost only understand numbers 
                                        if EventStatus.has_key(str(vchild.nodeValue)):
                                            drClient.eventStates['EventStatus'] = EventStatus[str(vchild.nodeValue)]
                                        else:
                                            drClient.eventStates['EventStatus'] = None               
                            # Get the DR event status
                            if simplechild.nodeName == 'p:OperationModeValue':
                                if simplechild.hasChildNodes():
                                    vchild = simplechild.firstChild
                                    if vchild.nodeType == vchild.TEXT_NODE:
                                        #Get the proper mapping form the OperationMode  since the 
                                        #perfecthost only understand numbers 
                                        if OperationMode.has_key(str(vchild.nodeValue)):
                                            drClient.eventStates['OperationModeValue'] = OperationMode[str(vchild.nodeValue)]
                                        else:
                                            drClient.eventStates['OperationModeValue'] = None
                            # Get the DR event status
                            if simplechild.nodeName == 'p:currentTime':
                                if simplechild.hasChildNodes():
                                    vchild = simplechild.firstChild
                                    if vchild.nodeType == vchild.TEXT_NODE:
                                        drClient.eventStates['currentTime'] = float(vchild.nodeValue)
                            #Get ResponseSchedule
                            if simplechild.nodeName == 'p:operationModeSchedule':
                                for modeSlots in simplechild.childNodes:
                                    if modeSlots.nodeName == 'p:modeSlot':
                                        for simpleModeSlot in modeSlots.childNodes:
                                            if simpleModeSlot.nodeName == 'p:OperationModeValue':
                                                if simpleModeSlot.hasChildNodes():
                                                    vchild = simpleModeSlot.firstChild
                                                    if vchild.nodeType == vchild.TEXT_NODE:
                                                        if OperationMode.has_key(str(vchild.nodeValue)):
                                                            drClient.eventStates['ModeSlot']['OperationModeValue'].append(OperationMode[str(vchild.nodeValue)])
                                                        else:
                                                            drClient.eventStates['ModeSlot']['OperationModeValue'].append(None)
                                                                    
                                            if simpleModeSlot.nodeName == 'p:modeTimeSlot':
                                                if simpleModeSlot.hasChildNodes():
                                                    vchild = simpleModeSlot.firstChild
                                                    if vchild.nodeType == vchild.TEXT_NODE:
                                                        drClient.eventStates['ModeSlot']['modeTimeSlot'].append(int(vchild.nodeValue))
                            #Get ResponseSchedule
                    if eventStateschild.nodeName == 'p:drEventData':
                                for drEventData in eventStateschild.childNodes:
                                    # Get the DR event status
                                    if drEventData.nodeName == 'p:notificationTime':
                                        if drEventData.hasChildNodes():
                                            vchild = drEventData.firstChild
                                            if vchild.nodeType == vchild.TEXT_NODE:
                                                drClient.eventStates['drEventData']['notificationTime'] = str(vchild.nodeValue)
                                    # Get the DR event status
                                    if drEventData.nodeName == 'p:startTime':
                                        if drEventData.hasChildNodes():
                                            vchild = drEventData.firstChild
                                            if vchild.nodeType == vchild.TEXT_NODE:
                                                drClient.eventStates['drEventData']['startTime'] = str(vchild.nodeValue)
                                    # Get the DR event status
                                    if drEventData.nodeName == 'p:endTime':
                                        if drEventData.hasChildNodes():
                                            vchild = drEventData.firstChild
                                            if vchild.nodeType == vchild.TEXT_NODE:
                                                drClient.eventStates['drEventData']['endTime'] = str(vchild.nodeValue)

    else:
        raise EInvalidResponse('Couldnt find any EventStateinfo')
    return res     
