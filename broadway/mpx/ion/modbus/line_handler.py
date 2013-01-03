"""
Copyright (C) 2001 2002 2007 2008 2009 2010 2011 Cisco Systems

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
# 2.  Add auto-detect.

from time import sleep
from moab.linux.lib.uptime import secs as now

from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ETimeout
from mpx.lib.exceptions import EInvalidMessage
from mpx.lib.modbus import base, command, exception, response
from mpx.lib import msglog

from mpx.service.device_manager import device_manager_node

from monitor import ModbusMonitor
from monitor import ModbusDeviceIdentifier

from mpx import properties

# LineHandler modules should supply the following functions:
buffer = base.buffer
crc = base.crc

class LineHandler(CompositeNode):
    CHARACTER_TIME = 'Character Time'
    ABSOLUTE = 'Absolute'
    def __init__(self):
        CompositeNode.__init__(self)
        self.timeout = REQUIRED
        self.debug = REQUIRED
        self.interval_calculation = REQUIRED
        self.silent_interval_characters = REQUIRED
        self.silent_interval_absolute = REQUIRED
        self.__silent_interval = None # Initialized in start()
        self.__last_character_time = now() # OK, this isn't true...
        self.retries = 3 #used by register_cache.RegisterCache._refresh
        self.report_timeouts = 1 #0 == try but give back last good value
        return
    def start(self):
        if self.interval_calculation == self.CHARACTER_TIME:
            self.__silent_interval = (self.silent_interval_characters *
                                      self.port.seconds_per_character())
        elif self.interval_calculation == self.ABSOLUTE:
            self.__silent_interval = self.silent_interval_absolute
        else:
            raise EInvalidValue('interval_calculation',
                                self.interval_calculation)
        CompositeNode.start(self)
        return
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'timeout', 2.5, config, float)
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'interval_calculation', self.CHARACTER_TIME,
                      config, str)
        set_attribute(self, 'silent_interval_characters', 3.5, config, float)
        set_attribute(self, 'silent_interval_absolute', 50.0/1000.0, config,
                      float)
        set_attribute(self, 'retries', 3, config, int)
        set_attribute(self, 'report_timeouts', 1, config, int)
        self.port = self.parent
        self.port_url = self.port.as_node_url()
        if not self.port.is_open():
            self.port.open()
        self.ip = None
        self.device_manager = device_manager_node()
        return
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'timeout', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'interval_calculation', config, str)
        get_attribute(self, 'silent_interval_characters', config, str)
        get_attribute(self, 'silent_interval_absolute', config, str)
        get_attribute(self, 'retries', config, str)
        get_attribute(self, 'report_timeouts', config, str)
        return config

    def buffer(self, initializer=None):
        return base.buffer(initializer)

    def crc(self, byte_array):
        return base.crc(byte_array)

    def __wait_for_port(self, timeout=10.0):
        chatter_timeout = now() + timeout
        last_character_time = self.__last_character_time
        silent_interval = self.__silent_interval
        silence_timeout = last_character_time + silent_interval
        chatter = self.port.drain()
        while now() < chatter_timeout:
            if len(chatter):
                chatter = self.port.drain()
                last_character_time = now()
                silence_timeout = last_character_time + silent_interval
                continue
            if now() > silence_timeout:
                # OK, there has been no "chatter" for the required interval
                self.__last_character_time = last_character_time
                return
            sleep_timeout = silence_timeout - now()
            if sleep_timeout > 0.0:
                sleep(sleep_timeout)
            chatter = self.port.drain()
        raise ETimeout(
            'Failed to detect %.2d millisecond silent interval '
            'after %d seconds.' % (silent_interval/1000.0, timeout)
            )
    def command(self,cmd, ip=None):
        b = cmd.buffer
        timeout = cmd.timeout(self.timeout)
        # @fixme Caching monitors based on address could speed things up.
        monitor = self.device_manager.monitor_from_kw(
            ModbusDeviceIdentifier, 
            device_class="modbus",
            port=self.port_url, 
            address=cmd.slave_address)
        self.port.lock()
        try:
            self.__wait_for_port()
            self.port.write(b)
            self.port.flush()
            header = buffer()
            # All Modbus responses are at least five bytes in length.
            bytesleft = 5
            discarded = 0
            timeleft = timeout

            # If this is a Megatron RS485 port then consume echoed transmit characters
            if properties.HARDWARE_CODENAME == 'Megatron':
                megatron_485 = self.parent.name in ('com3', 'com4', 'com5', 'com6')
                if megatron_485:
                    expiration = now() + timeout
                    try:
                        self.port.read(header, len(b), timeleft)
                        # We can check the received data here. If it is not what we sent then we have a
                        # transmit error. Might be a collision.
                        if (header != b):
                            msglog.log('MODBUS', msglog.types.WARN, 'Transmitted message corrupt: Collision?')
                        del(header[:])
                    except:
                        msglog.exception()

            expiration = now() + timeout
            while bytesleft:
                self.port.read(header, bytesleft, timeleft)
                bytesleft = 0
                while header and not header[0]:
                    header.pop(0)
                    bytesleft += 1
                if bytesleft:
                    discarded += bytesleft
                    timeleft = expiration - now()
                    if self.debug:
                        print "Modbus.LinHandler: Discard %d 0s" % bytesleft
                    if timeleft <= 0:
                        raise ETimeout("Timeout discarding %d 0s" % discarded)
            if header[1] & 0x80:
                self.__last_character_time = now()
                e = cmd.exception(exception.factory)(self, header)
                raise e
            resp = cmd.response(response.factory)(self, header, timeout)
            self.__last_character_time = now()
            if (resp.slave_address != cmd.slave_address or
                resp.function != cmd.function):
                # Not a response to this command, ignore it
                raise exception.EModbusMismatch()
        except Exception, e:
            monitor.notify_exception(e)
            raise # Reraise the exception for processing...
        else:
            monitor.notify_success()
        finally:
            self.port.unlock()
        return resp

    def scan(self, scan_range=range(1,248), verbose=0):
        list = []
        for slave_address in scan_range:
            try:
                cmd = command.ReportSlaveID(slave_address)
                if verbose:
                    print '%02X (%3d): ' % (slave_address, slave_address)
                resp = self.command(cmd)
                if self.debug:
                    print resp
                list.append(resp)
            except exception.EModbusResponse, e:
                if verbose:
                    print '%02X (%3d): ' % (slave_address, slave_address),
                    print e
                e.slave_id = response.ReportSlaveID.bogus_id
                e.run_status = response.ReportSlaveID.bogus_status
                e.data = response.ReportSlaveID.bogus_data
                list.append(e)
            except KeyboardInterrupt:
                print 'Exitting due to keyboard interrupt.'
                return list
            except Exception, e:
                if verbose:
                    print e
            except:
                if verbose:
                    print "."
        return list
    def increase_retries(self):
        self.retries += 1
    def decrease_retries(self):
        self.retries -= 1
        if self.retries < 1:
            self.retries = 1
    #returns a list of tuples that contain info about how well the device is
    #communicating.  
    def error_report(self):
        answer = []
        devices = filter(lambda x: hasattr(x,'caches'), self.children_nodes()) 
        for d in devices:
            for c in d.caches:
                answer.append((c.ion.name, c.start, c.error_rate,
                    c.error_count,))
        return answer
    #clear the raw error counters
    def clear_error_counts(self):
        devices = filter(lambda x: hasattr(x,'caches'), self.children_nodes()) 
        for d in devices:
            for c in d.caches:
                c.error_count = 0

def factory():
    return LineHandler()
