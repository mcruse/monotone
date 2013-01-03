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
import os
import sys
import signal

class daemon(object):
    def __init__(self, name, use_pid_file=True):
        self.pid_file = None
        if use_pid_file:
            self.pid_file = '/var/run/%s.pid' % name

        return

    def _sigterm_handler(self, signum, frame):
        # Be a good citizen and clean up after ourselves.
        if os.access(self.pid_file, os.F_OK):
            os.unlink(self.pid_file)

        os._exit(0)

    def setup_daemon(self):
        ####
        # Fork a child process so the parent can exit.  This will return control
        # to the command line or shell.  This is required so that the new process
        # is guaranteed not to be a process group leader.  We have this guarantee
        # because the process GID of the parent is inherited by the child, but
        # the child gets a new PID, making it impossible for its PID to equal its
        # PGID.
        try:
            pid = os.fork()
        except OSError, e:
            return (e.errno, e.strerror)

        if (pid != 0):
            os._exit(0)

        ####
        # Next we call os.setsid() to become the session leader of this new
        # session.  The process also becomes the process group leader of the
        # new process group.  Since a controlling terminal is associated with a
        # session, and this new session has not yet acquired a controlling
        # terminal our process now has no controlling terminal.  This shouldn't
        # fail, since we're guaranteed that the child is not a process group
        # leader.
        os.setsid()

        ####
        # When the first child terminates, all processes in the second child
        # are sent a SIGHUP, so it's ignored.
        signal.signal(signal.SIGHUP, signal.SIG_IGN)

        ####
        # Fork a second child to prevent zombies.  Since the first child is
        # a session leader without a controlling terminal, it's possible for
        # it to acquire one by opening a terminal in the future.  This second
        # fork guarantees that the child is no longer a session leader, thus
        # preventing the daemon from ever acquiring a controlling terminal.
        try:
            pid = os.fork()
        except OSError, e:
            return (e.errno, e.strerror)

        if (pid != 0):
            os._exit(0)

        if self.pid_file:
            pf = open(self.pid_file, 'w+')
            pf.write('%d' % os.getpid())
            pf.close()

        ####
        # Ensure that the daemon doesn't keep any directory in use.  Failure
        # to do this could make a filesystem unmountable.
        os.chdir("/")

        os.umask(0)

        signal.signal(signal.SIGTERM, self._sigterm_handler)

        ####
        # Close all open files.  Try the system configuration variable, SC_OPEN_MAX,
        # for the maximum number of open files to close.  If it doesn't exist, use
        # the default value (configurable).
        try:
            maxfd = os.sysconf("SC_OPEN_MAX")
        except (AttributeError, ValueError):
            maxfd = 256

        for fd in range(0, maxfd):
            try:
                os.close(fd)
            except OSError:
                pass

        # Redirect the standard file descriptors to /dev/null.
        os.open("/dev/null", os.O_RDONLY)    # STDIN
        os.open("/dev/null", os.O_RDWR)      # STDOUT
        os.open("/dev/null", os.O_RDWR)      # STDERR

        return 0
