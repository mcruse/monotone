"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
import math, struct
from mpx.lib.translator._translator import Translator
from mpx.lib.exceptions import EInvalidValue, ETimeout
from mpx.lib import msglog
from mpx.lib.node import as_node_url

debug = 1

def get_ref_voltage_from_seq(seq_num):
    seq = struct.unpack('4B', seq_num[0:3])[0]
    vref = (seq & 0xff800000L) >> 23
    if vref == 0:
        return 0
    return 1252352.0 / vref
    
class XbowConversion:
    def __init__(self, caller):
        # a reference back to the node that 'has-a' XbowConversion
        self.caller = caller
        # a reference back to the callers parent - which is our source of 
        # raw values to convert.
        if self.caller.hasattr('ion'):
            self.ion = self.caller.ion
        else:
            self.ion = self.caller.parent
    # convert overridden by subclass to do useful conversions
    # base class returns raw value if an appropriate conversion
    # class was not found.
    def convert(self):
        if debug:
            msg = '%s returning raw value - verify conversion configuration' % as_node_url(self.caller)
            msglog.log('mpx.xbow', WARN, msg)
        return self.ion.parent.get()
            
class BinaryValueFromRaw(XbowConversion):        
    def convert(self): 
        if self.ion.get():
            return 1
        else:
            return 0
        
# computes the voltage of an adc channel using the reference voltage
# (adc_data * 625mV) / 1024
#
class ADCSingleFromRaw(XbowConversion):        
    def convert(self):
        return ((625 * self.ion.get() / 512) - 2500)

# computes the voltage of an adc channel using the reference voltage
# (5 * 625 * adc_prec / 512) - 2500
#
class ADCPrecisionFromRaw(XbowConversion):        
    def convert(self):
        return 5 * ((625 * self.ion.get() / 512) - 2500)

# computes the ADC count of ADXL202E Accelerometer

class AccelFromRaw(XbowConversion):
    def __init__(self, caller):
        XbowConversion.__init__(self, caller)
        # lets us override conversion constants through the callers configuration
        if caller.hasattr('calib_pos_lg'):
            self.calib_pos_lg = self.caller.calib_pos_lg
        else:
            self.calib_pos_lg = 500
        if caller.hasattr('calib_neg_lg'):
            self.calib_neg_lg = self.caller.calib_neg_lg
        else:
            self.calib_neg_lg = 400
            
    def convert(self):
        scale_factor = float((self.calib_pos_lg - self.calib_neg_lg) / 2)
        reading = 1.0 - (self.calib_pos_lg - self.ion.get()) / scale_factor
        reading *= 1000.0
        return reading
        
# computes the temperature reading for a spectrum soil temp sensor
class SoilTempFFromRaw(XbowConversion):
    def convert(self):
        look_up_tbl = [481.8, 404.1, 363.8, 337.2, 317.6, 302.1, 289.4, 278.6,
        269.3, 261.2, 253.9, 247.3, 241.4, 235.9, 230.9, 226.2, 
        221.8, 217.7, 213.9, 210.3, 206.9, 203.6, 200.5, 197.5,
        194.7, 192, 189.4, 186.9, 184.5, 182.2, 180, 177.8, 
        175.7, 173.7, 171.7, 169.8, 167.9, 166.1, 164.4, 162.7, 
        161, 159.4, 157.8, 156.2, 154.7, 153.2, 151.7, 150.3, 
        148.9, 147.5, 146.2, 144.8, 143.5, 142.3, 141, 139.8, 
        138.5, 137.4, 136.2, 135, 133.9, 132.7, 131.6, 130.5, 
        129.4, 128.4, 127.3, 126.3, 125.3, 124.2, 123.2, 122.2, 
        121.3, 120.3, 119.3, 118.4, 117.4, 116.5, 115.6, 114.7, 
        113.8, 112.9, 112, 111.1, 110.2, 109.4, 108.5, 107.7, 
        106.8, 106, 105.1, 104.3, 103.5, 102.7, 101.9, 101.1,
        100.3, 99.5, 98.7, 97.9, 97.1, 96.4, 95.6, 94.8, 
        94.1, 93.3, 92.5, 91.8, 91, 90.3, 89.6, 88.8, 
        88.1, 87.4, 86.6, 85.9, 85.2, 84.5, 83.7, 83, 
        82.3, 81.6, 80.9, 80.2, 79.5, 78.8, 78.1, 77.4, 
        76.7, 76, 75.3, 74.6, 73.9, 73.2, 72.5, 71.8,
        71.1, 70.4, 69.7, 69, 68.4, 67.7, 67, 66.3, 
        65.6, 64.9, 64.2, 63.5, 62.8, 61.5, 60.8, 
        60.1, 59.4, 58.7, 58, 57.3, 56.6, 55.9, 55.2, 
        54.5, 53.8, 53.1, 52.4, 51.7, 51, 50.3, 49.6, 
        48.8, 48.1, 47.4, 46.7, 45.9, 45.2, 44.5, 43.7, 
        43, 42.3, 41.5, 40.8, 40, 39.3, 38.5, 37.7, 
        36.9, 36.2, 35.4, 34.6, 33.8, 33, 32.2, 31.4, 
        30.6, 29.7, 28.9, 28.1, 27.2, 26.4, 25.5, 24.6, 
        23.7, 22.9, 22, 21, 20.1, 19.2, 18.2, 17.3,
        16.3, 15.3, 14.3, 13.3, 12.3, 11.2, 10.2, 9.1, 
        8, 6.9, 5.7, 4.6, 3.4, 2.2, 0.9, -0.3,
        -1.6, -2.9, -4.3, -5.7, -7.1, -8.6, -10.2, -11.7,
        -13.4, -15.1, -16.8, -18.6, -20.5, -22.5, -24.6, -26.8,
        -29.1, -31.6, -34.2, -37, -40.1, -43.4, -47, -51.1, 
        -55.7, -61, -67.3, -75.2, -86, -86, 254, 254]
        try:
            s_temp = look_up_tbl[self.ion.get()]
            return s_temp
        except:
            raise EInvalidValue('value out of range', offset, 'convert()')
        
class TempCFromRaw(XbowConversion):
    def _convert(self):
        raw_tmp = self.ion.get()
        adj_temp = raw_tmp << 2
        if adj_temp == 0:
            return 0
        a = 0.001307050
        b = 0.000214381
        c = 0.000000093
        rthr = 10000 * (1023 - adj_temp) / adj_temp
        temperature = 1 / (a + b * math.log(rthr) + c * math.pow(math.log(rthr),3))
        temperature = temperature - 273.15
        return temperature
    
    def convert(self):
        return self._convert()
		
class TempFFromRaw(TempCFromRaw):        
    def convert(self):
        return ((self._convert() * 9 / 5) + 32)

class LightFromRaw(XbowConversion):
    def convert(self):
        try:
            raw_val = self.ion.get()
            voltage = self.ion.parent.get_ref_voltage_from_seq()
            l_lvl = voltage * self.ion.get() / 1024
            return l_lvl
        except:
            raise ETimeout

def ConversionFactory(class_name, caller):
    # class_name is really provided by user via broadway.xml - we don't want
    # to just eval it.
    conversion_classes = {'LightFromRaw':LightFromRaw,
                          'TempFFromRaw':TempFFromRaw,
                          'TempCFromRaw':TempCFromRaw,
                          'SoilTempFFromRaw':SoilTempFFromRaw,
                          'AccelFromRaw':AccelFromRaw,
                          'ADCPrecisionFromRaw':ADCPrecisionFromRaw,
                          'ADCSingleFromRaw':ADCSingleFromRaw,
                          'BinaryValueFromRaw':BinaryValueFromRaw}
    
    if class_name in conversion_classes.keys():
        return conversion_classes[class_name](caller)
    else:
        msg = 'could not find conversion class %s for %s' % (class_name, as_node_url(caller))
        msglog.log('mpx.xbow', WARN, msg)
        return XbowConversion(caller)
        
