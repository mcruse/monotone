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
from mpx_test import DefaultTestFixture

import sys
import traceback
import StringIO

from mpx.lib.exceptions import *

def stack1(klass, *args):
    raise klass(*args)

for i in xrange(2,101):
    definition = compile("""\
def stack%(current)r(klass, *args):
    return stack%(previous)r(klass, *args)
"""
                      % {'current':i, 'previous':i-1},
                      '%s_%r' % (__name__, i),
                      'exec')
    exec definition

def string1(arg):
    raise arg

for i in xrange(2,101):
    definition = compile("""\
def string%(current)r(arg):
    return string%(previous)r(arg)
"""
                      % {'current':i, 'previous':i-1},
                      '%s_%r' % (__name__, i),
                      'exec')
    exec definition

class TestCase(DefaultTestFixture):
    def test_decorated_exception_1(self):
        try:
            stack1(EAttributeError, 'Invoked stack1')
        except:
            e = decorated_exception(*sys.exc_info())
        self.assert_hasattr(e, 'exception')
        self.assert_hasattr(e, 'traceback')
        self.assert_comparison(
            'e.exception.args', '==', "('Invoked stack1',)"
            )
        self.assert_comparison('len(e.traceback)', '==', '2')
        self.assert_comparison('e.nickname', '==', "'EAttributeError'")
        self.assert_comparison(
            'e.name', '==', "'mpx.lib.exceptions.EAttributeError'"
            )
        line1 = e.traceback[0]
        return
    def test_decorated_exception_2(self):
        try:
            stack100(Exception, 'Invoked stack100')
        except:
            e = decorated_exception(*sys.exc_info())
        self.assert_comparison(
            'e.exception.args', '==', "('Invoked stack100',)"
            )
        # len is 65 because the actual traceback was truncated at
        # 64 and then the 'Traceback terminated due to 64 entry limit'
        # line was appended.
        self.assert_comparison('len(e.traceback)', '==', '65')
        return
    def test_current_decoration_1(self):
        try:
            # The invokation is a stack entry, and then stack63()
            # generates 63 more for a total of 64 stack entries.
            stack63(MpxException, 'Invoked stack63')
        except:
            e = current_exception()
        self.assert_comparison(
            'e.exception.args', '==', "('Invoked stack63',)"
            )
        self.assert_comparison('len(e.traceback)', '==', '64')
        self.assert_comparison('e.nickname', '==', "'MpxException'")
        self.assert_comparison(
            'e.name', '==', "'mpx.lib.exceptions.MpxException'"
            )
        return
    def test_current_decoration_2(self):
        try:
            stack1(ENoSuchName, 'bob')
        except:
            e = current_exception()
        self.assert_comparison('e.nickname', '==', "'ENoSuchName'")
        self.assert_comparison(
            'e.name', '==', "'mpx.lib.exceptions.ENoSuchName'"
            )
        return
    ##
    # @return The output of traceback.print_exc() as a string.
    def print_exc(self):
        s = StringIO.StringIO()
        traceback.print_exc(None,s)
        return s.getvalue()
    ##
    # @return The DecoratedException returned by
    #         mpx.lib.exceptions.current_exception() converted into a string
    #         string via str().
    def str_decorated(self):
        return str(current_exception())
    ##
    # @return The list [self.print_exc(), self.str_decorated()] which should
    #         be identical.
    def exception_results(self, call, *args):
        results = []
        for converter in (self.print_exc, self.str_decorated):
            try:
                call(*args)
            except:
                results.append(converter())
        return results
    def test_current_decoration_3(self):
        print_exc, str_decorated = self.exception_results(
            stack10, ENotImplemented, 'stack10(ENotImplemented)'
            )
        self.assert_comparison(repr(print_exc), '==', repr(str_decorated))
        return
    def test_current_deprecated(self):
        print_exc, str_decorated = self.exception_results(
            string10, 'deprecated string exception'
            )
        self.assert_comparison(repr(print_exc), '==', repr(str_decorated))
        return
