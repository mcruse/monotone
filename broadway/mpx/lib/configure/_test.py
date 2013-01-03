"""
Copyright (C) 2006 2010 2011 Cisco Systems

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

def run_iterator(it):
    import time
    while it.has_more():
        node = it.get_next_node()
        print node.get_url(), '\n%s\n' % node.get_config()
        time.sleep(1)

def regression_test():
    from xml_handler import parse_xml
    error = 0
    root = parse_xml('mpx/lib/configure/_test.xml')
    
    mpx = root.get_children()[0]
    service = root.get_children()[1]
    
    if mpx.get_url() != '/ion':
        error += 1
        print 'error: the mpx has an incorrect URL = %s' % mpx.get_url()
    
    if service.get_url() != '/service':
        error += 1
        print 'error: the service ion has an incorrect URL = %s' % service.get_url()
    
    logger = service.get_children()[0]
    if logger.get_url() != '/service/logger':
        error += 1
        print 'error: the logger ion has an incorrect URL = %s' % logger.get_url()
    
    config = logger.get_config()
    if len(config.keys()) != 3:
        error += 1
        print 'the config dictionary has an incorrect number of entries, it has %s' % len(config.keys())
    
    logs = config['logs']
    log = logs[0]
    if len(log.keys()) != 3:
        error += 1
        print 'the logs dictionary has an incorrect number of entries, it has %s' % len(log.keys())
    
    collector = log['collector']
    cols = collector['columns']
    if len(cols) != len(log['columns']):
        error += 1
        print 'error: number of cols in log entry, %s, does not match number in collector, %s.' % (len(cols), len(log['columns']))
        
    ts = cols[0]
    ts_right = {'args': [], 'name': 'timestamp', 'function': 'self.sched_time'}
    if ts != ts_right:
        error += 1
        print 'error: timestamp column, %s, is not what it is supposed to be, %s' % (ts, ts_right)

    if error:
        print 'There were %s errors encountered' % error
    else:
        print 'There were NO errors encountered when testing the parser!'
