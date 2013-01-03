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

class IExporterContainer(Interface):
    """
        Mainly a marker interface intended for adaption for
        web interaction.  Some convenience functions are provided,
        but could easily be skipped through the use of appropriate
        children_nodes, children_names, etc., functions.
    """

    def get_exporters():
        """
            Return a list of all exporters in this container.
        """

    def get_exporter(name):
        """
            Return exporter named 'name'.
        """

    def add_exporter(exporter):
        """
            Add exporter 'exporter' to the container.
        """

    def remove_exporter(exporter):
        """
            Remove exporter 'exporter' from list of exporters
            contained by container.
        """

    def get_exporter_names():
        """
            Return list of names of exporters contained in
            container.
        """

class IAlarmExporter(Interface):
    """
        Instances catch events from specific alarms and exports
        a string representation of those events using the assigned
        formatter to determine the formatting of the payload, and the
        assigned transporter to actually transfer the payload.

        Any number of alarms may be exported by this exporter.
    """

    name = Attribute("""
        Named used by alarms to identify exporter.
    """)

    description = Attribute("""
        Brief description of exporter to assist configuration.
    """)

    alarms = Attribute("""
        Dictionary of alarm objects being exported by this exporter,
        and the dispatcher subscription for catching that event.
    """)

    def add_alarm(alarm):
        """
            Add alarm 'alarm' to list of alarms whose
            events will be exported by this exporter.
        """

    def remove_alarm(alarm):
        """
            Remove alarm 'alarm' from list of alarms to be
            exported by this exporter.
        """

    def export(event):
        """
            Export data associated with alarm event 'event.'
        """

    def get_formatter():
        """
            Return reference to this exporter's formatter.
        """

    def get_transporter():
        """
            Return reference to this exporter's transporter.
        """

    def set_formatter(formatter):
        """
            Set formatter for this exporter.  Note, previous
            formatter will be deleted if one is already configured.
        """

    def set_transporter(transporter):
        """
            Set transporter for this exporter.  Note, previous
            transporter will be deleted if one is already configured.
        """

class ITransporter(Interface):
    """
        Instances may be used by exporter objects to transport data
        provided as a string to some preconfigured recipient service.
    """

    def transport(data):
        """
            Perform actual transfer.
        """

class IAlarmFormatter(Interface):
    """
        Instances may be used by exporter objects to convert an alarm
        event into a string representation suitable for transport.
    """

    def format(event):
        """
            Use information contained in event 'event' to
            generate an appropriate string description of event
            'event' and return it.
        """
