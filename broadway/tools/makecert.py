"""
Copyright (C) 2002 2006 2009 2011 Cisco Systems

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
import sys
import string
import os
from mpx.lib.exceptions import ENotImplemented

def create_from_file(configfile, keyfile, outfile):
    out,inp = os.popen4('openssl req -config %s -new -key %s -x509' % \
                        (configfile,keyfile) + \
                        ' -sha1 -days 3650 -out %s || exit $?' % outfile)
    inp.read()

def get_fingerprint(certfile):
    out,inp = os.popen4( 'openssl x509 -noout -in %s' % certfile + ' -fingerprint' )

    return inp.read()

def create_from_string(instring, outfile, keyfile):
    ENotImplemented('Use the create from file function instead')

if __name__ == '__main__':
    if '-h' in sys.argv:
        print 'Syntax:'
        print '\tmakecert --key keyfile --config configfile --out outfile'
        print 'Where config is the file containing the configuration ' + \
              'information to be used in making the certificate and outfile ' + \
              'is the file where the certificate will be written to and keyfile ' + \
              'is the file that holds the private key to be used when generating ' + \
              'the certificate.'
    else:
        configfile = sys.argv[sys.argv.index('--config') + 1]
        outfile = sys.argv[sys.argv.index('--out') + 1]
        keyfile = sys.argv[sys.argv.index('--key') + 1]
        create_from_file(configfile, keyfile, outfile)
