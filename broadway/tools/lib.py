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
# Tools for use in developing Broadway scripts.
#

import getopt
GetoptError = getopt.GetoptError
_getopt = getopt.getopt
del getopt

import os as _os
import sys as _sys

class CommandKeywords:
    FATAL_KEY = 'errors_are_fatal'
    MESSAGE_KEY = 'message'
    VERBOSITY_KEY = 'verbosity'
    DEBUG_KEY = 'debug'
    TEST_KEY = 'test'
    DEFAULTS = {
        FATAL_KEY:0,
        MESSAGE_KEY:'',
        VERBOSITY_KEY:1,
        DEBUG_KEY:0,
        TEST_KEY:0
        }
    def __init__(self, command, keywords, additional_defaults=None):
        if additional_defaults is None: additional_defaults={}
        self.keywords = {}
        self.keywords.update(self.DEFAULTS)
        self.keywords.update(additional_defaults)
        self.keywords.update(keywords)
        for k, v in self.keywords.items():
            setattr(self, k, v)
        return
    def _write_message_to(self, files, format, *args):
        if hasattr(format, 'readline'):
            line = format.readline()
            while line:
                self._write_message_to(files, line)
        else:
            for file in files:
                if args:
                    file.write(format % args)
                else:
                    file.write(format)
                file.write('\n')
                file.flush()
        return
    def _default_files(self, files, keywords):
        if keywords.has_key('file'):
            return (keywords['file'],)
        if keywords.has_key('files'):
            return keywords['files']
        return files
    def normal_message(self, format, *args, **keywords):
        files = self._default_files((_sys.stdout,), keywords)
        self._write_message_to(files, format, *args)
        return
    def debug_message(self, format, *args, **keywords):
        if self.debug:
            files = self._default_files((_sys.stderr,), keywords)
            self._write_message_to(files, format, *args)
        return
    def test_message(self, format, *args, **keywords):
        if self.test:
            files = self._default_files((_sys.stderr,), keywords)
            self._write_message_to(files, format, *args)
        return
    def error_message(self, format, *args, **keywords):
        files = self._default_files((_sys.stderr,), keywords)
        self._write_message_to(files, format, *args)
        return
    def fatal_message(self, format, *args, **keywords):
        files = self._default_files(files, keywords)
        self._write_message_to(files, format, *args)
        return
    def verbose_message(self, verbosity, format, *args, **keywords):
        files = self._default_files((_sys.stderr,), keywords)
        if self.verbosity >= verbosity:
            self._write_message_to(files, format, *args)
        return

##
# A much better, basically reverse compatible, version of getopt.  At least
# the functionality is better, the implementation is a bit sketchy.
#
# @fixme If the last option on the command line takes an optional argument
#        and the next token is intended as the first non-option argument,
#        it will still be consumed as the optional argument.
#        Example: Assuming 'v:"1"', then "./script -v filename" will set
#                 filename as -v's optional argument.

## fgd changed the default argument from [] to None to prevent unintended reuse

def getopt(args, short_args, long_args=None):
    class _OptionDescription:
        NO_ARGUMENT = 'no argument'
        OPTIONAL_ARGUMENT = 'optional argument'
        REQUIRED_ARGUMENT = 'required argument'

        def __init__(self):
            self.type = 'option not loaded'
            self.name = ''
            self.cli_name = ''
            self.getopt_description = ''
            self.argument_type = self.NO_ARGUMENT
            self.argument_default=None
            
        def __str__(self):
            msg = "%s: %s (cli %s, getopt %s), %s" % (self.type, self.name,
                                                      self.cli_name,
                                                      self.getopt_description,
                                                      self.argument_type)
            if self.argument_default is not None:
                msg += " (default %s)" % self.argument_default
            return msg
        
        def incremental_load(self, remaining_options):
            pass
        
    class _LongDescription(_OptionDescription):
        def incremental_load(self, remaining_options):
            self.__init__()
            self.type = 'long option'
            option = remaining_options[0].split("=",1)
            self.name = option[0]
            if len(option) > 1:
                self.argument_type = self.OPTIONAL_ARGUMENT
                default = option[1]
                if default:
                    if default == '=':
                        self.argument_type = self.REQUIRED_ARGUMENT
                        default = None
                    elif default[0] == '\\':
                        # Eat leading escape
                        default = default[1:]
                    self.argument_default = default
            self.cli_name = '--' + self.name
            self.getopt_description = self.name
            if self.argument_type == self.REQUIRED_ARGUMENT:
                self.getopt_description += "="
            return remaining_options[1:]
        
    class _ShortDescription(_OptionDescription):
        def incremental_load(self, remaining_options):
            self.__init__()
            self.type = 'short option'
            self.name = remaining_options[0]
            remaining_options = remaining_options[1:]
            if (len(remaining_options)):
                if remaining_options[0] == ':':
                    self.argument_type = self.OPTIONAL_ARGUMENT
                    remaining_options = remaining_options[1:]
                    if (len(remaining_options)):
                        if remaining_options[0] in "\"'":
                            quote = remaining_options[0]
                            triplet = remaining_options.split(quote,2)
                            if len(triplet) < 3:
                                raise GetoptError(
                                    "Missmatched %s in internal " + \
                                    "description of the short argument %s." \
                                    % (repr(quote), repr(self.name)),
                                    "Invalid short argument sescription")
                            self.argument_default = triplet[1]
                            remaining_options = triplet[2]
                        elif remaining_options[0] == ":":
                            self.argument_type = self.REQUIRED_ARGUMENT
                            remaining_options = remaining_options[1:]
            self.cli_name = '-' + self.name
            self.getopt_description = self.name
            if self.argument_type == self.REQUIRED_ARGUMENT:
                self.getopt_description += ":"
            return remaining_options

    def find_option_by_cli(options, cli_name):
        for o in option_list:
            if o.cli_name == cli_name:
                return o
        return None

    #
    # getopt()
    #
    option_list = []
    getopt_short = ''
    o = _ShortDescription()
    while short_args:
        short_args = o.incremental_load(short_args)
        getopt_short += o.getopt_description
        option_list.append(o)
        o = _ShortDescription()
    getopt_long = []
    o = _LongDescription()
    while long_args: #will be None or a list passed in
        long_args = o.incremental_load(long_args)
        getopt_long.append(o.getopt_description)
        option_list.append(o)
        o = _LongDescription()
        
    optlist = []
    # remainder is all the unprocessed arguments.
    remainder = []
    for arg in args:
        if arg[0:2] == '--' and len(arg) > 2:
            arg_list = arg.split('=',1)
            remainder.extend(arg_list)
        else:
            remainder.append(arg)
    while 1:
        optlist_temp, remainder = _getopt(remainder,
                                          getopt_short, getopt_long)
        # See if any REQUIRED option ate another option.
        for opt, arg in optlist_temp:
            o = find_option_by_cli(option_list, opt)
            if o.argument_type == o.REQUIRED_ARGUMENT:
                ol, rl = _getopt((arg, 'place holder'),
                                 getopt_short, getopt_long)
                if ol:
                    raise GetoptError(("option %s requires an argument"+
                                       ", but is followed by %s.") %
                                      (o.cli_name, ol[0][0]),
                                      o.cli_name)
        # See if the last option missed it's optional argmument.
        if len(optlist_temp):
            last = optlist_temp[-1][0]
            o = find_option_by_cli(option_list, last)
            if o.argument_type == o.OPTIONAL_ARGUMENT:
                # The last option is optional, use the first remaining
                # argument if it exists.
                if (remainder):
                    optlist_temp[-1] = (last, remainder.pop(0))
        if not optlist_temp:
            # Apply defaults
            retlist = []
            for opt, arg in optlist:
                if not arg:
                    o = find_option_by_cli(option_list, opt)
                    if o.argument_default:
                        arg = o.argument_default
                retlist.append((opt,arg))
            return retlist, remainder
        optlist.extend(optlist_temp)

#
# Helpers for DecodeStatus
#

_invalid_exit_status = """\
The process' exit status is invalid.  The process may still be running."""

_inconsistent_count_and_stati = """\
Internal error,  decoding is inconsistent."""

_internal_error = """\
The reason the process terminated can not be \
reported due to an internal error"""

def _generate_too_many_stati_message(exited, err,
                                     stopped, stopsig,
                                     signaled, signal):
    return _inconsistent_count_and_stati
def _generate_exited_message(err):
    if err:
        result = "The process terminated with a non-zero exit status of %s." \
                 % err
        if err == 2:
            result += "  Typically this indicates a syntax err."
    else:
        result = "The process terminated with an exit status of 0." +\
                 "Typically this indicates success."
    return result

def _get_signal_name(sig):
    import signal
    for s in dir(signal):
        if s[0:3] == "SIG" and s[0:4] != "SIG_":
            v = getattr(signal,s)
            if v == sig:
                return s
    return None

def _generate_stopped_message(stopsig):
    signame = _get_signal_name(stopsig)
    if signame is None:
        sigtext = "unknown signal %s" % stopsig
    else:
        sigtext = "%s %s" % (signame, stopsig)
    return "Unexpected state:  Command is stopped due to %s." % sigtext

def _generate_signaled_message(stopsig):
    signame = _get_signal_name(stopsig)
    if signame is None:
        sigtext = "unknown signal %s" % stopsig
    else:
        sigtext = "%s %s" % (signame, stopsig)
    return "Command terminated due to %s." % sigtext

##
# Decode the status of a dead external program.
class DecodeStatus:
    def __init__(self, status):
        ##
        # 1 IFF the status is decodable.
        self.valid = 0
        ##
        # 1 IFF the process is stopped, 0 otherwise.
        self.stopped = 0
        ##
        # The signal number that stopped the process.  -1 if the process is
        # not stopped.
        self.stopped_by = -1
        ##
        # 1 IFF the process called the exit() function.  0 otherwise.
        self.called_exit = 0
        ##
        # The exit code passed to the exit() function.  -1 if the process
        # did not call exit.
        # @note Typically, an exit_code of 0 indicates success, and a non-zero
        #       exit_code indicates failure.  Furthermore, an exit_code
        #       of 2 usually indicates a syntax failure.
        self.exit_code = -1
        ##
        # 1 IFF the process was killed by a signal (external or internal).
        # 0 otherwise.
        self.killed = 0
        ##
        # The signal number that killed the process.  -1 if the process
        # was not killed.
        self.killed_by = -1
        ##
        # The generic message that best describes why the process terminated,
        # or an internal failure message.
        self.message = ''

        self.called_exit = _os.WIFEXITED(status)
        if self.called_exit:
            self.exit_code = _os.WEXITSTATUS(status)
        else:
            self.exit_code = -1
        self.stopped = _os.WIFSTOPPED(status)
        if self.stopped:
            self.stopped_by = _os.WSTOPSIG(status)
        else:
            self.stopped_by = -1
        self.killed = _os.WIFSIGNALED(status)
        if self.killed:
            self.killed_by = _os.WTERMSIG(status)
        else:
            self.killed_by = -1
        self.message = ''
        count = self.called_exit + self.stopped + self.killed
        if not count:
            # This one's too little...
            self.message = _invalid_exit_status
        elif count > 1:
            # This one's too big...
            self.message = _generate_too_many_stati_message(self.called_exit,
                                                            exit_code,
                                                            self.stopped,
                                                            self.stopped_by,
                                                            self.killed,
                                                            self.killed_by)
        elif count == 1:
            # This one's just right...
            if self.called_exit:
                self.message = _generate_exited_message(self.exit_code)
                self.valid = 1
            elif self.stopped:
                self.message = _generate_stopped_message(self.stopped_by)
                self.valid = 1
            elif self.killed:
                self.message = _generate_signaled_message(self.killed_by)
                self.valid = 1
            else:
                self.message = _inconsistent_count_and_stati
                self.valid = 1
        else:
            # This one's fricken imposible!
            self.message = _internal_error
        return

##
# Handy os module-like extensions...
# Concrete class can replace:
#   method verbosity() that returns the default verbosity as an integer.
#   method debug() that returns the default debugging level as an integer.
#
class OS_Mixin:
    _DBGCMD = 'export OS_MIXIN_DEBUG=1; set -x -v;'
    ##
    # @keyword 'errors_are_fatal' If true, then a non-zero exit status
    #                             from the <code>command</code> will cause
    #                             this method to print a <code>message</code>
    #                             and exit the program.
    # @default 0
    # @keyword 'message' A message to print if the <code>command</code> fails
    #                    and <code>errors_are_fatal</code> is true.
    # @default ''
    # @keyword 'verbosity' 0 redirects all output to /dev/null, 1 redirects
    #                      standard output to /dev/null and 2 (or above)
    #                      does not redirect any output.
    # @default 1
    # @keyword 'debug'
    # default 0
    # @keyword 'test'
    # default 0
    def kill(self, pid, signal, **keywords):
        command_keywords = CommandKeywords("kill()", keywords)
        message = "os.kill(%d, %d)" % (pid, signal)
        if command_keywords.test:
            command_keywords.test_message("TEST: %s", message)
            return 0
        command_keywords.debug_message("DEBUG: %s", message)
        return _os.kill(pid, signal)
    ##
    # @keyword 'errors_are_fatal' If true, then a non-zero exit status
    #                             from the <code>command</code> will cause
    #                             this method to print a <code>message</code>
    #                             and exit the program.
    # @default 0
    # @keyword 'message' A message to print if the <code>command</code> fails
    #                    and <code>errors_are_fatal</code> is true.
    # @default ''
    # @keyword 'verbosity' 0 redirects all output to /dev/null, 1 redirects
    #                      standard output to /dev/null and 2 (or above)
    #                      does not redirect any output.
    # @default 1
    # @keyword 'debug'
    # default 0
    # @keyword 'test'
    # default 0
    def system(self, *command_fragments, **keywords):
        keywords = CommandKeywords("system()", keywords)
        command = ''
        for fragment in command_fragments:
            if command: command += ' '
            command += fragment
        original_command = command
        command = "( %s )" % command
        if keywords.verbosity < 1:
            command += ' 2>/dev/null'
        if keywords.verbosity < 2:
            command += ' >/dev/null'
        if keywords.debug:
            command = self._DBGCMD + command
        if not keywords.test:
            keywords.verbose_message(2, "PROGRESS: os.system(%s)", command)
            status = _os.system(command)
            if status and keywords.errors_are_fatal:
                self.fatal_command_exit(original_command, status,
                                        keywords.message)
            return status
        else:
            keywords.normal_message("TEST: os.system(%s)...", command)
        return 0
    def error_exit(self, message, code=1, **keywords):
        keywords = CommandKeywords("error_exit()", keywords)
        keywords.error_message("ERROR: %s", message)
        _sys.exit(code)
        return
    def fatal_command_exit(self, command, status, message="", **keywords):
        keywords = CommandKeywords("error_exit()", keywords)
        banner = "ERROR:  %s " % repr(command)
        if _os.WIFEXITED(status):
            banner += "returned exit code %d." % _os.WEXITSTATUS(status)
        elif _os.WIFSIGNALED(status):
            banner += "was killed with signal %d." % _os.WTERMSIG(status)
        elif _os.WIFSTOPPED(status):
            banner += "was stopped with signal %d." % _os.WSTOPSIG(status)
        else:
            banner += "exited for unknown reasons."
        keywords.error_message(banner)
        if message: keywords.error_message(message)
        _sys.exit(3)

class _OS(OS_Mixin):
    def system(self, *args, **keywords):
        if not keywords.has_key('debug'):
            keywords['debug'] = self.__debug()
        if not keywords.has_key('verbosity'):
            keywords['verbosity'] = self.__verbosity()
        OS_Mixin.system(self, *args, **keywords)
    def __getattr__(self, name):
        return getattr(_os, name)
    def __debug(self):
        level = os.environ.get('OS_MIXIN_DEBUG')
        if level is None: level = 0
        return level
    def __verbosity(self):
        level = os.environ.get('OS_MIXIN_VERBOSITY')
        if level is None: level = 1
        return level

##
# "Enhanced" os module...
os = _OS()

##
# @fixme Use MpxException?
class EInvalidState(Exception):
    pass

##
# @fixme Use MpxException?
class EInvalidAction(Exception):
    pass

##
#
class SimpleTag:
    class States:
        INITIALIZED = "INITIALIZED"
        SCANNING = "SCANNING"
        NODATA = "NODATA"
        EXTRACTING = "EXTRACTING"
    class Actions:
        PARSE = "PARSE"
        EOD = "EOD"
        EXTRACT = "EXTRACT"
        EOT = "EOT"
    def __init__(self, first_line_text, first_line_number, next_line_callback):
        self._state = self.INITIALIZED
        self._current_line = first_line_text
        self._partial_line = first_line_text
        self._first_line_number = first_line_number
        self._last_line_number = first_line_number
        self._next_line = next_line_callback
        self._name = None
        self._elements = []
        self._state_table = None
        # The default table is initialized here to allow using any callable.
        self.DEFAULT_STATE_TABLE = {
            States.INITIALIZED:{
                Actions.PARSE:(self._scan,()),
                },
            States.SCANNING:{
                Actions.EOD:(self._eod,()),
                Actions.EXTRACT:(self._extract,()),
                },
            States.EXTRACTING:{
                Actions.EXTRACT_FIRST:(self.extract_argument,
                    (Actions.EXTRACT_NEXT,
                     Actions.EOT,
                     Actions.EXTRACT_FAILED)),
                Actions.EXTRACT_NEXT:(self.extract_to_eot,
                    (Actions.EOT,
                     Actions.EOT,
                     Actions.EXTRACT_FAILED)),
                Actions.EOT:(self.eot,()),
                Actions.EXTRACT_FAILED:(self.failed,()),
                },
            }
        return
    def _handle_action(self, action):
        if not self._state_table.has_key(self._state_table):
            raise EInvalidState(self._state, action)
        actions = self._state_table[self._state]
        if not actions.has_key(action):
            raise EInvalidAction(self._state, action)
        return actions[action]()
    ##
    # @return A dictionary specifiying new rules for the extracting the tag's
    #         arguments.
    # @note By default the current rules are returned.
    # @fixme Too limitting?  Replace ALL rules?
    def new_extracting_rules(self):
        return self._state_table[States.EXTRACTING]
    ##
    # Extract a single argument from the current line.  If the argument
    # starts with a qoute, it may contain whitespace and span several
    # lines.
    #
    # @return The next action to perform.  If no actions remain,
    #         return Actions.EOT.
    def extract_argument(self):
        text = self._partial_line.strip()
        q = text[0:1]
        if q == '"' or q == "'":
            text, self._partial_line = self._split_quoted_text(text,q)
        else:
            filter = self.split(None,1)
            text = filter[0]
            if len(filter) == 1:
                self._advance_current_line()
            else:
                self._partial_line = filter[1]
        return Actions.EXTRACT_NEXT
    def _advance_current_line(self):
        self._current_line = self._next_line()
        self._partial_line = self._current_line
        if self._state == self.SCANNING:
            self._first_line_number += 1
        self._last_line_number += 1
        return self._current_line
    def _extract(self):
        self._state = States.EXTRACTING
        self._state_table[States.EXTRACTING] = self.new_extracting_rules()
        return self._handle_action(Actions.EXTRACT_FIRST)
    def _eod(self):
        self._state = States.NODATA
        return None
    def _scan(self):
        self._state = States.SCANNING
        while self._current_line is not None:
            filter = self._current_line.split('#',1)
            if len(filter) == 2:
                filter = filter[1]
                if filter[0:2] == ' @':
                    filter = filter[2:].split(None,1)
                    self._name = filter[0]
                    if len(filter) == 2:
                        self._partial_line = filter[1]
                    else:
                        self._partial_line = ''
                    return self._handle_action(Actions.EXTRACT)
            self._advance_current_line()
        return self._handle_action("EOD")
    def parse(self):
        if self._state_table is None:
            self._state_table = self.DEFAULT_STATE_TABLE
        return self._handle_action(self.Actions.PARSE)
