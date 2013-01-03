"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main

import time

from mpx.lib.stream import *
from mpx.lib.threading import Thread, Condition
from mpx.lib import pause

_failed = None
_callback_stream = None
_reason = ''

def _writer(cv,stream,length):
    global _failed
    global _reason
    start = time.time()
    total = 0
    while total < length:
        count = stream.write('c' * (length-total))
        total += count
    stream.close()
    end = time.time()
    cv.acquire()
    try:
        if (end - start) < 1:
            _failed = 1
            _reason = 'There was no delay when writing ' + \
                    'appears that write did not block'
        else:
            _failed = 0
    finally:
        cv.notify()
        cv.release()
    return count

_callback_count = 0
def _callback(stream):
    global _failed
    global _reason
    global _callback_stream
    global _callback_count
    if _callback_count >= 2:
        _callback_stream.close()
    else:
        _callback_stream.write('c'*100000)
        _callback_count += 1

_list = []
for x in range(0,100):
    _list.append(x)

def _get_item(index, stream):
    if index < 0:
        index = len(stream) + index
    if index + stream.get_meta_value('begin') >= \
       len(_list):
        raise IndexError()
    return _list[stream.get_meta_value('begin') + index]
def _get_len(stream):
    return len(_list) - stream.get_meta()['begin']

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        global _failed
        global _callback_stream
        global _reason
        global _callback_count
        _callback_count = 0
        _failed = None
        _callback_stream = None
        _reason = ''
    def test_cross_thread(self):
        # @note:  This test is relying on the write being large enough to
        #         fill all the OS buffers and block.
        #
        # @note:  Methinks this test relies on too many side effects...
        too_big_for_one_write = 1000000
        some_of_but_not_all_of_it = 65536
        stream = CrossThreadStream()
        cv = Condition()
        t1 = Thread(target=_writer, args=(cv,stream,too_big_for_one_write))
        cv.acquire()
        t1.start()
        # @note:  This pause should cause the _writer to block since it is
        #         trying to write too_big_for_one_write.
        pause(2)
        data = stream.read(some_of_but_not_all_of_it)
        count = len(data)
        self.failUnless(data == 'c'*count and
                        count <= some_of_but_not_all_of_it, 'First read ' + 
                        'failed to return the correct data or returned ' + 
                        'too much data')
        while count < too_big_for_one_write:
            data += stream.read(too_big_for_one_write - count)
            count = len(data)
        self.failUnless(data == 'c'*too_big_for_one_write,
                        'Overall stream did not return ' + 
                        'data written to it correctly or the wrong number')
        self.failUnless(stream.read(100) == '', 'Read did not return empty ' + 
                        'string even though no more data should have been ' + 
                        'waiting and the stream closed')
        cv.wait()
        try:
            self.failIf(_failed, _reason)
        finally:
            cv.release()
    
    def test_callback_stream(self):
        global _callback_stream
        _callback_stream = StreamWithCallback(_callback)
        data = _callback_stream.read(100000)
        count = len(data)
        self.failUnless(data == 'c'*count and count <= 100000, 'First read ' + 
                        'failed to return the correct data or returned ' + 
                        'too much data')
        while data:
            data = _callback_stream.read(100000)
    
    def test_callback_tuple(self):
        stream = StreamingTupleWithCallback(_get_item, _get_len)
        stream.set_meta('begin', 2)
        count = 0
        for item in stream:
            self.failIf(item != _list[count + stream.get_meta_value('begin')], \
                        'Iteration returned incorrect item for index %s' % count)
            count += 1
        self.failUnless(stream[0] == _list[stream.get_meta_value('begin')])
        self.failUnless(stream[5] == _list[stream.get_meta_value('begin')+5])
        self.failUnless(stream[-1] == _list[-1], 'Negative index ' +
                        'did not return correct item')
    

if __name__ == '__main__':
    main()
