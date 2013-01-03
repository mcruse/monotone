"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
import string
import sys
import time
import traceback
import types
import StringIO
from mpx import properties
from mpx.lib.stream import StreamingTupleWithCallback
from mpx.lib import threading as _threading
from mpx.lib import exceptions as _exceptions
from mpx.lib import security as _security
from mpx.lib import persistent as _persistent
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED

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
def column_sort(c1,c2):
    return c1.position - c2.position
def convert_to_dict(keys, values):
    dict = {}
    for i in range(0, len(keys)):
        dict[keys[i]] = values[i]
    return dict
class _Row:
    def __init__(self,columns):
        self._eval = _security.RExec().r_eval
        self._names = []
        self._columns = columns
        for column in self._columns:
            self._names.append(column.name)
    def get_position(self,column):
        if type(column) is types.IntType:
            return column
        for i in range(0,len(self._columns)):
            if self._columns[i].name == column:
                return i
        raise _exceptions.ENoSuchName(column)
    def get_column(self,column):
        position = self.get_position(column)
        return self._columns[position]
    def get_columns(self,column):
        return self._columns[:]
    def get_name(self,column):
        position = self.get_position(column)
        return self._columns[position].name
    def get_names(self):
        names = []
        for column in self._columns:
            names.append(column.name)
        return names
    def get_sort_order(self,column):
        position = self.get_position(column)
        return self._columns[position].sort_order
    def get_sort_orders(self):
        orders = []
        for column in self._columns:
            orders.append(column.sort_order)
        return orders
    def get_meta(self,column):
        position = self.get_position(column)
        return self._columns[position].meta
    def get_metas(self):
        metas = []
        for column in self._columns:
            metas.append(column.meta)
        return metas
    def __len__(self):
        return len(self._columns)
    def __getitem__(self,key):
        position = self.get_position(key)
        return self._columns[position]
    def as_dictionary(self,data):
        if type(data) is types.StringType:
            data = self.eval(data)
        elif type(data) is types.DictType:
            data = self.as_values(data)
        if type(data) is not types.ListType:
            raise _exceptions.EInvalidValue('data',data)
        return convert_to_dict(self._names[0:len(data)],data)
    def as_values(self,data):
        values = []
        if type(data) is types.DictType:
            for name in self._names:
                values.append(data[name])
            return values
        if type(data) is types.StringType:
            return self.eval(data)
        if type(data) is types.ListType:
            return data
        raise _exceptions.EInvalidValue('data',data)
    def repr(self,values):
        return repr(values)
    def eval(self,line):
        return self._eval(line)
    def sequence(self,data):
        if type(data) is types.StringType:
            index = data.rfind(',')
            if index == -1:
                return int(data.strip()[1:-1].strip())
            return int(data.strip()[index+1:-1].strip())
        elif type(data) is types.ListType:
            return data[-1]
        elif type(data) is types.DictType and data.has_key('_seq'):
            return data['_seq']
        raise _exceptions.EInvalidValue('data',data)
class LogDataManager(_persistent.PersistentDataObject):
    def __init__(self, name):
        _persistent.PersistentDataObject.__init__(self, name)
        self.seq = 0
        self.column_data = {}
        self.load()
        self._seqs = []
        self._rows = {}
        self._build_rows()
    def upgrade(self, pdo):
        seqs = pdo.column_data.keys()
        seqs.sort()
        for seq in seqs:
            columns = pdo.column_data[seq]
            new = []
            for pos,config in columns.items():
                meta = {}
                if config.has_key('meta'):
                    meta = config['meta']
                column = ColumnConfiguration(config['name'],pos,
                                             config['sort_order'],meta)
                new.append(column)
            self.set_seq(seq)
            self.configure(new)
        self.set_seq(pdo.seq)
        self.save()
    def get_columns(self):
        return self.column_data
    def configure(self, columns):
        columns_data = []
        for column in columns:
            columns_data.append(column.configuration())
        if self.column_data:
            last_data = self.column_data[self._seqs[0]]
            if columns_data == last_data:
                return None
        self.column_data[self.inspect_seq()] = columns_data
        self.save()
        self._build_rows()
    def _build_rows(self):
        self._rows = {}
        if not self.column_data:
            return
        self._seqs = self.column_data.keys()
        self._seqs.sort()
        self._seqs.reverse()
        for seq in self._seqs:
            columns = []
            configs = self.column_data[seq]
            for config in configs:
                column = ColumnConfiguration()
                column.configure(config)
                columns.append(column)
            columns.sort(column_sort)
            self._rows[seq] = _Row(columns)
    def get_row(self,seq=None):
        if seq is None:
            return self._rows[self._seqs[0]]
        for sequence in self._seqs:
            if seq >= sequence:
                return self._rows[sequence]
        if seq < self._seqs[-1]:
            return self._rows[self._seqs[-1]]
        raise _exceptions.ENoData()
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
            self._build_rows()
    def destroy(self):
        self.column_data = {}
        self.seq = 0
        self.save()
        _persistent.PersistentDataObject.destroy(self)
        self._build_rows()
    def set_seq(self, seq):
        self.seq = seq
        self.save()
    def release_seq(self):
        seq = self.seq
        self.seq += 1
        return seq
    def inspect_seq(self):
        return self.seq
    def is_sort_order_constant(self, column):
        row = self.get_row()
        order = row.get_sort_order(column)
        for seq in self._seqs[0:-1]:
            row = self.get_row(seq)
            if row.get_sort_order(column) != order:
                return 0
        return 1
    def is_position_constant(self, column):
        row = self.get_row()
        position = row.get_position(column)
        for seq in self._seqs[0:-1]:
            row = self.get_row(seq)
            if row.get_position(column) != position:
                return 0
        return 1
    def get_seq(self,line):
        return self.get_row().sequence(line)
##
# Log class manages a log file.
class LogObject_2:
    ##
    # @param name
    #   name of the log
    # @return none
    # @note If the LOGFILE_DIRECTORY property is set the LogObject
    #       will use that path to store the logs.
    def __init__(self,name):
        self._write_lock = _threading.Lock()
        self._trim_lock = _threading.Lock()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self.name = name
            self._queue = []
            self.eval = _security.RExec().r_eval
            self.path = properties.LOGFILE_DIRECTORY
            self.filename = os.path.join(self.path, self.name + ".log.2")
            self.data_manager = LogDataManager(self.filename)
            # If our file doesn't exist and one without a version number
            #  does, rename it (upgrade).
            if (not os.path.exists(self.filename)
                and _prior_version_exists(self.name,self.path)):
                from mpx.upgrade.log import log_1
                old = log_1.LogObject(name)
                self.data_manager.upgrade(old.data_manager)
                os.rename(old.filename,self.filename)
                old.destroy()
                del(log_1)
            self._slice_position = 0
            self.last_values = self._get_last_row()
            # It is likely that the log contains a higher seq number than
            #  the one that was last saved by DataManager, if so, update it.
            # NOTE: the data manager will have a higher number if a trim_g* was
            #       done and then the log was closed.
            if self.last_values:
                if self.last_values[-1] >= self.data_manager.inspect_seq():
                    self.data_manager.set_seq(self.last_values[-1] + 1)
                else:
                    self.last_values = []
        finally:
            self._write_lock.release()
            self._trim_lock.release()
    
    ############################################################################
    # Configuration
    ############################################################################
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
                columns.append(ColumnConfiguration(name, len(columns), 'none'))
        # check to make sure they haven't given a col a name that matches
        #  one of our hidden names.
        positions = []
        names = ['_seq']
        for column in columns:
            if column.name in names:
                raise _exceptions.ENameInUse(column.name)
            names.append(column.name)
            if column.position in positions:
                raise _exceptions.EInvalidValue('columns',column.name,
                                                'Position is already populated.')
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
        return self.data_manager.get_row().get_position(column)
    ##
    # @param column_name_index
    #    an int that is the index of the column_name to return
    # @return string
    #   the column_name
    def get_column_name(self,position):
        return self.data_manager.get_row().get_name(position)
    ##
    # @return list of ColumnConfiguration objects.
    #
    def get_columns(self, extended = 0):
        columns = self.data_manager.get_row().get_columns()
        if not extended:
            columns = columns[0:-1]
        return columns
    ##
    # @return list
    #   a list of column names in the order that
    #   they are collected
    def get_column_names(self, extended = 0):
        names = self.data_manager.get_row().get_names()
        if not extended:
            names = names[0:-1]
        return names
    
    ############################################################################
    # Data Entry
    ############################################################################
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
        row = self.data_manager.get_row()
        if self.last_values:
            sort_orders = row.get_sort_orders()
            for pos in range(0, len(values)):
                if sort_orders[pos] == 'ascending':
                    if values[pos] <= self.last_values[pos]:
                        raise _exceptions.EInvalidValue(
                            row.get_name(pos),
                            values[pos], 'Contradicts sort order')
                elif sort_orders[pos] == 'descending':
                    if values[pos] >= self.last_values[pos]:
                        raise _exceptions.EInvalidValue(
                            row.get_name(index),
                            values[index], 'Contradicts sort order')
        if len(row) != (len(values) + 1):
            raise _exceptions.EInvalidValue('values', values)
        self.last_values = values
        self._queue.append((row,values))
        self._write_queue()
    def _write_queue(self):
        if self._queue and self._write_lock.acquire(0):
            try:
                file = open(self.filename,'a')
                while self._queue:
                    row,values = self._queue.pop(0)
                    values.append(self.data_manager.release_seq())
                    file.write(row.repr(values) + '\n')
                file.close()
            finally:
                self._write_lock.release()
        return
    ############################################################################
    # Data Retrieval
    ############################################################################
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
            sort_order = self.data_manager.get_row().get_sort_order(column)
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
            sort = self.data_manager.get_row().get_sort_order(column)
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
        sort_order = self.data_manager.get_row().get_sort_order(column)
        if (sort_order != 'none'
            and self.data_manager.is_sort_order_constant(column)):
            if ((sort_order == 'descending' and end > start) or
                (sort_order == 'ascending' and end < start)):
                temp = end
                end = start
                start = temp
            stream = self._get_sorted_range_values(column,start,end,extended)
        else:
            stream = self._get_unsorted_range_values(column,start,end,extended)
        return stream
    def get_slice_values(self, column, start, end, extended=0):
        if not os.path.exists(self.filename):
            return ()
        self._trim_lock.acquire()
        try:
            sort = self.data_manager.get_row().get_sort_order(column)
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
        return self._setup_data_stream(log,callback,0,log.tell(),extended,meta)
    def _get_unsorted_range(self,column,start,end,extended):
        meta = {'column':column,'start_value':start,'end_value':end}
        callback = self._get_unsorted_item_dictionary_callback
        self._write_queue()
        log = open(self.filename, 'r')
        log.seek(0,2)
        return self._setup_data_stream(log,callback,0,log.tell(),extended,meta)
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
        row = self.data_manager.get_row(self.data_manager.get_seq(line))
        info['last'] = row.eval(line)
        return info['last']
    def _get_sorted_item_dictionary_callback(self,index,stream):
        values = self._get_sorted_item_values_callback(index,stream)
        row = self.data_manager.get_row(values[-1])
        if not stream.get_meta_value('extended'):
            return row.as_dictionary(values[0:-1])
        return row.as_dictionary(values)
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
            row = self.data_manager.get_row(self.data_manager.get_seq(line))
            entry = row.eval(line)
            value = entry[row.get_position(meta['column'])]
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
        row = self.data_manager.get_row(values[-1])
        if not stream.get_meta_value('extended'):
            return row.as_dictionary(values[0:-1])
        return row.as_dictionary(values)
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
            row = self.data_manager.get_row(self.data_manager.get_seq(line))
            if row.eval(line)[row.get_position(column)] == end_val:
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
        sort = self.data_manager.get_row().get_sort_order(column)
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
            row = self.data_manager.get_row(self.data_manager.get_seq(line))
            list = row.eval(line)
            pos = row.get_position(column)
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
    def get_first_record(self):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            values = self._get_first_row()
            row = self.data_manager.get_row(values[-1])
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        return row.as_dictionary(values)
    def _get_first_row(self):
        line = self._get_first_line()
        if not line:
            return []
        row = self.data_manager.get_row(self.data_manager.get_seq(line))
        return row.as_values(line)
    def get_last_record(self):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            values = self._get_last_row()
            row = self.data_manager.get_row(values[-1])
        finally:
            self._write_lock.release()
            self._trim_lock.release()
        return row.as_dictionary(values)
    def _get_last_row(self):
        line = self._get_last_line()
        if not line:
            return []
        row = self.data_manager.get_row(self.data_manager.get_seq(line))
        return row.as_values(line)
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
                s1 = self.data_manager.get_seq(line1)
                s2 = self.data_manager.get_seq(line2)
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
        if index < 0:
            index += self.get_last_record()['_seq'] + 1
        return self.get_range('_seq', index, index)[0]
    def _get_last_line(self):
        if not os.path.isfile(self.filename):
            return ''
        log = open(self.filename,'r')
        try:
            log.seek(0,2)
            return _readline_backwards(log)
        finally:
            log.close()
    def _get_first_line(self):
        if not os.path.isfile(self.filename):
            return ''
        f = open(self.filename,'r')
        try:
            return f.readline()
        finally:
            f.close()
    ############################################################################
    # Trimming / Destroying
    ############################################################################
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
        sort_order = self.data_manager.get_row().get_sort_order(column)
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
            row = self.data_manager.get_row(self.data_manager.get_seq(line))
            names = row.get_names()
            if column in names:
                value = row.eval(line)[names.index(column)]
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
        seq = self.data_manager.get_seq(line)
        row = self.data_manager.get_row(seq)
        list = row.eval(line)
        pos = row.get_position(column)
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
    ##
    # deletes the log file
    def destroy(self):
        self._write_queue()
        self._trim_lock.acquire()
        self._write_lock.acquire()
        try:
            self.data_manager.destroy()
            self._slice_position = 0
            if os.path.exists(self.filename):
                os.remove(self.filename)
        finally:
            self._write_lock.release()
            self._trim_lock.release()

LogObject = LogObject_2

class TrimmingLogObject(LogObject):
    def configure(self, columns, min_size=250, max_size=500):
        self.set_limits(min_size, max_size)
        LogObject.configure(self, columns)
        self._trim_check = _threading.Lock()
        return
    def set_limits(self, min_size, max_size):
        self.min_bytes = min_size * 1024
        self.max_bytes = max_size * 1024
        return
    def add_entry(self, values):
        LogObject.add_entry(self, values)
        self._trim_check.acquire()
        try:
            log = open(self.filename, 'r')
            log.seek(0, 2)
            length = log.tell()
            if length >= self.max_bytes:
                log.seek(length - self.min_bytes)
                log.readline()
                line = log.readline()
                try:
                    seq = self.data_manager.get_seq(log.readline())
                except:
                    seq = self.data_manager.inspect_seq() + 1
                self.trim_lt('_seq', seq)
            log.close()
        finally:
            self._trim_check.release()

def _prior_version_exists(name, path):
    if (os.path.exists(os.path.join(path,name) + '.log') or 
        os.path.exists(os.path.join(path,name) + '.log.1')):
        return 1
    return 0

def version_exists(name,path):
    if (os.path.exists(os.path.join(path,name) + '.log.2') or 
        _prior_version_exists(name,path)):
        return 1
    return 0
