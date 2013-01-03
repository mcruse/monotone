"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
import signal
from popen2 import Popen4
from select import select
from socket import gethostbyname
from os import kill, WIFEXITED, WEXITSTATUS
from tools.lib import os
from mpx import properties
from mpx.lib.threading import Thread
from mpx.lib.threading import Lock
from mpx.lib.scheduler import scheduler
from mpx.lib.event import ConnectionEvent,EventConsumerMixin
from mpx.lib.configure import set_attribute, get_attribute, \
     map_to_attribute, map_from_attribute, map_to_seconds, \
     map_from_seconds, as_boolean
from mpx.lib.node import CompositeNode, as_node
from mpx.lib import msglog
from mpx.lib.exceptions import EAlreadyRunning, ETimeout, EConnectionError, ENoSuchName
from mpx.lib.configure import REQUIRED
from mpx.lib.bacnet.datatype import BACnetTime, BACnetDate
from moab.linux.lib.zoneinfo import set_time

_NODE_TIMESYNCH_BCU   = '/services/time/synch_bcu'

##
# Class to manage synchronization using Network Time Protocol.
#
class BcuTimeSynchronizer( CompositeNode ):
    # This class variable counts the number of nodes that are enabled.
    # The status file is removed when this count is zero.
    nodesEnabled = 0
    
    def __init__( self ):
        CompositeNode.__init__( self )
        self.timeout = 30
        self.isRunning = 0
        self._lock = Lock()
        self.thread = None
        self.fast_adjust_threshold = 600
        self.adjust_threshold = 15
        self.nudge_amount = 1
        self.adjustment = 0 #+/-/0 amount of adjustment
        self.period = 60
        self.bcu_time_node = None
        self.bcu_date_node = None
        self.debug = 0
        self.enabled = 0
        
    def _is_debug( self ):
        if self.__dict__.has_key( 'debug' ):       
            if self.debug:
                return 1
        return 0

    def msglog( self, msg ):
        if self._is_debug():       
            msglog.log( 'broadway', msglog.types.DB, msg )
                
    def configure( self, config_dict ):     
        CompositeNode.configure( self, config_dict )
        set_attribute( self, 'enabled', 0, config_dict, int )
        set_attribute( self, 'debug', self.debug, config_dict, int )
        set_attribute( self, 'period', self.period, config_dict, int )
        set_attribute( self, 'fast_adjust_threshold', self.fast_adjust_threshold, config_dict, int )
        set_attribute( self, 'adjust_threshold', self.adjust_threshold, config_dict, int )
        set_attribute( self, 'nudge_amount', self.nudge_amount, config_dict, int )
        set_attribute( self, 'bcu_date', REQUIRED, config_dict )
        set_attribute( self, 'bcu_time', REQUIRED, config_dict )
        
    def configuration( self ):
        config_dict = CompositeNode.configuration( self )
        get_attribute( self, 'enabled', config_dict )
        get_attribute( self, 'debug', config_dict )
        get_attribute( self, 'period', config_dict )
        get_attribute( self, 'fast_adjust_threshold', config_dict )
        get_attribute( self, 'adjust_threshold', config_dict )
        get_attribute( self, 'nudge_amount', config_dict )
        get_attribute( self, 'bcu_date', config_dict )
        get_attribute( self, 'bcu_time', config_dict )
        return config_dict
    
    def start( self ):      
        msg = "Starting %s, period = %d" % (self.name, self.period)
        msglog.log( 'broadway', msglog.types.INFO, msg)            
        if not self.isRunning:
            self.isRunning = 1
            self._period = self.period
            self._schedule()
        else:
            raise EAlreadyRunning
    
    def _schedule( self ):        
        scheduler.seconds_from_now_do( self._period, self.go )

    def stop( self ):
        if self.isRunning:
            self.isRunning = 0

    def go( self ): #spin off a thread to allow _synchronize to run at its own pace
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
            self._synchronize()
        except:
            if self.debug: print '_complete exception'
            msglog.exception()
            
        if self.isRunning and self.period:
            self._schedule()
        #and terminate thread

    def _synchronize( self ):        
        bcu_date, bcu_time = self._get_bcu_time() #date tuple and seconds
        # get system and bcu times
        system_date, system_time = self._get_system_time() 
        #only adjust time when system time is outside the range of 11pm to 3am
        #this is to prevent any funny business around midnight or daylight savings changeovers
        #also avoids having to deal with modulo math comparisons around midnight
        if system_time > 82800: return #it's after 11pm
        if system_time < 12600: return #it's before 3:30am

        time_error = bcu_time - system_time
        if self.debug: print 'time error is: ', time_error
        if bcu_date != system_date:
           time_error = self.fast_adjust_threshold + 1 #force big time error update 

        # if big time error, just force the system time to the bcu time
        if abs(time_error) > self.fast_adjust_threshold:
            if self.debug: print 'big time error'
            self.adjustment = 0
            self.msglog( 'Timesync to BCU due to large error: %d' % bcu_time )
            self._set_system_time(bcu_date, bcu_time)
            return

        # if the error has difted too far, nudge the system time back towards the bcu time
        if time_error > self.adjust_threshold:
            if self.debug: print 'mediator time is too slow'
            self.adjustment = self.nudge_amount + 2 #it takes about 1.something seconds to set the time
        elif time_error < -self.adjust_threshold:
            if self.debug: print 'mediator time is too fast'
            self.adjustment = -self.nudge_amount

        # test for adjustment in progress and if it's time to stop nudging the time
        if (self.adjustment > 0):
            if system_time > bcu_time:
                self.adjustment = 0
        elif (self.adjustment < 0):
            if system_time < bcu_time:
                self.adjustment = 0

        if (self.adjustment != 0):
            self.msglog( 'Timesync to BCU due to small error: %d' % time_error )
            self._set_system_time(system_date, system_time + self.adjustment)
            self._period = 5
        else:
            self._period = self.period

        # nudge system time towards bcu time.
        # max nudge is X unless error is greater than Y then slam it (should only happen rarely)
        # if nudging time back, never nudge more than Z
        # never set time around midnight 
    def _get_system_time( self ):
        y, m, d, hour, min, second, wday, yday, isdst = time.localtime()
        if self.debug: print 'get localtime', y, m, d, hour, min, second, wday, yday, isdst
        return ((m, d, y), hour * 3600 + min * 60 + second)
    def _set_system_time( self, mmddyyyy, seconds ):
        seconds = int(seconds)
        ss = seconds % 60
        mm = (seconds % 3600) / 60
        hh = (seconds / 3600)
        hhmmss = [hh, mm, ss]
        if self.debug: print 'set time: ', hh, mm, ss
        set_time( mmddyyyy, hhmmss, None )
        
    def _get_bcu_time( self ):
        if self.debug: print 'get bcu time'
        if self.bcu_time_node is None:
            self.bcu_time_node = as_node(self.bcu_time)  #could test classes etc
        if self.bcu_date_node is None:
            self.bcu_date_node = as_node(self.bcu_date)
        y, m, d, dwk = self.bcu_date_node.get(1).value.value #should be date list
        hour, min, second, hundreths = self.bcu_time_node.get(1).value.value #should be time list
        answer = ((m, d, y), hour * 3600 + min * 60 + second)
        if self.debug: print 'bcu time', y, m, d, dwk, hour, min, second, hundreths
        return answer
    
    
def factory():
    return BcuTimeSynchronizer()
