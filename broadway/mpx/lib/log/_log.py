"""
Copyright (C) 2002 2003 2006 2007 2010 2011 Cisco Systems

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
import StringIO
import copy
import os
import re
import string
import sys
import time
import traceback
import types
import urllib

from mpx import properties

from mpx.lib import threading as _threading
from mpx.lib import exceptions as _exceptions
from mpx.lib import security as _security
from mpx.lib import persistent as _persistent

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.event import EventProducerMixin
from mpx.lib.event import Event as _Event

from mpx.lib.stream import StreamingTupleWithCallback

from mpx.lib.uuid import UUID

##
# Common baseclass for log events.  Intended to for easy consumption/forwarding
# of all LogEvents and to ease migration to the common event model coming to a
# Mediator near you soon!
class LogEvent(_Event):
    ##
    # All LogEvents contain a unique LOG_GUID that identifes the source log
    # object.
    #
    # @note The source of a log object (mpx.lib.log.Log) is the Log instance.
    #       Which is NOT a Node.  The source of a logger service
    #       (mpx.service.logger.Log) IS the logger server Node.  Capeech?
    def __init__(self, log_guid, **kw):
        _Event.__init__(self, **kw)
        self.log_guid = log_guid
        return
    def clone(self):
        return copy.copy(self)

class LogAddEntryEvent(LogEvent):
    def __init__(self, log_guid, entry_guid, values, seq, **kw):
        LogEvent.__init__(self, log_guid, **kw)
        self.entry_guid = entry_guid
        self.values = values
        self.seq = seq
        return

def _readline_backwards(log):
    if log.tell() < 2:
        return ''
    log.seek(-1,1)
    seek = _seek_beginning(log)
    line = log.readline()
    log.seek(seek)
    return line
def _readline_forwards(log):
    return log.readline()
def _seek_beginning(log):
    start = log.tell()
    data = ''
    while '\n' not in data and start != 0:
        log.seek(start)
        end = log.tell()
        if end < 1024:
            log.seek(0)
        else:
            log.seek(-1024,1)
        start = log.tell()
        data = log.read(end-start)
    log.seek(start + data.rfind('\n') + 1)
    return log.tell()
def convert_to_dict(keys, values):
    dict = {}
    for i in range(0, len(keys)):
        dict[keys[i]] = values[i]
    return dict

_comparison_map = {'lt':(-1,),
                   '<': (-1,),
                   'gt':(1,),
                   '>':(1,),
                   'le':(-1, 0),
                   '<=':(-1, 0),
                   'ge':(1, 0),
                   '>=':(1, 0)}
def _compare(val1, val2, sign):
    if cmp(val1, val2) in _comparison_map[sign]:
        return 1
    return 0

class ColumnConfiguration:
    def __init__(self,name=None,position=None,sort_order=None,meta=None):
        if meta is None:
            meta = {}
        self.name = name
        self.position = position
        self.meta = meta
        if sort_order in (None, 'None'):
            sort_order = 'none'
        if sort_order not in ['none', 'ascending', 'descending']:
            text = 'Needs to be: "none", "ascending", or "descending"'
            raise _exceptions.EInvalidValue('sort_order', sort_order, text)
        self.sort_order = sort_order
    ##
    # Configure column with dicionary of form:
    # {position:{'name':name, 'sort_order':sort_order}}
    #
    # @param config Configuration Dictionary.
    #
    def _configure(self, config):
        dict = config[config.keys()[0]].copy()
        dict['position'] = config.keys()[0]
        return self.configure(dict)
    def configure(self, config):
        set_attribute(self, 'name', REQUIRED, config, str)
        set_attribute(self, 'position', REQUIRED, config, int)
        set_attribute(self, 'sort_order', 'none', config, str)
        set_attribute(self, 'meta', {}, config)
    def configuration(self):
        config = {}
        get_attribute(self, 'name', config)
        get_attribute(self, 'position', config, str)
        get_attribute(self, 'sort_order', config)
        get_attribute(self, 'meta', config)
        return config
    def get_name(self):
        return self.name
    def get_position(self):
        return self.position
    def get_sort_order(self):
        return self.sort_order
    ##
    # Get configuration dictinary of form:
    # {position:{'name':name, 'sort_order':sort_order}}.
    #
    # @return Configuration dictionary.
    #
    def _configuration(self):
        config = self.configuration()
        del(config['position'])
        _config = {self.position:config}
        return _config

class LogDataManager(_persistent.PersistentDataObject):
    def __init__(self, name):
        _persistent.PersistentDataObject.__init__(self, name)
        self.seq = 0
        self.column_data = {}
        self.log_guid = None
        self.load()
        if self.log_guid is None:
            # Logs now have a GUID.
            self.log_guid = str(UUID())
            self.save()
        self._build_lookup()
        return
    def upgrade(self, pdo):
        self.seq = pdo.seq
        self.column_data = pdo.column_data
        self._build_lookup()
        self.save()

    def get_data(self):
        return self.column_data
    
    def set_data(self, data):
        self.column_data = data
        self.load()
        self._build_lookup()
    ##
    # Take new columns passed in and compare to
    # previous column data to see if we need to add
    # new meta data to our persistent information.
    #
    # @param seq  The seq number that the new configuration
    #             data applies to.
    # @param columns  List of new ColumnConfigurations.
    #
    def configure(self, columns):
        columns_data = {}
        for column in columns:
            columns_data.update(column._configuration())
        if self.column_data:
            last_data = self.column_data[self._lookup[0][0]]
            # last_data = {0:{'name':name, 'sort_order':sort_order}, ...}
            if columns_data == last_data:
                return None
        self.column_data[self.inspect_seq()] = columns_data
        self._build_lookup()
        self.save()
    ##
    # Return a list of ColumnConfiguration objects that describes the
    # configuration of the Log.
    # @param seq The sequence number to use when determining the Log's
    #            configuration.
    # @default None The latest configuration of the log.
    def configuration(self, seq=None):
        keys = []
        keys.extend(self.column_data.keys())
        keys.sort()
        if seq is None:
            key = keys[-1]
        else:
            key = keys[0]
            for i in range(seq):
                if keys[i] <= seq:
                    key = keys[i]
                    break
        column_data = self.column_data[key]
        positions = column_data.keys()
        positions.sort()
        columns = []
        for position in positions:
            column = column_data[position]
            name = column['name']
            sort_order = column['sort_order']
            meta = None
            if column.has_key('meta'):
                meta = column['meta']
            columns.append(ColumnConfiguration(name,position,sort_order,meta))
        return columns
    def _build_lookup(self):
        self._lookup = []
        if not self.column_data:
            return
        seqs = self.column_data.keys()
        seqs.sort()
        seqs.reverse()
        for seq in seqs:
            names = []
            sort_orders = []
            metas = []
            data = self.column_data[seq]
            positions = data.keys()
            positions.sort()
            for position in positions:
                names.append(data[position]['name'])
                sort_orders.append(data[position]['sort_order'])
                metas.append({})
                if data[position].has_key('meta'):
                    metas.append(data[position]['meta'])
            self._lookup.append([seq, names, sort_orders, metas])
    def trim(self, seq, sign):
        seqs = self.column_data.keys()
        seqs.sort()
        if 'g' in sign:
            seqs.pop()
            seqs.reverse()
            _seqs = seqs[:]
        else:
            _seqs = seqs[:-1]
            for i in range(0, len(seqs) - 1):
                seqs[i] = seqs[i + 1] - 1
            seqs.pop()
        deleted = 0
        for i in range(0, len(seqs)):
            if _compare(seqs[i], seq, sign):
                deleted = 1
                del(self.column_data[_seqs[i]])
            else:
                break
        self.save()
        if deleted:
            self._build_lookup()
    def destroy(self):
        self.column_data = {}
        self.seq = 0
        self.save()
        _persistent.PersistentDataObject.destroy(self)
        self._build_lookup()
    def set_seq(self, seq):
        self.seq = seq
        self.save()
    def release_seq(self):
        seq = self.seq
        self.seq += 1
        return seq
    def inspect_seq(self):
        return self.seq
    def get_tuple(self, seq = None):
        if seq == None:
            seq = self._lookup[0][0]
        for tuple in self._lookup:
            if seq >= tuple[0]:
                return tuple
        if seq < tuple[0]:
            return tuple
        raise _exceptions.ENoData()
    def get_name(self, column, seq = None):
        pos = self.get_position(column, seq)
        return self.get_names(seq)[pos]
    def get_names(self, seq = None):
        data = self.get_tuple(seq)
        return data[1]
    def get_sort_order(self, column, seq = None):
        pos = self.get_position(column, seq)
        return self.get_sort_orders(seq)[pos]
    def get_sort_orders(self, seq = None):
        data = self.get_tuple(seq)
        return data[2]
    def get_meta(self,column,seq=None):
        pos = self.get_position(column,seq)
        return self.get_metas(seq)[pos]
    def get_metas(self,seq=None):
        data = self.get_tuple(seq)
        return data[3]
    def get_position(self, column, seq = None):
        if type(column) == types.IntType:
            return column
        try:
            column = self.get_names(seq).index(column)
        except(ValueError):
            raise _exceptions.ENoSuchName(column)
        return column
    def is_sort_order_constant(self, column):
        if type(column) == types.StringType:
            column = self.get_name(column)
        order = self.get_sort_order(column)
        for tuple in self._lookup:
            if self.get_sort_order(column, tuple[0]) != order:
                return 0
        return 1
    def is_position_constant(self, column):
        pos = self.get_position(column)
        for tuple in self._lookup:
            if self.get_position(column, tuple[0]) != pos:
                return 0
        return 1
    def num_columns(self, seq = None):
        return len(self.get_names(seq))

class LogObjectInfo(object):
    def __init__(self, log_object):
        self.first_record=log_object.get_first_record()
        self.last_record=log_object.get_last_record()
        self.column_names=log_object.get_column_names()
        return
    def as_dict(self):
        result = {}
        for attr in ('first_record', 'last_record', 'column_names'):
            result[attr] = getattr(self,attr)
        return result

#
# Install the XMLRPC Marshaller:
#
from mpx.lib.xmlrpclib import register_marshaller
from mpx.lib.xmlrpclib import AsDictMarshaller

register_marshaller(LogObjectInfo, AsDictMarshaller())

##
# Log class manages a log file.
class LogObject_1(EventProducerMixin):
    ##
    # Every low level log object now has a GUID string which uniquely
    # indentifies that log instance.
    # @note There is now way to open a log based on GUID, but that would not be
    #       too hard to implement.
    # @fixme Deleting the PDO losses the GUID and a new GUID will be created,
    #        which is not ideal.  SOMEDAY, WE SHOULD OFFER A BETTER WAY TO
    #        RECOVER THAN DELETING PDOs.  They are intentionally text based,
    #        there should be ways to recover them...
    # @return A string that contains a GUID to use to identify this log
    #         instance. 
    def log_guid(self):
        return self.data_manager.log_guid
    ##
    # 
    def entry_guid_from_seq(self, seq):
        return ''.join((self.data_manager.log_guid, '.', str(seq)))
    ##
    #
    def seq_from_entry_guid(self, entry_guid):
        log_guid, seq_str = entry_guid.split('.')
        assert log_guid == self.log_guid(), (
            "entry_guid(%r) is not valid for this log(%r)" % (entry_guid,
                                                              self.log_guid())
            )
        return int(seq_str)
    def singleton_unload_hook(self):
        return
    def __attributes_str(self):
        result = ''
        for attr in ("name", "filename",):
            try:
                result = ("\n    %s%s = %r") % (
                    result, attr, getattr(self,attr)
                    )
            except:
                result = (
                    "\n    %s%s = Could not determine %s"
                    ) % (result, attr, attr)
        return result
    ##
    # Class method that returns the filename that would be used for
    # a given log name.
    def filename_for(klass, name, recovery_file=0):
        suffix = ".log.1"
        if recovery_file:
            suffix = ".lrf.1"
        qname = urllib.quote(name,' ')
        if qname != name:
            # Support an existing, unquoted, filename, for reverse
            # compatibility.
            filename = os.path.join(properties.LOGFILE_DIRECTORY,
                                    name + suffix)
            if os.path.exists(filename):
                return filename
        return os.path.join(properties.LOGFILE_DIRECTORY, qname + suffix)
    filename_for = classmethod(filename_for)
    def _init_data_manager(self):
        try:
            self.data_manager = LogDataManager(self.filename)
        except:
            raise
        return
    def _init_upgrade(self):
        # Deferred loading should resolve reentrant imports.
        from mpx.lib import msglog
        try:
            # If our file doesn't exist and one without a version number
            # does, rename it (upgrade).
            if (not os.path.exists(self.filename)
                and _prior_version_exists(self.name,self.path)):
                # Deferred loading should resolve reentrant imports.
                # But don't try to log a message if it is the msglog that we are 
                # having problems with or we end up in recursive hell.
                if self.name != 'msglog':
                    from mpx.lib import msglog
                    msglog.log("mpx.lib.log.LogObject_1", msglog.types.INFO,
                               "Upgrading existing log file.")
                from mpx.upgrade.log import log_0
                old = log_0.log(self.name)
                self.data_manager.upgrade(old.data_manager)
                os.rename(old.filename,self.filename)
                old.destroy()
                del(log_0)
        except:
            raise
        return
    def _init_last_values(self):
        self._slice_position = 0
        try:
            self.last_values = self._get_last_row()
        except:
            # But don't try to log a message if it is the msglog that we are 
            # having problems with or we end up in recursive hell.
            if self.name != 'msglog':
                from mpx.lib import msglog
                msglog.log("mpx.lib.log.LogObject_1", msglog.types.WARN,
                           "The %r log is corrupt, attempting to recover" %
                           self.name)
            self._reinit_last_row()
        try:
            # It is likely that the log contains a higher seq number than
            #  the one that was last saved by DataManager, if so, update it.
            # NOTE: the data manager will have a higher number if a trim_g* was
            #       done and then the log was closed.
            if self.last_values:
                if self.last_values[-1] >= self.data_manager.inspect_seq():
                    self.data_manager.set_seq(self.last_values[-1] + 1)
                else:
                    self.last_values = []
        except:
            if not self._reinit_last_seq():
                raise
        return
    def _reinit_last_row(self):
        self.last_values = []
        self.recover(locked=1)
        self.last_values = self._get_last_row()
        return 1
    ##
    # @param name
    #   name of the log
    # @return none
    # @note If the LOGFILE_DIRECTORY property is set the LogObject
    #       will use that path to store the logs.
    def __init__(self, name, recovery_log=0):
        EventProducerMixin.__init__(self)
        self._write_lock = _threading.Lock()
        self._trim_lock = _threading.Lock()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self._queue = []
            self.__eval = _security.RExec().r_eval
            self.path = properties.LOGFILE_DIRECTORY
            self.name = name
            self.filename = self.filename_for(name, recovery_log)
            self._init_data_manager()
            self._init_upgrade()
            self._init_last_values()
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        return
    #########################################################################
    # Configuration
    #########################################################################
    ##
    # @param column_names
    #   a list of column_names to be logged.
    # @return None
    def configure(self, columns):
        self._write_lock.acquire()
        try:
            self._configure(columns)
        finally:
            self._write_lock.release()
    def _configure(self, columns):
        columns = list(columns)
        # build list of ColConfigs from list of strings - backward compat.
        self._string_configured = 0
        if columns and type(columns[0]) == types.StringType:
            self._string_configured = 1
            column_names = columns
            columns = []
            for name in column_names:
                columns.append(ColumnConfiguration(name, len(columns),
                                                   'none'))
        # check to make sure they haven't given a col a name that matches
        #  one of our hidden names.
        positions = []
        names = ['_seq']
        for column in columns:
            if column.name in names:
                raise _exceptions.ENameInUse(column.name)
            names.append(column.name)
            if column.position in positions:
                raise _exceptions.EInvalidValue(
                    'columns',column.name,
                    'Position is already populated.'
                    )
            positions.append(column.position)
        columns.append(ColumnConfiguration('_seq', len(columns), 'ascending'))
        self.last_values = []
        self.columns = columns
        self.data_manager.configure(columns)
    ## 
    # @return Exactly what was passed to the configure method.
    #         It will be a list of names if that what was passed,
    #         otherwise it will be a list of ColumnConfigurations.
    def configuration(self):
        if self._string_configured:
            return self.columns[0:-1]
        else:
            return self.data_manager.get_names()
    ##
    # @param column_name
    # @return int
    #   an int that represents the column_name index
    #   in the current configuration
    def get_column_position(self,column):
        return self.data_manager.get_position(column)
    ##
    # @param column_name_index
    #    an int that is the index of the column_name to return
    # @return string
    #   the column_name
    def get_column_name(self,position):
        return self.data_manager.get_name(position)
    ##
    # @return list of ColumnConfiguration objects.
    #
    def get_columns(self, extended = 0):
        columns = self.columns
        if not extended:
            columns = columns[0:-1]
        return columns
    ##
    # @return list
    #   a list of column names in the order that
    #   they are collected
    def get_column_names(self, extended = 0):
        names = self.data_manager.get_names()
        if not extended:
            names = names[0:-1]
        return names
    def eval(self,line):
        try:
            data = self.__eval(line)
        except:
            raise
        return data
    
    ##########################################################################
    # Data Entry
    ##########################################################################

    ##
    # @param values 
    #  a list of values. values are logged in the same order
    #  as the list of column_names that were passed into the
    #  configure method
    # @throws
    #   EBadConfiguration if the number of
    #   values that are passed in don't match the number
    #   of column_names that were passed in to the
    #   configure method
    def add_entry(self, values):
        if self.last_values:
            sort_orders = self.data_manager.get_sort_orders()
            for pos in range(0, len(values)):
                if sort_orders[pos] == 'ascending':
                    if values[pos] <= self.last_values[pos]:
                        raise _exceptions.EInvalidValue(
                            self.data_manager.get_name(pos),
                            values[pos], 'Contradicts sort order')
                elif sort_orders[pos] == 'descending':
                    if values[pos] >= self.last_values[pos]:
                        raise _exceptions.EInvalidValue(
                            self.data_manager.get_name(index),
                            values[index], 'Contradicts sort order')
        if self.data_manager.num_columns() != (len(values) + 1):
            raise _exceptions.EInvalidValue('values', values)
        self.last_values = values
        self._queue.append(values)
        self._write_queue()
        return
    def _write_queue(self):
        if self._queue and self._write_lock.acquire(0):
            try:
                file = open(self.filename,'a')
                while self._queue:
                    values = self._queue.pop(0)
                    seq = self.data_manager.release_seq()
                    file_row = values + [seq]
                    file.write(repr(file_row) + '\n')
                    if self.event_has_subscribers():
                        event = LogAddEntryEvent(self.log_guid(),
                                                 self.entry_guid_from_seq(seq),
                                                 values, seq, source=self)
                        self.event_generate(event)
                file.close()
            finally:
                self._write_lock.release()
        return

    #########################################################################
    # Data Retrieval
    #########################################################################

    ##
    # @todo There is a lot of repetitive programming that can be 
    #       broken out and re-used by the functions that have them.
    # @todo Currently all read functions acquire the trimming lock, 
    #       which means that only one read function can take place at
    #       a time.  This should be fixed; perhaps trimming and its related
    #       problems should be event driven?
    #
    def get_range(self, column, start, end, extended = 0):
        if not os.path.exists(self.filename):
            return ()
        self._trim_lock.acquire()
        try:
            sort_order = self.data_manager.get_sort_order(column)
            if (sort_order != 'none' and \
                self.data_manager.is_sort_order_constant(column)):
                if ((sort_order == 'descending' and end > start) or
                    (sort_order == 'ascending' and end < start)):
                    temp = end
                    end = start
                    start = temp
                stream = self._get_sorted_range(column,start,end,extended)
            else:
                stream = self._get_unsorted_range(column,start,end,extended)
        finally:
            self._trim_lock.release()
        return stream
    def get_slice(self, column, start, end, extended = 0):
        if not os.path.exists(self.filename):
            return ()
        self._trim_lock.acquire()
        try:
            sort = self.data_manager.get_sort_order(column)
            if (sort == 'none'
                or not self.data_manager.is_sort_order_constant(column)):
                text = 'Cannot get slice on non-ordered field'
                raise _exceptions.EInvalidValue('column', column, text)
            if (sort == 'descending' and end > start) or \
               (sort == 'ascending' and end < start):
                temp = end
                end = start
                start = temp
            stream = self._get_sorted_slice(column,start,end,extended)
        finally:
            self._trim_lock.release()
        return stream
    def get_range_values(self, column, start, end, extended=0):
        sort_order = self.data_manager.get_sort_order(column)
        if (sort_order != 'none'
            and self.data_manager.is_sort_order_constant(column)):
            if ((sort_order == 'descending' and end > start) or
                (sort_order == 'ascending' and end < start)):
                temp = end
                end = start
                start = temp
            stream = self._get_sorted_range_values(column,start,end,extended)
        else:
            stream = self._get_unsorted_range_values(column,start,end,
                                                     extended)
        return stream
    def get_slice_values(self, column, start, end, extended=0):
        if not os.path.exists(self.filename):
            return ()
        self._trim_lock.acquire()
        try:
            sort = self.data_manager.get_sort_order(column)
            if (sort == 'none'
                or not self.data_manager.is_sort_order_constant(column)):
                text = 'Cannot get slice on non-ordered field'
                raise _exceptions.EInvalidValue('column', column, text)
            if (sort == 'descending' and end > start) or \
               (sort == 'ascending' and end < start):
                temp = end
                end = start
                start = temp
            stream = self._get_sorted_slice_values(column,start,end,extended)
        finally:
            self._trim_lock.release()
        return stream
    def _get_sorted_slice_values(self,column,start,end,extended):
        log = open(self.filename, 'r')
        try:
            start,end = self._get_slice_boundries(log,column,start,end)
        except IndexError:
            log.close()
            return ()
        callback = self._get_sorted_item_values_callback
        return self._setup_data_stream(log,callback,start,end,extended)
    def _get_sorted_range_values(self,column,start,end,extended):
        log = open(self.filename, 'r')
        try:
            start,end = self._get_range_boundries(log,column,start,end)
        except IndexError:
            log.close()
            return ()
        callback = self._get_sorted_item_values_callback
        return self._setup_data_stream(log,callback,start,end,extended)
    def _get_unsorted_range_values(self,column,start,end,extended):
        meta = {'column':column,'start_value':start,'end_value':end}
        callback = self._get_unsorted_item_values_callback
        self._write_queue()
        log = open(self.filename, 'r')
        log.seek(0,2)
        return self._setup_data_stream(log,callback,0,log.tell(),extended,
                                       meta)
    def _get_unsorted_range(self,column,start,end,extended):
        meta = {'column':column,'start_value':start,'end_value':end}
        callback = self._get_unsorted_item_dictionary_callback
        self._write_queue()
        log = open(self.filename, 'r')
        log.seek(0,2)
        return self._setup_data_stream(log,callback,0,log.tell(),extended,
                                       meta)
    def _get_sorted_range(self,column,start,end,extended):
        log = open(self.filename, 'r')
        try:
            start,end = self._get_range_boundries(log,column,start,end)
        except IndexError:
            return ()
        callback = self._get_sorted_item_dictionary_callback
        return self._setup_data_stream(log,callback,start,end,extended)
    def _get_sorted_slice(self,column,start,end,extended):
        log = open(self.filename, 'r')
        try:
            start,end = self._get_slice_boundries(log,column,start,end)
        except IndexError:
            log.close()
            return ()
        callback = self._get_sorted_item_dictionary_callback
        return self._setup_data_stream(log,callback,start,end,extended)
    def _get_sorted_item_values_callback(self,index,stream):
        meta = stream.get_meta()
        log = meta['log']
        if index >= 0:
            info = meta['positive']
        else:    
            info = meta['negative']
        if index == info['index'] - 1:
            return info['last']
        increment = 1
        readline = _readline_forwards
        log.seek(info['seek'])
        if info['index'] > index:
            increment = -1
            readline = _readline_backwards
            readline(log)
        for i in range(info['index'],index+1,increment):
            if (log.tell() >= meta['end'] or 
                log.tell() < meta['begin']):
                raise IndexError
            line = readline(log)
        if info['index'] > index:
            log.readline()
        info['index'] = index+1
        info['seek'] = log.tell()
        info['last'] = self.eval(line)
        return info['last']
    def _get_sorted_item_dictionary_callback(self,index,stream):
        values = self._get_sorted_item_values_callback(index,stream)
        extended = stream.get_meta_value('extended')
        return self._convert_to_dictionary(values,extended)
    def _get_unsorted_item_values_callback(self,index,stream):
        meta = stream.get_meta()
        if index >= 0:
            info = meta['positive']
        else:
            info = meta['negative']
        if index == info['index'] - 1:
            return info['last']
        log = meta['log']
        log.seek(info['seek'])
        adjustment = 1
        readline = _readline_forwards
        if index < info['index']:
            readline = _readline_backwards
            adjustment = 0
        count = 0
        while count < abs(index - info['index']) + adjustment:
            if (log.tell() >= meta['end'] or 
                log.tell() < meta['begin']):
                raise IndexError
            line = readline(log)
            entry = self.eval(line)
            value = entry[self.data_manager.get_position(meta['column'],
                                                   entry[-1])]
            if ((value - meta['start_value']) * 
                (value - meta['end_value'])) <= 0:
                count += 1
        if index < info['index']:
            log.readline()
        info['index'] = index + 1
        info['seek'] = log.tell()
        info['last'] = entry
        return info['last']
    def _get_unsorted_item_dictionary_callback(self,index,stream):
        values = self._get_unsorted_item_values_callback(index,stream)
        extended = stream.get_meta_value('extended')
        return self._convert_to_dictionary(values,extended)
    # stream.get_meta() == {'begin':begin_seek,'end':end_seek,
    #                       'extended':extended,
    #                       'positive':{'index':index_of_next_readline,
    #                                   'seek':current_seek_position,
    #                                   'last':list_of_last_values},
    #                       'negative':{'index':index_before_last_read,
    #                                   'seek':pos_of_end_of_index
    #                                   'last':list_of_last_values}}
    def _setup_data_stream(self,log,callback,start,end,extended,meta=None):
        if meta is None:
            meta = {}
        stream = StreamingTupleWithCallback(callback,self._get_stream_length)
        stream.set_meta('begin',start)
        stream.set_meta('end',end)
        stream.set_meta('log', log)
        stream.set_meta('extended', extended)
        positive = {'index':0}
        negative = {'index':-1}
        positive['seek'] = start
        log.seek(end)
        line = _readline_backwards(log)
        negative['seek'] = log.tell()
        positive['last'] = None
        negative['last'] = None
        stream.set_meta('positive',positive)
        stream.set_meta('negative',negative)
        stream.get_meta().update(meta)
        try:
            callback(-1,stream)
            callback(0,stream)
        except IndexError:
            pass
        return stream
    def _get_range_boundries(self, log, column, begin_val, end_val):
        start,end = self._get_slice_boundries(log, column, begin_val, end_val)
        log.seek(end)
        line = log.readline()
        if line:
            list = self.eval(line)
            pos = self.data_manager.get_position(column, list[-1])
            if list[pos] == end_val:
                return (start, log.tell())
        return (start,end)
    def _get_slice_boundries(self, log, column, begin_val, end_val):
        self._write_queue()
        self._write_lock.acquire()
        try:
            log.seek(0,2)
            end = log.tell()
        finally:
            self._write_lock.release()
        start = self._find_boundry(log, column, begin_val, 0, end)
        try:
            end = self._find_boundry(log, column, end_val, start, end)
        except IndexError:
            pass
        return (start,end)
    ##
    # This function will return the seek value such that doing a 
    # readline from the seek value will return the entry whose 
    # value for <code>column</code> == <code>value</code>, or whose 
    # valuse for <code>column</code> is the first that comes after 
    # <code>value</code> in the log.  In the case that it is not 
    # equal in value, an ascending log's value will be first greater 
    # than <code>value</code>, and a descending log's value will be 
    # the first that is less than <code>value</code>.
    #
    # @throws IndexError When end of log is reached and boundry has
    #                    not been found, for example if an ascending 
    #                    columns value is greater than that of the 
    #                    last log, or for a descendings if the value
    #                    is less than the last entry.
    def _find_boundry(self, log, column, value, begin=0, end=None):
        sort = self.data_manager.get_sort_order(column)
        if end == None:
            log.seek(0,2)
            end = log.tell()
        start_at = begin
        end_at = end
        log.seek(begin)
        line_begin = log.tell()
        line = log.readline()
        line_end = log.tell()
        while line:
            list = self.eval(line)
            pos = self.data_manager.get_position(column,list[-1])
            if value == list[pos]:
                return line_begin
            if ((value > list[pos] and sort == 'ascending') or \
                (value < list[pos] and sort == 'descending')):
                if log.tell() >= end:
                    raise IndexError, 'value out of range'
                start_at = log.tell()
            elif ((value < list[pos] and sort == 'ascending') or \
                  (value > list[pos] and sort == 'descending')):
                if line_begin <= begin:
                    return line_begin
                end_at = line_begin
            last_value = list[pos]
            log.seek((start_at + end_at) / 2)
            _seek_beginning(log)
            line_begin = log.tell()
            line = log.readline()
            if line_end == log.tell():
                return line_begin
            line_end = log.tell()
        return line_begin
    def _convert_to_dictionaries(self, data, extended):
        for index in range(0, len(data)):
            data[index] = self._convert_to_dictionary(data[index])
        return data
    def _convert_to_dictionary(self, values, extended):
        names = self.data_manager.get_names(values[-1])
        if not extended:
            names = names[0:-1]
        return convert_to_dict(names,values)
    def get_info(self):
        return LogObjectInfo(self)
    def get_first_record(self):
        self._trim_lock.acquire()
        try:
            values = self._get_first_row()
        finally:
            self._trim_lock.release()
        if not values:
            return {}
        return self._convert_to_dictionary(values,1)
    def get_last_record(self):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            values = self._get_last_row()
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        if not values:
            return {}
        return self._convert_to_dictionary(values,1)
    def _get_stream_length(self,stream):
        if not stream.get_meta().has_key('length'):            
            start = stream.get_meta_value('begin')
            end = stream.get_meta_value('end')
            log = stream.get_meta_value('log')
            log.seek(start)
            line1 = _readline_forwards(log)
            log.seek(end)
            line2 = _readline_backwards(log)
            if not line1 or not line2:
                stream.set_meta('length',0)
            else:
                s1 = self.eval(line1)[-1]
                s2 = self.eval(line2)[-1]
                stream.set_meta('length',s2 - s1 + 1)
        return stream.get_meta_value('length')
    def __getslice__(self, start, end):
        if (end - start) < 1:
            return ()
        return self.get_slice('_seq',start,end,1)
    def __len__(self):
        # returning seq so that - nums can be used in getslice
        return self.data_manager.inspect_seq()
    def __getitem__(self, index):
        def max_seq(self):
            last_record = self.get_last_record()
            if last_record:
                return last_record['_seq']
            return 0
        if isinstance(index,types.SliceType):
            # @note __getslice__ is deprecated but I don't want to change that
            #       now.  ReloadableSingleton object passes along slice()
            #       object as the index.
            start = index.start or 0
            stop = index.stop
            if stop is None:
                stop = max_seq(self) + 1
            return self.__getslice__(start,stop)
        if index < 0:
            index += max_seq(self) + 1
        return self.get_range('_seq', index, index)[0]
    def _get_last_row(self):
        if not os.path.isfile(self.filename):
            return []
        log = open(self.filename,'r')
        try:
            log.seek(0,2)
            line = _readline_backwards(log)
            if not line:
                return []
            list = self.eval(line)
        finally:
            log.close()
        return list
    def _get_first_row(self):
        list = []
        if not os.path.isfile(self.filename):
            return list
        f = open(self.filename,'r')
        try:
            line = f.readline()
            if not line:
                return list
            list = self.eval(line)
        finally:
            f.close()
        return list
    #########################################################################
    # Trimming / Destroying
    #########################################################################

    ##
    # @param column_name
    #   column_name to do the triming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less then the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_lt(self,column_name,value):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self._trim(column_name,value,'lt')
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        self._write_queue()
    ##
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_le(self,column_name,value):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self._trim(column_name,value,'le') 
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        self._write_queue()
    ##
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater then the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_gt(self,column_name,value):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self._trim(column_name,value,'gt')
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        self._write_queue()
    ##
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_ge(self,column_name,start):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self._trim(column_name,start,'ge')
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        self._write_queue()
    ##
    # @param column_name
    #   column_name to do the triming on
    # @param trim_value
    #   the value to use to preform the trim
    # @param sign
    #   the sign to use I.E. lt=<  gt=>,... etc
    # @return None
    def _trim(self,column,value,sign):
        self._slice_position = 0
        sort_order = self.data_manager.get_sort_order(column)
        if (sort_order != 'none'
            and self.data_manager.is_sort_order_constant(column)):
            self._trim_sorted(column, value, sign, sort_order)
        else:
            self._trim_unsorted(column, value, sign)
    def _trim_unsorted(self, column, trim_value, sign):
        full_log = open(self.filename, 'r')
        tmp_file = open(self.filename + '.tmp', 'w')
        line = full_log.readline()
        while line:
            list = self.eval(line)
            names = self.data_manager.get_names(list[-1])
            if column in names:
                value = list[names.index(column)]
                if not _compare(value, trim_value, sign):
                    tmp_file.write(line)
            else:
                tmp_file.write(line)
            line = full_log.readline()
        full_log.close()
        tmp_file.close()
        os.remove(self.filename)
        os.rename(self.filename + '.tmp', self.filename)
    def _trim_sorted(self, column, value, sign, order):
        full_log = open(self.filename, 'r')
        full_log.seek(0,2)
        log_length = full_log.tell()
        try:
            line_begin = self._find_boundry(full_log, column, value)
        except IndexError:
            if ((order == 'ascending' and 'l' in sign)
                or (order == 'descending' and 'g' in sign)):
                column = '_seq'
                value = 0
                sign = 'ge'
                line_begin = 0
            else:
                full_log.close()
                return
        full_log.seek(line_begin)
        line = full_log.readline()
        line_end = full_log.tell()
        list = self.eval(line)
        seq = list[-1]
        pos = self.data_manager.get_position(column, list[-1])
        if ((order == 'ascending' and 'l' in sign)
            or (order == 'descending' and 'g' in sign)):
            column_sign = 'lt'
            begin = line_begin
            end = log_length
            if 'e' in sign:
                if list[pos] == value:
                    begin = line_end
                    column_sign = 'le'
        elif ((order == 'ascending' and 'g' in sign)
              or (order == 'descending' and 'l' in sign)):
            column_sign = 'ge'
            begin = 0
            end = line_begin
            if 't' in sign:
                if list[pos] == value:
                    end = line_end
                    column_sign = 'gt'
        tmp_file = open(self.filename + '.tmp', 'w')
        full_log.seek(begin)
        line = full_log.readline()
        while line:
            if full_log.tell() <= end:
                tmp_file.write(line)
                line = full_log.readline()
            else:
                line = None
        full_log.close()
        tmp_file.close()
        os.remove(self.filename)
        os.rename(self.filename + '.tmp', self.filename)
        self.data_manager.trim(seq, column_sign)
    ##
    # NOT IMPLEMENTED YET
    def reset(self):
        raise ENotImplemented('reset')
    def _destroy(self):
        assert self._trim_lock.locked(), "Trim lock must be locked"
        assert self._write_lock.locked(), "Write lock must be locked"
        self.data_manager.destroy()
        self._slice_position = 0
        if os.path.exists(self.filename):
            os.remove(self.filename)
        return
    ##
    # Deletes the log file and associated PDO.
    def destroy(self):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self._destroy()
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        return
    ##
    # Low-level cut from a file that requires no additional disk space.
    def _cut(self,start,length):
        # This is hard on the flash, but any guesses I make to be
        # nice to the flash will complication the logic and probably
        # not really be any nicer.
        output = os.open(self.filename, os.O_WRONLY)
        input = os.open(self.filename, os.O_RDONLY)
        try:
            os.lseek(output, start, 0)
            os.lseek(input, start+length, 0)
            chunk = os.read(input,1024)
            while chunk:
                os.write(output, chunk)
                chunk = os.read(input,1024)
            os.ftruncate(output, os.lseek(output, 0, 1))
        finally:
            os.close(output)
            os.close(input)
    ##
    # Expensive, but uses minimal disk!
    def _get_and_trim_first_lines(self, count=64):
        nread = 0
        list = []
        if not os.path.isfile(self.filename):
            return list
        f = open(self.filename,'rb')
        try:
            for n in xrange(count):
                line = f.readline()
                if line:
                    list.append(line)
                    nread += len(line)
                else:
                    break
        finally:
            f.close()
        if list:
            self._cut(0, nread)
        return list

    ##
    # Recovers every record possible for a log by processing each row
    # of the log.
    # @param locked Internal use only!
    # @default 0

    # CSCtq99168

    # This a pre 3.1.3 database fix for the power loss during the log recovery problem

    # Scan through the file checking for validity with eval()
    # At the first non valid entry truncate the file inplace and the end of the last
    # valid entry.
    # Also, for the msglog, make sure the sequence number is sensible and saved in the PDO
    # Log a message in msglog about what was done. In the case of the msglog we have to 
    # do this with standard file I/O as we can't call msglog.log() because a lock is already 
    # being held.

    # Switching to sqlite based logs will provide atomic write commit capability
    # which will clean this kind of problem up nicely and recovery will not be necessary 
    # at all.
    def recover(self, locked=0):
        f = open(self.filename, 'r+')
        while True:
            line = f.readline()
            try:
                # Check the validity of the entry and remember the sequence number
                l = self.eval(line)
                seq = l[-1]
            except:
                # Truncate the file right after the end of the last valid entry
                f.truncate(f.tell() - len(line))
                f.close()
                # Log a message but do it at the file level if we are the msglog otherwise we deadlock
                if self.name == 'msglog':
                    self.data_manager.set_seq(seq + 1)
                    f = open('/var/mpx/log/msglog.log.1', 'a')
                    f.write('[%f, "broadway", "warning", "Removed damaged entry in %s (%d bytes)", %d]\n' % (time.time(), self.filename, len(line), seq + 1))
                    f.close()
                else:
                    from mpx.lib import msglog
                    msglog.log("mpx.lib.log.LogObject_1", msglog.types.WARN, "Removed damaged entry in %s (%d bytes)" % (self.filename, len(line)))
                break
        return

LogObject = LogObject_1

class TrimmingLogObject(LogObject):
    trim_on = 1 # trimming is on by default
    
    def configure(self, columns, min_size=250, max_size=500):
        self.set_limits(min_size, max_size)
        LogObject.configure(self, columns)
        self._trim_check = _threading.Lock()
        return
    def set_limits(self, min_size, max_size):
        if min_size >= max_size:
            raise _exceptions.EInvalidValue('min_size',min_size,
                                            'Minimum size must ' +
                                            'be greater than max')
        self.min_bytes = min_size * 1024
        self.max_bytes = max_size * 1024
        return
    def get_limits(self):
        return (self.min_bytes/1024, self.max_bytes/1024)
    def add_entry(self, values):
        LogObject.add_entry(self, values)
        if self.trim_on: # Mark Carlson - 2007-03-21: Only trim if allowed to
            self._trim_check.acquire()
            try:
                log = open(self.filename, 'r')
                log.seek(0, 2)
                length = log.tell()
                if length >= self.max_bytes:
                    log.seek(length - self.min_bytes)
                    log.readline()
                    try:
                        seq = self.eval(log.readline())[-1]
                    except:
                        seq = self.data_manager.inspect_seq() + 1
                    self.trim_lt('_seq', seq)
                log.close()
            finally:
                self._trim_check.release()
    def stop_trimming(self):
        self.trim_on = 0
        return
    def start_trimming(self):
        self.trim_on = 1
        return
    
def _prior_version_exists(name, path):
    if os.path.exists(os.path.join(path,name) + '.log'):
        return 1
    return 0

def version_exists(name,path):
    if LogObject_1.filename_for(name) or _prior_version_exists(name,path):
        return 1
    return 0
