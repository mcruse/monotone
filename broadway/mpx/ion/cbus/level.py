"""
Copyright (C) 2008 2010 2011 Cisco Systems

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

from mpx.lib import Result

from mpx.lib.node import Node

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import set_attributes, get_attributes, as_boolean

from mpx.lib.exceptions import EInvalidMessage
from mpx.lib.exceptions import EInvalidValue

class Level(Node):
    __node_id__ = "eefc556a-0a6d-4a4b-b577-33a955bf23d1"
    def __init__(self):
        Node.__init__(self)
        self._cbus = None
        self._app = None
        self._grp = None
        return
    def _get_cbus(self):
        return self.parent._get_cbus()
    def _get_app(self):
        return self.parent._app
    def _get_grp(self):
        return self.parent.group
    def configure(self,config):
        Node.configure(self,config)
        # set_attribute(self, '', REQUIRED, config, int)
        return
    def configuration(self):
        config = Node.configuration(self)
        # get_attribute(self, '', config)
        return config
    def start(self):
        self._cbus = self._get_cbus()
        self._app = self._get_app()
        self._grp = self._get_grp()
        Node.start(self)
        return
    def stop(self):
        Node.stop(self)
        self._cbus = None
        self._app = None
        self._grp = None
        return
    def get_result(self, skipCache=0):
        return Result(self.get(), time.time(), 0, 0)
    def get(self, skipCache=0):
        result = self._cbus.blocking_command("Ga=%s,g=%g\n" % (self._app,
                                                               self._grp))
        for line in result:
            name, value = line.split(":")
            return int(value)
        raise EInvalidMessage(result)
    def set(self, value, asyncOK=1):
        level=int(value)
        if level < 0 or level > 255:
            raise EInvalidValue('level', value,
                                "The level must be between 0 and 255")
        result = self._cbus.blocking_command(
            "Sa=%s,g=%g,l=%s\n" % (self._app,
                                   self._grp,
                                   level)
            )
        return
