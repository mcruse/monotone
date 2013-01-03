"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import array
import errno
import re
from signal import SIGHUP
from shutil import copyfile
from tools.lib import os, CommandKeywords
from moab.linux.lib.devicemgr import LockFile
from mpx import properties
from mpx.lib.exceptions import EIOError

class EResourceInUse( EIOError ):
    def __init__( self, resName, pid ):
        self.resName = resName
        self.in_use_by_pid = pid

#
# servivemgr.py
#
# Classes to manage system services.
#

##
#  
class _Attribute:
    def __init__(self, name):
        self._value = ""
        self._name = str(name).strip() 
        return
    def __nonzero__(self):
        return self._value != ""
    ##
    # @return The attributes name.
    def name(self):
        return self._name
    ##
    # Setter/getter for an attribute.
    # If no <code>value</code> is provided, then return the
    # values current value.  Otherwise, update the attribute's value
    # and return the previous stored value.
    # @return The string value stored in this attribute.
    def value(self, value=None):
        result = self._value
        if value is not None:
            self._value = str(value).strip()
        return result

class _ItemIter:
    def __init__(self,collection):
        self._collection = collection
        self._keys = range(0,len(collection))
        return
    def __iter__(self):
        return self
    def next(self):
        while len(self._keys):
            result = self._collection[self._keys.pop()]
            if result:
                return result
        raise StopIteration

class _AttrIter(_ItemIter):
    def __init__(self,collection):
        _ItemIter.__init__(self,collection)
        self._keys = collection.keys()
        return

class _SetIter(_AttrIter):
    pass

class _Set:
    def __init__(self, name):
        self._items = []
        self._name = name
        self._attrs = {}
        self._subsets = {}
        return
    def __nonzero__(self):
        for item in self._items:
            if item:
                return 1
        for attr in self._attrs:
            if attr:
                return 1
        for subset in self._subsets:
            if subset:
                return 1
        return 0
    def name(self):
        return self._name
    
    def items(self):
        return _ItemIter(self._items)
    
    def attributes(self):
        return _AttrIter(self._attrs)
    
    def sets(self):
        return _SetIter(self._subsets)
    
    ##
    # @return The ServiceGroup set known as <code>name</code>.  If the set
    #         does not exist, an empty set is created for future refernce.
    # @note The name is forced to a string and stripped of leading
    #       and trailing whitespace.
    # @note Empty sets never persist.
    def subset(self,name):
        if not self._subsets.has_key(name):
            self._subsets[name] = _Set(name)
        return self._subsets[name]
    ##
    # @return The ServiceGroup attribute known as <code>name</code>.  If the
    #         attribute does not exist, it is created with the value of an
    #         empty string.
    # @note The name is forced to a string and stripped of leading
    #       and trailing whitespace.
    def attribute(self,name):
        if not self._attrs.has_key(name):
            self._attrs[name] = _Attribute(name)
        return self._attrs[name]
    ##
    # @return The number of items in the group.
    def num_items(self):
        return len(self._items)
    ##
    # @return True if the set includes the string <code>item</code>.
    # @note <code>item</value> is forced to a string and then
    #       stripped of leading and trailing whitespace.
    def has_item(self, item):
        item = str(item).strip()
        if item in self._items:
            return 1
        return 0
    ##
    # Add the string item to the set.
    # @note <code>item</value> is forced to a string and then
    #       stripped of leading and trailing whitespace.
    def add_item(self, item):
        item = str(item).strip()
        if item not in self._items:
            self._items.append(item)
        return
    ##
    # Remove the string item from the set.
    # @note <code>item</value> is forced to a string and then
    #       stripped of leading and trailing whitespace.
    def remove_item(self, item):
        if item in self._items:
            self._items.remove(item)
        return

##
# Base class for a service group.  Very minimal for the time being -- in the
# future should add dependency information.
#
class ServiceGroup(_Set):
    def __init__(self, name=""):
        _Set.__init__(self, name)
        return
    
    def enable_daemon(self, daemon, enable=1):
        assert 0, "Unimplemented abstract method"
        return
    
    def disable_daemon(self, daemon, enable=0):
        assert 0, "Unimplemented abstract method"
        return

##
# Base class for manipulating a set of service groups.
# <p>
# Standard sets:
# <dl>
# <dt>REQUIRED_BY</dt>
# <dd>A node that requires the service enabled will add an item that is the
#     internal URL to the node (e.g. "/services/network/webdev").</dd>
# </dl>
class ServiceManager:
    def __init__(self, **keywords):
        self.cmd_keywords = CommandKeywords(self.__class__.__name__, keywords)
        self.group_list = []
    ##
    # Add group to the list of ServiceManager groups.
    def addgroup(self, group):
        self.group_list.append(group)
    ##
    # Remove all groups with the given <code>name</code>.
    # @param name The name of the group(s) to delete.
    # @returns the number of groups removed.
    def remgroup(self, name):
        count = 0
        for g in self.group_list:
            if g.name() == name:
                i = self.group_list.index(g)
                del self.group_list[i]
                count += 1
        return count
    
    def findgroup(self, name):
        for g in self.group_list:
            if g.name() == name:
                return g
        return None
    
    def getgroups(self):
        return self.group_list
    
    def __getitem__(self, group_name):
        group = self.findgroup(group_name)
        if group is None:
            raise KeyError, group_name
        return group
    
    def has_key(self, group_name):
        return None != self.findgroup(group_name)
    
    def commit(self):
        assert 0, "Unimplemented abstract method"
        return

##
# Class representing a group of Linux services.
# @fixme deprecate InittabGroup.text and replace with line oriented logic.
class InittabGroup(ServiceGroup):
    # Initialize a group from text.
    TAG_SEP=":"		# Separates a tag from its name.
    ATTRIBUTE_SEP="="   # Seperates a name from it's value.
    BEGIN_GROUP_TAG="#>>>BEGIN"		# Identifies the start of a group.
    END_GROUP_TAG="#>>>END"		# Identifies the end of a group.
    GROUP_ATTRIBUTE_TAG="#___ATTR"	# Sets an attribute on a group.
    GROUP_ATTRIBUTE_SET_ITEM="[]"	# Identifies an item in a set.
    ENTRY_DISABLED_TAG="#___OFF_"	# Comment used to disable a service
                                            # in a group.
    # "#>>>BEGIN:tag_name"
    _BEGIN_PATTERN = re.compile("^\\s*(%s)%s(.*)\\s*$" %
                                (re.escape(BEGIN_GROUP_TAG),
                                 re.escape(TAG_SEP))
                                )
    # "#>>>END:tag_name"
    _END_PATTERN = re.compile("^\\s*(%s)%s(.*)\\s*$" %
                              (re.escape(END_GROUP_TAG),
                               re.escape(TAG_SEP))
                              )
    # "#___ATTR:attribute_name\\=value"
    _ATTR_PATTERN = re.compile("^\\s*(%s)%s([^%s]+)%s(.*)\\s*$" % (
        re.escape(GROUP_ATTRIBUTE_TAG), re.escape(TAG_SEP),
        re.escape(ATTRIBUTE_SEP), re.escape(ATTRIBUTE_SEP)))
    # "#___ATTR:attribute_name\\[\\]\\=value"
    _ATTR_ITEM_PATTERN = re.compile("^\\s*(%s)%s([^%s%s]+)%s%s(.*)\\s*$" % (
        re.escape(GROUP_ATTRIBUTE_TAG), re.escape(TAG_SEP),
        re.escape(GROUP_ATTRIBUTE_SET_ITEM), re.escape(ATTRIBUTE_SEP),
        re.escape(GROUP_ATTRIBUTE_SET_ITEM), re.escape(ATTRIBUTE_SEP)))
    
    def __init__(self, name = None, text = ''):
        ServiceGroup.__init__(self, name)
        self.text = text
        return
    
    def _append_begin(self, a):
        name = self.name()
        if name:
            a.fromstring(self.BEGIN_GROUP_TAG)
            a.fromstring(self.TAG_SEP)
            a.fromstring(name)
            a.fromstring('\n')
        return
    
    def _append_attributes(self, a):
        for attr in self.attributes():
            a.fromstring(self.GROUP_ATTRIBUTE_TAG)
            a.fromstring(self.TAG_SEP)
            a.fromstring(attr.name())
            a.fromstring(self.ATTRIBUTE_SEP)
            a.fromstring(attr.value())
            a.fromstring('\n')
        return
    
    def _append_sets(self, a):
        for set in self.sets():
            for item in set.items():
                a.fromstring(self.GROUP_ATTRIBUTE_TAG)
                a.fromstring(self.TAG_SEP)
                a.fromstring(set.name())
                a.fromstring(self.GROUP_ATTRIBUTE_SET_ITEM)
                a.fromstring(self.ATTRIBUTE_SEP)
                a.fromstring(item)
                a.fromstring('\n')
        return
    
    def _append_text(self,a):
        last_line = None
        for line in self.text.split('\n'):
            line = line.strip()
            if not self.name():
                # Remove duplicate lines (there either blank, a repeated
                # and therefore useless entry, or a duplicated and therefore
                # unecesarily wordy comment).
                if line == last_line:
                    # Skip repitition.
                    continue
            else:
                if not line:
                    # In named groups, blank lines are useless.
                    continue
            last_line = line
            a.fromstring(line)
            a.fromstring('\n')
        return
    
    def _append_end(self, a):
        name = self.name()
        if name:
            a.fromstring(self.END_GROUP_TAG)
            a.fromstring(self.TAG_SEP)
            a.fromstring(name)
            a.fromstring('\n')
        return
    
    def __str__(self):
        a = array.array('c')
        self._append_begin(a)
        self._append_attributes(a)
        self._append_sets(a)
        self._append_text(a)
        self._append_end(a)
        return a.tostring()
    ##
    # Load one group from a file.  Parsing is very crude, in that there
    # is no checking for matching begin-end tags, or nesting of groups.
    # Text not delimited by begin-end tags is put into an unnamed group.
    # An unnuamed group is terminated by EOF or the
    # start of a named group.
    def load(self, file):
        self.text = ''
        while 1:
            # Get a line.
            pos = file.tell()
            line = file.readline()
            if not line:
                # EOF
                return
            if self._new_begin(line):
                # End of an anonymous group.
                file.seek(pos)
                return
            if self._first_begin(line):
                continue
            if self._match_end(line):
                # End of a named group.
                return
            if self._match_item(line):
                continue
            if self._match_attr(line):
                continue
            # Add line to text buffer.
            self.text += line
        return
    
    def _new_begin(self, line):
        match = self._BEGIN_PATTERN.match(line)
        if match is None:
            return 0
        tag, name = match.groups()
        if not self._name:
            if self.text:
                # Found BEGIN tag while processing an unnamed group.
                # Restore file position to the previous line and stop
                # processing.
                return 1
        else:
            # Found BEGIN tag while processing a another group.
            raise SyntaxError, "Nested begin"
        return 0
    
    def _first_begin(self, line):
        match = self._BEGIN_PATTERN.match(line)
        if match is None:
            return 0
        tag, name = match.groups()
        if self._name:
            assert 0, "_new_begin should have prevented this."
        else:
            if not self.text:
                # Found BEGIN tag to a virgin group.
                self._name = name
                return 1
            else:
                assert 0, "_new_begin should have prevented this."
        return 0
    
    def _match_end(self, line):
        match = self._END_PATTERN.match(line)
        if match is None:
            return 0
        tag, name = match.groups()
        if self.name() != name:
            raise SyntaxError("Found END of %r while in group %r." %
                              (name, self.name()))
        return 1
    
    def _match_attr(self, line):
        match = self._ATTR_PATTERN.match(line)
        if match is None:
            return 0
        tag, name, value = match.groups()
        self.attribute(name).value(value)
        return 1
    
    def _match_item(self, line):
        match = self._ATTR_ITEM_PATTERN.match(line)
        if match is None:
            return 0
        tag, name, item = match.groups()
        self.subset(name).add_item(item)
        return 1
    
    def _disabled_tag_daemon(self, daemon):
        return re.compile("^(%s%s|)(%s.*)$" %
                          (self.ENTRY_DISABLED_TAG, self.TAG_SEP, daemon))

    def _find_daemon_line(self, daemon):
        pattern = self._disabled_tag_daemon(daemon)
        for line in self.text.split('\n'):
            match = pattern.match(line)
            if match:
                return line
        # If we didn't find the line, signal failure by returning None
        return None
    
    def is_daemon_enabled(self, daemon):
        line = self._find_daemon_line(daemon)
        if line:
            strind = line.find(self.ENTRY_DISABLED_TAG)
            if strind != -1:
                return 0
            # Just for the heck of it, check for a comment as the first char
            if line[0] == '#':
                return 0
            return 1
        # If we didn't find the line, then it can't be enabled
        return 0

    def get_daemon_entry(self, daemon):
        line = self._find_daemon_line(daemon)
        if not line:
            return None
        strrind = line.rfind(self.TAG_SEP)
        if strrind == -1:
            raise SyntaxError("Could not parse %s." % line)
        return line[strrind+1:]
    
    def enable_daemon(self, daemon, enable=1):
        count = 0
        new_text = ''
        pattern = self._disabled_tag_daemon(daemon)
        for line in self.text.split('\n'):
            match = pattern.match(line)
            if match:
                count += 1
                tag, entry = match.groups()
                if enable and tag:
                    # Enable (uncomment) a disabled (commented) line.
                    line = entry
                elif not enable and not tag:
                    # Disable (comment) an enabled (uncommented) line.
                    line = "%s%s%s" % (self.ENTRY_DISABLED_TAG,
                                       self.TAG_SEP, line)
            if new_text:
                new_text = "%s\n%s" % (new_text,line)
            else:
                new_text = line
        self.text = new_text
        assert count == 1, (
            "%s found %s times.  Exactly once is correct." % (daemon, count)
            )
        return

    def disable_daemon(self, daemon, enable=0):
        self.enable_daemon(daemon, enable)
        return

    def __nonzero__(self):
        return ServiceGroup.__nonzero__(self) or (len(self.text) != 0)

    ##
    # Delete all lines that match the supplied <code>pattern</code>.
    def delete_matching_lines(self, pattern):
        pattern = re.compile(pattern)
        new_text = ''
        for line in self.text.split('\n'):
            if pattern.match(line):
                continue
            if new_text:
                new_text = "%s\n%s" % (new_text,line)
            else:
                new_text = line
        self.text = new_text
        return

    def isEmpty(self):
        from mpx.lib import deprecated
        deprecated("Use standard Python comparison.")
        return not self.__nonzero__()

##
# Class for manipulating the Linux inittab file.
##
class InittabManager(ServiceManager):
    def __init__(self, fileName = properties.INITTAB_FILE, **keywords):
        ServiceManager.__init__(self, **keywords)
        self.fileName = fileName
        self.lock = LockFile( fileName + '..LCK' )
        pid = self.lock.acquire()
        if pid:
            raise EResourceInUse( fileName, pid )
        self._load()
        return
    
    def __del__(self):
        self.lock.release()

    def _load(self):
        try:
            file = open(self.fileName, 'r')
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise
            file = open('/dev/null', 'r')
        try:
            while 1:
                g = InittabGroup()
                g.load(file)
                # Empty group indicates EOF.
                if not g:
                    break
                self.addgroup(g)
        finally:
            file.close()
        return

    def commit(self):
        if self.cmd_keywords.test:
            self.cmd_keywords.test_message("TEST: cat >%s <<EOF", self.fileName)
            for g in self.group_list:
                for line in str(g).split('\n'):
                    self.cmd_keywords.test_message("TEST: %s", line)
            self.cmd_keywords.test_message("TEST: EOF")
        else:
            tmpFileName = self.fileName + '.tmp'
            file = open(tmpFileName, 'w')
            isOK = 0
            try:
                for g in self.group_list:
                    file.write(str(g))
                isOK = 1
            finally:
                file.close()
                if isOK:
                    if os.path.exists(self.fileName):
                        copyfile( self.fileName, self.fileName + '.bak' )                    
                    os.rename( tmpFileName, self.fileName )
                if os.getuid() == 0:
                    os.kill(1, SIGHUP)
                else:
                    # We're not root, presumably this is a test.
                    import warnings
                    warnings.warn("init process not signaled.")
    ##
    # Delete all lines that match the supplied <code>pattern</code>.
    def delete_matching_lines(self, pattern):
        pattern = re.compile(pattern)
        for g in self.group_list:
            new_text = ''
            for line in g.text.split('\n'):
                g.delete_matching_lines(pattern)
        return

