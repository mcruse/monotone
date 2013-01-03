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
from select import select
from time import sleep
import errno
import os
from mpx import properties

from mpx.lib.exceptions import ETimeout, EIOError

class EPortInUse( EIOError ):
    def __init__( self, pid ):
        self.in_use_by_pid = pid

##
# LockFile
#
# Class to manage the creation of an HDB UUCP-style lock file with an
# arbritary path and name.
#
##
class LockFile:
    def __init__( self, fileName ):
        self._fileName = fileName
        self._my_pid = os.getpid()
        
    # Return the pid of the process that owns the lock file, 0 if unable read pid.
    def _readPID( self ):
        try:
            lockFile = os.open( self._fileName, os.O_RDONLY )
        except:
            return 0
        
        pid = os.read( lockFile, 32 )
        if len( pid ):
            pid = int( pid.split()[0] )
        else:
            pid = 0
            
        os.close( lockFile )
        return pid
    
    # Return 1 if the pid is active, 0 if not, or an exception.
    def _testPID( self, pid ):
        try:
            os.kill( pid, 0 )
        except OSError, e:
            if e.errno == errno.ESRCH:
                return 0
            raise e
        return 1
    
    # Return 0 if lock acquired, or pid of lock owner, or an exception.
    def _acquire( self ):
        # Try to create the lock file.
        try:
            lockFile = os.open( self._fileName,
                                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                0644 )
        except OSError, e:
            # The only error we can handle is a file that already exists.
            if e.errno == errno.EEXIST:
                owner = self._readPID()
                # Return 0 if we already own the file.
                if owner == self._my_pid:
                    return 0
                # Return pid of owning process if the process is still active.
                if self._testPID( owner ):
                    return owner
                # Try to remove the stale lock and re-acquire the file.
                os.unlink( self._fileName )
                return self._acquire()
            raise e
            
        # Write our pid to the file as per Filesystem Hierarchy Standard (FHS) 2.2
        # (see http://www.pathname.com/fhs/2.2/).
        os.write( lockFile, "%10d\n" % self._my_pid )
        os.close( lockFile )
        return 0
    
    ##
    # Create the lock file.
    #
    # @param retries Number of times to try to create the file.
    # @param interval The amount of time between retries, expressed in seconds.
    # @return 0 if lock acquired, or pid of lock owner, or an exception.
    #
    def acquire( self, retries = 10, interval = 1.0 ):
        while 1:
            result = self._acquire()
            if result == 0 or retries <= 0:
                return result
            retries -= 1
            sleep( interval )
            
    ##
    # Remove the lock file.
    #
    # @note This method is a no-op if we don't own the lock file.
    #
    def release( self ):
        if self._acquire() == 0:
            os.unlink( self._fileName )


##
# DeviceLock
#
# Class to manage the creation of an HDB UUCP-style lock file for a specified
# device.
#
# @note The HDB UUCP lock file format and naming convention is used.
#       The SVR4 lock file naming convention is more robust in that it will
#       detect devices opened via a link.
# @todo Support SVR4 (LK.%03u.%03u.%03u), what appears to be a RedHat variant
#       (LCK..%03d.%03d), and PID locking (LCK...pid) file names as well.
#       Multiple formats need to be supported or we need to ensure that all
#       programs in MOE are consistant.
##
class DeviceLock( LockFile ):
    def __init__( self, devPath, lock_directory = None ):
        if lock_directory:
            self.lock_directory = lock_directory
        else:
            self.lock_directory = properties.get( 'VAR_LOCK', '/var/lock' )
        
        # Filename that conforms to the Filesystem Hierarchy Standard (FHS) 2.2
        # (see http://www.pathname.com/fhs/2.2/).
        self._devName = os.path.split( devPath )[-1]
        LockFile.__init__( self, os.path.join( self.lock_directory, 'LCK..%s' % self._devName ) )
        
        
##
# test_modem
#
# Function to test for the existance of a modem on the specified serial port.
#
# @param devName The name of the serial port to test.
# @param retries Number of times to try to create the file.
# @param interval The amount of time between retries, expressed in seconds.
# @return 1 if the modems exists, 0 otherwise, or exception EPortInUse.
#
def test_modem( devName, retries = 10, interval = 1.0 ):
    isOK = 0
    lock = DeviceLock( devName )
    pid = lock.acquire( retries, interval )
    if pid:
        raise EPortInUse( pid )
    else:
        odev = os.open( devName, os.O_WRONLY|os.O_NONBLOCK )
        if os.isatty( odev ):
            idev = os.open( devName, os.O_RDONLY|os.O_NONBLOCK )
            
            # Send a simple command to the modem.
            # Another good choice might be 'ATQ0V1E1\r'
            os.write( odev, 'ATZ\r' )
            
            # Wait three seconds for the modem to respond with 'OK'.
            while 1:
                result = select( [idev], [], [], 3 )
                if not result[0]:
                    # Timed out
                    break
                response = os.read( idev, 100 )
                if 'OK' in response.split():
                    isOK = 1
                    break
            os.close( idev )
            
        os.close( odev )
        lock.release()
            
    return isOK

##
# Test routine executed if this module is run as main.
##
if __name__ == "__main__":
    import sys
    if len( sys.argv ) > 1:
        dev = sys.argv[1]
        print "Testing", dev
        try:
            if test_modem( dev, 3 ):
                print "modem ready"
            else:
                print "modem not available"
        except EPortInUse, e:
            print dev, "locked by process", e.in_use_by_pid
        except OSError, e:
            print e
