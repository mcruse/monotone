"""
Copyright (C) 2001 2002 2005 2010 2011 Cisco Systems

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
import os

from mpx._python.thread import *
from mpx._python.exceptions import Exception as _Exception

def msglog():
    from mpx.lib import msglog as msglog_module
    return msglog_module

##
# Wrapper function used to ensure that we log all exceptions in threads.
#
# @param func The real target function to call.
# @param args A tuple of arguments to pass to <code>func</code>.
# @param kwargs A dictionary to use as keyword arguments for <code>func</code>.
def _func_wrapper(func, *args, **kwargs):
    try:
        apply(func, args, kwargs)
    except _Exception:
        msglog().exception()
    except:
        msglog().exception()
    return

_python_start_new_thread = start_new_thread

##
# Start a new Broadway thread.
#
# The thread executes the function function with the argument list args (which
# must be a tuple). The optional kwargs argument specifies a dictionary of
# keyword arguments. When the function returns, the thread silently exits. When
# the function terminates with an unhandled exception, a stack trace is printed
# and then the thread exits (but other threads continue to run).
#
# @param func The function to call in the context of the new thread.
# @param args A tuple of arguments to pass to <code>func()</code>.
# @param kwargs An optional dictionary of keyword arguments to pass to
#               <code>func()</code>.
# @default {}
def start_new_thread(func, args, kwargs=None):
    global _python_start_new_thread
    if kwargs is None:
        kwargs = {}
    return _python_start_new_thread(_func_wrapper, (func,)+args, kwargs)

from mpx import properties

def log_startup(new_thread, name, spidfileprefix):
    msglog().log('broadway',msglog().types.INFO,
                 ('%s (%s) thread starting (with SPID %d).' % 
                  (name, id(new_thread), gettid())))
    fn = os.path.join(properties.VAR_RUN_BROADWAY, spidfileprefix + '.spid')
    try:
        f = open(fn, 'w')
        f.write(str(gettid()))
        f.close()
    except:
        msglog().log('broadway',msglog().types.WARN,
                     'Got exception trying to write %s SPID to %s' % (name, fn))
        msglog().exception()

from os import getpid

# gettid()
#
# This next section defines the gettid() function that returns the current
# thread's id.  On a running Mediator this uses the _thread.so library.
# The build system itself imports mpx.lib.thread.  On a native build, this
# is not a problem as it can load the compile library.  In a cross-compiled
# environment the library won't load.
#
# If the shared library fails to load, then C code is compile to find the
# running system's SYS_gettid constant to create a the gettid().
try:
    # Mediator/Native code path:
    def _shared_library():
        import ctypes
        import os
        so_dir = os.path.dirname(os.path.abspath(__file__))
        so_file = os.path.join(so_dir, '_thread.so')
        so_lib = ctypes.cdll.LoadLibrary(so_file)
        return so_lib
    _thread_so = _shared_library()
    def gettid():
        return _thread_so.gettid()
except:
    # Cross compile load path:
    def _get_SYS_gettid():
        import os
        import tempfile
        import subprocess
        f=tempfile.NamedTemporaryFile(suffix='.c')
        f.write('\n'.join((
                    r'#include <sys/types.h>',
                    r'#include <sys/syscall.h>',
                    r'#include <stdio.h>',
                    r'int main(void)',
                    r'{',
                    r'printf("%d", SYS_gettid);',
                    r'return 0;',
                    r'}',
                    r'',
                    )))
        f.file.flush()
        iname=f.name
        oname=f.name.rsplit('.',1)[0]
        p = subprocess.Popen(
            # @fixme Fix configure and rc file so paths aren't hard coded.
            'unset CROSS_COMPILE; unset ARCH; PATH=/bin:/usr/bin; '
            '/usr/bin/gcc -o %(oname)s %(iname)s && %(oname)s' % {
                'iname':iname,'oname':oname
                },
            shell=True,
            stdout=subprocess.PIPE
            )
        assert p.wait() == 0
        os.unlink('%(oname)s' % {'oname':oname})
        f.close()
        return int(p.stdout.read())
    SYS_gettid=_get_SYS_gettid()
    from ctypes import CDLL
    _syscall=CDLL('libc.so.6').syscall
    def gettid():
        global _syscall
        return _syscall(SYS_gettid)
    del CDLL    

########################################################################
#                        LOCK DEBUGGING HOOKS.
########################################################################
if properties.get_boolean('DEBUG_LOCKS', 0):
    from debugging_locks import approach
    # @todo Support LockType.
    from debugging_locks import _LockAssertion
    from debugging_locks import _InternalAssertion
    from debugging_locks import _WrongThreadAssertion
    from debugging_locks import allocate
    from debugging_locks import allocate_lock
