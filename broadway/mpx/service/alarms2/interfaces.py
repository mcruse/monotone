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
# Refactor 2/11/2007
from mpx.componentry import Interface
from mpx.componentry import Attribute
from mpx.componentry.interfaces import IOrderedCollection
from mpx.lib.eventdispatch.interfaces import IEvent

class IAlarmEventSource(Interface):
    name = Attribute('Name of Alarm which produced AlarmEvent.')
    priority = Attribute('Priority assigned to Alarm.')
    description = Attribute('Description given to Alarm.')

class IAlarmEvent(IEvent):
    current_event = Attribute("""
        Reference to current state's StateChangedEvent instance.""")

    state = Attribute("""
        String giving name of current state.""")

    history = Attribute(
        """
            List of all previous, but no longer active, StateChangedEvent
            instances.  Last StateChangedEvent to be current is last
            item in list.

            NOTE: This is a property that uses method
            'get_history' to protect integrity of actual attribute.
        """)

    def get_history():
        """
            Returns copy of history list, so mutations do not
            affect attribute itself.  This method is used by
            property 'history' as well, so accessing history directly
            also returns a copy that may be modified without affecting
            the original.
        """

    def acknowledge(actuator, timestamp, context):
        """
            Acknowledge the alarm event.  Depending upon the
            alarm event's state, this may cause a state
            change to occur a StateChangedEvent instance
            to be dispatched.
        """

    def get_alarm_event():
        """
            Return a reference to self.
        """

    def handle_event(event):
        """
            Meant to be called by dispatchers as result of
            event registration; not typically going to be
            called by external sources.
        """

    def notify(command, *args, **kw):
        """
            This method invokes one of this object's other methods.
            Parameter 'command' should be a string which specifies
            the name of one of this object's other methods.
        """

    def synchronize(history):
        """
            Synchronize this event's state, and therefore its
            history, with the list of events passed in.  To be
            used when synchronizing an AlarmEvent with information
            from a remote event.
        """

    def is_state(state):
        """
            Returns boolean indication whether or not this events
            current state is equal to 'state' param.  Param is
            string representation of state name, may be either upper
            or lower.
        """

class IAlarm(IAlarmEventSource):
    dispatcher = Attribute("""Alarm's own dispatcher for use
                              primarily by AlarmEvents it produces.""")
    def trigger(source, time, context, information=None, *args, **keywords):
        """
            Function allows any object to trigger alarm, causing
            the Alarm to create and generate an AlarmEvent.  Caller
            must pass reference to itself, the time associated with
            alarm detection, the context within which the alarm condition
            was determined, and can pass additional information to
            be associated with alarm event.

            Note: Uses internal dispatcher--self.dispatcher--to dispatch
            AlarmTriggeredEvent as result of this call.  Prior to dispatching,
            a new AlarmEvent is instanciated which will be the catcher of
            this TriggeredEvent.
        """
    def clear(source, time, context, information=None, *args, **keywords):
        """
            Clear triggered alarm.  Function will
            likely cache clear information for active alarm,
            or notify active alarm of cleared status.
        """
    def get_event(id):
        """
            Returns AlarmEvent with GUID 'id'.
        """
    def get_events():
        """
            Returns list of all AlarmEvent instances.
        """
    def events_by_state(state, negate = False):
        """
            Retreive events by any state 'state'; or
            retrieve all events not in state 'state' by
            passing True for 'negate'.

            NOTE: This method is used mostly internally as
            shortcut methods are provided for each possible
            query as well.
        """

    def get_raised():
        """
            Return list of raised alarms.
        """

    def get_accepted():
        """
            Return list of acknowledged alarms.
        """

    def get_cleared():
        """
            Return list of cleared but not acknowledged
            alarms.
        """

    def get_closed():
        """
            Return a list of closed AlarmEvents.
        """

    def get_not_raised():
        """
            Return list of alarm events not in state raised.
        """

    def get_not_accepted():
        """
            Return list of alarm events not in acknowledged state.
        """

    def get_not_cleared():
        """
            Return list of all alarm events not in cleared state.
        """

    def get_not_closed():
        """
            Return a AlarmEvents not in closed state.
        """

    def dispatch(event):
        """
            Dispatch function for AlarmEvents to dispatch
            StateChangeEvents through.  Not to be called
            by anything other than AlarmEvents produced by this
            alarm.
        """

class IAlarmManager(Interface):
    dispatcher = Attribute("""
            Dispatcher to be accessed directly by Alarms and AlarmEvents
            for listening and dispatching semi-private events.

            This Dispatcher's ID is the URL of the Alarm Manager.
        """)
    alarm_dispatcher = Attribute("""
            Dispatcher which exposes the Alarm Event interface
            publicly.

            This Dispatcher's ID is "Alarm Manager".
        """)
    def add_alarm(alarm):
        """
            Add alarm instance 'alarm' under
            name 'name' to list of alarms being managed.
        """
    def remove_alarm(name):
        """
            Remove alarm named 'name' from
            list of alarms being managed.
        """
    def get_alarm(name):
        """
            Get reference to alarm object with name 'name'.
        """
    def get_alarms():
        """
            Get list of all Alarm object being managed.
        """
    def get_alarm_names():
        """
            Return list of alarm names being managed.
        """
    def get_alarm_dictionary():
        """
            Return dictionary of alarms
            being managed.
        """
    def get_local_events():
        """
            Return list of all local events--those events
            produced by alarms defined and residing on this
            host.
        """
    def get_remote_events():
        """
            Return list of all remote events--those events
            produced by other hosts within the cloud, and
            propogated here.
        """
    def get_all_events():
        """
            Return list of all alarm events--returned list
            will include both local and remote events.
        """
    def get_event_dictionary(order_by = 'state', source = 'all'):
        """
            Get dictionary of events.

            If order_by is not provided, or
            is 'state', the dictionary keys will be the state, and the values
            will be lists of events in that state.

            If order_by is 'GUID', the dictionary keys will be the event
            GUID, and the value will be the event.

            If source is not provided or is 'all', the events will include
            both local and remote events.

            If source is 'local' or 'remote', the events will be only those
            events that are local or remote events, respectively.
        """
    def get_events_by_state(state, source = 'all'):
        """
            Returns a list of only those events in state 'state'.

            If 'source' is 'all' or not provided, the events will
            include both local and remote events.

            If 'source' is 'local' or 'remote', the events will
            include only those events that are local or remote,
            respectively.
        """
    def dispatch(*args, **kw):
        """
            Shortcut dispatch method for Alarms to dispatch
            via AlarmManager's dispatcher.
        """
    def register_for_type(*args, **kw):
        """
            Shortcut register method for registering
            with AlarmManager's dispatcher for types of
            events.  Typically will be used to register
            for StateChangedEvents.
        """

class IStateEvent(IEvent):
    name = Attribute("""
        Name of this particular state.""")

    action = Attribute("""Reference to ActionEvent that caused state.""")

    def __init__(alarmevent, actionevent):
        """
            See individual attributes with same
            names for definition of parameters.
        """

    def tostring():
        """
            Return nicely formatted string description of
            this particular state change.
        """

    def get_alarm_event():
        """
            Return reference to AlarmEvent of which
            this is a state.
        """

    def __call__(self, actionevent):
        """
            Return instanctiated and configured event
            appropriate for action 'actionevent' called
            on this state.
        """

class IActionEvent(IEvent):
    timestamp = Attribute("Time at which action was induced.")
    actuator = Attribute("Agent/object responsible for causing event.")
    context = Attribute("Additional information provided by actuator.")

    def __init__(source, timestamp, actuator, context):
        """
            Initialize event encapsulating a particular action
            perpetrated on source 'source'.  Such as calling
            function 'trigger' on an Alarm.
        """

class IFlatAlarmManager(IOrderedCollection):
    """
        Interface for an Alarm Manager that provides list and
        dictionary type access to Alarm Management details.

        See individual functions for details.

        Object implement IOrderedCollection where collection
        alarm alarm events only.
    """
    def get_alarms():
        """
            Return OrdredCollection of Alarm objects.
        """
    def get_alarm(name):
        """
            Return alarm instance with name 'name.'
        """
    def get_alarm_events(alarm_name):
        """
            Return list of all alarm events owned
            by alarm 'alarm_name.'
        """
