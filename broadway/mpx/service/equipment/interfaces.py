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
from mpx.componentry import Interface

class IEquipmentMonitor(Interface):
    """
        Service for managing subscriptions for equipment upates, persisting 
        those subscriptions to auto-restart following shutdown, and to 
        periodically push subscription COV data out to target URLs.
    """
    
    def create_pushed(target, node_table, period=2, retries=10, persist=True):
        """
            Creates new subscription for nodes specified in node table.  
            Pushed subscriptions use child formatter and transporter 
            nodes to determine how pushed data is formatted and transported.
            Target 'target' will be passed directly to the transporter when 
            pushing out data; it's meaning is opaque to the EQ Monitor.
            Typically it will be the URL to which an HTTP POST Transporter 
            is to send data.
            
            Providing a 'period' that is None, 0, or less that zero indicates 
            that data should be pushed as COV events are captured.  
            
            If 'period' is a positive numeric value, COV data associated with 
            the subscription will be formatted and pushed every 'period' 
            seconds.  When a positive numeric 'period' is specified, data 
            will be pushed every 'period' seconds even if no COV data 
            is available for that interval; meaning an empty transmit can 
            be used as a heartbeat and expected even in the absence of COV 
            data.
            
            If 'retries' is not None and not 0, the subscription will be 
            canceled after 'retries' consecutive failures to push data 
            to target.  This provides a safety for misconfigured targets.
            
            The format of the pushed data will be determined by the attached 
            formatter.
        """
    
    def cancel(sid):
        """
            Destroy subscription associated with subscription ID 
            'sid'.  The subscription will be canceled regardless 
            of the subscription type.  If a subscription was found 
            and canceled, return True, otherwise return False.
        """
    
    def pause(sid, delay=None):
        """
            Pause pushed subscription with ID 'sid'.  Although 
            it is not an error to call pause on a polled subscription, 
            doing so will have no effect.  Optional delay 'delay' in 
            seconds may be provided, indicating the subscription should 
            begin pushing automatically following the delay.  If delay is 
            None or 0, the pause is indefinite.
        """
    
    def play(sid):
        """
            Restart paused subscription with ID 'sid'.  Calling 
            method with subscription that has not been paused has 
            no effect; calling with subscription that is not pushed 
            has no effect; calling with subscription that does not 
            exist raises an exception.
        """
    
    def reset(sid):
        """
            Reset subscription with ID 'sid', causing the export of 
            all point values upon next execution, regardless of 
            whether they would be exported in a COV export or not.
        """
    
    def list_subscriptions():
        """
            Return list of all existing subscription IDs.
        """
