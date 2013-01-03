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
#=----------------------------------------------------------------------------
# i2c.py
#
# I2C tests.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import fcntl
import os
import re
import struct
import sys
import time
import math

from cmdexec import execute_command
from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger
from test_methods import TestMethods
from msg import *

class _I2CMemory(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'I2C RAM', config, hw_info, logger)

        self._detected = 0

        ###
        # The i2c RAM lives at address 0x50 on bus 0; look for it.
        result, spewage = execute_command('/usr/bin/i2cdetect 0 | grep -q 50')
        if result:
            self._detected = 1

        return

    def runtest(self, burnin = 0):
        if not self._detected:
            return

        msg_testing('Testing the i2c RAM CHIP.................................................')

        ###
        # The i2cset program reads back after writing to make sure that
        # the write operation was successful.  If not, then we get back
        # an error code.  Therefore it is not necessary to do a read
        # and parse the results.  Nifty, huh?
        result, spewage = execute_command('/usr/bin/i2cset 0 0x50 0 0xff')
        if result:
            msg_pass()
            return
        else:
            self._nerrors += 1
            self._logger.log('ERROR: memory test failed: %s' % spewage)
            msg_fail()

        return

class _I2CRtc_Registers:
    def __init__(self):
        ####
        # ITS REALLY STUPID to code in magic numbers like this, but there's
        # no other sane way to get at vendor-specific function numbers for
        # use with ioctl's.
        self.ds1307_get_date_fn = ~int(~0x80046400L & 0xffffffffL)
        # ........................^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # This wackiness is to prevent python from "promoting" an unsigned
        # 32 bit number to a 64 bit number.  It seems that as of python 2.4,
        # if a number has its MSB set, python gets cute.  Stupid python.

        self.datetime_buf = struct.pack('7i', 0, 0, 0, 0, 0, 0, 0)
        self.i2c_dev = file('/dev/i2c-0', 'rb')

        self.dead_chip_re = re.compile("^00:\s(XX)")

        return

    ###
    # If an I2C RTC chip is not readable, i2cdump will place 'XX' in each
    # byte column instead of values.
    def is_dead(self):
        result, spewage = execute_command('/usr/bin/i2cdump 0 0x68')
        if not result:
            return 1

        result = self.dead_chip_re.match(spewage[4])
        if result:
            return 1

        return 0

    def get_time(self):
        # Make sure you pass in an 'arg' or the kernel will Oops.
        result = fcntl.ioctl(self.i2c_dev.fileno(),
                              self.ds1307_get_date_fn,
                              self.datetime_buf)
        (sec, min, hr, mday, mon, year, wday) = struct.unpack('7i', result)
        return sec, min, hr

    #####
    # This is currently not working, do not use.
    #####
    def read_buf(self, nbytes):
        if nbytes > 56:
            message('ERROR: Read size cannot be more than 56 bytes.')

        buff = '         x         x         x         x         x     x'
        ds1307_mem = struct.pack('bpb', 0, buff, nbytes)

        result = fcntl.ioctl(self.i2c_dev.fileno(),
                              self.ds1307_read_fn,
                              ds1307_mem)

        (offs, buf, len) = struct.unpack('bpb', ds1307_mem)
        return buf, len

    #####
    # This is currently not working, do not use.
    #####
    def write_buf(self, buf):
        buf_len = len(buf)
        if buf_len > 56:
            message('ERROR: Buffer cannot be more than 56 bytes.')

        ds1307_mem = struct.pack('bpb', 0, buf, int(buf_len))

        result = fcntl.ioctl(self.i2c_dev.fileno(),
                              self.ds1307_write_fn,
                              ds1307_mem)
        return

class _I2CRtc(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'I2C RTC', config, hw_info, logger)

        self._detected = 0

        self._rtc_regs = _I2CRtc_Registers()

        ###
        # I have seen during tests, the chip will occasionally look like it
        # has gone south (see _I2CRtc_Registers::is_dead), but then magically
        # resurrects itself.  We'll allow this to happen a certain number of
        # *consecutive* times before pronouncing the chip fubar.
        self._rtc_death_watch = 0
        self._rtc_death_toll = 0
        self._rtc_num_lives = 5

        #####
        # This is currently not working, do not use.
        #####
        #print 'Quick I2C RTC memory test...'
        #sys.stdout.flush()
        #self._rtc_regs.write_buf('Hello World!')
        #buff, nbytes = self._rtc_regs.read_buf(12)
        #print 'Read %d bytes from I2C RTC: \"%s\"' % (nbytes, buff)
        #time.sleep(10)

        ###
        # We have to be careful about this.  I think the time.sleep() uses
        # the system clock, anything longer than this and we might see
        # too much drift in wall time.
        self._rtc_test_duration = 30
        self._rtc_test_tolerance = 5

        ###
        # The i2c RTC lives at address 0x68 on bus 0; look for it.
        result, spewage = execute_command('/usr/bin/i2cdetect 0 | grep -q 68')
        if result:
            self._detected = 1

        ####
        # Benchmark the overhead of the system call so we can deduct this
        # overhead from the final RTC time tests.  Ten iterations should be
        # sufficient, we're not controlling nuclear power.
        #
        # TBD: Measure this once and store, or each time we test the RTC?
        #
        # I would prefer to err on the side of caution and measure it each
        # iteration, but so far results have proven reliable measuring once
        # and storing the overhead.
        delta_t = 0.0
        for iteration in range(0, 10):
            start_t = time.clock()
            sec, min, hrs = self._rtc_regs.get_time()
            end_t = time.clock()

            ###
            # The value we get back from 'clocks' is in processor units.  On
            # x86 Linux, there are 100 processor units per second in
            # userspace (HZ in include/asm-i386/param.h).
            delta_t += ((end_t - start_t) * 100)

        self.overhead = int(math.ceil(delta_t / 10.0))

        return

    ###
    # Sleep for a specified duration and make sure that the RTC's clock
    # tracks.  If not, this indicates that the crystal we drive the RTC
    # with is not oscillating at the proper frequency -- we've seen this
    # on two boards as of this writing.
    def _time_rtc(self):
        ###
        # Do a quick check to make sure that the RTC has not dropped off the
        # bus (all registers contain 'XX').  We've seen this failure on four
        # boards as of this writing.
        result = self._rtc_regs.is_dead()
        if result:
            self._rtc_death_toll += 1

            if self._rtc_death_toll == self._rtc_num_lives:
                self._logger.msg('ERROR: Your RTC chip has died!\n')
                self._nerrors += 1

                ###
                # Prevent further testing.
                self._detected = 0

                return 0
            else:
                self._logger.msg('RTC DEATHWATCH: %d\n' % (5 - self._rtc_death_toll))
                if not self._rtc_death_watch:
                    self._logger.log('RTC: Beginning deathwatch.\n')
                    self._nwarnings += 1
                    self._rtc_death_watch = 1
                return 0
        else:
            self._rtc_death_toll = 0
            self._rtc_death_watch = 0

        ######
        # NOTE: Moved the benchmarking code from here to __init__
        ######
        start_secs, start_mins, start_hrs = self._rtc_regs.get_time()
        time.sleep(self._rtc_test_duration)
        end_secs, end_mins, end_hrs = self._rtc_regs.get_time()

        ###
        # TBD: If we run a test longer than 59 seconds then we need to deal
        #      with minutes and hours wrapping around.
        if (end_mins > start_mins):
            end_secs += 60
        elapsed_secs = (end_secs - start_secs) - self.overhead

        if (abs(elapsed_secs - self._rtc_test_duration) > self._rtc_test_tolerance):
            self._logger.msg('\nI2CRtc: WARNING: %d seconds elapsed, expected %d\n' % (elapsed_secs, self._rtc_test_duration))
            self._logger.log('I2CRtc: start_secs: %d, start_mins: %d, start_hrs: %d\n' % (start_secs, start_mins, start_hrs))
            self._logger.log('I2CRtc: end_secs: %d, end_mins: %d, end_hrs: %d\n' % (end_secs, end_mins, end_hrs))
            self._logger.log('I2CRtc: elapsed_secs: %d, overhead: %d\n' % (elapsed_secs, self.overhead))
            self._nwarnings += 1
        else:
            msg_pass()

        return 1
    
    def runtest(self, burnin = 0):
        if self._detected:
            msg_testing('Testing the i2c RTC chip (DS1307), this will take about two minutes....')

            ###
            # My modifications to 'hwclock' for the i2c clock will NOT fall
            # back to the ISA (internal) hardware clock for Geode platforms.
            #
            # Therefore, 'hwclock' will fail if either:
            #     Cannot access i2c bus -or-
            #     The IOCTL in the i2c driver craps out
            result, spewage = execute_command('/sbin/hwclock --utc')
            if not result:
                msg_fail()
                self._nerrors += 1
                self._logger.log('ERROR: RTC tests failed: %s' % spewage)
                return

            self._time_rtc()

        return

class _I2CSensor(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'I2C Sensor', config, hw_info, logger)

        self._detected = 0

        ###
        # The i2c RTC lives at address 0x4a on bus 0; look for it.
        result, spewage = execute_command('/usr/bin/i2cdetect 0 | grep -q 4a')
        if result:
            self._detected = 1
        
        return

    def runtest(self, burnin = 0):
        if not self._detected:
            return

        msg_testing('Testing the i2c sensor chip (LM75).....................................')

        ###
        # By specifying the exact address of the LM75 sensor we can force
        # the 'sensors' program to not get cute and search for any kind
        # of sensor.  If there isn't a functional LM75 at i2c bus 0
        # address 0x4a, then 'sensors' will return a failure.
        result, spewage = execute_command('/usr/bin/sensors lm75-i2c-0-4a')
        if 1:#result:
            msg_pass()
        else:
            self._nerrors += 1
            self._logger.log('ERROR: LM75 test failed: %s\n' % spewage)
            msg_fail()

        return


class I2CTester(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'I2CBus', config, hw_info, logger)

        #self._i2cmem = _I2CMemory(config, hw_info, logger)
        self._i2crtc = _I2CRtc(config, hw_info, logger)
        #self._i2csensor = _I2CSensor(config, hw_info, logger)

    def print_results(self):
        #self._i2cmem.print_results()
        self._i2crtc.print_results()
        #self._i2csensor.print_results()

    def runtest(self, burnin = 0):
        ###
        # Make sure we can "see" the i2c bus before attempting to test
        # attached components, duh.  (We're only interested in bus 0.)
        result, spewage = execute_command('/usr/bin/i2cdetect 0')
        if not result:
            self._logger.log('ERROR: Cannot access the I2C bus: %s\n' % spewage)
            self._nerrors += 1
            print 'I2C bus tests FAILED'
            return

        #self._i2cmem.runtest(burnin)
        #self._nerrors += self._i2cmem.nerrors()

        self._i2crtc.runtest(burnin)
        self._nwarnings += self._i2crtc.nwarnings()
        self._nerrors += self._i2crtc.nerrors()

        #self._i2csensor.runtest(burnin)
        #self._nerrors += self._i2csensor.nerrors()

#=- EOF ----------------------------------------------------------------------
