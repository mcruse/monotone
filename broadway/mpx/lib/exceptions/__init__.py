"""
Copyright (C) 2001 2002 2003 2004 2005 2007 2008 2009 2010 2011 Cisco Systems

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
import sys as _sys
import traceback as _traceback
import weakref as _weakref
import StringIO as _StringIO

# @fixme (1) Implement the consistant "argument stack" approach to the
#            parameter parsing.
# @fixme (2) As part of (1), save off popped values in self.parsed_args so
#            the default __repr__ always works.
# @fixme (3) Use the same trick [see (2)] on any extracted keyword
#            arguments.
# @fixme (4) Document the rules for parsing/extracting args and
#            keywords.

##
# Defines the base classes from which all Broadway exceptions are derived,
# contains the core Broadway exceptions and all the built-in Python
# exceptions.
#
# There are special
# considerations when implmenting Broadway exceptions.  If the derived
# exception implements a constructor (the <code>__init__()</code> method),
# then it must follow the following conventions:
# <ol>
#   <li>It must support keyword arguments.</li>
#   <li>It must call its base class' constructor.</li>
# </ol>
# <p>
# If the derived class does not implement a constructor, then there are no
# special considerations.
# <p>
# Examples of implementing Broadway exceptions:
# <code>
# <p>
# ##
# <br>
# # This is the most simple implementation of a new MPX exception.
# <br>
# class ESimpleException(MpxException):
# <br>&nbsp;&nbsp;&nbsp;&nbsp;
#     pass
# <br>
#
# ##
# <br>
# # Example exception that overrides the __init__ method:
# <br>
# class EUsesKeywords(MpxException):
# <br>&nbsp;&nbsp;&nbsp;&nbsp;
#     def __init__(self, *args, **keywords):
# <br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
#         for arg in args:
# <br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
#             pass # <i>Do something with the args...</i>
# <br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
#         MpxException.__init__(self, **keywords)
# <br>
# </code>
# <p>
# The naming convention for all derived classes is to begin the exception's
# name with an uppercase 'E' immediately followed by the mixed case name.  This
# naming convention prevents any name confilicts with built-in exceptions.
# Examples:  EIOError, ETimeout, ENoSuchName, etc...
#

#
# IMPLEMENTATION NOTES:
# 1.  This is implemented as a package so that it may include the built-in
#     exceptions in an import statement.  If it where a module, then internal
#     'import exception' statements whould import itself, instead of the
#     built-ins.
#
# All builtin exceptions are imported primarily so that modules in the lib
# package have access to the standard exceptions via exception.<i>whatever</i>.
# This is especially crucial to the RNA implementation.

import errno as _errno
import os as _os
import types as _types

from mpx._python.exceptions import *

def class_path_of(object):
    return '.'.join((object.__class__.__module__,
                     object.__class__.__name__))

def exception_as_dict__(self):
    d = {}
    d['__base__'] = 'Exception'
    d['__class__'] = class_path_of(self)
    d['args'] = self.args
    d['str'] = self.__str__()
    return d

def exception_as_dict(self):
    bound_method = getattr(self,'_as_dict',None)
    if bound_method is None:
        return exception_as_dict__(self)
    return bound_method()

def exception_repr(self):
    return repr(exception_as_dict(self))

##
# The base class for all Broadway exceptions.
class MpxException(Exception):
    ##
    # The constructor for the base MPX exception class.
    #
    # @param *args  Tuple of all non-keyword args.
    # @param **keywords Dictionary of keyword args.
    def __init__(self, *args, **keywords):
        Exception.__init__(self, *args)
        self.keywords = keywords
        self._print_exc_str = None
    def __str__(self):
        if len(self.args) == 1:
            return str(self.args[0])
        elif len(self.args) > 1:
            return str(self.args)
        return ''
    def _as_dict(self):
        d = exception_as_dict__(self)
        d['keywords'] = self.keywords
        return d
    def __repr__(self):
        return repr(self._as_dict())

class SecurityException(MpxException):
    pass

class Unauthorized(SecurityException):
    """
        User wasn't allowed to access a resource.
    """
    def __init__(self, explanation='unknown'):
        self.details = explanation
        SecurityException.__init__(self, explanation)
    def __str__(self):
        return 'Action Not Authorized: %s' % self.details

class Forbidden(SecurityException):
    """
        A resource cannot be accessed under any circumstances.
    """
    def __init__(self, explanation='unknown'):
        self.details = explanation
        SecurityException.__init__(self, explanation)
    def __str__(self):
        return 'Action Forbidden: %s' % self.details

class ForbiddenAttribute(Forbidden, AttributeError):
    """
        An attribute is unavailable because it is forbidden (private).
    """


#
# Common framework exceptions.
#

##
# Exception raised when an argument to a function or method is invalid.
class EInvalidValue(MpxException):
    ##
    # @param name The name of the value that was invalid.
    # @param value The value that is invalid.
    # @param text An optional string of descriptive text.  This variable may
    #             also be set to a dictionary to be used as MpxException
    #             keywords.
    # @default None
    # @keyword **keywords
    def __init__(self, name='unknown', bad_value='unknown', text=None,
                 **keywords):
        ##
        # The name of the argument that raised the error.
        self.name = name
        ##
        # The value that was considerred invalid.
        self.bad_value = bad_value
        ##
        # Optional descriptive text.
        self.text = text
        if text != None:
            MpxException.__init__(self, name, bad_value, text, **keywords)
        else:
            MpxException.__init__(self, name, bad_value, **keywords)

class ENotUpgradable(MpxException):
    def __init__(self, name='unknown', reason='unknown'):
        self.name = name
        self.reason = reason
        MpxException.__init__(self, name, reason)

class EInvalidXML(MpxException):
    pass

class EUnknownVersion(MpxException):
    pass

##
# Indicates that some functionality has not been implemented.
# @param callable_object The callable entity that raised the
#                        exception.
# @default None
class ENotImplemented(MpxException, NotImplementedError):
    def __init__(self, *args, **keywords):
        self.callable_object = None
        if len(args):
            callable_object = args[0]
            if callable(callable_object):
                self.callable_object = callable_object
                args = args[1:]
        MpxException.__init__(self, *args, **keywords)
    def _builtin_function_str(self, callable_object):
        # The built-in function's name.
        return "built-in function or method '%s'" % str(callable_object)
    def _builtin_method_str(self, callable_object):
        # At the time of implementation (Python2.2.1),
        # types.BuiltinFunctionType is types.BuiltinMethodType.
        return self._builtin_function_str(callable_object)
    def _class_str(self, callable_object):
        # The class' module.name.
        return "class '%s'" % str(callable_object)
    def _function_str(self, callable_object):
        # The function's name,
        return "function '%s'" % callable_object.__name__
    def _instance_str(self, callable_object):
        # The instance's module.class.
        return "instance '%s.%s'" % (callable_object.__module__,
                                     callable_object.__class__.__name__)
    def _method_str(self, callable_object):
        # The method's module.class.name.
        binding = ''
        if callable_object.im_self is None:
            binding = 'un'
        return "%sbound method '%s.%s.%s'" % (
            binding,
            callable_object.im_class.__module__,
            callable_object.im_class.__name__,
            callable_object.im_func.__name__)
    def _unbound_method_str(self, callable_object):
        # At the time of implementation (Python2.2.1),
        # types.MethodType is types.UnboundMethodType.
        return self._method_str(callable_object)
    def __str__(self):
        if self.callable_object is not None:
            if not len(self.args):
                callable_type = type(self.callable_object)
                if callable_type is _types.BuiltinFunctionType:
                    return self._builtin_function_str(self.callable_object)
                elif callable_type is _types.BuiltinMethodType:
                    return self._builtin_method_str(self.callable_object)
                elif callable_type is _types.ClassType:
                    return self._class_str(self.callable_object)
                elif callable_type is _types.FunctionType:
                    return self._function_str(self.callable_object)
                elif callable_type is _types.MethodType:
                    return self._method_str(self.callable_object)
                elif callable_type is _types.UnboundMethodType:
                    return self._unbound_method_str(self.callable_object)
                pass
            # Since we're not processing callable_object, push it back
            # into the arguments and use the fallback string representation.
            args = [self.callable_object]
            args.extend(self.args)
            self.args = args
        elif (len(self.args) == 1
              and type(self.args[0]) is _types.InstanceType):
            return self._instance_str(self.args[0])
        return MpxException.__str__(self)

##
# EAbstract is a specific case of ENotImplemented that is raised by
# methods of an Abstract that need to be implemented by the derived
# class.
class EAbstract(ENotImplemented):
    pass

class EInternalError(MpxException):
    pass

class EUnreachableCode(EInternalError):
    pass

class ENotFound(MpxException):
    pass

class EIOError(MpxException, IOError):
    pass

class EDeviceNotFound(ENotFound):
    pass

class ETimeout(MpxException):
    pass

class EResourceError(MpxException):
    pass

class EProtocol(MpxException):
    pass

class EInvalidSession(MpxException):
    pass

class EInvalidMessage(EProtocol):
    pass

class EBadChecksum(EInvalidMessage):
    pass

class EInvalidResponse(EProtocol):
    pass

class EInvalidCommand(EProtocol):
    pass

class EInvalidProtocol(EProtocol):
    pass

class EFileNotFound(ENotFound):
    pass

class EConnectionError(MpxException):
    pass

class EBadChecksum(MpxException):
    pass

class ENotEnabled(MpxException):
    pass

class ENotStarted(MpxException):
    pass

class EBusy(MpxException):
    pass

class EBadBatch(MpxException):
    pass

##
# Exception raised to indicate that an object does not have a required
# attribute.
#
# Typically raised to indicate that an object does not sufficiently
# support an interface.
#
class EMissingAttribute(MpxException):
    ##
    # Instaciate Object.
    #
    # @param name  The name of the attribute that is missing.
    #
    def __init__(self, name='unknown', **keywords):
        MpxException.__init__(self, name, **keywords)

class ENameError(MpxException):
    pass

class EDeleteActiveUser(ENameError,KeyError):
    def __str__(self):
        return "%s(%s)" % (type(self).__name__, KeyError.__str__(self))

class ENoSuchName(ENameError,KeyError):
    def __str__(self):
        return "%s(%s)" % (type(self).__name__, KeyError.__str__(self))

class ENoSuchNode(ENoSuchName):
    pass

class ECovNode(MpxException):
    pass

class ENonCovNode(MpxException):
    pass

class EAttributeError(MpxException, AttributeError):
    def __str__(self):
        return AttributeError.__str__(self)

##
# Exception raised to indicate that a name is already in use.
#
class ENameInUse(ENameError):
    ##
    # Instaciate Object.
    #
    # @param name  The name that is already in use.
    #
    def __init__(self, name='unknown', **keywords):
        MpxException.__init__(self, name, **keywords)

class EUnknownScheme(ENameError):
    pass

##
# Exception for circular alias referencing.
#
class ECircularReference(ENameError):
    ##
    # Initialize object.
    #
    # @param first_name  The name of the alias being looked up.
    # @param last_name  The name of the alias that refers back to
    #                   the first alias.
    #
    def __init__(self, first_name='unknown', last_name='unknown', **keywords):
        MpxException.__init__(self, 'Alias "' + last_name +
                              '" points back at Alias "' + first_name + '"',
                              **keywords)

class EAlreadyOpen(EIOError):
    pass

class ENotOpen(EIOError):
    pass

class ETypeError(MpxException, TypeError):
    pass

class EImmutable(ETypeError):
    def __init__(self, *args, **keywords):
        if len(args) == 0:
            args = ("Instance is immutable",)
        ETypeError.__init__(self, *args, **keywords)

class EConfiguration(MpxException):
    pass

##
# Exception raised if a configuration dictionary does not
# contain a required attribute and that attribute has not
# previously been configured.
class EConfigurationIncomplete(EConfiguration):
    ##
    # Initialize the object.
    #
    # @param name  The name of the attribute
    #              whose configuration is incomplete.
    #
    def __init__(self, name='unknown', **keywords):
        EConfiguration.__init__(self,name,**keywords)

class EConfigurationInvalid(EConfiguration):
    pass

class EAlreadyRunning(MpxException):
    pass

class ENotRunning(MpxException):
    pass

class ENoData(MpxException):
    pass

class EDatabase(MpxException):
    pass

class EDatabaseVersion(EDatabase):
    pass
##
# Exception raised by batching operations that invoke the same method on
# a list of targets.
class EBatchedException(MpxException):
    def __init__(self, method='unknown', exc_map={}):
        # exc_map = relates nodepath to exc_string
        MpxException.__init__(self, method, exc_map)

class ERangeError(EResourceError):
    def __init__(self, name='unknown', start='unknown', end='unknown',
                 **keywords):
        self.name = name
        self.start = start
        self.end = end
        if keywords.has_key('good_start'):
            self.good_start = keywords['good_start']
            del(keywords['good_start'])
        if keywords.has_key('good_end'):
            self.good_end = keywords['good_end']
            del(keywords['good_end'])
        EResourceError.__init__(self, **keywords)

class EParseFailure(MpxException, SyntaxError):
    pass

class EPermission(MpxException, OSError):
    ##
    # @keyword 'target' String used to identify the node/file/whatever on which
    #                   permission was denied.
    def __init__(self, *args, **kw):
        target=None
        if kw.has_key('target'):
            target=kw['target']
            del kw['target']
        OSError.__init__(self, _errno.EACCES, _os.strerror(_errno.EACCES),
                         target)
        MpxException.__init__(self, *args, **kw)
    def __str__(self):
        result = MpxException.__str__(self)
        if self.filename is not None:
            result = "%s: %s" % (self.filename, result)
        return result

class EOverflow(MpxException, OverflowError):
    pass

class EBreakupTransfer(EIOError):
    def __init__(self,break_at,reason='Format/Transport Error'):
        self.break_at = break_at
        EIOError(self,reason)

class EUnexpectedTerminalMode(EProtocol):
    pass

class ERemoteNodeAbstraction(EProtocol):
    pass

class ERNATimeout(ERemoteNodeAbstraction):
    pass

##
# A "wrapper" used when decorating exceptions generated using Python's
# depricated exception model.
# @note DO NOT USE THIS CLASS TO RAISE EXCEPTIONS!
class DeprecatedPythonException(Exception):
    """A "wrapper" used when decorating exceptions generated using Python's
    depricated exception model.

    DO NOT USE THIS CLASS TO RAISE EXCEPTIONS!"""

class _NicknameAttr(object):
    def __get__(self, instance, klass):
        if not hasattr(instance, 'nickname'):
            setattr(instance, 'nickname',
                    instance._nickname())
        return getattr(instance, 'nickname')

class _NameAttr(object):
    def __get__(self, instance, klass):
        if not hasattr(instance, 'name'):
            setattr(instance, 'name',
                    instance._name())
        return getattr(instance, 'name')

class _TracebackAttr(object):
    def __get__(self, instance, klass):
        if not hasattr(instance, 'traceback'):
            setattr(instance, 'traceback',
                    instance._traceback())
        return getattr(instance, 'traceback')

##
# Decorates an exception with consistent information about the exception.
#
# @note This class is where standard exception formating methods should
#       be added, both for reverse compatibility (e.g. the existing
#       batch and async_batch handling, as well as new, Broadway wide
#       consistent text messages are developed.
class DecoratedException(object):
    ##
    # Class method that returns a <code>DecoratedException</code> that
    # describes the supplied exception.
    #
    # @param exc_type The class of the exception to decorate.
    # @param exc_value The instance of the exception to decorate.
    # @param exc_traceback The traceback of the exception to decorate.
    # @return An instance of a DecoratedException that describes the supplied
    #         exception in a consistant manner.
    # @note To improve performance, <code>DecoratedException</code>'s
    #       lazily initialize thier traceback attribute.  Until the
    #       the traceback attribute is initialize, the
    #       <code>DecoratedException</code> keeps a reference to the
    #       exception's exc_traceback.  This can cause a lot of
    #       references that delay the collection of objects, thereby
    #       increasing memory consumption.  This is an intentional
    #       trade-off, please be aware of it.
    def factory(klass, exc_type, exc_value, exc_traceback, limit=64):
        return klass(exc_type, exc_value, exc_traceback, limit)
    factory = classmethod(factory)
    ##
    # Instantiate a new <code>DecoratedException</code> that describes
    # the supplied exception.
    #
    # @param exc_type The class of the exception to decorate.
    # @param exc_value The instance of the exception to decorate.
    # @param exc_traceback The traceback of the exception to decorate.
    def __init__(self, exc_type, exc_value, exc_traceback, limit=64):
        assert isinstance(exc_value, Exception), (
            "exc_value must be an Exception."
            )

        self.__exc_traceback = exc_traceback
        self.__limit = limit

        ##
        # The instance of actual exception to decorate.
        self.exception = exc_value

        ##
        # A tuple of dictionaries that discribe each line in exception's
        # traceback. The first entry (index 0) is the line which raised
        # the exception, with each subsequent entry describing the line
        # that invoked the previous entry.  Each entry consists of the
        # following optional key/value pairs:
        # @key 'line-number' The line number where the error occurred.
        # @key 'filename' The name of file in which the error occurred.
        # @key 'function-name' The name of the function or method
        #                      in which the error occurred.
        # @key 'text' The text that caused the error, or if 'line-number'
        #             'filename' and 'function-name' are not present,
        #             additional descriptive text.
        #
        # @note The <code>traceback</code> is limited to <code>limit</code>
        #       entries+1 maximum, which defaults (arbitrarily) to 65.
        #
        # @note This attribute is lazily initialized.
        self.traceback = None
        del self.traceback

        ##
        # The full-name of the exception.  The full-name is expressed as a
        # Python module path.  Examples are: 'exceptions.KeyError', and
        # 'mpx.lib.exceptions.ENoSuchName'.
        #
        # @note This attribute is lazily initialized.
        self.name = None
        del self.name

        ##
        # The nickname of the exception.  The nickname is expressed as the last
        # component of the exception's full-name.  Examples are: 'KeyError',
        # and 'ENoSuchName'.
        #
        # @note This attribute is lazily initialized.
        self.nickname = None
        del self.nickname

        return
    ##
    # @return A string that mimics the output of the Python's
    #         traceback.print_exc() function.
    def print_exc_as_string(self):
        result = _StringIO.StringIO()
        result.write("Traceback (most recent call last):\n")
        for line in self.traceback:
            if line.has_key('filename'): filename = line['filename']
            else: filename = None
            if line.has_key('line-number'): lineno = line['line-number']
            else: lineno = None
            if line.has_key('function-name'): function = line['function-name']
            else: function = None
            if line.has_key('text'): text = line['text']
            else: text = None
            if (filename is not None and lineno is not None and
                function is not None):
                result.write('  File "%s", line %s, in %s\n' % (filename, lineno,
                                                                function))
                if text is not None:
                    text_lines = text.split('\n')
                    for text_line in text_lines:
                        result.write('    %s\n' % text_line)
            elif filename is None and lineno is None and function is None:
                if text is not None:
                    text_lines = text.split('\n')
                    for text_line in text_lines:
                        result.write('%s\n' % text_line)
        nickname = self.nickname
        argv = self.exception.args
        if nickname == 'DeprecatedPythonException' and argv:
            nickname = argv[0]
            argv = argv[1:]
        argc = len(argv)
        if argc == 0:
            result.write(nickname)
        elif argc == 1:
            result.write("%s: %s" % (nickname, argv[0]))
        else:
            result.write("%s: %r" % (nickname, tuple(argv)))
        result.write('\n')
        return result.getvalue()
    ##
    # @return A string that mimics the output of the Python's
    #         traceback.print_exc() function.
    def __str__(self):
        return self.print_exc_as_string()
    ##
    # Returns the calculated nickname of the exception as a string.
    def _nickname(self):
        return self.exception.__class__.__name__
    ##
    # Returns the calculated name of the exception as a string.
    def _name(self):
        return "%s.%s" % (self.exception.__class__.__module__,
                          self.exception.__class__.__name__)
    ##
    # Returns the calculated traceback tuple.
    def _traceback(self):
        result = []
        traceback = _traceback.extract_tb(self.__exc_traceback)
        del self.__exc_traceback
        if traceback:
            for line in traceback[0:self.__limit]:
                filename, lineno, function, text = line
                line = {}
                if filename: line['filename'] = filename
                if lineno is not None: line['line-number'] = lineno
                if function and function != '?': line['function-name'] = function
                if text is not None: line['text'] = text
                result.append(line)
            if len(result) < len(traceback):
                result.append(
                    {'text':'Traceback terminated due to %r entry limit.' %
                     self.__limit,}
                    )
        result = tuple(result)
        return result

DecoratedException.name = _NameAttr()
DecoratedException.nickname = _NicknameAttr()
DecoratedException.traceback = _TracebackAttr()

##
# Return a  <code>DecoratedException</code> instance that
# describes the supplied exception.
#
# @param exc_type The class of exception.
# @param exc_value The instance of the exception.
# @param exc_traceback The exception's traceback.
# @return An instance of a DecoratedException that describes the supplied
#         exception in a consistant manner.
def decorated_exception(exc_type, exc_value, exc_traceback):
    # Test for old style "string" exceptions, e.g.:  raise 'hell'
    if type(exc_type) in _types.StringTypes:
        # For old-style exceptions, exc_value is the argument passed to the
        # raise keyword, e.g.:  raise 'hell', 'argument'.  Convert exc_value
        # to an optional argument list.
        if exc_value is None:
            exc_value = ()
        else:
            exc_value = (exc_value,)
        # Now replace exc_value with an DeprecatedPythonException instance,
        # using the raise keyword's arguments.
        exc_value = DeprecatedPythonException(exc_type, *exc_value)
        # Finally, replace exc_type with a reference to the
        # DeprecatedPythonException class.
        exc_type = DeprecatedPythonException
    # Now, exc_type is the class of exception, exc_value is the instance of
    # the exception and exc_traceback is the exception's traceback.
    return DecoratedException.factory(exc_type, exc_value, exc_traceback)

##
# Return a  <code>DecoratedException</code> instance that
# describes the current exception.
#
# @note The "current" exception means the exception currently being
#       handled inside of the except block of a try/except clause
#       in the current thread.
#
# @return An instance of a DecoratedException that describes the supplied
#         exception in a consistant manner.
def current_exception():
    exc_type, exc_value, exc_traceback = _sys.exc_info()
    assert exc_type is not None, (
        "current_exception() can only be called in a stack frame that is"
        " currently handling an exception (i.e. code ultimately invoked"
        " in the except block of a try/except clause."
        )
    return decorated_exception(exc_type, exc_value, exc_traceback)
