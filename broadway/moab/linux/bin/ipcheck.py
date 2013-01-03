"""
Copyright (C) 2002 2003 2005 2007 2011 Cisco Systems

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
import getopt
import os, sys
import urllib, httplib, socket
import base64, re
import time

from mpx.lib import msglog, exceptions
#from moab.linux.lib.routing import RoutingTable

_MODULE_VERSION = "$Revision: 20844 $" # Revision number assigned by CVS

# Extract a program version from the module version.
VersionGrep = re.compile( '\d+(\.\d)+' )
_PROG_VERSION = VersionGrep.search( _MODULE_VERSION )
if _PROG_VERSION:
    _PROG_VERSION = _PROG_VERSION.group()
else:
    _PROG_VERSION = '0.0'

# Regular expression for addresses.
AddressGrep = re.compile( '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' )

class EHostNameError( exceptions.MpxException ):
    # This exception indicates that a problem was detected with a host name.
    pass

class EIpDectionError( exceptions.MpxException ):
    # This exception indicates that a problem was encountered while trying to detect
    # the WAN address.
    pass

class EConnectError( exceptions.MpxException ):
    # This exception indicates that a problem was detected with a host name.
    pass

class Logger:
    def __init__( self, progName, isVerbose, isDebug ):
        self.progName = progName
        self.isVerbose = isVerbose
        self.isDebug = isDebug
    
    def logError( self, msg ):
        msglog.log( self.progName, msglog.types.ERR, msg )
        self.logDebug( "ERROR: " + msg )

    def logInfo( self, msg ):
        if self.isVerbose:
            msglog.log( self.progName, msglog.types.INFO, msg )  
        self.logDebug( "INFO: " + msg )

    def logDebug( self, msg ):
        if self.isDebug:
            print "DEBUG: %s: %s" % (self.progName, msg)

##
# Base class that encapsulates a dynamic DNS service.
##
class DynamicDnsService:
    SECONDS_PER_DAY = 24 * 60 * 60
    
    def __init__( self, account, password, hostname, logger ):
        self.account = account
        self.password = password
        self.hostname = hostname
        self.logger = logger
        
        try:
            hostip = socket.gethostbyname( hostname )
        except socket.gaierror, e:
            erc, msg = e
            raise EHostNameError( "Cannot resolve host name '%s'. %s." % (hostname, msg) )
    
    def check_ip( self, localip ):
        octets = localip.split('.')
        if len( octets ) != 4:
            # check the IP to make sure it is sensible
            raise EHostNameError( "Malformed IP address '%s'" % localip )

        try:
            for i in range( 4 ):
                n = int( octets[i] )
                if n < 0 or n > 255:
                    raise SyntaxError
                octets[i] = n
        except:
            raise EHostNameError( "Malformed IP address '%s'" % localip )
        
        if self._is_private_ip( octets ):
            raise EHostNameError( "'%s' is a private intranet address" % localip )

    # _is_private_ip verifies that given ip address does not belong to 
    # one of those private ip address spaces, which are reserved for
    # intranet use.
    def _is_private_ip( self, octets ):
        if octets[0] == 127 or octets[0] == 172 or octets[0] == 10 or octets[0] == 0:
            return 1
        if octets[0] == 192 and octets[1] == 168:
            return 1
        return 0
    
    def isRefreshTime( self, lastTime ):
        return 0
    
    def getWanAddressFromWebQuery( self ):
        raise NotImplementedError
  
    def UpdateHostAddress( self, account, password, hostname ):
        raise NotImplementedError
    
##
# dyndns.org
##
class DynDnsDotOrg( DynamicDnsService ):
    DYNDNS_HOST = "members.dyndns.org"
    DYNDNS_UPDATE_PAGE = "/nic/update"
    DYNDNS_USER_AGENT = "ipcheck/" + _MODULE_VERSION
    DYNDNS_EXPIRE_DAYS = 25      # days after which to force an update
    DYNDNS_QUERY_URL = "http://checkip.dyndns.org:8245"
    
    SYSTEM_DYNAMIC = 0
    SYSTEM_CUSTOM = 1
    SYSTEM_STATIC = 2

    def __init__( self, account, password, hostname, logger ):

        DynamicDnsService.__init__( self, account, password, hostname, logger )
        
        self.proxy = 0
        
        # The following service-specific data could, in the future, come from an account file.
        self.system = self.SYSTEM_DYNAMIC
        self.offline = 0
        self.guess = 0
        self.wildcard = 0
        self.backupmx = 0
        self.alt_port = 8254
        self.mx = None
        self.useHttps = 0

    #
    # Query the web-based service for our WAN address.  The returned data
    # looks like this:
    #    <html><head><title>Current IP Check</title></head>
    #    <body bgcolor=white text=black>
    #    Current IP Address: 206.72.74.82
    #    <br>Hostname: dyndns1.envenergy.com
    #    </body></html>
    #
    def getWanAddressFromWebQuery( self ):
        try:
            urlFile = urllib.urlopen( self.DYNDNS_QUERY_URL )
            queryResult = urlFile.read()
            urlFile.close()
        except:
            raise EIpDectionError( "Unable to open %s, exception = %s"
                                   % (self.DYNDNS_QUERY_URL, sys.exc_info()[0] ) )
         
        # Grab first thing that looks like an IP address.
        myIP = AddressGrep.search( queryResult )
        if myIP != None:
            myIP = myIP.group()
            self.logger.logInfo( "Detected IP = " + myIP )
        else:
            raise EIpDectionError( "Unable to detect IP address, query result = " + queryResult )
            
        return myIP
    
    def _getUpdateString( self, myIP ):
        updateString = self.DYNDNS_UPDATE_PAGE
        
        if self.system == self.SYSTEM_STATIC:
            updateString += "?system=statdns&hostname="
        elif self.system == self.SYSTEM_CUSTOM:
            updateString += "?system=custom&hostname="
        else:
            updateString += "?system=dyndns&hostname="
            
        updateString += self.hostname

        if self.offline:
            updateString += "&offline=YES"
        else:
            if not self.guess:
                updateString += "&myip=" + myIP 
      
            # Custom domains do not have wildcard or mx records.
            if self.system != self.SYSTEM_CUSTOM:
                if self.wildcard:
                    updateString += "&wildcard=ON"
                else:
                    updateString += "&wildcard=OFF"
  
                if self.backupmx:
                    updateString += "&backmx=YES"
                else:
                    updateString += "&backmx=NO"
  
                if self.mx:
                    updateString += "&mx=" + self.mx

        return updateString
    
    def _openNormalConnection( self ):
        h2 = None
        try:
            if not self.proxy:
                h2 = httplib.HTTP( self.DYNDNS_HOST )
            else:
                h2 = httplib.HTTP( self.DYNDNS_HOST, self.alt_port )
            self.logger.logDebug( "HTTP connection successful" )
        except:
            self.logger.logDebug( "HTTP connection error %s: %s"
                                  % (sys.exc_info()[0], sys.exc_info()[1]) )
        return h2
    
    def _openSecureConnection( self ):
        h2 = None
        try:
            if not self.proxy:
                h2 = httplib.HTTPS( self.DYNDNS_HOST )
            else:
                h2 = httplib.HTTPS( self.DYNDNS_HOST, self.alt_port )
            self.logger.logDebug( "HTTPS connection successful" )
        except:
            self.logger.logDebug( "HTTPS connection error %s: %s"
                                  % (sys.exc_info()[0], sys.exc_info()[1]) )
        return h2
    
    ##
    # lastTime - time of last update, expressed as seconds since epoch, UTC.
    ##
    def isRefreshTime( self, lastTime ):
        elapsed_seconds = time.time() - lastTime
        elapsed_days = int( elapsed_seconds / self.SECONDS_PER_DAY )
        self.logger.logDebug( "days since last update = %s" % elapsed_days )
        return elapsed_days > self.DYNDNS_EXPIRE_DAYS
    
    ##
    # Returns true (1) if successful, false (0) otherwise.
    # Raises EConnectError if unable to connect to host.
    ##
    def UpdateHostAddress( self, myIP ):
        updateString = self._getUpdateString( myIP )
        self.logger.logDebug( "Update string = " + updateString )
      
        connection = None
        if self.useHttps:
            connection = self._openSecureConnection()
        if not connection:
            connection = self._openNormalConnection()
        if not connection:
            raise EConnectError( "Unable to connect to " + self.DYNDNS_HOST )

        connection.putrequest( "GET", updateString )
        connection.putheader( "HOST", self.DYNDNS_HOST )
        connection.putheader( "USER-AGENT", self.DYNDNS_USER_AGENT )
        authstring = base64.encodestring( "%s:%s" % (self.account, self.password) )
        authstring.replace( "\012", "" )
        connection.putheader( "AUTHORIZATION", "Basic " + authstring )
        connection.endheaders()
      
        # Get the reply and abort if not successful (status code != 200)
        errcode, errmsg, headers = connection.getreply()
        self.logger.logDebug( "HTTP reply = %s: %s" % (errcode, errmsg) )
        if errcode != 200:
            self.logger.logError( "HTTP error %s: %s" % (errcode, errmsg) )
            return 0
      
        # Get the html text
        fp = None
        try:
            fp = connection.getfile()
            httpdata = fp.read()
        except:
            self.logDebug( "Caught %s: %s" % (sys.exc_info()[0], sys.exc_info()[1]) )
            httpdata = "No output from HTTP request."
        if fp:
            fp.close()
        self.logger.logDebug( "HTML text = %s" % httpdata )
      
        # Error if "good" not found in response.
        if httpdata.find( "good" ) == -1:
            self.logger.logError( "Update failed, service response was: " + httpdata )
            return 0
        
        # Good return
        self.logger.logInfo( self.hostname + " successfully updated" )
        return 1


class PersistantStore:
    def __init__( self, dir, logger ):
        self.logger = logger
        self.fileName = os.path.join( dir, logger.progName ) + '.data'
        self._hostip = ""
        self._timestamp = 0
        self._errorCode = 0
        
        if os.access( self.fileName, os.R_OK ):
            f = open( self.fileName, 'r' )
            contents = f.readlines()
            f.close()
            
            data = contents[0].strip().split(':')
            if len( data ) != 3:
                self._errorCode = -1
                self.logger.logError( "Bad format for %s; data = %s" % (self.fileName, contents[0]) )
            else:
                self._hostip = data[0]
                self._timestamp = float( data[1] )
                self._errorCode = int( data[2] )
                self.logger.logDebug( "read from %s: %s" % (self.fileName, str( data )) )
        else:
            self._timestamp = time.time()
            self.logger.logDebug( self.fileName + " not found and will be created" )
            
    def getHostIp( self ):
        return self._hostip
    
    def getLastUpdateTime( self ):
        return self._timestamp
    
    def getErrorCode( self ):
        return self._errorCode
    
    def update( self, errorCode, ip = None ):
        self.logger.logDebug( "updating %s" % self.fileName )
        
        if ip:
            self._hostip = ip
            
        f = open( self.fileName, "w" )
        f.write( "%s:%s:%s\n" % (self._hostip, time.time(), errorCode) )
        f.close()


def Usage( progname, msg = None ):
    if msg:
        print msg
    print """usage  : %s [options] username password hostname

options: -a address     manually specify the address
         -e             ignore previously encountered errors
         -i interface   interface name (currently ignored)
         -d             enable debugging
         -f             force update regardless of current state 
         -p dir         directory to use for persistant storage (default is .)
         -v             verbose mode 
""" % progname
    return -1  # For convenience

##
# Returns status code, 0 if successful, -1 otherwise.
##
def _check_ip( argc, argv ):
    opt_address = None
    opt_interface = None
    opt_debug = 0
    opt_force = 0
    opt_persistDir = "."
    opt_verbose = 0
    opt_ignoreErrs = 0
  
    tmp = argv[0].split( "/" )
    thisProg = tmp[len( tmp ) - 1]
    
    print "%s v%s " % (thisProg, _PROG_VERSION)

    #
    # Parse the command line.
    #
    if argc == 1:
        return Usage( thisProg )
    
    try:
        charopts = "a:defi:p:v"
        wordopts = ["address=", "debug", "force", "interface=", "pdir=", "verbose"]
        opts, args = getopt.getopt( argv[1:], charopts, wordopts )
    except getopt.error, reason:
        return Usage( thisProg, reason )

    for opt in opts:
        (oname, oval) = opt
        if oname == "-a" or oname == "--address":
            opt_address = oval
        elif oname == "-d" or oname == "--debug":
            opt_debug = 1
        elif oname == "-f" or oname == "--force":
            opt_force = 1
        elif oname == "-i" or oname == "--interface":
            opt_interface = oval
        elif oname == "-p" or oname == "--pdir":
            if os.path.isdir( oval ):
                opt_persistDir = oval
            else:
                print "Invalid directory in %s option: %s" % (oname, oval)
                return -1
        elif oname == "-v" or oname == "--verbose":
            opt_verbose = 1
        elif oname == "-e":
            opt_ignoreErrs = 1
            
    if len( args ) < 3:
        return Usage( thisProg, "Missing arguments" )

    arg_acctname = args[0]
    arg_password = args[1]
    arg_hostname = args[2]

    #
    # Create the logger.
    #
    logger = Logger( thisProg, opt_verbose, opt_debug )
    
    #
    # Retrieve persistant data.
    #
    prev = PersistantStore( opt_persistDir, logger )
    if prev.getErrorCode() != 0 and not opt_ignoreErrs:
        logger.logError( "Unable to procede until previous errors are corrected" )
        return -1
    
    #
    # Create the dynamic DNS service handler and determine the local machine's IP address
    # using the service's prefered web-based detection scheme.
    #
    try:
        dyn = DynDnsDotOrg( arg_acctname, arg_password, arg_hostname, logger )
        if opt_address:
            dyn.check_ip( opt_address )
        else:
            opt_address = dyn.getWanAddressFromWebQuery()
    except (EHostNameError, EIpDectionError), e:
        logger.logError( str( e ) )
        return -1

    #
    # Update the IP address if forced to, or if it changed, or if expiration is eminent.
    #
    if opt_force or (prev.getHostIp() != opt_address) or dyn.isRefreshTime( prev.getLastUpdateTime() ):
        try:
            if dyn.UpdateHostAddress( opt_address ):
                # Update peristant data
                prev.update( 0, opt_address )
            else:
                prev.update( 1 )
        except EConnectError, e:
            logger.logError( str( e ) )
            return -1
    else:
        logger.logInfo( 'No update required' )
        
    return 0

# Set the process exit status to the value returned by the main program.
if __name__== "__main__":
    sys.exit( _check_ip( len( sys.argv ), sys.argv ) )




