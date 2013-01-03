"""
Copyright (C) 2002 2003 2005 2006 2010 2011 Cisco Systems

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
# @fixme Write an extensive test case!

from time import time as _time
from time import ctime as _ctime
from sys import stderr as _stderr
import traceback as _traceback

import mpx as _mpx

##
# Provides the ability to log system messages to the msglog
# which defaults to /var/mpx/log/msglog.log

##
# @author Craig Warren
# a class used to log messages to the msglog.log file
#
class Msglog:
   ##
   # @author Craig Warren
   def  __init__(self):
      # Msglog is required early in the import sequence, so it's
      # lock will not participate in DEBUG_LOCKS mode.
      from mpx._python.threading import RLock

      self.debug = 0
      self._ready_to_log = 0
      self._deferred_entries = []
      self._lock = RLock() # If the "msglog" is corrupt, it can go reentrant.
      return
   def __write_failure_stderr(self, entry, exc=None):
      if exc is not None:
         try:
            msg = ''
            try:    msg = str(exc)
            except: pass
            if hasattr(exc, '__class__'):
               if hasattr(exc, '__name__'):
                  msg = "%s: %s" % (exc.__class__.__name__, msg)
            _stderr.write("MSGLOG FAILURE: %s\n" % msg)
         except:
            _traceback.print_exc()
      try:
         _stderr.write("%s %s %s\n%s\n" % (_ctime(entry[0]),
                                           entry[1], entry[2], entry[3],))
      except:
         _traceback.print_exc()
      return
   ##
   # @note Assumes the MsgLog is locked
   def _log_deferred_entries(self):
      # Log any previously deferred entries.
      while self._deferred_entries:
         try:
            self.log.add_entry(self._deferred_entries.pop(0))
         except Exception, e:
            try:
               self.__write_failure_stderr(entry, e)
            except:
               # ...Wow, we can't even write it to standard error.
               pass # Explicit end of while/except/except
            pass    # Explicit end of while/except
         continue   # Explicit end of while
      return
   ##
   # Determin if it framework is initialized to the point that we can
   # instantiate the actual msglog.
   #
   # @fixme TOO MUCH MAGIC.  ARGUMENT ABUSE.  HELP!!!
   #
   # @return True if the framework has initialized to the state that it is
   #         ready to log data.  Otherwise, false.
   def _log_ready(self, log_module=None,
                  reloadable_singleton_factory=None,
                  eloadingdisabled=None):
      if self._ready_to_log:
         return 1
      if eloadingdisabled is not None:
         self.ELoadingDisabled = eloadingdisabled
      ##
      # OK, we should be good to go.
      self._lock.acquire()
      try:
         def msglog_factory(log_module, reloadable_singleton_factory, eloadingdisabled):
            msglog_instance = log_module.TrimmingLog("msglog")
            # Mark Carlson - 2007-03-21: Do not start trimming the log yet
            #                because the trim parameters have not been set up
            msglog_instance.stop_trimming()
            timestamp = log_module.ColumnConfiguration('timestamp', 0, 'none')
            application = log_module.ColumnConfiguration('application', 1,
                                                         'none')
            type = log_module.ColumnConfiguration('type', 2, 'none')
            message = log_module.ColumnConfiguration('message', 3, 'none')
            msglog_instance.configure((timestamp, application, type, message))
            return msglog_instance
         self.log = reloadable_singleton_factory(
            msglog_factory, log_module, reloadable_singleton_factory, eloadingdisabled
            )
         self._log_deferred_entries()
         self._ready_to_log = 1
      finally:
         self._lock.release()
      return 1
   ##
   # @author Craig Warren
   # @param values The list of values to add to the msglog file.
   # @return None if logging was successful, otherwise the list of exceptions
   #              that occurred while attemoting the log the entry.
   def add_entry(self,values):
      exceptions = []
      try:
         time = _time()
         row = [time] + values
      except Exception, e:
         exceptions.append(e)
         try:
            err = (
               "MSGLOG FAILURE: Could not use %r as the log tuple due to %s."
               )
            _stderr.write(err % (values, e))
         except Exception, e:
            exceptions.append(e)
            try:
               err = "MSGLOG FAILURE: Unexpected msglog failure %s."
               _stderr.write(err % e)
            except Exception, e:
               exceptions.append(e)
               pass
            pass
         return exceptions
      self._lock.acquire()
      try:
         if self._log_ready():
            try:
               # Log the specified entry.
               self.log.add_entry(row)
            except self.ELoadingDisabled:
               # Test case hack.  Through away messages logged after the test
               # case has torn down the reloadable singletons.
               pass
            except Exception, e:
               # Attempt to log the entry failed...
               try:
                  exceptions.append(e)
                  self.__write_failure_stderr(row, e)
               except:
                  exceptions.append(e)
                  # ...Wow, we can't even write it to standard error.
                  pass
               return exceptions
            pass
         else:
            # Save off the entry for later.
            self._deferred_entries.append(row)
            if self.debug:
               try: _stderr.write("MSGLOG: Deferring %r row.\n" % row)
               except: pass
            pass
         pass
      finally:
         self._lock.release()
      return None
