"""
Copyright (C) 2002 2003 2004 2010 2011 2012 Cisco Systems

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
#from popen2 import Popen4
from subprocess import Popen, PIPE
from select import select
from socket import gethostbyname, inet_aton

import stat
import errno

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
import moab.linux.lib.process as process

_NODE_CONNECTION_INCOMING  = '/interfaces/modem/ppp0/incoming'
_NODE_CONNECTION_OUTGOING  = '/interfaces/modem/ppp0/outgoing'
_NODE_CONNECTION_BROADBAND = '/services/network'
_NODE_TIMESYNCH_PERIODIC   = '/services/time/synch_periodic'
_NODE_TIMESYNCH_CONTINUOUS = '/services/time/synch_continuous'

DRIFT_FILE_PATH = os.path.join(properties.ETC_DIR, 'ntp.drift')

_NTP_CONF_PROLOG = """
######################################################################
#
# ntp.conf for RedHat Linux systems running ntpd.
# http://www.ntp.org/ for additional information on NTP.
#
######################################################################

# deny-by-default policy
restrict default ignore

# synchronize with the following time servers
"""

_NTP_CONF_EPILOG = """
# local fudge if network servers not available (not currently used)
##server  127.127.1.0     # local clock
##fudge   127.127.1.0 stratum 10

restrict 127.0.0.1 # allow ntpd access/mod from localhost, via ntpq or ntpdc

# track wander (leading directories _and_ file itself must exist, and have 
# permissions 0777!)
driftfile %s
""" % DRIFT_FILE_PATH

# Default time servers
_DEFAULT_SERVERS = ['clock.via.net', 'clock2.redhat.com']

##
# Class to manage synchronization using Network Time Protocol.
#
class TimeSynchronizer( CompositeNode, EventConsumerMixin ):
    # This class variable counts the number of nodes that are enabled.
    # The status file is removed when this count is zero.
    nodesEnabled = 0
    NTP_FREQ_MIN = -500.0
    NTP_FREQ_MAX = 500.0
    NTP_FREQ_DEFAULT = 0.000
    NTPD_RETRY_PERIOD = 60 # sec
    ST_START = 0
    ST_SVRNAME_RESOLVED = 1
    ST_NOT_CONN = 2
    ST_RUNNING = 3
    MSG_NO_RESOLUTION = 'Unable to resolve any NTP server hostnames into IP '\
        'addrs: %s. Cannot synch SW clock time continuously or periodically.'
    def __init__( self ):
        CompositeNode.__init__( self )
        EventConsumerMixin.__init__( self, self.handle_connected, self.connection_event_error )
        self.maxConnectionAttempts = 3
        self.timeout = 30
        self.isRunning = 0
        self._lock = Lock()
        self.thread = None
        self.is_periodic = False # actual setting done in configure()
        self.server_list = []
        self.state = self.ST_START

    def handle_connected( self, event ):
        msg = 'Got connection event -- ignored'
        self.msglog( msg )
        
    def connection_event_error( self, exc, event ):
        msg = 'Connection event for ' + str( self.connection_node ) + ' had the following error:\n'
        msg += 'Event: ' + str( event )
        msg += 'Error: ' + str( exc )
        msglog.log( 'broadway', msglog.types.WARN, msg )
           
    def _is_debug( self ):
        if self.__dict__.has_key( 'debug' ):
            if self.debug:
                return 1
        return 0

    def msglog( self, msg, force=0 ):
        if self._is_debug() or force:       
            msglog.log( 'broadway.mpx.service.time.synch', msglog.types.DB, msg )
                
    def configure( self, config_dict ):     
        CompositeNode.configure( self, config_dict )
        set_attribute( self, 'enable', 0, config_dict, int )
        set_attribute( self, 'debug', 0, config_dict, int )
        map_to_attribute( self, 'period', 0, config_dict, map_to_seconds )
        set_attribute( self, 'servers', [],  config_dict )
        set_attribute( self, 'connection_type', '', config_dict )
        if self.connection_type.lower() == 'lan':
            self.connection_node = _NODE_CONNECTION_BROADBAND
        elif self.connection_type.lower() == 'dial out':
            self.connection_node = _NODE_CONNECTION_OUTGOING
        else:
            msg = 'Connection type "%s" NOT supported' % self.connection_type
            raise EAttributeError( msg )
        self.is_periodic = True
        node_url = self.as_node_url()
        if node_url.strip() == _NODE_TIMESYNCH_CONTINUOUS.strip():
            self.is_periodic = False
        self.msglog("is_periodic = %s" % str(self.is_periodic),1)
        self.server_list = []
        
    def configuration( self ):
        config_dict = CompositeNode.configuration( self )
        get_attribute( self, 'enable', config_dict )
        get_attribute( self, 'debug', config_dict )
        map_from_attribute( self, 'period', config_dict, map_from_seconds )
        get_attribute( self, 'servers', config_dict )
        get_attribute( self, 'connection_type', config_dict )
        return config_dict

    def _create_conf_file( self ):
        # This method wipes out any current contents of any existing conf file:
        file = open( os.path.join( properties.ETC_DIR, 'ntp.conf' ), 'w' )
        file.write( _NTP_CONF_PROLOG )
        for server in self.server_list:
            file.write( "server %s iburst minpoll 4\n" % server )
        file.write( '\n' )
        for server in self.server_list:
            file.write( "restrict %s nomodify nopeer notrap\n" % server )
        file.write( _NTP_CONF_EPILOG )
        file.close()

    # Ensure that ntp.drift file exists, has adequately liberal permissions,
    # and contains a valid float:
    def _create_drift_file(self):
        drift_file= None
        freq = self.NTP_FREQ_DEFAULT # default value
        try:
            drift_file = open(DRIFT_FILE_PATH, 'r')
            lines = drift_file.readlines()
            num_lines = len(lines)
            if num_lines != 1:
                raise ValueError('File must have exactly 1 line. Has %u' \
                                 % num_lines)
            freq = float(lines[0])
            if freq < self.NTP_FREQ_MIN or freq > self.NTP_FREQ_MAX:
                raise ValueError('freq out of range: %.3f' % freq)
        except(Exception),e:
            if drift_file and isinstance(drift_file, file) \
                and not drift_file.closed:
                    drift_file.close()
            self.msglog('Problem with %s: %s. (Re)Creating file...' \
                        % (DRIFT_FILE_PATH, str(e)),1)
            # Truncate or create if necy:
            drift_file = open(DRIFT_FILE_PATH, 'w')
            freq = self.NTP_FREQ_DEFAULT
            drift_file.write('%.3f\n' % freq)
        finally:
            print 'Current freq = %.3f' % freq
            drift_file.close()
            os.chmod(DRIFT_FILE_PATH, 0777)
        return

    def _kill_all_ntpds(self):
        # Obtain a ps output of processes with ntpd in cmdline:
        ntp_procs_filepath = '/home/mpxadmin/ntp_procs.txt'
        os.system('ps ax | grep ntpd > ' + ntp_procs_filepath)
        ntp_procs_file = open(ntp_procs_filepath, 'r')
        lines = ntp_procs_file.readlines()
        ntp_procs_file.close()
        os.remove(ntp_procs_filepath)
        # Walk the list and kill all except those created by grep above:
        num_ntpds = 0
        for line in lines:
            if line.find('grep') >= 0:
                continue
            try:
                pid = int(line[:6])
                os.kill(pid, signal.SIGKILL)
                num_ntpds += 1
            except(Exception),e:
                self.msglog('Failed to kill ntpd: %s' % str(e), 1)
                continue
        self.msglog('Killed %u ntpd instances.' % num_ntpds, num_ntpds)
        return

    # Changes to how MOE 2.0.32 (and beyond) manage time requires some information
    # from the Framework. The Framework currently manages NTP configuration. This will
    # also be changed sometime soon but until then the logman process needs to know
    # whether NTP is enabled or not. The Framework indicates this by creating or
    # modifying a file in /etc called timesync. This file contains one line with
    # one word of either 'ntp' if NTP is being used as the authoritative, or rtc if
    # the hwclock is being used for this purpose. If the file does not exist then the
    # assumption is that the hwclock is being used.Create, or remove, the file
    #
    def _manage_status_file( self ):
        file_name = os.path.join( properties.ETC_DIR, 'timesync' )
        if TimeSynchronizer.nodesEnabled == 1:
            file = open( file_name, 'w' )
            file.write( 'ntp\n' )
            file.close()
        elif TimeSynchronizer.nodesEnabled == 0 and os.path.exists( file_name ):
            os.remove( file_name )

    def _resolve_hostname(self, hostname):
        try:
            server_ip = gethostbyname(hostname) # get IP addr
            server_addr = inet_aton(server_ip) # validate IP addr fmt
        except(Exception),e:
                server_ip = False
        return server_ip

    def start( self ):
        if self.enable:
            if self.isRunning:
                raise EAlreadyRunning
            # May be multiple copies of ntpd running. Kill all of them now:
            self._kill_all_ntpds()
            # Bug, apparently in all versions of NTP: ntpd on 2400 (4.1.2)
            # cannot recover from DNS failure on NTP server names listed in 
            # ntp.conf, at startup. Even so, ntpd continues to run, rather than
            # killing itself. So, try to resolve all server hostnames
            # before starting ntpd. If no names can be resolved,
            # then schedule a retry in 60 sec. Also, we can use "ntpq -c as" 
            # immediately after ntpd starts to determine whether ntpd found any
            # resolved IP addrs to TRY to connect with. If not, then we kill 
            # ntpd, wait awhile, and retry later.
            self.server_list = []
            at_least_one_name_resolved = False
            if self.servers:
                for server_dict in self.servers:
                    server_name = server_dict['server']
                    server_ip = self._resolve_hostname(server_name)
                    if server_ip:
                        at_least_one_name_resolved = True
                    else:
                        server_ip = server_name
                    self.server_list.append(server_ip)
            else:
                for server_name in _DEFAULT_SERVERS:
                    server_ip = self._resolve_hostname(server_name)
                    if server_ip:
                        at_least_one_name_resolved = True
                    else:
                        server_ip = server_name
                    self.server_list.append(server_ip)
            self.state = self.ST_START
            if at_least_one_name_resolved:
                self.state = self.ST_SVRNAME_RESOLVED
                self._create_conf_file()
                self.msglog('server_list: %s' % str(self.server_list), 1)
            else:
                self.msglog(self.MSG_NO_RESOLUTION % str(self.server_list), 1)
            self.msglog("STARTING %s, period = %d" % (self.name, self.period))
            self._create_drift_file()
            self.isRunning = 1
            self._schedule()
            TimeSynchronizer.nodesEnabled += 1
        self._manage_status_file()
        return
    def _schedule( self ):
        interval = self.period
        if self.state == self.ST_START or self.state == self.ST_NOT_CONN:
            interval = self.NTPD_RETRY_PERIOD
        scheduler.seconds_from_now_do(interval, self.go)

    def stop( self ):
        # @fixme: NEVER ACTUALLY CALLED BY MFW DURING SHUTDOWN! So, ntpd is
        # left running. However, all vestigial instances of ntpd still running
        # at next MFW restart are killed, and a single new instance is started.
        if self.isRunning:
            self._kill_all_ntpds()
            self.isRunning = 0

    def go( self ):
        # Lock here
        self._lock.acquire()
        try:
            if self.thread and self.thread.isAlive():
                # Don't do it!
                return
            self.thread = Thread( name = self.name, target = self._complete, \
                                  args = () )
            self.thread.start()
        finally:
            self._lock.release()

    def _complete( self ):
        try:
            self._synchronize()
        except:
            msglog.exception()
            
        if self.state == self.ST_START \
            or self.state == self.ST_NOT_CONN \
            or (self.isRunning and self.period):
                self._schedule()

    def _synchronize( self ):
        # Don't attempt to run ntpd or ntpdate until at >= 1 NTP server name
        # in ntp.conf has been resolved to an IP address:
        if self.state == self.ST_START:
            at_least_one_name_resolved = False
            for i in range(0, len(self.server_list)):
                server = self.server_list[i]
                server_ip = self._resolve_hostname(server)
                if server_ip:
                    at_least_one_name_resolved = True
                    self.server_list[i] = server_ip
            if not at_least_one_name_resolved:
                self.msglog(self.MSG_NO_RESOLUTION % str(self.server_list), 1)
                return
            self._create_conf_file()
        # If we get here, then we resolved >= 1 NTP server hostnames:
        self.state = self.ST_NOT_CONN
        self.msglog( 'Connection node: ' + str( self.connection_node ) )
        connection = as_node( self.connection_node )
        numberOfAttempts = 0
        isConnected = 0
        self.msglog('Trying to acquire...', 1)
        while not isConnected and numberOfAttempts < self.maxConnectionAttempts:
            try:
                numberOfAttempts += 1 
                if connection.acquire( self.timeout ):
                    isConnected = 1
                    self.msglog( 'connection acquired',1 )
                elif self.connection_node != _NODE_CONNECTION_INCOMING:
                    self.msglog( 'unable to acquire connection' )
            
            except ETimeout, e:
                msg = 'Timeout occured while trying to connect,\nerror: %s' \
                        % str( e )
                msglog.log( 'broadway', msglog.types.WARN, msg )
                ## retry ##
            
            except EConnectionError, e:
                msg = 'Connection error: %s' % str( e )
                msglog.log( 'broadway', msglog.types.WARN, msg )  
                break 
            
            except ENoSuchName, e:
                msg = 'Connection error: no connection node named "%s"' \
                        % str( self.connection_node )
                msglog.log( 'broadway', msglog.types.WARN, msg )
                break
        if isConnected:
            if self.is_periodic and self.period:
                self._kill_all_ntpds() # ensure no other instances running now
                try:
                    # This node seems to be properly configured periodic synch.
                    # "ntpd -q" takes 5+ sec even if it _can_ connect to
                    # one of the servers specified in ntp.conf; it does not
                    # bother to return for >15 sec if the server cannot be 
                    # found via DNS or if the IP address is not reachable. Also,
                    # return values do not indicate failure! In contrast, 
                    # ntpdate (nominally deprecated now in favor of ntpd -q) 
                    # returns immediately, upon success or failure. So, use 
                    # ntpdate with current versions of ntpd on 2400 (4.1.2)
                    # and 2500 (4.2.2):
                    for server in self.server_list:
                        proc = Popen(['ntpdate',server],
                                      stdout=PIPE,stderr=PIPE, close_fds=True)
                        output = proc.communicate()
                        if proc.returncode != 0:
                            msg = '"ntpdate %s" failed: Rtnd %i: %s' \
                                        % (server, proc.returncode, output[1])
                            self.msglog(msg,1)
                            continue
                        msg = 'ntpdate updated SW clock from server %s: %s'\
                                % (server, output[0])
                        self.msglog(msg,1)
                        self.state = self.ST_RUNNING
                        break # ntpdate update of SW clock apparently succeeded
                except(Exception),e:
                    msglog.log('broadway', msglog.types.ERR, str(e))
            elif not self.is_periodic:
                # This node appears to be a continuous synch:
                args = '-Agx'
                try:
                    # MUST set close_fds to True in Popen ctor below, so that
                    # open file descriptors will not keep the MFW from exiting
                    # cleanly without killing child ntpd 1st. Symptoms of NOT
                    # using this setting are: lsmod shows residual usage of
                    # n_mstp module, even though the MFW is mostly dead, AND 
                    # the next MFW start shows a bunch of errors in the msglog,
                    # especially "11": resource temporarily unavailable.
                    proc = Popen(['ntpd',args],
                                  stdout=PIPE,stderr=PIPE, close_fds=True)
                    output = proc.communicate()
                    if proc.returncode != 0:
                        raise Exception('"ntpd %s" failed: Rtnd %i: %s' \
                                    % (args, proc.returncode, output[1]))
                    # Check for at least one _possible_ assn:
                    proc = Popen(['ntpq','-c','as'],stdout=PIPE,stderr=PIPE)
                    output = proc.communicate()
                    if proc.returncode != 0:
                        raise Exception('"ntpq -c as" failed: Rtnd %i: %s' \
                                    % (proc.returncode, output[1]))
                    if output[0][:2] == 'No':
                        # Cannot reach NTP server. Kill all extant
                        # instances of ntpd:
                        self._kill_all_ntpds()
                        msg = 'ntpd unable to connect to a server. ntpd '\
                                'stopped. Retry in %u sec...' \
                                % self.NTPD_RETRY_PERIOD
                        self.msglog(msg, 1)
                    else:
                        msg = 'ntpd connected (or may connect in the future)'\
                                ' to >= 1 server. Leaving ntpd running...'
                        self.msglog(msg, 1)
                        self.state = self.ST_RUNNING
                        self.period = 0
                except(Exception),e:
                    msglog.log('broadway', msglog.types.ERR, str(e))
            self.msglog('Releasing...', 1)
            connection.release()
        elif self.connection_node != _NODE_CONNECTION_INCOMING:
            s = ''
            if numberOfAttempts > 1:
                s = 's'
            msg = 'Unable to connect using node "%s" after %d attempt%s' \
                % (self.connection_node, numberOfAttempts, s)
            msglog.log( 'broadway', msglog.types.INFO, msg )
        return

def factory():
    return TimeSynchronizer()
