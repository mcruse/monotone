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
"""
_test_case_protocompiler.py
"""

import os
import sys

import gdhelpers as gd
import protocompiler

from mpx_test import DefaultTestFixture, main
from mpx import properties
from protocompiler import ProtoCompiler

def add_path(newpath):
    # Ensure that newpath is in the system path so that import will find it
    # to facilitate testing our newly generated classes.
    if not newpath in sys.path:
        sys.path.append(newpath)

class TestCase(DefaultTestFixture): 
    def setUp(self):
        DefaultTestFixture.setUp(self)
        add_path(properties.TEMP_DIR)
    #
    def test_strip_comments(self):
        pc = ProtoCompiler()

        test_data = (('#', ''),
                     ('#  ', ''),
                     ('', ''),
                     ('                 ', ''),
                     ('#aaaa', ''),
                     ('}#comment', '}'),
                     ('} # comment', '}'),
                     )

        for x in test_data:
            line,exp_res = x
            res = pc.strip_comments(line)
            assert res == exp_res, 'Expected result of "%s", got result of "%s" for "%s".' % (exp_res,
                                                                                              res,
                                                                                              line)
    #
    def test_case_removeExtraneousWhitespace(self):
        tdata = (('this=1 what=2', 'this=1 what=2'),
                 ('this = 2 what = 3', 'this=2 what=3'),
                 ('this   =   4    what=5', 'this=4 what=5'),
                 ('this = 1 that', 'this=1 that'),
                 ('that this  =  1', 'that this=1'),
                 ('this = 1', 'this=1'),
                 ('that', 'that'),
                 )
        for x in tdata:
            ostr, exp_res = x
            res = protocompiler.removeExtraneousWhitespace(ostr)
            assert res == exp_res, "Expected result of %s, but got result of %s for %s" % (exp_res, res, ostr)
    #
    def test_case_parseOptions(self):
        tdata = (('this=1 that=2', {'this':'1', 'that':'2'}),
                 ('this = 1 that', {'this':'1', 'that':1}),
                 ('this =  1', {'this':'1'}),
                 ('that', {'that':1}),
                 )
        for x in tdata:
            ostr,exp_res = x
            res = protocompiler.parseOptions(ostr)
            assert res == exp_res, "Expected result of %s, but got result of %s for %s" % (str(exp_res),
                                                                                           str(res),
                                                                                           str(ostr))
    #
    def test_case_parseOptionsList(self):
        tdata = ((['width=10'], {'width':'10'}),
                 (['width=10', 'length=15'], {'width':'10', 'length':'15'}),
                 )
        for x in tdata:
            olist,exp_res = x
            res = protocompiler.parseOptionsList(olist)
            assert res == exp_res, "Expected result of %s, but got result of %s for %s" % (str(exp_res),
                                                                                           str(res),
                                                                                           str(olist))
    #
    def test_case_singlebyte(self):
        lines = "" \
                "# Single byte Class\n" \
                "class singlebyte {\n" \
                "   uint8 preamble = 0xAA;\n" \
                "   uint8 data;\n" \
                "   uint8 postamble = 0xFF;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'single_byte.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['singlebyte'], "Classnames != ['singlebyte']"

        my_class = pc._getClass('singlebyte')

        assert my_class.isPackCompatible() == 1, "Class should be pack compatible."
        exp_spec = '<B<B<B'
        assert my_class.packSpec() == exp_spec, "Class spec should be '%s', got '%s'." % (exp_spec,
                                                                                          my_class.packSpec())
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 3, "Width should be 3, got %d." % my_class.getWidth()

        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "singlebyte.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import singlebyte

        obj = singlebyte.singlebyte()

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 1, "isPackCompatible() should be 1"
        assert obj.packSpec() == "<B<B<B", "packSpec() should be <B<B<B"
        assert obj.getWidth() == 3, "Width should be 3, got %d" % obj.getWidth()
        assert obj.getNumItems() == 3, "NumItems should be 3, got %d" % obj.getNumItems()

        # @fixme: May make sense to do some similar tests to test_case_gdhelpers here.
    #
    def test_case_insertline(self):
        lines = "" \
                "# Import a standard framework library.\n" \
                "insert from mpx import properties\n" \
                "insert #\n" \
                "insert # This is a comment that should not be stripped\n" \
                "insert temp_dir = properties.TEMP_DIR\n" \
                "#\n" \
                "# Single byte Class\n" \
                "class singlebyte {\n" \
                "   uint8 preamble = 0xAA;\n" \
                "   uint8 data;\n" \
                "   uint8 postamble = 0xFF;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'single_byte_with_insert.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "singlebytewithinsert.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import singlebytewithinsert

        obj = singlebytewithinsert.singlebyte()

        # Prove that the import (in the insert line above) worked.
        assert singlebytewithinsert.temp_dir == properties.TEMP_DIR, "Properties apparently not properly imported"
    #
    def test_case_multiple_classes(self):
        lines = "" \
                "# Single byte Class\n" \
                "class singlebyte {\n" \
                "   uint8 preamble = 0xAA;\n" \
                "   uint8 data;\n" \
                "   uint8 postamble = 0xFF;\n" \
                "}\n" \
                "\n" \
                "class doublebyte {\n" \
                "   uint8 preamble = 0xAA;\n" \
                "   uint8 data1;\n" \
                "   uint8 data2;\n" \
                "   uint8 postamble = 0xFF;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'mutiples.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        #print pc.classnames

        assert pc.classnames == ['singlebyte', 'doublebyte'], "Classnames != ['singlebyte', 'doublebyte']"

        my_class = pc._getClass('singlebyte')

        #print 'Got class of %s.' % str(my_class)

        assert my_class.isPackCompatible() == 1, "Class should be pack compatible."
        exp_spec = '<B<B<B'
        assert my_class.packSpec() == exp_spec, "Class spec should be '%s', got '%s'." % (exp_spec,
                                                                                          my_class.packSpec())
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 3, "Width should be 3, got %d." % my_class.getWidth()

        my_class = pc._getClass('doublebyte')

        assert my_class.isPackCompatible() == 1, "Class should be pack compatible."
        exp_spec = '<B<B<B<B'
        assert my_class.packSpec() == exp_spec, "Class spec should be '%s', got '%s'." % (exp_spec,
                                                                                          my_class.packSpec())
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 4, "Width should be 4, got %d." % my_class.getWidth()

        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "multiples.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import multiples

        obj = multiples.singlebyte()

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 1, "isPackCompatible() should be 1"
        assert obj.packSpec() == "<B<B<B", "packSpec() should be <B<B<B"
        assert obj.getWidth() == 3, "Width should be 3, got %d" % obj.getWidth()
        assert obj.getNumItems() == 3, "NumItems should be 3, got %d" % obj.getNumItems()

        obj = multiples.doublebyte()

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 1, "isPackCompatible() should be 1"
        assert obj.packSpec() == "<B<B<B<B", "packSpec() should be <B<B<B<B"
        assert obj.getWidth() == 4, "Width should be 4, got %d" % obj.getWidth()
        assert obj.getNumItems() == 4, "NumItems should be 4, got %d" % obj.getNumItems()
    #
    def test_case_allints(self):
        lines = "" \
                "# All Ints Class\n" \
                "class allints {\n" \
                "   uint8    data01;\n" \
                "   beuint8  data02;\n" \
                "   int8     data03;\n" \
                "   uint8    data04;\n" \
                "" \
                "   uint16   data05;\n" \
                "   beuint16 data06;\n" \
                "   int16    data07;\n" \
                "   uint16   data08;\n" \
                "" \
                "   uint32   data09;\n" \
                "   beuint32 data10;\n" \
                "   int32    data11;\n" \
                "   uint32   data12;\n" \
                "" \
                "   uint64   data13;\n" \
                "   beuint64 data14;\n" \
                "   int64    data15;\n" \
                "   uint64   data16;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'all_ints.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['allints'], "Classnames != ['allints']"
        
        my_class = pc._getClass('allints')
        
        #print 'Got class of %s.' % str(my_class)
        
        assert my_class.isPackCompatible() == 1, "Class should be pack compatible."
        exp_spec = '<B>B<b<B<H>H<h<H<L>L<l<L<Q>Q<q<Q'
        assert my_class.packSpec() == exp_spec, "Class spec should be '%s', got '%s'." % (exp_spec,
                                                                                          my_class.packSpec())
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 60, "Width should be 60, got %d." % my_class.getWidth()

        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "allints.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import allints

        obj = allints.allints()

        #print 'Dir of new object: %s' % str(dir(obj))

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 1, "isPackCompatible() should be 1"
        assert obj.packSpec() == exp_spec, "packSpec() should be %s" % exp_spec
        assert obj.getWidth() == 60, "Width should be 60, got %d" % obj.getWidth()
        assert obj.getNumItems() == 16, "NumItems should be 16, got %d" % obj.getNumItems()
    #
    def test_case_dup_item_names(self):
        lines = "" \
                "# Dup Name Class\n" \
                "class dupname {\n" \
                "   uint8    data01;\n" \
                "   beuint8  data01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'dup_name.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        # We should catch an exception when trying to parse this file.
        didcatch = 0
        try:
            pc.parseFile(fname)
        except:
            didcatch = 1
        if not didcatch:
            raise "Expected to catch an exception when parsing dupname class, but did not"

    def test_case_float1(self):
        lines = "" \
                "# Float Class\n" \
                "class float1 {\n" \
                "   float1   float01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'float1.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['float1'], "Classnames != ['float1']"
        
        my_class = pc._getClass('float1')
        
        assert my_class.isPackCompatible() == 1, "Class should be pack compatible."
        exp_spec = 'f'
        assert my_class.packSpec() == exp_spec, "Class spec should be '%s', got '%s'." % (exp_spec,
                                                                                          my_class.packSpec())
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 4, "Width should be 4, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "float1.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import float1

        obj = float1.float1()

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 1, "isPackCompatible() should be 1"
        assert obj.packSpec() == "f", "packSpec() should be f"
        assert obj.getWidth() == 4, "Width should be 4, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()
    #
    def test_case_double1(self):
        lines = "" \
                "# Float Class\n" \
                "class double1 {\n" \
                "   double1   double01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'double1.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['double1'], "Classnames != ['double1']"
        
        my_class = pc._getClass('double1')

        assert my_class.isPackCompatible() == 1, "Class should be pack compatible."
        exp_spec = 'd'
        assert my_class.packSpec() == exp_spec, "Class spec should be '%s', got '%s'." % (exp_spec,
                                                                                          my_class.packSpec())
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 8, "Width should be 8, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "double1.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import double1

        obj = double1.double1()

        #print 'Dir of new object: %s' % str(dir(obj))

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 1, "isPackCompatible() should be 1"
        assert obj.packSpec() == "d", "packSpec() should be d"
        assert obj.getWidth() == 8, "Width should be 8, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()
    #
    def test_case_pad(self):
        lines = "" \
                "# Pad Class\n" \
                "class testpad {\n" \
                "   width=10 pad pad01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'pad.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['testpad'], "Classnames != ['testpad']"
        
        my_class = pc._getClass('testpad')
        
        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 10, "Width should be 10, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "testpad.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testpad

        obj = testpad.testpad()

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 10, "Width should be 10, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()    
    #
    def test_case_fbuffer(self):
        lines = "" \
                "# Fixed Buffer Class\n" \
                "class testfbuffer {\n" \
                "   width=7 fbuffer fbuffer01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'fbuffer.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['testfbuffer'], "Classnames != ['testfbuffer']"
        
        my_class = pc._getClass('testfbuffer')
        
        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 7, "Width should be 7, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "testfbuffer.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testfbuffer

        obj = testfbuffer.testfbuffer()

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 7, "Width should be 7, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()
    #
    def test_case_string(self):
        lines = "" \
                "# String Class\n" \
                "class teststring {\n" \
                "   width=13 string string01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'string.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['teststring'], "Classnames != ['teststring']"
        
        my_class = pc._getClass('teststring')
        
        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 13, "Width should be 13, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "teststring.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import teststring

        obj = teststring.teststring()

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 13, "Width should be 13, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()
    #
    def test_case_vbuffer1(self):
        lines = "" \
                "# Variable Buffer 1 Class\n" \
                "class testvbuffer1 {\n" \
                "   vbuffer1 vbuffer01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'vbuffer1.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['testvbuffer1'], "Classnames != ['testvbuffer1']"
        
        my_class = pc._getClass('testvbuffer1')
        
        #print 'Got class of %s.' % str(my_class)

        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 0, "Width should not be fixed."
        assert my_class.getWidth() == 0, "Width should be 0, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "testvbuffer1.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        pyfilename = os.path.join('/tmp', "testvbuffer1.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testvbuffer1

        obj = testvbuffer1.testvbuffer1()

        assert obj.isFixedWidth() == 0, "isFixedWidth() should be 0"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 0, "Width should be 0, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()

        # Object has only one item, run some tests against that item
        item_obj = obj.items[0]

        width = item_obj.getWidth()
        assert width == 1, "width should be 1, got %s" % str(width)
    #
    def test_case_vbuffer2(self):
        lines = "" \
                "# Variable Buffer 2 Class\n" \
                "class testvbuffer2 {\n" \
                "   vbuffer2 vbuffer01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'vbuffer2.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['testvbuffer2'], "Classnames != ['testvbuffer2']"
        
        my_class = pc._getClass('testvbuffer2')
        
        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 0, "Width should not be fixed."
        assert my_class.getWidth() == 0, "Width should be 0, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "testvbuffer2.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testvbuffer2

        obj = testvbuffer2.testvbuffer2()

        assert obj.isFixedWidth() == 0, "isFixedWidth() should be 0"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 0, "Width should be 0, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()

        # Object has only one item, run some tests against that item
        item_obj = obj.items[0]

        width = item_obj.getWidth()
        assert width == 2, "width should be 2, got %s" % str(width)
    #
    def test_case_levbuffer2(self):
        lines = "" \
                "# Little-Endian Variable Buffer 2 Class\n" \
                "class testlevbuffer2 {\n" \
                "   levbuffer2 levbuffer01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'levbuffer2.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['testlevbuffer2'], "Classnames != ['testlevbuffer2']"
        
        my_class = pc._getClass('testlevbuffer2')
        
        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 0, "Width should not be fixed."
        assert my_class.getWidth() == 0, "Width should be 0, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "testlevbuffer2.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testlevbuffer2

        obj = testlevbuffer2.testlevbuffer2()

        assert obj.isFixedWidth() == 0, "isFixedWidth() should be 0"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 0, "Width should be 0, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()

        # Object has only one item, run some tests against that item
        item_obj = obj.items[0]

        width = item_obj.getWidth()
        assert width == 2, "width should be 2, got %s" % str(width)
    #
    def test_case_bevbuffer2(self):
        lines = "" \
                "# Big-Endian Variable Buffer 2 Class\n" \
                "class testbevbuffer2 {\n" \
                "   bevbuffer2 bevbuffer01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'bevbuffer2.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['testbevbuffer2'], "Classnames != ['testbevbuffer2']"
        
        my_class = pc._getClass('testbevbuffer2')
        
        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 0, "Width should not be fixed."
        assert my_class.getWidth() == 0, "Width should be 0, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        pyfilename = os.path.join(properties.TEMP_DIR, "testbevbuffer2.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testbevbuffer2

        obj = testbevbuffer2.testbevbuffer2()

        assert obj.isFixedWidth() == 0, "isFixedWidth() should be 0"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 0, "Width should be 0, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()

        # Object has only one item, run some tests against that item
        item_obj = obj.items[0]
        
        width = item_obj.getWidth()
        assert width == 2, "width should be 2, got %s" % str(width)

        os.remove(pyfilename)
    #
    def _test_case_dbuffer(self):
        lines = "" \
                "# Dynamic Buffer Class\n" \
                "class testdbuffer {\n" \
                "   dbuffer dbuffer01;\n" \
                "}\n"

        pc = ProtoCompiler()

        x = protocompiler.DynamicBufferItem('dbuffer', 'mydbuffer', None)

        fname = os.path.join(properties.TEMP_DIR, 'dbuffer.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        #print lines

        pc.parseFile(fname)

        assert pc.classnames == ['testdbuffer'], "Classnames != ['testdbuffer']"
        
        my_class = pc._getClass('testdbuffer')
        
        #print 'Got class of %s.' % str(my_class)

        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 0, "Width should not be fixed."
        assert my_class.getWidth() == 0, "Width should be 0, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        #print "Got code of:"
        #print c

        pyfilename = os.path.join(properties.TEMP_DIR, "testdbuffer.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testdbuffer

        obj = testdbuffer.testdbuffer()

        #print 'Got object of: %s' % str(obj)
        #print 'Dir of new object: %s' % str(dir(obj))

        assert obj.isFixedWidth() == 0, "isFixedWidth() should be 0"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 0, "Width should be 0, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()

        # Object has only one item, run some tests against that item
        item_obj = obj.items[0]
        #print 'str', item_obj
        #print 'dir', dir (item_obj)

        #width = item_obj.getWidth()
        #assert width == 2, "width should be 2, got %s" % str(width)

        os.remove(pyfilename)
    #
    def test_case_nested_fbuffer_class(self):
        lines = "" \
                 "# Single byte Class\n" \
                "class singlebyte {\n" \
                "   uint8 preamble = 0xAA;\n" \
                "   uint8 data;\n" \
                "   uint8 postamble = 0xFF;\n" \
                "}\n" \
                "# Fixed Buffer Class\n" \
                "class testnestedfbuffer {\n" \
                "   width=3 class=singlebyte fbuffer fbuffer01;\n" \
                "}\n"

        pc = ProtoCompiler()

        fname = os.path.join(properties.TEMP_DIR, 'nestedfbuffer.class')

        f = open(fname, 'w')
        f.write(lines)
        f.close()

        pc.parseFile(fname)

        assert pc.classnames == ['singlebyte', 'testnestedfbuffer'], "Classnames != ['singlebyte', 'testnestedfbuffer']"
        
        my_class = pc._getClass('testnestedfbuffer')
        
        assert my_class.isPackCompatible() == 0, "Class should be not pack compatible."
        assert my_class.isFixedWidth() == 1, "Width should be fixed."
        assert my_class.getWidth() == 3, "Width should be 3, got %d." % my_class.getWidth()
        
        c = pc.emitCode()

        #print "Got code of:"
        #print c

        pyfilename = os.path.join(properties.TEMP_DIR, "testnestedfbuffer.py")

        f = open(pyfilename, 'w')
        f.write(c)
        f.close()

        # Now try to import it.
        import testnestedfbuffer

        obj = testnestedfbuffer.testnestedfbuffer()

        #print 'Got object of: %s' % str(obj)
        #print 'Dir of new object: %s' % str(dir(obj))

        #print obj.getChildren()
        #print obj.findChildByName('singlebyte')

        assert obj.isFixedWidth() == 1, "isFixedWidth() should be 1"
        assert obj.isPackCompatible() == 0, "isPackCompatible() should be 0"
        assert obj.getWidth() == 3, "Width should be 3, got %d" % obj.getWidth()
        assert obj.getNumItems() == 1, "NumItems should be 1, got %d" % obj.getNumItems()

        #print 'Items:'
        #for x in obj.items:
        #    print ' %s' % str(x)


#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
        
