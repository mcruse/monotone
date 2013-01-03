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
# @fixme Move _create_* into classes, somehow...

import re
import array
import types

from tools.clu import CommandLineUtility, SubCommand
from tools.clu import EArgument, EInput, ECommand

class _Statement:
    def __init__(self, statement):
        self._statement = statement.strip()
        return
    def __str__(self):
        return self._statement
    def __cmp__(self, other):
        return cmp(str(self), str(other))

class _Grant(_Statement):
    ##
    # \1 = Statement
    GRANT = re.compile("^\s*(GRANT\s+.*)\s*$",
                       re.IGNORECASE)

class _Alias(_Statement):
    ##
    # \1 = Statement
    ALIAS = re.compile("^\s*(CREATE\s+ALIAS\s+.*)\s*$",
                       re.IGNORECASE)

class _User(_Statement):
    ##
    # \1 = Statement
    USER = re.compile("^\s*(CREATE\s+USER\s+.*)\s*$",
                      re.IGNORECASE)

class _Connect(_Statement):
    ##
    # \1 = Statement
    CONNECT = re.compile("^(.*CONNECT\s+USER\s+.*)\s*$",
                         re.IGNORECASE)

class _Index:
    ##
    # \1 = Index Name
    # \2 = Table Name
    # \3 = Column Names
    CREATE_INDEX = re.compile(
        "^\s*CREATE\s+INDEX\s+(\S*)\s+"
        "ON\s+(\S+)\(\s*([^\s\)]+\s*)\)\s*$",
        re.IGNORECASE)
    def name(self):
        return self._name
    def table_name(self):
        return self._table_name
    def column_names(self):
        return self._column_names
    def _column_names_str(self):
        names = []
        names.extend(self.column_names())
        result = "(%s" % (names.pop(0),)
        while names:
            result = "%s,%s" % (result,names.pop(0))
        result = "%s)" % (result,)
        return result
    _STR_FMT = "CREATE INDEX %s ON %s%s"
    def __str__(self):
        return self._STR_FMT % (self.name(), self.table_name(),
                                self._column_names_str())
    def __init__(self, index_name, table_name, column_names):
        self._name = index_name.upper()
        self._table_name = table_name.upper()
        self._column_names = []
        column_names = column_names.upper()
        column_names = column_names.split(',')
        for n in column_names:
            self._column_names.append(n.strip())
        self._column_names = tuple(self._column_names)
        self._hash = {}
        self.__unique = 0
        return
    def key_for(self, row):
        key = []
        for n in self._column_names:
            key.append(row.value(n))
        key = tuple(key)
        return key
    def __bucket(self, row):
        key = self.key_for(row)
        row._indexed_by(self)
        if self._hash.has_key(key):
            if self.__unique:
                assert row not in self._hash[key], (
                    "%r already in table." % str(row)
                    )
        else:
            self._hash[key] = []
        return self._hash[key]
    def index(self, row):
        self.__bucket(row).append(row)
        return
    def unindex(self, row):
        self.__bucket(row).remove(row)
        return

class _UniqueIndex(_Index):
    ##
    # \1 = Index Name
    # \2 = Table Name
    # \3 = Column Names
    CREATE_UNIQUE_INDEX = re.compile(
        "^\s*CREATE\s+UNIQUE\s+INDEX\s+(\S*)\s+"
        "ON\s+(\S+)\(\s*([^\s\)]+\s*)\)\s*$",
        re.IGNORECASE)
    _STR_FMT = "CREATE UNIQUE INDEX %s ON %s%s"
    def __init__(self, *args):
        _Index.__init__(self, *args)
        self.__unique = 1
        return

class _Table:
    ##
    # \1 = Table Name
    # \2 = Column Definitions
    CREATE_TABLE = re.compile(
        "^\s*CREATE\s+TABLE\s*(\S+)\s*\(\s*(.*)\)\s*$",
        re.IGNORECASE)
    UNIQUE_COLUMN = re.compile("^\s*UNIQUE\((.*)\)\s*$")
    def name(self):
        return self._name
    def __init__(self, name, column_defs, repository):
        self._name = name
        self._column_defs = {}
        self._repository = repository
        self._rows = []
        self._rows_sorted = 0
        column_defs = column_defs.upper()
        column_defs = column_defs.split(',')
        self._column_tuple = None
        self._indexes = {}
        i = 0
        for d in column_defs:
            d = d.strip().split()
            match = self.UNIQUE_COLUMN.match(d[0])
            if match:
                name = match.groups()[0]
                key, value = 'UNIQUE', 1
                index = -1
                # Add the implicit, UNIQUE INDEX.
                self.create_index(_UniqueIndex(name, self._name, name))
            else:
                name = d[0]
                key, value = 'type', d[1]
                index = i
                i += 1
            if self._column_defs.has_key(name):
                column_def = self._column_defs[name]
            else:
                column_def = {}
            column_def[key] = value
            if index != -1:
                column_def['index'] = index
            self._column_defs[name] = column_def
        return
    def insert(self, row):
        self._rows.append(row)
        self._rows_sorted = 0
        for index in self._indexes.values():
            index.index(row)
        return
    def delete(self, row):
        self._rows.remove(row)
        self._rows_sorted = 0
        for index in self._indexes.values():
            index.unindex(row)
    def rows(self):
        if not self._rows_sorted:
            self._rows.sort()
            self._rows_sorted = 1
        rows = []
        rows.extend(self._rows)
        return rows
    def unique_rows(self):
        rows = self.rows()
        unique_rows = []
        if rows:
            unique_rows.append(rows.pop(0))
        for row in rows:
            if rows[-1] != row:
                unique_rows.append(row)
        return unique_rows
    def column_count(self):
        return len(self._column_defs)
    ##
    # @return the column position of a column identified by name.
    def column_position(self, name):
        return self._column_defs[name]['index']
    ##
    # @return An array of the table's column definitions, indexed by the
    #         columns position.
    def column_definitions(self):
        if self._column_tuple is None:
            self._column_tuple = []
            for name, value in self._column_defs.items():
                cdef = {}
                cdef.update(value)
                cdef['name'] = name
                self._column_tuple.append(cdef)
            def _cmp_(c1, c2):
                return cmp(c1['index'],c2['index'])
            self._column_tuple.sort(_cmp_)
            self._column_tuple = tuple(self._column_tuple)
        result = []
        result.extend(self._column_tuple)
        return result
    def _column_definitions_str(self):
        special=[]
        defs = self.column_definitions()
        cdef = defs.pop(0)
        if cdef.has_key('UNIQUE') and cdef['UNIQUE']:
            special.append("UNIQUE(%s)" % cdef['name'])
        result = "(%s %s" % (cdef['name'],cdef['type'],)
        while defs:
            cdef = defs.pop(0)
            if cdef.has_key('UNIQUE') and cdef['UNIQUE']:
                special.append("UNIQUE(%s)" % cdef['name'])
            result = "%s,%s %s" % (result,cdef['name'],cdef['type'])
        special.sort()
        while special:
            cspecial = special.pop(0)
            result = "%s,%s" % (result,cspecial)
        result = "%s)" % (result,)
        return result
    def has_index(self, name):
        return self._indexes.has_key(name)
    def create_index(self, index):
        if self._indexes.has_key(index.name()):
            raise Exception(
                'ndchk create index %s on %s: Index already exists.' %
                name, self.name())
        self._indexes[index.name()] = index
        return
    def definition_as_array(self):
        buffer = array.array('c')
        buffer.fromstring("CREATE TABLE %s%s" %
                          (self.name(), self._column_definitions_str(),)
                          )
        names = self._indexes.keys()
        names.sort()
        for name in names:
            i = self._indexes[name]
            buffer.fromstring('\n')
            buffer.fromstring(str(i))
        return buffer
    def dump_definition(self):
        return self.definition_as_array().tostring()
    def rows_as_array(self):
        buffer = array.array('c')
        rows = self.rows()
        if rows:
            c = rows.pop(0)
            buffer.fromstring(str(c))
        for c in rows:
            buffer.fromstring('\n')
            buffer.fromstring(str(c))
        return buffer
    def dump_rows(self):
        return self.rows_as_array().tostring()
    def unique_rows_as_array(self):
        buffer = array.array('c')
        rows = self.unique_rows()
        if rows:
            c = rows.pop(0)
            buffer.fromstring(str(c))
        for c in rows:
            buffer.fromstring('\n')
            buffer.fromstring(str(c))
        return buffer
    def dump_unique_rows(self):
        return self.unique_rows_as_array().tostring()
    def as_array(self):
        buffer = self.definition_as_array()
        if self._rows:
            buffer.fromstring('\n')
            buffer.extend(self.rows_as_array())
        return buffer
    def dump(self):
        return self.as_array().tostring()
    def unique_as_array(self):
        buffer = self.definition_as_array()
        if self._rows:
            buffer.fromstring('\n')
            buffer.extend(self.unique_rows_as_array())
        return buffer
    def dump_unique(self):
        return self.as_array().tostring()
    def __str__(self):
        return ("CREATE TABLE %s%s" % (self.name(),
                                       self._column_definitions_str(),))
    def __cmp__(self, other):
        return cmp(str(self), str(other))

class _Row:
    ##
    # \1 = Table
    # \2 = Values
    INSERT_INTO = re.compile(
        "^\s*INSERT\s+INTO\s+([^\s]+)\s+VALUES\s*\((.*)\)\s*$"
        )
    def __init__(self, table, values):
        self._table = table
        self._values = self.__split(values)
        self._indexes = []
        return
    def _indexed_by(self, index):
        assert index not in self._indexes
        self._indexes.append(index)
        return
    def __split(self, values):
        temp = values.split(',')
        if len(temp) == self._table.column_count():
            result = []
            for v in temp:
                result.append(v.strip())
            return result
        save = []
        save.extend(temp)
        if len(temp) > self._table.column_count():
            # OK, some string(s) had a comma in it.  Find them, and combine
            # them.
            result = [temp.pop(0)]
            while temp:
                value = result[-1]
                strip = value.strip()
                if strip[0] == "'" and (strip[-1] != "'" or len(strip) == 1):
                    result[-1] = "%s,%s" % (value, temp.pop(0))
                    continue
                result.append(temp.pop(0))
            if len(result) == self._table.column_count():
                return result
        else:
            # For assertion...
            result = []
        assert 1, (
            40*"*" + "\n" +
            "NEED A BETTER EXCEPTION CASE PARSER FOR SPLITTING OUT VALUES\n" +
            ("FAILED PARSING: %r\n" % values) +
            ("SIMPLE SPLIT:   %r\n" % save) +
            ("RECOMBINED AS:  %r\n" % result) +
            40*"*" + "\n"
            )
        return
    ##
    # @param name The name or positional index of a column.
    def value(self, name):
        if type(name) in types.StringTypes:
            return self._values[self._table.column_position(name)]
        return self._values[name]
    ##
    # @return a list of the column's values.
    def values(self):
        result = []
        result.extend(self._values)
        return result
    def table_name(self):
        return self._table.name()
    def __str(self):
        text = ""
        for i in range(0,len(self._values)-1):
            text = "%s%s," % (text, self._values[i])
        if self._values:
            text = "%s%s" % (text, self._values[-1])
        return text
    def __str__(self):
        return "INSERT INTO %s VALUES(%s)" % (self._table.name(), self.__str())
    def __cmp__(self, other):
        v1 = self.values()
        v2 = other.values()
        return cmp(v1,v2)

class EUnknownStatement(EInput):
    def __fileinfo(self):
        if self._filename and self._lineno:
            return "%r:%d" % (self._filename, self._lineno)
        elif self._filename:
            return "%r" % (self._filename)
        elif self._lineno:
            return "line %s" % (self._lineno)
        return ''
    def __str__(self):
        return self.__str()
    def __str(self):
        fileinfo = self.__fileinfo()
        text = ''
        if self._statement:
            text = self._statement
            if fileinfo:
                text = "%s (%s)" % (text, fileinfo)
        else:
            text = fileinfo
        return text
    def __init__(self, statement=None, filename=None, lineno=None):
        self._statement = statement
        self._filename = filename
        self._lineno = lineno
        EInput.__init__(self, self.__str())
        return

class EDatabase(ECommand):
    pass

class EInvalidDatabase(EDatabase):
    pass

class EDatabaseInUse(EDatabase):
    pass

class _Database:
    def __init__(self, filename):
        self._filename = filename
        self._tables = {}
        self._grants = []
        self._aliases = []
        self._users = []
        self._connections = []
        self._lineno = 1
        return
    ##
    # @return A list of all the names of tables defined in this databse.
    def table_names(self):
        return self._tables.keys()
    def table(self, name):
        return self._tables[name]
    def definitions_as_array(self):
        buffer = array.array('c')
        tables = self._tables.keys()
        tables.sort()
        for table_name in tables:
            if table_name is not tables[0]:
                buffer.fromstring('\n')
            table = self._tables[table_name]
            buffer.extend(table.definition_as_array())
        return buffer
    def dump_definitions(self):
        return self.definitions_as_array().tostring()
    def rows_as_array(self):
        buffer = array.array('c')
        tables = self._tables.keys()
        tables.sort()
        for table_name in tables:
            if table_name is not tables[0]:
                buffer.fromstring('\n')
            table = self._tables[table_name]
            buffer.extend(table.rows_as_array())
        return buffer
    def dump_rows(self):
        return self.rows_as_array().tostring()
    def unique_rows_as_array(self):
        buffer = array.array('c')
        tables = self._tables.keys()
        tables.sort()
        for table_name in tables:
            if table_name is not tables[0]:
                buffer.fromstring('\n')
            table = self._tables[table_name]
            buffer.extend(table.unique_rows_as_array())
        return buffer
    def dump_unique_rows(self):
        return self.unique_rows_as_array().tostring()
    def as_array(self):
        buffer = self.definitions_as_array()
        buffer.fromstring('\n')
        buffer.extend(self.rows_as_array())
        for g in self._grants:
            buffer.fromstring('\n')
            buffer.fromstring(str(g))
        for u in self._users:
            buffer.fromstring('\n')
            buffer.fromstring(str(u))
        for a in self._aliases:
            buffer.fromstring('\n')
            buffer.fromstring(str(a))
        for c in self._connections:
            buffer.fromstring('\n')
            buffer.fromstring(str(c))
        return buffer
    def dump(self):
        return self.as_array().tostring()
    def unique_as_array(self):
        buffer = self.definitions_as_array()
        buffer.fromstring('\n')
        buffer.extend(self.unique_rows_as_array())
        for g in self._grants:
            buffer.fromstring('\n')
            buffer.fromstring(str(g))
        for u in self._users:
            buffer.fromstring('\n')
            buffer.fromstring(str(u))
        for a in self._aliases:
            buffer.fromstring('\n')
            buffer.fromstring(str(a))
        for c in self._connections:
            buffer.fromstring('\n')
            buffer.fromstring(str(c))
        return buffer
    def dump_unique(self):
        return self.unique_as_array().tostring()
    def __str__(self):
        return self.filename()
    def filename(self):
        return self._filename
    def load_script_file(self, filename, force=0):
        if not force:
            modified = -1
            iext = filename.rfind('.')
            if iext >= 0:
                properties = filename[0:iext]
            else:
                properties = filename
            properties += '.properties'
            try:
                f = open(properties, 'r')
            except IOError, e:
                raise EInvalidDatabase("Could not open %r." % properties)
            try:
                for line in f.xreadlines():
                    result = line.split('=')
                    kw=result[0].strip().lower()
                    if kw == 'modified':
                        if result[1].strip().lower() == 'no':
                            modified = 0
                        else:
                            modified = 1
                        break
                if modified:
                    if modified < 0:
                        raise EInvalidDatabase(
                            ("%r is not a valid database property file."
                             " No 'modified=' keyword.") %
                            properties)
                    else:
                        raise EDatabaseInUse(
                            ("%r is in use, please exit the"
                             " configuration tool.  If the configuration tool"
                             " is not running, then launch the configuration"
                             " tool, open these NodeDefs, view a NodeDef"
                             " via 'Right Click->System->Edit NodeDef' and"
                             " then exit the configuration tool.") % filename)
            finally:
                f.close()
        f = open(filename, 'r')
        try:
            self.__init__(filename)
            for line in f.xreadlines():
                self.parse_line(line)
        finally:
            f.close()
        return self
    def parse_line(self, line, lineno=None):
        if lineno is None:
            lineno = self._lineno
            self._lineno += 1
        result = _Row.INSERT_INTO.match(line)
        if result:
            self._insert_into(result)
            return
        result = _Table.CREATE_TABLE.match(line)
        if result:
            self._create_table(result)
            return
        result = _UniqueIndex.CREATE_UNIQUE_INDEX.match(line)
        if result:
            self._create_unique_index(result)
            return
        result = _Index.CREATE_INDEX.match(line)
        if result:
            self._create_index(result)
            return
        result = _Grant.GRANT.match(line)
        if result:
            self._grant(result)
            return
        result = _Alias.ALIAS.match(line)
        if result:
            self._alias(result)
            return
        result = _User.USER.match(line)
        if result:
            self._user(result)
            return
        result = _User.USER.match(line)
        if result:
            self._user(result)
            return
        result = _Connect.CONNECT.match(line)
        if result:
            self._connect(result)
            return
        raise EUnknownStatement(line.strip(),
                                filename=self.filename(),
                                lineno=lineno)
    def _create_table(self, match):
        groups = match.groups()
        table_name = groups[0].strip().upper()
        column_defs = groups[1]
        if self._tables.has_key(table_name):
            raise Exception('ndchk create table %s: Tabled already exists.' %
                            table_name)
        self._tables[table_name] = _Table(table_name, column_defs,
                                          self._tables)
        return
    def _insert_into(self, match):
        groups = match.groups()
        table_name = groups[0].strip().upper()
        values = groups[1]
        row = _Row(self._tables[table_name], values)
        if not self._tables.has_key(row.table_name()):
            raise Exception('ndchk insert into %s: Tabled does not exist.' %
                            row.table_name())
        self._tables[row.table_name()].insert(row)
        return
    def _create_index(self, match,_index_factory=_Index):
        groups = match.groups()
        index_name = groups[0]
        table_name = groups[1]
        column_names = groups[2]
        if not self._tables.has_key(table_name):
            raise Exception(
                'ndchk create index %s on %s: Table does not exists.' %
                index_name, table_name)
        table = self._tables[table_name]
        table.create_index(_index_factory(index_name, table_name,
                                          column_names))
        return
    def _create_unique_index(self, match):
        self._create_index(match,_UniqueIndex)
        return
    def _grant(self, match):
        self._grants.append(_Grant(match.groups()[0]))
        self._grants.sort()
        return
    def _alias(self, match):
        self._aliases.append(_Alias(match.groups()[0]))
        self._aliases.sort()
        return
    def _user(self, match):
        self._users.append(_User(match.groups()[0]))
        self._users.sort()
        return
    def _connect(self, match):
        self._connections.append(_Connect(match.groups()[0]))
        self._connections.sort()
        return

class Dump(SubCommand):
    def _definitions_only_handler(self, *args):
        self._definitions_only = 1
        return
    def _unique_only_handler(self, *args):
        self._unique_only = 1
        return
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        self._definitions_only = 0
        self._unique_only = 0
        self.register_option('--definitions-only',
                             self._definitions_only_handler,
                             "Only output the table definitions, not the"
                             " row data",
                             ['-d'])
        self.register_option('--unique',
                             self._unique_only_handler,
                             "Only output unique rows.",
                             ['-u'])
        return
    def __str__(self):
        return "database-script-file"
    def _load(self):
        filename = self.pop_next()
        if filename is None:
            filename = 'master.script'
        if self.arguments():
            EArgument("Too many arguments.")
        self._database = _Database(filename)
        self._database.load_script_file(
            filename, force=self.registered_command().root()._force
            )
        return
    def _dump_definitions(self):
        self.put_stdout_msg(self._database.dump_definitions())
        return
    def _dump_all(self):
        self.put_stdout_msg(self._database.dump())
        return
    def _dump_unique(self):
        self.put_stdout_msg(self._database.dump_unique())
        return
    def __call__(self, *args):
        self._load()
        if self._definitions_only:
            self._dump_definitions()
        else:
            if self._unique_only:
                self._dump_unique()
            else:
                self._dump_all()
        self.put_stdout_msg('\n')
        return 0

class Diff(SubCommand):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        self._null_eq_empty = 0
        self._dump_mismatched_tables = 0
        self._simple_table_compare = 0
        self.register_option('--null-eq-empty',
                             self._null_eq_empty_handler,
                             "Compare NULL and '' as equal.  This is to"
                             " compensate for inconsistencies in the"
                             " configuration tool when saving values.",
                             ['-n'])
        self.register_option('--boolean-as-numeric',
                             self._boolean_as_numeric_handler,
                             "Compare true as 1 and false as 0.",
                             ['-b'])
        self.register_option('--dump-mismatched-tables',
                             self._dump_mismatched_tables_handler,
                             "Also dump the differences for rows in tables"
                             " that only exist in one of the databases, or"
                             " that have different definitions.  Typically"
                             " these rows are not included in the diff since"
                             " every row in such tables will be different"
                             " (and therefore implicit and quite noisy).",
                             ['-m'])
        self.register_option('--simple-table-compare',
                             self._simple_table_compare__handler,
                             "Disable NodeDef specific analysis of the"
                             " tables.",
                             ['-s'])
        return
    def _simple_table_compare__handler(self, *args):
        self._simple_table_compare = 1
        return
    def _dump_mismatched_tables_handler(self, *args):
        self._dump_mismatched_tables = 1
        return
    def _null_eq_empty_handler(self, *args):
        raise NotImplementedError("--null-eq-empty")
        self._null_eq_empty = 1
        return
    def _boolean_as_numeric_handler(self, *args):
        raise NotImplementedError("--boolean-as-numeric")
        self._null_eq_empty = 1
        return
    def __str__(self):
        return "database1-script-file database2-script-file"
    def _load(self,argument_name):
        filename = self.pop_next()
        if filename is None:
            raise EArgument("Missing required %r argument." % argument_name)
        database = _Database(filename)
        database.load_script_file(
            filename, force=self.registered_command().root()._force
            )
        return database
    ##
    # Report a table as only in one database.
    def _dump_table(self, name, missing):
        if missing:
            prefix = ' <'
            table = self._db1.table(name)
        else:
            prefix = ' >'
            table = self._db2.table(name)
        definition = table.dump_definition().split('\n')
        for line in definition:
            self.put_stdout_msg("%s %s\n", prefix, line)
        return
    ##
    # Report any differences in the definition of A table.
    def _diff_table_definition(self, name):
        table1 = self._db1.table(name)
        table2 = self._db2.table(name)
        def1 = table1.dump_definition().split('\n')
        def2 = table2.dump_definition().split('\n')
        if def1 != def2:
            # Actual table is the first line.
            create1 = def1.pop(0)
            create2 = def2.pop(0)
            if create1 != create2:
                self.put_stdout_msg(" < %s\n", create1)
                self.put_stdout_msg(" > %s\n", create1)
            # Everything left is INDEXES, which are sorted...
            self._diff_simple_sorted_list(def1, def2)
        return
    ##
    # Report differences in the definitions of ALL tables.
    def _diff_tables_definitions(self):
        names1 = self._db1.table_names()
        names2 = self._db2.table_names()
        names1.sort()
        names2.sort()
        i1 = 0
        i2 = 0
        while i1 < len(names1) or i2 < len(names2):
            if i1 >= len(names1):
                self._dump_table(names2[i2], 0)
                i2 += 1
            elif i2 >= len(names2):
                self._dump_table(names1[i1], 1)
                i1 += 1
            elif names1[i1] == names2[i2]:
                self._diff_table_definition(names1[i1])
                i1 += 1
                i2 += 1
            elif names1[i1] < names2[i2]:
                self._dump_table(names1[i1], 1)
                i1 += 1
            else:
                self._dump_table(names2[i2], 0)
                i2 += 1
        return
    def _diff_table_rows(self, name):
        if name not in self._db1.table_names():
            # Add all rows.
            self._diff_simple_sorted_list([], self._db2.table(name).rows())
        elif name not in self._db2.table_names():
            # Remove all rows.
            self._diff_simple_sorted_list(self._db1.table(name).rows(), [])
        else:
            # Preform a row-by-row comparison of the tables.
            if self._simple_table_compare:
                self._diff_simple_sorted_list(self._db1.table(name).rows(),
                                              self._db2.table(name).rows())
            else:
                raise NotImplementedError("not self._simple_table_compare")
    def _diff_tables_rows(self):
        tables1 = self._db1.table_names()
        tables2 = self._db2.table_names()
        if self._dump_mismatched_tables:
            # Dump row differences for the union of tables.
            tables = []
            tables.extend(tables1)
            for name in tables2:
                if name not in tables:
                    tables.append(name)
        else:
            # Dump row differences for the intersection of tables.
            tables = []
            tables.extend(tables1)
            for name in tables1:
                if name not in tables2:
                    tables.remove(name)
        tables.sort()
        for name in tables:
            self._diff_table_rows(name)
        return
    def _diff_simple_sorted_list(self, list1, list2):
        i1 = 0
        i2 = 0
        while i1 < len(list1) or i2 < len(list2):
            if i1 >= len(list1):
                self.put_stdout_msg(" > %s\n", list2[i2])
                i2 += 1
            elif i2 >= len(list2):
                self.put_stdout_msg(" < %s\n", list1[i1])
                i1 += 1
            elif list1[i1] == list2[i2]:
                i1 += 1
                i2 += 1
            elif list1[i1] < list2[i2]:
                self.put_stdout_msg(" < %s\n", list1[i1])
                i1 += 1
            else:
                self.put_stdout_msg(" > %s\n", list2[i2])
                i2 += 1
        return
    def _diff_grants(self):
        self._diff_simple_sorted_list(self._db1._grants, self._db2._grants)
        return
    def _diff_users(self):
        self._diff_simple_sorted_list(self._db1._users, self._db2._users)
        return
    def _diff_aliases(self):
        self._diff_simple_sorted_list(self._db1._aliases, self._db2._aliases)
        return
    def _diff_connections(self):
        self._diff_simple_sorted_list(self._db1._connections,
                                      self._db2._connections)
        return
    def _diff(self):
        self._db1 = self._load("database1-script-file")
        self._db2 = self._load("database2-script-file")
        if self.arguments():
            EArgument("Too many arguments.")
        self._diff_tables_definitions()
        self._diff_tables_rows()
        self._diff_grants()
        self._diff_users()
        self._diff_aliases()
        self._diff_connections()
        return
    def __call__(self, *args):
        self._diff()
        return 0

class Validate(SubCommand):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        return
    def __str__(self):
        return "database-script-file"
    def _load(self):
        filename = self.pop_next()
        if filename is None:
            raise EArgument(
                "Missing required 'database-script-file' argument." %
                argument_name
                )
        database = _Database(filename)
        database.load_script_file(
            filename, force=self.registered_command().root()._force
            )
        
        return
    def __call__(self, *args):
        self._load()
        if self.arguments():
            EArgument("Too many arguments.")
        return 0

class NodeDefCheck(CommandLineUtility):
    HELP = """
ndchk:  Command-line utility to help manage a NodeDefs.
"""
    OVERVIEW = """
"""
    def __init__(self):
        CommandLineUtility.__init__(self, self.HELP)
        self._force = 0
        # register the "ndchk dump" command handler.
        Dump(self, "dump")
        # register the "ndchk diff" command handler.
        Diff(self, "diff")
        # register the "ndchk validate" command handler.
        Validate(self, "validate")
        # register the global force option.
        self.register_option('--force',
                             self._force_handler,
                             "Ignore any sanity checks and force the"
                             " SUB-COMMAND.",
                             ['-f'])
        return
    def _force_handler(self, *args):
        self._force = 1
        return
    def run_command(self, command):
        self.put_stdout_msg(self.HELP)
        self.put_stdout_msg(self.OVERVIEW)
        self.put_stdout_msg("\n")
        self.put_stdout_msg("sub-commands:\n\n")
        keys = self.commands().keys()
        keys.sort()
        for key in keys:
            info = self.commands()[key].help_description()
            self.put_stdout_msg("  %s" % info['name'])
            for alias in info['aliases']:
                self.put_stdout_msg(", %s" % alias)
            self.put_stdout_msg(":\n")
            self.put_stdout_msg("    %s" % info['text'])
            self.put_stdout_msg("\n")
        return 0

if __name__ == '__main__':
    main = NodeDefCheck()
    main()
