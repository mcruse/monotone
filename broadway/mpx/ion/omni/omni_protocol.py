"""
Copyright (C) 2011 Cisco Systems

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
import mpx.lib.genericdriver.gdconnection as gdconn
import mpx.lib.genericdriver.gdlinehandler as gdlh
import mpx.lib.omni.stx as om
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.exceptions import EAlreadyRunning, ENotRunning, EAlreadyOpen
from mpx.lib.exceptions import ETimeout, EInvalidMessage
from mpx.lib.threading import Lock
from mpx.lib.node import CompositeNode
from mpx.lib import msglog
from mpx.ion.omni import EWriteError

class OmniProto(CompositeNode):
    """ This class is modelled to hold the omnimeter protocol . 
    The class gives protocol level service for enabling and disabling protocol
     and enabling and disabling the debug prints . """
    __node_id = 'fcab0563-fabf-452a-b527-f592d04dbe8e'
    
    def __init__(self):
        super(OmniProto, self).__init__()
        self.lock = Lock()
        self.lh = None
        self.conn = None

    def configure(self, config):
#        #polling period was used in case of thread
#        set_attribute(self, 'polling_period', 120, config, int)
        set_attribute(self, 'cache_life', 10, config, int)
        set_attribute(self, 'retry_count', 3, config, int)
        set_attribute(self, 'reply_timeout', 1, config, float)
        super(OmniProto, self).configure(config)  
        if self.debug:
            msglog.log('omnimeter', msglog.types.INFO, 
                       "OMNIMETER in configure")
            msglog.log('omnimeter', msglog.types.INFO, "Enabled:%d" 
                       % (self.enabled))
            msglog.log('omnimeter', msglog.types.INFO, "Debug:%d" 
                       % (self.debug))

    def configuration(self):
        config = super(OmniProto, self).configuration()
        get_attribute(self, 'cache_life', config)
        get_attribute(self, 'retry_count', config)
        get_attribute(self, 'reply_timeout', config)
#        #polling period was used in case of thread        
#        get_attribute(self, 'polling_period', config)
        return config

    def start(self):
        if self.is_running():
            raise EAlreadyRunning()
        self.conn = gdconn.FrameworkSerialPortWrapper(self.parent)
        self.lh = gdlh.SimpleLineHandler(self.conn)
        try:
            self.lh.connect()
        except EAlreadyOpen:
            msglog.log('omnimeter', msglog.types.ERR, 
                       'COM Port already in use')
            raise
            
        #stx seems to be the core of omnimeter.
        #though stx shouldn't be here, it ensures we recieve data properly
        #inspite of variable no. of FEs
        self.stx_obj = om.start_byte()
        # starting the polling thread. 
        # Polling thread not being used currently
#        self.start_thread()
        msglog.log('omnimeter', msglog.types.INFO, 
                       "OMNIMETER Protocol started")
        super(OmniProto, self).start()

    def stop(self):
        if not self.is_running():
            raise ENotRunning()
        self.lh.disconnect()
        #have to see some more here ??
        super(OmniProto, self).stop()
        msglog.log('omnimeter', msglog.types.INFO, 
                   "OMNIMETER Protocol stopping")

    def send_request(self, request_obj,
                     response_obj, wait_time=None, numretries=None):
        """API to devices to send a request object and wait for response

        devices may provide wait_time, retry_count else may use defaults
        provided by protocol
        """
        if not self.is_running():
            raise ENotRunning()
        if wait_time is None:
            wait_time = self.reply_timeout
        if numretries is None:
            numretries = self.retry_count
        #have to lock here to ensure, no one drains the port out
        if self.debug:
            msglog.log('omnimeter', msglog.types.INFO, 
                       'wait time and numretries are %s'
                       % str((wait_time, numretries)))
        save_wait_time = wait_time
        self.lock.acquire()
        try:
            while numretries:
                try:
                    self.conn.drain()
                    wait_time = save_wait_time
                    t0 = time.time()
                    #loopback object
                    res = self.lh.send_request_with_response(request_obj, 
                                                             request_obj, 
                                                             wait_time)
                    if not res:
                        #should not happen
                        raise EWriteError()
                    wait_time = wait_time - (time.time() - t0)
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO, 
                                   'got loopback-resp:time left:%f' 
                                   % wait_time)
                    if wait_time < 0 :
                        #can never be
                        raise ETimeout() 
                    #wait until we get first byte of packet
                    res = 0    
                    while not res:
                        t0 = time.time()
                        res = self.lh.receive_response(self.stx_obj, wait_time)
                        wait_time = wait_time - (time.time() - t0)
                        if wait_time < 0 :
                            raise ETimeout()
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO, 
                                   'got first byte. wait time:%f' % wait_time)
                    res = self.lh.receive_response(response_obj, 
                                                   wait_time)
                    if not res:
                        raise EInvalidMessage()
                    return
                except:
                    numretries -= 1
        finally:
            self.lock.release()
        if self.debug:
            msglog.log('omnimeter', msglog.types.INFO,
                       'Exhausted no. of retries. Raising last exception')
        raise 

#      def start_thread():
#          """
#          Threading support.
#
#          Not being used currently
#          """
#
#          # start the polling thread
#          try:
#              self._thread_instance = threading.Thread(
#                 None, self._omnimeter_thread)
#             self._thread_instance.start()
#          except:
#              msglog.exception()
#
#       
#             def _omnimeter_thread(self):
#          """Polling thread
#
#          This thread will poll the devices at regular polling interval.
#          Polling interval can be configured by the user.
#          Not being used currently"""
#
#         if self.debug:
#             msglog.log('omnimeter', msglog.types.INFO, 
#                        'polling period %d' %(self.polling_period))
#         while self.is_running():
#             t_start = time.time()
#             for meter in self.children_nodes():
#                 try:
#                     t0 = time.time()
#                     meter.read(3)
#                     if self.debug:
#                         msglog.log('omnimeter', msglog.types.INFO, 
#                                    'Meter address %s' % str(meter.address))
#                         msglog.log('omnimeter', msglog.types.INFO, 
#                                    'Time to read %s' % str(time.time() - t0 ))
#                         msglog.log('omnimeter', msglog.types.INFO, 
#                                    'Meter Reading %s' % meter.reading) 
# 	        #i don't think any exception would be raised,
#                 # because read would take care of all the exceptions
#                 except:
#                     msglog.exception()
#             t_end = time.time()
#             time_remain = self.polling_period - (t_end - t_start)
#             if time_remain < 0:
#                 msglog.log('omnimeter', msglog.types.WARN, 
#                            'Polling period too small')
#                 time_remain = 0
#             time.sleep(time_remain)
#         return
