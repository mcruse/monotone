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
#=----------------------------------------------------------------------------
# config.py
#
# Class that reads and manages the common config file for both the hw_test
# and hwtest_svr programs.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import ConfigParser

class TestConfig(object):
    def __init__(self, burnin, cfg_filename):
        # In the 'Defaults' section
        self._def_ipaddr = None
        self._def_macaddr = None

        # In the 'Servers' section
        self._hwtest_server = None
        self._hwtest_port = None
        self._ntpserver = None

        # In the 'TestParams' section
        self._bootlog = None
        self._burnin_iterations = None
        self._callout = None
        self._hangup = None
        self._memtester = None
        self._stressmemtester = None
        self._modem_test_iterations = None
        self._netperf_eth0 = None
        self._netperf_eth0_port = None
        self._netperf_eth1 = None
        self._netperf_eth1_port = None
        self._ping_count_eth0 = None
        self._ping_host_eth0 = None
        self._ping_count_eth1 = None
        self._ping_host_eth1 = None
        self._relay1_counts = None
        self._relay2_counts = None
        self._i2c_rtc_addr = None
        self._sensor_chip = None

        ###
        # Read the config file...
        config = ConfigParser.ConfigParser()
        config.read(cfg_filename)

        self._def_ipaddr = self._get_config(config, 'Defaults', 'def_ipaddr')
        assert(self._def_ipaddr != None)

        self._def_macaddr = self._get_config(config, 'Defaults', 'def_macaddr')
        assert(self._def_macaddr != None)

        self._hwtest_port = self._get_config_int(config, 'Servers', 'hwtest_port')
        assert(self._hwtest_port != None)

        self._hwtest_server = self._get_config(config, 'Servers', 'hwtest_server')
        assert(self._hwtest_server != None)

        self._ntpserver = self._get_config(config, 'Servers', 'ntp_server')
        assert(self._ntpserver != None)

        self._bootlog = self._get_config(config, 'TestParams', 'bootlog')
        assert(self._bootlog != None)

        self._burnin_iterations = self._get_config_int(config, 'TestParams', 'burnin_iterations')
        assert(self._bootlog != None)

        self._callout = self._get_config(config, 'TestParams', 'callout')
        assert(self._callout != None)

        self._hangup = self._get_config(config, 'TestParams', 'hangup')
        assert(self._hangup != None)

        self._i2c_rtc_addr = self._get_config(config, 'TestParams', 'i2c_rtc_addr')
        assert(self._i2c_rtc_addr != None)

        if burnin:
            self._memtester = self._get_config(config, 'TestParams', 'burnin_memtester')
        else:
            self._memtester = self._get_config(config, 'TestParams', 'prod_memtester')
        assert(self._memtester != None)
        
        self._stressmemtester = self._get_config(config, 'TestParams', 'stress_memtester')

        self._modem_test_iterations = self._get_config_int(config, 'TestParams', 'modem_test_iterations')
        assert(self._modem_test_iterations != None)

        self._netperf_eth0 = self._get_config(config, 'TestParams', 'netperf_eth0')
        assert(self._netperf_eth0 != None)

        self._netperf_eth0_port = self._get_config(config, 'TestParams', 'netperf_eth0_port')
        assert(self._netperf_eth0_port != None)

        self._netperf_eth1 = self._get_config(config, 'TestParams', 'netperf_eth1')
        assert(self._netperf_eth1 != None)

        self._netperf_eth1_port = self._get_config(config, 'TestParams', 'netperf_eth1_port')
        assert(self._netperf_eth1_port != None)
        
        self._ping_count_eth0 = self._get_config_int(config, 'TestParams', 'ping_count_eth0')
        assert(self._ping_count_eth0 != None)

        self._ping_host_eth0 = self._get_config(config, 'TestParams', 'ping_host_eth0')
        assert(self._ping_host_eth0 != None)
        
        self._ping_count_eth1 = self._get_config_int(config, 'TestParams', 'ping_count_eth1')
        assert(self._ping_count_eth1 != None)

        self._ping_host_eth1 = self._get_config(config, 'TestParams', 'ping_host_eth1')
        assert(self._ping_host_eth1 != None)

        self._relay1_counts = self._get_config_int(config, 'TestParams', 'relay1_counts')
        assert(self._relay1_counts != None)

        self._relay2_counts = self._get_config_int(config, 'TestParams', 'relay2_counts')
        assert(self._relay2_counts != None)

        self._sensor_chip = self._get_config(config, 'TestParams', 'sensor_chip')
        assert(self._sensor_chip != None)

        return

    def _get_config(self, config, section, value):
        if config.has_option(section, value):
            return config.get(section, value)
        return None

    def _get_config_int(self, config, section, value):
        if config.has_option(section, value):
            return config.getint(section, value)
        return None

    def bootlog(self):
        return self._bootlog

    def callout(self):
        return self._callout

    def def_ipaddr(self):
        return self._def_ipaddr

    def def_macaddr(self):
        return self._def_macaddr

    def hwtest_port(self):
        return self._hwtest_port

    def hwtest_server(self):
        return self._hwtest_server

    def hangup(self):
        return self._hangup

    def modem_test_iterations(self):
        return self._modem_test_iterations

    def memtester(self):
        return self._memtester
    
    def stressmemtester(self):
        return self._stressmemtester

    def netperf_eth0(self):
        return self._netperf_eth0

    def netperf_eth0_port(self):
        return self._netperf_eth0_port

    def netperf_eth1(self):
        return self._netperf_eth1

    def netperf_eth1_port(self):
        return self._netperf_eth1_port

    def ntpserver(self):
        return self._ntpserver

    def ping_count_eth0(self):
        return self._ping_count_eth0

    def ping_host_eth0(self):
        return self._ping_host_eth0
    
    def ping_count_eth1(self):
        return self._ping_count_eth1

    def ping_host_eth1(self):
        return self._ping_host_eth1

    def relay1_counts(self):
        return self._relay1_counts

    def relay2_counts(self):
        return self._relay2_counts

    def rtc_i2c_addr(self):
        return self._rtc_i2c_addr

    def sensor_chip(self):
        return self._sensor_chip

#=- EOF ----------------------------------------------------------------------
