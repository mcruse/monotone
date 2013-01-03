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
from mpx.componentry import Interface
from mpx.componentry import Attribute

class ICounter(Interface):
    """
        General purpose counter uses long integer to prevent 
        overflows and provides increment and decrement interface.
    """
    value = Attribute('Read Only value of counter')
    def increment(delta = 0):
        """
            Alias for post_increment.
        """
    def decrement(delta = 0):
        """
            Alias for post_decrement.
        """
    def post_increment(delta = 0):
        """
            Increment counter value by absolute value of 
            delta.  Return counter value previous to operation.
        """
    def post_decrement(delta = 0):
        """
            Decrement counter value by absolute value of 
            delta.  Return counter value previous to operation.            
        """
    def pre_increment(delta = 0):
        """
            Increment counter value by absolute value of 
            delta.  Return new counter value.
        """
    def pre_decrement(delta = 0):
        """
            Decrement counter value by absolute value of 
            delta.  Return new counter value.
        """
    def reset():
        """
            Reset counter value to its initial value.
        """

class ITimer(Interface):
    def start(tstart = None):
        """
            Start timer clock.  Start time may be provided explicitly, 
            but will default to the current time in its absence.
        """
    def stop(tstop = None):
        """
            Stop timer clock.  Stop time may be provided explicitly, 
            but will default to the current time in its absence.
        """
    def get_name():
        """
            Get the name provided to this timer at instantation.
        """
    def get_start():
        """
            Get the time at which this timer was started.  If it 
            has not been started, the return value will be None.
        """
    def get_stop():
        """
            Get the time at which this timer was stopped.  If it 
            has not been stopped, the return value will be None.
        """
    def get_lapse():
        """
            Calculate and return the number of seconds that lapsed 
            between the timer's start and stop times.
        """
    def reset():
        """
            Reset all timing values associated with this timer allowing 
            its reuse.  Note that the number of times a timer has been 
            reset, as well as accumlated run times, etc., are tracked.
        """
    def __repr__():
        """
            Returned detailed string representation of Timer.
        """
    def __str__():
        """
            Return friendly string representation of timer.
        """
    def get_timestr(lapseonly = False):
        """
            Return string representation of Timer, including various 
            times and the name for friendly printing.  If lapseonly is 
            set to True, the start and stop times will not be included 
            in the sring, only the number of seconds lapsed between them.
        """
