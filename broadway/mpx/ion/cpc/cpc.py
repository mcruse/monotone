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
import time

from mpx.lib import msglog
from mpx.lib import socket
from mpx.lib import threading

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.debug import _debug
from mpx.lib.exceptions import *
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.msglog.types import *
from mpx.lib.scheduler import scheduler
from moab.linux.lib import uptime

from cpc_decode import *

debug = 0
CSI = '\x1b[' #ANSI escape
CSI_Reset = CSI+'0m'
CSI_RED = CSI + '41;37;1m'
CSI_CYAN = CSI + '46;37;1m'
CSI_GREEN = CSI + '42;37;1m'

class CPC(CompositeNode): #node to represent a device on the CPC network
    def __init__(self, *args):
        super(CPC, self).__init__(*args)
        self.ip = None
        self.port = 1025 #all seem to use 1025
        self.starting = 0
    def configure(self, config):
        super(CPC, self).configure(config)
        set_attribute(self, 'ip', self.ip, config, str)
        set_attribute(self, 'port', self.port, config, int)
    def configuration(self):
        config = super(CPC, self).configuration()
        get_attribute(self, 'ip', config, str)
        get_attribute(self, 'port', config, str)
        return config

class Device(CompositeNode): #line handler for CPC screen scraper
    def __init__(self, *args):
        super(Device, self).__init__(*args)
        self.login_status = None
        self.socket = None
        self.user = 'USER'
        self.password = 'PASS'
        self.device_number = 0
        self.__running = 0
        self.timeout = 10
        self.service_thread = None #thread used for packet exchanges
        self.retry_schedule = None
        self.active_screen = None
        self.response_queue = threading.Queue()
        self.default_screen = ScreenDecoder()
        self.read_buffer = ''
        self.debug = debug
        self.error_counter = 0
    def configure(self, config):
        super(Device, self).configure(config)
        set_attribute(self, 'user', self.user, config, str)
        set_attribute(self, 'password', self.password, config, str)
        set_attribute(self, 'device_name', self.name, config, str)
        if debug: self.debug = debug #override configuration is module is in debug
    def configuration(self):
        config = super(Device, self).configuration()
        get_attribute(self, 'user', config, str)
        get_attribute(self, 'password', config, str)
        get_attribute(self, 'device_name', config, str)
        get_attribute(self, 'loop_time', config, str)
        return config
    def start(self):
        self.starting = 1
        super(Device, self).start()
        self.restart()
        #start a thread that polls all the screens (children)
    def stop(self):
        super(Device, self).stop()
        self.__running = 0
        self.shutdown()
    def restart(self):
        self.shutdown() #start from a known state
        if self.open_socket():
            if self.login():
                if self.debug: print 'login successful - start polling'
                self.service_thread = threading.ImmortalThread(None, self.poll_screens, 'CPC', reincarnate=self.poll_error)
                self.service_thread.start()
                self.__running = 1
                return 1
        self.shutdown()
        self.retry_schedule = scheduler.after(60.0,self.restart)
        msglog.log(INFO, 'CPC', 'retry starting CPC device in 60 seconds')
        return 0
    def poll_screens(self): #main loop of driver
        screens = filter(lambda c: isinstance(c, Screen), self.children_nodes())
        start_time = time.time()
        for s in screens: #ripple down through all the screens and subscreens and get the values
            try:
                if self.service_thread is None: return #shut down
                s.poll() #sends the keys strokes and decodes the finial page
                self.send_key('f9') #does not clear the screen
                for i in range(2):
                    self.poll_for_incomming_packets()
                self.error_counter = 0 #flag to indicate at least one page is working
            except:
                if self.service_thread is None: return #shut down
                self.error_counter += 1
                msglog.exception()
                if self.debug: print CSI_RED+'Device Poll Exception'+CSI_Reset
                self.send_key('f9')
        self.active_screen = None #just to make sure
        self.loop_time = time.time() - start_time
        if self.starting:
            if not self.debug:
                self.starting = 0 #only report once if debug is off.
            msglog.log(INFO, 'CPC', 'scan completed in: %d seconds' % (self.loop_time,))
        if self.debug: print 'poll loop'
    def poll_for_incomming_packets(self): #return ACK responses and handle commands from CPC
        #if self.debug: print 'enter poll_for_incoming_packets'
        pkt = self.read() #block in here until data shows up
        pobj = find_response_type(pkt)
        if len(pkt) > pobj.pkt_len: #possibly read in two packets catenated together
            self.read_buffer = pkt[pobj.pkt_len:]
            if self.debug: print CSI_RED+'unread: ', len(self.read_buffer), CSI_Reset
        if type(pobj) == ScreenUpdate: #command to update screen object
            self.handle_screen_update(pobj)
        elif type(pobj) == InitScreenCmd: #command from cpc
            self.handle_screen_init(pobj)
        elif pobj: # put it into queue for 
            return pobj
        else: #unknown packets type
            msglog.log(WARN, 'CPC', 'Unknown packet type: %s' % (repr(pkt),))
        return None
    def wait_for_response(self):
        then = uptime.secs()
        answer = self.poll_for_incomming_packets()
        while answer is None:
            if uptime.secs() > (then + self.timeout):
                break
            answer = self.poll_for_incomming_packets()
        return answer
    def poll_error(self):
        if self.error_counter > 10:
            self.service_thread.should_die()
            self.error_counter = 0
            self.restart()
        pass #maybe do something if an exception occurs during poll?
    def handle_screen_update(self, pobj):
        #if self.debug: print 'enter handle_screen_update' 
        try:
            #figure out which screen node to update and let it extract values
            if self.active_screen: #the node that most recently sent key strokes
                self.active_screen.update(pobj) #let the active screen get its values
            elif self.default_screen:
                self.default_screen.parse(pobj)
        except:
            msglog.exception()
            if self.debug: print CSI_RED+'Handle Screen Update exception'+CSI_Reset
            #send back ACK
        self.write(ScreenUpdateAck(self.device_number))
    def handle_screen_init(self, pobj):
        if self.debug: print 'enter handle_screen_init' 
        #not much to do for this
        self.write(InitialScreenRequest(self.device_number))
    def open_socket(self): #call to start or restart the connection to the CPC device
        if self.debug: print 'enter open_socket' 
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #, self.timeout)
            result = self.socket.connect((self.parent.ip, self.parent.port), self.timeout)
            time.sleep(2)
            if self.debug: 'socket opened'
            return 1
        except:
            msglog.exception()
        return 0
        #log into CPC
    def shutdown(self): #clean up anything left over from (trying to) run(ning)
        if self.debug: print 'enter shutdown'
        self.__running = 0
        try:
            self.retry_schedule.cancel()
        except:
            pass
        self.retry_schedule = None
        if self.service_thread:
            self.service_thread.should_die()
            self.service_thread = None
            time.sleep(5) #give the last exchange a chance to finish
        try:
            if self.socket:
                self.logout()
                self.socket.close()
        except:
            msglog.exception()
            print 'CPC Device close socket error'
        self.socket = None
        time.sleep(2.0) #give the socket a couple of seconds to close before allowing it to reopen.
    def read(self, count=2048, timeout=None):
        if self.socket is None: return None
        if self.read_buffer: #read have 'unread' bytes to deal with first
            answer = self.read_buffer
            self.read_buffer = ''
            return answer
        #if self.debug:
            #print 'Read from socket: ', count, self.socket
        if timeout is None:
            timeout = self.timeout
        rcvd = self.socket.recv(count, timeout)
        answer = rcvd[:]
        self.read_buffer = '' #buffer used to "unread" concatentated packets
        if len(answer) == count: #cooincidence?  I don't think so...
            print CSI_RED+'length == count'+CSI_Reset
            try:
                rcvd = self.socket.recv(count, 1)
                answer += rcvd[:]
                #print repr(answer)
            except:
                pass #if it was a cooincidence, just continue
        #if self.debug:
            #_debug.dump(answer, 'Read from socket')
        return answer
    def write(self, buffer):
        if self.socket is None: return
        buffer = str(buffer) #convert outgoing packet object to string
        #if self.debug:
            #_debug.dump(buffer, 'TcpConnection write bytes: ')
        self.socket.send(buffer, self.timeout)
    def drain_socket(self):
        try:
            bytes = self.read(8192, 2)
            if self.debug > 1: print 'drained ', len(bytes), ' bytes'
        except:
            pass
    def login(self): #send the initial series of packets to get started
        if self.debug: print 'start login'
        try:
            self.drain_socket()
            if self.debug: print 'write device list request'
            self.write(DeviceListRequest())
            self._device_list = DeviceListResponse(self.read())
            self.device_number = self._device_list.units()[self.device_name]
            if self.debug: print 'write login request'
            self.write(LoginRequest(self.device_number, self.user, self.password))
            self._login_response = LoginResponse(self.read())
            if self.debug: print 'write request 3'
            self.write(Request3(self.device_number))
            self._response3 = Response3(self.read())
            if self.debug: print 'write request 4'
            self.write(Request4(self.device_number))
            self._response4 = Response4(self.read())
            if self.debug: print 'write request 5'
            self.write(Request5(self.device_number))
            self._response5 = self.poll_for_incomming_packets() #Response5(self.read()) #may get first screen update before response
            if self.debug: print 'login successful'
            for i in range(10): #get the first screen complete before moving on to new pages
                self.poll_for_incomming_packets()
            self.send_key('f9')
            for i in range(10): #get the first screen complete before moving on to new pages
                self.poll_for_incomming_packets()
            return 1
        except:
            print 'CPC login failed'
            msglog.exception()
        return 0
    def logout(self):
        try:
            buffer = str(SignOffRequest1(self.device_number)) + str(SignOffRequest2(self.device_number, self.user)) #combine two pkts into one
            self.write(buffer)
            self._device_list = SignOffResponse(self.read())
        except:
            msglog.exception()
    def send_key(self, key): #send a 'key' packet to the device and wait for reply packet
        #convert key to proper key code
        if key in KEYS.keys(): #legal key found
            if self.debug: print CSI_CYAN+'CPC sending key: ', key, CSI_Reset
            self.write(KeyDown(self.device_number, key))
            self.wait_for_response() #need to check for proper response?
        else:
            raise EInvalidValue()
    def set_active_screen(self, node):
        self.active_screen = node
    def all_texts(self):
        answer = 'All Text elements from device\n'
        answer += repr({'user':self.user, 'password':self.password,
                        'device_name':self.device_name, 'name':self.name})
        answer += '\n'
        sub_pages = filter(lambda c: isinstance(c, Screen), self.children_nodes())
        for s in sub_pages: #sub pages MUST only be pages that can return to this one with a F10
            answer += s.all_texts()
        return answer
class Screen(CompositeNode): #node to represent a screen from the Insite terminal mode
    def __init__(self, *args):
        super(Screen, self).__init__(*args)
        self.screen = None
        self.key_path = None
        self.timeout = 10.0
        self.last_screen = None #screen contents once entire screen read in completely
        self.points_screen = None #screen contents at the moment all child points are accounted for
        self.screen_cleared = 0
    def configure(self, config):
        super(Screen, self).configure(config)
        set_attribute(self, 'key_path', self.key_path, config, str)
        set_attribute(self, 'timeout', self.timeout, config, float)
        self.debug = self.parent.debug
    def configuration(self):
        config = super(Screen, self).configuration()
        get_attribute(self, 'key_path', config, str)
        return config
    def get_name(self, aname, screen=None):
        if screen is None:
            screen = self.points_screen
        if screen:
            return screen.get_name(aname)
        return None
    def find_x_y(self, x, y, screen=None):
        if screen is None:
            screen = self.points_screen
        if screen:
            return screen.find_x_y(x,y)
        return None
    def poll(self, key_to_parent=None): #key to parent is either F9 for menu or F10 for previous screen
        self.debug = self.parent.debug
        if self.key_path is None:
            return
        self.goto(self.key_path)
        sub_pages = filter(lambda c: isinstance(c, Screen), self.children_nodes())
        first = 1
        for s in sub_pages: #sub pages MUST only be pages that can return to this one with a F10
            if first:
                first = 0
            else:
                if self.debug: print 'Send Key to return to Parent', key_to_parent
                self._send_key('f10')
            
            s.poll() #F10 from this child page will bring focus back to this page and ready for next child
    def goto(self, key_path): #send keys to destination pages & absorb all values
        path = self.key_path
        path = path.lower()
        keys = path.split(' ') #turn string into list of keywords - pun intended - that will be sent to device
        self.set_active_screen(self) #allow changes to this screen
        self.screen = None #after final key, clear the screen object to get a fresh decode
        eos = 1 #default to wait to make sure no more data
        for k in keys:
            eos = self._send_key(k)
        #self.screen = None #after final key, clear the screen object to get a fresh list of texts decoded
        if self.debug > 1: print 'start looking for values from screen'
        #now wait for string that indicated we have read in the page.
        points = filter(lambda c: isinstance(c, Point), self.children_nodes())
        point_count = len(points)
        then = uptime.secs()
        if self.debug > 1: print 'remaining points: ', [p.name for p in points]
        while points: #keep polling until all points have been seen at least once
            #filter out points that have received values since clearning screen
            points = filter(lambda p: p._get(self.screen) is None, points)
            if self.debug > 1 and len(points): print 'remaining points: ', [p.name for p in points]
            if uptime.secs() > (then + self.timeout):
                if self.debug: 
                    print CSI_RED+'Timedout waiting for screen values'+CSI_Reset   
                    if len(points): print 'remaining points: ', [p.name for p in points]
                break #timeout has occured
            self.poll_for_incomming_packets()
        self.points_screen = self.screen #make new values available to point nodes
        if eos: #true if "screen complete" was received so _send_key did not wait around for new elements to stop showing up
            eop = 0
            for i in range(20): #read in rest of screen for getting points list
                old_count = len(self.screen.texts)
                self.poll_for_incomming_packets()
                if self.screen_complete: break #this flag is reset when a zero length update is recevied
                if old_count == len(self.screen.texts):
                    if eop: break #no new points displayed for 2nd time, we are done.
                    eop = 1
            else:
                if self.debug: print CSI_RED+'Screen did not complete for value page'+CSI_Reset            
        self.last_screen = self.screen #if any new values came since nodes were satisfied, make available for texts() command
        self.set_active_screen(None) #block any further changes to this screen
        if self.debug:
            if points:
                print CSI_RED+'CPC timeout on screen', self.as_node_url(),
                for p in points:
                    print p.name,
                print ' were all not read'+CSI_Reset
            else:
                print CSI_GREEN+'CPC completed '+str(point_count)+' points for screen:', self.as_node_url(), CSI_Reset
    ## called from Device node when it receives screen update packets  for the "active_screen"
    def update(self, pobj):
        if self.screen is None:
            self.screen = ScreenDecoder() #get fresh clean screen
            self.screen_complete = 0
            self.screen_cleared = 0
        old_count = len(self.screen.texts)
        old_points = self.screen.texts.values()
        self.screen.parse(pobj)
        if self.debug > 1: print "number of new items: ", len(self.screen.texts) - old_count,\
             ' items: ', self._texts(filter(lambda v: v not in old_points, self.screen.texts.values()))
        try:
            if pobj.pkt_count == 0:
                self.screen_complete = 1 #flag for goto to stop waiting for screen to complete
                if self.debug > 1: print CSI_GREEN+'Screen Complete'+CSI_Reset
        except:
            print 'update packet did not have pkt_count attr'
        try:
            self.screen_cleared = pobj.screen_cleared
            if self.screen_cleared:
                if self.debug > 1: print CSI_GREEN+'Screen Cleared'+CSI_Reset
        except:
            print 'update packet did not have screen_cleared attr'
        

    ## these methods cascade up to the parent - this screen node can have other screen nodes as children
    def _send_key(self, key):
        self.screen_complete = 0
        self.screen = None #force new screen text elements
        self.send_key(key)
        eop = 0 #two updates with no new points means screen is done
        for i in range(10): #get screen updates before moving to next key
            old_count = -1
            if self.screen: #not first time through loop
                old_count = len(self.screen.texts)
            self.poll_for_incomming_packets()
            if key == 'down' and i > 0: return 1 #speed up 'down' keys
            if self.screen_cleared: 
                if self.debug > 1: print 'key acked by clear screen detected'
                return 1 #a clear screen commnad means our last keystroke was received but there may be more of the screen to read
            if self.screen and (len(self.screen.texts) == old_count): 
                if eop: 
                    if self.debug > 1: print 'key acked by lack of new screen elements'
                    return 0 #tell "goto" that nothing changing on screen
                eop = 1 #two passes with no new points means page is done
            #if self.screen_complete: break #this flag is reset when a zero length update is recevied
        else:
            if self.debug: print CSI_RED+'Screen did not complete for send key'+CSI_Reset   
        return 1 #we don't know if there is more to read

    def send_key(self, key):
        try:
            self.parent.send_key(key)
        except EInvalidValue,e:
            raise EInvalidValue(WARN, 'CPC', 'unknown key %s used by node %s' % (key, self.as_node_url()))
    def poll_for_incomming_packets(self):
        return self.parent.poll_for_incomming_packets()
    def set_active_screen(self, node):
        self.parent.set_active_screen(node)
    def _texts(self, texts):
        answer = '\n' + self.as_node_url() + ',' + self.key_path + \
            ',' + str(self.timeout) + '\n'
        if texts:
            texts.sort()
            y = -1
            for t in texts:
                if t.y != y: 
                    answer += '\n' #group all equal x's on the same line
                else:
                    answer += ', '
                answer += repr(t)
                y = t.y
            answer += '\n'
        return answer
    def texts(self):
        return self._texts(self.points_screen.texts.values())
    def all_texts(self):
        answer = self.texts()
        sub_pages = filter(lambda c: isinstance(c, Screen), self.children_nodes())
        for s in sub_pages: #sub pages MUST only be pages that can return to this one with a F10
            answer += s.all_texts()
        return answer
        
class Point(CompositeNode): #node to represent a screen from the Insite terminal mode
    def __init__(self, *args):
        super(CompositeNode, self).__init__(*args)
        self.match_text = None
        self.x = None
        self.y = None
        self._value = None
    def configure(self, config):
        super(Point, self).configure(config)
        set_attribute(self, 'match_text', self.match_text, config, str)
        set_attribute(self, 'x', self.x, config, int)
        set_attribute(self, 'y', self.y, config, int)
    def configuration(self):
        config = super(Point, self).configuration()
        get_attribute(self, 'match_text', config, str)
        get_attribute(self, 'x', config, str)
        get_attribute(self, 'y', config, str)
        return config
    def _get(self, screen=None):
        if self.x:
            if self.y: #not None, use x y location to get value
                answer = self.parent.find_x_y(self.x, self.y, screen)
                if answer:
                    return answer[0].text
        if self.match_text:
            answer = self.parent.get_name(self.match_text, screen)
            if answer:
                return answer
        return None
    def get(self, skipcache=None):
        answer = self._get()
        if answer is not None:
            for conversion in (int, float): #can add custom conversion methods after float
                try:
                    self._value = conversion(answer)
                    break
                except:
                    pass
            else:
                self._value = answer.strip()
        return self._value #return old value is new one is not available due to page refresh

        
        