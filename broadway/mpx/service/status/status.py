"""
Copyright (C) 2002 2003 2005 2006 2008 2010 2011 Cisco Systems

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

from moab.config_service._config_service import _get_hostname, _get_serial
from moab.config_service._config_service import _read_from_proc
from moab.linux.lib.statusled import StatusLED
from moab.linux.lib.uptime import secs

from mpx import properties as P
from mpx.lib import msglog
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.exceptions import EAlreadyRunning, EInvalidValue
from mpx.lib.ifconfig import mac_address
from mpx.lib.node import CompositeNode
from mpx.lib.scheduler import scheduler

##
# Node to manage the mediator's status LED.
#
class StatusNode(CompositeNode, StatusLED ):
    def __init__( self ):
        CompositeNode.__init__( self )
        StatusLED.__init__( self )

        self.stateDict = { 'idle'      : self.setIdle,
                           'installing': self.setInstalling,
                           'running'   : self.setRunning,
                           'error'     : self.setError,
                           'panic'     : self.setPanic }

        self.isStarted = 0
        self.stateName = ''
        self.stateSetFunction = None
        self.sched_id = None

    def _is_debug( self ):
        if self.__dict__.has_key( 'debug' ):
            if self.debug:
                return 1
        return 0

    def _msglog( self, msg ):
        if self._is_debug():
            msglog.log( 'broadway.mpx.service.status', msglog.types.DB, msg )

    def configure( self, config_dict ):
        CompositeNode.configure( self, config_dict )
        set_attribute( self, 'debug', 0, config_dict, int )


    def configuration( self ):
        config_dict = CompositeNode.configuration( self )
        get_attribute( self, 'debug', config_dict )
        return config_dict

    def start( self ):
        if not self.isStarted:
            self.set( 'running' )
            self.isStarted = 1
            self._schedule()
        else:
            raise EAlreadyRunning
        return CompositeNode.start( self )

    # Dummy arg is required by scheduler.
    def _schedule( self, dummy = None ):
        self._msglog( 'setting led, state = %s' % self.stateName )
        apply( self.stateSetFunction, [] )
        if self.isStarted:
            self.sched_id = scheduler.seconds_from_now_do( 50, self._schedule, None )

    def stop( self ):
        if self.sched_id:
            scheduler.cancel( self.sched_id )
            self.sched_id = None
        self.set( 'idle' )
        self.setIdle()
        self.isStarted = 0

    def set( self, stateName ):
        _stateName = stateName.lower()
        if self.stateDict.has_key( _stateName ):
            self.stateName = _stateName
            self.stateSetFunction = self.stateDict[_stateName]
            if self.isStarted and self.sched_id:
                scheduler.cancel( self.sched_id )
                self._schedule()
        else:
            msg = "valid states are one of %s" % repr( self.stateDict.keys() )
            raise EInvalidValue( 'state name', stateName, msg )

    def get( self, skipCache=0 ):
        return self.stateName



class MoeVersionNode(CompositeNode):
    def get(self, skup=0):
        return P.MOE_VERSION

class FWVersionNode(CompositeNode):
    def get(self, skip=0):
        version = P.PRODUCT_VERSION
        if not version:
            version = P.COMPOUND_VERSION 
        return version
    
class SerialNumberNode(CompositeNode):
    def get(self, skip=0):
        return P.SERIAL_NUMBER

class LastStartTimeNode(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.time = time.strftime('%X %x %Z')
    def get(self, skip=0):
        return self.time

class HostnameNode( CompositeNode):
    def get(self, skipCache=0):
        return _get_hostname()

class KernelVersionNode( CompositeNode):
    def get(self, skipCache=0):
        return _read_from_proc('version')

class UptimeNode( CompositeNode):
    def get(self, skipCache=0):
        return secs()

class UptimeAtFrameworkStartNode( CompositeNode):
    def __init__(self):
        self.uptime_at_framework_start = secs()

    def get(self, skipCache=0):
        return self.uptime_at_framework_start

class MacAddress(CompositeNode):
    def configure(self, cd):
        super(CompositeNode, self).configure(cd)
        set_attribute(self, 'mac', 0, cd, int)
        return

    def configuration(self):
        cd = super(CompositeNode, self).configuration()
        get_attribute(self, 'mac', cd)
        return cd

    def get(self, skipCache=0):
        return mac_address("eth%d" % self.mac)
