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
"""
object: Contains code and data pertaining to basic, common BACnet objects.
"""

object_types = {
        'analog_input':0,
        'analog_output':1,
        'analog_value':2,
        'binary_input':3,
        'binary_output':4,
        'binary_value':5,
        'calendar':6,
        'command':7,
        'device':8,
        'event_enrollment':9,
        'file':10,
        'group':11,
        'loop':12,
        'multi_state_input':13,
        'multi_state_output':14,
        'notification_class':15,
        'program':16,
        'schedule':17,
        'averaging':18,
        'multi_state_value':19,
        'trend_log':20,
        'life_safety_point':21,
        'life_safety_zone':22
        }
