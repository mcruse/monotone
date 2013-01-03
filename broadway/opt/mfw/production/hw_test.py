"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
#=----------------------------------------------------------------------------
# hw_test.py
#
# Run a series of manufacturing tests on a mediator.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------
# TBD's
#  - Make stdout unbuffered and get rid of all the stupid calls to flush()
#=----------------------------------------------------------------------------

import getopt
import os
import sys
import time

from burnin_test import BurninTester
from hwinfo import HardwareInfo
from production_test import ProductionTester
from versioner import hwtest_version
from test_framework import all_tests
from cmdexec import execute_command
from mpx import properties
import msg
from msg import *

class KeyWordAssist(dict):
    def __call__(self, *args):
        pairs = []
        for i in range(0, len(args), 2):
            pairs.append((args[i],args[i+1]))
        # Modification to enable in python 2.2
        pairs = dict(pairs)
        self.update(pairs)
        return self.copy()

def show_usage():
#--------1---------2---------3---------4---------5---------6---------7-------x-|
    print """
The hardware test program has several options:
    -h: This screen.
    -n: In burnin mode, do ping tests to exercise the ethernet interface(s).
        Ignored if running in production mode.
    -m: In burnin mode, execute modem tests.  Ignored if running in
        production mode.
    -v: Print program version and copyright info and exit.
    -d: Execute the Dallas test.
    -b: Analyze the Bootlog for warnings and errors.
    -c: Execute the Relays and Counters test.
    -i: Execute the I2C bus test.
    -e: Execute the Ethernet test.
    -r: Execute the quick RAM test.
    -t: Execute the robust RAM test.
    -s: Execute the Serial test.
    -u: Execute the USB test.
    -a: Provides information about this Mediator.
    -A: Sets the Assembly ID associated with this Mediator.
    -M: Sets the manufacturers serial #
    -D: Sets the Distribution Facilites serial #
    -C: Sets the Cisco serial #
    -P: Sets the Mediators Product ID.
    -0: Sets the Mediators MAC address for eth0.
    -1: Sets the Mediators MAC address for eth1."""
#--------1---------2---------3---------4---------5---------6---------7-------x-|
    return

def _set_attr(attrs, attr_name):
    if not attrs:
        for attr in all_tests:
            attrs[attr] = False
    attrs[attr_name] = True

def main():
    burnin = 0
    burnin_network = 0
    burnin_modem = 0
    quiet_mode = False
    
    if os.path.basename(sys.argv[0]) == 'burnin':
        burnin = 1

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hmnvdbciersuatqA:M:D:C:P:0:1:',
            ['help', 'modem', 'network', 'version', 'dallas', 'bootlog',
             'relayscounters', 'i2c', 'ethernet', 'ram', 'serial', 'usb',
             'about', 'ramstress', 'quiet', 'assembly=', 'manufacturing=', 
             'distribution=', 'cisco=', 
             'productid=', 'mac0=', 'mac1='])
    except getopt.GetoptError, e:
        print e
        return 1
    
    attrs = KeyWordAssist()
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            show_usage()
            return 1

        if opt in ('-m', '--modem'):
            if burnin == 1:
                burnin_modem = 1
            continue

        if opt in ('-n', '--network'):
            if burnin:
                burnin_network = 1
            continue
         
        if opt in ('-d', '--dallas'):
            _set_attr(attrs, 'dallas')
            continue
        
        if opt in ('-b', '--bootlog'):
            _set_attr(attrs, 'bootlog')
            continue
        
        if opt in ('-c', '--relayscounters'):
            _set_attr(attrs, 'relayscounters')
            continue
        
        if opt in ('-i', '--i2c'):
            _set_attr(attrs, 'i2c')
            continue
        
        if opt in ('-e', '--ethernet'):
            _set_attr(attrs, 'ethernet')
            continue
        
        if opt in ('-r', '--ram'):
            _set_attr(attrs, 'ram')
            continue
        
        if opt in ('-t', '--ramstress'):
            _set_attr(attrs, 'ramstress')
            continue
        
        if opt in ('-s', '--serial'):
            _set_attr(attrs, 'serial')
            continue
        
        if opt in ('-u', '--usb'):
            _set_attr(attrs, 'usb')
            continue
        
        if opt in ('-q', '--quiet'):
            quiet_mode = True
            continue
        
        if opt in ('-v', '--version'):
            print 'Mediator hw_test version %s\nCopyright (c) 2009 by Cisco Systems, Inc.' % (hwtest_version())
            return 1
        
        hw_info = HardwareInfo()
        if arg:
            arg = arg.strip()
        if opt in ('-A', '--assembly'):
            if arg:
                try:
                    hw_info.set_assembly(arg)
                    return 1
                except:
                    print 'Error writing Assembly ID.'
            return -1
        
        if opt in ('-M', '--manufacturing'):
            if arg:
                try:
                    hw_info.set_serialno(arg)
                    return 1
                except:
                    print 'Error writing Manufacturers serial number'
            return -1
            
        if opt in ('-D', '--distribution'):
            if arg:
                try:
                    hw_info.set_serialno_df(arg)
                    return 1
                except:
                    print 'Error writing DF\'s serial number'
            return -1
            
        if opt in ('-C', '--cisco'):
            if arg:
                try:
                    hw_info.set_serialno_cisco(arg)
                    return 1
                except:
                    print 'Error writing Cisco serial number'
            return -1
            
        if opt in ('-P', '--productid'):
            if arg:
                try:
                    hw_info.set_pid(arg)
                    return 1
                except:
                    print 'Error writing Product ID.'
            return -1
        
        if opt in ('-0', '--mac0', '-1', '--mac1'):
            if opt in ('-0', '--mac0'):
                which = 0
            else:
                which = 1
            if arg:
                try:
                    hw_info.set_mac_addr(which, arg)
                except:
                    print 'Error setting mac address'
            return -1
        
        if opt in ('-a', '--about'):
            about = 'Model number: %s\n' % hw_info.model()
            about += 'Product ID: %s\n' % hw_info.get_pid()
            about += 'Framework version: %s\n' % properties.COMPOUND_VERSION
            about += 'MOE version: %s\n' % properties.MOE_VERSION
            about += 'Manufacturing serial number: %s\n' % hw_info.serialno()
            about += 'Distribution serial number: %s\n' % hw_info.serialno_df()
            about += 'Cisco serial number: %s\n' % hw_info.serialno_cisco()
            about += 'Assembly number: %s\n' % hw_info.get_assembly()
            about += 'eth0 MAC address: %s\n' % hw_info.mac_addr(0)
            if hw_info.model() in ('TSWS', '2400', '2500'):
                about += 'eth1 MAC address: %s\n' % hw_info.mac_addr(1)
            message(about)
            return 1
        
    verbose_printing = not bool(attrs)
    if verbose_printing:
        message('Initializing the test framework, this will take up to two minutes...')
    try:
        fd = open('/dev/avr')
        fd.close()
    except:
        message('Error - the framework must be stopped before running tests')
        return -1

    if burnin:
        hw_tester = BurninTester(burnin_network, burnin_modem, **attrs)
    else:
        enable_eth_tests = 1
        hw_tester = ProductionTester(enable_eth_tests, **attrs)

    preflight_ok = hw_tester.preflight_check()
    if not preflight_ok:
        return 0
    if verbose_printing and not quiet_mode:
        message('done.')
    if not quiet_mode:
        hw_tester.print_prerun_summary()
    msg.QUIET = quiet_mode
    hw_tester.runtests()
    msg.QUIET = 0
    if quiet_mode:
        if hw_tester.tests_in_error():
            msg_fail()
        else:
            msg_pass()
    else:
        hw_tester.report_results()
    return 1
if __name__ == '__main__':
    exit_status = not main()
    sys.exit(exit_status)

#=- EOF ----------------------------------------------------------------------
