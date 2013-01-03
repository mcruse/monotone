"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
from mpx.lib.node import as_node
from mpx.lib.task.manager import TaskManager

def action(*args, **kw):
    print "action(*%s, **%s)" % (args, kw)
    return "Action Ran!"

def callback(*args, **kw):
    print "callback(*%s, **%s)" % (args, kw)
    return "Callback Ran!"

def errback(error, *args, **kw):
    print "errback(%s, *%s, **%s)" % (error, args, kw)
    msglog.exception()
    return error

def format_time(seconds):
    timestamp = time.ctime(seconds)
    print "format_time(%f) -> %s" % (seconds, timestamp)
    return timestamp

def show_time(seconds):
    print "show_time(%f): %s" % (seconds, format_time(seconds))
    return seconds

def log_result(result):
    msglog.log('broadway', msglog.types.DB, "Result: %r" % result)
    return result



tm = TaskManager()
timenode = as_node('/services/time')

d = tm.add_task(action, 1, 2, 3, name="shane")
d.register(callback, errback)



d = tm.add_task(timenode.get)
d.register(show_time)
print 'd.getvalue() -> %r' % (d.getvalue(),)

d = tm.add_task(timenode.get)
d.register(format_time)
print 'd.getvalue() -> %r' % (d.getvalue(),)


d = tm.add_task(timenode.get)
d.register(log_result, errback)
d.register(show_time)
d.register(log_result)
d.register(format_time)
d.register(log_result)
print 'd.getvalue() -> %r' % (d.getvalue(),)




