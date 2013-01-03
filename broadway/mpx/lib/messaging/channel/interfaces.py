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
Undefined = object()

class IMessageListener(Interface):
    def handle_message(message):
        """
            Accept incoming message from channel to which 
            listener has subscribed.
        """

class IDestinationRegistry(Interface):
    def has_destination(destspec):
        """
            Does registry contain IDestination named 'name'?
        """
    def get_destination(destspec, default=Undefined):
        """
        """
    def get_destinations():
        """
        """
    def add_destination(destination):
        """
        """
    def pop_destination(destspec):
        """
        """

class IDestination(Interface):
    """
        Addressable resource of messaging system.
    """
    def __init__(name):
        """
           Create instance named 'name'. 
        """
    def getname():
        """
            Get label (URI) uniquely identifying destination.
        """

class IMessageChannel(IDestination):
    """
        Base Channel interface.  
        
        Channels serve to decouple publishers and consumers 
        within a system or network.  Rather than invoking 
        or notifying a component directly, a channel based 
        architecture inserts the channel component between 
        each component.  As a result, publishers only need to 
        understand publishing messages into a channel; and 
        consumers only need to understand receiving messages 
        from channels.  Most processor components are both 
        publishers and consumers.
        
        The use of channels between components which consume 
        messages from channels, and publish messages to channels, 
        allows a system, or set of systems, to be constructed 
        using a pipes & filters architecture.  In such an 
        architecture, channels act as the pipes, and processors 
        act as the filters.
        
        Note that the term "filter" in a pipes & filters 
        architecture, does not imply that the processor 
        literally filters information it is receiving.  I 
        don't recall why the term was used, but it implies 
        only that component consumes input, processes the 
        input, and outputs the results.
    """
    def send(message):
        """
            Send Message instance 'message' over channel.
        """
    def receive(blocking=True, timeout=None):
        """
            Get Message instance from channel, blocking 
            until one arrives if 'blocking' is True, or 
            blocking until 'timeout' seconds have transpired 
            if blocking and non-None timeout.
        """
    def attach(listener):
        """
            Start notifying message listener 'listener' of 
            incoming messages.
        """
    def detach(listener):
        """
            Stop notifying message listener 'listener' of 
            incoming messages.
        """
    def subscribe(channel):
        """
            Start sending Channel 'channel' incoming Messages. 
        """
    def unsubscribe(channel):
        """
            Stop sending Channel 'channel' incoming Messages. 
        """
    def full():
        """
        """
    def empty():
        """
        """
    def notify():
        """
            Notify listeners and subscribers of incoming Messages.
            
            Implementation depends upon Channel subtype.
        """

class IMessageQueue(IMessageChannel):
    """
        Standard Message Queue Interface definition.
        
        This API extends the base-Channel interface by 
        providing a synchronous get method, which 
        callers can invoke to get the next message from 
        the queue; and also by extending a couple existing 
        methods.
        
        The subscribe method is extended to automatically 
        notify a subscriber of pending messages if that 
        subscriber happens to be the only subscriber on 
        the channel.
        
        A Message Queue enqueues incoming messages to 
        be retrieved explicitly, and synchronously.  
        Listeners may also subscribe for automatic 
        notification, using the API defined by the base 
        channel interface.
        
        Regardless of how a subscriber gets messages from a 
        message queue, a defining characteristic of the 
        message queue construct is that each message sent 
        to the queue will be consumed by no more than one 
        consumer.
        
        When multiple consumers share a single Message 
        Queue, those consumers are "competing consumers."
        When this is done via registration, each consumer 
        is passed a message in a roughly round-robin manner.
        There is no guarantee the round-robin will be exact, 
        but the mechanism is relatively consistent, especially 
        when dealing with a fairly static set of registered 
        consumers.
        
        Messages sent to a Message Queue remain there until 
        they are consumed.  If there are no registered listeners, 
        no messages are removed automatically.
    """
    # Redeclared methods provided to describe type-specific 
    # extensions to method semantics.
    def attach(listener):
        """
            Add listener to set of listeners.
            
            Invokes notify following registration, so 
            that queued messages are sent if listener is 
            only subscriber.
        """
    def notify():
        """
            Send each queued message to a listener.
            
            If no listeners are registered, the message 
            if left on the queue.  If multiple listeners 
            are registered, each will be selected and in 
            round-robin fashion, and sent a single message.
            Notification continues as long as listeners are 
            registered, and messages are on queue.
        """

class IMessageTopic(IMessageChannel):
    """
        Standard Publish-Subscribe, or Topic, channel 
        interface definition.
        
        This interface redefines the base-channel's notify 
        method to clarify semantics.  The publish-subscribe 
        channel construct delivers incoming messages to 
        all registered listeners.  The first listener typically 
        gets the original message, while subsequent listeners 
        get copies of that message.  Message sent while 
        no listeners are registered, are permanently lost by 
        the channel.  Unlike queues, publish-subscribe channels 
        remove messages from the channel, regardless of whether 
        or not there are consumers to get the message.
    """
    def publish(message):
        """
            Type specific alias for 'send' method. 
        """
    # Redeclared methods provided to describe type-specific 
    # extensions to method semantics.
    def receive(blocking=True, timeout=None):
        """
            Blocking receive call as described in general 
            API above.
            
            Noted again here to explain that non-blocking 
            invocations are essentially meaningless in the 
            context of a publish-subscribe channel.  Because 
            publish-subscribe channels do not enqueue messages, 
            no messages are ever awaiting receive invocations.
        """
    def notify():
        """
            Send each queued message to all listeners. 
            
            For each message in queue, a copy is sent to 
            every registered listener.
        """
















