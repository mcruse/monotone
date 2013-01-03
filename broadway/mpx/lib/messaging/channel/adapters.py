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
from mpx.componentry import adapts
from mpx.componentry import implements
from mpx.componentry import register_adapter
from mpx.lib.messaging.channel.interfaces import IMessageChannel
from mpx.lib.messaging.channel.interfaces import IMessageListener

class ChannelAdapter(object):
    """
        Wrap Channel instance with message listener interface.
    """
    implements(IMessageListener)
    adapts(IMessageChannel)
    def __init__(self, channel):
        self.channel = channel
        super(ChannelAdapter, self).__init__()
    def handle_message(self, message):
        self.channel.send(message)
    def __eq__(self, other):
        return self.channel == other.channel

register_adapter(ChannelAdapter)

class ListenerAdapter(object):
    implements(IMessageChannel)
    adapts(IMessageListener)
    def __init__(self, listener):
        self.listener = listener
        super(ListenerAdapter, self).__init__()
    def send(self, message):
        self.listener.handle_message(message)
    def __eq__(self, other):
        return self.listener == other.listener

register_adapter(ListenerAdapter)