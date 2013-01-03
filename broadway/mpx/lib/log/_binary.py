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
import os
import struct
import string
from mpx import properties
from mpx.lib import EnumeratedValue
from mpx.lib.threading import Lock
from mpx.lib.configure import set_attribute,get_attribute
from mpx.lib.exceptions import EInvalidValue
import _log

class BinaryColumnConfiguration(_log.ColumnConfiguration):
    def __init__(self,name=None,position=None,sort_order='none',type=None):
        self.type = type
        _log.ColumnConfiguration.__init__(self,name,position,sort_order)
    def configure(self,config):
        _log.ColumnConfiguration.configure(self,config)
        set_attribute(self,'type','float',config,_to_type_value)
    def configuration(self):
        config = _log.ColumnConfiguration.configuration(self)
        get_attribute(self,'type',config,_to_type_name)
        return config
    def get_type(self):
        return _to_type_name(self.type)
class RecordConfiguration:
    def __init__(self,colum_configs):
        self._columns = colum_configs
    def columns(self):
        return self._columns
    def column(self,index):
        return self.columns()[index]
##
# @todo RecordManager is going to need to be a 
#       PDO that stores seqs and validity values.
class RecordManager:
    def __init__(self,log):
        self._log = log
    def configure(self,record_config):
        self._config = record_config
    def configuration(self):
        return self._config
    ##
    # @param record Record instance with one column
    #               initialized.  Rest will be filled
    #               in from log.
    def record(self,record):
        pass
    ##
    # Get records from record1 to record2.  
    # 
    # @param record1 Beginning Record instance with 
    #                one column initialized.
    # @param record2 Ending Record.
    # @return Stream object.
    # @note Inclusive of boundries.
    def records(self,record1,record2):
        pass
    ##
    # @see records
    # @note Exclusive of ending boundry.
    def record_slice(self,record1,record2):
        pass
    ##
    # Index passed in is record number.
    def __getitem__(self,seq):
        pass
    ##
    # @see record_slice
    def __getslice__(self,seq1,seq2):
        pass
    ##
    # @return Fully configured record instance
    #         that with columns = values.
    def initialize_record(self,values):
        pass
    ##
    # @see initialize_record
    # Works with list of column sets.
    def initialize_records(self,value_set):
        records = []
        for values in value_set:
            records.append(self.initialize_record(values))
        return records
    ##
    # Return configured record with no values set.
    def record_factory(self):
        pass
    ##
    # Add one record to the log.
    def add_record(self,record):
        pass
    ##
    # Add multiple records to the log.
    def add_records(self,records):
        pass
    ##
    # Save a record back to the config file,
    # no matter where its location within the file is.
    # This function can be used to update something 
    # like the time on a bunch of existing records.
    def save_record(self,record):
        pass
    ##
    # Can be used to apply a change to all records 
    # in a log.  For example, records could be a stream 
    # that is reading a stream from a get_records 
    # on the same log and applying some modification 
    # to each one, like add n seconds to timestamp.
    # @see save_record
    def save_records(self,records):
        for record in records:
            self.save_record(record)
    ##
    # Deletes record with column == <code>column</code>.
    def delete_record(self,column):
        pass
    ##
    # Deletes all records with columns between col1 
    # and col2.  Inclusive of col2.
    def delete_records(self,record1,record2):
        pass
    ##
    # @see delet_records
    # Exclusive of col2.
    def delete_slice(self,record1,record2):
        pass
    
class Record_0:
    ##
    # @param record_config The record configuration
    #                      that applies to this record.
    def __init__(self,record_config):
        self._config = record_config
        self._columns = []
        for column_config in record_config.columns():
            self._columns.append(Column(column_config))
    ##
    # Get the records configuration.
    def configuration(self):
        return self._config
    ##
    # Get list of column objects that have been
    # initialized.
    def columns(self):
        return self._columns
    ##
    # Get binary representation of this records data.
    def to_binary(self):
        bin = ''
        for column in self.columns():
            bin += column.to_binary()
        return bin
    ##
    # Initialize this record's data from binary representation.
    def from_binary(self,data):
        for column in self.columns():
            column.from_binary(data[0:column.size()])
            data = data[column.size():]
    ##
    # Get the validity counter of this record.
    # Zero means that the record has not been deleted,
    # otherwise, it is an ever increasing integer that 
    # can be used to make decisions regarding dirty reads.
    def validity(self):
        return self.columns()[0].value()
    ##
    # Get the sequence number of this record.
    def sequence(self):
        return self.columns()[1].value()
    ##
    # Set the validity of this record.
    def set_validity(self,validity):
        self.columns()[0].set_value(validity)
    ##
    # Set the sequence number of this record.
    def set_sequence(self,seq):
        self.columns()[1].set_value(seq)
    ##
    # True if this record has not been 
    # deleted.
    def is_valid(self):
        return not self.validity()
Record = Record_0

##
# @todo Consider adding pack and unpack 
#       functions to interface to mirror 
#       the struct module.
class Column_0:
    def __init__(self,column_config):
        self._config = column_config
        # 0 so that it can be put into bin.
        self._value = 0
        # Invalid to start.
        self._validity = 0x01
    def configuration(self):
        return self._config
    ##
    # Get the name of this column.
    def name(self):
        return self._config.name
    ##
    # Get the position of this column within
    # the record.
    def position(self):
        return self._config.position
    ##
    # Output value and validity information 
    # as it should be stored in log file.
    def to_binary(self):
        return struct.pack('B'+self._config.type(),self._validity,self._value)
    ##
    # Takes binary data and turns it into value and validity.
    def from_binary(self,data):
        values = struct.unpack('B'+self._config.type(),data)
        self._validity,self._value = values
    ##
    # Get the value of this column.
    def value(self):
        return self._value
    ##
    # Get the value of this columns 
    # validity byte; hook for when 
    # validity bytes are not just 1 or 0.
    def validity(self):
        return self._validity
    ##
    # Set the value and optionaly the validity of this column.
    def set_value(self,value,validity=1):
        self._value = value
        self._validity = validity
    ##
    # Hook for being able to encode information
    # into the value of the validity byte.
    def set_validity(self,validity):
        self._validity = validity
    ##
    # Set validity byte to indicate 
    # invalid record.
    def invalidate(self):
        self.set_validity(0x01)
    ##
    # Check to see if this column has 
    # been invalidated.
    def is_valid(self):
        if not self._validity:
            return 1
        return 0
    def __len__(self):
        return struct.calcsize('B'+self._config.type)
    def size(self):
        return self.__len__()
Column = Column_0

class _FixedLengthLogObject_0:
    def configure(self,columns):
        pass
    def configuration(self):
        pass
    def commit(self):
        pass
    def get_column_position(self,column):
        pass
    def get_column_names(self,extended=0):
        pass
    def get_column_name(self,position):
        pass
    def get_columns(self,extended=0):
        pass
    def add_entry(self,values):
        pass
    def get_range_values(self,column,start,end,extended=0):
        pass
    def get_range(self,column,start,end,extended=0):
        pass
    def get_slice_values(self,column,start,end,extended=0):
        pass
    def get_slice(self,column,start,end,extended=0):
        pass
    def get_first_record(self):
        pass
    def get_last_record(self):
        pass
    def __getslice__(self,start,end):
        pass
    def __getitem__(self,index):
        pass
    def __len__(self):
        pass
    def trim_lt(self,column,value):
        pass
    def trim_le(self,column,value):
        pass
    def trim_gt(self,column,value):
        pass
    def trim_ge(self,column,value):
        pass
    def reset(self):
        pass
    def destroy(self):
        pass

##
# Type Conversion data and functions.
#
_types = {'char':EnumeratedValue(0,'c'),
          'char':EnumeratedValue(1,'b'),
          'unsigned_char':EnumeratedValue(2,'B'),
          'short':EnumeratedValue(3,'h'),
          'unsgined_short':EnumeratedValue(4,'H'),
          'int':EnumeratedValue(5,'i'),
          'unsigned_int':EnumeratedValue(6,'I'),
          'long':EnumeratedValue(7,'l'),
          'unsigned_long':EnumeratedValue(8,'L'),
          'float':EnumeratedValue(9,'f'),
          'double':EnumeratedValue(10,'d')}
def _to_type_value(name):
    return _types[name]
def _to_type_format(name):
    return str(_to_type_value(name))
def _to_type_name(value):
    for name,enum in _types.items():
        if enum == value:
            return name
    raise KeyError()
def _to_type_names(values):
    names = []
    for value in values:
        names.append(_to_type_name(value))
    return names
##
# Log and version related functions.
#
FixedLengthLogObject = _FixedLengthLogObject_0
def _prior_version_exists(name,path):
    return _log.version_exists(name,path)
def _current_version_exists(name,path):
    if os.path.exists(os.path.join(path,name) + '.bin.0'):
        return 1
    return 0
def version_exists(name,path):
    if (_current_version_exists(name,path) or 
        _prior_version_exists(name,path)):
        return 1
    return 0
