"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
##
# @todo Maintain some turbine state (specifically password mode via prompt_type).
#       Add UNKNOWN port + BASE PromptType as default state?
# @todo Move default timeout to the response class???

from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute

class EOutOfSync(Exception):
    def __init__(self,oops):
        Exception.__init__(self,oops)

##
# Line Handler for Capstone Micro-Turbines.
#
class LineHandler(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
    
    ##
    # Lock port this line-handler is on
    # for safe access.
    #
    def lock(self):
        self.port.lock()

    ##
    # Unlock port this line-handler is on to
    # allow access.
    #
    def unlock(self):
        self.port.unlock()

    ##
    # Configure Object.
    #
    # @param config  Configuration dictionary.
    # @key timeout  Time to wait before timing out on port
    #               commmands.
    # @default 1.0
    # @key debug  Run in debug mode.
    # @default 0
    #
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'timeout', 1.0, config, float)
        set_attribute(self, 'debug', 0, config, int)
        self.port = self.parent
        if not self.port.is_open():
            self.port.open()

    ##
    # Get object's configuration.
    #
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'timeout', config, str)
        get_attribute(self, 'debug', config, str)
        return config

    ##
    # Send a command through the port.
    #
    # @param cmd  <code>Command</code> object to send.
    # @return Response to <code>cmd</code>
    #
    def command(self,cmd):
        try:
            self.lock()
            self.port.drain()
            cmd.send(self.port)
            self.port.flush()
            response = cmd.response_factory()
            response.receive(self.port, self.timeout)
        finally:
            self.unlock()
        return response

def factory():
    return LineHandler()
