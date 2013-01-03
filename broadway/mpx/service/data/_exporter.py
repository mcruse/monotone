"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import time

from mpx.service import ServiceNode, SubServiceNode
from mpx.lib.configure import REQUIRED, set_attribute, \
     get_attribute, as_boolean
from mpx.lib.node import as_node, as_node_url
from mpx.lib import thread, pause
from mpx.lib.exceptions import ENotImplemented,EInvalidValue,EConfiguration

##
# Interface for all data exporters.  Data exporters
# export data from the log file that is their parent.
# Exporters use a formatter to format log information
# and transporters to transport the formatted data.
#
class Exporter(ServiceNode):
    def __init__(self):
        ServiceNode.__init__(self)
        self.running = 0
        self.formatter = None
        self.transporter = None
    
    def configure(self, config):
        ServiceNode.configure(self, config)
        set_attribute(self, 'log', self.parent.parent, config, as_node)
        set_attribute(self, 'gm_time', 1, config, as_boolean)
        self.time_function = time.localtime
        if self.gm_time:
            self.time_function = time.gmtime
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self, 'log', config, as_node_url)
        get_attribute(self, 'gm_time', config, str)
        return config
    def start(self):
        for child in self.children_nodes():
            if isinstance(child,Formatter):
                if self.formatter is not None:
                    raise EConfiguration('Can only have one formatter')
                self.formatter = child
            elif isinstance(child,Transporter):
                if self.transporter is not None:
                    raise EConfiguration('Can only have one transporter')
                self.transporter = child
        if self.formatter is None or self.transporter is None:
            raise EConfiguration('Exporter one formatter '
                                 'and one transporter child')
        return ServiceNode.start(self)
    def stop(self):
        self.formatter = None
        self.transporter = None
        return ServiceNode.stop(self)
    def _export(self):
        raise ENotImplemented

##
# Interface for all formatters.  Formatters
# take data in the form of a log slice, a
# list of dictionaries, and format the data
# and return it as a string.
#
class Formatter(SubServiceNode):
    MIME_TYPE='text/plain'
    ##
    # Function call to format a list of dictionaries.
    #
    # @param data  List of dictionaries containing data
    #              to be formatted.
    # @return string containing formatted data.
    #
    def format(self, data):
        raise ENotImplemented

##
# Interface for all transporters.  Transporters
# take data as a string and transport it.  Typical
# transporters might send the data over a network connection,
# like FTP, or write the data to a file.
#
class Transporter(SubServiceNode):
    ##
    # Function for sending data.
    #
    # @param data  String containing data
    #              to be transported.
    #
    def transport(self, data):
        raise ENotImplemented
