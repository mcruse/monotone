"""
Copyright (C) 2001 2002 2003 2006 2010 2011 Cisco Systems

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
# TODO:
# 0.  Handle configuring the temperature sensor and values returned from
#     unusual configurations?
# 2.  Need some level of 'auto'
# 3.  See FIXME comments.
# 4.  Change 'C', 'F', and 'K' as lazily initialized inherant children.
# 5.  Need a cache layer to poll devices that require a conversion period.
import mpx.lib
from mpx.lib.node import CompositeNode
from mpx.lib.node import ConfigurableNode
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.exceptions import EInvalidValue
from time import sleep
from device import Device
from crc import crc_of
from mpx.lib.exceptions import EInvalidResponse,ETimeout
from mpx.lib import msglog
from struct import unpack
from moab.linux.lib.uptime import secs as uptime_secs

_models = {'18B20':16,
           '18S20':2}
def _as_divisor(model):
    try:
        return _models[model.upper()]
    except KeyError:
        raise EInvalidValue('model', model)
def _as_model(divisor):
    for entry in _models.items():
        if entry[1] == divisor:
            return entry[0]
    raise EInvalidValue('divisor', divisor)

##
# Base class for simple Dallas tempurature sensors.
#
class Temperature(Device):
    ##
    # Class to retreive the celsius temp of the sensor.
    #
    class C(ConfigurableNode):
        ##
        # @see mpx.lib.node.ConfigurableNode#configure
        #
        def configure(self, config):
            ConfigurableNode.configure(self, config)
            # set ion attribute to be a reference to parent.
            set_attribute(self, 'ion', self.parent, config, as_node)
            set_attribute(self, 'divisor', REQUIRED, config, float)
        
        ##
        # Get object's configuration.
        #
        # @return Configuration dictionary.
        #
        def configuration(self):
            config = ConfigurableNode.configuration(self)
            get_attribute(self, 'ion', config, as_node_url)
            get_attribute(self, 'divisor', config, str)
            return config

        ##
        # Get celsius temperature.
        #
        # @return Temperature from sensor in celsius.
        #
        def get(self, skipCache=0):
            return self.ion.get(skipCache)/self.divisor
    
    ## End of inner-class C
    
    ##
    # Configure object.  Instanciates and configures
    # children for getting temp in degress C, F, Kelvin.
    #
    # @see device.Device#configure
    #
    def configure(self, config):
        Device.configure(self, config)
        self.debug = 0
        self.result = None
        self.bad_crc_count = 0
        self._last_read_time = 0
        self.scan_period = None
        # Create the inherent C, F and K children.
        set_attribute(self, 'model', '18B20', config, _as_divisor)
        c = self.C()
        c.configure({'name':'C', 'parent':self, 'divisor':self.model})
        f = mpx.lib.factory('mpx.lib.translator.f_from_c')
        f.configure({'name':'F', 'parent':self, 'ion':c})
        k = mpx.lib.factory('mpx.lib.translator.k_from_c')
        k.configure({'name':'K', 'parent':self, 'ion':c})
        self.parent.conversion_list[self] = None #register for mass conversions

    ##
    # @return configuration dictionary.
    #
    def configuration(self):
        config = Device.configuration(self)
        get_attribute(self, 'model', config, _as_model)
        get_attribute(self, 'scan_period', config, float)
        return config
    
    ##
    # Get the raw value from the temperature sensor.
    #
    # @return Device's value.
    #
    def get(self, skipCache=0):
        if self.result == None:
            if self.bad_crc_count:
                raise ETimeout('communications error for: %s' % self.as_node_url())
            raise ETimeout('no data yet for: %s' % self.as_node_url())
        return self.result  # value is placed here by another thread

    def _read(self):
        dallas = self.parent
        dallas.reset()
        dallas.matchrom(self.address)
        dallas.readscratch()
        result = dallas.readbytes(9)
        if crc_of(result) == 0:
            t = unpack('<h', result[:2])[0]
            self.result = t
            if self.bad_crc_count > 10: #was logged as bad
                msglog.log('DallasBus', 'information', 'Resumed: %s' % \
                                as_node_url(self))
            self.bad_crc_count = 0
            t = uptime_secs()
            self.scan_period = t - self._last_read_time
            self._last_read_time = t
            if self.debug:
                print "TEMPERATURE SENSOR: _read value", self.result
        else:
            if self.bad_crc_count < 11:
                self.bad_crc_count += 1
                if self.bad_crc_count == 10:
                    self.result = None #return ETimeout to gets
                    raise EInvalidResponse('Failed read ten times: %s' % \
                                       as_node_url(self))
            if self.debug:
                print "TEMPERATURE SENSOR: BAD CRC", result
        return
    def fail(self):
        self.result = None

def _read_temperature_sensors_for(dallas):
    dallas.lock()
    try:
        _do_read(dallas)
    finally:
        dallas.unlock()
def _do_read(dallas):
    try:
        dallas.reset()
        dallas.skiprom()
        dallas.convert()
        sleep(1)
    except:
        msglog.exception()
        for sensor in dallas.conversion_list.keys():
            sensor.fail()
    else:
        for sensor in dallas.conversion_list.keys():
            sensor._read()
    return

def factory():
    return Temperature()
