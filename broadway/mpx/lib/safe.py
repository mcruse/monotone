"""
Copyright (C) 2001 2003 2010 2011 Cisco Systems

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
from mpx.lib.threading import Thread,Condition,Lock
from mpx.lib.exceptions import ETimeout

class _ResultThread(Thread):
    def __init__(self,target,args,cleanup,c_args,group=None,name=None,
                 kwargs=None,verbose=None,*vargs,**keywords):
        if kwargs is None:
            kwargs={}
        self._cleanup = cleanup
        self._cleanup_args = c_args
        self._complete = 0
        self._expired = 0
        self._lock = Lock()
        self._exception = None
        self._result = None
        Thread.__init__(self,group,target,name,args,
                        kwargs,verbose,*vargs,**keywords)
    def run(self):
        try:
            result = apply(self._Thread__target, 
                           self._Thread__args, 
                           self._Thread__kwargs)
        except Exception,e:
            self._exception = e
            raise
        self._lock.acquire()
        try:
            expired = self._expired
            if expired:
                self._exception = ETimeout('Action has been expired')
            else:
                self._result = result
                self._complete = 1
        finally:
            self._lock.release()
        if expired and self._cleanup is not None:
            apply(self._cleanup,self._cleanup_args)
        return
    def result(self,timeout=None):
        self.join(timeout)
        self._lock.acquire()
        try:
            if self._exception is not None:
                raise self._exception
            if self._complete:
                return self._result
        finally:
            self._lock.release()
        raise ETimeout()
    ##
    # Hook for decreasing mass of threads stuck in memory by deleting 
    # attributes.  Not implemented.
    def minimize(self):
        pass
    def expire(self):
        self._lock.acquire()
        try:
            self._expired = 1
        finally:
            self._lock.release()
        return
def limited_apply(func,args=(),timeout=None,cleanup=None,c_args=()):
    thread = _ResultThread(func,args,cleanup,c_args)
    thread.start()
    try:
        return thread.result(timeout)
    except ETimeout:
        thread.expire()
        thread.minimize()
        raise ETimeout('Function call timed out.  Warning, calls which ' + 
                       'timeout may leave blocked threads in memory.')
##
# Safely apply args to a function.
# This procedure can be used with generic functions, unbound methods (if
# the first argument is aninstance) and bound methods.  This is largely
# intended as an example.
#
# Example:<p>
# <code>
# >>> def before():<br>
# ... &nbsp;&nbsp;&nbsp;&nbsp;print 'before'<br>
# ... <br>
# >>> def after():<br>
# ... &nbsp;&nbsp;&nbsp;&nbsp;print 'after'<br>
# ... <br>
# >>> def funky(a,b,c):<br>
# ... &nbsp;&nbsp;&nbsp;&nbsp;print a,b,c<br>
# ... <br>
# >>> apply(before, after, funky, 1, 2, 3)<br>
# before<br>
# 1 2 3<br>
# after<br>
# >>> def stinky(a,b,c):<br>
# ...&nbsp;&nbsp;&nbsp;&nbsp; raise hell<br>
# ... <br>
# >>> apply(before, after, stinky, 1, 2, 3)<br>
# before<br>
# after<br>
# Traceback (innermost last):<br>
# &nbsp;&nbsp;File "<stdin>", line 1, in ?<br>
# &nbsp;&nbsp;File "<stdin>", line 5, in apply<br>
# &nbsp;&nbsp;File "<stdin>", line 2, in stinky<br>
# NameError: hell<br>
# >>><br>
# </code>
#
# @param preamble  First function to call with no arguments.
#                  Value returned by <code>preamble</code>
#                  will be the first part of what is returned by
#                  <code>apply</code>
#
# @param postcript  Last function to call, with no arguments.
#                   Value returned by <code>postscript</code>
#                   will be the last part of what is returned by
#                   <code>apply</code>
#
# @param func  The function to call safely.  Value returned
#              will be middle of value returned by
#              <code>apply</code>
#
# @param *args  Variable number of arguments to be passed to
#               <code>func</code>
#
# @return Result generated by concatenating the return values
#         from calling <code>preamble, func, postscript</code>
#         in that order.
#
def wrapped_apply(preamble, postscript, func, *args):
    result = None
    preamble()
    try:
        result = apply(func, args)
    finally:
        postscript()
    return result
