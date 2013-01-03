"""
Copyright (C) 2002 2003 2004 2010 2011 Cisco Systems

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
import os.path
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.ion.host.port import Port
from mpx.lib.configure import REQUIRED, set_attribute, set_attributes
from mpx.lib.configure import get_attribute

# These are characters that we will allow in the dialing string (after atd).
# Note: Didn't include semi-colon (;) although it is listed as
#       an acceptable character in a dialing string because it
#       looks like it might be more "dangerous" than it is worth.
allowed_dialing_chars = ['*', '#', 'A', 'B', 'C', 'D', 'L',
                         'P', 'T', 'R', 'S', '=', '!', 'W',
                         '@', '&', ',' '^', '>']
silent_strip_chars    = ['-', '(', ')', ' ']                 # These are cosmetic

# Mix-in class to represent attributes specific to a modem.
class Modem:
    def __init__( self, port ):
        self.port = port
        
    def configure( self, config_dict ):
        set_attribute( self, 'init_string', 'AT&C1&D2', config_dict )
        set_attribute( self, 'reset_string', 'ATZ', config_dict )
        return 
    def configuration( self, config_dict ):
        get_attribute( self, 'init_string', config_dict )
        get_attribute( self, 'reset_string', config_dict )
        return config_dict
    def getChatScript( self, comment, phone_number ):
        self.edited_phone = ''
        self.banned_chars = ''
        if len( phone_number ) > 0:
            for ch in phone_number:
                if not ch in silent_strip_chars:
                    if ch.isdigit() or ch in allowed_dialing_chars:
                        self.edited_phone += ch
                    else:
                        self.banned_chars += ch
        if self.banned_chars:
            self._msglog( 'Got banned char(s) of %s.' % self.banned_chars )
        initializer = "# Note: no modem initialization string\n"
        if self.init_string:
            initializer = "OK %s\n" % self.init_string
            
        # This script introduces a 6 second delay after the connection is made.
        # Apparantly this is required with some servers (notably Canadian) to
        # avoid getting "connection is not 8-bit clean" errors.
        chat_script = [comment,
                       "REPORT ''\n",
                       "ABORT 'BUSY'\n",
                       "ABORT 'NO CARRIER'\n",
                       "ABORT 'NO DIALTONE'\n",
                       "'' %s\n" % self.reset_string,
                       initializer,
                       "OK ATDT%s\n" % self.edited_phone,
                       "CONNECT \\d\\d\\d\\d\\d\\d\\c\n"]
        return chat_script

    def _msglog( self, msg ):
        if self.__dict__.has_key( 'debug' ) and self.debug:
            msglog.log( 'broadway.mpx.ion.host.modem', msglog.types.DB, msg )


# Derived from Port, parent node is Host
class InternalModem( Port, Modem ):
    def __init__( self ):     
        Port.__init__( self )
        Modem.__init__( self, self )
        
    def configure( self, config_dict ):     
        Port.configure( self, config_dict )
        Modem.configure( self, config_dict )
        self._msglog( 'Configured internal modem %s' % self.dev )
       
    def configuration( self ):
        return Modem.configuration( self, Port.configuration( self ) )

    def start( self ):
        Port.start( self )
        self._msglog( 'Started internal modem %s' % self.dev )


# Parent node is a Port (comm port)
class ExternalModem( CompositeNode, Modem ):
    def __init__( self ):
        CompositeNode.__init__( self )
        Modem.__init__( self, None )
              
    def getFlowControlName( self ):
        return self.fc_name_map[self.parent.flow_control]
            
    def getSpeed( self ):
        return self.parent.baud

    def configure( self, config_dict ):
        CompositeNode.configure( self, config_dict )
        Modem.configure( self, config_dict )
        self.port = self.parent
        self._msglog( 'Configured external modem %s' % self.port.dev )
        
    def configuration( self ):
        return Modem.configuration( self, CompositeNode.configuration( self ) )

    def start( self ):
        CompositeNode.start( self )
        self._msglog( 'Started external modem %s' % self.port.dev )

class RedwingModem( ExternalModem ):
    def __init__( self ):
        ExternalModem.__init__( self )

    ##
    # Overrides Modem method.
    #
    def getChatScript( self, comment, phone_number ):
        # NOTE: phone number is ignored for this modem
        chat_script = [comment,
                       "REPORT ''\n",
                       "ABORT 'NO DIALTONE'\n",
                       "'' %s\n" % self.init_string,
                       "OK ATDT10001\n",
                       "CONNECT ''\n"]
        return chat_script

    def override_outgoing_ppp_options( self, podict ):
        # NOTE: user ID is ignored for this modem
        podict['userid'] = ''
