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
import time
import os
from select import select
from popen2 import Popen4
from mpx import properties
from mpx.lib.threading import Thread
from mpx.lib.threading import Lock
from mpx.lib.scheduler import scheduler
from mpx.lib.configure import set_attribute, get_attribute, \
     map_to_seconds, map_from_seconds, map_from_attribute, map_to_attribute
from mpx.lib.node import ConfigurableNode, as_node
from mpx.lib import msglog
from mpx.lib.exceptions import EAlreadyRunning
import moab.linux.lib.process as process


##
# Class to manage support for dynamic DNS.
#
class DynDNSManager( ConfigurableNode ):
    def __init__( self ):
        ConfigurableNode.__init__( self )
        self.isRunning = 0
        self.ipcheck_pid = 0
        self._lock = Lock()
        self.thread = None
        self.first_time = 0
        self.log_name = 'broadway'
        self.update_count = 0
            
    def _is_debug( self ):
        if self.__dict__.has_key( 'debug' ):       
            if self.debug:
                return 1
        return 0

    def msglog( self, msg ):
        if self._is_debug():       
            msglog.log( self.log_name, msglog.types.DB, msg )
                
    def configure( self, config_dict ):     
        ConfigurableNode.configure( self, config_dict )
        set_attribute( self, 'enable', 0, config_dict, int )
        set_attribute( self, 'debug', 0, config_dict, int )
        
        set_attribute( self, 'ddns_service', 0, config_dict )
        set_attribute( self, 'ddns_acct', 0, config_dict )
        set_attribute( self, 'ddns_pswd', 0, config_dict )
        set_attribute( self, 'host_name', 0, config_dict )
        map_to_attribute( self, 'period', 0, config_dict, map_to_seconds )
        
    def configuration( self ):
        config_dict = ConfigurableNode.configuration( self )
        get_attribute( self, 'enable', config_dict )
        get_attribute( self, 'debug', config_dict )
        
        get_attribute( self, 'ddns_service', config_dict )
        get_attribute( self, 'ddns_acct', config_dict )
        get_attribute( self, 'ddns_pswd', config_dict )
        get_attribute( self, 'host_name', config_dict )
        map_from_attribute( self, 'period', config_dict, map_from_seconds )
        
        return config_dict

    def start( self ):
        if self.enable:
            msglog.log( self.log_name, msglog.types.INFO,
                        "STARTING %s, period = %d" % (self.name, self.period) )
            if not self.isRunning:
                self.isRunning = 1
                 # Wait for a bit to give time for a possible PPP connection
                 # to be brought up.
                scheduler.seconds_from_now_do( 90, self.go )
            else:
                raise EAlreadyRunning

    def stop( self ):
        if self.isRunning:
            if self.ipcheck_pid:
                os.kill( self.ipcheck_pid, signal.SIGKILL )
            self.isRunning = 0

    def go( self ):
        # Lock here
        self._lock.acquire()
        try:
            if self.thread and self.thread.isAlive():
                # Don't do it!
                return
            self.thread = Thread( name = self.name, target = self._complete, args = () )
            self.thread.start()
        finally:
            self._lock.release()
       
    def _complete( self ):
        try:
            self._ipcheck()
        except:
            msglog.exception()
            
        if self.isRunning and self.period:
            # Schedule another run in self.period seconds
            scheduler.seconds_from_now_do( self.period, self.go )

    def _ipcheck( self ):
        cmd = 'ipcheck -p ' + properties.ETC_DIR
        # Ignore errors the first time after startup.
        if self.update_count == 0:
            cmd += ' -e'
        if self._is_debug():
            cmd += ' -dv'
        cmd += ' %s %s %s' % (self.ddns_acct, self.ddns_pswd, self.host_name)

        # Start the ip checker
        self.msglog( "running %s" % cmd )
        child = Popen4( cmd )
        self.ipcheck_pid = child.pid
        outfile = child.fromchild
        
        # Wait for ip checker to finish.  Log any output in the message log.
        while 1:
            result = select( [outfile], [], [], 3.0 )
            if result[0]:
                lines = outfile.readlines()
                for line in lines:
                    self.msglog( line )
            status = child.poll()
            if not status == -1:
                break
        self.ipcheck_pid = 0
        
        if os.WIFEXITED( status ):
            exit_code = os.WEXITSTATUS( status )
            self.msglog( 'ipcheck exit status = %d' % exit_code )
        else:
            self.msglog( 'ipcheck forcibly stopped, status = %d' % status )
            
        self.update_count += 1
            
    
def factory():
    return DynDNSManager()
