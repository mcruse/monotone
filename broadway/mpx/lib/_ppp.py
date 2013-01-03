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
import popen2
import os
import signal 
import select
from mpx import properties
from mpx.lib import msglog, threading, exceptions
from moab.linux.lib.servicemgr import *
from moab.linux.lib.routing import RoutingTable, flag_filename

_PPP_ERRORS = [
"""Normal, successful completion""",
"""An immediately  fatal error of some kind occurred, such as an
essential system call failing,  or  running out of virtual memory.""",
"""An  error was  detected in processing the options given, such
as two mutually exclusive options being used.""",
"""Pppd is not setuid-root and the invoking user is not root.""",
"""The kernel does not support PPP, for example, the PPP kernel
driver is not included or cannot be loaded.""",
"""Pppd terminated because it was sent a SIGINT, SIGTERM or SIGHUP signal.""",
"""The serial port could not be locked.""",
"""The serial port could not be opened.""",
"""The connect script failed (returned a non-zero exit status).""",
"""The command specified as the argument to the pty option could not be run.""",
"""The PPP negotiation failed, that is, it didn't reach the point
where at least one network protocol (e.g. IP) was running.""",
"""The peer system failed (or refused) to authenticate itself.""",
"""The link was established  successfully and terminated because it was idle.""",
"""The link was established successfully and terminated because
the connect time limit was reached.""",
"""Callback was negotiated and an incoming call should arrive shortly.""",
"""The  ink was terminated because the peer is not responding to
echo requests.""",
"""The link was terminated by the modem hanging up.""",
"""The PPP negotiation failed because serial loopback was detected.""",
"""The init script failed (returned a non-zero exit status).""",
"""We failed to authenticate ourselves to the peer.""" ]

#
# Exceptions raised by this module.  All clean up is done before an
# exception is raised.
#
class EPppErrantProcess( exceptions.MpxException ):
    # This exception indicates that the child process spewed more output
    # than expected.
    pass

class EPppConnectionTimedOut( exceptions.MpxException ):
    # This exception indicates that a successful connection could not be
    # established in the time alloted.
    pass

class EPppDeviceLocked( exceptions.MpxException ):
    # This exception indicates that the serial port was locked by another process.
    pass

#
# Constants
#
_MAX_LINES_TO_READ = 100   # Prevents run-away child process
DEFAULT_TIMEOUT = 60       # Number of seconds to wait for the connection to complete.

##
# This object is not thread safe right now!!
class PPP:
    def __del__( self ):
        self._disconnect()
     
    def __init__( self ):
        self._process = None          # Object returned by popen2.Popen4()
        self._is_connected = 0        # 1 if connected, 0 otherwise
        self._lock = threading.Lock() # Lock to make connect/disconnect thread safe

    
    def set_override_default_route( self, value ):
        # If value is 1, then make sure that the flag file does not exist.
        # This will cause ip-up.local to override the default route.  Otherwise,
        # create the flag file which will cause ip-up.local to skip overriding
        # the default route
        if value == 1:
            if os.path.isfile( flag_filename ):
                try:
                    os.remove( flag_filename)
                except:
                    msglog.exception()
        else:
            if not os.path.isfile( flag_filename ):
                try:
                    fd = open( flag_filename, "w" )
                    fd.close()
                except:
                    msglog.exception()
        
    #################################################################################
    #
    # _disconnect
    #
    # Local function to stop the pppd process, thus taking down the ppp connection.
    #
    # Returns:
    #    (status, summary)
    #    Where 'status' is the status code of the child process. The status code
    #    encodes both the return code of the process and information about whether
    #    it exited using the exit() system call or died due to a signal. Functions
    #    to help interpret the status code are defined in the os module; 'summary'
    #    is a list of strings representing the final output from pppd.
    #
    #################################################################################
    
        
    def _disconnect( self ):       
        result = None
        
        # Send ^C. Other options are SIGTERM and SIGKILL, but SIGINT results in
        # a process summary being output before the process exits.
        try:
            os.kill( self._process.pid, signal.SIGINT )                      
            status = self._process.wait()  
            output = self._process.fromchild.readlines()
            result = (status, output)
        except KeyboardInterrupt:
            # This exception is a possible side-effect of SIGINT
            pass
        except Exception, e:
            # self._process.wait()  throws an error often and I don't know why.
            # It would be nice to figure out!! But the process does get killed.
            pass
        self._is_connected = 0
        self._process = None
        return result
    
    
    #################################################################################
    #
    # _connect
    #
    # Local function to start the pppd process, thus bringing up the ppp connection.
    #
    # Parameters:
    #    timeout              - the approx. amount of time, in seconds, to wait for the
    #                           connection to complete.
    #    dialout_options_file - name of options file to use
    #
    # Exceptions raised:    (see descriptions at the top of this module)
    #    EPppErrantProcess,
    #    EPppDeviceLocked,
    #    EPppBadDefaultRoute,
    #    EPppConnectionTimedOut
    # 
    #################################################################################
    def _connect( self, timeout, dialout_options_file, routes ):   
        # Launch pppd to initiate a ppp connection. Superexec is used to ensure that
        # the daemon is not affected by python mucking with process signal handlers.
        pppdcmd = 'superexec pppd nodetach defaultroute file %s' % dialout_options_file
        self._process = popen2.Popen4( pppdcmd )

        # Wait for a successful connection.  Output from pppd usually looks
        # something like what is shown below, except that the warning about
        # the default route is conditional on a pre-existing default route.
        #
        #   chat:  Apr 24 21:12:51 TZ
        #   Serial connection established.
        #   Using interface ppp0
        #   Connect: ppp0 <--> /dev/ttyS1
        #   not replacing existing default route to eth0 [10.0.1.1]
        #   local  IP address 12.65.169.172
        #   remote IP address 12.67.7.56
        #
        # If another instance of pppd is already running, then the new instance
        # will display a message similar to the following and terminate.
        #   Device ttyS1 is locked by pid 229
        #
        infile = self._process.fromchild
        is_default_route_replaced = 1     # optimistic assumption
        lines_read = 0
        seconds_remaining = timeout
    
        while seconds_remaining:
            # Block for at most 1 second waiting for input.  If input is available,
            # then read one line.
            if infile in select.select( [infile], [], [], 1 )[0]:
                line = infile.readline()
 
                # Empty line means EOF, which means that the process terminated
                # prematurely.  Polling the process should return pppd's exit code.
                if not line:
                    result = self._process.poll()
                    if result > 0:
                        result = os.WEXITSTATUS( result )
                        if result < len( _PPP_ERRORS ):
                            raise exceptions.EConnectionError( _PPP_ERRORS[result] )
                    raise exceptions.EConnectionError(
                        "unknown and unexpected error (%d)!" % result )
                
                lines_read += 1
                
                # Bail out if this is a runaway program.
                if lines_read > _MAX_LINES_TO_READ:
                    self._disconnect()
                    raise EPppErrantProcess()
                 
                # Check for locked device
                elif line.find( 'is locked by pid' ) > 0:
                    raise EPppDeviceLocked( line )
                
                # Warning if there was already an existing default route.
                elif line.startswith( 'not replacing existing default route' ):
                    msglog.log( 'broadway.mpx.lib.ppp', msglog.types.INFO, line )
                    break
                
                # Connection complete when the local IP address is displayed.
                # NOTE: It would be preferable to check for the remote address,
                # which is displayed in the the last line, but for some reason
                # the last line isn't flushed to the I/O buffer until the process
                # is terminated.  Go figure.
                elif line.startswith( 'local  IP address' ):
                    break
            else:
                # Timed out.
                seconds_remaining -= 1
        else:
            self._disconnect()
            raise EPppConnectionTimedOut()
        
        # OK, the connection seems to have come up, now try to add
        # any "on-demand" routes which the user has configured.
        rt = RoutingTable()
        for x in routes:
            try:
                ip = x['ipaddr']
                nm = x['netmask']
                
                rt.addRoute(ip, nm, 'ppp0')
            except:
                msglog.log( 'broadway.mpx.lib.ppp', msglog.types.INFO,
                            'Got exception trying to add route.')
                msglog.exception()
        self._is_connected = 1
        return
    
    
    #################################################################################
    #
    # disconnect
    #
    # A thread-safe wrapper around _disconnect.  Stops the pppd process, thus
    # taking down the ppp connection.
    #
    # Returns:
    #    (status, summary) if successful
    #    Where 'status' is the status code of the child process. The status code
    #    encodes both the return code of the process and information about whether
    #    it exited using the exit() system call or died due to a signal. Functions
    #    to help interpret the status code are defined in the os module; 'summary'
    #    is a list of strings representing the final output from pppd.
    #
    #    None if the connection was not active
    #
    #################################################################################
    def disconnect(self):
        result = None
        self._lock.acquire()
        try:
            if self._is_connected:
                result = self._disconnect()
        finally:
            self._lock.release()
            
        return result
    
    
    #################################################################################
    #
    # is_connected
    #
    # Tests to see if the ppp connection is active.  If the pppd process died
    # unexpectedly then this function will complete the disconnection process.
    #
    # Returns:
    #    0 if not connected or the pppd process died
    #    1 if connected
    #
    #################################################################################
    def is_connected(self):
        if self._is_connected:
            # We think we're connected, but is the pppd process still alive?
            if self._process.poll() != -1:
                # Should an exception be logged here?
                self._disconnect()
        return self._is_connected
    
    
    #################################################################################
    #
    # connect
    #
    # A thread-safe wrapper around _connect.  Starts the pppd process, thus bringing
    # up the ppp connection.  A no-op if the connection is already active.
    #
    # Parameters:
    #    timeout   - the approx. amount of time, in seconds, to wait for the
    #                connection to complete.  The default is DEFAULT_TIMEOUT.
    #
    # Exceptions passed:
    #    EErrantProcess, EErrantProcess, EConnectionTimedOut
    #    (see descriptions at the top of this module)
    # 
    #################################################################################
    def connect( self, timeout = DEFAULT_TIMEOUT,
                 dialout_options_file = None,
                 routes = None ):
        if dialout_options_file is None:
            raise exceptions.EInvalidValue('dialout_options_file', None,
                                           'dialout_options_file parameter must '\
                                           'be specified.')
        if routes is None:
            routes = []
        self._lock.acquire()
        try:
            if not self.is_connected():
                self._connect( timeout, dialout_options_file, routes )
        finally:
            self._lock.release()
    
        return

    #################################################################################
    #
    # start_service
    #
    # Function to start pppd as a service.
    #
    # Parameters:
    #    sid                  - service id, 1-4 chars
    #    dialout_options_file - name of options file to use
    #
    #################################################################################
    def start_service( self, sid, dialout_options_file ):   
        # Launch pppd as a service.
        pppdcmd = '/usr/sbin/pppd nodetach defaultroute file %s' % dialout_options_file
        gname = 'MPX_PPPD_%s' % sid
        inittab = InittabManager()
        if inittab.findgroup( gname ) == None:
            inittab.addgroup( InittabGroup( gname, '%s:345:respawn:%s' % (sid, pppdcmd) ) )
        inittab.commit()

    #################################################################################
    #
    # stop_service
    #
    # Function to stop pppd as a service.
    #
    # Parameters:
    #    sid                  - service id, 1-4 chars
    #
    #################################################################################
    def stop_service( self, sid ):   
        # Launch pppd as a service.
        gname = 'MPX_PPPD_%s' % sid
        inittab = InittabManager()
        if inittab.findgroup( gname ) != None:
            inittab.remgroup( gname )
        inittab.commit()
