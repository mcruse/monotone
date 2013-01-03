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
##
## This module defines classes to are used to manipulate select Linux configuration files.
##
import string, os
from mpx import properties


#
# Base class for config file editors.
#
class ConfigFile:
    # Load the config file into the line buffer.
    def __init__( self, fileName ):
        self.fileName = fileName
        self.lines = []
        try:
            f = open( fileName, 'r' )
            self.lines = f.readlines()
            f.close()
        except:
            pass
        
    # Skip blank lines and comments.  Returns -1 to indicate EOF.
    def nextLineIndex( self, start = -1 ):
        start += 1
        while start < len( self.lines ):
            if not self.lines[start].startswith( '#' ):
                if not self.lines[start].isspace():
                    return start;
            start += 1
        return -1

    # Save the line buffer to the config file.
    def save( self ):
        f = open( self.fileName, 'w' )
        f.writelines( self.lines )
        f.close()

#
# See mgetty.info for details
#
class MgettyConfig( ConfigFile ):
    def __init__( self, fileName = properties.MGETTY_CONFIG_FILE ):
        ConfigFile.__init__( self, fileName )
    
    def _findPort( self, port ):
        port_slice = None
        for i in range( len( self.lines ) ):
            curline = self.lines[i]
            if curline.startswith( 'port' ):
                if port_slice != None:
                    # Found the next group, bail
                    break
                else:
                    # Found the start of a group, is it the one we are
                    # looking for?
                    tmp = curline.split()
                    if tmp[1] == port:
                        # Yes it is, start keeping track.
                        port_slice = [i, i]
            elif port_slice != None:
                # If we've gotten to a blank line, then return without
                # incrementing port_slice because we don't want to
                # remove the blank line before the next group.
                if len(string.strip(curline)) == 0:
                    break
                else:
                    # Otherwise update the end of the slice.
                    port_slice[1] = i
        return port_slice
        
    def removePort( self, port ):
        port_slice = self._findPort( port )
        if port_slice:
            self.lines[port_slice[0] : port_slice[1] + 1] = []

    def addPort( self, port, lines, comment = None ):
        lines_to_add = []
        lines_to_add.append( 'port %s\n' % port )
        lines_to_add += lines.splitlines( 1 )
        
        port_slice = self._findPort( port )
        if port_slice:
            # Note: no logic to replace existing comments
            self.lines[port_slice[0] : port_slice[1] + 1] = lines_to_add
        else:
            self.lines.append( '\n' )
            if comment:
                self.lines += comment.splitlines( 1 )
            self.lines += lines_to_add
            
#
# Base class for tab-delimited config file editors.
#
class TabDelimitedConfigFile( ConfigFile ):
    def __init__( self, fileName ):
        ConfigFile.__init__( self, fileName )

    # Return a tuple of the form (first_line, last_line) describing the block of
    # lines for the named key (the key is assumed to be the first entry on
    # the tab-delimited line).  Return (-1,-1) if key is not found.
    def _findLine( self, key ):
        iEnd = -1
        while 1:
            iEnd = self.nextLineIndex( iEnd )
            if iEnd < 0:
                break;
            tmp = self.lines[iEnd].split()
            if tmp[0] == key:
                break;

        # Look for a preceding, attached comment block.
        iBegin = iEnd
        while iBegin > 0 and self.lines[iBegin - 1].startswith('#'):
            iBegin -= 1
            
        return (iBegin, iEnd)
        
    def removeLine( self, key ):
        (iBegin, iEnd) = self._findLine( key )
        if iBegin >= 0:
            self.lines[iBegin : iEnd + 1] = []
                        
    def addLine( self, key, *args, **kwargs):
        self.removeLine( key )
            
        line_to_add = key
        for x in args:
            line_to_add = line_to_add + '\t%s' % str(x)
        line_to_add = line_to_add + '\n'

        if kwargs.has_key('comment'):
            comment = kwargs['comment']
            if comment:
                self.addComment(comment)
        self.lines.append( line_to_add )

    def addComment (self, comment):
        self.lines += comment.splitlines( 1 )

#
# Format:
#	username userid utmp_entry login_program [arguments]
#
# Meaning:
#       for a "username" entered at mgettys login: prompt, call
#	"login_program" with [arguments], with the uid set to "userid",
#	and a USER_PROCESS utmp entry with ut_user = "utmp_entry"
#
# username may be prefixed / suffixed by "*" (wildcard)
#
# userid is a valid user name from /etc/passwd, or "-" to not set
#  a login user id and keep the uid/euid root (needed for /bin/login)
#
# utmp_entry is what will appear in the "who" listing. Use "-" to not
#  set an utmp entry (a must for /bin/login), use "@" to set it to the
#  username entered. Maximum length is 8 characters.
#
# login_program is the program that will be exec()ed, with the arguments
#  passed in [arguments]. A "@" in the arguments will be replaced with the
#  username entered. Warning: if no "@" is given, the login_program has
#  no way to know what user name the user entered.
#
# Example:
# /AutoPPP/ -	a_ppp	/usr/sbin/pppd auth -chap +pap login debug 10.1.2.3:10.3.4.5
#
class LoginConfig( TabDelimitedConfigFile ):
    def __init__( self, fileName ):
        TabDelimitedConfigFile.__init__( self, fileName )
    
    def removeUser( self, user ):
        return self.removeLine( user )
                        
    def addUser( self, user, userid, utmp_entry, login_program, _comment = None ):
        self.removeUser( user )

        savedUser = None
            
        # If the * user exists, keep the entry at the end of the list.
        (iBeginCatchAll, iEndCatchAll) = self._findLine( '*' )
        if iBeginCatchAll != -1:
            savedUser = self.lines[iBeginCatchAll : iEndCatchAll + 1]
            self.removeUser( '*' )
        TabDelimitedConfigFile.addLine( self, user, userid, utmp_entry,
                                        login_program, comment=_comment )

        if savedUser:
            self.lines.append( '\n' )
            self.lines += savedUser

    def save( self ):
        TabDelimitedConfigFile.save( self )

        # Prevent ppp LOGIN from complaining about this file's protection level.
        if os.access( self.fileName, os.F_OK ):
            os.chmod( self.fileName, (os.R_OK|os.W_OK) << 6 )

#
# Secrets for authentication using PAP.
# The format is:
#
#   client	server	secret	IP addresses
#
# Example:
#   pppuser	*	password	*
#
class PAPSecrets(  TabDelimitedConfigFile ):
    def __init__( self, fileName = properties.PAP_SECRETS_FILE ):
        TabDelimitedConfigFile.__init__( self, fileName )
        if len( self.lines ) == 0:
            self.lines = ["# Secrets for authentication using PAP\n",
                          "# client	server	secret			IP addresses\n",
                          "####### redhat-config-network will overwrite this part!!! (begin) ##########\n",
                          "####### redhat-config-network will overwrite this part!!! (end) ############\n",
                          "\n"]
        # Give the TabDelimitedConfigFile routines names which match our
        # purpose a little more closely.
        self.removeClient = self.removeLine
        self.addClient = self.addLine

#
# Secrets for authentication using CHAP.
# The format is:
#
#   client	server	secret	IP addresses
#
# Example:
#   pppuser	*	password	*
#
class CHAPSecrets( TabDelimitedConfigFile ):
    def __init__( self, fileName = properties.CHAP_SECRETS_FILE ):
        TabDelimitedConfigFile.__init__( self, fileName )
        if len( self.lines ) == 0:
            self.lines = ["# Secrets for authentication using CHAP\n",
                          "# client	server	secret			IP addresses\n",
                          "####### redhat-config-network will overwrite this part!!! (begin) ##########\n",
                          "####### redhat-config-network will overwrite this part!!! (end) ############\n",
                          "\n"]

        # Give the TabDelimitedConfigFile routines names which match our
        # purpose a little more closely.
        self.removeClient = self.removeLine
        self.addClient = self.addLine
    




