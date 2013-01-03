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
import time
from node import ARMNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from arm import calibration_index as index
from arm import calibration_items as k
from moab.linux.lib.uptime import secs as uptime_secs
##
# Class for analog input on Megatron board.
#
class float_volts(float):
    def __str__(self):
        return '%0.2f' % self
class float_ohms(float):
    def __str__(self):
        return '%0.1f' % self
class float_ma(float):
    def __str__(self):
        return '%0.3f' % self

        
modes = ['volts', 'ohms', 'ma']

class AnalogInput(ARMNode):

    def __init__(self):
        ARMNode.__init__(self)
        self.r0 = 0
        self.r1 = 1 # high voltage mode for safety
        self.r2 = 0
        self.r3 = 0
        self.mode = 'volts'
        self._raw_value = 0
        self._volts = None
        self._ais = None
        self._data_type = float
        self._ttl = 0
        self._value = 0
    ##
    # @see node.ARMNode#configure
    #
    def configure(self, config):
        ARMNode.configure(self, config)
        set_attribute(self, 'mode', 'volts', config, str)
        set_attribute(self, 'ttl', 10.0, config, int)
    def configuration(self):
        cd = ARMNode.configuration(self)
        get_attribute(self, 'mode', cd, str)
        get_attribute(self, 'ttl', cd, str)
        return cd
    def start(self):
        # prepare all the calculations so at run time things go faster
        self.r1 = 1
        self.convert = self.raw_value #default conversion
        # take channel calibration tuple and turn it into a dictionary
        # trim calibration to what we understand.  new stuff would be at end
        calibration = self.coprocessor.calibration['ai%d' % self.id][:len(k)]
        self.calibration = dict(zip(k, calibration))
        self._ratio = self.calibration['ratio']
        self._ai_slope = self.calibration['ai_slope']
        self._ai_offset = self.calibration['ai_offset']
        self._v_5 = self.calibration['v_5']
        self._r3 = self.calibration['r3']
        self._r2 = self.calibration['r2']
        self._r1 = self.calibration['r1']
        self._r0 = self.calibration['r0']
        # for version 2+ get voltage calibration arrays
        if self.coprocessor.calibration.get('version', 1) > 1:
            self._ais = self.coprocessor.calibration['ais%d' % (self.id,)]
            self._volts = self.coprocessor.calibration['volts%d' % (self.id,)]
        # set up signal mode, conversion method and data_type object
        if self.mode not in modes:
            self.mode = 'volts'
        self.r1 = 0
        if self.mode == 'volts':
            self.r1 = 1
            self.convert = self.convert_high_voltage
            self._data_type = float_volts
        elif self.mode == 'ohms':
            self.r1 = 1
            self.r3 = 1
            self.convert = self.convert_high_resistance
            self._data_type = float_ohms
        elif self.mode == 'ma':
            self.r0 = 1
            self.convert = self.convert_current
            self._data_type = float_ma
        channel = self.id
        if channel < 1 or channel > 4:
            raise Exception('channel must be between 1 and 4')
        command = 'ai %d' % self.id
        if self.r0:
            command += ' r0'
        if self.r1:
            command += ' r1'
        if self.r2:
            command += ' r2' # ohms low
        if self.r3:
            command += ' r3' # ohms high
        command += ' scan\r' # lets coprocessor continuously scan instead of conversion upon demand
        self.command = command
        self.hv = 1 # start in high voltage mode
        rsp_dict = self.read_response('adc w 3 64\r') # initialize AI chip
        if rsp_dict['command'] != 'adc':
            raise Exception('command mismatch: %s, should be adc' % (rsp_dict['command'],))
        self.get() # start it by reading once

    ##
    # Get current value for analog input.
    #
    # @param skipCache  Use cached value.
    # @value 0  May use cached value.
    # @value 1  May not use cached value.
    # @return Current value.
    #
    def get(self, skipCache=0):
        t = uptime_secs()
        if self._ttl > t and skipCache == 0: # return cached value
            return self._value
        self._ttl = t + self.ttl # set time of ttl expire
        self._value = self._data_type(self.convert())
        return self._value
    def _get_ai(self):
        dict = self.read_response(self.command)
        if dict['command'] != 'ai':
            raise Exception('command mismatch: %s' % (dict['command'],))
        self._raw_value = dict['values'][-1]
        return self._raw_value
    def convert_high_voltage(self):
        v = self.convert_low_voltage() * self._ratio
        if v < 0.03: # force to 0 for cosmetic reasons 
            v = 0.0
        return v
    def convert_low_voltage(self):
        v = self._convert_low_voltage()
        self._last_voltage = v # save for debugging
        return max(v, 0.0) # limit any negative voltages.  people don't like them
    def _convert_low_voltage(self):
        self._get_ai()
        if self._volts: # version 2 calibration data available
            return self.volts_from(self._raw_value, self._volts, self._ais)
        return (self._raw_value * self._ai_slope) + self._ai_offset
    def volts_from(self, ai_value, volts, ais):
        max_ai = ais[0]
        zero_ai = ais[-1]
        max_v = volts[0]
        zero_v = volts[-1]
        for i in range(1, len(ais)-1): # check each ai value
            ai = ais[i]
            v = volts[i]
            if ai_value > ai: # found range
                #print 'range: ', i, ai, v, max_ai, max_v, ai_value
                mh = (max_v - v) / (max_ai - ai) 
                bh = v - (mh * ai)
                return (ai_value * mh) + bh
            max_ai = ai
            max_v = v
        m = (max_v - zero_v) / (max_ai - zero_ai) 
        b = zero_v - (m * zero_ai)
        return (ai_value * m) + b
    def _hv_to_r(self, v):
        # current in pull up resistor
        i3 = (self._v_5 - v) / self._r3
        # current in voltage divider
        i1 = v / self._r1
        # current in sensor
        iR = i3 - i1
        #print 'i3=', i3, ' i1=', i1, ' iR=', iR
        if iR < 0.000001: # too little current to measure
            return 199999.9
        r = v / iR
        return max(min(r, 199999.0), 0.0) 
    def _lv_to_r(self, v):   
        return max(v / ((self._v_5 - v) / self._r3), 0.0)
    def convert_high_resistance(self):
        # there are two resistance ranges that are used.  Since the resistor
        # is pulled up to 5 volts, an open circuit or a high resistance can
        # lead to the input to the AI chip exceeding the supply voltage of 3.2 volts
        # When this happens, all the other channels are pulled high and readings
        # suffer.  To prevent this, the high range is used to switch in the 
        # 11:1 divider to protect the input.  Once in the high range, it takes
        # a reading in the range 15000-100 to switch to low range.  A direct
        # short to ground will not switch it low range to facilitate using the
        # AI as a DI.
        v = self.convert_low_voltage()  # get raw voltage reading
        #print self.command
        #print 'v=', v
        if self.hv: # high range, means voltage input is higher
            self.command = 'ai %d r1 r3 scan\r' % self.id
            v = v * self._ratio
            #print 'hv mode v=', v
            r = self._hv_to_r(v)
            #print 'hv mode r=', r
            if r > 15000: # keep high resistance mode
                return r
            if r < 100: # keep high resistance mode for short but report 0 ohms
                return 0.0
            #print 'switching to low voltage mode'
            self.command = 'ai %d r3 scan\r' % self.id
            self.hv = 0
            self._get_ai() # to set up new resistor settings
            time.sleep(1.3) # delay to allow another scan of the ai
            v = self._convert_low_voltage()
            #print 'v=', v
        else: # low range resistance
            self.command = 'ai %d r3 scan\r' % self.id
            r = self._lv_to_r(v)
            if (v > 3.2 or r > 16000): # switch to high voltage mode to protect other AI's
                #print 'switching to high voltage mode'
                self.command = 'ai %d r1 r3 scan\r' % self.id
                self.hv = 1
                self._get_ai() # to set up new resistor settings
                time.sleep(1.3)
                v = self._convert_low_voltage()
                #print 'v=', v
                v = v * self._ratio
                return self._hv_to_r(v)
            return r
        # low resistance mode
        return self._lv_to_r(v)
    def convert_low_resistance(self): # assuming r2 and 11:1 divider on
        v = self.convert_high_voltage()
        return max(v / (((self._v_5 - v) / self._r2) - (v / self._r1)), 0.0)
    def convert_current(self):
        return max(1000.0 * self.convert_low_voltage() / self._r0, 0.0)
    def raw_value(self):
        return self._raw_value
def factory():
    return AnalogInput()
