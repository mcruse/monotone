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
from mpx.componentry import Interface
from mpx.componentry import Attribute

class IChannelMonitor(Interface):
    """
        Dictionary-like object which holds set of channels and 
        provides methods for monitoring channel set for events.
    """
    def set_timeout(timeout):
        """
            Set timeout for monitoring loop.
            By default this value is set to 30 seconds.
        """
    def check_channels():
        """
            Wakeup monitoring loop so that all channels 
            are checked for interest in read/write events.
        """
    def start_monitor():
        """
            Start new monitoring thread.  Once called, channels 
            in monitor will be actively montored for events.
        """
    def stop_monitor(timeout = None):
        """
            Stop monitoring thread.  Once called, channels in monitor 
            will no longer be actively monitored for events.
            
            Optional parameter timeout permits caller to block, waiting 
            for monitoring thread to finish running.  Providing None 
            for parameter blocks forever until thread termination, otherwise 
            maximum seconds can be provided.  Note that providing no value 
            here does not cause any wait delay; None must be provided 
            explicitly to wait indefinitely.
        """
    def shutdown_channels():
        """
            Monitor will run through channels closing each.
        """
    def join_monitor(timeout = None):
        """
            Wait for monitoring thread to terminate.  Timeout 
            parameter may express maximum wait period in seconds.
        """
    def is_running():
        """
            Returns true if channels are currently being monitored 
            by channel monitor.
        """
    def run_monitor():
        """
            Run monitoring loop.  This method will not return until 
            stop_monitor is called explicitly.
        """
    
class IChannel(Interface):
    def should_monitor_writable():
        """
            Return True if channel wants notification when 
            underlying socket object becomes writable.  Note, 
            this usually means the channel has data it wishes 
            to send over the socket.
        """
    def should_monitor_readable():
        """
            Return True if channel wants notification when 
            underlying socket object becomes readable.  Note, 
            this usually means the channel has room in input 
            buffers or is receiving data actively over channel.
        """
    def get_socket():
        """
            Return underlying socket object which channel is 
            receiving data from and sending data to.
        """
    def file_descriptor():
        """
            Return file-descriptor associated with socket.
        """
    def reset_terminator():
        """
            Reset terminator indicator to default value of \r\n\r\n
            
            NOTE: this method is usually invoked internally.
        """
    def notify_response_loaded(response):
        """
            Notify Channel that a response has been read completely 
            and the channel may now close or prepare for next 
            response accordingly.
            
            NOTE: this method is usually invoked internally.
        """
    def reset_channel():
        """
            Discard current incoming buffers and reconfigure channel
            to initial incoming settings, such as resetting terminator.
            
            NOTE: this method is usually invoked internally, either 
            when a complete request has been recevied and setup or 
            when a continue-100 header has been received.
        """
    def send_request(request):
        """
            Add request 'request' to channel's outgoing request information.
            Although this method does not directly begin transmitting data 
            over the connection, it does notify the socket map that outgoing 
            data is now available and the map should be repolled for 
            readable/writable handles.
        """
    def setup_connection(host, port, connectiontype):
        """
            Setup this channels socket connection.  Host and port 
            indicate target device, and connection type is either 
            'http' or 'https'.  No other connection types are supported 
            at this time.
            
            NOTE: this method may be invoked explicitly by outside entity, 
            or will be invoked implicitly upon adding the first request; 
            implicit invocation uses data of added request object.
        """
    def create_secure_socket(family, stype):
        """
            Create secure socket connection.
            
            NOTE: this method is invoked internally by setup_connection 
            method to setup connections for HTTPS type connections.
        """
    def secure_connect(addr):
        """
            Connect to server over secure connection.
            
            NOTE: this method is invoked interally by setup_connection 
            when handling HTTPS type connections.  It is called instead of 
            default 'connect' method.
        """
    def refill_buffer():
        """
            Refill outgoing producer data structures so more data is 
            made available for sending.
            
            NOTE: this method extends super class asynchat.async_chat's
            refill buffer method.  It is invoked automatically by superclass 
            as needed, and first pushes any pending requests producers 
            onto outgoing data strucuture before invoking superclass's method.
        """
    def found_terminator():
        """
            Notify channel that current terminator has been found 
            in incoming data.
            
            NOTE: this method is invoked automatically by superclass.
        """
    def collect_incoming_data(data):
        """
            Handle new incoming data being read from connection.
            
            NOTE: this method is invoked automatically by superclass.
        """
    def handle_connect():
        """
            Handle connection event.  Indicates that socket not previsouly 
            connected is now connected.  May occur directly as result of call 
            to 'connect' method, or at a later time when the socket being 
            connected indicates it is readable; this means connection process 
            is complete.
        """
    def handle_write ():
        """
           Callback invoked on channel indicating that socket may now 
           be written to without blocking.  This method is invoked after a 
           channel which indicated it was 'writable' has become able to 
           accept data.  At this point the channel should begin 
           sending data to socket. 
        """
    def send(data):
        """
            Send data 'data' over socket.  Data should be of type 
            string, socket is able to accept incoming data.
            
            NOTE: this is invoked internally by superclass following 
            handle_write invocation.
        """
    def handle_read():
        """
           Callback invoked on channel indicating that socket may now 
           be read from without blocking.  This method is invoked after a 
           channel which indicated it was 'readable' has been sent data and 
           may be read.  The channel should receive data from socket.
        """
    def close():
        """
        """
    def handle_error():
        """
        """
