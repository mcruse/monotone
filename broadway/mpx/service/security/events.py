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
from mpx.lib.eventdispatch import Event

class SecurityEvent(Event):
    def __init__(self, node, *args, **kw):
        self.node = node
        super(SecurityEvent, self).__init__(*args, **kw)

class RoleEvent(SecurityEvent):
    pass

class UserEvent(SecurityEvent):
    pass

class PolicyEvent(SecurityEvent):
    pass

class RoleRemoved(RoleEvent):
    def __init__(self, url, node, *args, **kw):
        self.removed = url
        super(RoleRemoved, self).__init__(node, *args, **kw)

class RoleAdded(RoleEvent):
    pass

class RoleConfigured(RoleEvent):
    def __init__(self, config, *args, **kw):
        self.previous = config
        super(RoleConfigured, self).__init__(*args, **kw)

class UserRemoved(UserEvent):
    def __init__(self, url, *args, **kw):
        self.removed = url
        super(UserRemoved, self).__init__(*args, **kw)

class UserAdded(UserEvent):
    pass

class UserConfigured(UserEvent):
    def __init__(self, config, *args, **kw):
        self.previous = config
        super(UserConfigured, self).__init__(*args, **kw)

class PolicyRemoved(PolicyEvent):
    def __init__(self, url, node, *args, **kw):
        self.removed = url
        super(PolicyRemoved, self).__init__(node, *args, **kw)

class PolicyAdded(PolicyEvent):
    pass

class PolicyConfigured(PolicyEvent):
    def __init__(self, config, *args, **kw):
        self.previous = config
        super(PolicyConfigured, self).__init__(*args, **kw)
