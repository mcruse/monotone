"""
Copyright (C) 2010 2011 Cisco Systems

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
# Broadway Log Tool:
#
# TODO:
# - Create a log of any type or version. (default ASCII, latest).
# - Generate a WHOLE BUNCH of bogus data.
# - Delete a log.
# - Populate a log from a file (csv, xml, etc).
# - List all known logs, there type and version.
# - Force a log to upgrade to any later version.

# @fixme
# Too complicated output wise?  Methinks it is close, maybe drop
# _verbosity and set it to _output. -v could control assorted levels
# and/or combinations of other flags (-1, errors only, 1, errors +
# standard output, 2, add progress messages, 3, adds debogging).
# @fixme Actually, there should be stdout + log messages.
#        log messages have a type DEBUG, etc, and can be directed
#        to files and/or logs...
# @fixme Group advanced commands together?  Support --help and
#        --help-advanced?
#

import string
import sys
import types

from lib import os, CommandKeywords, getopt

def parse_args(argv):
    pass

class Option:
    def __init__(self, generic_name, help_text,
                 short_name=None, long_name=None):
        self.generic_name = generic_name
        self.help_text = help_text
        self.short_name = short_name
        self.long_name = long_name
        return

class Argument:
    pass

class RequiredArgument:
    pass

class RequiredArgumentList:
    pass

class OptionalArgumentList:
    pass

class CommandOutput:
    def __init__(self, file, output_level):
        file_type = type(file)
        if file_type is types.IntType:
            self.file = fdopen(file)
        elif file_type is types.FileType:
            self.file = file
        elif (file_type is types.StringType or
              file_type is types.UnicodeType):
            self.file = open(file,'w+')
        else:
            raise EInvalidType('file', file_type)
        self.default_level = 1 # If no level is specfied in a
                               # write, then use this as the
                               # level for the write.
        self.output_level = output_level   # Maximum write level that will
                                           # actually generate output.  The
                                           # higher this number, the noisier
                                           # the output.
        return
    def write(self, text):
        self.file.write(text)

class Utility:
    LEVEL='level'
    HEADER='header'
    ##
    # The order that arguments are added is the order they are expected.
    def __init__(self, argv, options=(), *arguments):
        self._progress = CommandOutput(sys.stdout, 0)
        self._verbose = CommandOutput(sys.stdout, 1)
        self._debug = CommandOutput(sys.stderr, 0)
        self._warning = CommandOutput(sys.stderr, 1)
        self._error = CommandOutput(sys.stderr, 1)
        self.command_line = string.join(argv)
        self.command = os.path.basename(argv[0])
        self.options = {}
        self.arguments = []
        for option in options:
            self.options[option.generic_name]
        for argument in arguments:
            self.add_argument(argument)
    def add_option(self, option):
        self.options[option.generic_name] = option
        return
    def add_argument(self, argument):
        self.arguments.append(argument)
        return
    def parse(self):
        pass
    def invoke(self):
        return 0
    def run(self):
        # @fixme Exception handling.
        self.parse()
        return self.invoke()
    def _write_line(self, output, fmt, args, keywords):
        if keywords.has_key(self.LEVEL):
            level=keywords[self.LEVEL]
        else:
            level=output.default_level
        if level >= output.output_level:
            try:
                output.write(output.header + (fmt % args))
                output.write('\n')
                return 1
            except:
                pass
            pass
        return 0

    # -------------- BETTER MODEL -
    # ERR, WARN, DEBUG, PROGRESS, FATAL, ... ?
    def log(self, type, level, fmt, args):
        pass

    def output(self, fmt, args):
        pass

    def error(self, fmt, args): # Not sure...
        pass

    def warning(self, fmt, args): # Not sure...
        pass

# -------------- BETTER MODEL -
    
    ##
    #
    def message(self, fmt, *args):
        return self.verbose_message(fmt, *args, **{self.LEVEL:0,
                                                   self.HEADER:0})
    ##
    # stdout and progress >= **level
    # @return True if output, false if ignorred.
    def progress_message(self, fmt, *args, **keywords):
        return self._write_line(self._progress, fmt, args, keywords)
    ##
    # stderr and debug >= **level
    # @return True if output, false if ignorred.
    def debug_message(self, fmt, *args, **keywords):
        return self._write_line(self._debug, fmt, args, keywords)
    ##
    # stdout and verbosity >= **level
    # @return True if output, false if ignorred.
    def verbose_message(self, fmt, *args, **keywords):
        return self._write_line(self._verbose, fmt, args, keywords)
    ##
    # stderr and warning >= **level
    # @return True if output, false if ignorred.
    def warning_message(self, fmt, *args, **keywords):
        return self._write_line(self._warning, fmt, args, keywords)
    ##
    # stderr, and error >= **level.
    # @return True if output, false if ignorred.
    def error_message(self, fmt, *args):
        return self._write_line(self._error, fmt, args, keywords)

class BLT(Utility):
    pass

# def MAIN(argv):    
#     args = parse_args(argv)
#     output = CommandKeywords(args.command, args.keywords)
#     return

# run = parse() + invoke() + nice exception handling (so you don't have to).
# add an options module for peacemeal assembly.
#

if __name__ == '__main__':
    BLT(sys.argv).run()
