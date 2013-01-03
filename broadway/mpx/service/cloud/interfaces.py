"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.componentry import Interface, Attribute

class ICloudManager(Interface):
    def handle_remote_event(data):
        """
            Parse and dispatch incoming event by topic to any topic
            listeners, then propogate event to remainder of cloud.
        """

    def handle_local_event(event, topics = []):
        """
            Create cloud event with topic 'topic' and content 'event',
            then propogate event to remainder of cloud.

            Event 'event' will be propogated throughout cloud.
        """

    def add_listener(callback, topic):
        """
            Register callback 'callback' for all remote events
            with topic 'topic.'

            Returns ID for use when unregistering.
        """

    def remove_listener(id):
        """
            Remove callback whose registration returned id 'id'.
        """

    def handle_formation_udpate(self, event):
        """
            Even listener to handle formation updates.
        """

    def propogate(cloudevent, from_host = None):
        """
            Propogate the cloud event to the
            appropriate targets.
        """

class ICloudEvent(Interface):
    topics = Attribute(
        """
            The list of event topic under which this
            CloudEvent's event should be notified.
        """)
    event = Attribute(
        """
            The Event instance the CloudEvent wraps.
        """
    )
    targets = Attribute(
        """
            A list of targets to which this event is currently being sent.
        """
    )
    portal = Attribute(
        """
            A portal to which this event is currently being sent.
        """
    )
