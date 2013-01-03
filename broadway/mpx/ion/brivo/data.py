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

class BrivoData(dict):
    _props = ()    
    def __call__(self, **kw):
        a = {}
        for k,v in kw.items():
            if k in self._props:
                a[k] = v
        self.update(a)
        return self.copy()

class BrivoId(BrivoData):
    _props = ('type', 'value')
        
class BrivoUser(BrivoData):
    _props = ('brivo_id', 'external_id','first_name', 
        'last_name','enabled', 'expires','pin', 
        'card_id', 'group_ids', 'custom_fields')
    
class BrivoCard(BrivoData):
    _props = ('id', 'value', 'facility', 'format_id')
    
class BrivoCardFormat(BrivoData):
    _props = ('id', 'name')
    
class BrivoCustomField(BrivoData):
    _props = ('id', 'value')
    
class BrivoCustomFieldDefinition(BrivoData):
    _props = ('id', 'name', 'type', 'length')
    
class BrivoGroup(BrivoData):
    _props = ('name', 'brivo_id', 'external_id', 
        'member_count')
        
class BrivoEvent(BrivoData):
    _props = ('id', 'event', 'occurred', 'device',
        'device_id', 'user', 'user_id', 'schedule',
        'schedule_id', 'user_sets', 'device_sets',
        'control_panel', 'control_panel_id')
        
class BrivoEventSubscription(BrivoData):
    _props = ('id', 'name', 'url', 'error_email', 'criteria')
    
class BrivoDevice(BrivoData):
    _props = ('id', 'name', 'type')
    
class BrivoDeviceSet(BrivoData):
    _props = ('id', 'name')
    
class BrivoUserSet(BrivoData):
    _props = ('id', 'name')
    
class BrivoAccount(BrivoData):
    _props = ('id', 'name')
    
class BrivoCriteria(BrivoData):
    _props = ('keyword', 'operator', 'value')
    
class BrivoControlPanel(BrivoData):
    _props = ('id', 'name')

class BrivoCriteria(BrivoData):
    _props = ('keyword', 'operator', 'value')
    
    
    
    
    