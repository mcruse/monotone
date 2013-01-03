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
# Provides the factory used to instantiate the ABB SCD2000 ION.

import array
import time
from base import buffer, crc
from mpx.lib import msglog
from mpx.lib.debug import dump_tostring
from mpx.lib.exceptions import *
from conversions import ConvertRegister, ConvertBitField, ConvertValue
from mpx.lib import msglog
from mpx.lib.threading import Lock

debug = 0
_module_lock = Lock()

function_enum = {1: 'read_coil',
                 2: 'read_input_status',
                 3: 'read_holding_register',
                 4: 'read_input_register',
                 5: 'force_single_coil',
                 6: 'write_single_register',
                 16: 'write_multiple_registers',
                 15: 'write_multiple_coils',
                 }

##
# @todo Speed up timeouts on missing devices
# @todo Have modbus parity check on start

##
# Modules the SCD2000 as an ION.
class Server:
    def __init__(self):
        self.debug = debug
        self.map = {}
    def add_register_to_map_for(self, register, node):
        if not self.map.has_key(register):
            self.map[register] = []
        self.map[register].append(node)
    def perform_command(self, cmd):
        _module_lock.acquire()
        try:
            try:
                if   (cmd.function == 1) or (cmd.function == 2): #read coil / input status
                    base_register = 1
                    if cmd.function == 2: base_register = 10001
                    if len(cmd.buffer) > 5:
                        register = cmd.register()
                        count = cmd.count()
                        answer = ConvertValue()
                        for i in range(register,register+count):
                            if self.debug: print '>>>> MODBUS Read coil offset: ' + str(i)
                            value = 0
                            if self.map.has_key(i+base_register):
                                for r in self.map[i+base_register]:
                                    value |= int(r.read())
                            answer.convert_bits(value)
                        if self.debug: print 'server response: ', register, count, answer
                        response = ServerReadResponse(cmd.slave_address, cmd.function, None)
                        response.buffer += chr((count + 7) / 8)
                        response.buffer += answer.collapsed_buffer()
                        return response
                elif (cmd.function == 3) or (cmd.function == 4): #read holding registers
                    base_register = 40001
                    if cmd.function == 4: base_register = 30001
                    if len(cmd.buffer) > 5:
                        register = cmd.register()
                        count = cmd.count()
                        answer = []
                        for i in range(register,register+count):
                            if self.debug: print '>>>> MODBUS Read offset: ' + str(i)
                            #combine the outputs of all nodes that contribute to this register
                            value = [0,0]
                            if self.map.has_key(i+base_register):
                                nodes = self.map[i+base_register]
                                force = len(nodes) > 1
                                for r in nodes:
                                    val_list = r.read(i)
                                    value[0] |= val_list[0]
                                    value[1] |= val_list[1]
                            answer.extend(value)
                        if self.debug: print 'server response: ', register, count, answer
                        return ServerReadResponse(cmd.slave_address, cmd.function, answer)
                elif cmd.function == 5: #force single coil
                    if len(cmd.buffer) > 5:
                        register = cmd.register()
                        value = cmd.word_at(4)
                        if value: value = 1
                        if self.map.has_key(register+1):
                            for r in self.map[register+1]:
                                r.write(value != 0)
                        else:
                            return ErrorResponse(cmd.slave_address, cmd.function, 2) #ILLEGAL DATA ADDRESS
                        return ServerWriteResponse(cmd)
                elif cmd.function == 6: #write single register
                    if len(cmd.buffer) > 5:
                        register = cmd.register()
                        if self.map.has_key(register+40001):
                            nodes = self.map[register+40001]
                            force = len(nodes) > 1
                            for r in nodes:
                            #for r in self.map[register+40001]:
                                r.write(register, cmd.buffer[4:6])
                                if force: #if more than one node at this register, force update to value
                                    r.convert_buffer_to_value()
                                    r.buffer = None
                        else:
                            return ErrorResponse(cmd.slave_address, cmd.function, 2) #ILLEGAL DATA ADDRESS
                        return ServerWriteResponse(cmd)
                elif cmd.function == 16: #write multiple registers
                    if len(cmd.buffer) > 6:
                        register = cmd.register()
                        if self.debug: print 'register', str(register)
                        count = cmd.count()
                        if self.debug: print 'count', str(count)
                        for i in range(0, count):
                            byte_offset = i*2 + 7
                            if self.debug: print '>>>> MODBUS write offset: ' + str(register+i)
                            if self.map.has_key(register+i+40001):
                                nodes = self.map[register+i+40001]
                                for r in nodes:
                                    if self.debug:
                                        print 'node', str(r), str(register+i), str(cmd)
                                        print repr(cmd.buffer)
                                        print str(byte_offset)
                                        print repr(cmd.buffer[byte_offset:byte_offset+2])
                                        print type(cmd.buffer[byte_offset:byte_offset+2])
                                        #print repr(cmd.buffer[byte_offset:byte_offset+2].tostring())
                                        #print repr(r.write)
                                        print 'about to write'
                                    r.write(register+i, cmd.buffer[byte_offset:byte_offset+2]) #.tostring())
                                    if self.debug: print 'finished write'
                            else:
                                return ErrorResponse(cmd.slave_address, cmd.function, 2) #ILLEGAL DATA ADDRESS
                        if self.debug: print 'server response: ', register, count #, answer
                        return ServerWriteResponse(cmd)
                elif cmd.function == 15: #write multiple coils
                    if len(cmd.buffer) > 6:
                        register = cmd.word_at(2)
                        count = cmd.word_at(4)
                        for i in range(0, count):
                            byte_offset = (i/8) + 7
                            bit_offset = i & 0x7
                            if self.debug: print '>>>> MODBUS write offset: ' + str(register+i)
                            if self.map.has_key(register+i+1):
                                value = ord(cmd.buffer[byte_offset]) & (1 << bit_offset)
                                for r in self.map[register+i+1]:
                                    r.write(value != 0)
                            else:
                                return ErrorResponse(cmd.slave_address, cmd.function, 2) #ILLEGAL DATA ADDRESS
                        if self.debug: print 'server response: ', register, count, answer
                        return ServerWriteResponse(cmd)
                if self.debug: print 'Modbus device: Error response sent', cmd.buffer
                return ErrorResponse(cmd.slave_address, cmd.function + 128, 1)
            except:
                msglog.exception()
                if self.debug: print 'modbus server exception during command'
                return ErrorResponse(cmd.slave_address, cmd.function + 128, 4)
        finally:
            _module_lock.release()
        
class ServerCommand:
    def __init__(self, *args, **keywords):
        self.response = None
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        else:
            raise ETypeError('requires decode')
    def decode(self, buffer):
        self.buffer = buffer
        if len(buffer) < 2:
            raise EInvalidValue
        self.slave_address = self.byte_at(0)
        self.function = self.byte_at(1)
    def word_at(self, index):
        answer = ord(self.buffer[index]) << 8
        answer += ord(self.buffer[index+1])
        return answer
    def byte_at(self, index):
        return ord(self.buffer[index])
    def register(self):
        return self.word_at(2)
    def count(self):
        return self.word_at(4)
    def byte_count(self):
        return self.byte_at(6)
    def __str__(self):
        answer = ''
        answer += 'slave_address: ' + str(self.slave_address)
        answer += ' function: '
        if function_enum.has_key(self.function):
            answer += function_enum[self.function]
        else:
            answer += 'unknown: ' + str(self.function)
        answer += ' register: '
        try:
            answer += str(self.register())
        except:
            answer += ' exception on register '
        answer += ' count: '
        try:
            answer += str(self.count())
        except:
            answer += ' exception on count'
        return answer

class _Server_Response:
    def append_crc(self):
        #append a crc character to an existing response string
        buffer = array.array('B')
        buffer.fromstring(self.buffer)
        x = crc(buffer)
        buffer.append(x & 0xFF)
        buffer.append(x >> 8)
        self.crc = x
        self.buffer = buffer.tostring()
        
class ServerReadResponse(_Server_Response):
    def __init__(self, id, function, values=None):
        buffer = array.array('B')
        buffer.append(id)
        buffer.append(function)
        if not values is None:
            buffer.append(len(values))
            buffer.fromlist(values)
        self.buffer = buffer.tostring()
##
# The response to write commands is to echo back the first 6 bytes
class ServerWriteResponse(_Server_Response):
    def __init__(self, cmd):
        self.buffer = cmd.buffer[:6]
#"""
    #Exceptions
    #01 ILLEGAL FUNCTION      The function code received in the query
                             #is not an allowable action for the slave.
                             #If a Poll Program Complete command
                             #was issued, this code indicates that no
                             #program function preceded it.
    #02 ILLEGAL DATA ADDRESS  The data address received in the query
                             #is not an allowable address for the
                             #slave.
    #03 ILLEGAL DATA VALUE    A value contained in the query data
                             #field is not an allowable value for the
                             #slave.
    #04 SLAVE DEVICE FAILURE  An unrecoverable error occurred while
                             #the slave was attempting to perform the
                             #requested action.
    #05 ACKNOWLEDGE           The slave has accepted the request
                             #and is processing it, but a long duration
                             #of time will be required to do so. This
                             #response is returned to prevent a
                             #timeout error from occurring in the
                             #master. The master can next issue a
                             #Poll Program Complete message to
                             #determine if processing is completed.
    #06 SLAVE DEVICE BUSY     The slave is engaged in processing a
                             #long duration program command. The
                             #master should retransmit the message
                             #later when the slave is free.
    #07 NEGATIVE ACKNOWLEDGE  The slave cannot perform the program
                             #function received in the query. This
                             #code is returned for an unsuccessful
                             #programming request using function
                             #code 13 or 14 decimal. The master
                             #should request diagnostic or error
                             #information from the slave.
    #08 MEMORY PARITY ERROR   The slave attempted to read extended
                             #memory, but detected a parity error in
                             #the memory. The master can retry the
                             #request, but service may be required on
                             #the slave device.
#"""
class ErrorResponse(_Server_Response):
    def __init__(self, id, function, error_code):
        buffer = array.array('B')
        buffer.append(id)
        buffer.append(function)
        buffer.append(error_code)
        self.buffer = buffer.tostring()
        

        
   
