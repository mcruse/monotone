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
# Refactor 2/11/2007
from mpx.componentry import Interface
from mpx.componentry import Attribute

class ITriggerManager(Interface):
    """
        Mainly a marker interface intended for adaption for
        web interaction.  Some convenience functions are provided,
        but could easily be skipped through the use of appropriate
        children_nodes, children_names, etc., functions.
    """

    def get_triggers():
        """
            Return a list of all triggers in this container.
        """

    def get_trigger(name):
        """
            Return trigger named 'name'.
        """

    def add_trigger(trigger):
        """
            Add trigger 'trigger' to the container.
        """

    def remove_trigger(trigger):
        """
            Remove trigger 'trigger' from list of triggers
            contained by container.
        """

    def get_trigger_names():
        """
            Return list of names of triggers contained in
            container.
        """

class ITrigger(Interface):
    state = Attribute("""
        EnumeratedValue instance that is currently this trigger's state.
    """)
    targets = Attribute("""
        List of Alarm nodes which are registered to be triggered and cleared
        by this trigger.
    """)

    def is_active():
        """
            Boolean indicator with value true if this trigger is currently
            True and false otherwise.
        """

    def is_running():
        """
            Returns true if Trigger has been started; false otherwise.
        """

    def get_state():
        """
            Return state attribute.
        """

    def __call__():
        """
            Perform evaluation of trigger condition, and generate
            TriggerActivated/TriggerCleared events in manager
            if state has changed.
        """

    def add_target(target):
        """
            Append target 'target' to list of targets for this trigger.
        """

    def remove_target(target):
        """
            If target 'target' is in targets, remove it.
        """

    def get_targets():
        """
            Return copy of this trigger's targets list.
        """

class IComparisonTrigger(ITrigger):
    """
        Marker interface to differentiate trigger types.
    """

