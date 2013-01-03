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
import os
from time import sleep

# Default patterns.  These are used only if blinky bill isn't running,
# which shoud only happen during the initial installation process.
_PATTERNS = { '.' : '111111111000000000000000000000',
              'I' : '111000111000000000000000000000',
              'R' : '111111111000111111111000111111111000000000000000000000',
              'E' : '111000111000111000111000000000000000000000',
              'P' : '111000111000111000000000111111111000111111111000111111111000000000111000111000111000000000000000000000'
            }
_PATTERN_FILE_NAME = '/proc/mediator/pattern'

def is_megatron(s=None):
    try:
        f = open("/proc/cpuinfo")
        cpu_info = f.read()
        f.close()
        return cpu_info.find('Megatron') >= 0
    except:
        return False


class StatusLED:
    def __init__( self ):
        # Open pipe to blinky_bill.
        try:
            self._megatron = None
            self._bbPipe = None
            if is_megatron():
                import megatron
                self._megatron = megatron
                return
            self._bbPipe = os.open( "/tmp/.blinky_bill.fifo", os.O_WRONLY|os.O_NONBLOCK )
        except:
            pass
            
    def __del__( self ):
        if self._bbPipe:
            try:
                os.close( self._bbPipe )
            except:
                pass
            
    def _setState( self, state ):
        if self._megatron:
            return
        if self._bbPipe:
            try:
                os.write( self._bbPipe, state )
            except:
                pass
        else:
            try:
                procFile = file( _PATTERN_FILE_NAME, 'w' )
                procFile.write( _PATTERNS[state] + '\n' )
                procFile.close()
            except:
                pass
            
    def setIdle( self ):
        if self._megatron:
            self._megatron.setIdle()
            return
        self._setState( '.' )

    def setInstalling( self ):
        if self._megatron:
            self._megatron.setInstalling()
            return
        self._setState( 'I' )

    def setRunning( self ):
        if self._megatron:
            self._megatron.setRunning()
            return
        self._setState( 'R' )

    def setError( self ):
        if self._megatron:
            self._megatron.setError()
            return
        self._setState( 'E' )

    def setPanic( self ):
        if self._megatron:
            self._megatron.setPanic()
            return
        self._setState( 'P' )
        
    # Return 1 if the pipe is open, 0 otherwise.
    def waitForStart( self, seconds_to_wait = 10 ):
        if self._megatron:
            return True
        for i in range( seconds_to_wait ):
            if self._bbPipe:
                return 1
            sleep( 1 )
            self.__init__()
        return 0


##
# Test routine executed if this module is run as main.
##
if __name__ == "__main__":
    sleep_time = 10
    led = StatusLED()
    
    if led.waitForStart():
        print "pipe is open"
    else:
        print "pipe is NOT open"
    
    print "idling..."
    led.setIdle()
    sleep( sleep_time )

    print "installing..."
    led.setInstalling()
    sleep( sleep_time )

    print "running..."
    led.setRunning()
    sleep( sleep_time )

    print "running with error..."
    led.setError()
    sleep( sleep_time )

    print "panic..."
    led.setPanic()
    sleep( sleep_time )

    print "Returning to idle..."
    led.setIdle()
    print "done."

    
