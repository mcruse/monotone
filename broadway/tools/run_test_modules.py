"""
Copyright (C) 2003 2007 2010 2011 Cisco Systems

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
# Manage the running of automated TestCases
# 
# Given a starting directory, this module will seek out test
# modules in that directory and its subdirectories and run all
# the tests in those test modules.  The test results are displayed
# on standard output.
#
# A test module is any file in the directory hierarchy whose name
# matches the pattern "_test_case*.py".  The order in which tests
# are run is arbitrary.
#
# @fixme 2 Get rid of _WrappingText and log when #1 is fixed.

import unittest
import os
import popen2
import string
import sys
import types
import string
from traceback import print_exc,format_exception

_INVALID_TEST_UNIT_OR_DIRECTORY = "%s is not a valid test unit or directory."
c_test_prefix = "_test" # C unit tests match '_test*'

##
# Append the root_dir relative module path to the test case module if the file
# referenced by the full path string filepath.
#
# @param The project's root directory.
# @patam The full path to the file to add to the list of test_units.
def _test_module_from_file(root_dir, filepath, test_units):
    #
    # Strip off root_dir and final '.py[co]'
    #
    if filepath[-3:] == '.py':
        iend = -3
    elif filepath[-4:-1] == '.py':
        iend = -4
    else:
        raise NameError(_INVALID_TEST_UNIT_OR_DIRECTORY % filepath)
    filepath = filepath[len(root_dir)+1:iend]
    #
    # Replace '/' with '.' for a valid module path.
    #
    modulepath = string.replace(filepath, "/", ".")
    test_units.append(modulepath)
    if _debug > 0:
        sys.stderr.write("Adding %s (%s) to test suite.\n" %
                         (modulepath, filepath,))
    return

def _c_test_from_path(root_dir, srcname, c_tests):
    c_tests.append(srcname)
    if _debug > 0:
        sys.stderr.write("Adding %s (%s) to test suite.\n" %
                         (srcname, os.path.basename(srcname),))        
    return

##
# Beginning in the directory named "src" searching for files whose name
# matches the glob pattern "_test_unit*.py".  For each such file found,
# construct the corresponding python module name by removing the ".py" 
# from the end of the filename and converting all "/" characters in the
# filename into ".".  Append the resulting module name to the "test_units"
# global variable.
def _find_test_units(current_dir, root_dir, test_units):
    if _debug > 1:
        sys.stderr.write("Scanning %s, relative to %s, for test cases..\n" %
                         (current_dir, root_dir,))
    names = os.listdir(current_dir)
    for name in names:
        srcname = os.path.join(current_dir, name)
        try:
            if os.path.isdir(srcname):
                if "." in name:
                    # A directory with a "." in the name is not a valid
                    # Python path.
                    continue
                _find_test_units(srcname, root_dir, test_units)
            else:
                # is a file
                # See if it is a TestCase
                if _debug > 2:
                    sys.stderr.write("Check if %s is a test cases..\n" %
                                     (srcname,))
                base = os.path.basename(srcname)
                if base[:10] == "_test_case" and (base[-3:] == ".py" or
                                                  base[-4:] == ".pyc"):
                    _test_module_from_file(root_dir, srcname, test_units)
        except (IOError, os.error), e:
            raise "find_test_units_error", e

##
# Beginning in the directory named "current_dir" searching for files whose name
# matches that start with c_test_prefix and is executable.  Add those files
# to a list so they can be run later.
def _find_c_tests(current_dir, root_dir, c_tests):
    if _debug > 1:
        sys.stderr.write("Scanning %s, relative to %s, for c tests...\n" %
                         (current_dir, root_dir,))
    names = os.listdir(current_dir)
    for name in names:
        srcname = os.path.join(current_dir, name)
        try:
            if os.path.isdir(srcname):
                if "." in name:
                    # A directory with a "." in the name is not a valid
                    # Python path.
                    continue
                _find_c_tests(srcname, root_dir, c_tests)
            else:
                # is a file
                # See if it is a TestCase
                if _debug > 2:
                    sys.stderr.write("Check if %s is a c test..\n" %
                                     (srcname,))
                base = os.path.basename(srcname)
                if base[:len(c_test_prefix)] == c_test_prefix \
                       and os.access(srcname,os.X_OK) \
                       and (base[-3:] != ".py" or base[-4:] != ".pyc"):
                    _c_test_from_path(root_dir, srcname, c_tests)
        except (IOError, os.error), e:
            raise "_find_c_tests error", e
    return

# The "module" parameter is a python module name.
# (Ex: "mpx.ion.host._test_case_eth")  This routine does a python "import"
# of the named module and returns the name of the module as it appears
# in the symbol table.
#
# This routine is used (rather than the built-in "import" command of python)
# when the name of the module to be imported is not known until run-time.
#
def _import(module):
    command = compile('import ' + module, 'Import',  'exec')
    eval(command)
    return eval(module)

# This class acts as a "filter" to transform a stream.  Extra newlines
# are inserted so that output lines do not exceed 78 characters in length.
#
# The output stream is specified by the first parameter to the constructor.
# All text given to the _WrappingStream.write() method has the appropriate
# newlines inserted to limit the maximum line length, then the result is
# relayed on to the output stream.
#
# The maximum line length defaults to 78 characters but can be be changed
# using an optional named parameter to the constructor.
#
# The original purpose of this class was to make test output more readable
# within e-mail messages by limiting the line length.
#
class _WrappingStream:
    def __init__(self, stream, max_col=78):
        assert hasattr(stream,'write')
        self.stream = stream
        self.max_col = max_col
        self.column = 0
        return None
    def __getattr__(self, attr):
        return getattr(self.stream,attr)
    def write(self, text):
        # Cheesy, ugly, but good enough...
        i = text.rfind('\n')
        if i < 0:
            n = len(text)
        else:
            self.column = 0
            n = len(text) - i
        self.column += n
        if self.column > self.max_col:
            self.stream.write('\n')
            self.column = 0
        return self.stream.write(text)

##
# Run all tests defined by the testing modules contained in the
# "test_units" list.  See the comments above for additional information
# about "test_units" and how it is constructed.
#
# The output of all tests is written to the stream that is passed in
# as the argument.
#
# @fixme need to handle _import errors a little cleaner
#
def run_tests(test_units, stream=sys.stdout):
    assert hasattr(stream,'write')
    testSuite = unittest.TestSuite()
    for testCase in test_units:
        ## Do import of testCase stuff
        try:
            m = _import(testCase)
        except:
            stream.write(string.join(apply(format_exception, sys.exc_info())))
            continue
        ## create an instance of value of testCase
        ## create a new TestSuite that contains all tests
        ## defined in TestCase.  Each test should be start with
        ## with test.  For example, testSize, testExcept, testMax ...
        if hasattr(m,'TestCase'):
            i = m.TestCase
            s = unittest.makeSuite(i, 'test')
            testSuite.addTest( s  )
        else:
            stream.write('WARNING:...Module: ' + str(m) +
                         'does not have a class TestCase\n')
    stream.write("Running Test Suite containing %d test fixtures:\n" %
                 len(test_units))
    global _verbosity
    global _descriptions
    testRunner = unittest.TextTestRunner(stream,_descriptions,_verbosity)
    testRunner.run(testSuite)
    return

##
# Run all C unit tests in the 'c_tests' list
#
# The output of all tests is written to the stream that is passed in
# as the argument.
#
# The tests are run by doing a `cd` to the directory the test is in, 
# then executing the test and waiting for it to finish.  All results are 
# printed to 'stream'
def run_c_tests(c_tests, stream=sys.stdout):
    assert hasattr(stream,'write')
    old_pwd = os.path.abspath(os.curdir) # remember old pwd
    for test_case in c_tests:
        print "Running tests from: " + test_case
        err_str = ""
        out_str = ""
        ret = (0,0)
        os.chdir(os.path.dirname(test_case))
        p = popen2.Popen3(test_case, 1) # use stderr
        while 1:
            err_str += p.childerr.read()
            out_str += p.fromchild.read()
            try:
                # use waitpid, because p.wait() can cause problems!
                ret = os.waitpid(p.pid, os.WNOHANG)
            except:
                # Force a break, we're already done!
                ret = (p.pid, None)
            if ret[0] == p.pid:
                err_str += p.childerr.read()
                out_str += p.fromchild.read()
                break # done the test
        if ret != 0:
            #error occurred
            pass
        print out_str
        del(p)
    os.chdir(old_pwd) # go back to the old pwd
    return

_verbosity=1
_descriptions=0
_debug=0

def _MAIN(argv):
    """
%s [-l] [file ...]

  Run all the unittests in the framework and output a report.

  -h                      Display this help information.
  --help

  -l                      Do not actually run any tests.  Just print out
  --list_test_cases_only  the _test_case*.py modules that would have been
                          run.

  -v level                level == 1: Display a single character for each test
  --verbosity=level                   method that is run.  A period ('.')
                                      indicates success, an 'E' or 'F' indicate
                                      an error or failure, respectively.
                          level == 2: The name of each method and the full
                                      Python module path to the method is
                                      displayed immediately before running the
                                      test.  Upon completion, the word 'ok',
                                      'ERROR' or failure is displayed on the
                                      same line, after the 'in progress'
                                      elipsis.

  -D level                level == 1: Displays each _test_case being added
  --debug=level                       to the test suite.
                          level == 2: Level 1, plus displaying each directory
                                      being scanned for _test_case fixtures.
                          level == 3: Level 2, plus displaying each file
                                      being considerred for inclusion as a
                                      _test_case.
  
  file ...                An optional list of directories and files to search
                          for test cases.  If no file arguments are specified,
                          it defaults to the current project's root
                          and scans for all test cases in the project.
  NOTES:
    current proot         %s
"""
    import getopt
    # The following variable will (ultimately) contain a list of all
    # test modules in the source tree.  The _find_test_units procedure
    # walks down through the source tree searching for files whose name
    # matches the glob pattern "_test_case*.py".  For each such file
    # found, the ".py" suffix is removed, all "/" characters in the
    # path are converted into "." and the resulting module name is
    # added to test_units.
    #
    global _verbosity
    test_units = []
    c_test_list = []
    list_test_cases_only = 0
    opts, args = getopt.getopt(argv[1:],
                               'u?hr:lv:dD:',
                               ['help','root=','list_test_cases_only',
                                'debug=','descriptions',
                                'verbosity='])
    root_dir = argv[0]                   # ... broadway/tools/unittester.py
    root_dir = os.path.dirname(root_dir) # ... broadway/tools/
    root_dir = os.path.dirname(root_dir) # ... broadway/
    root_dir = os.path.realpath(root_dir)
    search_list = []
    start_dir = os.getcwd()
    options = []
    for opt,arg in opts:
        options.append(opt)
    if len(opts) > 0:
        for opt,arg in opts:
            if opt in ('-u','--help', '-?', '-h'):
                command = os.path.basename(argv[0])
                if command[-3:] == ".py":
                    command = command[:-3]
                elif command[-4:] == ".pyc":
                    command = command[:-4]                    
                os.system("""cat <<EOF | less
%s
EOF""" % _MAIN.__doc__ % (command, root_dir))
                return 1
            elif opt in ('-l','--list_test_cases_only'):
                list_test_cases_only = 1
            elif opt in ('-v','--verbosity'):
                _verbosity = int(arg)
            elif opt in ('-D','--debug'):
                _debug = int(arg)
            elif opt in ('-d','--descriptions'):
                _descriptions = 1
    # Process arguments.
    for arg in args:
        search_list.append(os.path.realpath(os.path.join(start_dir, arg)))
    stdout = _WrappingStream(sys.stdout)
    # sys.path.insert(0,root_dir) 
    if not list_test_cases_only:
        stdout.write('Project build root: %s\n' % root_dir)
    os.chdir(root_dir)
    if not search_list:
        search_list.append(root_dir)
    for dir_or_file in search_list:
        if os.path.exists(dir_or_file):
            if os.path.isdir(dir_or_file):
                _find_test_units(dir_or_file, root_dir, test_units)
                _find_c_tests(dir_or_file, root_dir, c_test_list)
            elif os.path.isfile(dir_or_file):
                _test_module_from_file(root_dir, dir_or_file, test_units)
            else:
                raise 'asdfasdfasdfsdfasdfa'
        else:
            stdout.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                         "!!!!!!!!!!!!!!!!!!!!!\nWARNING:  " +
                         (_INVALID_TEST_UNIT_OR_DIRECTORY % dir_or_file) +
                         "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                         "!!!!!!!!!!!!!!!!!!!!!\n")
    if list_test_cases_only:
        for tu in test_units:
            stdout.write(str(tu) + '\n')
        for tu in c_test_list:
            stdout.write(tu + '\n')
    else:
        run_tests(test_units, stdout)
        run_c_tests(c_test_list) 
    return 0

def MAIN(argv=sys.argv):
    from mpx_test import destroy_testing_directories
    try:
        return _MAIN(argv)
    finally:
        destroy_testing_directories()
    
if __name__ == "__main__":
    result = MAIN(sys.argv)
