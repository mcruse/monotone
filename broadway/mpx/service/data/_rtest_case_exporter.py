"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main

##
# Regression tests for the exporter.

import time as _time

from _exporter import Transporter as _Transporter

from mpx.service import logger as _logger
from mpx.service.logger import periodic_log as _periodic_log
from mpx.service.logger import periodic_column as _periodic_column
from mpx.service.data import periodic_exporter as _periodic_exporter
from mpx.service.data import delimited_data_formatter as _delimited_data_formatter
from mpx.lib import node as _node
from mpx.lib import pause as _pause

DEBUG = 0
VERBOSE = 0

if DEBUG:
    from mpx.lib import msglog as _msglog
    def print_log(*args):
        if args[1] != 'information':
            print _time.ctime(_time.time()), args
    _msglog._log = print_log

from mpx.lib.node import as_node, as_internal_node

class FakeNetwork(_node.CompositeNode):
    def acquire(*args):
        return 1
    def release(*args):
        return

class FakeTransporter(_Transporter):
    IYEAR = 0
    IMONTH = 1
    IDAY = 2
    IHOUR = 3
    IMIN = 4
    ISEC = 5
    IDOW = 6
    IDOY = 7
    IDST = 8
    def __init__(self, utc_offset, export_period, gm_time):
        self.errors = []
        self.utc_offset = utc_offset
        self.export_period = export_period
        self.gm_time = gm_time
        return
    def transport(self, output):
        # @fixme, could miss on loaded machine...
        if self.gm_time:
            now = int(_time.time())
        else:
            now = int(_time.time() - self.utc_offset)
        seconds = _time.gmtime(now)[self.ISEC]
        if (seconds % self.export_period) != 0:
            self.errors.append(
                "Transport called (and therefore export scheduled) on a non-local"
                " time period (now=%f, utc_offset=%f, seconds=%f)"
                % (now, self.utc_offset, seconds)
                )
        if VERBOSE:
            print "START XPORT"
            line = output.readline()
            while line:
                print line,
                line = output.readline()
            print "STOP XPORT"

class TestCase(DefaultTestFixture):
    def _localtime(self, now=None):
        if now is None:
            now = _time.time()
        now -= self._utc_offset
        return _time.gmtime(now)
    def _rawfunc(self, func):
        return "R(%f)" % func()
    def _utcfunc(self, func):
        return "U(%s)" % _time.asctime(_time.gmtime(func()))
    def _localfunc(self, func):
        return "L(%s)" % _time.asctime(self._localtime(func()))
    def _configure4437(self, utc_offset, log_period, export_period, gm_time):
        logger = _logger.factory()
        logger.configure({'name':'logger', 'parent':'/', 'debug':0, 'enable':1})
        self.logger = logger
        network = FakeNetwork()
        network.configure({'name':'network', 'parent':'/'})
        self.network = network
        log = _periodic_log.factory()
        log.configure({'name':'log', 'parent':logger, 'debug':0, 'enable':1,
                       'minimum_size':300, 'maximum_size':500,
                       'period':log_period})
        self.log = log
        columns = _node.factory()
        columns.configure({'name':'columns','parent':log})
        self.columns = columns
        timestamp = _periodic_column.factory()
        timestamp.configure({'name':'timestamp', 'parent':columns, 'position':'0',
                             'context':'None', 'function':'self.scheduled_time',
                             'args':'()',
                             'sort_order':'ascending',
                             'debug':'0'})
        self.timestamp = timestamp
        rawtime = _periodic_column.factory()
        rawtime.configure({'name':'rawtime',
                             'parent':columns, 'position':'1',
                             'context':'None',
                             'function':self._rawfunc,
                             'args':(rawtime.scheduled_time,),
                             'sort_order':'none',
                             'debug':'0'})
        self.rawtime = rawtime
        utctime = _periodic_column.factory()
        utctime.configure({'name':'utctime',
                             'parent':columns, 'position':'2',
                             'context':'None',
                             'function':self._utcfunc,
                             'args':(utctime.scheduled_time,),
                             'sort_order':'none',
                             'debug':'0'})
        self.utctime = utctime
        localtime = _periodic_column.factory()
        localtime.configure({'name':'localtime',
                             'parent':columns, 'position':'3',
                             'context':'None',
                             'function':self._localfunc,
                             'args':(localtime.scheduled_time,),
                             'sort_order':'none',
                             'debug':'0'})
        self.localtime = localtime
        exporters = _node.factory()
        exporters.configure({'name':'exporters','parent':log})
        self.exporters = exporters
        test_exporter = _periodic_exporter.factory()
        test_exporter.configure({'name':'test_exporter',
                                 'parent':exporters,
                                 'hours':0,
                                 'minutes':0,
                                 'seconds':export_period,
                                 'connection_attempts':1,
                                 'days':0,
                                 'gm_time':gm_time,
                                 'debug':1,
                                 'connection_node':self.network,
                                 'enabled':1,
                                 'timeout':60})
        self._utc_offset = utc_offset
        if not test_exporter.gm_time:
            # Use our bugus UTC time offset...
            test_exporter.time_function = self._localtime
        self.test_exporter = test_exporter
        formatter = _delimited_data_formatter.factory()
        formatter.configure({'name':'formatter',
                             'parent':test_exporter,
                             'header_delimeter':'|',
                             'data_delimiter':'|',
                             'timestamp_format':'%Y-%m-%d-%H:%M:%S'})
        self.formatter = formatter
        transporter = FakeTransporter(utc_offset, export_period, gm_time)
        transporter.configure({'name':'transporter', 'parent':test_exporter})
        self.transporter = transporter
        return
    def _test_tutos4437(self, utc_offset, log_period, export_period,
                        run_length, gm_time):
        self._configure4437(utc_offset, log_period, export_period, gm_time)
        self.logger.start()
        _pause(run_length)
        self.logger.stop()
        assert not self.transporter.errors, (repr(self.transporter.errors))
        return
    def test_tutos4437_localtime(self):
        # utc_offset = 4
        # log_period = 1
        # export_period = 6
        # gm_time = 0
        self._test_tutos4437(4, 1, 6, 30, 0)
        return
    def test_tutos4437_utc(self):
        # utc_offset = 4
        # log_period = 1
        # export_period = 6
        # gm_time = 1
        self._test_tutos4437(4, 1, 6, 30, 1)
        return

if __name__ == '__main__':
    main()
