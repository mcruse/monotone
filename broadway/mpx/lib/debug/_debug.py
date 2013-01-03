"""
Copyright (C) 2002 2003 2004 2007 2010 2011 Cisco Systems

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
# Provides functions to assist in debuging.

import array
import gc
import inspect
import os
import string
import sys
import time
import types

_dump_chars = string.digits + string.letters + string.punctuation

class _DebugDict(dict):
    pass

class _DebugTuple(tuple):
    pass

class _DebugList(list):
    pass

##
# Get a list of objects who cannot be referenced
# in the system but who cannot be garbage collected.
#
# @return List of uncollectables.
# @note Uncollectables usually result from circular
#       references involving objects who have defined
#       __del__ functions.
#
def get_uncollectables():
    gc.collect()
    return gc.garbage

##
# Inspects system to gather list of all
# loaded classes and their respective 
# reference counts.  Their reference counts
# corresponsds strongly with the number of 
# instances in memory.
#
# @return List of tuples, sorted by reference
#         count.  Tuple = (reference_count, class)
#
def get_refcounts():
    d = _DebugDict()
    sys.modules
    # collect all classes
    for m in sys.modules.values():
        for sym in dir(m):
            o = getattr (m, sym)
            if type(o) is types.ClassType:
                d[o] = sys.getrefcount (o)
    # sort by refcount
    pairs = map (lambda x: (x[1],x[0]), d.items())
    pairs.sort()
    pairs.reverse()
    return pairs

##
# Print out the 100 classes with the
# highest reference counts.
#
def print_top_100():
    for n, c in get_refcounts()[:100]:
        print '%10d %s' % (n, c.__name__)


##
# Generate a string that is a formatted, multi-line dump of integers.
# The integers are displayed in hexadecimal.
# @param ints A list of integer values.
# @param hdr A string to display at the start of each line.
# @default None No text is added to the start of each line.
# @param offset The offset where to start dumping integers.
# @default 0
# @param ipl <b>I</b>ntegers <b>p</b>er <b>l</b>ine.  The number of values
#            displayed on each line.
# @default 8
# @param width The number of zero filled nibbles to display for each integer.
# @default 4
def dump_ints_tostring(ints, hdr=None, offset=0, ipl=8, width=4):

    format = '%%0%dX ' % width
    result = array.array('c')

    ilen = len(ints)
    for istart in xrange(offset,ilen,ipl):
        iend = min(istart + ipl, ilen)
        if hdr:
            result.fromstring(hdr)
        for i in range(istart,iend):
            result.fromstring(format % ints[i])
        result.append('\n')
    return result.tostring()

##
# Generate a string that is a formatted, multi-line dump of characters.
# The generated string shows the actual character (when it's printable)
# and the hex value of each character.
# @param msg A String or array of characters to dump.
# @param hdr A string to display at the start of each line.
# @default None No text is added to the start of each line.
# @param offset The offset where to start dumping characters.
# @default 0
# @param cpl <b>C</b>haracters <b>p</b>er <b>l</b>ine.  The number of characters
#            to dump on each line.
# @default 8
def dump_tostring(msg, hdr=None, offset=0, cpl=16):
    result = array.array('c')
    unprintable = ' '
    bar = '|'

    if not type(msg) is types.StringType:
        if msg.typecode != 'c':
            msg = msg.tostring()

    for istart in xrange(offset,len(msg),cpl):
        iend = istart + cpl
        npad = cpl
        if hdr:
            result.fromstring(hdr)
        result.append(bar)
        for c in msg[istart:iend]:
            npad -= 1
            if c in _dump_chars:
                result.append(c)
            else:
                result.append(unprintable)
        while npad:
            result.append(' ')
            npad -= 1
        result.append(bar)
        result.fromstring('  ')
        for c in msg[istart:iend]:
            result.fromstring('%02X ' % (ord(c)))
        result.append('\n')
    return result.tostring()

##
# Dump a string or array of characters to sys.stderr.
# The generated output shows the actual character (when it's printable)
# and the hex value of each character.
# @param msg A String or array of characters to dump.
# @param hdr A string to display at the start of each line.
# @default None No text is added to the start of each line.
# @param offset The offset where to start dumping characters.
# @default 0
# @param cpl <b>C</b>haracters <b>p</b>er <b>l</b>ine.  The number of characters
#            to dump on each line.
# @default 8
def dump(msg, hdr=None, offset=0, cpl=16):
    str = dump_tostring(msg, hdr, offset, cpl)
    sys.stdout.write(str)
    return

##
# Output a list of integers as a formatted, multi-line dump to sys.stderr.
# The integers are displayed in hexadecimal.
# @param ints A list of integer values.
# @param hdr A string to display at the start of each line.
# @default None No text is added to the start of each line.
# @param offset The offset where to start dumping integers.
# @default 0
# @param ipl <b>I</b>ntegers <b>p</b>er <b>l</b>ine.  The number of values
#            displayed on each line.
# @default 8
# @param width The number of zero filled nibbles to display for each integer.
# @default 4
def dump_ints(ints, hdr=None, offset=0, cpl=8, width=4):
    str = dump_ints_tostring(ints, hdr, offset, cpl, width)
    sys.stdout.write(str)
    return

##
# Convert dump style output back into a simple Python string.
# @param text The dump style data.
# @return A string representing the dumped data.
def string_fromdump(text):
    result = ''
    lines = text.split('\n')
    for line in lines:
        try:
            left = line.index('|')
            right = line.rindex('|')
            if left == right:
                continue
            for hex_byte in line[right+1:].split():
                result += chr(int(hex_byte,16))
        except:
            return result
    return result

def _merge_lists(l1, l2):
    for e in l2:
        if not e in l1:
            l1.append(e)
    return l1

def _merge_class(l, c):
    for b in c.__bases__:
        _merge_class(l, b)
    _merge_lists(l, dir(c))
    return l

##
# Print everything that can discoverred about an object via introspection.
# @param obj The object inspect and discribe.
# @todo 1.  Better handling of sequences and dictionaries.
# @todo 2.  Handling of classes, instances, functions and modules.
# @todo 3.  If possible, handle built-in methods.
def print_object(obj):
    list = dir(obj)
    if hasattr(obj, '__class__'):
        _merge_class(list, obj.__class__)
    list.sort()
    for n in list:
        a = getattr(obj, n)
        t = type(a)
        if t is types.MethodType:
            if a.im_self:
                un = ''
            else:
                un = 'un'
            print '%s: %sbound method (%s.%s)' % (n, un, a.im_class.__name__,
                                                  a.im_func.__name__)
        else:
            print '%s: %s' % (n, a)

def _is_program(file):
    temp = open(file,'r')
    header = temp.read(2)
    temp.close()
    return (header == '#!')

def _walker(arg, dirname, names):
    module_base = dirname.replace('/','.')
    for name in names:
        if name == '__init__.py':
            # Import the package.
            module = module_base
            print 'Importing package: ', module
        elif name[-3:] == '.py':
            # Import the file.
            if not _is_program(os.path.join(dirname, name)):
                module = module_base + '.' + name[:-3]
                print 'Importing file: ', module
        else:
            continue
        command = compile('import ' + module,
                          'import_everything ' + module,
                          'exec')
        eval(command, globals(), locals())

##
# Import every Python file.
def import_everything(directory, packages):
    popdir = os.getcwd()
    directory = os.path.expanduser(directory) # Support ~
    directory = os.path.expandvars(directory) # Support variable expansion.
    os.chdir(directory)
    try:
        if type(packages) == types.StringType:
            packages = [packages]
        for package in packages:
            os.path.walk(package, _walker, None)
    finally:
        os.chdir(popdir)

##
# Return the end of the process' current data segment.
# @return A long that represents the Framework's end of data segment.
def get_brk():
    pass # For documentation only.
try:
    from _debug_memory import get_brk
except:
    pass

_vm_data_map = {
    'VmSize':'total',	# Total virtual memory used by this process.
    'VmLck':'locked',	# Total amount of memory locked by this process.
    'VmRSS':'rss',	# RSS used by this process.
    'VmData':'data',	# The amount of data (sans stack) used by this process.
    'VmStk':'stack',	# The current amount of stack used by this process.
    'VmExe':'exec',	# The size of the executable segment, sans library code.
    'VmLib':'lib'	# The size of the library code in this process.
    }

##
# Returns a dictionaray of interesting statistics about the process' virtual
# memory.
# @note The VM debug functions are crude and not intended for precise
#       measurement.
# @note The returned dictionary values are in bytes.  The underlying OS probably
#       allocates memory in large chucks (e.g. Linux IA32 allocates 4K pages).
def get_vm_data():
    result = _DebugDict()
    f = open('/proc/self/status')
    for line in f.xreadlines():
        name, remainder = line.split(':')
        if _vm_data_map.has_key(name):
            result[_vm_data_map[name]] = int(remainder.strip().split()[0]) * 1024
    result['brk'] = get_brk()
    return result

##
# Mark the current VM memory usage.
# @note The VM debug functions are crude and not intended for precise
#       measurement.
def set_memory_baseline():
    global _memory_scratch_pad
    global _memory_baseline
    del _memory_scratch_pad
    _memory_scratch_pad = get_vm_data()
    _memory_baseline = get_vm_data()

##
# Return a get_vm_data() style dictionary with deltas since set_memory_baseline
# was called.
# @note The VM debug functions are crude and not intended for precise
#       measurement.
def delta_memory_baseline():
    global _memory_scratch_pad
    global _memory_baseline
    del _memory_scratch_pad
    _memory_scratch_pad = get_vm_data()
    for k in _memory_keys:
        _memory_scratch_pad[k] = _memory_scratch_pad[k] - _memory_baseline[k]
    return _memory_scratch_pad

# Cheesy attempy to minimize changes in memory alloation due to
# set_memory_baseline() and delta_memory_baseline().  Calling these functions
# from more than one thread is not advisable.

try:
    _memory_scratch_pad = get_vm_data()
    _memory_baseline = get_vm_data()
    _memory_keys = _memory_baseline.keys()
    set_memory_baseline()
except:
    pass

##
# @return Every object in the system that is derived from the specified
#         class(es).
# @warning Keeping references to the returned list will prevent those
#          objects from being garbage collected!
def instances_of(klass_or_tuple):
    everything=gc.get_objects()
    instances=_DebugList()
    while everything:
        instance=everything.pop()
        if isinstance(instance,klass_or_tuple):
           instances.append(instance)
    return instances

##
# @return Every object in the system that is derived from any of the classes
#         defined in the specified module.
# @warning Keeping references to the returned list will prevent those
#          objects from being garbage collected!
def module_instances(module):
    if not hasattr(module, '__debug_class_list'):
        klasses = _DebugList()
        for instance in module.__dict__.values():
            if type(instance) in (types.ClassType, types.TypeType):
                klasses.append(instance)
        setattr(module,'__debug_class_list',_DebugTuple(klasses))
    klasses = getattr(module,'__debug_class_list')
    return instances_of(klasses)

_max_object_count = 0
_min_object_count = 0
##
# Every second counts the total number of objects in the system.
# @note Inteded for interactive use.  Ctrl-C to exit.
def monitor_object_count():
    global _min_object_count
    global _max_object_count
    _now=len(gc.get_objects())
    print "NOW:%d"%_now
    while 1:
        _now=len(gc.get_objects())
        if _now<_min_object_count:
            print "MIN:%d"%_now
            _min_object_count=_now
        elif _now>_max_object_count:
            print "MAX:%d"%_now
            _max_object_count=_now
        time.sleep(1)

def simple_class_report():
    everything = gc.get_objects()
    class_counts = _DebugDict()
    while everything:
        instance = everything.pop()
        tipe = type(instance)
        if tipe is types.InstanceType:
            # Old school Python object.
            key = ("instance %s.%s", instance.__module__,
                   instance.__class__.__name__)
        elif tipe is types.BuiltinFunctionType:
            # A built-in or C module.
            key = ("built-in %s",instance.__name__)
        elif tipe is types.MethodType:
            # A method on a Python object.
            key = ("method %s.%s.%s",
                   instance.im_class.__module__,
                   instance.im_class.__name__,
                   instance.im_func.__name__)
        elif tipe is types.FunctionType:
            key = ("function",)
        elif hasattr(instance, '__class__'):
            klass = instance.__class__
            key = ("object %s.%s", klass.__module__,klass.__name__)
        else:
            key = ("%s", tipe.__name__)
        if class_counts.has_key(key):
            class_counts[key] += 1
        else:
            class_counts[key] = 1
    return class_counts

def print_simple_class_report(report=None):
    if report is None:
        report = simple_class_report()
    klass_counts = _DebugList()
    for key,count in report.items():
        klass_counts.append(_DebugTuple((count,key)))
    klass_counts.sort()
    for count,key in klass_counts:
        print "%d: %s" % (count,key[0] % key[1:])
    return

def simple_class_diff(r1, r2=None):
    if r2 is None:
        r2 = simple_class_report()
    keys = r1.keys()
    for key in r2.keys():
        if key not in keys:
            keys.append(key)
    delta_counts = _DebugDict()
    for key in keys:
        if r1.has_key(key):
            if r2.has_key(key):
                # r1 and r2 have key.
                count = r2[key]-r1[key]
                if count:
                    delta_counts[key] = count
            else:
                # only r1 has the key.
                delta_counts[key] = -r1[key]
        else:
            # only r2 has the key.
            delta_counts[key] = r2[key]
    return delta_counts

def print_simple_class_diff(r1, r2=None):
    print_simple_class_report(simple_class_diff(r1,r2))
    return

def randpass():
    p = ''
    f = open('/dev/urandom')
    for i in range(0,8):
        b = f.read(1)
        # No 1, I, l, O or 0 to avoid confusion.
        x = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
        c = x[ord(b) % len(x)]
        p = p + c
    return p

def print_line(fmt, *args):
    sys.stderr.flush()
    if args:
        sys.stdout.write(fmt % args)
    else:
        sys.stdout.write(str(fmt))
    sys.stdout.write('\n')
    sys.stdout.flush()
    return

def print_raw(fmt, *args):
    sys.stderr.flush()
    if args:
        sys.stdout.write(fmt % args)
    else:
        sys.stdout.write(str(fmt))
    sys.stdout.flush()
    return

def countAllTypes(printTypeCounts=1):
    typeCounts = {}
    everything=gc.get_objects()
    for o in everything:
        t=type(o)
        if typeCounts.has_key(t):
            typeCounts[t] += 1
        else:
            typeCounts[t] = 1
    if printTypeCounts == 1:
        # sort by count
        pairs = map (lambda x: (x[1],x[0]), typeCounts.items())
        pairs.sort()
        pairs.reverse()
        for c, t in pairs:
            print '%10d %s' % (c, t.__name__)
    return typeCounts

# continually monitors max counts of all types
def monitorMax():
    maxCounts = {}
    while 1:
        printTimeOfNewMax = 1
        typeCounts = countAllTypes(0)
        for t, c in typeCounts.items():
            if maxCounts.has_key(t):
                if c > maxCounts[t]:
                    if printTimeOfNewMax == 1:
                        print
                        print '_debug.py.monitorMax(): %s' % time.asctime()
                        print '--------------------------------------------'
                        # only print one heading per iteration
                        printTimeOfNewMax = 0
                    maxCounts[t] = c
                    print '_debug.py.monitorMax(): New Max %10d for %s' % (c,
                                                                 t.__name__)
            else:
                maxCounts[t] = c
        time.sleep(1)

##
# @return the current line number in of the caller.
def lineno():
    return inspect.currentframe().f_back.f_lineno
