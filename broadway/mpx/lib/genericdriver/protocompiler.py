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
import sys
import os

debug = 0

PROGRAM_VER = '$Revision: 20101 $'
version = PROGRAM_VER.replace( '$Revision: ', '' )[:-2]
 
# Takes a list of options parameters and parses them into a dictionary.
# The parameters can take the form of:
# OPTNAME=OPTVALUE
# or
# BOOLOPT
def parseOptionsList(optlist):
    retdict = {}
    #
    for x in optlist:
        opt = x.split('=')
        if len(opt) == 1:
            # Must be a boolean parameter.
            keyname = opt[0]
            keyval = 1
        elif len(opt) == 2:
            keyname = opt[0]
            keyval = opt[1]
        else:
            raise "Got unrecognized option string of %s (problem clause around %s)" % (optstr, x)
        #
        retdict[keyname] = keyval
    #
    return retdict
#
# Takes a number of options parameters and parses them into a dictionary.
# The parameters can take the form of:
# OPTNAME=OPTVALUE
# or
# OPTNAME = OPTVALUE
def parseOptions(optstr):
    retdict = {}
    #
    optstr = removeExtraneousWhitespace(optstr)
    #
    opts = optstr.split(' ')
    #
    for x in opts:
        opt = x.split('=')
        if len(opt) == 1:
            # Must be a boolean parameter.
            keyname = opt[0]
            keyval = 1
        elif len(opt) == 2:
            keyname = opt[0]
            keyval = opt[1]
        else:
            raise "Got unrecognized option string of %s (problem clause around %s)" % (optstr, x)
        #
        retdict[keyname] = keyval
    #
    return retdict

def removeExtraneousWhitespace(optstr):
    retstr = ''
    topts = optstr.split()
    opts = []
    for x in topts:
        if x == '':
            continue
        strind = x.find('=')
        if strind == -1 or x == '=':
            opts.append(x)
        else:
            y = x.split('=')
            opts.append(y[0])
            opts.append('=')
            opts.append(y[1])
    # States are 0 - in between clauses or at the start of the string.
    #            1 - first part of clause found (keyname)
    #            2 - equal sign found
    #            3 - second part of clause found (keyval)
    state = 0
    for x in opts:
        if x == '':
            continue
        if state == 0:
            keyname = None
            keyval = None
            keyname = x
            state = 1
            continue
        elif state == 1:
            if x == '=':
                state = 2
            else:
                # Must be a boolean parameter.
                if retstr:
                    retstr += ' '
                retstr += keyname
                keyname = x
                state = 1
            continue
        elif state == 2:
            keyval = x
            state = 3
            if retstr:
                retstr += ' '
            retstr += '%s=%s' % (keyname, keyval)
            state = 0
            continue
    if state == 1:
        # Must have had a trailing boolean parameter.
        if retstr:
            retstr += ' '
        retstr += keyname
    return retstr

class BaseItem:
    def __init__(self):
        self.initial_value = None
        self.pack_compatible = 0
        self.width_in_bytes = 0
        self.is_fixed_width = 0
        self.pack_spec = None
        self.type = None
        self.name = None
        self.gd_class_name = None
        self.width_is_pack = None
        self.width_pack_spec = None
        self.width_pack_len = None
        self.class_name = None
        self.class_from = None
    #
    def isPackCompatible(self):
        return self.pack_compatible
    #
    def isFixedWidth(self):
        return self.is_fixed_width
    #
    def getWidth(self):
        return self.width_in_bytes
    #
    def packSpec(self):
        return self.pack_spec
    #
    def __str__(self):
        rstr  = 'Item with type: %s' % str(self.type)
        rstr += ', name: %s' % str(self.name)
        rstr += ', is_fixed_width: %d' % self.is_fixed_width
        if self.width_in_bytes is None:
            rstr += ', width: None'
        else:
            rstr += ', width: %d' % self.width_in_bytes
        rstr += ', pack_compatible: %d' % self.pack_compatible
        if self.pack_compatible:
            rstr += ', pack_spec: %s' % self.pack_spec
        if self.initial_value:
            rstr += ', initial_value: %s' % self.initial_value
        if self.class_name:
            rstr += ', class_name: %s' % self.class_name
        return rstr
    #
    def getInitializationCode(self, ident):
        istr = ' '*ident
        icode = ''
        # If we have a child object, then build the code to instantiate the child object
        # so we can pass it in to our item.
        if self.class_name:
            icode += istr + 'child_obj = %s()\n' % self.class_name
      
        args = 'name="%s"' % self.name
        if self.isFixedWidth():
            args += ', width=%d' % self.getWidth()
        if self.initial_value:
            args += ', value=%s' % self.initial_value
        if self.pack_compatible:
            args += ', packspec="%s"' % self.pack_spec
            args += ', ispack=1'
        else:
            args += ', ispack=0'
        if self.width_is_pack:
            args +=', widthispack=1'
        else:
            args +=', widthispack=0'
        if self.width_pack_spec:
            args +=', widthpackspec="%s"' % self.width_pack_spec
        if self.width_pack_len:
            args +=', widthpacklen=%d' % self.width_pack_len
        if self.type:
            args += ', type="%s"' % self.type
        if self.class_name:
            args += ', child_object=child_obj'
        #
        icode += istr + 'x = gd.%s(%s)\n' % (self.gd_class_name, args)
        icode += istr + 'self.items.append(x)\n'
        return icode

# The format for this dictionary is:
# key = item_type
# value = tuple of width_in_bytes, is_pack_compatible_flag, pack_spec (or None)
#
int_mapping_dictionary = {
                          # 8-bit int values 
                          'uint8'    : (1, 1, '<B'),
                          'beuint8'  : (1, 1, '>B'),   # Sort of redundant
                          'int8'     : (1, 1, '<b'),
                          'beint8'   : (1, 1, '>b'),   # Sort of redundant
                          
                          # 16-bit int values
                          'uint16'   : (2, 1, '<H'),   # Default uint16 is little-endian
                          'beuint16' : (2, 1, '>H'),
                          'int16'    : (2, 1, '<h'),   # Default int16 is little-endian
                          'beint16'  : (2, 1, '>h'),

                          # 32-bit int values
                          'uint32'   : (4, 1, '<L'),   # Default uint32 is little-endian
                          'beuint32' : (4, 1, '>L'),
                          'int32'    : (4, 1, '<l'),   # Default int32 is little-endian
                          'beint32'  : (4, 1, '>l'),

                          # 64-bit int values
                          'uint64'   : (8, 1, '<Q'),   # Default uint64 is little-endian
                          'beuint64' : (8, 1, '>Q'),
                          'int64'    : (8, 1, '<q'),   # Default int64 is little-endian
                          'beint64'  : (8, 1, '>q'),
                         }

class GenericIntItem(BaseItem):
    def __init__(self, item_type, item_name, options):
        BaseItem.__init__(self)
        #
        # Presently no options are expected for integer types.
        assert options is None, "Error: Unexpected options specified for int type."
        #
        # All integer types are fixed width.
        self.is_fixed_width = 1
        #
        # Now set our relevant information based on our type.
        map_tuple = int_mapping_dictionary[item_type]
        #
        width, is_pack, pack_spec = map_tuple
        #
        self.type = item_type
        self.name = item_name
        self.width_in_bytes = width
        self.pack_compatible = is_pack
        self.pack_spec = pack_spec
        self.gd_class_name = 'IntItem'
    #
    def set_initial_value(self, value):
        # Note: May want to do some validation here.
        self.initial_value = value
        
# The format for this dictionary is:
# key = item_type
# value = tuple of width_in_bytes, is_pack_compatible_flag, pack_spec (or None)
#
# Note: @fixme:  May need to account for big-endian floats and doubles.
float_mapping_dictionary = {
                            'float1'   : (4, 1, 'f'),
                            'double1'  : (8, 1, 'd'),
                           }

class GenericFloatItem(BaseItem):
    def __init__(self, item_type, item_name, options):
        BaseItem.__init__(self)
        #
        # Presently no options are expected for float types.
        assert options is None, "Error: Unexpected options specified for float type."
        #
        # All float types are fixed width.
        self.is_fixed_width = 1
        #
        # Now set our relevant information based on our type.
        map_tuple = float_mapping_dictionary[item_type]
        #
        width, is_pack, pack_spec = map_tuple
        #
        self.type = item_type
        self.name = item_name
        self.width_in_bytes = width
        self.pack_compatible = is_pack
        self.pack_spec = pack_spec
        # Note: @fixme.  This could be consolidated with IntItem into a generic PackItem.
        self.gd_class_name = 'FloatItem'
    #
    def set_initial_value(self, value):
        # Note: May want to do some validation here.
        self.initial_value = value

class PadItem(BaseItem):
    def __init__(self, item_type, item_name, options):
        BaseItem.__init__(self)
        #
        if not options is None:
            opt_dict = parseOptionsList(options)
        else:
            opt_dict = {}
        #
        if debug > 4:
            print 'Options are: %s' % str(options)
            print 'Options dict is: %s' % str(opt_dict)
        #
        # For PadItem's a width parameter is optional.  Default to 1
        # if not present.
        if not opt_dict.has_key('width'):
            width = 1
        else:
            width = int(opt_dict['width'])
        #
        # All pads types are fixed width.
        self.is_fixed_width = 1
        #
        self.type = item_type
        self.name = item_name
        self.width_in_bytes = width
        self.gd_class_name = 'PadItem'
        
# The format for this dictionary is:
# key = item_type
# value = tuple of isfixedwidth, number_of_length_bytes, width_pack_spec
# Note: For items with isfixedwidth of 1 a width parameter is mandatory.
#       For items with isfixedwidth of 0, then the width is assumed to be
#       part of the data and represented by a pack specification, so the
#       width_pack_spec is required.
#
buffer_mapping_dictionary = {
                            'fbuffer'  :  (1, 0, None),
                            'string'   :  (1, 0, None),
                            'vbuffer1' :  (0, 1, 'B'),
                            'vbuffer2' :  (0, 2, '<H'),  # Default vbuffer2 is little-endian
                            'levbuffer2': (0, 2, '<H'),
                            'bevbuffer2': (0, 2, '>H'),
                            }
class GenericBufferItem(BaseItem):
    def __init__(self, item_type, item_name, options):
        BaseItem.__init__(self)
        #
        if not options is None:
            opt_dict = parseOptionsList(options)
        else:
            opt_dict = {}
        if debug > 2:
            print 'Options are: %s' % str(options)
            print 'Options dict is: %s' % str(opt_dict)
        #
        # Now set our relevant information based on our type.
        map_tuple = buffer_mapping_dictionary[item_type]
        #
        self.type = item_type
        self.name = item_name
        
        self.is_fixed_width = map_tuple[0]
        self.width_pack_len = map_tuple[1]
        self.width_pack_spec = map_tuple[2]
        
        if self.is_fixed_width:
            if not opt_dict.has_key('width'):
                raise "Error: width parameter must be specified for type: %s" % str(item_type)
            else:
                width = int(opt_dict['width'])
            self.width_is_pack = 0
        else:
            width = None
            self.width_is_pack = 1
        self.width_in_bytes = width

        # Check for optional parameters
        if opt_dict.has_key('class'):
            # @fixme: Should probably check to see if this is a valid
            #         parameter for this type of item.
            self.class_name = opt_dict['class']

        # @fixme: Should probably check to make sure that any mandatory options are set here.
        
        self.gd_class_name = 'BufferItem'
    #
    def set_initial_value(self, value):
        # Note: May want to do some validation here.
        self.initial_value = value

class DynamicBufferItem(BaseItem):
    def __init__(self, item_type, item_name, options):
        BaseItem.__init__(self)
        #
        if not options is None:
            opt_dict = parseOptionsList(options)
        else:
            opt_dict = {}
        #
        if debug > 2:
            print 'Options are: %s' % str(options)
            print 'Options dict is: %s' % str(opt_dict)
        #
        self.type = item_type
        self.name = item_name
        
        self.is_fixed_width = 0

        # Check for optional parameters
        if opt_dict.has_key('class'):
            self.class_name = opt_dict['class']

        # @fixme: Check for preamble and/or postamble parameters.

        # @fixme: Should probably check to make sure that mandatory options are set here.
        self.gd_class_name = 'DynamicBufferItem'
    #
    def set_initial_value(self, value):
        # Note: May want to do some validation here.
        self.initial_value = value

item_mapping_dictionary = {
                           'uint8':      GenericIntItem,
                           'beuint8':    GenericIntItem,
                           'int8':       GenericIntItem,
                           'beint8':     GenericIntItem,
                           #
                           'uint16':     GenericIntItem,
                           'beuint16':   GenericIntItem,
                           'int16':      GenericIntItem,
                           'beint16':    GenericIntItem,
                           #
                           'uint32':     GenericIntItem,
                           'beuint32':   GenericIntItem,
                           'int32':      GenericIntItem,
                           'beint32':    GenericIntItem,
                           #
                           'uint64':     GenericIntItem,
                           'beuint64':   GenericIntItem,
                           'int64':      GenericIntItem,
                           'beint64':    GenericIntItem,
                           #
                           'float1':     GenericFloatItem,
                           'double1':    GenericFloatItem,
                           #
                           'pad':        PadItem,
                           #
                           'fbuffer':    GenericBufferItem,
                           'string':     GenericBufferItem,
                           'vbuffer1':   GenericBufferItem,
                           'vbuffer2':   GenericBufferItem,
                           'levbuffer2': GenericBufferItem,
                           'bevbuffer2': GenericBufferItem,
                           #
                           'dbuffer':    DynamicBufferItem,
                          }

#   item_obj = createItemObject(item_type, item_name, initial_value, options)
def createItemObject(item_type, item_name, initial_value, options):
    if not item_mapping_dictionary.has_key(item_type):
        raise "Error: got unrecognized type of %s." % item_type
    item_class = item_mapping_dictionary[item_type]
    #print item_class
    try:
        item_obj = item_class(item_type, item_name, options)
    except:
        mstr  = 'Could not instantiate item object with: '
        mstr += 'item_type: %s - item_class: %s - ' % (str(item_type), str(item_class))
        mstr += 'item_name: %s - options: %s' % (str(item_name), str(options))
        print 'Got exception: %s' % mstr
        raise mstr
    #
    if initial_value:
        item_obj.set_initial_value(initial_value)
    #
    if debug > 3:
        print 'Got item object of %s.' % str(item_obj)
    #
    return item_obj
    

class ClassObject:
    def __init__(self, name):
        # Need to set this as appropriate
        self.is_finished = 0
        self.name = name
        self.item_objects = []
    #
    def addObject(self, item_object):
        self.item_objects.append(item_object)
    #
    def findObjectByName(self, item_name):
        for x in self.item_objects:
            if x.name == item_name:
                return x
        return None
    #
    def isPackCompatible(self):
        for x in self.item_objects:
            if not x.isPackCompatible():
                return 0
        return 1
    #
    def packSpec(self):
        pack_spec = ''
        for x in self.item_objects:
            if not x.isPackCompatible():
                raise "Error: Tried to get pack specification for class which is not pack compatible."
            pack_spec += x.packSpec()
        return pack_spec
    # 
    def isFixedWidth(self):
        for x in self.item_objects:
            if not x.isFixedWidth():
                return 0
        return 1
    #
    # Note: If one or more items is not fixed width, the width returned will be a
    #       minimum width.
    def getWidth(self):
        width = 0
        for x in self.item_objects:
            new_width = x.getWidth()
            if new_width:
                width += new_width
        return width
    #
    def __str__(self):
        rstr =  'Class with name: %s' % self.name
        rstr += ', isPackCompatible: %d' % self.isPackCompatible()
        if self.isPackCompatible():
            rstr += ', packSpec: %s' % self.packSpec()
        rstr += ', isFixedWidth: %d' % self.isFixedWidth()
        rstr += ', width: %d' % self.getWidth()
        itemnames = []
        for x in self.item_objects:
            itemnames.append(x.name)
        rstr += ', items: %s' % str(itemnames)
        return rstr
    #
    def emitCode(self):
        # Do some validation here.
        numitems = len(self.item_objects)
        #
        code = ""
        code += "class %s(gd.BaseGDClass):\n" % self.name
        code += "    def __init__(self):\n"
        code += "        gd.BaseGDClass.__init__(self)\n"
        code += "        #\n"
        code += "        self.name = '%s'\n" % self.name
        code += "        self._isFixed = %d\n" % self.isFixedWidth()
        code += "        self._width = %d\n" % self.getWidth()
        code += "        self._num_items = %d\n" % numitems
        code += "        self._isPackCompatible = %d\n" % self.isPackCompatible()
        if self.isPackCompatible():
            code += "        self._packSpec = '%s'\n" % self.packSpec()
        else:
            code += "        self._packSpec = None\n"
        code += "        #\n"
        code += "        # Code to create item objects.\n"
        code += "        self.items = []\n"
        for x in self.item_objects:
            code += "        #\n"
            item_initialization_code = x.getInitializationCode(8)
            code += item_initialization_code
            #code += "        #\n"
        code += "\n"
        return code


class ProtoCompiler:
    def __init__(self):
        self.classobjects = {}
        self.classnames = []
        self.insert_lines = []
        self.is_class = 0
        self.source = None
    #
    def _getClass(self, classname):
        if not self.classobjects.has_key(classname):
            return None
        return self.classobjects[classname]
    #
    # class start lines should look like:
    # class CLASSNAME {
    def handleClassStart(self, line, items):
        # First check to make sure we weren't already in the middle
        # of parsing a class.
        if self.is_class:
            raise "Error: Class start in the middle of another class: %s" % line
        # Now make sure that the line has the proper syntax
        if len(items) != 3:
            raise "Error: Extraneous characters after class statement: %s" % line
        if items[2] != '{':
            raise "Error: Opening squiggly brace not matched: %s" % line
        class_name = items[1]
        if debug > 2:
            print 'Started parsing class with name: %s' % class_name
        self.is_class = 1
        self.current_class = ClassObject(class_name)
    #
    # class end lines should look like:
    # }
    def handleClassEnd(self, line, items):
        # First check to make sure we were in the middle of parsing
        # a class.
        if not self.is_class:
            raise "Error: Class end without a class begin: %s" % line
        if len(items) != 1:
            raise "Error: Extraneous characters after class statement: %s" % line
        current_class_name = self.current_class.name
        self.classobjects[current_class_name] = self.current_class
        self.classnames.append(current_class_name)
        self.is_class = 0
        self.current_class = None
    #
    # insert lines should look like
    #  insert SOMEPYTHONCODEHERE
    def handleInsertLine(self, line):
        # insert_line should be everything past the "insert " at the beginning
        # of the command.  It is up to the developer to make sure that it is
        # proper Python code.
        insert_cmd = 'insert '
        strind = line.find(insert_cmd)
        insert_line = line[strind+len(insert_cmd):]
        self.insert_lines.append(insert_line)
    #
    # class definition lines should look like:
    # [OPTIONS] ITEMTYPE ITEMNAME [= ITEMVALUE];
    def handleClassDefinition(self, line, items):
        options = None
        initial_value = None
        # We had better be in the middle of parsing a class.
        if not self.is_class:
            raise "Error: Unrecoginized line when not parsing a class: %s" % line
        # The last character should be a semi-colon (;)
        if line[-1] != ';':
            raise "Error: Class definition line not terminated with a semi-colon: %s" % line
        line = line[:-1]
        #print line
        # Check for an item value clause
        items = line.split()
        lenitems = len(items)
        if lenitems > 3:
            if items[lenitems-2] == '=':
                initial_value = items[lenitems-1]
                if debug > 2:
                    print 'Found an initial value of %s' % initial_value
                # Remove the last two items (= INITIALVALUE)
                del(items[lenitems-1])
                del(items[lenitems-2])
                lenitems = len(items)
                if debug > 2:
                    print 'Items: ', items
        # Now the final two items should be the item type and the item name
        item_name = items[lenitems-1]
        item_type = items[lenitems-2]
        if debug > 8:
            print 'Got item name of %s.' % item_name
            print 'Got item type of %s.' % item_type
        #
        # Remove the last two items (ITEMTYPE ITEMNAME)
        del(items[lenitems-1])
        del(items[lenitems-2])
        lenitems = len(items)
        #print items
        # Anything left is options.
        if lenitems != 0:
            # Handle options here.
            options = items
        #
        # Check to make sure there isn't an item with item_name already known.
        existing_obj = self.current_class.findObjectByName(item_name)
        #
        if existing_obj:
            raise "Object with name %s already exists in class %s" % (item_name,
                                                                      self.current_class.name)
        item_obj = createItemObject(item_type, item_name, initial_value, options)
        #
        self.current_class.addObject(item_obj)
    #   
    def parseLine(self, line):
        tline = self.strip_comments(line)
        if tline == "":
            return
        items = tline.split()
        if items[0] == 'class':
            self.handleClassStart(tline, items)
        elif items[0] == '}':
            self.handleClassEnd(tline, items)
        elif items[0] == 'insert':
            self.handleInsertLine(line)
        else:
            #
            # OK, it wasn't a class beginning, a class ending, or an insert
            # so try to parse it as a statement within a class.
            self.handleClassDefinition(tline, items)
    #
    def strip_comments(self, line):
        line = line.strip()
        if line == '':
            return ''
        if line[0] == '#':
            return ''
        strind = line.find('#')
        if strind == -1:
            return line
        line = line[:strind]
        line = line.strip()
        return line     
    #
    def parseLines(self, lines):
        for l in lines:
            self.parseLine(l)
    #
    def parseFile(self, filename):
        self.source = "File: %s" % filename
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()
        return self.parseLines(lines)
    #
    def emitCode(self):
        # @fixme: Possibly do some validation here.
        code = self.getBoilerPlateCode()

        # Now dump any insert lines that have been defined.
        if self.insert_lines:
            code = code + "# Beginning of inserted code\n"
            for x in self.insert_lines:
                code = code + x
            code = code + "# End of inserted code\n"
            code = code + "\n"
        
        for x in self.classnames:
            c = self.classobjects[x]
            class_code = c.emitCode()
            #print class_code
            code = code + class_code + "\n"
        return code
    #
    def getBoilerPlateCode(self):
        code  = ""
        #
        if self.source:
            code += "# This code was generated from %s .\n" % self.source
            code += "# Please modify the original source rather than this generated code.\n"
        else:
            code += "# This code was generated from a definition file of unknown source.\n"
        code += "\n"
        #
        # First try to import gdhelpers both from within a framework directory
        # and in the current directory.
        code += "didimport = 0\n" \
                "try:\n" \
                "    import mpx.lib.genericdriver.gdhelpers as gd\n" \
                "    didimport = 1\n" \
                "except:\n" \
                "    pass\n" \
                "if not didimport:\n" \
                "    try:\n" \
                "        import gdhelpers as gd\n" \
                "        didimport = 1\n" \
                "    except:\n" \
                "        pass\n" \
                "if not didimport:\n" \
                '    raise "Error: Could not import gdhelpers."\n'
        #
        code += "\n\n"
        #
        return code


if __name__ == '__main__':
    lenargs = len(sys.argv)

    if lenargs == 2:
        if sys.argv[1] == '--version':
            print 'Version: %s' % version
            sys.exit(0)
    
    if lenargs != 3:
        print 'Takes two arguments, inputfilename and outputfilename'
        sys.exit(-2)
        
    inputfilename = sys.argv[1]
    outputfilename = sys.argv[2]

    print 'Got inputfilename of: %s' % str(inputfilename)
    print 'Got outputfilename of: %s' % str(outputfilename)

    if not os.path.exists(inputfilename):
        print 'Error: Input file (%s) does not exist!' % str(inputfilename)
        sys.exit(-3)

    if os.path.exists(outputfilename):
        print 'Error: Output file (%s) already exists!' % str(outputfilename)
        sys.exit(-4)
        
    pc = ProtoCompiler()
    pc.parseFile(inputfilename)

    code = pc.emitCode()
    
    f = open(outputfilename, 'w')
    f.write(code)
    f.close()
    
