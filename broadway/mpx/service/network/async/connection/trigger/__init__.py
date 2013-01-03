"""
Copyright (C) 2008 2011 Cisco Systems

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
from threading import Lock
from mpx.lib import msglog

if os.name == 'posix':
    from pipe_trigger import PipeTrigger as Trigger
else:
    # This will actually cause a failure because use of 
    #   Unix-type sockets for trigger.  Eventually implement 
    #   trigger using TCP socket only for use on other OS.
    from socket_trigger import SocketTrigger as Trigger

class CallbackTrigger(Trigger):
    # Adds ability to queue callback when trigger 
    #   handle-event is invoked by asyncore loop.
    #   The benefit of this is that it allows other 
    #   threads to "queue" up work to be done by the 
    #   async-i/o thread and therefore may alleviate the 
    #   need to introduce locking constructs to pretect 
    #   shared data structures for modification.  The problem 
    #   is that there is currently no ordering mechanism to 
    #   guarantee the callback is invoked before the triggering 
    #   channel is repolled itself, making it potentially 
    #   inneficient.  In the future this can be revised to 
    #   ensure efficient ordering if needed.
    def __init__ (self, socketmap):
        self._callbacks = []
        self._callback_lock = Lock()
        Trigger.__init__(self, socketmap)
    def close(self):
        self._callback_lock.acquire()
        try:
            for callback, args in self._callbacks:
                print 'Callback discarded because close: %s' % callback
            self._callbacks = []
        finally:
            self._callback_lock.release()
        return Trigger.close(self)
    def trigger_event(self, callback = None, *args):
        if callback:
            self._callback_lock.acquire()
            try:
                self._callbacks.append((callback, args))
            finally:
                self._callback_lock.release()
        return Trigger.trigger_event(self)
    def handle_read (self):
        result = Trigger.handle_read(self)
        self._callback_lock.acquire()
        try:
            for callback, args in self._callbacks:
                try: 
                    callback(*args)
                except: 
                    msglog.exception()
            self._callbacks = []
        finally:
            self._callback_lock.release()
        return result
