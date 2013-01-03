"""
Copyright (C) 2010 2011 Cisco Systems

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
import gdutil

# Note: On the SimpleLineHandler instance lock, the convention is that the
#       public routines (which don't start with a _) grab a lock if necessary,
#       then release it before returning.  The "private" routines assume that
#       the lock is already held, so they don't try to acquire it, and they
#       don't release it.
class SimpleLineHandler:
    def __init__(self, connection_object):
        self.debug = 0
        self.connection = connection_object
        self.connected = 0

        # Note: The following lock guards transactions
        self.transaction_lock = gdutil.get_lock()

        # Note: The following lock guards changes to the connection (connection,
        #       disconnection, etc.) as well as access to the connection object.
        self.connection_lock = gdutil.get_lock()
 
    def _connect(self, numretries=3):
        attempt = 0
        while attempt < numretries:
            if self.debug:
                print 'Connection Attempt #%d of %d.' % (attempt+1, numretries)
            try:
                self.connected = 0
                self.connection.connect()
                self.connected = 1  
                if self.debug:
                    print 'connected'
                return
            except:
                attempt += 1
        raise
    
    # Connect to our target
    def connect(self, numretries=3):
        if self.debug:
            print 'In SimpleLineHandler.connect().'
        self.connection_lock.acquire()
        try:
            if self.connected == 0:
                self._connect(numretries)
        finally:
            self.connection_lock.release()
    #
    def _disconnect(self):
        if self.debug:
            print 'In SimpleLineHandler._disconnect().'
        self.connection.disconnect()
        self.connected = 0
    #
    def disconnect(self):
        if self.debug:
            print 'In disconnect().'
        self.connection_lock.acquire()
        try:
            self._disconnect()
        finally:
            self.connection_lock.release()
    ##
    # Note: A slightly more complicated version of this routine could accomidate possible
    #       "garbage" characters in front of the expected response.
    def _receive_response(self, response_obj, timeout_secs):
        # If our response object is fixed width, then just read the number of bytes
        # we need, parse the response, and return.
        if response_obj.isFixedWidth():
            len_obj = response_obj.getWidth()
            data = self.connection.read(len_obj, timeout_secs)
            match_obj = response_obj.isMatch(data, 0)
            # If we got a match, then return success!
            if match_obj.isMatch() == 1:
                return 1
            # Apparently we didn't get the response we were expecting.  Return failure.
            return 0
        else:
            # Our response object is not fixed width, so read data one byte at a time
            # until we either get a full match, a definitive non-match or a timeout.
            data = ''
            st_time = gdutil.get_time()
            while 1:
                curtime = gdutil.get_time()
                if curtime - st_time > timeout_secs:
                    raise gdutil.GDTimeoutException("Got trying to read matching data")
                new_data = self.connection.read(1, timeout_secs)
                if new_data:
                    data += new_data
                if self.debug > 2:
                    print 'calling isMatch with %s' % gdutil.dump_binary_str(data)
                match_obj = response_obj.isMatch(data, 0)
                # If we got a match, then return success!
                if match_obj.isMatch() == 1:
                    return 1
                # If we got a definitive non-match, return failure.
                if match_obj.isNotMatch() == 1:
                    return 0        
            
    def send_request_with_response(self, request_obj, response_obj, timeout_secs, numretries=1):
        if self.debug > 2:
            print 'In SimpleLineHandler.send_request_with_response() with %s' % str(request_obj)

        send_data = request_obj.dumpStr()
            
        self.transaction_lock.acquire()
        try:
            curtries = 0
            while (curtries < numretries):
                curtries += 1

                self.connect()

                self.connection_lock.acquire()
                try:
                    self.connection.write(send_data, timeout_secs)
                except:
                    self.connection_lock.release()
                    continue
                try:
                    res = self._receive_response(response_obj, timeout_secs)
                    self.connection_lock.release()
                    if res == 1:
                        # Got a successful response, return 1 for success.
                        return 1
                    else:
                        if curtries >= numretries:
                            return 0
                except:
                    self.connection_lock.release()
                    if self.debug:
                        # @fixme: Fix following two lines (using a routine from gdutil).
                        #logMsg('Got an exception trying to send a request or receive a response.')
                        #msglog.exception()
                        pass

            # If we fall through to here, we've tried as many times as we've been told
            # to, and haven't succeeded.  In this case, just re-raise the last exception
            # we got to signal our failure and give some hint as to why we failed.
            raise
        #
        finally:
            self.transaction_lock.release()

    def send_request_without_response(self, request_obj, timeout_secs, numretries=1):
        if self.debug > 2:
            print 'In SimpleLineHandler.send_request_without_response() with %s' % cmd

        send_data = request_obj.dumpStr()
            
        self.transaction_lock.acquire()
        try:
            curtries = 0
            while (curtries < numretries):
                curtries += 1

                self.connect()

                self.connection_lock.acquire()
                try:
                    self.connection.write(send_data, timeout_secs)
                    self.connection_lock.release()
                    return
                except:
                    self.connection_lock.release()
           
            # If we fall through to here, we've tried as many times as we've been told
            # to, and haven't succeeded.  In this case, just re-raise the last exception
            # we got to signal our failure and give some hint as to why we failed.
            raise
        #
        finally:
            self.transaction_lock.release()

    def receive_response(self, response_obj, timeout_secs, numretries=1):
        if self.debug > 2:
            print 'In SimpleLineHandler.send_request_with_response() with %s' % str(request_obj)

        self.transaction_lock.acquire()
        try:
            curtries = 0
            while (curtries < numretries):
                curtries += 1

                self.connect()

                self.connection_lock.acquire()
                try:
                    res = self._receive_response(response_obj, timeout_secs)
                    self.connection_lock.release()
                    if res == 1:
                        # Got a successful response, return 1 for success.
                        return 1
                    else:
                        if curtries >= numretries:
                            return 0
                except:
                    self.connection_lock.release()
                    if self.debug:
                        # @fixme: Fix following two lines (using a routine from gdutil)
                        #logMsg('Got an exception trying to send a request or receive a response.')
                        #msglog.exception()
                        pass

            # If we fall through to here, we've tried as many times as we've been told
            # to, and haven't succeeded.  In this case, just re-raise the last exception
            # we got to signal our failure and give some hint as to why we failed.
            raise
        #
        finally:
            self.transaction_lock.release()
