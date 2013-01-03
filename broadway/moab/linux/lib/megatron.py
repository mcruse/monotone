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
##
#

# TODO:
# 2.  Need to recover from tracebacks better.  Some sort of reset on the dev?
#
import select, termios, time, os, array, struct, threading
from exceptions import Exception

class _MpxException(Exception):
    ##
    # The constructor for the base MPX exception class.
    #
    # @param *args  Tuple of all non-keyword args.
    # @param **keywords Dictionary of keyword args.
    def __init__(self, *args, **keywords):
        Exception.__init__(self, *args)
        self.keywords = keywords
        self._print_exc_str = None
    def __str__(self):
        if len(self.args) == 1:
            return str(self.args[0])
        elif len(self.args) > 1:
            return str(self.args)
        return ''
    def _as_dict(self):
        d = exception_as_dict__(self)
        d['keywords'] = self.keywords
        return d
    def __repr__(self):
        return repr(self._as_dict())

class _ETimeout(_MpxException):
    pass

class _EInvalidResponse(_MpxException):
    pass

TXT = 0
DEC = 1
HEX = 2
FIX = 3

udi_list = (
    ('Product_ID-PID', 27, TXT),
    ('HW_Version_ID-VID', 2, HEX),
    ('Chassis_serial_number-SN', 16, TXT),
    ('PCA_serial_number', 16, TXT),
    ('MAC_Address-ETH0', 6, HEX),
    ('MAC_Address-ETH1', 6, HEX),
    ('PCA_Item_Number-Class_Code', 2, DEC),
    ('PCA_Item_Number-Base_Number', 3, DEC),
    ('PCA_Item_Number-Version', 1, DEC),
    ('PCA_Item_Number-Revision', 1, HEX),
    ('Chassis_Item_Number(800)-Class_Code', 2, DEC),
    ('Chassis_Item_Number(800)-Base_Number', 3, DEC),
    ('Chassis_Item_Number(800)-Version', 1, DEC),
    ('Chassis_Item_Number(800)-Revision', 1, HEX),
    ('Deviation_Number_1', 3, HEX),
    ('Deviation_Number_2', 3, HEX),
    ('Deviation_Number_3', 3, HEX),
    ('Deviation_Number_4', 3, HEX),
    ('Deviation_Number_5', 3, HEX),
    ('CPU_Clock_Speed', 2, DEC),
    ('Memory_DIMM_Interface_Speed', 3, DEC),
    ('Memory_Configuration', 3, DEC),
    ('Diagnostics_Version', 2, FIX),
    ('Main_Unit_RMA_Number', 1, HEX),
    ('Main_Unit_RMA_History', 1, HEX),
    ('OEM_String', 19, TXT),
    ('Entity_Name', 9, TXT),
    ('Product_description', 25, TXT),
    )

udi_dynamic_map = {}

UDI_BEGIN = 0

udi_address = {}
udi_map = {}
addr = UDI_BEGIN
index = 1
for u in udi_list:
    udi_map[index] = u[0]
    udi_address[index] = addr
    addr += u[1]
    index += 1

UDI_MAX_LENGTH = addr - UDI_BEGIN
FRAM_DICT_HEADER = 0x200 # 2 bytes for dictionary length and 2 for CRC
FRAM_DICT = FRAM_DICT_HEADER + 4
FRAM_TOP = 2047
FRAM_DICT_MAX_LENGTH = FRAM_TOP - FRAM_DICT

debug = 0
crctab = [ \
 0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7, \
 0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF, \
 0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6, \
 0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE, \
 0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485, \
 0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D, \
 0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4, \
 0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC, \
 0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823, \
 0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B, \
 0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12, \
 0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A, \
 0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41, \
 0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49, \
 0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70, \
 0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78, \
 0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F, \
 0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067, \
 0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E, \
 0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256, \
 0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D, \
 0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405, \
 0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C, \
 0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634, \
 0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB, \
 0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3, \
 0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A, \
 0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92, \
 0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9, \
 0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1, \
 0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8, \
 0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0 ]

#/* This is a function to figure the Cyclic Redundancy Check of each request */
def getcrc16(aString):
    crc = 0
    for c in aString:
        crc = ((crc << 8) ^ crctab[((crc >> 8) ^ ord(c)) & 255]) & 65535
    return crc

##
# Class for coprocessor module's ION.
#
class ARM(object):
    # Thread-safe lock.  Should be extended to be process independant.
    _lock = threading.Lock()

    def __init__(self):
        self.debug = 0
        self.udi = None
        self.fram_data = None
        self._watchdog = 60 # sixty second counter to keep coprocessor active
        self._watchdog_thread = None
        self._lock_pool = []
        self._fifo_locks = [threading.Lock(),] # start with one released lock

        # Open the coprocessor devices.
        try:
            if debug: print 'open coprocessor port'
            self.open()
            if debug: print 'port open, verbose off'
            self.verbose_off()
            self._watchdog_thread = threading.Thread(None, self._tick, 'ARMWD')
            self._watchdog_thread.setDaemon(True)
            self._watchdog_thread.start()
            print 'coprocessor link opened OK'
        except Exception, e:
            print 'exception opening coprocessor port', str(e)
            if self.file:
                self.file.close()
                self.file = None
    def __del__( self ):
        if self._watchdog_thread:
            self._watchdog = 0
            self._watchdog_thread = None
        if self.file:
            try:
                self.file.close()
                self.file = None
            except:
                pass
    def _tick(self, *args, **kw):
        while self._watchdog:
            if self._watchdog > 1:
                self._watchdog -= 1
                time.sleep(1)
            elif self._watchdog > 0:
                self._watchdog = 60
                try:
                    self.verbose_off()
                    if debug: print 'refreshed coprocessor idle loop'
                except:
                    print 'coprocessor error in watchdog'
        if debug: print 'end coprocessor thread'

    # Actual coprocessor code.

    ##
    # Lock coprocessor comm channel for safe access.
    # Simple locks do not release blocked tasks in the order in which they
    # acquire the lock; it can be random and lead to some tasks waiting
    # a long time to be serviced.  This implements a queue of locks that release
    # the locks in the order they were aquired.
    #
    def lock(self):
        self._lock.acquire()
        try:
            # maintain pool of locks to avoid constant creation but create
            # new ones as needed
            if not self._lock_pool: 
                self._lock_pool.append(threading.Lock())
            # get a lock from the pool, acquire it and place it at the end of queue
            fifo_lock = self._lock_pool.pop()
            # next thread will have to wait for this lock to be release
            fifo_lock.acquire() 
            self._fifo_locks.append(fifo_lock) 
            # get the lock set up from the previous thread
            fifo_lock = self._fifo_locks[-2] 
        finally:
            self._lock.release()
        # now wait for previous thread to release the lock, if still locked.
        # by the time this lock is released, it will be at the beginning of the
        # queue
        fifo_lock.acquire()
        return
    ##
    # Unlock coprocessor to allow access.
    #
    def unlock(self):
        self._lock.acquire()
        try:
            # take the lock we acquired, release it and place it back in pool
            fifo_lock = self._fifo_locks.pop(0)
            fifo_lock.release()
            self._lock_pool.append(fifo_lock) # to be recycled
            # release the lock blocking next waiting thread
            self._fifo_locks[0].release()
        finally:
            self._lock.release()
        return
    ##
    # Print msg.
    #
    # @param msg  Message to be printed.
    #
    def dump(self, msg):
        for b in msg:
            print "%02x" % (ord(b)),
        print
        
    def open(self, dev="/dev/ttyS1", baud=115200, non_blocking=0):
        self.file= open(dev, "w+b", 0)
        self.poll = select.poll()
        self.poll.register(self.file, select.POLLIN)
        iflags = 0
        oflags = 0
        cflags = termios.CREAD | termios.CLOCAL | termios.HUPCL
        lflags = 0
        baud = getattr(termios,'B%u' % baud) #baud rate contant
        cflags = cflags | getattr(termios,'CS%u' % 8) #eight bits
        iflags = iflags | termios.IGNPAR | termios.IGNBRK #ignore chars with parity errors. why? parity check not enabled
        flags = termios.tcgetattr(self.file.fileno())
        flags[0] = iflags
        flags[1] = oflags
        flags[2] = cflags
        flags[3] = lflags
        flags[4] = baud
        flags[5] = baud
        flags[6][termios.VMIN] = 1 # 0
        flags[6][termios.VTIME] = 0 #10
        termios.tcsetattr(self.file.fileno(), termios.TCSANOW, flags)
        self.verbose = False
        self.command_retries = 0
        self.last_bad_response = None
        self.buf = ''
        self.baud = baud
    def close(self):
        self._watchdog = 0
        try:
            self.poll.unregister(self.file)
        except:
            #print '***failed to unregister port file object from poll***'
            pass
        self.file.close()
        self.file = None
    def readline(self, timeout=10):
        t_end = time.time() + timeout
        #poll_list = self.poll.poll(0)
        while 1:
            #if len(self.poll.poll(0)):
            #print 'about to select'
            ready,_,_ = select.select([self.file.fileno()],[],[], timeout)
            #print 'select returned'
            # If select was used with a timeout, and the timeout occurs, it
            # returns with empty lists -> thus abort read operation.
            # For timeout == 0 (non-blocking operation) also abort when there
            # is nothing to read.
            #print 'ready: ', repr(ready)
            if not ready:
                if debug: print 'readlin select timeout'
                break   # timeout
            self.wait(0.1)
            read_buf = os.read(self.file.fileno(), 512)
            self.pieces.append(read_buf)
            if debug: print 'read_buf: ', repr(read_buf)
            self.buf += read_buf
            pos = self.buf.find('\n')
            if pos >= 0:
                if debug: print 'buffer found newline'
                line, self.buf = self.buf[:pos+1], self.buf[pos+1:]
                if debug: print repr(line), repr(self.buf)
                return line
            #read_buf = self.file.readline()
            t_end = time.time() + timeout
            if (time.time() >= t_end): 
                if debug: print 'readline idle timeout'
                break
        line, self.buf = self.buf, ''
        return line
    def write(self, s):
        # reset timer to prevent watchdog from triggering
        self._watchdog = 60
        return self.file.write(s)
    ##
    # Send message to coprocessor.
    #
    # @param msg  Message to send.
    # @return  Response sent back from coprocessor.
    #
    def read_response(self, command, timeout = 10, retries=3, *args): #read until a full response is received
        try:
            self.lock()
            for tries in range(retries):
                # clear left overs
                limit = 0
                self.pieces = []
                while self.readline(0):
                    #print 'leftover'
                    limit += 1
                    if limit > 100:
                        print 'coprocessor readline limit exceeded'
                        break
                #self.wait(0.1)
                self.write(command)
                if debug: print 'command: ', repr(command)
                #self.wait(0.2)
                answer = ''
                self.pieces = []
                tend = time.time() + timeout
                # skip echo of command
                while True: #read and discard until we see a { character
                    read_buf = self.readline(timeout) #.tostring()
                    if read_buf.find('{') >= 0:
                        answer = read_buf[read_buf.find('{'):]
                        pre = read_buf[:read_buf.find('{')]
                        if pre:
                            if debug: print 'pre: ', repr(pre)
                        break
                    if read_buf and debug: print repr(read_buf),
                    if time.time() > tend:
                        break # timeout and try again
                if len(answer): # { character received, get the rest of the response
                    # once the first { received, read through end of line
                    tend = time.time() + 15
                    if debug: print 'answer: ', repr(answer)
                    try:
                        if answer.find('\x00') >= 0:
                            if debug: print '**********************null char in response*******************'
                            raise _EInvalidResponse('null char')
                        dict = eval(answer[:answer.find('\r')])
                        error = dict.get('error')
                        if error:
                            raise _EInvalidResponse(str(dict['error']))
                        return dict
                    except:
                        self.command_retries += 1
                        self.wait(0.3)
                        limit = 0
                        while self.readline(0.5):
                            limit += 1
                            if limit > 1000:
                                raise _EInvalidResponse('coprocessor port streaming garbage')
                        self.last_bad_response = repr(answer)
                        if debug: print 'response exception'
            if debug: 
                print '*** Coprocessor Response eval error: ', repr(answer)
                print repr(self.pieces), self.command_retries
            raise _ETimeout('no response from coprocessor')
        finally:
            self.unlock()
    def verbose_off(self):
        dict = {}
        limit = 0
        while not dict.has_key('verbose'):
            dict = self.read_response('verbose 0\r')
            #print repr(dict)
            limit += 1
            if limit > 20: raise Exception('**** repeated errors while setting Verbose mode ****')
        if dict['verbose'] == 0:
            return
        #print 'verbose was true'
        # verbose command is a toggle. 
        # If verbose is True, repeat command should turn it False
        dict = self.read_response('verbose\r')
        if dict['verbose'] == 0:
            return
        #print 'failed to set verbosity mode'
        raise Exception('failed to set verbosity mode')
    def led(self, rgb, pattern, period):
        try:
            self.read_response('led %d %d %d\r' % (rgb, pattern, period))
        except Exception, e:
            try:
                if float(self.version()) < 1.015:
                    print 'Info: Unable to set LED pattern.'
                    print '  Coprocessor Firmware will be upgraded when Framework starts'
            except:
                print 'set coprocessor LED exception'
                print str(e)
    def wait(self, delay):
        timeout = time.time() + delay
        while time.time() < timeout:
            time.sleep(0.1)
    ##
    # Get the version of the coprocessor module.
    #
    # @return coprocessor Version number.
    #
    def version(self):
        command = 'version\r'
        dict = self.read_response(command)
        if dict['command'] != 'version':
            raise _EInvalidResponse('command mismatch: %s' % (dict['command'],))
        return dict['version']        
    def isp(self):
        print 'coprocessor', 'WARNING', 'coprocessor firmware upgrade required'
    def fram_read(self, location, length):
        answer = []
        for i in range(0, length, 16):
            command = 'fram %d\r' % (location,)
            dict = self.read_response(command)
            if dict is None:
                raise Exception('no response')
            error = dict.get('error')
            if error:
                raise Exception(str(dict['error']))
            if dict['command'] != 'fram':
                raise Exception('command mismatch: %s' % (dict['command'],))
            #print dict
            answer.append(array.array('B', dict['values']).tostring())
            location += 16
        return ''.join(answer)[:length]
    def fram_get_udi(self, key, udi=None):
        name, length, type = udi_list[int(key) - 1]
        address = udi_address[int(key)]
        if udi: # previous copy of udi contents
            value = udi[address:address+length]
        else: # no previous copy, read directly from FRAM
            value = self.fram_read(address, length)
        if type == TXT:# get string and trim blanks
            result = value.strip()
        elif type == DEC: # decimal number
            # pad leading zero to make length 4
            # format with leading zero if less than 100
            result = '%02d' % (struct.unpack('!L', ('\x00\x00\x00' + value)[-4:])[0],)
        elif type == FIX: # decimal number
            # pad leading zero to make length 4
            # format with leading zero if less than 100
            result = '%0.3f' % ((struct.unpack('!L', ('\x00\x00\x00' + value)[-4:])[0])/1000.0,)
        elif type == HEX: # hex ascii pairs 00 11 22 AA FF
            result = ' '.join(['%02X' % (ord(c),) for c in value])
        return result
    def fram_get_dict(self):
        scratch = self.fram_read(FRAM_DICT_HEADER, 4)
        dict_length, dict_crc = struct.unpack('!HH', scratch)
        #print 'fram dictionary length: ', dict_length
        if dict_length > 0 and dict_length <= FRAM_DICT_MAX_LENGTH:
            scratch = self.fram_read(FRAM_DICT, dict_length)
            print
            crc = getcrc16(scratch)
            if dict_crc == crc:
                answer = eval(scratch)
                print
                return answer
            else:
                print 'fram crc mismatch'
        else:
            print 'fram string wrong length'
        return {}
    def fram_get(self, key):
        if self.fram_data is None:
            self.fram_data = self.fram_get_dict()
        return self.fram_data.get(key, None)
    def show_udi_info(self):
        for key in udi_map.keys():
            print '%2d ' % key,
            print (udi_map[key] + (' ' * 35))[:37],
            print self.fram_get_udi(key)

_coprocessor = None
def get_coprocessor():
    global _coprocessor
    if _coprocessor is None:
        _coprocessor = ARM()
    return _coprocessor

def setConfiguring():
    if debug: print 'set configuring led pattern on megatron'
    get_coprocessor().led(4, 2, 30) # slow blue saw tooth
def setStarting():
    if debug: print 'set starting led pattern on megatron'
    get_coprocessor().led(4, 1, 5) # medium blue square wave
def setRunning():
    if debug: print 'set running led pattern on megatron'
    get_coprocessor().led(2, 3, 70) # slow green triangle
def setError():
    if debug: print 'set error led pattern on megatron'
    get_coprocessor().led(1, 1, 20) # medium red square wave
def setPanic():
    if debug: print 'set panic led pattern on megatron'
    get_coprocessor().led(1, 1, 1) # fast red square wave
def setInstalling():
    global _coprocessor
    if debug: print 'set installing led pattern on megatron'
    get_coprocessor().led(2, 1, 2) # fast green square wave
    get_coprocessor()._watchdog = 0 # don't need keep alive thread
    time.sleep(1) # make sure there is enough time for thread to end
    _coprocessor = None
def setIdle():
    if debug: print 'set idle led pattern on megatron'
    get_coprocessor().led(7, 3, 50) # very slow white triangle

