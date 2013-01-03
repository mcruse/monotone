"""
Copyright (C) 2002 2003 2004 2005 2007 2010 2011 Cisco Systems

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

##
# tool for reading the msglog file on the mpx.
# @fixme Refactor using [tools.]clu.CommandLineUtility

import os
import stat
import string
import time
import sys
from types import *

from mpx import properties
from mpx.lib.log import TrimmingLog
from mpx.lib.exceptions import ENoData

# stat members which are deemed import with respect
# to whether or not a file has really changed.
_members_to_check = (stat.ST_INO,
                     stat.ST_MTIME,
                     stat.ST_SIZE,
                     )

# The maximum amount of time (seconds) to wait before
# forcing a re-read of the log whether or not it seems
# to have changed
max_wait_time = 60

# How often (in seconds) to check the log file to see
# if it has changed (in follow mode).
stat_check_time = .25

# Old stat dictionary
old_stats = {}

# Returns 1 if the stats differ in an "important" way,
# otherwise returns 0.
def _cmp_stat(stat1, stat2):
    for x in _members_to_check:
        if stat1[x] != stat2[x]:
            return 1
    return 0

def _initialize_stat(filename):
    if os.path.exists(filename):
        old_stats[filename] = os.stat(filename)
    
def _sleep_until_file_changes_with_timeout(filename,
                                           timeout):
    time_count = 0
    if not os.path.exists(filename):
        time.sleep(5)
        return
    if not old_stats.has_key(filename):
        old_stats[filename] = os.stat(filename)
    while time_count < timeout:
        if not os.path.exists(filename):
            return
        nstat = os.stat(filename)
        differ = _cmp_stat(old_stats[filename], nstat)
        if differ:
            old_stats[filename] = nstat
            return
        time.sleep(stat_check_time)
        time_count = time_count + stat_check_time

def get_types(index):
    types = []
    arg = sys.argv[index+1:]
    end = len(arg)
    counter = 0
    while counter < end:
        if arg[counter][:2] == '--':
            counter = end
        else:
            types.append(arg[counter])
        counter = counter + 1
    return types

def _get_num_of_lines(index):
    result = 5
    #if there are more arguments
    if len(sys.argv) > index:
        try:
            result = int(sys.argv[index + 1])
        except:
            pass
    return result

def _get_after_ts(index):
    tmp = ()
    tmp2 = []
    ts = str(sys.argv[index + 1]) + ' ' + str(sys.argv[index + 2])
    #retrieve the tuple 
    tmp = ()
    tmp = time.strptime(ts,'%Y/%m/%d %H:%M:%S')
    tmp2 = []
    #turn the tuple into a list so we can change the last value
    for x in tmp:
        tmp2.append(x)
    #change the last value
    tmp2[8] = -1
    ts =time.mktime(tmp2)
    return ts

def _printable(dic,types,after_ts):
    result = 0
    # see if the record is after the timestamp
    if dic['timestamp'] > after_ts:
        result = 1
    # see if they specified types
    if len(types) and result == 1 :
        for type in types:
            if type == dic['type']:
                result = 1
            else:
                result = 0
    return result

def _parse_args():
    args = {}
    types = []
    args['tail_lines'] = None
    args['head_lines'] = None
    args['help'] = 0
    args['after_ts'] = 0
    args['follow'] = 0
    args['color'] = 0
    args['match'] = []
    counter = 0
    for arg in sys.argv:
        if (len(arg) == 6 and arg[0:6] == '--type') or (len(arg) == 2 and arg == '-t'):
            args['types'] = _get_types(counter)       
        elif (len(arg) == 6 and arg[0:6] == '--head') or (len(arg) == 2 and arg == '-H'):
            args['head_lines'] =  _get_num_of_lines(counter)        
        elif (len(arg) == 8 and arg[0:8] == '--follow') or (len(arg) == 2 and arg == '-f'):
            args['follow'] = 1        
        elif (len(arg) == 6 and arg[0:6] == '--tail') or (len(arg) ==2 and arg == '-T'):
            args['tail_lines'] =  _get_num_of_lines(counter)        
        elif (len(arg) == 7 and arg[0:8] == '--after') or (len(arg) == 2 and arg == '-a'):
            args['after_ts'] = _get_after_ts(counter)        
        elif (len(arg) == 7 and arg[0:8] == '--color') or (len(arg) == 2 and arg == '-c'):
            args['color'] = 1
        elif (len(arg) == 7 and arg[0:8] == '--match') or (len(arg) == 2 and arg == '-m'):
            if len(sys.argv) > (counter + 1):
                args['match'].append(sys.argv[counter+1])
        elif (len(arg) == 6 and arg[0:6] == '--help') or (len(arg) == 2 and arg == '-h'):
            args['help'] = 1
        elif arg[0:2] == '--':              
             if arg[2:7] != 'tail=' or arg[2:7] != 'head=' or arg[2:8] != 'follow' or arg[2:8] != 'after=':
                 raise bad_option
        counter += 1
    return args

def _display_help():
    print '\n'
    print "VERSION: Beta 0.5.0"
    print "Author: Craig Warren"
    print "Date: 04/19/01"
    print '\n'
    print 'SYNTAX:'
    print '\n'
    print '%5s %s' % ('','python msglog.py [options]')
    print '\n'
    print '%5s %s' % ('','If you have an environment variable BROADWAY_LOGFILE_DIRECTORY defined')
    print '%5s %s' % ('','the program will look there for the msglog.  If you')
    print '%5s %s' % ('','want to use the current directory set it to \'.\'')
    print '\n'
    print 'OPTIONS:'
    print '\n'
    print '%5s %s' % ('','NOTE: pass in options seperately, ie you CAN\'T do something like msglog.py -ta')
    print '\n'
    print '%5s %-20s %s' % ('','-t or --type','Used to filter the msglog by type')
    print '%26s %s' % ('','pass as many types as you would like to display')
    print '%26s %s' % ('','example:')
    print '%30s %s' % ('','-t information error')
    print '\n'
    print '%5s %-20s %s' % ('','-h or --help','Used to dislpay this HELP')
    print '\n'
    print '%5s %-20s %s' % ('','-T or --tail','Used to look at the tail of a file')
    print '%26s %s' % ('','5 is used as the default')
    print '%26s %s' % ('','example:')
    print '%30s %s' % ('','-T 10 -- Last 10 lines are displayed')
    print '\n'
    print '%5s %-20s %s' % ('','-H or --head','Used to look at the head of a file')
    print '%26s %s' % ('','5 is used as the default')
    print '%26s %s' % ('','example:')
    print '%30s %s' % ('','-H 10 -- First 10 lines are displayed')
    print '\n'
    print '%5s %-20s %s' % ('','-f or --follow','Used to follow the file')
    print '%26s %s' % ('','Continues to display the msglog and shows new entries')
    print '\n'
    print '%5s %-20s %s' % ('','-a or --after','Used to show records after a date')
    print '%26s %s' % ('','Date Format: YYYY/MM/DD HH:MM:SS (time is in 24 hour time)')
    print '%26s %s' % ('','example:')
    print '%30s %s' % ('','-a 02/10/01 12:00:00')
    print '\n'
    print '%5s %-20s %s' % ('','-c or --color','Use ANSI color to improve log readability')
    print '\n'
    print '%5s %-20s %s' % ('','-m or --match','Use ANSI color to highlight matching text')
    print '%26s %s' % ('','Specified text must match the full text found in the ')
    print '%26s %s' % ('','  "Application" or "Type" column.')
    print '%26s %s' % ('','This can be used more than once.')
    print '%26s %s' % ('','example:')
    print '%30s %s' % ('','-m exception -- Exception type messages are highlighted')
    print '\n'

def _display_header():
    print "\n"
    print " %-25s %-12s %-12s %s" % ('Timestamp','Application','Type', 'Message')
    print "|-------------------------|------------|-----------|------------------------"

def _display_message(message, color=None, matchlist=None):
    timestamp = time.ctime(int((message['timestamp'])))
    application = message['application']
    type = message['type']
    note = message['message']
    if color:
        maincolor = "\033[1;34m" # Blue
        colorend = "\033[0;0m" # Reset
    else:
        maincolor = ""
        colorend = ""
    appcolor = maincolor
    typecolor = maincolor
    if matchlist:
        for match in matchlist:
            if match == application:
                appcolor = "\033[1;31m" # Red
            if match == type:
                typecolor = "\033[1;31m" # Red
    
    output = "%s%-25s %s%-12s%s %s%-12s%s %s" % \
           (maincolor, timestamp, appcolor, application, colorend, typecolor, type, colorend, note)
    print output

def display_log():
    args = _parse_args()
    if args['help']:
        _display_help()
        return
    _display_header()
    log = TrimmingLog('msglog')
    start = 0
    try:
        if args['tail_lines'] is not None or args['follow']:
            tail_lines = 10
            if args['tail_lines'] != None:
                tail_lines = int(args['tail_lines'])
            assert tail_lines >= -1, (
                "tail_lines must be greater than or eaual to -1")
            if tail_lines == -1:
                start = int(log.get_first_record()['_seq'])
            else:
                start = int(log.get_last_record()['_seq']) - tail_lines + 1
        else:
            start = int(log.get_first_record()['_seq'])
    except AssertionError:
        raise # Reraise the original exception.
    except:
        pass
    end = args['head_lines']
    assert end is None or end >= 0, (
        "head_lines must be None or it must be greater than or eaual to 0")
    entries = ()
    try:
        if end is not None:
            end += start
            entries = log[start:end]
        else:
            end = start
            entries = log[start:]
            end += len(entries)
    except ENoData:
        entries = []
        pass
    for entry in entries:
        _display_message(entry, args['color'], args['match'])
    if args['follow']:
        # If the file doesn't exist, there doesn't seem to be an obvious
        # way to gracefully recover at this point.  Just inform the user
        # that the file doesn't exist, and bail.  While we are at it,
        # we can make sure that the file does exist so that the next
        # time we are run, we have half a chance.
        if not os.path.exists(log.filename):
            print 'Error: %s does not exist.  Please restart.' % log.filename
            try:
                fd = open(log.filename, 'a+')
                fd.close()
            except:
                pass
            return
        _initialize_stat(log.filename)
        restart = end
        while 1:
            try:
                entries = log[restart:]
                restart += len(entries)
                for entry in entries:
                    _display_message(entry, args['color'], args['match'])
            except ENoData:
                pass
            # Sleep until either the file has changed, or
            # a certain maximum amount of time has elasped.
            _sleep_until_file_changes_with_timeout(log.filename,
                                                   max_wait_time)

if __name__ == '__main__':
    try:
        display_log()
    except KeyboardInterrupt:
        # Exit cleanly if user types control-C
        pass
