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
##
# @todo Add rules for where to add properties.
# @todo Add sections that support extraction, and updating (could become
#       our common template model.
#       <!-- envenergy_file_info/section_open: 'section name here.' -->
#       <!-- envenergy_file_info/section_close: 'section name here.' -->

import re
import os

from mpx.lib import thread

from tools.clu import CommandLineUtility, SubCommand
from tools.clu import EArgument, EOption, EInput, ECommand

class _FileInfoMixin:
    _KNOWN_TYPES = ('html', 'xml', 'js', 'shell', 'ansi-esc', 'auto')
    _KNOWN_TYPES_ENGLISH = " or %r" % _KNOWN_TYPES[-1]
    _known_types = []
    _known_types.extend(_KNOWN_TYPES[:-1])
    _known_types.sort()
    _known_types.reverse()
    for t in _known_types:
        _KNOWN_TYPES_ENGLISH = "%r, %s" % (t, _KNOWN_TYPES_ENGLISH)
    del t
    del _known_types
    def _file_type_handler(self, *args):
        self._file_type = self.pop_next()
        if hasattr(self._file_type, 'lower'):
            self._file_type = self._file_type.lower()
        if self._file_type not in self._KNOWN_TYPES:
            raise EOption("--file-type requires an argument of %s." %
                          self._KNOWN_TYPES_ENGLISH)
        return
    def __init__(self):
        self._file_type = 'auto'
        self.register_option('--file-type', self._file_type_handler,
                             "auto|html|xml\t"
                             "Explicitly treat files as 'type'",
                             ['-t'])
    def file_type(self, filename):
        if not os.path.exists(filename):
            raise EArgument('%r does not exist.' % filename)
        if self._file_type is not 'auto':
            return self._file_type
        lname = filename.lower()
        if lname.endswith('.template'):
            lname = lname[:-9]
        if lname.endswith('.html') or lname.endswith('.htm'):
            return 'html'
        if lname.endswith('.xml'):
            return 'xml'
        if lname.endswith('.js'):
            return 'js'
        if (lname.endswith('.sh') or
            lname.endswith('.rc') or
            lname.endswith('.csh') or
            lname.endswith('.ksh') or
            lname.endswith('.ash') or
            lname.endswith('.bash') or
            lname.endswith('.profile') or
            lname.endswith('.bash_profile') or
            lname.endswith('.bashrc')):
            return 'shell'
        if isdir(filename):
            return 'directory'
        f = open(filename, 'r')
        try:
            for line in f.xreadlines():
                if line.find('\x1b') != -1:
                    return 'ansi-esc'
        finally:
            f.close()
        raise EArgument('can not determine file type of %r.' % filename)
    _COMMON_FMT = " envenergy_file_info/property: '%s' = '%s' "
    _COMMON_RE = ("\s*envenergy_file_info/property\s*:\s*"
                  "'(.*[^\\\])'\s*=\s*" # Group(1):  Property name
                  "'(.*[^\\\])'\s*"     # Group(2):  Property value
                  )
    _RE_HTML  = re.compile("\s*<!--%s-->.*" % _COMMON_RE, re.IGNORECASE)
    _RE_XML   = _RE_HTML
    _RE_JS    = re.compile("\s*//\s*<<%s>>.*" % _COMMON_RE, re.IGNORECASE)
    _RE_SHELL = re.compile("\s*#\s*<<%s>>.*" % _COMMON_RE, re.IGNORECASE)
    _RE_ANSI  = re.compile("\s*\x1b\[08m%s\x1b\[00m.*" % _COMMON_RE,
                           re.IGNORECASE)
    def property_regex(self, file_type):
        return {'html':self._RE_HTML,
                'js':self._RE_JS,
                'xml':self._RE_HTML,
                'shell':self._RE_SHELL,
                'ansi-esc':self._RE_ANSI,
                }[file_type]
    _PROPERTY_FMT = {
        "html":"<!--" + _COMMON_FMT + "-->\n",
        "xml":"<!--" + _COMMON_FMT + "-->\n",
        "js":"// << " + _COMMON_FMT + " >>\n",
        "shell":"# << " + _COMMON_FMT + " >>\n",
        "ansi-esc":"\x1b[08m" + _COMMON_FMT + "\x1b[00m\n",
        }
    def property_string(self, file_type, property, value):
        return self._PROPERTY_FMT[file_type] % (property, value)
    def as_dict(self, filename, use_first=1):
        property_values = {}
        file_type = self.file_type(filename)
        regex = self.property_regex(file_type)
        property_value = None
        f = open(filename,'r')
        for line in f.xreadlines():
            match = regex.match(line)
            if match:
                property_name = match.group(1)
                property_value = match.group(2)
                property_value = property_value.replace("\\\'","'")
                if use_first:
                    if property_values.has_key(property_name):
                        continue
                property_values[property_name] = property_value
        return property_values
    def get(self, filename, property_name, use_first=1):
        file_type = self.file_type(filename)
        regex = self.property_regex(file_type)
        property_value = None
        f = open(filename,'r')
        for line in f.xreadlines():
            match = regex.match(line)
            if match and match.group(1) == property_name:
                property_value = match.group(2)
                property_value = property_value.replace("\\\'","'")
                if use_first:
                    f.close()
                    break
        return property_value
    def set_properties(self, property_value_list, files, target):
        property_names = []
        for pv in property_value_list:
            property_names.append(pv[0])
        temp_targets = []
        real_targets = []
        tid = thread.gettid()
        for f in files:
            f_type = self.file_type(f)
            regex = self.property_regex(f_type)
            real_target = target
            temp_target = "%s.%s" % (target,tid)
            if os.path.isdir(target):
                real_target = os.path.join(target,
                                           os.path.basename(f))
                temp_target = os.path.join(target,
                                           os.path.basename(temp_target))
            input_file = open(f, 'r')
            output_file = open(temp_target,'w')
            try:
                for pv in property_value_list:
                    output_file.write(self.property_string(f_type, *pv))
                try:
                    for line in input_file.xreadlines():
                        if property_names: # Once all the previous values
                                           # are removed, no need to pattern
                                           # match each line.
                            match = regex.match(line)
                            if match:
                                property_name = match.group(1)
                                if property_name in property_names:
                                    # Assume that the value is only in there
                                    # once.
                                    property_names.remove(property_name)
                                    continue # Skip old value.
                        output_file.write(line)
                except:
                    os.unlink(temp_target)
                    raise
            finally:
                output_file.close()
                input_file.close()
            os.rename(temp_target, real_target)
        return 0

class FileInfo_Set(SubCommand, _FileInfoMixin):
    def _and_handler(self, *args):
        property=self.pop_next()
        value=self.pop_next()
        if property is None or value is None:
            raise EArgument('--and requires property value arguments.')
        self._property_value_list.append((property,value))
        return
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        _FileInfoMixin.__init__(self)
        self.register_option('--and', self._and_handler,
                             "property value\t"
                             "Add another property, value pair to the set"
                             " list",
                             ['-a'])
        self._property_value_list = []
        return
    def __str__(self):
        return "property value file [...] target"
    def __call__(self, *args):
        if not self._property_value_list:
            property_name=self.pop_next()
            property_value=self.pop_next()
            if property_name is None or property_value is None:
                raise EArgument('pfileinfo set requires property_name'
                                ' property_value arguments.')
            self._property_value_list.append((property_name,property_value))
        files = self.arguments()
        if len(files) < 2:
            if len(files) == 1:
                raise EArgument("pfileinfo set command requires a target file"
                                " or directory.")
            raise EArgument("pfileinfo set command requires at least one "
                            " source file and a target file or directory.")
        target = files.pop()
        if len(files) > 1 and not os.path.isdir(target):
            raise EArgument("If more then one source file is specified, then"
                            " the target must be a directory.")
        return self.set_properties(self._property_value_list, files, target)

class FileInfo_Equal(SubCommand, _FileInfoMixin):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        _FileInfoMixin.__init__(self)
        return
    def __str__(self):
        return "property_name property_value file [...]"
    def __call__(self, *args):
        property_name  = self.pop_next()
        property_value = self.pop_next()
        if property_name is None:
            raise EArgument("pfileinfo equal command requires a property_name"
                            " and a property_value as it's first and second"
                            " arguments.")
        if property_value is None:
            raise EArgument("pfileinfo equal command requires a property_value"
                            " name as it's second argument.")
        files = self.arguments()
        if not files:
            raise  EArgument("pfileinfo equal command requires a list of file"
                            " names after the property_value name argument.")
        for f in self.arguments():
            if self.get(f, property_name) != property_value:
                return 2
        return 0

class FileInfo_Get(SubCommand, _FileInfoMixin):
    def _all_properties_handler(self, *args):
        self._all_properties = 1
        return
    def _no_property_text_handler(self, *args):
        self._no_property_text = self.pop_next()
        if self._no_property_text is None:
            raise EOption("--no-property-text requires an argument.")
        return
    def _value_only_handler(self, *args):
        self._value_only = 1
        return
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        _FileInfoMixin.__init__(self)
        self._no_property_text = 'None'
        self._value_only = 0
        self._all_properties = 0
        self.register_option('--all-properties',
                             self._all_properties_handler,
                             "List all properties in the file(s).",
                             ['-a'])
        self.register_option('--no-property-text',
                             self._no_property_text_handler,
                             "text\t"
                             "Text to display if there is no property.",
                             ['-n'])
        self.register_option('--value-only',
                             self._value_only_handler,
                             "Only onput the value a the property.",
                             ['-V'])
        return
    def __str__(self):
        return "property_name file [...]"
    def _all(self):
        files = self.arguments()
        if not files:
            raise  EArgument("pfileinfo get --all command requires a list of"
                             " file names.")
        for f in self.arguments():
            property_values = self.as_dict(f)
            property_names = property_values.keys()
            property_names.sort()
            for property_name in property_names:
                property_value = property_values[property_name]
                if self._value_only:
                    self.put_stdout_msg("%s\n", property_value)
                else:
                    self.put_stdout_msg("%s: %s = '%s'\n",
                                        f, property_name, property_value)
        return 0
    def _specific(self):
        property_name = self.pop_next()
        if property_name is None:
            raise  EArgument("pfileinfo get command requires a property_name"
                             " followed by a list of file names.")
        files = self.arguments()
        if not files:
            raise  EArgument("pfileinfo get command requires a list of file"
                            " names.")
        for f in self.arguments():
            property_value=self.get(f, property_name)
            if property_value is None:
                property_value=self._no_property_text
            if self._value_only:
                self.put_stdout_msg("%s\n", property_value)
            else:
                self.put_stdout_msg("%s: %s = '%s'\n",
                            f, property_name, property_value)
        return 0
    def __call__(self, *args):
        if self._all_properties:
            return self._all()
        return self._specific()

class FileInfo_Type(SubCommand, _FileInfoMixin):
    def _unknown_type_text_handler(self, *args):
        self._unknown_type_text = self.pop_next()
        if self._unknown_type_text is None:
            raise EOption("--unknown-type-text requires an argument.")
        return
    def _value_only_handler(self, *args):
        self._value_only = 1
        return
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        _FileInfoMixin.__init__(self)
        self._unknown_type_text = 'Unknown'
        self._value_only = 0
        self.register_option('--unknown-type-text',
                             self._unknown_type_text_handler,
                             "text\t"
                             "Text to display if the type is not obvious.",
                             ['-n'])
        self.register_option('--value-only',
                             self._value_only_handler,
                             "Only onput the value a the property.",
                             ['-n'])
        return
    def __str__(self):
        return "property_name file [...]"
    def __call__(self, *args):
        files = self.arguments()
        if not files:
            raise EArgument("pfileinfo type command requires a list of file"
                            " names.")
        for f in self.arguments():
            try:
                file_type=self.file_type(f)
            except ECommand:
                file_type=self._unknown_type_text
            if self._value_only:
                self.put_stdout_msg("%s\n", file_type)
            else:
                self.put_stdout_msg("%s: %s\n", f, file_type)
        return 0

class FileInfo(CommandLineUtility):
    HELP = """
pfileinfo:  Command-line utility to set and check properties in shared files.
"""
    OVERVIEW = """
"""
    def __init__(self,  argv=None):
        CommandLineUtility.__init__(self, self.HELP, argv)
        FileInfo_Set(self, "set")
        FileInfo_Equal(self, "equal", ['==', 'eq'])
        FileInfo_Get(self, "get")
        FileInfo_Type(self, "type")
        return
    def run_command(self, command):
        raise EArgument('pfileinfo requires a sub-command.')

if __name__ == '__main__':
    main = FileInfo()
    main()
