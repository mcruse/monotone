"""
Copyright (C) 2002 2003 2004 2010 2011 Cisco Systems

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
import time
import stat
import signal

from system import BOOTTIME as _BOOTTIME

# @note The following try/except block is to support using mpx.properties
#       when running 'in place', but also to function when copied to for
#       use by a "stand alone" package (e.g. /usr/sbin/config_service ->
#       /usr/lib/moab/config_service).
try:
  import mpx
  VAR_RUN_BROADWAY = mpx.properties.get('VAR_RUN_BROADWAY','/var/run/broadway')
except:
  VAR_RUN = os.environ.get('BROADWAY_VAR_RUN', '/var/run')
  VAR_RUN_BROADWAY = os.environ.get('BROADWAY_VAR_RUN_BROADWAY',
                                    os.path.join(VAR_RUN,'broadway'))

VAR_RUN_BROADWAY = os.path.realpath(VAR_RUN_BROADWAY)

class EProcess(Exception):
  pass

class EProcessRunning(EProcess):
  pass

class EProcessRegistrationFailed(EProcess):
  pass

class EProcessNotTerminated(EProcess):
  pass

def _get_filename(name):
  return os.path.join(VAR_RUN_BROADWAY, name + '.pid')

##
# @fixme Raising OSError for stale run files is a hack...
def _read_pid(filename):
  fd = os.open(filename, os.O_RDONLY)
  try:
    if os.fstat(fd)[stat.ST_MTIME] < _BOOTTIME:
      # This is a stale file, tell a lie...
      e = OSError('Stale pid file.')
      e.errno =  3 # @fixme Use errno No such process
      e.filename = filename
      raise e
    line = os.read(fd, 10)
    line = line.split('\n')[0]
    line = line.strip()
    if len(line) == 0:
      # The PID was not correctly written.  Tell
      # the same lie as if this were a stale file.
      e = OSError('Empty pid file.')
      e.errno =  3 # @fixme Use errno No such process
      e.filename = filename
      raise e
    return int(line)
  finally:
    os.close(fd)
  return

import os

def register_named_process(name, pid):
  filename = _get_filename(name)
  dirname = os.path.dirname(filename)
  if not os.path.exists(dirname):
    os.makedirs(dirname)
  retry = 0
  max_retry = 10
  while retry < max_retry:
    #
    # Step one, try to create the file with our PID.
    #
    try:
      fd = os.open(filename, os.O_EXCL|os.O_CREAT|os.O_RDWR, 0644)
      os.write(fd, str(pid))
      os.close(fd)
      return
    except OSError, e:
      if e.errno == 17: # @fixme Use errno File Exists.
        pass # File exists, see if the process does.
      else:
        raise
    #
    # Step two, see if the process exists.
    #
    try:
      time.sleep(1) # Give a potential writer time to save their pid.
      running_pid = _read_pid(filename)
      os.kill(running_pid, 0)
      raise EProcessRunning('%r is already running with pid %d.' %
                            (name, running_pid))
    except OSError, e:
      if e.errno == 3: # @fixme Use errno No such process
        # Process does not exists, delete the invalid pid file and try again.
        try: os.unlink(filename)
        except OSError, e:
          if e.errno == 2: # @fixme Use errno No such file
            pass # Damn race conditions, try again.
          else:
            raise e
      elif e.errno == 2: # @fixme Use errno No such file
        pass # The file is gone, try again.
      else:
        raise e # Re-raise the exception.
    # @fixme Handle corrupt pid files...
    # OK, we are trying again...
    retry += 1
  raise EProcessRegistrationFailed(
    'After %d attempts, %r could not be registerred.' % (retry, name))

##
# @fixme Consider using an mpx.lib.Enumerated[Value|Dictionary]
class StatusEnum:
  DOESNOTEXIST = 'DOESNOTEXIST'
  UNKNOWN = 'UNKNOWN'
  EXISTS = 'EXISTS'

class NamedProcessStatus:
  def __init__(self, name, pid, state):
    self.name = name
    self.pid = pid
    self.state = state
    return

def status_from_name(name):
  filename = _get_filename(name)
  pid = None
  try:
    pid = _read_pid(filename)
  except OSError, e:
    if e.errno == 2: # @fixme Use errno No such file
      return NamedProcessStatus(name, None, StatusEnum.DOESNOTEXIST)
    elif e.errno == 13: # @fixme Permission denied.
      return NamedProcessStatus(name, None, StatusEnum.UNKNOWN)
    elif e.errno == 3: # @fixme Use errno No such process
      # The run file is stale.
      return NamedProcessStatus(name, None, StatusEnum.DOESNOTEXIST)
    raise e
  # We read a pid, check for the process.
  state = StatusEnum.UNKNOWN
  try:
    os.kill(pid, 0)
    state = StatusEnum.EXISTS
  except OSError, e:
    if e.errno == 3: # @fixme Use errno No such process
      # Process does not exists
      state = StatusEnum.DOESNOTEXIST
    elif e.errno == 1: # @fixm Operation not permitted
      state = StatusEnum.EXISTS
    else:
      raise e
  return NamedProcessStatus(name, pid, state)

##
# Attempt to terminate a child process that had been registered via
# register_named_process.
#
# @exception EProcessNotTerminated Raised if the process could not be
#                                  terminated in the established
#                                  <code>timeout</code> and <code>force</code>
#                                  is is not true.
# @keyword force If true, send a SIGKILL if the termination signal does not
#                terminate the process.
# @default 1
# @keyword signal The signal to use to terminate the process.
# @default SIGTERM
# @keyword timeout The time, in seconds, to wait for the process to die.
# @default 10.0
# @keyword poll_interval The time, in seconds, to sleep until rechecking the
#                        process' state.
# @default 0.1
# @return A UNIX exit status if it could be retrieved, otherwise
#         <code>None</code>.
# @note If the return value is not None, then it can be interpreted using
#       Python's os module (see os.WIFSTOPPED(status), os.WIFSIGNALED(status),
#       os.WIFEXITED(status), os.WEXITSTATUS(status), os.WSTOPSIG(status),
#       and WTERMSIG(status))
def terminate_named_process(name, **keywords):
  defaults = {'force':1, 'signal':signal.SIGTERM, 'timeout':10.0,
              'poll_interval':0.1}
  defaults.update(keywords)
  keywords = defaults
  # Setup the termination parameters.
  force = keywords['force']
  using = keywords['signal']
  timeout = keywords['timeout']
  poll_interval = keywords['poll_interval']
  logged_waitpid_exception = 0
  status = status_from_name(name)
  if status.state == StatusEnum.DOESNOTEXIST:
    return
  exit_status = None
  os.kill(status.pid, using)
  expiration_time = time.time() + timeout
  while 1:
    try:
      pid, exit_status = os.waitpid(status.pid, os.WNOHANG)
      if pid == 0:
        exit_status = None
    except Exception, e:
      if not logged_waitpid_exception:
        try:
          from mpx.lib import msglog
          msglog.exception(msglog.types.WARN,None,'Ignored')
        except:
          pass
        logged_waitpid_exception = 1
    status = status_from_name(name)
    if status.state == StatusEnum.DOESNOTEXIST:
      return exit_status # The process is not running.
    if expiration_time < time.time():
      if force:
        os.kill(status.pid, signal.SIGKILL)
        time.sleep(poll_interval)
        try:
          pid, exit_status = os.waitpid(status.pid, os.WNOHANG)
          if pid == 0:
            exit_status = None
        except:
          pass
        return exit_status
      raise EProcessNotTerminated(
        'process %r found with pid %d, still running after %f seconds.'
        % (status.name, status.pid, timeout))
    time.sleep(poll_interval)
    return None

##
# @return Returns a list of process ids as gleaned from /proc.
#
def get_pids():
  pids = []
  names = os.listdir('/proc')
  for name in names:
    if name.isdigit():
      pid = int(name)
      pids.append(pid)
  return pids

##
# @param proc_name The name, or partial name to search for.
# @param exact Specifies whether the match must be exact.  1 if so, 0
#              otherwise.  Even if exact is 0, an exact match takes
#              precedence.
# @default 0
# @return Returns a process ID if a relevant match is found.  Otherwise
#         None is returned.
def get_pid_by_name(proc_name, exact=0):
  non_exact_match = None
  pids = get_pids()
  for pid in pids:
    try:
      cmdlinefilename = '/proc/%d/cmdline' % pid
      f = open(cmdlinefilename, 'r')
      cmdline = f.read()
      f.close()
      ents = cmdline.split('\x00')
      name = ents[0]
      if name == proc_name:
        return pid
      if not exact:
        if name.find(proc_name) != -1:
          non_exact_match = pid
    except:
      pass
  return non_exact_match
