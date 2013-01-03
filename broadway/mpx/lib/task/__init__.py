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
from mpx.lib import msglog
from mpx.lib.deferred import Deferred

class Action(object):
    """
        Represent action which is call-able object with 
        curried arguments and keywords.
    """
    def __init__(self, handler, *args, **kw):
        if not callable(handler):
            raise TypeError("Action() requires callable handler")
        self.handler = handler
        self.arguments = args
        self.keywords = kw
        super(Action, self).__init__()
    def invoke(self, *args, **kw):
        arguments = self.arguments
        if args:
            arguments = arguments + args
        keywords = self.keywords
        if kw:
            keywords = keywords.copy()
            keywords.update(kw)
        return self.handler(*arguments, **keywords)
    def __call__(self, *args, **kw):
        return self.invoke(*args, **kw)

class Task(Action):
    """
        Use deferred to detach action execution from 
        from caller, allowing registration by caller 
        to task for getting results asynchronously.
    """
    def __init__(self, *args, **kw):
        self.deferred = Deferred()
        super(Task, self).__init__(*args, **kw)
    def get_deferred(self):
        return self.deferred
    def invoke(self, *args, **kw):
        try:
            result = super(Task, self).invoke(*args, **kw)
        except Exception, error:
            msglog.log('broadway', msglog.types.WARN, 
                       "Task '%s' execution failed." % self)
            msglog.exception(prefix="handled")
            self.deferred.failed(error)
        else:
            self.deferred.succeeded(result)

