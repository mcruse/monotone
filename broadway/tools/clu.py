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
##
# A module to help write command line utilities for the Mediator in Python.

import os
import sys
import types
import traceback

class _Token(object):
    def __init__(self, parent, name, handler, help_str_or_callback, aliases):
        assert aliases is not None
        self.__parent = parent
        self.__name = name
        self.__handler = handler
        self.__help = help_str_or_callback
        self.__aliases = aliases
        self.__standard_io = 0
        self.__stdout_queue = []
        self.__stderr_queue = []
        self.__stdin  = sys.stdin
        self.__stdout = sys.stdout
        self.__stderr = sys.stderr
        return
    def name(self):
        return self.__name
    def parent(self):
        return self.__parent
    def name(self):
        return self.__name
    def get_stdout_msg(self):
        if self.__standard_io:
            return None
        if self.__stdout_queue:
            return self.__stdout_queue.pop(0)
    def get_stderr_msg(self):
        if self.__standard_io:
            return None
        if self.__stderr_queue:
            return self.__stderr_queue.pop(0)
    def put_stdout_msg(self, fmt, *args):
        if args:
            text = (fmt % args)
        else:
            text = fmt
        if self.__standard_io:
            return self.__stdout.write(text)
        self.__stdout_queue.append(text)
        return len(text)
    def put_stderr_msg(self, fmt, *args):
        if args:
            text = (fmt % args)
        else:
            text = fmt
        if self.__standard_io:
            return self.__stderr.write(text)
        self.__stderr_queue.append(text)
        return len(text)
    def _standard_io(self):
        self.__standard_io = 1
        return
    def _special_io(self):
        self.__standard_io = 0
        return
    ##
    # 
    def help_description(self):
        if callable(self.__help):
            text = self.__help()
        else:
            text = self.__help
        return {"name":self.__name,
                "text":text,
                "aliases":self.__aliases}
    def invoke_handler(self, token):
        return self.__handler(token)

class _Option(_Token):
    def process(self, option):
        self.invoke_handler(option)
        return

class _Command(_Token):
    def __init__(self, parent, command, handler,
                 help_str_or_callback, aliases=()):
        _Token.__init__(self, parent, command, handler,
                        help_str_or_callback, aliases)
        self.__verbosity_level = 1
        self.__debug_level = 0
        self.__context = self
        self.__options = {}
        self.__option_map = {}
        self.__commands = {}
        self.__command_map = {}
        self.__arguments = []
        self.register_option('--help', self.__help_option,
                             "Displays this message",
                             ['-h','-u','-?'])
        return
    def __help_option(self, option):
        info = self.help_description()
        self.put_stdout_msg("%s\n", info['text'])
        keys = self.options().keys()
        keys.sort()
        for key in keys:
            option = self.options()[key]
            info = option.help_description()
            self.put_stdout_msg("  %s", info['name'])
            for alias in info['aliases']:
                self.put_stdout_msg(", %s", alias)
            self.put_stdout_msg("\n")
            self.put_stdout_msg("          %s\n", info['text'])
        keys = self.commands().keys()
        keys.sort()
        for key in keys:
            command = self.commands()[key]
            info = command.help_description()
            self.put_stdout_msg("  SUB-COMMAND %s", info['name'])
            for alias in info['aliases']:
                self.put_stdout_msg(", %s", alias)
            self.put_stdout_msg("\n")
            self.put_stdout_msg("          %s\n", info['text'])
        raise EAbortCommand(0)
    def debug_level(self):
        return self.__debug_level
    def verbosity_level(self):
        return self.__verbosity_level
    ##
    # @warning DO NOT OVERRIDE
    def is_more(self):
        return self.parent().is_more()
    ##
    # @warning DO NOT OVERRIDE
    def peek_next(self):
        return self.parent().peek_next()
    ##
    # @warning DO NOT OVERRIDE
    def pop_next(self):
        return self.parent().pop_next()
    def register_option(self, option, handler, help_str_or_callback,
                        aliases=()):
        o = _Option(self, option, handler, help_str_or_callback, aliases)
        self.options()[option] = o
        self.option_map()[option] = option
        for alias in aliases:
            self.option_map()[alias] = option
        return o
    def register_command(self, command, handler, help_str_or_callback,
                        aliases=()):
        c = _Command(self, command, handler,
                     help_str_or_callback, aliases)
        self.commands()[command] = c
        self.command_map()[command] = command
        for alias in aliases:
            self.command_map()[alias] = command
        return c
    ##
    # Establishes this command as the one to run and changes the
    # context to our options and sub-commands
    def process(self):
        self.root().__context = self
        return
    ##
    #
    def root(self):
        root = self
        while root is not root.parent():
            root = root.parent()
        return root
    ##
    #
    def context(self):
        return self.__context
    ##
    # Return all options registerred on the command.
    def options(self):
        return self.__context.__options
    ##
    # 
    def option_map(self):
        return self.__context.__option_map
    ##
    # Return all commands registerred on the command.
    def commands(self):
        return self.__context.__commands
    ##
    # Return all arguments registerred on the command.
    def arguments(self):
        return self.__context.__arguments
    ##
    # 
    def command_map(self):
        return self.__context.__command_map
    ##
    #
    def accept_argument(self, argument):
        self.arguments().append(argument)
        return
    ##
    #
    def process_argument_hook(self, arg):
        self.accept_argument(arg)
        return
    ##
    # Invoke this to execute a command.
    def run_command(self, command):
        return self.__context.invoke_handler(command)

class ECommand(Exception):
    pass


class EAbortCommand(ECommand):
    pass

##
# Exception occurred relating to an argument supplied on the command
# line.
class EArgument(ECommand, TypeError):
    pass

##
# Exception occurred relating to an option supplied on the command
# line.
class EOption(EArgument):
    pass

##
# Exception occurred relating input read from stdin.
class EInput(ECommand):
    pass

##
# Base class that helps write sub-commands as individual classes.
# Instantiation of the SubCommand will result in the basic regestration of
# the sub-command with the super command.
#
# __init___ : A clean place to register options and nested SubCommands.
# __call___ : The method invoked to execute the sub-command.
# __str__   : The method invoked to retrieve this sub-commands help text.
class SubCommand(object):
    ##
    # Register self as sub-command of parent.
    def __init__(self, parent, command, aliases=(), help=None):
        if help is None:
            help = self.__str__
        self.__parent = parent
        self.__registered_command = self.parent().register_command(command,
                                                                   self,
                                                                   help,
                                                                   aliases)
        self.__argument_offset = 0
        return
    def __str__(self):
        return "Help not implemented on %s" % self.__class__
    def parent(self):
        return self.__parent
    def registered_command(self):
        return self.__registered_command
    def arguments(self):
        return self.registered_command().arguments()[self.__argument_offset:]
    def is_more(self):
        # Logic if invoked while parsing the command line.
        result = self.registered_command().is_more()
        if result:
            return result
        # Logic if invoked from the command handler.
        return len(self.arguments()) > 0
    def peek_next(self):
        # Logic if invoked while parsing the command line.
        result = self.registered_command().peek_next()
        if result is not None:
            return result
        # Logic if invoked from the command handler.
        argv = self.arguments()
        if argv:
            return argv[0]
        return None
    def pop_next(self):
        # Logic if invoked while parsing the command line.
        result = self.registered_command().pop_next()
        if result is not None:
            return result
        # Logic if invoked from the command handler.
        result = self.peek_next()
        if result is not None:
            self.__argument_offset += 1
        return result
    def register_option(self, option, handler, help_str_or_callback,
                        aliases=()):
        return self.registered_command().register_option(option, handler,
                                                         help_str_or_callback,
                                                         aliases)
    def register_command(self, command, handler, help_str_or_callback,
                         aliases=()):
        return self.registered_command().register_command(command, handler,
                                                          help_str_or_callback,
                                                          aliases)
    def verbose_message(self, threshold, fmt, *args):
        if self.verbosity_level() >= threshold:
            self.put_stdout_msg(fmt, *args)
        return
    def debug_message(self, threshold, fmt, *args):
        if self.verbosity_level() >= threshold:
            self.put_stderr_msg(fmt, *args)
        return
    def put_stdout_msg(self, fmt, *args):
        self.registered_command().root().put_stdout_msg(fmt, *args)
        return
    def put_stderr_msg(self, fmt, *args):
        self.registered_command().root().put_stderr_msg(fmt, *args)
        return
    def get_stdout_msg(self, fmt, *args):
        self.registered_command().root().get_stdout_msg(fmt, *args)
        return
    def get_stderr_msg(self, fmt, *args):
        self.registered_command().root().get_stderr_msg(fmt, *args)
        return
    def __call__(self, *args):
        raise ENotImplemented

class CommandLineUtility(_Command):
    IDLE = 'idle'
    READY = 'ready'
    PROCESSING_COMMAND = 'processing command'
    PROCESSING_COMMAND_LINE = 'processing command line'
    PROCESSING_TOKENS = 'processing tokens'
    PROCESSING_ARGUMENTS = 'processing arguments'
    def __init__(self, help_str_or_callback, argv=None):
        if argv is None:
            argv = sys.argv
        self.__unprocessed = []
        self.__unprocessed.extend(argv)
        self.__directory = os.path.realpath(os.getcwd())
        self.__command = self.__unprocessed.pop(0)
        self.__command_fullpath = os.path.realpath(self.__command)
        self.__command_basename = os.path.realpath(self.__command_fullpath)
        self.__command_line = self.__command
        self.__state = self.IDLE
        _Command.__init__(self, self, self.__command, self.run_command,
                          help_str_or_callback)
        self.register_separator("--")
        self.register_option('--debug=[level=1]', self.__debug_option,
                             "Enable the specified level of debugging " +
                             "messages.  If level is not specified, then " +
                             "it defaults to 1.",
                             ['-D'])
        self.register_option('--verbosity=[level=2]',
                             self.__verbosity_option,
                             "Enable the specified level of progress " +
                             "messages.  If level is not specified, then " +
                             "it defaults to 1.",
                             ['-v'])
        self.register_option('--doctest',
                             self.__doctest_option,
                             "Run the commands internal documentation string"
                             " tests.")
        return
    def __debug_option(self, option):
        optional_arg = self.peek_next()
        try:
            self.__debug_level = int(optional_arg)
            self.pop_next()
        except:
            self.__debug_level = 1
        return
    def __verbosity_option(self, option):
        optional_arg = self.peek_next()
        try:
            self.__verbosity_level = int(optional_arg)
            self.pop_next()
        except:
            self.__verbosity_level = 2
        return
    def __doctest_option(self, option):
        import doctest
        doctest.testmod(__import__(self.__module__))
        raise SystemExit(0)
    ##
    # @warning DO NOT OVERRIDE
    def is_more(self):
        return self.__unprocessed
    ##
    # @warning DO NOT OVERRIDE
    def peek_next(self):
        if self.__unprocessed:
            return self.__unprocessed[0]
        return None
    ##
    # @warning DO NOT OVERRIDE
    def pop_next(self):
        if self.__unprocessed:
            return self.__unprocessed.pop(0)
        return None
    ##
    # Regsiter's the string that identifies the explicit end of "flagged"
    # options and the beginning of the argument list.
    # @warning DO NOT OVERRIDE
    def register_separator(self, separator):
        self.__separator = separator
        return
    ##
    # @warning DO NOT OVERRIDE
    def is_separator(self, separator):
        return self.__separator == separator
    ##
    #
    # @warning DO NOT OVERRIDE
    def begin_processing_tokens(self):
        self.__state = self.PROCESSING_TOKENS
        return
    ##
    #
    # @warning DO NOT OVERRIDE
    def is_processing_tokens(self):
        return self.__state == self.PROCESSING_TOKENS
    ##
    #
    # @warning DO NOT OVERRIDE
    def begin_processing_arguments(self):
        self.__state = self.PROCESSING_ARGUMENTS
        return
    ##
    #
    # @warning DO NOT OVERRIDE
    def is_processing_arguments(self):
        return self.__state == self.PROCESSING_ARGUMENTS
    ##
    #
    # @warning DO NOT OVERRIDE
    def _process_tokens(self):
        while self.is_processing_tokens() and self.is_more():
            token = self.pop_next()
            if token[0:1] == '-':
                if self.option_map().has_key(token):
                    option = self.option_map()[token]
                    description = self.options()[option]
                    description.process(token)
                else:
                    self.unknown_option_hook(token)
            else:
                if self.command_map().has_key(token):
                    command = self.command_map()[token]
                    description = self.commands()[command]
                    description.process()
                else:
                    self.unknown_command_hook(token)
            continue
        return
    ##
    #
    # @warning DO NOT OVERRIDE
    def _process_arguments(self):
        while self.is_processing_arguments() and self.is_more():
            argument = self.pop_next()
            self.process_argument_hook(argument)
        return
    ##
    #
    # @warning DO NOT OVERRIDE
    def process_command_line(self):
        self.__state = self.PROCESSING_COMMAND_LINE
        self.begin_processing_tokens()
        self._process_tokens()
        self._process_arguments()
        self.__state = self.READY
        return
    ##
    # Overridable hook called when the seperator is located, or when
    # by unknown_command_hook.
    # @param explicit True indicates that the option separator was
    #        encounterred.
    def end_of_options_hook(self, explicit=0):
        return
    ##
    # Overridable hook called when an unknown "command" is encounterred.
    # By fallback, calls the end_of_options_hook, begin_processing_arguments,
    # and then encounterred_argument to accept the unknown command as the
    # first post option argument.
    def unknown_command_hook(self, command):
        self.end_of_options_hook()
        self.begin_processing_arguments()
        if not self.is_separator(command):
            self.process_argument_hook(command)
        return
    ##
    # Overridable hook called when an unknown "command" is encounterred.
    # By fallback, calls the end_of_options_hook, begin_processing_arguments,
    # and then encounterred_argument to accept the unknown command as the
    # first post option argument.
    def unknown_option_hook(self, option):
        if not self.is_separator(option):
            raise EOption("Unknown option %s" % option)
        self.begin_processing_arguments()
        return
    ##
    # Derived class must implement this method.  It must call the
    # self.process_command_line() method to handle command line arguments.
    def run_command(self, command):
        raise NotImplementedError
    ##
    # To run from a python module.
    def run(self):
        self.process_command_line()
        return self.context().run_command(self.name())
    ##
    # To run from a Python 'command'.  This entry point results in
    # raising system exit.
    #
    # ERROR CODE:
    #
    #   If the run() method does not raise an exception, then
    #   the command exits with whatever value the run_command()
    #   method returned.
    #
    #   1 -> EArgument, EOption:
    #   7 -> EInput
    #   8 -> ECommand
    #   9 -> Exception
    def __call__(self):
        e = None
        code = 9
        try:
            self._standard_io() # Don't queue I/O for programatic use.
            code = self.run()
        except SystemExit, e:
            code = e.args[0]
        except EAbortCommand, e:
            code = 9
            if e.args:
                if type(e.args[0]) == types.IntType:
                    code = e.args[0]
        except ECommand, e:
            if isinstance(e, EArgument) or isinstance(e, EOption):
                code = 1
            elif isinstance(e, EInput):
                code = 7
            else:
                code = 8
        except Exception, e:
            self.put_stderr_msg(
                "ERROR: Unexpected Exception, not derived from ECommand.\n"
                "       %s",
                e)
            traceback.print_exc()
            raise SystemExit(code)
        if e is not None and code is not 0:
            self.put_stderr_msg("ERROR: %s\n", e)
        raise SystemExit(code)
