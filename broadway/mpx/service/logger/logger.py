"""
Copyright (C) 2001 2002 2003 2010 2011 Cisco Systems

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
# @import from mpx.service  ServiceNode
#          service_interface ServiceInterface
#
from mpx.service import ServiceNode
from service_interface import ServiceInterface
from log import Log
import mpx.lib
import mpx.lib.log
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.node import Alias

class Logger(ServiceNode):

    ##
    # @author Craig Warren
    # @param config
    # @return None
    def configure(self,config):
        ServiceNode.configure(self,config)
    ##
    # @author Craig Warren
    #   starts the logger service
    # @return None
    def start(self):
        ServiceNode.start(self)
        # this will correctly add the msglog as a child
        #  to the logger.
        if 'msglog' not in self.children_names():
            columns = mpx.lib.msglog.get_columns()
            log = Log()
            log.configure({'name':'msglog', 'parent':self})
            for c in columns:
                column = mpx.lib.factory('mpx.service.logger.column')
                config = c.configuration()
                config['parent'] = log
                column.configure(config)
        self._logs = PersistentDataObject(self)
        self._logs.names = []
        self._logs.load()
        for name in self._logs.names:
            if ((not mpx.lib.log.log_exists(name)) and 
                (name not in self.children_names())):
                log = mpx.lib.log.log(name)
                log.destroy()
                del(log)
        self._logs.names = []
        for child in self.children_nodes():
            if not isinstance(child, Alias):
                # Don't manage other managers' logs...
                self._logs.names.append(child.name)
        self._logs.save()

    ##
    # @author Craig Warren
    #   stops the logger service
    # @return None
    def stop(self):
        return ServiceNode.stop(self)

    ##
    # @author Craig Warren
    # @param log_name
    #   the name of the log to return
    # @return Log
    #   returns the log if it can't find the log it
    #   returns None
    def get_log(self,log_name):
        for child in self.children_nodes():
            if child.name == log_name:
                return child
        return None

##
# @author Craig Warren
# @return logger
#  returns and instanciated Logger
def factory():
    return Logger()

        
        
    
