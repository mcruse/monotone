"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
# Log
# @author Craig Warren

import string
import time
import os
import traceback
import sys

from mpx._python import types

from mpx import properties

from mpx.lib import threading

from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENameInUse
from mpx.lib.exceptions import ENoData
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ERangeError

from mpx.lib.security import RExec
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED

def _convert_to_dict(keys, values):
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
    def __init__(self, name = None, position = None, sort_order = 'none'):
        self.name = name
        self.position = position
        if sort_order in (None, 'None'):
            sort_order = 'none'
        if sort_order not in ['none', 'ascending', 'descending']:
            raise EInvalidValue('sort_order', sort_order,
                                'Needs to be: "none", "ascending", or "descending"')
        self.sort_order = sort_order
    ##
    # Configure column with dicionary of form:
    # {position:{'name':name, 'sort_order':sort_order}}
    #
    # @param config Configuration Dictionary.
    #
    def _configure(self, config):
        self.position = config.keys()[0]
        self.name = config[self.position]['name']
        self.sort_order = config[self.position]['sort_order']
    def configure(self, config):
        set_attribute(self, 'name', REQUIRED, config, str)
        set_attribute(self, 'position', REQUIRED, config, int)
        set_attribute(self, 'sort_order', 'none', config, str)
    def configuration(self):
        config = {}
        get_attribute(self, 'name', config)
        get_attribute(self, 'position', config, str)
        get_attribute(self, 'sort_order', config)
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
        return {self.position:{'name':self.name, 'sort_order':self.sort_order}}

class _LogDataManager(PersistentDataObject):
    def __init__(self, name):
        PersistentDataObject.__init__(self, name)
        self.seq = 0
        self.column_data = {}
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
    def _build_lookup(self):
        self._lookup = []
        if not self.column_data:
            return
        seqs = self.column_data.keys()
        seqs.sort()
        seqs.reverse()
        # self._lookup = 
        for seq in seqs:
            names = []
            sort_orders = []
            data = self.column_data[seq]
            positions = data.keys()
            positions.sort()
            for position in positions:
                names.append(data[position]['name'])
                sort_orders.append(data[position]['sort_order'])
            self._lookup.append((seq, names, sort_orders))
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
        PersistentDataObject.destroy(self)
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
        raise ENoData()
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
    def get_position(self, column, seq = None):
        if type(column) == types.IntType:
            return column
        try:
            column = self.get_names(seq).index(column)
        except(ValueError):
            raise ENoSuchName(column)
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

#holds locks for all locks
_logs = {}
_logs_lock = threading.RLock()

##
# Log class manages a log file.
class LogObject_0:
    ##
    # @author Craig Warren
    # @param name
    #   name of the log
    # @return none
    # @note If the LOGFILE_DIRECTORY property is set the LogObject
    #       will use that path to store the logs.
    def __init__(self,name):
        _logs_lock.acquire()
        try:
            if _logs.has_key(name):
                from mpx.lib.msglog import types
                raise ENameInUse(name, logtype = types.ERR)
            self._lock = threading.Lock()
            self._lock.acquire()
            _logs[name] = self
        finally:
            _logs_lock.release()
        try:
            self.name = name
            self.eval = RExec().r_eval
            self.path = properties.LOGFILE_DIRECTORY
            self.filename = os.path.join(self.path, self.name + ".log")
            self.data_manager = _LogDataManager(self.filename)

            self._slice_position = 0
            self.max_return_length = 100000
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
            self._lock.release()
    ##
    # @author Craig Waren
    # @param column_names
    #   a list of column_names to be logged.
    # @return None
    def configure(self, columns, max_return_length = 100):
        self._lock.acquire()
        try:
            self._configure(columns, max_return_length)
        finally:
            self._lock.release()
    
    def _configure(self, columns, max_return_length):
        self.max_return_length = max_return_length * 1024
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
        for column in columns:
            if column.name == '_seq':
                raise ENameInUse(column.name)
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
    # @author Craig Warren
    # @param column_name
    # @return int
    #   an int that represents the column_name index
    #   in the current configuration
    def get_column_position(self,column):
        return self.data_manager.get_position(column)

    ##
    # @author Craig Warren
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
    # @author Craig Warren
    # @return list
    #   a list of column names in the order that
    #   they are collected
    def get_column_names(self, extended = 0):
        names = self.data_manager.get_names()
        if not extended:
            names = names[0:-1]
        return names
    
    ##
    # @author Craig Warren
    # @param values 
    #  a list of values. values are logged in the same order
    #  as the list of column_names that were passed into the
    #  configure method
    # @throws
    #   EBadConfiguration if the number of
    #   values that are passed in don't match the number
    #   of column_names that were passed in to the
    #   configure method
    def add_entry(self,values):
        self._lock.acquire()
        try:
            self._add_entry(values)
        finally:
            self._lock.release()

    def _add_entry(self, values):
        if self.last_values:
            sort_orders = self.data_manager.get_sort_orders()
            for pos in range(0, len(values)):
                if sort_orders[pos] == 'ascending':
                    if values[pos] <= self.last_values[pos]:
                        raise EInvalidValue(self.data_manager.get_name(pos),
                                        values[pos], 'Contradicts sort order')
                elif sort_orders[pos] == 'descending':
                    if values[pos] >= self.last_values[pos]:
                        raise EInvalidValue(self.data_manager.get_name(index),
                                        values[index], 'Contradicts sort order')
        if self.data_manager.num_columns() != (len(values) + 1):
            raise EInvalidValue('values', values)           
        file = open(self.filename,"a")    
        file.write(repr(values + [self.data_manager.release_seq()]) + "\n")
        file.close()
        self.last_values = values

    def get_range(self, column, start, end, extended = 0):
        data = []
        if not os.path.exists(self.filename):
            return data
        self._lock.acquire()
        try:
            data = self._get_range(column, start, end, extended)
            data = self._convert_to_dictionaries(data, extended)
        finally:
            self._lock.release()
        return data
    
    def _get_range(self, column, start, end, extended):
        sort_order = self.data_manager.get_sort_order(column)
        if sort_order != 'none' and self.data_manager.is_sort_order_constant(column):
            if (sort_order == 'descending' and end > start) or \
               (sort_order == 'ascending' and end < start):
                temp = end
                end = start
                start = temp
            data = self._get_sorted_range(column, start, end, sort_order)
        else:
            data = self._get_unsorted_range(column, start, end)
        return data
    
    def _convert_to_dictionaries(self, data, extended):
        for index in range(0, len(data)):
            names = self.data_manager.get_names(data[index][-1])
            if not extended:
                names = names[0:-1]
            data[index] = _convert_to_dict(names, data[index])
        return data

    def get_slice(self, column, start, end, extended = 0):
        if not os.path.exists(self.filename):
            return []
        self._lock.acquire()
        try:
            sort = self.data_manager.get_sort_order(column)
            if sort == 'none' or not self.data_manager.is_sort_order_constant(column):
                raise EInvalidValue('column', column, 'Cannot get slice on non-ordered field')
            if column == '_seq':
                end -= 1
            data = self._get_range(column, start, end, extended)
            data = self._convert_to_dictionaries(data, extended)
        finally:
            self._lock.release()
        if data and (column != '_seq') and (data[-1][column] == end):
            data.pop()
        return data
    
    def get_range_values(self, column, start, end, extended=0):
        data = []
        if not os.path.exists(self.filename):
            return data
        self._lock.acquire()
        try:
            data = self._get_range(column, start, end, extended)
        finally:
            self._lock.release()
        if not extended:
            for i in range(0, len(data)):
                data[i] = data[i][:-1]
        return data
    
    def get_slice_values(self, column, start, end, extended=0):
        if not os.path.exists(self.filename):
            return []
        self._lock.acquire()
        try:
            sort = self.data_manager.get_sort_order(column)
            if sort == 'none' or not self.data_manager.is_sort_order_constant(column):
                raise EInvalidValue('column', column, 'Cannot get slice on non-ordered field')
            if column == '_seq':
                end -= 1
            data = self._get_range(column, start, end, extended)
            index = self.data_manager.get_position(column)
        finally:
            self._lock.release()
        if data and (column != '_seq') and (data[-1][index] == end):
            data.pop()
        if not extended:
            for i in range(0, len(data)):
                data[i] = data[i][:-1]
        return data
    
    def get_first_record(self):
        data = {}
        self._lock.acquire()
        try:
            values = self._get_first_row()
        finally:
            self._lock.release()
        if not values:
            return data
        names = self.data_manager.get_names(values[-1])
        data = _convert_to_dict(names, values)
        return data
    
    def get_last_record(self):
        data = {}
        self._lock.acquire()
        try:
            values = self._get_last_row()
        finally:
            self._lock.release()
        if not values:
            return data
        names = self.data_manager.get_names(values[-1])
        data = _convert_to_dict(names, values)
        return data
    
    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the triming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less then the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_lt(self,column_name,value):
        self._lock.acquire()
        try:
            self._trim(column_name,value,'lt')
        finally:
            self._lock.release()

    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_le(self,column_name,value):
        self._lock.acquire()
        try:
            self._trim(column_name,value,'le') 
        finally:
            self._lock.release()

    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater then the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_gt(self,column_name,value):
        self._lock.acquire()
        try:
            self._trim(column_name,value,'gt')
        finally:
            self._lock.release()

    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_ge(self,column_name,start):
        self._lock.acquire()
        try:
            self._trim(column_name,start,'ge')
        finally:
            self._lock.release()

    ##
    # @author Craig Warren
    # NOT IMPLEMENTED YET
    def reset(self):
        raise ENotImplemented('reset')

    ##
    # @author Craig Warren
    # deletes the log file
    def destroy(self):
        self._lock.acquire()
        try:
            self.data_manager.destroy()
            self._slice_position = 0
            if os.path.exists(self.filename):
                os.remove(self.filename)
        finally:
            self._lock.release()
    
    def _get_unsorted_range(self, column, start, end):
        values = []
        log = open(self.filename, 'r')
        data_len = 0
        line = log.readline()
        while line:
            if data_len > self.max_return_length:
                raise ERangeError(column, start, end)
            list = self.eval(line)
            names = self.data_manager.get_names(list[-1])
            if column in names:
                pos = names.index(column)
                if start <= list[pos] and end >= list[pos]:
                    data_len += len(line)
                    values.append(list)
            line = log.readline()
        log.close()
        return values

    def _get_sorted_range(self, column, start, end, sort = None):
        if sort == None:
            sort = self.data_manager.get_sort_order(column)
        values = []
        log = open(self.filename, 'r')
        try:
            log.seek(self._find_equal_to_or_after(start, log, column, self._slice_position))
        except IndexError:
            return values
        data_len = 0
        line = log.readline()
        while line:
            list = self.eval(line)
            data_len += len(line)
            line = None
            pos = self.data_manager.get_position(column, list[-1])
            if data_len > self.max_return_length:
                raise ERangeError(column, start, end, good_end=values[-2][pos])
            if (sort == 'ascending' and end >= list[pos]) or \
               (sort == 'descending' and end <= list[pos]):
                values.append(list)
                self._slice_position = log.tell()
                line = log.readline()
        log.close()
        return values
    
    # Return a seek position such that, if you seek to that
    #  position and then do a readline, you will have the first
    #  entry whose first column is >= value.
    # @throws IndexError exception if value is greater than
    #         last value in the log.
    # @return Seek position for begining of line.
    def _find_equal_to_or_after(self, value, log, column, start_from = 0):
        bottom = 0
        log.seek(0, 2)
        log_len = log.tell()
        top = log_len
        log.seek(start_from)
        line_begin = start_from
        line = log.readline()
        if not line:
            log.seek(0)
            line_begin = 0
            line = log.readline()
        last_value = None
        sort_order = self.data_manager.get_sort_order(column)
        while line:
            list = eval(line)
            line = None
            pos = self.data_manager.get_position(column, list[-1])
            if value != list[pos] and last_value != list[pos]:
                if line_begin == 0:
                    if (sort_order == 'ascending' and value < list[pos]) or \
                       (sort_order == 'descending' and value > list[pos]):
                        return line_begin
                if log.tell() == log_len:
                    if (sort_order == 'ascending' and value > list[pos]) or \
                       (sort_order == 'descending' and value < list[pos]):
                        raise IndexError, 'value out of range'
                if (value > list[pos] and sort_order == 'ascending') or \
                     (value < list[pos] and sort_order == 'descending'):
                    bottom = log.tell()
                elif (value < list[pos] and sort_order == 'ascending') or \
                     (value > list[pos] and sort_order == 'descending'):
                    top = line_begin
                log.seek((top + bottom) / 2)
                # need to get to the beggining of this line
                while log.tell() != 0 and log.read(1) != '\n':
                    log.seek(-2, 1)
                line_begin = log.tell()
                last_value = list[pos]
                line = log.readline()
        return line_begin

    def __getslice__(self, start, end):
        return self.get_slice('_seq', start, end, 1)
    def __len__(self):
        # returning seq so that - nums can be used in getslice
        return self.data_manager.inspect_seq()
    def __getitem__(self, index):
        if index < 0:
            index += self.get_last_record()['_seq'] + 1
        return self.get_range('_seq', index, index)[0]
    
    def _get_last_row(self):
        list = []
        if not os.path.isfile(self.filename):
            return list
        f = open(self.filename)
        f.seek(0, 2)
        if f.tell() != 0:
            char = None
            while char != '\n' and f.tell() > 2:
                f.seek(-2, 1)
                char = f.read(1)
            if f.tell() <= 2:
                f.seek(0)
            line = f.readline()
            list = eval(line)
        f.close()
        return list
    
    def _get_first_row(self):
        list = []
        if not os.path.isfile(self.filename):
            return list
        f = open(self.filename)
        line = f.readline()
        if line:
            list = eval(line)
        f.close()
        return list
    
    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the triming on
    # @param trim_value
    #   the value to use to preform the trim
    # @param sign
    #   the sign to use I.E. lt=<  gt=>,... etc
    # @return None
    def _trim(self,column,value,sign):        
        sort_order = self.data_manager.get_sort_order(column)
        if sort_order != 'none' and self.data_manager.is_sort_order_constant(column):
            self._trim_sorted(column, value, sign, sort_order)
        else:
            self._trim_unsorted(column, value, sign)
    
    def _trim_unsorted(self, column, trim_value, sign):
        full_log = open(self.filename, 'r')
        tmp_file = open(self.filename + '.tmp', 'w')
        line = full_log.readline()
        while line:
            list = eval(line)
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
            line_begin = self._find_equal_to_or_after(value, full_log, column)            
        except IndexError:
            if (order == 'ascending' and 'l' in sign) or \
               (order == 'descending' and 'g' in sign):
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
        list = eval(line)
        seq = list[-1]
        pos = self.data_manager.get_position(column, list[-1])
        if (order == 'ascending' and 'l' in sign) or \
           (order == 'descending' and 'g' in sign):
            column_sign = 'lt'
            begin = line_begin
            end = log_length
            if 'e' in sign:
                if list[pos] == value:
                    begin = line_end
                    column_sign = 'le'
        elif (order == 'ascending' and 'g' in sign) or \
             (order == 'descending' and 'l' in sign):
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
    # @author Craig Warren
    # puts a lock on the log file
    def lock(self):
        self._lock.acquire()

    ##
    # @author Craig Warren
    # unlocks the log file
    def unlock(self):
         self._lock.release()

LogObject = LogObject_0

class TrimmingLogObject(LogObject):
    def configure(self, columns, min_size=250, max_size=500, max_return_length=100):
        self.min_bytes = min_size * 1024
        self.max_bytes = max_size * 1024
        LogObject.configure(self, columns, max_return_length)
    
    def add_entry(self, values):
        LogObject.add_entry(self, values)
        self._lock.acquire()
        try:
            log = open(self.filename, 'r')
            log.seek(0, 2)
            length = log.tell()
            log.close()
            if length >= self.max_bytes:
                self._backup()
        finally:
            self._lock.release()
    
    def _backup(self):
        log = open(self.filename, 'r')
        try:
            log.seek(self.min_bytes)
            log.readline()
            seq = eval(log.readline())[-1]
        finally:
            log.close()
        # Need to call private func so
        # no double lock occurs.
        self._trim('_seq', seq, 'le')


def Log(name, trimming=0):
    _logs_lock.acquire()
    try:
        if not _logs.has_key(name):
            if trimming:
                TrimmingLogObject(name)
            else:
                LogObject(name)
        log = _logs[name]
    finally:
        _logs_lock.release()
    return log
log = Log

def TrimmingLog(name):
    return Log(name, 1)
trimming_log = TrimmingLog

    
