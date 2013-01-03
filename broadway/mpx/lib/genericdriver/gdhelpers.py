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
# Note: By design this module has as little dependency on the framework as possible.
#       Any dependencies which exist should be optional.
import struct

import gdutil

##
# A class used to encapsulate the information returned by protocol object's
# isMatch() methods.  Once returned by isMatch() it can be queried to determine
# if the passed in data was an exact match, a potential match or not a match, and
# in the first two cases, how much data was consumed by the match or partial match.
#
class IsMatchReturn:
    ##
    # Initialize an IsMatchReturn object.
    #
    # @param didmatch int (-1, 0, 1) with the following meanings:
    #          1 if exact match,
    #         -1 if definitely not a match.
    #          0 if a potential match (incomplete match).
    # @param consumed int The number of bytes consumed if there was a partial or complete
    #                     match.  In the case of a partial match, the number of bytes
    #                     consumed will probably be subject to increase as more data
    #                     comes in.
    # @default None
    #
    def __init__(self, didmatch, consumed=None):
        assert didmatch in (-1, 0, 1), "Invalid value for didmatch of %s" % str(didmatch)
        #
        self.didmatch = didmatch
        self.bytes_consumed = consumed
    ##
    # Returns whether or not the data definitely does not match the protocol object.
    #
    # @return Returns 1 if the data definitely did not match the protocol object,
    #         and 0 if there was a match or a potential match.
    #
    def isNotMatch(self):
        if self.didmatch == -1:
            return 1
        return 0
    ##
    # Returns whether or not the data definitely does match the protocol object.
    #
    # @return Returns 1 if the data definitely did match the protocol object,
    #         and 0 if there was not a match or a potential match.
    #
    def isMatch(self):
        if self.didmatch == 1:
            return 1
        return 0
    ##
    # Returns wheter or not the data potentially matches the protocol object.
    #
    # @return Returns 1 if the data potentially matches the protocol object or
    #         if the data did exactly match the protocol object and 0 
    #         if the data definitely can't match the protocol object.
    #
    def isPotentialMatch(self):
        if self.didmatch == 0:
            return 1
        # For now, count an exact match as a potential match too.
        if self.didmatch == 1:
            return 1
        return 0
    ##
    # Sets the number of bytes consumed.
    #
    # @param num_bytes The number of bytes consumed by a protocol object.
    #
    def setBytesConsumed(self, num_bytes):
        self.bytes_consumed = num_bytes
    ##
    # Returns the number of bytes consumed by an exact or potential match of a
    # protocol object or None if nothing has been consumed.
    #
    # @return Returns the number of bytes consumed by a protocol object.
    #
    def bytesConsumed(self):
        if not self.bytes_consumed:
            # Handles the case where bytes_consumed is 0 or None.
            return None
        return self.bytes_consumed
    #
    def __str__(self):
        rstr  = 'IsMatchReturn object with '
        rstr += 'didmatch of %d and ' % self.didmatch
        rstr += 'bytes_consumed of %s.' % str(self.bytes_consumed)
        return rstr

def name_search_func(_obj, _name):
    #print 'In name_search_func() with %s and %s' % (str(_obj), str(_name))
    if _obj:
        if hasattr(_obj, 'name'):
            if _obj.name == _name:
                return _obj
    return None

class BaseGDClass:
    def __init__(self):
        self._isFixed = None
        self._width = None
        self._num_items = None
        self._isPackCompatible = None
        self._packSpec = None
        self.items = []
        self.name = None
        self.debug = 0
    #
    def __str__(self):
        rstr  = 'BaseGDClass with name: %s, ' % str(self.name)
        rstr += '_isFixed: %s, _width: %s, ' % (str(self._isFixed), str(self._width))
        rstr += '_num_items: %s, ' % str(self._num_items)
        rstr += '_isPackCompatible: %s, ' % str(self._isPackCompatible)
        rstr += '_packSpec: %s, ' % str(self._packSpec)
        rstr += 'debug: %s, ' % str(self.debug)
        rstr += 'items: %s.' % str(self.items)
        return rstr
    #
    def isFixedWidth(self):
        return self._isFixed
    #
    def isPackCompatible(self):
        return self._isPackCompatible
    #
    def packSpec(self):
        return self._packSpec
    #    
    def getWidth(self):
        return self._width
    #
    def getNumItems(self):
        return self._num_items
    #
    def getName(self):
        return self.name
    #
    # Returns >0 - Enough data (amound returned is amount consumed).
    #          0 - Not enough data
    #         <0 - Unknown, not fixed width
    def _isEnoughData(self, data, offset):
        if self.isFixedWidth():
            width = self.getWidth()
            lendata = len(data) - offset
            if lendata >= width:
                return width
            else:
                return 0
        else:
            # Not fixed width.  For now, behavior is undefined, but possibly
            # we could check each child in turn to see if there is enough data
            # for them.
            raise gdutil.GDException("Option not implemented")
    #
    # Returns an IsMatchReturn object.
    def isMatch(self, data, offset):
        for x in self.items:
            x.clearValue()
        #
        if self.isFixedWidth():
            isenough = self._isEnoughData(data, offset)
            if isenough < 0:
                # Not enough data, but may be a potential match.
                return IsMatchReturn(0)
        #
        # Note: Later we should store how many items have been matched and an
        #       offset into the data so we don't have to keep matching over
        #       and over on items already matched.  This requires a method to
        #       set the potential match data, and a method to reset the
        #       current idea of what has been matched if the match data is reset.
        consumed = 0
        lendata = len(data) - offset
        for i in range(0, self.getNumItems()):
            # If we have already consumed all of our data, then there is not need to check any more,
            # we must have a potential match.
            if consumed >= lendata:
                return IsMatchReturn(0, consumed)
            ismatchobj = self.items[i].isMatch(data, offset+consumed)
            # If this item is not a match then return a non-match result right away.
            if ismatchobj.isNotMatch():
                return ismatchobj
            # If this item is not a potential match then return a non-potential match right away.
            if not ismatchobj.isPotentialMatch():
                return ismatchobj
            # Must have been a match!
            bytes_consumed = ismatchobj.bytesConsumed()
            if bytes_consumed:   # Could be None
                consumed += bytes_consumed
            # If the match is only a potential match, then go ahead and return with the potential
            # match.
            if ismatchobj.isPotentialMatch() and not ismatchobj.isMatch():
                return IsMatchReturn(0, consumed)
        # Must have been a match!
        if self.debug > 5:
            print 'Object %s returning a match!' % str(self)
        ret_obj = IsMatchReturn(1, consumed)
        return ret_obj
    #
    # Attempts to parse data with each child item object.  If it all works,
    # return 1 otherwise return 0 (usually happens because of not enough
    # data)
    def getValue(self, data, offset):
        # @fixme: This method turned out not to be really relevant, consider removing.
        raise gdutil.GDException("Option not implemented")
    #
    def dumpStr(self):
        dstr = ''
        for x in self.items:
            dstr += x.dumpStr()
        return dstr
    #
    def setValue(self, item_name, item_value):
        for x in self.items:
            if x.name == item_name:
                x.setValue(item_value)
                return
        raise gdutil.GDException("Item with name %s not found." % item_name)
    #
    def getChildren(self):
        return self.items
    #
    def _recursive_search(self, _obj, search_func, search_args):
        #print 'In recursive_search with %s, %s and %s.' % (str(_obj), str(search_func), str(search_args))
        obj_children = _obj.getChildren()
        if obj_children:
            for x in obj_children:
                found_obj = self._recursive_search(x, search_func, search_args)
                if found_obj:
                    return found_obj
        found_obj = search_func(_obj, *search_args)
        return found_obj
    #
    # Note: Does a depth-first search at the moment, but in general it is
    #       best to make sure that important children have unique names.
    def findChildByName(self, child_name):
        # A little unorthodox, but check ourselves first to see if we match.
        if self.name == child_name:
            return self
        # It wasn't us, check any children recursively.
        for x in self.items:
            found_child = self._recursive_search(x, name_search_func, [child_name])
            if found_child:
                return found_child
        return None
        


class BaseItem:
    # __init__ takes several optional key word arguments.  They are:
    #      name, type, initial_value, width_in_bytes, is_fixed_width,
    #      initial_value, pack_spec, pack_compatible, width_is_pack,
    #      width_pack_spec, width_pack_len, child_obj and debug.
    #      
    def __init__(self, **kwargs):
        # Set initial values.  May be overriden by key word arguments.
        self.initial_value = None
        self.pack_compatible = 0
        self.width_in_bytes = None
        self.is_fixed_width = 0
        self.pack_spec = None
        self.type = None
        self.name = None
        self.value = None
        self.width_is_pack = None
        self.width_pack_spec = None
        self.width_pack_len = None
        self.child_obj = None
        self.debug = 0
        self.node = None

        # Establishes a mapping between keyword argument and
        # instance members.  First item in tuple is keyword
        # argument, second is instance member name.
        kwargs_map = (
                       ('name',         'name'),
                       ('type',         'type'),
                       ('width',        'width_in_bytes'),
                       ('isfixedwidth', 'is_fixed_width'),
                       ('value',        'initial_value'),
                       ('packspec',     'pack_spec'),
                       ('ispack',       'pack_compatible'),
                       ('widthispack',  'width_is_pack'),
                       ('widthpackspec','width_pack_spec'),
                       ('widthpacklen', 'width_pack_len'),
                       ('child_object', 'child_obj'),
                       ('debug',        'debug'),
                      )

        self._apply_arg_maps(kwargs_map, kwargs)
    #
    def _apply_arg_maps(self, arg_map, kwargs):
        for x in arg_map:
            arg_name, member_name = x
            if kwargs.has_key(arg_name):
                arg_val = kwargs[arg_name]
                if arg_val is not None:
                    setattr(self, member_name, arg_val)
    #
    # Returns >0 - Enough data (amount returned is amount consumed).
    #          0 - Not enough data
    #         <0 - Unknown, not fixed width
    def _isEnoughData(self, data, offset):
        if not self.isFixedWidth():
            return -1
        width = self.getWidth()
        lendata = len(data) - offset
        if lendata >= width:
            return width
        else:
            return 0
    #
    def _getValue(self, data, offset):
        if not self.isPackCompatible():
            return None
        if self._isEnoughData(data, offset) < 1:
            return None
        width = self.getWidth()
        relevant_data = data[offset:offset+width]
        #print 'Len relevant_data: %d' % len(relevant_data)
        #print 'packSpec: %s' % self.packSpec()
        #print relevant_data
        x = struct.unpack(self.packSpec(), relevant_data)
        return x[0]
    #
    def findChildByName(self, child_name):
        # A little unorthodox, but check ourselves first to see if we match.
        if self.name == child_name:
            return self
        if self.child_obj:
            # Right now all child objects should inherit from BaseGDClass which has
            # a findChildByName method, but check just to be safe.
            if hasattr(self.child_obj, 'findChildByName'):
                return self.child_obj.findChildByName(child_name)
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
    def getType(self):
        return self.type
    #
    def getName(self):
        return self.name
    #
    def packSpec(self):
        return self.pack_spec
    #
    def getWidthIsPack(self):
        return self.width_is_pack
    #
    def getWidthPackSpec(self):
        return self.width_pack_spec
    #
    def getWidthPackLen(self):
        return self.width_pack_len    
    #
    def setValue(self, value):
        self.value = value
    #
    def getValue(self):
        return self.value
    #
    def clearValue(self):
        self.value = None
    #
    def setNode(self, _node):
        self.node = _node
    #
    def getNode(self):
        return self.node
    #
    def updateNodeValue(self, new_value):
        if self.node:
            if not new_value is None:
                self.node._setValue(new_value)
    #
    def getChildren(self):
        if not self.child_obj:
            return None
        return [self.child_obj]
    #
    def dumpStr(self):
        # If this item is not pack compatible then we have no idea
        # how to dump it.
        if not self.isPackCompatible():
            raise gdutil.GDException("Could not dumpStr because item is not pack compatible.")
        val = None
        if self.value is None:
            if self.initial_value is None:
                raise gdutil.GDException("Could not dumpStr because value was not set")
            else:
                val = self.initial_value
        else:
            val = self.value
        cstr = struct.pack(self.packSpec(), val)
        return cstr
    #
    def __str__(self):
        rstr  = 'Item with type: %s' % str(self.type)
        rstr += ', name: %s' % str(self.name)
        rstr += ', is_fixed_width: %d' % self.is_fixed_width
        rstr += ', width: %s' % str(self.width_in_bytes)
        rstr += ', pack_compatible: %d' % self.pack_compatible
        if self.pack_compatible:
            rstr += ', pack_spec: %s' % self.pack_spec
        if self.initial_value:
            rstr += ', initial_value: %s' % self.initial_value
        if self.width_is_pack:
            rstr += ', width_is_pack: %s' % str(self.width_is_pack)
        if self.width_pack_spec:
            rstr += ', width_pack_spec: %s' % str(self.width_pack_spec)
        if self.width_pack_len:
            rstr += ', width_pack_len: %s' % str(self.width_pack_len)
        if self.value:
            rstr += ', value: %s' % str(self.value)
        if self.child_obj:
            rstr += ', child_obj: "%s"' % str(self.child_obj)
        return rstr

class IntItem(BaseItem):
    def __init__(self, **kwargs):
        BaseItem.__init__(self, **kwargs)
        #
        # All Int items are fixed width and pack compatible.
        self.is_fixed_width = 1
        self.pack_compatible = 1
    #
    # Returns an IsMatchReturn object.
    def isMatch(self, data, offset):
        if self.debug > 5:
            print 'In isMatch for %s' % str(self)
        val = self._getValue(data, offset)
        self.value = val
        if val is None:
            # Don't have enough data yet.
            return IsMatchReturn(0)
        #print 'Got val of %d' % val
        if not self.initial_value is None:
            if self.initial_value == val:
                #print 'Got a match for %X.' % val
                self.updateNodeValue(val)
                return IsMatchReturn(1, self.getWidth())
            else:
                return IsMatchReturn(-1)
        else:
            # If we don't have an initial value, then anything is a match.
            #print 'No initial value.'
            self.updateNodeValue(val)
            return IsMatchReturn(1, self.getWidth())

class FloatItem(BaseItem):
    def __init__(self, **kwargs):
        BaseItem.__init__(self, **kwargs)
        #
        # All Float items are fixed width and pack compatible.
        self.is_fixed_width = 1
        self.pack_compatible = 1
        #
        self.float_allowable_diff = 0.0001
    #
    # Returns 0 if the floats are close enough to be considered equal, 1 if
    # the first argument is greater than the second, and -1 if the second
    # argument is greater than the first.
    # 
    def _float_cmp(self, f1, f2):
        # First check for "equality"
        if abs(f1 - f2) < self.float_allowable_diff:
            # "Equal"
            return 0
        if f1 > f2:
            return 1
        else:
            return -1
    #
    # Returns an IsMatchReturn object.
    def isMatch(self, data, offset):
        if self.debug > 6:
            print 'In isMatch() with offset %d, and data.' % offset, gdutil.dump_binary_str(data)
        val = self._getValue(data, offset)
        if val is None:
            # Don't have enough data yet.
            return IsMatchReturn(0)
        if self.debug > 6:
            print 'Got val of %s' % str(val)
        if not self.initial_value is None:
            if self._float_cmp(self.initial_value, val) == 0:
                self.value = val
                if self.debug > 6:
                    print 'Got a match for %s.' % str(val)
                self.updateNodeValue(val)
                return IsMatchReturn(1, self.getWidth())
            else:
                return IsMatchReturn(-1)
        else:
            # If we don't have an initial value, then anything is a match.
            #print 'No initial value.'
            self.value = val
            self.updateNodeValue(val)
            return IsMatchReturn(1, self.getWidth())

class PadItem(BaseItem):
    def __init__(self, **kwargs):
        BaseItem.__init__(self, **kwargs)
        #
        # All pad items are fixed width and not pack compatible.
        self.is_fixed_width = 1
        self.pack_compatible = 0
        self.pack_spec = None
    #
    def _getValue(self, data, offset):
        if self._isEnoughData(data, offset) < 1:
            return None
        return '\00' * self.getWidth()
    #
    # Returns an IsMatchReturn object.
    def isMatch(self, data, offset):
        val = self._getValue(data, offset)
        if val is None:
            # Don't have enough data yet.
            return IsMatchReturn(0)
        # For pad item's, everything that is big enough is a match.
        # Note: No need to update any kind of related node here.
        return IsMatchReturn(1, self.getWidth())
    #
    def setValue(self, value):
        raise gdutil.GDException("setValue() not supported for PadItem")
    #
    def dumpStr(self):
        return '\00' * self.getWidth()

class BufferItem(BaseItem):
    def __init__(self, **kwargs):
        BaseItem.__init__(self, **kwargs)
        #
        # All buffer items are not pack compatible.
        self.pack_compatible = 0
        self.pack_spec = None
        self.computed_width = None
    #
    def getWidth(self):
        if self.isFixedWidth():
            return self.width_in_bytes
        else:
            # If this item is not of fixed width, then it must be
            # a variable width item with a preceeding length whose
            # length is specified by width_pack_len, so that is a
            # good starting point for the minimum length even if
            # we don't know the full length yet.
            width = self.width_pack_len
            if self.computed_width:
                # Looks like we know the length of our variable portion,
                # so add it in as well.
                width += self.computed_width
            return width
    #
    # Returns >0 - Enough data (amount returned is amount consumed).
    #          0 - Not enough data
    #         <0 - Unknown, not fixed width
    def _isEnoughData(self, data, offset):
        # If we are a fixed width item, go ahead and let BaseItem take care of it.
        if self.isFixedWidth():
            return BaseItem._isEnoughData(self, data, offset)
        #
        # We must be a variable width item.
        # First see if we have enough data for our length field.
        lendata = len(data) - offset
        if lendata < self.width_pack_len:
            # Not enough, and we don't know how much we need either.
            return -1
        # Cool we have at least enough for our length field.
        relevant_data = data[offset:offset+self.width_pack_len]
        self.computed_width = struct.unpack(self.getWidthPackSpec(), relevant_data)[0]
        if self.debug > 2:
            print 'Got computed_width of %s' % str(self.computed_width)
        # OK, now we know how much data we really need.
        width = self.width_pack_len + self.computed_width
        if lendata >= width:
            return width
        else:
            return 0
    #
    def _getValue(self, data, offset):
        if self._isEnoughData(data, offset) < 1:
            return None
        # We have enough data, so we know we are either fixed width, or
        # computed_width and width_pack_len has been filled in appropriately.
        relevant_data = None
        if self.isFixedWidth():
            relevant_data = data[offset:offset+self.getWidth()]

            # Do some special handling for string items
            if self.type == 'string':
                strind = relevant_data.find('\00')
                if strind != -1:
                    relevant_data = relevant_data[:strind]
        else:
            starting_pos = offset + self.width_pack_len
            relevant_data = data[starting_pos:starting_pos + self.computed_width]
        # If we have a child object, let it handle _getValue().
        if self.child_obj:
            pass
        return relevant_data
    #
    # Returns an IsMatchReturn object.
    def isMatch(self, data, offset):
        if not self.child_obj:
            val = self._getValue(data, offset)
            self.value = val
            if val is None:
                # Don't have enough data yet.
                return IsMatchReturn(0)
            # For buffer items without a child, everything that is big enough is a match.
            self.updateNodeValue(val)
            return IsMatchReturn(1, self.getWidth())
        else:
            if not self.isFixedWidth():
                # If we don't have enough data for at least our length field,
                # then return immedialtey.
                lendata = len(data) - offset
                if lendata < self.width_pack_len:
                     return IsMatchReturn(0)
                # OK, we have enough data for our length field,  let the
                # child start interpreting after that.
                offset += self.width_pack_len
            child_match = self.child_obj.isMatch(data, offset)
            #
            if not self.isFixedWidth():
                # Add the length of our length field to the number of bytes
                # consumed by the child.
                child_consumed = child_match.bytesConsumed()
                #
                if child_consumed is not None:
                    child_match.setBytesConsumed(child_consumed + self.width_pack_len)
            #
            return child_match
    #
    def setValue(self, value):
        # Do some minimal checking if possible.
        if self.isFixedWidth():
            if self.type != 'string':
                if len(value) != self.width_in_bytes:
                    mstr = "Got wrong size for data (got len of %d rather than %d)" % (len(value),
                                                                                       self.width_in_bytes)
                    raise gdutil.GDException(mstr)
            else:
                if len(value) >= self.width_in_bytes:
                    mstr  = "Got wrong size for data (got string length of %d for " % len(value)
                    mstr += "a string buffer of length %d (-1 for NULL)." % self.width_in_bytes
                    raise gdutil.GDException(mstr)
        #
        self.value = value
    #
    def dumpStr(self):
        if self.child_obj:
            val = self.child_obj.dumpStr()
        else:
            if self.value is None:
                if self.initial_value is None:
                    raise gdutil.GDException("Could not dumpStr because value was not set")
                else:
                    val = self.initial_value
            else:
                val = self.value
        if self.isFixedWidth():
            if self.type == 'string':
                # Make sure string is NULL-terminated and pad returned string
                # out to required length.
                val = val + '\00' * (self.width_in_bytes - len(val))
            return val
        else:
            self.computed_width = len(val)
            width_str = struct.pack(self.getWidthPackSpec(), self.computed_width)
            return width_str + val

