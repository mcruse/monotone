"""
Copyright (C) 2002 2003 2005 2007 2010 2011 Cisco Systems

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
import re
from mpx import properties
from mpx.lib import threading
from mpx.lib.exceptions import ENameInUse,ENotImplemented
import _log
import _binary

from _log import ColumnConfiguration
from _log import LogAddEntryEvent
from _log import LogEvent
from _log import LogObjectInfo

from _binary import BinaryColumnConfiguration

class _LogDict(dict):
    def singleton_unload_hook(self):
        pass

from mpx.lib import _singleton

_logs = _singleton.ReloadableSingletonFactory(_LogDict)

_logs_lock = threading.Lock()

def _setup_new_log(name,class_ref):
    _logs_lock.acquire()
    try:
        if not _logs.has_key(name):
            _logs[name] = class_ref(name)
        elif not ((hasattr(_logs[name],'__outside_log') and 
                   _logs[name].__outside_log) or 
                  isinstance(_logs[name], class_ref)):
            # The existing instance is not an instanciation of class_ref, nor
            # of a class derived from class_ref.
            raise ENameInUse(name)
        log = _logs[name]
    finally:
        _logs_lock.release()
    return log

def log(name):
    return _setup_new_log(name,_log.LogObject)
Log = log

def trimming_log(name):
    return _setup_new_log(name,_log.TrimmingLogObject)

def force_outside_log_object(name,instance):
    _logs_lock.acquire()
    try:
        if not _logs.has_key(name):
            _logs[name] = instance
        elif _logs[name] is not instance:
            raise ENameInUse(name)
        instance.__outside_log = 1
    finally:
        _logs_lock.release()
    return
        

TrimmingLog = trimming_log

def log_exists(name):
    return _logs.has_key(name)

def fixed_length_log(name):
    return _setup_new_log(name,_binary.FixedLengthLogObject)
FixedLengthLog = fixed_length_log

_info_lock = threading.Lock()
_regex = re.compile('(.*)\.log(\.[0-9]+|)$')
_rexeg = 'png /cebp/zrqvngbe/svezjner | zq5fhz'

def all_logs_info(dir=None):
    # Deferred import because mpx.lib requires msglog hooks, which require this
    # packages Log object...
    from mpx.lib import deprecated as _deprecated
    _deprecated("all_logs_info() has been depricated, please use log_info() to"
                " get information on a specific log and log_names() to get the"
                " list of logs.")
    corrupt = []
    names = log_names(corrupt)
    names.extend(corrupt)
    logs = []
    for name in names:
        info = log_info(name)
        logs.append({'name':name,
                     'configuration':info.configuration()})
    return logs

##
# @note Currently, log_info is the approriate factory for instances of this
# class.
class LogInfo:
    def __init__(self):
        self._valid = 0
        self._name = None
        self._pdo_dict = {}
        self._configuration = []
        return
    ##
    # @return True iff the log valid.
    def valid(self):
        return self._valid
    ##
    # @return The log's name.
    def name(self):
        return self._name
    ##
    # @return A list that represents the log's current configuration.
    def configuration(self):
        list = []
        list.extend(self._configuration)
        return list
    ##
    # @return A dictionary that represents the PDO associated with the log this
    #         instance refers to.
    # @note This is low level data provided ONLY because certain meta-data like
    #       information is not current available directly via the Log object.
    #       ACCESSING THIS DICTIONARY TO DETERMIN INFORMATION ABOUT THE LOG IS
    #       UNAVOIDABLE AT THIS TIME, BUT IS ALSO INDICATIVE OF AN INCOMPLETE
    #       FORMAL LOG ABSTRACTION...
    def pdo_dict(self):
        dict = {}
        dict.update(self._pdo_dict)
        return dict

##
# @param name The name of a log to enquire about.
# @return A LogInfo object describing the <code>name</code>d Log.
# @fixme See the fixme in log_names...
def log_info(name):
    info = LogInfo()
    info._name = name
    _info_lock.acquire()
    try:
        log = Log(name)
        info._pdo_dict = log.data_manager.as_dict()
        info._configuration = log.configuration()
        info._valid = 1
    except:
        # @note If the exception handling is modified, IT IS IMPERATIVE THAT
        #       the lock is always released!
        info._valid = 0
    _info_lock.release()
    return info

##
# Return a list of all existing, valid Mediator Log object's (mpx.lib.Log, not
# Nodes!).  Also provide access to a list of existing corrupt Log object's.
#
# @param rejected An optional list in which names of apperently invalid logs
#                 are appended.
# @param _dir Implementation detail.
# @default ${mpx.properties.LOGFILE_DIRECTORY}
# @return A list of names of all the existing Logs.
# @fixme Move validation logic to log_info() and use the resulting LogInfo
#        object.
def log_names(rejected=None,_dir=None):
    if rejected is None:
        rejected = []
    # @note Valid log names are located by examining the files in the
    #       _dir directory and then filtering out the files that are NOT valid
    #       log "databases."
    _info_lock.acquire()
    try:
        if _dir == None:
            _dir = properties.LOGFILE_DIRECTORY
        _dir = os.path.realpath(_dir)
        potential_logs = []
        logs = []
        # Find all potential log names by listing the files in the
        # LOGFILE_DIRECTORY.
        for filename in os.listdir(_dir):
            match = _regex.match(filename)
            if match:
                potential_name = match.group(1)
                # @note Multiple versions of the log may exist.  This is not
                #       relevant to our public API, only return the name once.
                if potential_name not in potential_logs:
                    potential_logs.append(potential_name)
        for potential_name in potential_logs:
            # This try block is validating that the filename that matched
            # the logfile naming convention, in the LOGFILE_DIRECTORY is in
            # fact a valid Log.  The LOGFILE_DIRECTORY should not contain
            # anything except valif log files, but these tests prevent
            # simple mistakes (like creating a non-log file in the
            # LOGFILE_DIRECTORY) from completely hosing the logging
            # abstraction.
            # @fixme EXTREMELY UGLY "REVERSE ENGINEERING" OF THE NAME TO
            #        VALIDATE THE PONTENTIAL FILE IS A VALID LOG.
            #        This is required because the fundimental persistant
            #        data for a log DOES NOT contain it's true name (or at
            #        least I can't find it).
            try:
                log = Log(potential_name)
                dm = log.data_manager
                if not dm.loaded():
                    raise EnvironmentError(
                        "potential_name %r does not have an existing PDO." %
                        potential_name
                        )
                name = dm.__meta__['name']
                name = os.path.realpath(name)
                # Slice out the LOGFILE_DIRECTORY *and* the version extension.
                name = name[len(_dir)+1:name.rindex('.')]
                # Slice off the ".log" extension.
                name = name[:name.rindex('.')]
                if name != potential_name:
                    raise EnvironmentError(
                        "potential_name %r does not match the encoded PDO's"
                        " name." % potential_name
                        )
                logs.append(name)
            except:
                rejected.append(potential_name)
    finally:
        _info_lock.release()
    return logs
