"""
Copyright (C) 2003 2011 Cisco Systems

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
import array
import struct
import copy

from mpx.lib.exceptions import *
from mpx.lib.debug import dump_ints_tostring, dump_tostring, dump
from mpx.lib import EnumeratedDictionary, EnumeratedValue
from mpx.service.time import time
from mpx.lib.datetime import TimeOfDay
import frame

debug = 0


def _int_from_tcs_word(w):
#    answer = w[0] * 256 + w[1]
    answer = int(w, 16)
    if debug: print '_int_from_tcs_word: ' + str(w) + '  ' + str(answer)
    if answer > 0x7FFF:
        return answer & 0x7FFF
    return -(answer & 0x7FFF)

#handles the response string from the TCS controller
#single or multiple values can be handled
#if the command is passed in, data can be associated with its position bit
#and accessed via the 'at' method

class Response:
    def __init__(self, string, command=None):
        if debug: 'Response init with: ' + str(string)
        self.string = string
        self.data = []
        self.position_data = []
        self.command = command
        for i in range(0,len(string),4):
            self.data.append(_int_from_tcs_word(string[i:i+4]))
        self.data.reverse() #data comes back in msb position order
        if command:
            if command.positions:
                dl = copy.copy(self.data)
                if len(self.data) >= len(command.positions): #copy data for each position on response
                    for p in command.positions:
                        self.position_data.append([p,dl.pop(0),])
    def __str__(self):
        if self.position_data:
            return str(self.position_data)
        return str(self.data)

class GetValueReply(Response):
    def at(self, position):
        for p in self.position_data:
            if p[0] == position: return p[1]
        if debug: print 'GetValueReply position not found at: '+str(position)
        return None
    def __str__(self):
        if len(self.position_data) == 1: #since only one value in response
            return str(self.position_data[0][1])
        return Response.__str__(self)

class GetTypeReply(GetValueReply):
    def type(self):
        return int(self.string, 10) #unique response, not hex

class GetVersionReply():
    def __init__(self, string, command=None):
        if debug: 'Response init with: ' + str(string)
        self.string = string
        self.command = command
    def __str__(self):
        return str(self.string)
    def version(self):
        return self.string

class GetTimeOfDayReply(GetValueReply):
    pass
    #def __init__(self, string, command=None):
        #if debug: print 'time of day reply received'
        #Response.__init__(self, string, command)
        ##now convert to Time objects
        #new_data = []
        #for d in self.data:
            #new_data.append(TimeOfDay(d * 60))
        #self.data = new_data
        #if debug: print str(self.data)
        #for p in self.position_data:
            #p[1] = TimeOfDay(p[1] * 60) #convert to a Time Object
        #if debug: print 'gettimeofdayreply: ', str(self.position_data)
class GetHolidayReply(Response):
    def __init__(self, string, command=None):
        Response.__init__(self, string, command)
    def value(self):
        return self.data[0] #only one value per reply

class SetValueReply(Response):
    pass 
class SetTimeOfDayReply(Response):
    pass 
class SetHolidayReply(Response):
    pass
