"""
Copyright (C) 2003 2005 2006 2007 2010 2011 Cisco Systems

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
# WARNING:  Importing this module will modify the running framework's
#           properties to ensure a clean environment.  For this to
#           to work correctly, it should be imported before any other
#           framework module.

# @fixme Could have unforeseen side effects.
import _mpxhooks
_mpxhooks.load_properties_warning = False

import os as _os
import shutil as _shutil
import sys as _sys
import traceback as _traceback
import unittest as _unittest

main = _unittest.main

# @warning These flags are some serious voodoo!  They deserve a fair amount of
#          explanation, but until then here is the summary:
#          DefaultTestFixture.assert_comparison and
#          DefaultTestFixture.should_raise_assertion() were causing extra
#          references to local variables in test case methods that meant that a
#          "del" of a variable did not result in its reference count going to
#          zero.  This made it hard to test __del__ methods without hard to
#          understand work arounds.  These flags result in cleaning up the
#          problem.
#
#          I should write more, but I'm busy.
#
# @fixme DEL_F_LOCALS and DEL_F_GLOBALS could be set via a module load time
#        test in case Python's inner workings regarding
#        frame.f_locals/frame.f_globals were to change.
DEL_F_LOCALS = True
DEL_F_GLOBALS = False

STATE = None
TEARDOWN_BEGUN ="tearDown begun."
TEARDOWN_COMPLETE ="tearDown complete."
SETUP_BEGUN = "setUp begun."
SETUP_COMPLETE = "setUp complete."

##
# Default TestCase Fixture for Envenergy
# This is the base class for all Envenergy Unit Tests that conform
# to PyUnit specifications.   It allows for centralized creating and
# tear down of objects needed for testing.
#
# This could open the logger file, setup the framework.   Or anything
# else that each test might need.
class DefaultTestFixture(_unittest.TestCase):
    _tmpnam_count = 0
    def __init__(self, *args, **kw):
        args = (self,) + args
        self.msglog_object = None
        _unittest.TestCase.__init__(*args, **kw)
        return
    def setUp(self):
        _sys.stderr.flush()
        _sys.stdout.flush()
        global STATE
        assert STATE in (None, TEARDOWN_COMPLETE), (
            "in setUp with bad state %r.  MOST LIKELY PREVIOUS TEST" % STATE
            )
        STATE = SETUP_BEGUN
        # Create all the overridden directories.
        create_testing_directories()
        allow_reloadable_singletons()
        # Ensure the msglog exists before any other logs.
        from mpx.lib import msglog
        self.msglog_object = msglog.log_object()
        self.msglog_object.singleton_load()
        STATE = SETUP_COMPLETE
        _sys.stderr.flush()
        _sys.stdout.flush()
        return
    def tearDown(self):
        _sys.stderr.flush()
        _sys.stdout.flush()
        global STATE
        assert STATE is SETUP_COMPLETE, (
            "in tearDown with bad state %r.  MOST LIKELY THIS TEST" % STATE
            )
        STATE = TEARDOWN_BEGUN
        unload_reloadable_singletons()
        # Delete all the overridden directories.
        destroy_testing_directories()
        reinit_touchy_modules()
        STATE = TEARDOWN_COMPLETE
        _sys.stderr.flush()
        _sys.stdout.flush()
        return
    ##
    # Raises an AssertionError exception if `lvalue operator rvalue` does not
    # evaluate to true.
    #
    # The `lvalue operator rvalue` expression is evaluated in the context
    # of the calling method/function.  In other words, all local and global
    # variables defined in the context of the caller are available, including
    # self for objects, built-in functions, imported modules and all other
    # references.
    #
    # If assertion fails, then the message associated with the AssertionError
    # describes the expected result and the actual result.  This message
    # is ultimately the reason that this method exists as it should make
    # the cause of failures more obvious for debugging.
    #
    # @param lvalue A string to evaluate as the left side of an expression.
    # @param operator A string to evaluate as the operand of an expression.
    # @param rvalue A string to evaluate as the right side of an expression.
    # @param _frame_index An integer that specifies the frame to use when
    #                     evaluating the expression `lvalue operator rvalue`.
    #                     This allows establishing the context as any execution
    #                     frame on the stack.
    # @default 1 Use the caller's frame as the context.
    def assert_comparison(self, lvalue, operator, rvalue, _frame_index=1):
        frame = _sys._getframe(_frame_index)
        l = frame.f_locals
        g = frame.f_globals
        try:
            self.assert_(
                eval("%s %s %s" % (lvalue, operator, rvalue),
                     g, l),
                ("\n"
                 "    Expected:\n"
                 "        %s %s %s\n"
                 "    Evaluated to:\n"
                 "        %r %s %r") % (lvalue, operator, rvalue,
                                        eval(lvalue, g, l),
                                        operator,
                                        eval(rvalue, g, l),)
                )
        finally:
            if DEL_F_LOCALS:
                for k in l.keys():
                    del l[k]
            if DEL_F_GLOBALS:
                for k in g.keys():
                    del g[k]
        return
    ##
    # Raises an AssertionError if object does not have attribute.
    #
    # @param object The object to test for the presence of an attribute.
    # @param attribute The name of the attribute to check for.
    def assert_hasattr(self, object, attribute):
        self.assert_(
            hasattr(object, attribute),
            "%r instance missing %r attribute" % (object.__class__.__name__,
                                                  attribute)
            )
        return
    ##
    # Raises an AssertionError exception if evaluating the
    # <code>expression</code> does not raise an AssertionError.
    #
    # This method is used to ensure that the target expression is enforcing
    # it's pre-condition "contract" via assertions.  In other words, it
    # is used to test the assert clauses of a function/method.  If the byte
    # code's were compiled optimized without assertions, them this method
    # simply returns.
    #
    # @param expression The string to exec that should raise an assertion.
    # @param message An additional message to add to the generic
    #                "`expression` failed to raise the expected assertion"
    #                message used if the `expression` does not raise an
    #                assertion.
    # @param _frame_index An integer that specifies the frame to use when
    #                     evaluating the expression `expression`.
    #                     This allows establishing the context as any execution
    #                     frame on the stack.
    # @default 1 Use the caller's frame as the context.
    #
    # @note It is assumed that all modules are built with the same assertion
    #       optimizations.
    def should_raise_assertion(self, expression, message=None, _frame_index=1):
        try:
            assert 0, "Test that the project was compiled with assertions."
        except AssertionError, e:
            try:
                frame = _sys._getframe(_frame_index)
                l = frame.f_locals
                g = frame.f_globals
                try:
                    exec(expression, frame.f_globals, frame.f_locals)
                except AssertionError, e:
                    return
                else:
                    text = ("%r failed to raise the expected assertion" %
                            expression)
                    if message:
                        text = test + ':\n' + message
                    self.fail(text)
            finally:
                if DEL_F_LOCALS:
                    for k in l.keys():
                        del l[k]
                if DEL_F_GLOBALS:
                    for k in g.keys():
                        del g[k]
        else:
            return
        raise EInternalError("Executed unreachable code.")
    ##
    # Creates a node tree with all the implicit services, an empty
    # /interfaces/virtuals and an empty /aliases subtree.
    #
    # @note The tree has NOT been started, the test case must
    #       call as_internal_node('/').start() if it wants
    #       a RUNNING node tree.
    def new_node_tree(self):
        import mpx.service
        import mpx.ion.host
        import mpx.lib.node
        services = mpx.service._Anchor()
        services.configure({'name':'services','parent':'/'})
        host = mpx.ion.host.Unknown()
        host.configure({'name':'interfaces','parent':'/'})
        virtuals = mpx.lib.node.CompositeNode()
        virtuals.configure({'name':'virtuals','parent':host})
        try:
            aliases = mpx.lib.node.Aliases()
        except:
            from mpx.lib import deprecated
            deprecated("Using deprecated Aliases factory:"
                       "  mpx.service.aliases.Aliases()")
            import mpx.service.aliases
            aliases = mpx.service.aliases.Aliases()
        aliases.configure({'name':'aliases','parent':'/'})
        return
    ##
    # Deletes the entire node tree, stopping any remaining
    # RUNNING nodes.
    #
    # @note The lack of start()/stop() symmetry is a bit annoying,
    #       but seems safest.
    def del_node_tree(self):
        from mpx.lib.node import as_internal_node
        root = as_internal_node('/')
        root.prune(force=0)
        return
    ##
    # Return a 'new' temporary file name each invokataion.
    #
    # This function does not create the file, it just
    # returns a filename that it never returned before.
    #
    # @param template A format string containing keyed references
    #                 to replacement values that is used to generate the
    #                 filename.  The valid keys are:
    #                 %(pid)d and %(tmpnam_count)d
    # @default "tmpnam%(pid)d.%(tmpnam_count)d.tmp"
    # @return A string containing the 'new' temporary file name.
    def tmpnam(self, template="tmpnam%(pid)d.%(tmpnam_count)d.tmp"):
        import mpx
        temp_dir = mpx.properties.TEMP_DIR
        DefaultTestFixture._tmpnam_count += 1
        return _os.path.join(
            temp_dir, template % {"pid":_os.getpid(),
                                  "tmpnam_count":DefaultTestFixture._tmpnam_count}
            )

##
# Class can represent a huge string (of repeated data) without consuming a lot
# of memory.
class RepeatingString(str):
    def __init__(self, value, count):
        self.__value = value
        self.__count = count
        self.__length = count * len(value)
        self.__appended = []
        return
    def __new__(klass, value, count):
        return str.__new__(klass, value)
    def __str__(self):
        result = ''
        for i in range(self.__count):
            result += self.__value
        for a in self.__appended:
            result += a
        return result
    def __repr__(self):
        return repr(self.__str__())
    def __len__(self):
        sappended = 0
        for a in self.__appended:
            sappended += len(a)
        return self.__length + sappended
    def __append(self,value):
        self.__appended.append(value)
        return
    def __eq__(self,other):
        return self.__cmp__(other) == 0
    def __cmp__(self, other):
        for start in xrange(0,self.__length,len(self.__value)):
            upto = start + len(self.__value)
            result = cmp(self.__value, other[start:upto])
            if result:
                return result
        for a in self.__appended:
            start = upto
            upto += len(a)
            result = cmp(a, other[start:upto])
            if result:
                return result
        if other[upto:]:
            return -1
        return 0
    def __getitem__(self,index):
        if index < self.__length:
            offset = index % len(self.__value)
            return self.__value[offset]
        adj_index = index - self.__length
        appended = []
        appended.extend(self.__appended)
        while appended:
            next = appended.pop(0)
            if len(next) > adj_index:
                return next[adj_index]
            adj_index -= len(next)
        # Raise str's exact exception...
        self.__value[index]
        raise EInternalError("Executing unreachable code.")
    def __getslice__(self, first, upto):
        if upto <= first:
            return ''
        repeat_upto = min(upto,self.__length)
        if repeat_upto > first:
            # Calculate the repeating bit.
            rotated_pattern = (self.__value[first % len(self.__value):] +
                               self.__value[:first % len(self.__value)])
            # Calculate the number of repeats.
            count = int((repeat_upto - first) / len(rotated_pattern))
            # Calculate the remaining portion from the rotated_pattern
            remainder = ''
            nremaining = (repeat_upto - first) % len(rotated_pattern)
            if nremaining:
                remainder = rotated_pattern[:nremaining]
            slice = RepeatingString(rotated_pattern,count)
            slice.__append(remainder)
        else:
            slice = ''
        # Add on any sliced data from our appended list.
        upto -= repeat_upto
        appended = []
        appended.extend(self.__appended)
        while appended and upto >= 0:
            next = appended.pop(0)[:upto]
            slice += next
            upto -= len(next)
        return slice
    def __add__(self, other):
        dup = RepeatingString(self.__value,self.__count)
        for more in self.__appended:
            dup.__append(more)
        dup.__append(other)
        return dup

_TARGET_ROOT = _os.path.join('/tmp', str(_os.getpid()))
_TEMP_DIR   = _os.path.join(_TARGET_ROOT, 'tmp')

_OVERRIDES = {
    "HTTPS_PORT":"8443",
    "HTTP_PORT":"8080",
    "STRICT_COMPLIANCE":"true",
    "TARGET_ROOT":_TARGET_ROOT,
    }
_DIRECTORY_LIST = (
    "BIN_DIR",
    "CONFIGURATION_DIR",
    "DATA_DIR",
    "ETC_DIR",
    "HOME_ROOT",
    "HTTPS_ROOT",
    "HTTP_ROOT",
    "INFO_DIR",
    "LIB_DIR",
    "LOGFILE_DIRECTORY",
    "MPX_PYTHON_LIB",
    "PDO_DIRECTORY",
    "SBIN_DIR",
    "TARGET_ROOT",
    "TEMP_DIR",
    "VAR_LOCK",
    "VAR_LOG",
    "VAR_RUN",
    "VAR_RUN_BROADWAY",
    "WWW_ROOT",
    )

##
# Create the temporary directories used for testing.
def create_testing_directories():
    global _properties
    # Create all the overridden directories.
    for prop in _DIRECTORY_LIST:
        if not _os.path.exists(getattr(_properties,prop)):
            _os.makedirs(getattr(_properties,prop))
    return

##
# Delete the temporary directories used for testing.
def destroy_testing_directories():
    # Delete all the overridden directories.
    if _os.path.exists(_TARGET_ROOT):
        _shutil.rmtree(_TARGET_ROOT)
    return

def reinit_touchy_modules():
    import mpx.lib.persistent
    mpx.lib.persistent._reinit()

##
# Mark singletons as unloadable and then unload all of them.
def unload_reloadable_singletons():
    from mpx.lib._singleton import _ReloadableSingleton
    _ReloadableSingleton.singleton_set_loadable_state_all(False)
    _ReloadableSingleton.singleton_unload_all()
    return

##
# Mark singletons as loadable.
def allow_reloadable_singletons():
    from mpx.lib._singleton import _ReloadableSingleton
    _ReloadableSingleton.singleton_set_loadable_state_all(True)
    return

##
# This function runs all test methods (that is to say, all methods
# whose names begin with the four characters "test") in the instance
# of the test_class objected passed in.  test_class must be an instance
# of unittest.TestCase or one of its subclasses.
#
# This procedure is a library procedure that is used by some of the
# test cases in the broadway source tree.  It is not called directly
# from code in this module.  But some _test_case modules import this
# module and call this procedure indirectly.
#
# @param test_class  Reference to class that has
#                    methods you want run.
# @param debug Boolean indicator to print additional
#              debug data.
# @default 0
def test(test_class, debug = 0):
    results = []
    for key in test_class.__dict__.keys():
        function = None
        if key.find('test') == 0:
            function = test_class.__dict__[key]
            if callable(function):
                result = _unittest.TestResult()
                test_class(key)(result)
                results.append(result)
    return results

if __name__ is not "__main__":
    # Update the environment used to establish the propoerties.
    for property, value in _OVERRIDES.items():
        _os.environ["BROADWAY_%s" % property] = value

    # Import and validate the properties.
    from mpx import properties as _properties
    #_properties.DEBUG_LOCKS = 1
    #_properties.DEBUG_LOCKS_APPROACH = 2
    #_properties.DEBUG_LOCKS_TIMEOUT = 10
    assert _properties.TARGET_ROOT == _TARGET_ROOT, ("""
ERROR: mpx.properties.TARGET_ROOT does not match the test system's TARGET_ROOT.
The most likely cause is that the mpx_test module was imported after
the mpx module.""")
    # Uncomment to force use of debugging locks:
    #_properties.DEBUG_LOCKS = 1
    #_properties.DEBUG_LOCKS_APPROACH = 2
    #_properties.DEBUG_LOCKS_TIMEOUT = 10

    # Ensure that the temporary target directories exist for other modules.
    create_testing_directories()
