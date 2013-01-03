"""
Copyright (C) 2002 2006 2007 2010 2011 Cisco Systems

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
from email.Utils import formatdate
from mpx.service.data import Formatter
from mpx.lib.configure import set_attribute,get_attribute
from mpx.lib.exceptions import EInvalidValue
from mpx.lib import msglog

class AlarmFormatter(Formatter):
    def format(self,data):
        data = data[0]
        if not (data.has_key('alarm') and 
                data.has_key('message') and 
                data.has_key('timestamp')):
            raise EInvalidValue('data',data,('Dictionary must contain ' +
                                             '"alarm","message", and ' + 
                                             '"timestamp" fields'))
        timestamp = data['timestamp']
        if hasattr(self.parent, 'gm_time') and not self.parent.gm_time:
            date = formatdate(timestamp, True)
        else:
            date = formatdate(timestamp, False)
        if data.has_key('subject'):
            subject = data['subject']
        else:
            subject = data['alarm']
        header = 'Subject: %s\r\n' % subject
        header += 'Date: %s\r\n\r\n' % date
        return header + data['message']

        
