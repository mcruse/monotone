"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
# Functionality related to evaluating dynamically generated code.

import types
import copy

from mpx.lib.exceptions import ETypeError

# Use mpx._python.threading because this module is required by log, which is
# is in turn required by msglog.  By using
# mpx._python.threading, it make it possible to log exceptions while still
# importing the core framework.
# @fixme Register the initial locks for potential upgrade later.
# @fixme Clean up initial start-up sequence.
from mpx._python import threading

##
# Provides a controllable (i.e. restricted) environment for executing a
# configurable function.
# @todo Try to make sharing name spaces thread safe without requiring locking.
class RFunction:
    _keyword_defaults = {'args':(), 'context':None, 'rexec':None}
    _init_lock = threading.Lock()
    class _NOARGS:
        pass
    ##
    # @param function The function to invoke.  This can be a string that
    #                 evaluates to a function, or a reference to a function.
    # @keyword args The list of arguments to pass to the function.  If this is
    #               a string it must evaluate to the argument(s) that are
    #               passed to the <code>function</code> by default.  If it is a
    #               list or 
    #               tuple it is assumed to be the list of arguments to pass
    #               to the <code>function</code> by default.  In general, this
    #               behavior is straight forward, the two exceptions are
    #               strings
    #               intended as a single string argument and lists/tuples
    #               intended as a single argument.  In these cases, the string
    #               must be contained in a string (e.g. "'A single arg.'"), and
    #               the list/tuple must contained in a list/tuple (e.g.
    #               [[1,2,3]]).  The best way to avoid confusion is to always
    #               construct the argument list as the entire list of arguments
    #               for the function.
    # @default ()
    # @keyword context The context in which the <code>function</code>
    #                  and <code>args</code> will be evaluated.  This
    #                  only applies if the <code>function</code> or
    #                  <code>args</code> are a string that requires
    #                  evaluation.
    # @default None
    # @keyword rexec A restricted execution environment in which the
    #                <code>function</code> and <code>args</code> are
    #                evaluated and invoked.  If <code>rexec</code> is
    #                None then the context is established in an
    #                unrestricted environment and the evaluations occur in
    #                in a private namespace in the unrestricted environment.
    #                It is possible to share namespaces in the unrestricted
    #                environment by setting <code>rexec</code> to a common
    #                dictionary to use as the namespace.  To share the
    #                namespace with the running Broadway environment, set
    #                <code>rexec</code> to <code>globals()</code>.
    #                
    # @default None
    # @return A callable instance.  If the instance is invoked without
    #         arguments, then the configured <code>functions</code> is
    #         invoked with the configured <code>args</code>.  If the instance
    #         is invoked with arguments, then the <code>function</code> is
    #         invoked with the supplied arguments.
    # @see mpx.lib.security.RExec
    def __init__(self, function, **keywords):
        for keyword in keywords.keys():
            if keyword not in self._keyword_defaults.keys():
                raise 'hell'
        for key, value in self._keyword_defaults.items():
            if not keywords.has_key(key):
                keywords[key] = value
        rexec = keywords['rexec']
        if type(rexec) is types.DictionaryType:
            self._globals = rexec
            rexec = None
        elif not rexec:
            self._globals = {}
        else:
            self._globals = rexec.add_module('__main__').__dict__
        self._eval = self._get_eval(rexec)
        self._exec = self._get_exec(rexec)
        self._set_context(keywords['context'])
        self._func = self._get_function(function)
        self._args = self._get_args(keywords['args'])
        self._command = compile('apply(self._func, self._args)',
                                'RFunction', 'eval')
        self._init_lock.acquire()
        if not hasattr(self,'_global_lock'):
            self._globals['_global_lock'] = threading.Lock()
        self._init_lock.release()
        return
    def _u_eval(self, command):
        return eval(command, self._globals, {})
    def _u_exec(self, command):
        exec command in self._globals
        return None
    def _get_eval(self, rexec):
        if not rexec:
            return self._u_eval
        return rexec.r_eval
    def _get_exec(self, rexec):
        if not rexec:
            return self._u_exec
        return rexec.r_exec
    def _set_context(self, context):
        if context:
            self._exec(context)
        return
    def _get_function(self, function):
        f_type = type(function)
        if f_type is types.StringType or f_type is types.UnicodeType:
            function = self._eval(function)
        if not callable(function):
            raise ETypeError
        return function
    def _get_args(self, args):
        a_type = type(args)
        if a_type is types.TupleType or a_type is types.ListType:
            # We were passed a pre-compile list of arguments.
            pass
        elif a_type is types.StringType or a_type is types.UnicodeType:
            # We were passed a string to compile.
            args = self._eval(args)
            a_type = type(args)
            if a_type is not types.TupleType and a_type is not types.ListType:
                # The args evaluated to a single argument.
                args = (args,)
        else:
            args = (args,)
        return args
    def __call__(self,_arg=_NOARGS,*args):
        self._globals['_global_lock'].acquire()
        self._globals['self'] = self
        try:
            if _arg is not self._NOARGS:
                old_args = self._args
                self._args = [_arg]
                self._args.extend(args)
            result = self._eval(self._command)
        finally:
            if _arg is not self._NOARGS:
                self._args = old_args
            
            del self._globals['self']
            self._globals['_global_lock'].release()
        return result
