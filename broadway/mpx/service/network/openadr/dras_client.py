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
import time
import os
import types
import sys
import urllib
import base64

from datetime import datetime

from mpx import properties
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import CompositeNode, as_node
from mpx.lib import msglog
from mpx.lib import EnumeratedDictionary 
from mpx.lib.msglog.types import INFO, WARN, ERR
from mpx.lib.configure import REQUIRED
from mpx.lib.threading import Lock
from mpx.lib.scheduler import scheduler
from mpx.lib import httplib

from mpx.service.network.openadr import  OperationMode
from mpx.service.network.openadr import  EventStatus
from mpx.lib.exceptions import ETimeout, EInvalidResponse,  MpxException, EInvalidMessage, \
    EInvalidXML, EConnectionError ,EFileNotFound,EAlreadyRunning, ENotRunning

#Parser for the xml file
from mpx.service.network.openadr.dras_parser import  parseDrasRESTful

class openADRService(CompositeNode):
    """Place holder for  openADR Service , Handles generic attribute like debug, enable common to all dras clients"""
    def __init__(self):
        super(openADRService, self).__init__()

    def configure(self, config):  
        super(openADRService, self).configure(config)
        if self.debug:
            msglog.log('openADR', msglog.types.INFO, "In Configure Debug:%d Enabled:%d" 
                        % (self.debug,self.enabled))
            
    def configuration(self):
        config = super(openADRService, self).configuration()
        get_attribute(self, 'debug', config)
        get_attribute(self, 'enabled', config)
        return config

    def start(self):
        if self.is_running():
            raise EAlreadyRunning()

        if not  self.is_enabled():
            raise ENotEnabled('DRAS Service Not Enabled')

        super(openADRService,self).start()
        if self.debug:
            msglog.log('openADR', msglog.types.INFO, "Starting OpenADR Service")

    def stop(self):
        if not self.is_running():
            raise ENotRunning()
        super(openADRService, self).stop()

class openADRClient(CompositeNode):
    """ Place holder for openADR client .
        The client is responsible for polling the server for  DR Status 
        and represent it in nodebrowser """
        
    def __init__(self):
        self.lock = Lock()
        self.server_url = ''
        self.debug = 0
        self.enabled=0
        self.currentTime = 0.0
        self.eventDuration = 0.0
        self.Error = None
        self.waitTimeout = 4
        #For Response schedule 
        self.response_scheduler_id = None
        #For periodic poll of events
        self.poll_id = None
        #
        #The State vaiables for modetimeslot updation
        #
        self.updateNextState = False
        self.nextOperationModeValue= None
        self.nextEventStatus = None
        #Initialize EventState Variables
        self.eventStates = { 'eventStatesAttr':{'offLine':None,'testEvent':None,'drasName':None,
            'schemaVersion':None,'eventStateID':None,'drasClientID':None,
            'eventIdentifier':None,'eventModNumber':None,'programName':None},
            'EventStatus':None, 'OperationModeValue':None,'currentTime':None,
            #Indexed operation mode value and modetime slot     
            'ModeSlot':{'OperationModeValue':[],'modeTimeSlot':[]},
            'drEventData':{'notificationTime':None,'startTime':None,'endTime':None}
        }
        super(openADRClient, self).__init__()

    def configure(self,config):
        super(openADRClient, self).configure(config)
        set_attribute(self, 'serverip', REQUIRED, config, str)
        set_attribute(self, 'username', REQUIRED, config, str)
        set_attribute(self, 'password', REQUIRED, config, str)
        set_attribute(self, 'portnumber', 8443, config, int)
        set_attribute(self, 'filepath', REQUIRED, config, str)
        set_attribute(self, 'pollperiod', 300, config,float)
        self.enabled = self.parent.enabled
        self.debug = self.parent.debug
    
    def configuration(self):
        config = super(openADRClient, self).configuration()
        get_attribute(self, 'serverip', config)
        get_attribute(self, 'username', config)
        get_attribute(self, 'portnumber', config)
        get_attribute(self, 'filepath', config)
        get_attribute(self, 'pollperiod', config)
        get_attribute(self,'enabled',config)
        get_attribute(self,'debug',config)
        return config
    
    def start(self):      
        """Schedules the poll which would pull the eventstates  from the server """
        if self.is_running():
            raise EAlreadyRunning()
        if not  self.is_enabled():
            raise ENotEnabled('DRAS Service Not Enabled')
        #set timeout based on the polling period
        #If poll period is greater than 60 set to 30sec 
        #else to 4 
        if self.pollperiod >= 60:
            self.waitTimeout = 30            
        else:
           self.waitTimeout = 4
        #Path to store the config file 
        #Or should it be kept in ram to save some flash life ??
        self.local_file_path = '/tmp/' + self.name + '.adr'
        self.eventstates_path = '/' + self.filepath
        #Event Confirmation path
        self.confirm_event_path = '/' + 'RestClientWS/restConfirm'
        #Fill the header with username and password for authentication
        base64string = base64.encodestring('%s:%s' % (self.username, self.password) ) 
        authString = 'Basic %s' % base64string 
        self.headers = {"AUTHORIZATION" : authString}
        if self.debug:
            msglog.log('openADR', msglog.types.INFO,"The url file for eventstate:%s confirm_event:%s " %(self.eventstates_path,self.confirm_event_path))
        self.parse = parseDrasRESTful
        if self.debug:
            msglog.log('OpenADR',msglog.types.INFO,"Scheduling the Poll") 
        self.poll_id = scheduler.after(5,self.dras_poll) 
        super(openADRClient, self).start()

    def stop(self):
        if not self.is_running():
            raise ENotRunning()
        #cancel all scheduled events 
        if self.poll_id != None:
            scheduler.cancel(self.poll_id)
        if self.response_scheduler_id != None:
            scheduler.cancel(self.response_scheduler_id)
        super(openADRClient, self).stop()

    def reinit_event_variables(self):
        """Clear all the state variables """
        self.currentTime = 0.0
        self.eventDuration = 0.0
        self.updateNextState = False
        self.nextOperationModeValue= None
        self.nextEventStatus = None
        self.eventStates['ModeSlot']['OperationModeValue'] = []
        self.eventStates['ModeSlot']['modeTimeSlot'] = []
        self.eventStates['drEventData']['notificationTime'] = None
        self.eventStates['drEventData']['startTime'] = None
        self.eventStates['drEventData']['endTime'] = None
        #cancel any schedules to avoid any raise conditions
        if self.response_scheduler_id != None:
            scheduler.cancel(self.response_scheduler_id)

    def calculate_event_duration(self):
        """Calculate duration of event from startTime and EndTime"""
        if  (self.eventStates['drEventData']['startTime'] != None) and (self.eventStates['drEventData']['endTime'] != None): 
            try:
                starttime =  datetime.strptime(self.eventStates['drEventData']['startTime'].split('.')[0],"%Y-%m-%dT%H:%M:%S") 
                endtime =  datetime.strptime(self.eventStates['drEventData']['endTime'].split('.')[0],"%Y-%m-%dT%H:%M:%S") 
                td = endtime - starttime
                self.eventDuration = td.seconds + td.days *  24 * 3600
                if self.debug:
                    msglog.log('openADR', msglog.types.INFO, "Event Duration %d" % (self.eventDuration))
                
            except Exception,e:
                msglog.exception("Error in parsing time %s" %e)
                raise Exception('Invalid Time information')

    def confirm_event(self):
        """ Confirms the event reception to the sever"""
        res = True
        connection = httplib.HTTPSConnection(self.serverip,self.portnumber,self.waitTimeout)
        try:
            connection.request('GET', self.confirm_event_path,None, self.headers)
            response = connection.getresponse()
            self.confirmEventStaus  = response.read()
            if self.debug:
                msglog.log('openADR', msglog.types.INFO, "Confirm Status %s" % (self.confirmEventStaus))
        except ETimeout:
            msglog.log('OpenADR',msglog.type.ERR,"Timeout on ConfirmEvent")
            res = ETimeout()        
        except Exception,e:
            msglog.exception("Error in loading confirm status file %s" %e)
            
        finally:
            connection.close()
        return res

    def get_eventState(self):
        """Loads xml file from server and save to a local file"""
        connection = httplib.HTTPSConnection(self.serverip,self.portnumber,self.waitTimeout)
        localFileHandle = open(self.local_file_path,'w')
        status = None
        try:
            connection.request('GET', self.eventstates_path,None, self.headers)
            response = connection.getresponse()
            eventStateData  = response.read()
            if self.debug:
                msglog.log('openADR', msglog.types.INFO, 'Response Code:%s ' % (response.status))
            if response.status >= 400:
                error = 'Request returned error code %s, reason "%s"'
                error = error % (response.status, response.reason)
                msglog.log('OpenADR', msglog.types.ERR, error)
                raise EConnectionError(error) 
            else:
                localFileHandle.write(eventStateData)
                status = 1
        except ETimeout,e:
                msglog.exception('Timeout Waiting for Response')
                raise ETimeout('Timeout waiting for Response %s' %e)
        except Exception,e:      
                err = "Error in getting the Eventstates xml %s" % e   
                msglog.exception(err)      
                raise Exception(err)
        finally:
            connection.close()
            localFileHandle.close()
        return status

    def update_active_event_state(self):
        if self.updateNextState:
            if self.debug:
                    msglog.log('OpenADR',msglog.types.INFO, "Event OperationModeValue:%s EventStatus:%s"  % (str(self.nextOperationModeValue),\
                        str(self.nextEventStatus)) )      
                
            self.eventStates['OperationModeValue'] = self.nextOperationModeValue           
            self.eventStates['EventStatus'] = self.nextEventStatus         

    def  schedule_event_state_updater(self):
        """Updates active event state info based on the modetimeslots and the eventDuration (Response Schedule) .
        The procedure handles the following 
        1. check the CurrentTime since an active event is issued (Note it can be negative also in case of FAR,NEAR).
        2. Schedules the same procedure to udpate the OperationModeValue,EventStatus depends upon modetime slot values if the 
            server is not polled in that time window(Depends on poll period )
        3. Updates the OperationModeValue,EventState once event is finished (based on event duration computed 
            from startime and endtime of the event)   
        """
        #Update eventState 
        self.update_active_event_state()
        #if event state is active walk through Response schedule and schedule event updation based on timings 
        stat = True
        sched_done = False
        #If there is some event state updates scheduled cancel it.
        if self.response_scheduler_id != None:
            scheduler.cancel(self.response_scheduler_id)

        #Unless the event state is not  NONE ie eventStatus is FAR , NEAR or ACTIVE
        # walk through the ResponseSchedule to see 
        #if any event change need to be updated 
        if self.debug:
                msglog.log('OpenADR',msglog.types.INFO, "Event State is %s" % str(self.eventStates['EventStatus']))      
        if self.eventStates['EventStatus'] != EventStatus['NONE']:
            if len(self.eventStates['ModeSlot']['modeTimeSlot']):
                # For each modeTimeslot index there should be the OperationModeValue at same index , so both this list
                #should have the same length
                if(len(self.eventStates['ModeSlot']['modeTimeSlot']) == len(self.eventStates['ModeSlot']['OperationModeValue'])):
                    for idx in range(len(self.eventStates['ModeSlot']['modeTimeSlot'])):
                        # calculate the next timeSlot , if there is no poll scheduled in the time gap 
                        #schedule updater  to udpate the eventStates
                        if (self.currentTime < self.eventStates['ModeSlot']['modeTimeSlot'][idx] ) and \
                                ((self.eventStates['ModeSlot']['modeTimeSlot'][idx] - self.currentTime) < self.pollperiod):
                            self.updateNextState = True
                            #Update CurrentTime to the next event Time
                            self.nextOperationModeValue = self.eventStates['ModeSlot']['OperationModeValue'][idx]
                            self.nextEventStatus = EventStatus['ACTIVE']
                            sched_done = True
                            if self.debug:
                                msglog.log('OpenADR', msglog.types.INFO, "Scheduling event state udpate after:%f to %s" % \
                                           ( self.eventStates['ModeSlot']['modeTimeSlot'][idx] - self.currentTime,str(self.nextEventStatus)))
                            self.response_scheduler_id = scheduler.after(self.eventStates['ModeSlot']['modeTimeSlot'][idx] - self.currentTime,self.schedule_event_state_updater)
                            self.currentTime  = self.eventStates['ModeSlot']['modeTimeSlot'][idx]
                            break;    
                
                else :
                    msglog.exception("Error Invalid xml data")
                    raise EInvalidResponse("Invalid xml file")
            #Check if the updater needs to be scheduled to update the eventState after event is complete
            if sched_done != True:
                if (self.currentTime < self.eventDuration ) and \
                        ((self.eventDuration - self.currentTime) < self.pollperiod):

                    self.updateNextState = True
                    self.nextOperationModeValue = OperationMode['NORMAL']
                    self.nextEventStatus = EventStatus['NONE']
                    sched_done = True
                    self.response_scheduler_id = scheduler.after(self.eventDuration - self.currentTime ,self.schedule_event_state_updater)
                    if self.debug:
                        msglog.log('OpenADR', msglog.types.INFO, "Scheduling event state udpate after:%f to %s" % \
                        (self.eventDuration - self.currentTime,str(self.nextEventStatus)))
                    self.currentTime  = self.eventDuration
        return stat

    def dras_poll(self):
        """Pulls the event state info ,parse it and fill in the dictionary which is used for noderepresentation of eventstates """
        self.Error  = None
        try:
            if self.debug:
                msglog.log('OpenADR',msglog.types.INFO,"PULLing the file from DRAS Server") 
            if self.get_eventState(): 
                if self.parse(self):
                    self.currentTime = self.eventStates['currentTime']
                    self.calculate_event_duration()
                    self.confirm_event()
                    self.schedule_event_state_updater()
                    if self.debug :
                        msglog.log('openADR', msglog.types.INFO, "Successfully parsed the DR file")
            else :
                msglog.log('openADR', msglog.types.ERR, "Error in Getting EventState")
        except Exception,e:
            msglog.exception("Error in Processing response from server %s" %e)
            self.Error = Exception(e)
        #Reschedule the event 
        self.poll_id = scheduler.after(self.pollperiod,self.dras_poll);

class drEventStates(CompositeNode):
    def __init__(self):
        super(drEventStates, self).__init__()
        
    def configure(self, config):
        super(drEventStates, self).configure(config)

    def configuration(self):
        config = super(drEventStates, self).configuration()
        return config

    def get(self, skipcache=0):
        #Check and raise any exceptions present 
        if self.parent.Error != None:
            raise self.parent.Error 
        if self.parent.eventStates.has_key(self.name):
            return self.parent.eventStates[self.name];
        else:
            return None
    
class drEventStatesAttr(CompositeNode):
    def __init__(self):
        super(drEventStatesAttr,self).__init__()
        
    def configure(self, config):
        super(drEventStatesAttr, self).configure(config)

    def configuration(self):
        config = super(drEventStatesAttr, self).configuration()
        return config

    def get(self, skipcache=0):
        #Check and raise exceptions present 
        if self.parent.parent.Error != None:
            raise self.parent.parent.Error 
        if self.parent.parent.eventStates['eventStatesAttr'].has_key(self.name):
            return self.parent.parent.eventStates['eventStatesAttr'][self.name];
        else:
            return None

class drModeSchedule(CompositeNode):
    def __init__(self):
        super(drModeSchedule,self).__init__()
        
    def configure(self, config):
        super(drModeSchedule, self).configure(config)

    def configuration(self):
        config = super(drModeSchedule, self).configuration()
        return config

    def get(self, skipcache=0):
        #Check and raise any exceptions present 
        if self.parent.parent.parent.Error != None:
            raise self.parent.parent.parent.Error 
        if self.parent.parent.parent.eventStates['ModeSlot'].has_key(self.name):
            return self.parent.parent.parent.eventStates['ModeSlot'][self.name];
        else:
            return None

class drEventData(CompositeNode):
    def __init__(self):
        super(drEventData,self).__init__()
        
    def configure(self, config):
        super(drEventData, self).configure(config)

    def configuration(self):
        config = super(drEventData, self).configuration()
        return config

    def get(self, skipcache=0):
        #Check and raise any exceptions if present 
        if self.parent.parent.Error != None:
            raise self.parent.parent.Error 
        if self.parent.parent.eventStates['drEventData'].has_key(self.name):
            return self.parent.parent.eventStates['drEventData'][self.name];
        else:
            return None

