"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx.lib.scheduler import scheduler
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import CompositeNode
from mpx.lib.exceptions import EAlreadyRunning, EInvalidValue

##
# Node to monitor the mediator's resources
#
class ResourceNode( CompositeNode ):
    def __init__( self ):
        CompositeNode.__init__( self )
        self.isStarted = 0
        self.sched_id = None
        
    def configure( self, config_dict ):     
        CompositeNode.configure( self, config_dict )
        set_attribute( self, 'debug', 0, config_dict, int )
        # Default the period (between tickling our children) to 15
        # seconds.  Note:  This may be overriden for specific
        # applications.
        set_attribute( self, 'period', 15, config_dict, int)
    def configuration( self ):
        config_dict = CompositeNode.configuration( self )
        get_attribute( self, 'debug', config_dict )
        get_attribute( self, 'period', config_dict, int)
        return config_dict

    def start( self ):
        CompositeNode.start( self )
        if not self.isStarted:
            self.isStarted = 1
            self._schedule()
        else:
            raise EAlreadyRunning
        
    def stop( self ):
        CompositeNode.stop( self )
        if self.sched_id:
            scheduler.cancel( self.sched_id )
            self.sched_id = None
        self.isStarted = 0
        
    # Dummy arg is required by scheduler.
    def _schedule( self, dummy = None ):
        if self.isStarted:
            # Wake up every period seconds and tickle our children so that they can keep
            # on top of resource usage.
            self.sched_id = scheduler.seconds_from_now_do( self.period, self._schedule, None )
            for x in self.children_nodes():
                if hasattr(x, 'tickle'):
                    x.tickle()

def factory():
    return ResourceNode()
