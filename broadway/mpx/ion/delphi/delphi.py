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
import paramiko
import urllib
import base64
import filecmp
from datetime import date, datetime
from os import remove 
from os.path import exists, getsize
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import CompositeNode
from mpx.lib import msglog
from mpx.lib import EnumeratedDictionary
from mpx.lib import EnumeratedValue 
from mpx.lib.msglog.types import INFO, WARN, ERR
from mpx.lib.scheduler import Scheduler
from mpx.lib import httplib
from ftplib import FTP
from shutil import move
from mpx.lib.xmlrpclib import register_marshaller
from mpx.lib.xmlrpclib import ObjectMarshaller 

#Offsets used to parse EVENTS.NSS file 
MINUTE = 60
EVENT_NAME_OFFSET = 120
EVENT_NAME_LEN = 40
ROOM_NAME_OFFSET = 171
ROOM_NAME_LEN = 40
START_TIME_OFFSET = 211
START_TIME_LEN = 4
END_TIME_OFFSET = 215
END_TIME_LEN = 4
AGREED_ATTD_OFFSET = 243
AGREED_ATTD_LEN = 7
MEETING_INFO_LEN = 252

MeetingSpaceStatus = EnumeratedDictionary({0:'0:Unknown',
                                           1:'1:Available',
                                           2:'2:Scheduled',
                                           3:'3:In Progress'})

PropertyStatus = EnumeratedDictionary({0:'0:Init',
                                       1:'1:OK',
                                       2:'2:OK with event file same as yesterday',
                                       3:'3:Incomplete meeting information',
                                       4:'4:Communication Error, using backup event file',
                                       5:'5:Communication Error',
                                       6:'6:File IO Error'})

# String Marshalling using xmlrpc marshaller 
class DelphiEnum(dict):
    pass

class MeetingEnumeratedValue(EnumeratedValue):
    def enum(self):
        return DelphiEnum(super(MeetingEnumeratedValue, self).enum())

class DelphiEnumeratedValue(EnumeratedValue):
    def enum(self):
        return DelphiEnum(super(DelphiEnumeratedValue, self).enum())

    def __repr__(self): 
        # Hack to force string representation as Enum's value when 
        # included in subscription's change set.  
        return repr(self.text())

class DelphiAsStrMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        value = args[0]
        if isinstance(value, DelphiEnum):
            value = value.get('str', '')
        xmlrpc_marshaller.dump_string(str(value), *args[1:])

register_marshaller(DelphiEnum, DelphiAsStrMarshaller())
register_marshaller(MeetingEnumeratedValue, DelphiAsStrMarshaller())
register_marshaller(DelphiEnumeratedValue, DelphiAsStrMarshaller())

class DelphiWebService(CompositeNode):
    def __init__(self):
        super(DelphiWebService, self).__init__()

    def configure(self, config):
        super(DelphiWebService,self).configure(config)
        if self.debug:
            msglog.log('Delphi', INFO, "enabled = %d, debug = %d" %(self.enabled, self.debug))

    def configuration(self):
        config = super(DelphiWebService,self).configuration()
        get_attribute(self, 'debug', config)
        get_attribute(self, 'enabled', config)
        return config

    def start(self):
        msglog.log('Delphi', INFO, "DelphiWebService Start")
        if self.enabled:
            super(DelphiWebService, self).start()
    
    def stop(self):
        msglog.log('Delphi', INFO, "DelphiWebService Stop")
        if self.enabled:
            super(DelphiWebService, self).stop()

class Property(CompositeNode):
    def __init__(self):
        super(Property,self).__init__()
        self.interface_pc_addr = None
        self.communication_interface = None
        self.user_name = "" 
        self.password = ""
        self.event_file_location = None 
        self.polling_time = 0 
        self.grace_time = 0
        self.fileHandle = None
        self.fileSize = 0
        self.prevFileSize = -1
        self.retryCount = 0
        self.errorRetryCount = 0
        self.local_file_path = None
        self.downloadStatus = None 
        self.status = PropertyStatus['0:Init']
        self.scheduled_execution = None
        self.scheduler = Scheduler()
 

    def configure(self,config):
        super(Property,self).configure(config)
        set_attribute(self, 'interface_pc_addr', self.interface_pc_addr, config, str)
        set_attribute(self, 'communication_interface',self.communication_interface, config, str)
        set_attribute(self, 'user_name',self.user_name, config, str)
        set_attribute(self, 'password',self.password, config, str)
        set_attribute(self, 'event_file_location', self.event_file_location, config, str)
        set_attribute(self, 'polling_time', self.polling_time, config, int)
        set_attribute(self, 'grace_time', self.grace_time, config, int)
        
        if self.parent.debug:
            msglog.log('Delphi', INFO, "Property interface_pc_addr = %s,communication_interface = %s,user_name = %s, password = %s, \
            event_file_location = %s, polling_time = %d, grace_time = %d" %(self.interface_pc_addr, self.communication_interface, self.user_name, \
            self.password, self.event_file_location, self.polling_time, self.grace_time))

    def configuration(self):
        config = super(Property,self).configuration()
        get_attribute(self, 'interface_pc_addr', config)
        get_attribute(self, 'communication_interface', config)
        get_attribute(self, 'user_name', config)
        get_attribute(self, 'password', config)
        get_attribute(self, 'event_file_location', config)
        get_attribute(self, 'polling_time', config)
        get_attribute(self, 'grace_time', config)
        return config

    def start(self):
        msglog.log('Delphi', INFO, "Property Start")
        if self.parent.enabled:

            self.local_file_path = '/tmp/'+self.name+'_EVENTS.NSS'
           
            # Lets remove if there is any stale file 
            if exists(self.local_file_path):
                remove(self.local_file_path)
            if exists(self.local_file_path+'_bak'):
                remove(self.local_file_path+'_bak')
            if exists(self.local_file_path+'_prevday'):
                remove(self.local_file_path+'_prevday')

            for child in self.children_nodes():
                if child.identity == 'status':
                    self.downloadStatus = child
                    break 

            if self.interface_pc_addr == None or self.event_file_location == None:
                msglog.log('Delphi', WARN, "Check interface pc address and event file location configurations")
            else:
                protocol=self.communication_interface+'://'
                if self.interface_pc_addr[:len(protocol)] == protocol:
                    self.interface_pc_addr = self.interface_pc_addr[len(protocol):]

                if not self.scheduler.is_started():
                    try:
                        self.scheduler.start()
                        self.schedulePollAfterInterval( 5 )#start scheduler in 5 second
                    except:
                      msglog.exception()

            super(Property, self).start()

    def stop(self):
        msglog.log('Delphi', INFO, "Property Stop")
        if self.parent.enabled:
            try:
                if self.scheduled_execution:
                    self.scheduled_execution.cancel()
                if not self.scheduler.is_stopped():
                    self.scheduler.stop()
            except:
                msglog.exception()

            if exists(self.local_file_path):
                remove(self.local_file_path)
            if exists(self.local_file_path+'_bak'):
                remove(self.local_file_path+'_bak')
            if exists(self.local_file_path+'_prevday'):
                remove(self.local_file_path+'_prevday')
            super(Property, self).stop()

    def get(self,skipcache=0):
        return  DelphiEnumeratedValue(int(self.status), str(self.status))

    def poll(self):
        if self.parent.debug:
            msglog.log('Delphi', INFO, "Property Poll")
        
        self.fileHandle = None
        
        if exists(self.local_file_path+'_bak'):
            if datetime.now().hour == 0 and datetime.now().minute < self.polling_time:
                move(self.local_file_path+'_bak', self.local_file_path+'_prevday') 
             
        if self.parent.debug:
            msglog.log('Delphi', INFO, self.communication_interface+" connection")
            
        if self.communication_interface == 'http':
            retValue = self.httpDownload()
        elif self.communication_interface == 'https':
            retValue = self.httpsDownload()
        elif self.communication_interface == 'ftp':
            retValue = self.ftpDownload()
        else:# communication_interface = 'sftp'
            retValue = self.sftpDownload()

        if retValue:
            try:
                self.fileHandle = open(self.local_file_path)
            except IOError, e:
                msglog.log('Delphi', ERR, "IOError: Unable to open events file. %s" %e)
                self.status = PropertyStatus['6:File IO Error']
            if self.downloadStatus:
                self.downloadStatus.status = "Download Success at %s" %datetime.now() 
        else:
            self.status = PropertyStatus['5:Communication Error']
            if self.downloadStatus: 
                self.downloadStatus.status = "Download Failed at %s" %datetime.now() 

        if self.fileHandle != None:
            self.fileSize = getsize(self.local_file_path)
            if self.fileSize == self.prevFileSize:
                if exists(self.local_file_path+'_prevday') and filecmp.cmp(self.local_file_path, self.local_file_path+'_prevday'):
                    self.status = PropertyStatus['2:OK with event file same as yesterday']
                else:
                    self.status = PropertyStatus['1:OK']
                self.parseResponse()
                self.fileHandle.close()
                self.fileSize = 0
                self.prevFileSize = -1 
                self.retryCount = 0
                move(self.local_file_path, self.local_file_path+'_bak')
                self.schedulePollAfterInterval( self.polling_time * MINUTE )
            else:
                self.prevFileSize = self.fileSize
                if self.retryCount < 5:# Retry max 5 times 
                    self.fileHandle.close()
                    self.retryCount += 1
                    self.schedulePollAfterInterval( 10 )
                else:
                    msglog.log('Delphi', WARN, "Consecutive 5 retries resulted in different file size. Continuing with last response")
                    if exists(self.local_file_path+'_prevday') and filecmp.cmp(self.local_file_path, self.local_file_path+'_prevday'):
                        self.status = PropertyStatus['2:OK with event file same as yesterday']
                    else:
                        self.status = PropertyStatus['1:OK']
                    self.parseResponse()
                    self.fileHandle.close()
                    self.fileSize = 0
                    self.prevFileSize = -1 
                    self.retryCount = 0
                    move(self.local_file_path, self.local_file_path+'_bak')
                    self.schedulePollAfterInterval( self.polling_time * MINUTE )
        else:
            if self.errorRetryCount < 10:# Retry for max 10 times on error
                msglog.log('Delphi', WARN, "Communication error: File Not received, Will retry after 10 seconds....")
                self.errorRetryCount += 1
                self.schedulePollAfterInterval( 10 )
            else:
                if exists(self.local_file_path+'_bak'):
                    try:
                        self.fileHandle = open(self.local_file_path+'_bak')
                        if self.fileHandle != None:
                            msglog.log('Delphi', INFO, "Latest events file not received. Loading information from previous event file..")
                            self.status = PropertyStatus['4:Communication Error, using backup event file']
                            self.parseResponse()
                            self.fileHandle.close()
                    except IOError, e:
                        msglog.log('Delphi', ERR, "IOError: Unable to open backup events file. %s" %e)
                        self.status = PropertyStatus['6:File IO Error']
                else:
                    for roomName in self.children_nodes():
                        if roomName.identity == 'room':
                            roomName.checkForMeetingSpace()

                msglog.log('Delphi', WARN, "Couldn't receive file in max retries attempt. Will attempt again after polling period....")
                self.errorRetryCount = 0
                self.schedulePollAfterInterval( self.polling_time * MINUTE )

    def schedulePollAfterInterval( self, interval = 0 ):
        try:
            if self.scheduled_execution:
                self.scheduled_execution.cancel()
            self.scheduled_execution = self.scheduler.after( interval , self.poll)
            if self.parent.debug:
                msglog.log('Delphi', INFO, "scheduled_execution - %s" %self.scheduled_execution)
        except:
            msglog.exception()
 
    def httpDownload(self):
        full_url = self.communication_interface+'://'+self.user_name+':'+self.password+'@'+self.interface_pc_addr+self.event_file_location
        try:
            url_opener = urllib.URLopener()
            webFileHandle = url_opener.open(full_url)
            localFileHandle = open(self.local_file_path,'wb')
            localFileHandle.write(webFileHandle.read())
            webFileHandle.close()
            localFileHandle.close()
            return True
        except IOError, e:
            if e[0] == "http error":
                msglog.log('Delphi', ERR, "HTTP Download Error: status = %d, reason = %s" %(e[1],e[2]))
            else:
                msglog.log('Delphi', ERR, "HTTP Download Error: %s" %e)
            
            if exists(self.local_file_path):
                remove(self.local_file_path)
        except Exception, e:
            msglog.log('Delphi', ERR, "%s communication error: %s. Check server configuration and network status." %(self.communication_interface, e))
        return False
    
    def httpsDownload(self):
        try:
            base64string = base64.encodestring('%s:%s' % (self.user_name,self.password))
            authString = 'Basic %s' % base64string
            headers = {"AUTHORIZATION" : authString}
            connection = httplib.HTTPSConnection(self.interface_pc_addr)
            connection.request('GET',self.event_file_location,None,headers)
            response = connection.getresponse()
            if response.status == 200:# O.K
                localFileHandle = open(self.local_file_path,'wb')
                localFileHandle.write(response.read())
                localFileHandle.close()
                connection.close()
                return True
            else:
                msglog.log('Delphi', ERR, "HTTPS Download Error: status = %d, reason = %s" %(response.status, response.reason))
                if exists(self.local_file_path):
                    remove(self.local_file_path)
                connection.close()
                return False 
        except IOError, e:
            msglog.log('Delphi', ERR, "HTTPS Download Error: %s" %e)
        except Exception, e:
            msglog.log('Delphi', ERR, "%s communication error: %s. Check server configuration and network status." %(self.communication_interface, e))
        return False

    def ftpDownload(self):
        try:
            ftp = FTP(self.interface_pc_addr)
            ftp.login(self.user_name,self.password)
            localFileHandle = open(self.local_file_path,'wb')
            ftp.retrbinary('RETR '+self.event_file_location, localFileHandle.write)
            localFileHandle.close()
            ftp.quit()
            return True
        except IOError, e:
            msglog.log('Delphi', ERR, "FTP Download Error: %s" %e)
        except Exception, e:
            msglog.log('Delphi', ERR, "%s communication error: %s. Check server configuration and network status." %(self.communication_interface, e))
        return False

    def sftpDownload(self):
        try:
            port = 22
            transport = paramiko.Transport((self.interface_pc_addr, port))
            transport.connect(username = self.user_name, password = self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get(self.event_file_location,self.local_file_path)
            sftp.close()
            transport.close()
            return True
        except IOError, e:
            msglog.log('Delphi', ERR, "SFTP Download Error: %s" %e)
        except Exception, e:
            msglog.log('Delphi', ERR, "%s communication error: %s. Check server configuration and network status." %(self.communication_interface, e))
        return False

    def parseResponse(self):
        if self.parent.debug:
            msglog.log('Delphi', INFO, "Property parseResponse")

        for roomName in self.children_nodes():
            if roomName.identity == 'room':
                roomName.checkForMeetingSpace()

        for meetingInfoLine in self.fileHandle:
            if len(meetingInfoLine) == MEETING_INFO_LEN:
                foundRoom = False
                string = meetingInfoLine[ROOM_NAME_OFFSET:ROOM_NAME_OFFSET+ROOM_NAME_LEN].strip().upper()
                for roomName in self.children_nodes():
                    if roomName.identity == 'room' and roomName.name.strip().upper() == string:
                        roomName.updateMeetingSpace(meetingInfoLine)
                        foundRoom = True
                        break
                if foundRoom == False:
                    if self.parent.debug:
                        msglog.log('Delphi', WARN, "Room Name %s is not configured in ConfigTool" %string) 
            else:
                msglog.log('Delphi', INFO, "Incomplete Meeting Information!!! Skipping Meeting Update")
                self.status = PropertyStatus['3:Incomplete meeting information']  

class DownloadStatus(CompositeNode):
    def __init__(self):
        super(DownloadStatus,self).__init__()
        self.status = 'Unknown'
        self.identity = 'status' 

    def configure(self,config):
        super(DownloadStatus,self).configure(config)

    def configuration(self):
        config = super(DownloadStatus,self).configuration()
        return config

    def get(self,skipcache=0):
        return self.status
            
class RoomName(CompositeNode):
    def __init__(self):
        super(RoomName,self).__init__()
        self.identity = 'room' 

    def configure(self,config):
        super(RoomName,self).configure(config)

    def configuration(self):
        config = super(RoomName,self).configuration()
        return config

    def checkForMeetingSpace(self):
        for name in sorted(self.children_names()):
            meetingSpace = self.as_node(name)
            meetingSpace.updateMeetingStatus('clear')
    
    def updateMeetingSpace(self, meetingInfoLine):
        if self.parent.parent.debug:
            msglog.log('Delphi', INFO, "RoomName - %s" %self.name)

        updateFlg = False
        lowest = 0.0
        highest = 0.0
        duplicateEntry = False

        eventStartTime = meetingInfoLine[START_TIME_OFFSET:START_TIME_OFFSET+START_TIME_LEN] 
        time_tuple = ( date.today().year, date.today().month, date.today().day, int(eventStartTime[0:2]), \
        int(eventStartTime[2:4]), 0, 0, 0, -1 )
        startEpochTime = time.mktime( time_tuple )

        eventEndTime = meetingInfoLine[END_TIME_OFFSET:END_TIME_OFFSET+END_TIME_LEN]
        time_tuple = (date.today().year, date.today().month, date.today().day, int(eventEndTime[0:2]), \
        int(eventEndTime[2:4]), 0, 0, 0, -1)
        endEpochTime = time.mktime( time_tuple )

        eventName = meetingInfoLine[EVENT_NAME_OFFSET:EVENT_NAME_OFFSET+EVENT_NAME_LEN].strip()

        #Finding if meeting is already present in any child node
        for name in sorted(self.children_names()):
            meetingSpace = self.as_node(name)
            if meetingSpace.status == MeetingSpaceStatus['3:In Progress']:
                if startEpochTime == meetingSpace.startEpochTime.sec and endEpochTime == meetingSpace.endEpochTime.sec and \
                eventName == meetingSpace.eventName.event:
                    duplicateEntry = True
                    break

        #Update Meeting details in Avaibale Meeting Space
        if duplicateEntry == False:
            for name in sorted(self.children_names()):
                meetingSpace = self.as_node(name)
                if meetingSpace.status == MeetingSpaceStatus['1:Available'] or meetingSpace.status == MeetingSpaceStatus['0:Unknown']:
                    meetingSpace.updateMeetingSpaceDetail(meetingInfoLine)
                    updateFlg = True
                    break
       
            #If there is not enough Meeting Spaces available to store then we have to store only upcoming meetings
            if updateFlg == False:
                for name in sorted(self.children_names()):
                    meetingSpace = self.as_node(name)
                    if meetingSpace.status != MeetingSpaceStatus['3:In Progress']:
                        lowest = meetingSpace.startEpochTime.sec 
                        if lowest > highest:
                            highest = lowest
              
                if highest > startEpochTime:
                    for name in sorted(self.children_names()):
                        meetingSpace = self.as_node(name)
                        meetingSpace.clearLateStartMeetingSpace(highest)
                        if meetingSpace.status == MeetingSpaceStatus['1:Available']:
                            meetingSpace.updateMeetingSpaceDetail(meetingInfoLine)
                            break


class MeetingSpace(CompositeNode):
    def __init__(self):
        super(MeetingSpace,self).__init__()
        self.status = MeetingSpaceStatus['0:Unknown']
        self.eventName = None
        self.startDateTime = None
        self.startEpochTime = None
        self.endDateTime = None
        self.endEpochTime = None
        self.agreedAttd = None
        self.currentEpochTime = 0.0 

    def configure(self,config): 
        super(MeetingSpace,self).configure(config)

    def configuration(self):
        config = super(MeetingSpace,self).configuration()
        return config
        
    def get(self,skipcache=0):
        self.updateMeetingStatus('update')
        return  MeetingEnumeratedValue(int(self.status), str(self.status))
        
    def updateMeetingStatus(self, flag='clear'):
        self.currentEpochTime = time.time()
        grace_time = self.parent.parent.grace_time * MINUTE

        #If flag is clear then except "In Progress" clear other the Meeting Spaces to update new data
        #If flag is update then update meeting space based on timestamp 
        if exists(self.parent.parent.local_file_path) or exists(self.parent.parent.local_file_path+'_bak'):
            if (self.startEpochTime.sec < self.currentEpochTime) and ((self.endEpochTime.sec + grace_time) > self.currentEpochTime):
                self.status = MeetingSpaceStatus['3:In Progress']
            elif flag == 'update':
                if (self.endEpochTime.sec + grace_time) < self.currentEpochTime:
                    self.status = MeetingSpaceStatus['1:Available']
                    self.eventName.event = None
                    self.startDateTime.time = None
                    self.startEpochTime.sec = 0
                    self.endDateTime.time = None
                    self.endEpochTime.sec = 0 
                    self.agreedAttd.count = 0
                else:
                    self.status = MeetingSpaceStatus['2:Scheduled']
            else:
                self.status = MeetingSpaceStatus['1:Available']
                self.eventName.event = None
                self.startDateTime.time = None
                self.startEpochTime.sec = 0
                self.endDateTime.time = None
                self.endEpochTime.sec = 0
                self.agreedAttd.count = 0
        else: 
            self.status = MeetingSpaceStatus['0:Unknown']
            self.eventName.event = None
            self.startDateTime.time = None
            self.startEpochTime.sec = 0
            self.endDateTime.time = None
            self.endEpochTime.sec = 0
            self.agreedAttd.count = 0

        if self.parent.parent.parent.debug:
            msglog.log('Delphi', INFO, "updateMeetingStatus: %s - %s" %(self.name, str(self.status)))
       
    def updateMeetingSpaceDetail(self, meetingInfoLine):
        #Fetch information from meetingInfoLine and store it in child nodes
        
        #updating Dephi Meeting Event Name 
        self.eventName.event = meetingInfoLine[EVENT_NAME_OFFSET:EVENT_NAME_OFFSET+EVENT_NAME_LEN].strip()

        #updating startDateTime and startEpochTime
        eventStartTime = meetingInfoLine[START_TIME_OFFSET:START_TIME_OFFSET+START_TIME_LEN] 
        time_tuple = (date.today().year, date.today().month, date.today().day, int(eventStartTime[0:2]), \
        int(eventStartTime[2:4]), 0, 0, 0, -1)
        self.startEpochTime.sec = time.mktime( time_tuple ) 
        self.startDateTime.time = time.ctime( self.startEpochTime.sec ) 
        
        #updating endDateTime and endEpochTime
        eventEndTime = meetingInfoLine[END_TIME_OFFSET:END_TIME_OFFSET+END_TIME_LEN] 
        time_tuple = (date.today().year, date.today().month, date.today().day, int(eventEndTime[0:2]), \
        int(eventEndTime[2:4]), 0, 0, 0, -1)
        self.endEpochTime.sec = time.mktime( time_tuple )
        self.endDateTime.time = time.ctime( self.endEpochTime.sec ) 

        #updating Agreed Attendance 
        self.agreedAttd.count = int(meetingInfoLine[AGREED_ATTD_OFFSET:AGREED_ATTD_OFFSET+AGREED_ATTD_LEN].strip())
       
        self.updateMeetingStatus('update')
 
        if self.parent.parent.parent.debug:
            msglog.log('Delphi', INFO, "%s, EventName - %s, StartTime - %s, StartEpochTime - %f, EndTime - %s, EndEpochTime - %f, AgrAtd - %d" \
            %(self.name, self.eventName.event, self.startDateTime.time, self.startEpochTime.sec, self.endDateTime.time, self.endEpochTime.sec, \
            self.agreedAttd.count))

    def clearLateStartMeetingSpace(self,highest):
        if self.startEpochTime.sec ==  highest:
            self.status = MeetingSpaceStatus['1:Available'] 
            if self.parent.parent.parent.debug:
                msglog.log('Delphi', INFO, "clearLateStartMeetingSpace: %s" %(self.name))

class EventName(CompositeNode):
    def __init__(self):
        super(EventName,self).__init__()
        self.event = None 

    def configure(self,config):
        super(EventName,self).configure(config)
        self.parent.eventName = self

    def configuration(self):
        config = super(EventName,self).configuration()
        return config

    def get(self,skipcache=0):
        return self.event

class StartDateTime(CompositeNode):
    def __init__(self):
        super(StartDateTime,self).__init__()
        self.time = None 

    def configure(self,config):
        super(StartDateTime,self).configure(config)
        self.parent.startDateTime = self

    def configuration(self):
        config = super(StartDateTime,self).configuration()
        return config

    def get(self,skipcache=0):
        return self.time

class StartEpochTime(CompositeNode):
    def __init__(self):
        super(StartEpochTime,self).__init__()
        self.sec = 0 

    def configure(self,config):
        super(StartEpochTime,self).configure(config)
        self.parent.startEpochTime = self

    def configuration(self):
        config = super(StartEpochTime,self).configuration()
        return config

    def get(self,skipcache=0):
        return self.sec
    
class EndDateTime(CompositeNode):
    def __init__(self):
        super(EndDateTime,self).__init__()
        self.time = None 

    def configure(self,config):
        super(EndDateTime,self).configure(config)
        self.parent.endDateTime = self

    def configuration(self):
        config = super(EndDateTime,self).configuration()
        return config

    def get(self,skipcache=0):
        return self.time

class EndEpochTime(CompositeNode):
    def __init__(self):
        super(EndEpochTime,self).__init__()
        self.sec = 0  

    def configure(self,config):
        super(EndEpochTime,self).configure(config)
        self.parent.endEpochTime = self

    def configuration(self):
        config = super(EndEpochTime,self).configuration()
        return config

    def get(self,skipcache=0):
        return self.sec

class AgreedAttendance(CompositeNode):
    def __init__(self):
        super(AgreedAttendance, self).__init__()
        self.count = 0 

    def configure(self, config):
        super(AgreedAttendance, self).configure(config)
        self.parent.agreedAttd = self

    def configuration(self):
        config = super(AgreedAttendance, self).configuration()
        return config

    def get(self, skipcache=0):
        return self.count

