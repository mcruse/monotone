"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
# Test cases to exercise the data encoders and decoders.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib.bacnet import sequence, data, tag

class TestCase(DefaultTestFixture):
    def test_BACnetDateRange(self):
        r = sequence.BACnetDateRange(decode=[tag.Date(data.Date(2000,4,4)),
                                             tag.Date(data.Date(2000,8,8))])
        if r.start_date.year != 2000:
            raise 'Invalid start_date year'
        if r.start_date.month != 4:
            raise 'Invalid start_date month'
        if r.start_date.day != 4:
            raise 'Invalid start_date day'
        if r.end_date.year != 2000:
            raise 'Invalid end_date year'
        if r.end_date.month != 8:
            raise 'Invalid end_date month'
        if r.end_date.day != 8:
            raise 'Invalid end_date day'
        return
    def test_BACnetDateTime(self):
        dt = sequence.BACnetDateTime(decode=[tag.Date(data.Date(2000,4,4)),
                                             tag.Time(data.Time(12,0,0))])
        if dt.date.year != 2000:
            raise 'Invalid date year'
        if dt.date.month != 4:
            raise 'Invalid date month'
        if dt.date.day != 4:
            raise 'Invalid date day'
        if dt.time.hour != 12:
            raise 'Invalid time hour'
        if dt.time.minute != 0:
            raise 'Invalid time minute'
        if dt.time.second != 0:
            raise 'Invalid time second'
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
