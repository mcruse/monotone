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

from mpx.lib.xmlrpclib import dumps

from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ETimeout

class TestCase(DefaultTestFixture):
    class Int(int):
        pass
    class Long(long):
        pass
    class Float(float):
        pass
    class Dict(dict):
        pass
    class List(list):
        pass
    class Tuple(tuple):
        pass
    class String(str):
        pass
    # Regex would be better/more flexible...
    # @fixme test StreamingTupleWithCallback -> array
    SIMPLE_TESTS = (
        # {"one":1} -> struct
        ({"one":1},
         '<params>\n<param>\n<value><struct>\n<member>\n<name>one</name>\n'
         '<value><int>1</int></value>\n</member>\n</struct></value>\n'
         '</param>\n</params>\n'),
        # Dict({"two":2}) -> struct
        (Dict({"two":2}),
         '<params>\n<param>\n<value><struct>\n<member>\n<name>two</name>\n'
         '<value><int>2</int></value>\n</member>\n</struct></value>\n'
         '</param>\n</params>\n'),
        # 3.0 -> double
        (3.0,
         '<params>\n<param>\n<value><double>3.0</double></value>\n</param>\n'
         '</params>\n'),
        # Float(4.0) -> double
        (Float(4.0),
         '<params>\n<param>\n<value><double>4.0</double></value>\n</param>\n'
         '</params>\n'),
        # 5 -> int
        (5, '<params>\n<param>\n<value><int>5</int></value>\n</param>\n'
         '</params>\n'),
        # Int(6) -> int
        (Int(6), '<params>\n<param>\n<value><int>6</int></value>\n</param>\n'
         '</params>\n'),
        # [7] -> array
        ([7],
         '<params>\n<param>\n<value><array><data>\n'
         '<value><int>7</int></value>\n</data></array></value>\n</param>\n'
         '</params>\n'),
        # List([8]) -> array
        (List([8]),
         '<params>\n<param>\n<value><array><data>\n'
         '<value><int>8</int></value>\n</data></array></value>\n</param>\n'
         '</params>\n'),
        # 9L -> int
        (9L, '<params>\n<param>\n<value><int>9</int></value>\n</param>\n'
         '</params>\n'),
        # Long(10) -> int
        (Long(10), '<params>\n<param>\n<value><int>10</int></value>\n</param>\n'
         '</params>\n'),
        # 'eleven' -> string
        ('eleven',
         '<params>\n<param>\n<value><string><![CDATA[eleven]]></string></value>'
         '</param>\n</params>\n'),
        # String('twelve') -> string
        (String('twelve'),
         '<params>\n<param>\n<value><string><![CDATA[twelve]]></string></value>'
         '</param>\n</params>\n'),
        # (13,) -> tuple
        ((13,),
         '<params>\n<param>\n<value><array><data>\n'
         '<value><int>13</int></value>\n</data></array></value>\n</param>\n'
         '</params>\n'),
        # Tuple((14,)) -> tuple
        (Tuple((14,)),
         '<params>\n<param>\n<value><array><data>\n'
         '<value><int>14</int></value>\n</data></array></value>\n</param>\n'
         '</params>\n'),
        # Exceptions -> string
        (Exception('this is an exception'),
         "<params>\n<param>\n<value><string><![CDATA["
         "error: Exception('this is an exception',)"
         "]]></string></value></param>\n</params>\n"),
        (OverflowError('long int exceeds XML-RPC limits'),
         "<params>\n<param>\n<value><string><![CDATA["
         "error: OverflowError('long int exceeds XML-RPC limits',)"
         "]]></string></value></param>\n</params>\n"),
        (ENoSuchName('/bogus/path'),
         "<params>\n<param>\n<value><string><![CDATA["
         "error: ENoSuchName('/bogus/path',)"
         "]]></string></value></param>\n</params>\n"),
        (ETimeout(),
         "<params>\n<param>\n<value><string><![CDATA["
         "error: ETimeout()"
         "]]></string></value></param>\n</params>\n"),
        # 2147483647L -> int
        (2147483647L,
         '<params>\n<param>\n<value><int>2147483647</int></value>\n</param>\n'
         '</params>\n'),
        # 2147483648L -> double (coerced)
        (2147483648L,
         '<params>\n<param>\n<value><double>2147483648.0</double></value>\n'
         '</param>\n</params>\n'),
        # Long(2147483649L) -> double (coerced)
        (2147483649L,
         '<params>\n<param>\n<value><double>2147483649.0</double></value>\n'
         '</param>\n</params>\n'),
        )
    def test_simple_conversions(self):
        for value, valid_result in self.SIMPLE_TESTS:
            result = dumps((value,))
            self.assert_comparison(repr(result), '==', repr(valid_result))
        return
