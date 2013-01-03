"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
##
# Implements the alarm client for Enflex's eWebConnect.

# @todo Use PDO of undeliverred alarms!

import time

from mpx.lib import msglog
from mpx.lib import socket

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.exceptions import ENotStarted

from mpx.lib.thread_pool import LOW

from mpx.lib.threading import Lock
from mpx.lib.threading import NOTHING
from mpx.lib.threading import Queue
from mpx.lib.threading import currentThread

from mpx.service.hal.alarms import NewAlarmsEvent

from mpx.service.hal.client import Client

class EWebConnectAlarmClient(Client):
    _batch_mode_default = 0
    _host_default = REQUIRED
    _port_default = 4546
    _timeout_default = 60
    def _init_default_attribute_values(self):
        self.batch_mode = self._batch_mode_default
        self.host = self._host_default
        self.port = self._port_default
        self.timeout = self._timeout_default
        return
    def __init__(self):
        self.__alarm_queue = Queue()
        self.__current_thread = None
        self.__lock = Lock()
        self._init_default_attribute_values()
        Client.__init__(self)
        return
    def configure(self,config):
        Client.configure(self,config)
        set_attribute(self,'batch_mode', self._batch_mode_default, config, int)
        set_attribute(self,'host', self._host_default, config, str)
        set_attribute(self,'port', self._port_default, config, int)
        set_attribute(self,'timeout', self._timeout_default, config, int)
        return
    def configuration(self):
        config = Client.configuration(self)
        get_attribute(self, 'batch_mode', config, int)
        get_attribute(self, 'host', config, str)
        get_attribute(self, 'port', config, int)
        get_attribute(self, 'timeout', config, int)
        return config
    def start(self):
        self.__lock.acquire()
        try:
            self.__running = 1
            self.register_event(NewAlarmsEvent,self._new_alarms)
        finally:
            self.__lock.release()
        Client.start(self)
        self.debug = 1
    def stop(self):
        self.__lock.acquire()
        try:
            self.unregister_event(NewAlarmsEvent)
            self.__running = 0
        finally:
            self.__lock.release()
        Client.stop(self)
    def is_running(self):
        return self.__running
    def message_log(self,message,message_type=msglog.types.DB):
        if message_type != msglog.types.DB or self.debug:
            msglog.log('EWebConnect Alarm Client',message_type,message)
    ##
    # Event handler for the NewAlarmsEvent
    #
    # Queues each new alarm for processing and then schedules
    # _prime_process_alarm_queue() on a thread pool to ensure that alarms
    # are processed.
    def _new_alarms(self, event):
        self.__lock.acquire()
        try:
            if not self.is_running():
                raise ENotStarted('%s' % self.as_node_url())
        finally:
            self.__lock.release()
        for alarm in event:
            self.__alarm_queue.put(alarm.as_dictionary())
        self.message_log('New Alarms Event, queuing action')
        LOW.queue_noresult(self._prime_process_alarm_queue)
        return
    ##
    # If no thread is actively processing the alarm queue, then set this thread
    # as the current alarm queue processor and invoke _process_alarm_queue().
    #
    # @note This method is in invoked as an action queued on a thread pool and
    #       should never be called directly when processing an event.
    def _prime_process_alarm_queue(self):
        # @todo Save queue in a PDO?
        thread = currentThread()
        self.__current_thread = thread
        self._process_alarm_queue(thread)
    ##
    # Process all alarms on the alarm queue.
    #
    # @note This method is in invoked indirectly as an action queued on a
    #       thread pool and should never be called directly when processing an
    #       event.
    def _process_alarm_queue(self,my_thread):
        self.message_log('Processing Alarm Queue...')
        while my_thread == self.__current_thread:
            alarm_dict = self.__alarm_queue.get(0)
            if alarm_dict is NOTHING:
                break
            try:
                self._send_alarm_dict(alarm_dict)
            except:
                self.message_log('Failed to send alarm:\n  %r' % alarm_dict,
                                 msglog.types.ERR)
                msglog.exception()
        else:
            self.message_log('New alarm process coincided with running process')
        self.message_log('Finished Processing Alarm Queue')
    ##
    # Format the Alarm described by alarm_dict as an eWebConnect Alarm
    # message and send it to the eWebConnect server.
    # @note This method always succeeds to format a message, any field that
    #       is not valid for any reason is set to "N/A".   Furthermore,
    #       this method does not intercept any networking failures as it
    #       is the caller's responsibility to handle retries, etc...
    def _send_alarm_dict(self, alarm_dict):
        if self.host is None:
            self.message_log('Failed to send alarm; host address is None:\n  %r' % alarm_dict,
                                 msglog.types.INFO)
            return # nowhere to send it!
        ewebconnect_text = (
            "%(timestamp)s, %(TZ)s, %(host)s, %(what)s, %(code)s:"
            " %(type)s %(text)s"
            ) % {
            "timestamp":self._alarm_timestamp(alarm_dict),
            "TZ":self._alarm_tz(alarm_dict),
            "host":self._alarm_host(alarm_dict),
            "what":self._alarm_what(alarm_dict),
            "code":self._alarm_code(alarm_dict),
            "type":self._alarm_type(alarm_dict),
            "text":self._alarm_text(alarm_dict),
            }
        self.message_log('Sending Alarm: %s' % ewebconnect_text)
        server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            # @fixme Try block only exists because the normal desctructor
            #        invokation does not appear to work on mpx.lib.socket
            #        sockets which is a big deal if there is an exception.
            #        - mevans
            server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            server_socket.connect((self.host, self.port), self.timeout)
            server_socket.sendall(ewebconnect_text, self.timeout)
        finally:
            # A finally block is used because the normal desctructor invokation
            # does not appear to work on mpx.lib.socket socket's. - mevans
            # @fixme Figure out why!
            server_socket.close() # Could this hang?  Should I use shutdown?
        self.message_log('Alarm Sent')
        return
    ##
    # Convert an Alarm's time-stamp to a string in eWebConnect's format.
    #
    # @param alarm_dict The dictionary representation of an Alarm, presumably
    #                   returned by the Alarm's as_dictionary() method.
    # @return A string representing the the time-stamp in eWebConnect's format.
    # @note Any failure during the conversion results in the string "N/A" and
    #       the exception is logged to the msglog.  This is to help ensure that
    #       the alarm is still delivered with as much useful information as
    #       possible.
    def _alarm_timestamp(self, alarm_dict):
        result = "N/A"
        try:
            localtime = time.localtime(alarm_dict['timestamp'])
            result = time.strftime("%m/%d/%Y %H:%M:%S", localtime)
        except:
            msglog.exception()
        return result
    ##
    # @see _alarm_timestamp().
    def _alarm_tz(self, alarm_dict):
        result = "N/A"
        try:
            is_dst = time.localtime(alarm_dict['timestamp']).tm_isdst
            result = time.tzname[is_dst]
        except:
            msglog.exception()
        return result
    ##
    # @see _alarm_timestamp().
    def _alarm_host(self, alarm_dict):
        result = "N/A"
        try:
            # @fixme F/W should have this as a 'system attribute' (aka
            #        property) and should support COV on properties.
            result = socket.gethostbyaddr(socket.gethostname())[0]
        except:
            msglog.exception()
        return result
    ##
    # @see _alarm_timestamp().
    def _alarm_code(self, alarm_dict):
        result = "N/A"
        try:
            result = alarm_dict['state']
        except:
            msglog.exception()
        return result
    ##
    # @see _alarm_timestamp().
    def _alarm_what(self, alarm_dict):
        result = "ALARM"
        return result
    ##
    # @see _alarm_timestamp().
    def _alarm_type(self, alarm_dict):
        result = "N/A"
        try:
            result = alarm_dict['type']
        except:
            msglog.exception()
        return result
    ##
    # @see _alarm_timestamp().
    def _alarm_text(self, alarm_dict):
        result = "N/A"
        try:
            result = alarm_dict['data']
        except:
            msglog.exception()
        return result
