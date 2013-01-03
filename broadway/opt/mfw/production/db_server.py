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
#=----------------------------------------------------------------------------
# db_server.py
#
# Wait for a barcode to be scanned in, quiz the database, and return vitals
# to the waiting mediator.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import socket
import sys

from db_lib import *

#=- Ok GO! -------------------------------------------------------------------

def main():
    config_string = "07-00101:0003bd"

    scanner = open('/dev/ttyS1', 'r+', 0)

    database = 'prodtest'
    dbuser = 'dba'
    dbhost = 'postgres.encorp.com'

    pdb = ProductDB(database, dbhost, dbuser)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 50007))
    s.listen(1)

    #
    # TBD: This is pretty much a sit-n-spin brute force approach.  We
    #      could probably make this more elegant by using non-blocking
    #      calls...
    #
    while 1:
        serialno = ''
        mac0_cfg = ''
        mac1_cfg = ''
        mediator_cfg = ''

        print 'Waiting for barcode scanner input... ',
        sys.stdout.flush()
        serialno = scanner.read(10).strip()
        print 'read \"%s\"' % serialno
        sys.stdout.flush()

        mac0, mac1 = pdb.get_macs(serialno)

        by0, by1, by2, by3, by4, by5 = mac0.split(":")
        mac0_cfg = '%s%s%s' % (by3, by4, by5)

        if not mac1 == "":
            by0, by1, by2, by3, by4, by5 = mac1.split(":")
            mac1_cfg = '%s%s%s' % (by3, by4, by5)

        mediator_cfg = '%s:%s:%s' % (serialno, mac0_cfg, mac1_cfg)
        conn, addr = s.accept()
        print 'Accepting connection from ', addr
        while 1:
            data = conn.recv(64)
            if not data:
                # Socket closed probably by mediator.
                break
            else:
                if data == 'GreetZ_1138':
                    # TBD: Change state to 'Test' from 'WIP'
                    print 'Got the proper greeting, sending serial and MAC\'s'
                    conn.send(mediator_cfg)

    conn.close()
    s.close()
    scanner.close()
    
    return 1

if __name__ == '__main__':
    exit_status = not main()
    sys.exit(exit_status)

#=- EOF ----------------------------------------------------------------------
