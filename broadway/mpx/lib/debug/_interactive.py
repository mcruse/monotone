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
##
# Implements the interactive debug capability.

import code as _code
import os as _os
import sys as _sys

from mpx.lib.threading import Thread as _Thread

class InteractiveDiagThread(_Thread):
    _original_stdin = None
    _original_stdout = None
    _original_stderr = None
    _stolen_stdin_stack = []
    _stolen_stdout_stack = []
    _stolen_stderr_stack = []
    def __init__(self, socket):
        _Thread.__init__(self)
        self._socket = socket
        self._my_stdin = None
        self._my_stdout = None
        self._my_stderr = None
        self._console = _InteractiveDiagConsole(self)
        return
    def run(self):
        self._acquire_stdio()
        try:
            self._console.interact()
                #"Entering the Broadway Interactive Diagnostic Tool."
                #)
        finally:
            self._release_stdio()
        return
    def exit(self):
        self.push("raise EOFError")
        self._console = None # Breaks the circular reference to allow instant
                             # releasing of this object without garbage
                             # collection.
        return
    def __replace_fd(self, name, mode, fd):
        message = ("%s being rerouted to the Interactive Diagnostic Tool.\n" %
                   name)
        # istty logic...
        if mode is 'w':
            getattr(_sys, name).write(message)
            getattr(_sys, name).flush()
        else:
            _sys.stdout.write(message)
            _sys.stdout.flush()
        setattr(module, '_orig_%s' % name, _os.dup(fd))
        _os.dup2(self._socket.fileno(),fd)
        setattr(module, name, _os.fdopen(fd, mode, 0))
        return
    def _acquire_stdio(self):
        self.__replace_fd('stdin','r',0)
        self.__replace_fd('stdout','w',1)
        self.__replace_fd('stderr','w',2)
        return
    def __restore_fd(self, name, mode, fd):
        orig_fd = getattr(module, '_orig_%s' % name)
        # istty logic...
        _os.dup2(orig_fd, fd)
        _os.close(orig_fd)
        setattr(module, '_orig_%s' % name, None)
        setattr(module, name, _os.fdopen(fd, mode, 0))
        message = ("%s relinquished by the Interactive Diagnostic Tool.\n" %
                   name)
        if mode is 'w':
            getattr(module, name).write(message)
            getattr(module, name).flush()
        else:
            _sys.stdout.write(message)
            _sys.stdout.flush()
        return
    def _release_stdio(self):
        self.__restore_fd('stdout','w',1)
        self.__restore_fd('stderr','w',2)
        self.__restore_fd('stdin','r',0)
        return

class _InteractiveDiagConsole(_code.InteractiveConsole):
    def __init__(self, thread):
        _code.InteractiveConsole.__init__(self)
        self._thread = thread
        self._file = thread._socket.makefile('a+b', 0)
        return
    def raw_input(self, prompt):
        try:
            self._file.write(prompt)
            result = self._file.readline()
            if len(result) and result[-1] == '\n':
                result = result[:-1]
        except:
            self._thread.exit()
            raise
        return result
    def write(self, data):
        self._file.write(data)
        return

# Temp code for testing purposes...
#

def _start_listener_thread(port=8333):
    import struct
    from mpx.lib.threading import Thread # Make immortal...
    class T(Thread):
        def run(self):
            import socket # reincarnate to clean up...
            listen = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            listen.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listen.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                              struct.pack("ii", 1, 0))
            listen.bind(('', 8333))
            listen.listen(5)
            while 1:
                input = listen.accept()[0]
                input.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                input.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                 struct.pack("ii", 1, 0))
                it = InteractiveDiagThread(input)
                it.start()
            return
    t = T()
    t.start()
    return t

# from mpx.lib.debug import _interactive
# _interactive._start_listener_thread()

import socket
import time
import struct
import os
import sys

_ps_duh_what = "[%s] ??? "
_ps1 = "[%s] >>> "
_ps2 = "[%s] ... "
_prompts = {
    ">>> ":_ps1,
    "... ":_ps2,
    "??? ":_ps_duh_what,
    }

def _client(host='127.0.0.1', port=8333):
    def _read_lines(s):
        lines = ''
        try:
            time.sleep(0.1)
            lines = s.recv(1024)
            prev = lines
            while lines != prev:
                prev = lines
                time.sleep(0.1)
                lines += s.recv(1024)
        except socket.error:
            pass
        return lines
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect((host,port))
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                 struct.pack("ii", 1, 0))
    s.setblocking(0)
    hostname = os.uname()[1].split('.')[0]
    try:
        prompt = "[%s] ??? " % hostname
        while 1:
            import readline
            line = _read_lines(s)
            if line[-4:] in _prompts.keys():
                prompt = _prompts[line[-4:]] % hostname
                line = line[:-4]
            sys.stdout.write(line)
            sys.stdout.flush()
            line = raw_input(prompt)
            s.sendall(line + '\n')
    finally:
        s.close()

# f.flush() then os.fsync(f.fileno())
