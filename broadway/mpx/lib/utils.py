"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
# Miscellaneous Utility Functions and Classes:
#

import types, struct, array
from copy import copy

from mpx.lib.exceptions import EInvalidValue


import os
import stat

##
#
# a replacement for filecmp.cmp, see bug #6712
# filecmp.cmp has a memory leak as its _cache is never cleared
#

def filecompare(f1, f2):
    s1 = os.stat(f1)[stat.ST_SIZE]
    s2 = os.stat(f2)[stat.ST_SIZE]
    if s1 != s2:
        return 0
    
    bufsize = 8192
    fp1 = open(f1, 'rb')
    fp2 = open(f2, 'rb')
    while 1:
        b1 = fp1.read(bufsize)
        b2 = fp2.read(bufsize)
        if b1 != b2:
            return 0
        if not b1:
            return 1


##
# bytes_as_string_of_hex_values():
# @param input 4-byte IntType, or ListType, or TupleType, or StringType
#
def bytes_as_string_of_hex_values(input, input_len=None):
    bytes = input
    if (type(input) == types.IntType):
        temp = struct.pack('!L', input) # '!': network byte order (NOT Intel order)
        bytes = list(struct.unpack('B' * 4, temp))
    elif (type(input) == types.StringType):
        bytes = list(struct.unpack('B' * len(input), input))
    elif (not type(input) == types.ListType) and (not type(input) == types.TupleType):
        raise EInvalidValue('input',input,'must be 4-byte integer, list, tuple, or string')
    result = array.array('B', bytes)
    if (not input_len is None):
        diff = len(bytes) - input_len
        if diff > 0:
            result = result[-input_len:]
        elif diff < 0:
            temp = array.array('B', '\0' * -diff)
            temp.extend(result)
            result = temp
    return result.tostring()

##
# interpolate a value from two lists of values
# @param xlist ListType or TupleType of monotonically increasing or decreasing values
# @param ylist ListType or TupleType of values related to cooresponding values in xlist
#
def interpolate(xlist, ylist, x):
    x = float(x) #make sure all calculations are in real numbers
    if (not type(xlist) == types.ListType) and (not type(xlist) == types.TupleType):
        raise EInvalidValue('xlist', xlist, 'must be list or tuple')
    if (not type(ylist) == types.ListType) and (not type(ylist) == types.TupleType):
        raise EInvalidValue('ylist', ylist, 'must be list or tuple')
    if not len(xlist) == len(ylist):
        raise EInvalidValue('xlist, ylist', (xlist, ylist,), 'must be lists or tuples of equal length')
    if len(xlist) < 2:
        raise EInvalidValue('xlist, ylist', (xlist, ylist,), 'list must be at least two elements in length')
    #
    #determine the proper order in which to search
    zlist = xlist
    tlist = ylist
    if xlist[0] > xlist[-1]: #reverse search
        zlist = copy(list(xlist))
        tlist = copy(list(ylist))
        zlist.reverse()
        tlist.reverse()
    x1 = None
    y1 = None
    i = 0
    for z in zlist:  #search for first value that exceeds x
        if z >= x: #we found the range
            if x1 is None: #hit on the first lookup
                return tlist[0]
            return (((x - x1) / (z - x1)) * (tlist[i] - y1)) + y1 #since x is float, all math will be float
        x1 = z
        y1 = tlist[i]
        i += 1
    return tlist[-1]
