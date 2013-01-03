"""
Copyright (C) 2003 2006 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
                                                                                
                                                                                
import time
#import exercise
import aero
import struct
                                                                                
class scs(aero.aero):
    def __init__(self, port):
        #m = exercise.mpx()
        # Broadcast address
        self.all = '\xff\xff\xff\xff\xff\xff'                                                                        
        print 'Initializing serial port'
        aero.aero.__init__(self, port)
                                                                                
        print 'Starting receiver thread'
        self.start()
                                                                                
        print 'Resetting the tranceiver'
        self.reset()
        time.sleep(1)
                                                                                
        print 'Enabling the tranceiver'
        self.rf_enable()
        time.sleep(8)
                                                                                
        print 'Aerocomm software version %s' % self.get_version()
        time.sleep(1)

        self.addr = self.get_address()
        print 'Aerocomm wireless address %s' % self.hexdump(self.addr)
        time.sleep(1)
        print
        print 'Discovering Fitness Equipment Units'
        self.sendto(self.all, self.addr, '\xf1\x00\x00\xf2')
        time.sleep(1)
        # Discard responses
        self.rf_event.clear()
        self.update_device_list()
        self.show_devices()

    #def send_command(self, dest, command):
        #if command[0] != '\x00':
            #checksum = self.checksum(command)
            #command += '%c' % checksum
            #frame_contents = ''
            #for byte in command:
                #if byte in ('\xf0', '\xf1', '\xf2', '\xf3'):
                    #frame_contents += '\xf3%c' % (ord(byte) & 0x03)
                #else:
                    #frame_contents += byte
        #else:
            #frame_contents = command

        #self.sendto(dest, self.addr, '\xf1' + frame_contents + '\xf2')
        #time.sleep(0.1)
        #while self.check() == 1:
            #addr, msg = self.recv()
            #if msg[0] != '\xf1':
                #return msg
            #else:
                #print 'FEU %s sent %s' % (self.hexdump(addr), self.hexdump(msg))
                #if ord(msg[1]) & 0x80:
                    #return msg
                #else:
                    #print 'FEU state change'
        
        
        

    #def mainloop(self):
        ## First discard any pending response
        #self.rf_event.clear()
        #while 1:
            #for feu in self.devices:
                #print 'Polling FEU %s' % self.hexdump(feu)
                #msg = self.send_command(feu, '\x00')
                #print 'Status = %2.2x' % ord(msg[0])
                #msg = self.send_command(feu, '\xaa')
                #print 'Response = %s' % msg
                #time.sleep(1)

