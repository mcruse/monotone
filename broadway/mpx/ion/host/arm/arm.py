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
##  Current firmware version for coprocessor
FIRMWARE_VERSION = 1.016

import select, termios, time, os, array, struct, binascii
from mpx.lib.exceptions import EInvalidResponse,ETimeout

import mpx.lib
from mpx.lib import threading
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, set_attributes, \
     get_attribute, get_attributes
from mpx.lib import msglog
from mpx import properties
from mpx.lib.persistent import PersistentDataObject
from mpx.service import garbage_collector
import cPickle

from moab.linux.lib.megatron import udi_map, UDI_BEGIN, UDI_MAX_LENGTH

debug = 0

default_calibration = {'ai4': "4\xa4Y\xce?$\xe2\xa8A0\n\xd0C\x18\x1d'F+\xcehDz\xe9mF\x1c\x8a7Dx\xe9\xce:\xdf\xc9\xb9\xff\xdf\xfb$@M\x8b\xa5\x00\x7f\xfa\xaf\x00\x00\x04.?\xcd\xa5\x1e\x00/\xf8\x9f@<z\x8d\xff\xed<\xc5@\xa2\x10\x91\x00\x00\x070\xff\xf5\x10\xd1\x00\x0f\xf2O\xff\xf8\x12\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 
                       'ai1': '4\xa4Z\x85?$\xe1\xebA/\xfb\xd3C\x18\t\xcbF+\xc3\xdaDz\xb5\xb3F\x1cr\x02Dy\x1a\x18:&~B\xff\xdf\xed\xbe@M\x91\x97\x00\x7f\xfe\xe7\x00\x00\x046?\xcc:\xe9\x00/g\xeb@<|\x01\xff\xed><@\xa2\x19b\x00\x00\x079\xff\xf5\x0b\xbb\x00\x0f\xf23\xff\xf8\x0e\x13\x00\x00\r\n5\xbf\xb1\xd7@D/d', 
                       'ai3': '4\xa4Z\xe2?$\xe3^A0&\xaeC\x18\tTF+\xe0|Dz\xd1\x97F\x1cy\tDx\xee\\:\xdd\xf7b\xff\xdf\xfb\t@M\x8b\xfa\x00\x7f\xf9\xf7\x00\x00\x04.?\xcd\xad\xc0\x00/\xf8&@<|7\xff\xed:\xc3@\xa2\x15X\x00\x00\x070\xff\xf5\x0e\x0e\x00\x0f\xf0-\xff\xf8\x10\x11\x00\x00\x0c\xf95\xbf\xb21@C\xb5\xe2', 
                       'ai2': '4\xa4Z ?$\xe3!A0\x17TC\x18\x1fZF+\xce\xa3Dz\xe7\xa2F\x1cz\xd0Dx\xf6&:\xa9\xc2\xe1\xff\xdf\xf5\xda@M\x91\xb3\x00\x7f\xff\x0f\x00\x00\x040?\xcd\x1e\xe5\x00/\xc0\xc4@<\x7fY\xff\xed<\x1b@\xa2\x15\xfd\x00\x00\x073\xff\xf5\x10\xba\x00\x0f\xf3\xc6\xff\xf8\x13\x15\x00\x00\r\x005\xbe\x9a\xdf@B\xcbk'}

# calibration indices:
calibration_items = ('ai_slope','ai_offset','ratio','r0','r1','r2','r3','r_10k',
     'zero_v','zero_ai','max_v','max_ai','max_v_out','mid_v','mid_ai',
     'ratio_v','ratio_ai','v_5','ao_5v_out','r0_ai','r2_ai','r3_ai',
     'ao_max_out','ai_ao_fb_slope','ai_ao_fb_offset')

calibration_index = dict(zip(calibration_items, range(len(calibration_items))))

#/* This is a function to figure the Cyclic Redundancy Check of each request */
def getcrc16(aString):
    crc = 0
    for c in aString:
        crc = ((crc << 8) ^ crctab[((crc >> 8) ^ ord(c)) & 255]) & 65535
    return crc

##
# Class for coprocessor module's IO points invisible parent ION.
#
class ARM(CompositeNode):
    # Thread-safe lock.  Should be extended to be process independant.
    _lock = threading.Lock()
    def __init__(self):
        CompositeNode.__init__(self)
        self.debug = 0
        self.is_arm = True
        self.udi = None
        self.fram_data = None
        self.calibration = {}
        self._pdo = None
        self._pdo_lock = threading.Lock()
        self._coprocessor = None

    ##
    # @see mpx.ion.host.Host#configure
    #
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'ncounters', REQUIRED, config, int)
        set_attribute(self, 'nDIs', REQUIRED, config, int)
        set_attribute(self, 'nrelays', REQUIRED, config, int)
        set_attribute(self, 'nAIs', REQUIRED, config, int)
        set_attribute(self, 'nAOs', REQUIRED, config, int)
        set_attribute(self, 'ndallas_busses', REQUIRED, config, int)
        #set_attribute(self, 'nCAN_busses', REQUIRED, config, int)

        # Open the coprocessor devices.
        try:
            if debug: print 'ARM.py about to import megatron from moab'
            from moab.linux.lib import megatron
            self._coprocessor = megatron.get_coprocessor()
            if debug: print 'check version'
            version = self._coprocessor.version()
            if debug: print 'version is: ', version
        except Exception, e:
            msglog.log('broadway',msglog.types.ERR,"Failed to open coprocessor device.")
            msglog.exception()
            version = 0 #force attempt to reload firmware
        if float(version) < FIRMWARE_VERSION:
            # need to load newer version of firmware
            # @TODO
            self.isp(version)
        try:
            # force votage margining circuits to neutral
            rsp = self._coprocessor.read_response('vm cpu 1.0 1.8 3.3 5.0 phy 1.0 2.5 save\r')
            if rsp.get('error',1):
                raise # throw error on None response, error true or bad dict
            self._coprocessor.read_response('vm restore\r')
        except:
                msglog.log('coprocessor', msglog.types.ERR, 
                        'Failed to clear voltage margin %s' % str(rsp))
        if debug: print 'load calibration data from PDO or FRAM'
        try:
            self.get_pdo_info()
        except Exception, e:
            print 'Error reading calibration info', str(e)
            msglog.log('broadway',msglog.types.ERR,"Failed to read calibration info.")
            msglog.exception()

        # Attach the counters, relays and dallas busses to the coprocessor.
        if debug: print 'configure children of ARM'
        config_list = (('mpx.ion.host.arm.counter', 'counter',
                        self.ncounters),
                       ('mpx.ion.host.arm.di', 'DI', self.nDIs),
                       ('mpx.ion.host.arm.ai', 'AI', self.nAIs),
                       ('mpx.ion.host.arm.ao', 'AO', self.nAOs),
                       ('mpx.ion.host.arm.relay', 'relay', self.nrelays),
                       ('mpx.ion.host.arm.dallasbus', 'dallas',
                        self.ndallas_busses),)
                       #('mpx.ion.host.arm.canbus', 'CAN',
                        #self.nCAN_busses))
        for module,prefix,count in config_list:
            for i in range(1,count+1):
                name = prefix + str(i)
                config = {'name':name, 'id':i, 'coprocessor':self, 'parent':self}
                ion = mpx.lib.factory(module)
                ion.configure(config)
        if debug: print 'arm.py configure finished OK'

    # Link to actual coprocessor code.
    def read_response(self, command, *args):
        return self._coprocessor.read_response(command, *args)
    ##
    # Print msg.
    #
    # @param msg  Message to be printed.
    #
    def dump(self, msg):
        for b in msg:
            print "%02x" % (ord(b)),
        print
    def isp(self, version):
        msglog.log('coprocessor', 'warning', 'coprocessor has old %s version firmware. Current version is %s. Please standby for 3 minutes for upgrade. DO **NOT** REMOVE POWER OR INTERRUPT PROCESS!!!!' % (version, FIRMWARE_VERSION))
        # clear voltage margin and di counters fram
        # first clear di counters
        # @todo add clear di counters to bst/fst in production tests and remove this
        try:
            self._coprocessor.read_response('fram 256 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\r')
        except:
            pass # but do nothing else
        # force calibration data to be read from fram next time we start up
        self.clear_pdo()
        try:
            # place coprocessor into ISP mode
            command = 'isp\r'
            dict = self._coprocessor.read_response(command)
            if dict is not None:
                error = dict.get('error')
                if error:
                    raise Exception(str(dict['error']))
                if dict['command'] != 'isp':
                    raise Exception('command mismatch: %s' % (dict['command'],))
                print 'When isp function is finished, cycle power if coprocessor does not restart within 2 minutes.'
            else:
                print 'assuming coprocessor is in ISP mode'
            self._coprocessor.close()
        except:
            msglog.log('coprocessor','error', 'failed to place processor into ISP mode.  Assuming ISP already enabled.  It may be necessary to cycle power after ISP is complete')
        time.sleep(2)
        dir = __file__.split('/')[:-1]
        file_path = '/'.join(dir) + '/m2cp.hex'
        os.system('lpc21isp -wipe -hex %s /dev/ttyS1 38400 12000' % file_path)
        msglog.log('coprocessor', 'information', 'waiting two minutes for coprocessor to restart')
        time.sleep(130)
        msglog.log('coprocessor', 'information', 'restarting coprocessor link')
        self._coprocessor.__init__()
        if self._coprocessor.file is None: 
            msglog.log('coprocessor', 'error', 'Failed to initialize coprocessor channel after ISP.  Try power cycle')
    def show_udi_info(self): # return html table of UDI info
        lines = []
        lines.append('<table border="1">')
        for key in udi_map.keys():
            lines.append('<tr><td>%2d</td><td>%s</td><td>%s</td></tr>' % \
                (key, (udi_map[key] + (' ' * 35))[:37], 
                self._coprocessor.fram_get_udi(key, self.udi)))
        lines.append('</table>')
        return '\n'.join(lines)
    def get_pdo(self): #call while locked
        if self._pdo is None:
            self._pdo = PersistentDataObject(self, dmtype=garbage_collector.GC_NEVER)
            self._pdo.calibration_dict = '(d.' #pickled empty dict
            self._pdo.udi = '(d.' #pickled empty dict
            self._pdo.load()
        return self._pdo
    def clear_pdo(self): # force calibration data to be read from the fram
        self._pdo_lock.acquire()
        try:
            self.get_pdo()
            self._pdo.calibration_dict = '(d.' #pickled empty dict
            self._pdo.udi = '(d.' #pickled empty dict
            self._pdo.save()
        finally:
            self._pdo_lock.release()
    def get_pdo_info(self):
        self._pdo_lock.acquire()
        try:
            save = 0
            self.get_pdo()
            calibration = cPickle.loads(self._pdo.calibration_dict) #dict of node url and output registers
            self.calibration = calibration
            if not self.calibration: 
                msglog.log('coprocessor', 'information', 'retrieving analog calibration information')
                self.calibration = self.get_fram_calibration_data()
                # save calibration back to pdo
                self._pdo.calibration_dict = cPickle.dumps(self.calibration)
                save = 1
            udi = cPickle.loads(self._pdo.udi)
            self.udi = udi
            if not self.udi:
                msglog.log('coprocessor', 'information', 'retrieving udi information')
                try:
                    self.udi = self._coprocessor.fram_read(UDI_BEGIN, UDI_MAX_LENGTH)
                    self._pdo.udi = cPickle.dumps(self.udi)
                    save = 1
                except:
                    msglog.exception()
                    msglog.log('coprocessor', 'ERROR',
                               'unable to retrieve UDI information')
            if save:
                self._pdo.save()
        finally:
            self._pdo_lock.release()
    def get_fram_calibration_data(self):
        #print '\nCalibration data:'
        answer = {}
        fmt = '9flf2lflflf5l2f'
        try:
            calibration = self._coprocessor.fram_get('calibration')
        except:
            calibration = None
            msglog.exception()
        if calibration is None:
            msglog.log('coprocessor', 'ERROR',
                       'This board is not calibrated or calibration data unavailable.  Using defaults')
            calibration = default_calibration
        # expand calibration data
        answer['version'] = calibration.get('version',1)
        for channel in (1,2,3,4):
            if answer['version'] > 1:
                ais = calibration['ais%d' % (channel,)]
                ais = binascii.a2b_base64(ais)
                ais = struct.unpack('9l', ais)
                volts = calibration['volts%d' % (channel,)]
                volts = binascii.a2b_base64(volts)
                volts = struct.unpack('9f', volts)
                answer['ais%d' % (channel,)] = ais
                answer['volts%d' % (channel,)] = volts
            s = calibration.get('ai%d' % channel, None)
            if s:
                if answer['version'] > 1: # un-encode before unpacking
                    s = binascii.a2b_base64(s) # was encoded to save space
                ai = struct.unpack(fmt, s)
                #print 'ai %d = (' % channel, ai, ')'
                answer['ai%d' % channel] = ai
        return answer
    def reload_calibration(self):
        self.clear_pdo()
        self.get_pdo_info()
def factory():
    return ARM()
