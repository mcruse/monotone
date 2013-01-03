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
import array

class CircularBuffer:
    def __init__(self,buffer,length):
        self._buffer = buffer
        self.length = length
        self.filled = 0
        self.end = 0
    def initialize(self,init='\x00'):
        self._buffer.seek(0)
        while self._buffer.tell() < self.length - len(init):
            self._buffer.write(init)
        self._buffer.write(init[0:self.length - self._buffer.tell()])
        self._buffer.seek(0)
        self.filled = 0
        self.end = 0
    def beginning(self):
        if not self.filled:
            return 0
        return self.end
    def ending(self):
        return self.end
    def tell(self):
        if not self.filled:
            return self._buffer.tell()
        if self._buffer.tell() > self.end:
            return self._buffer.tell() - self.end
        return self.length - (self.end - self._buffer.tell())
    def __len__(self):
        if not self.filled:
            return self.end
        return self.length
    def seek(self,position,whence=0):
        if whence == 0:
            if self.filled:
                position = self.end + position
        elif whence == 1:
            position = self._buffer.tell() + position
            if position > self.length or position < 0:
                raise EOFError('Tring to seek before beginning ' + 
                               'or past ending of file')
        elif whence == 2:
            if position > 0:
                raise EOFError('Trying to seek past end of file')
            position = self.end + position
        if position > self.length:
            position -= self.length
        if position > self.end:
            raise EOFError()
        self._buffer.seek(position)
    def read(self,count=None):
        position = self._buffer.tell()
        if count == None:
            if position <= self.end:
                count = self.end - position
            else:
                count = self.length - position + self.end
        if not self.filled:
            if position + count > self.end:
                return self._buffer.read(position - self.end)
            return self._buffer.read(count)
        data = ''
        if position + count > self.length:
            data = self._buffer.read(self.length - position)
            self._buffer.seek(0)
        if count + len(data) > self.length:
            return data + self._buffer.read(self.length - len(data))
        return data + self._buffer.read(count - len(data))
    def write(self,data):
        if len(data) > self.length:
            raise EOFError('Writing too much data from current postition')
        position = self._buffer.tell()
        end = position + len(data)
        if not self.filled:
            if end > self.length:
                self._buffer.write(data[0:self.length-position])
                data = data[self.length-position:]
                self._buffer.seek(0)
                self.end = 0
            self._buffer.write(data)
            if self._buffer.tell() > self.end:
                self.end = self._buffer.tell()
        else:  
            if end > self.length:
                self._buffer.write(data[0:self.length-position])
                data = data[self.length-position:]
            self._buffer.write(data)
            if position < self.end and end > self.end:
                self.end = self._buffer.tell()
            elif (position > self.end and \
                  end > self.length and \
                  end - self.length > self.end):
                self.end = self._buffer.tell()
        if end >= self.length:
            self.filled = 1
    def append(self,data):
        self.seek(0,2)
        self.write(data)
    def readline(self):
        data = array.array('c')
        while '\n' not in data:
            data.fromstring(self.read(1))
            if len(data) > self.length:
                raise EOFError('Reading past end of file')
        return data.tostring()
    def flush(self):
        self._buffer.flush()
    def close(self):
        self._buffer.close()
##
# @todo These functions don't belong here.  Just saving for idea.
def formatted_output(columns):
    return reduce(Column.to_string,columns)
def values(columns):
    return map(Column.to_value,columns)
