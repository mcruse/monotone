"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
# File Input / Output for Tracer internal files.
#

from mpx.lib.exceptions import *
from mpx.lib.tcs import frame, command, response
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.datetime import *

debug = 0
MAX_ATTEMPTS = 5

_module_lock = Lock()

class TCSValue:
    def __init__(self, line_handler, parameter, position, unitnum):
        self.lh = line_handler
        self.parameter = parameter #letter code
        self.position = position #position number
        self.last_response = None
        self.unitnum = unitnum
        if debug:
            print 'line handler: ', str(self.lh)
            print 'parameter:    ', str(self.parameter)
            print 'position:     ', str(self.position)
            print 'unitnum:      ', str(self.unitnum)
    def __str__(self):
        return 'TCS point: parameter = '+str(self.parameter)+', index = '+str(self.position)
    def get(self, skipCache=0):
        c = command.GetValue(self.parameter, [self.position])
        if debug: print str(c)
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        if debug: print str(self.last_response)
        return self.last_response.at(self.position)
    def set(self, value):
        c = command.SetValue(self.parameter, [(self.position, value),])
        if debug: print str(c)
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        if debug: print str(self.last_response)
        return
    
class TCSTime(TCSValue):
    def get(self, skipCache=0):
        c = command.GetTimeOfDayValue(self.parameter, [self.position])
        self.last_response = self.lh.send_request_with_response(c,unitnum=self.unitnum,numretries=MAX_ATTEMPTS)
        return self.last_response.at(self.position)
    def set(self, value):
        c = command.SetTimeOfDayValue(self.parameter, [(self.position,value),])
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        return
    
class TCSType(TCSValue):
    def get(self, skipCache=0):
        c = command.GetType()
        if debug: print str(c)
        self.last_response = self.lh.send_request_with_response(c,unitnum=self.unitnum,numretries=MAX_ATTEMPTS)
        if debug: print str(self.last_response)
        return self.last_response.type()

class TCSHoliday(TCSValue):
    def get(self):
        if self.parameter != 'H':
            raise EInvalidCommand(self.parameter, 'Holiday parameter must be "H"')
        #position number index 1 - 12 for holiday 1 entries and 13 - 24 for holiday 2 entries
        index = self.position
        position = 1
        if index > 12:
            position = 8 #holiday 2 month
            index = index - 12
        c = command.GetHolidayValue(self.parameter, index, position) #month
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        m = self.last_response.value()
        c = command.GetHolidayValue(self.parameter, index, (position << 1)) #date
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        d = self.last_response.value()
        c = command.GetHolidayValue(self.parameter, index, (position << 2)) #duration
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        duration = self.last_response.value()
        print 'holiday: ', m, d, duration
        if (m == 0) or (d == 0):
            return None
        if duration > 0:
            duration = duration - 1 #date ranges are inclusive
        sd = Date(month=m, day=d)
        print 'start date ', str(sd)
        print 'duration type/value ', type(duration), int(duration)
        ed = sd + duration #magic
        print 'end date ', str(ed)
        return DateRange(sd, ed)
    def set(self, value):
        if self.parameter != 'H':
            raise EInvalidCommand(self.parameter, 'Holiday parameter must be "H"')
        #position number index 1 - 12 for holiday 1 entries and 13 - 24 for holiday 2 entries
        index = self.position
        position = 1
        if index > 12:
            position = 8 #holiday 2 month
            index = index - 12
        if value is None:
            month = 0
            day = 0
            duration = 0
        else:
            month = value.start_date.month
            day = value.start_date.day
            duration = value.get_duration()
        c = command.SetHolidayValue(self.parameter, index, position, month) #month
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        c = command.SetHolidayValue(self.parameter, index, (position << 1), day) #date
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        c = command.SetHolidayValue(self.parameter, index, (position << 2), duration) #duration
        self.last_response = self.lh.send_request_with_response(c,self.unitnum,numretries=MAX_ATTEMPTS)
        return
        
