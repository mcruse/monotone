"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
import os

flag_filename = '/etc/ppp/dont_override_defaultroute'

class RoutingTable:
    DESTINATION = 0
    GATEWAY     = 1
    GENMASK     = 2
    FLAGS       = 3
    METRIC      = 4
    REF         = 5
    USE         = 6
    IFACE       = 7
    
    SAVE_FILE_NAME = '/tmp/saved_routes'
    ROUTE_PROG     = '/sbin/route'
    
    def __init__( self, newInterface = None ):
        self.newInterface = newInterface
        self._load()
                
    def _load( self ):
        self.routes = []
        p = os.popen( "%s -n" % self.ROUTE_PROG )
        result = p.readlines()
        p.close()
        
        for line in result:
            entry = line.split()
            if len( entry ) == 8:
                self.routes.append( entry )
                
    def _add( self, gateway, interface ):
        os.system( '%s add default gw %s %s' % (self.ROUTE_PROG, gateway, interface) )
        
    def _getSaveFileName( self ):
        fileName = self.SAVE_FILE_NAME
        if self.newInterface != None:
            fileName += ".%s" % self.newInterface
        return fileName

    ##
    # Quick and dirty conversion to string.
    #
    def __str__( self ):
        result = ""
        for entry in self.routes:
            result += str( entry ) + '\n'
        return result
    
    def saveDefaultRoutes( self, interfaceList = None ):
        saveFile = open( self._getSaveFileName(), 'w' )
        for entry in self.routes:
            if entry[self.DESTINATION] == '0.0.0.0':
                if interfaceList == None or entry[self.IFACE] in interfaceList:
                    saveFile.write( "%s %s\n" % (entry[self.GATEWAY], entry[self.IFACE]) )
        saveFile.close()

    def deleteDefaultRoutes( self, interfaceList = None ):
        nDeleted = 0
        for entry in self.routes:
            if entry[self.DESTINATION] == '0.0.0.0':
                if interfaceList == None or entry[self.IFACE] in interfaceList:
                    os.system( '%s del default %s' % (self.ROUTE_PROG, entry[self.IFACE]) )
                    nDeleted += 1
        if nDeleted > 0:
            self._load()

    def restoreDefaultRoutes( self ):
        nAdded = 0
        try:
            fileName = self._getSaveFileName()
            saveFile = open( fileName, 'r' )
            routes = saveFile.readlines()
            saveFile.close()
            
            # Restore the routes in the reverse order that they were saved to preserve
            # the original order of the routing table.
            i = len( routes ) - 1
            while i >= 0:
                (gateway, interface) = routes[i].split()
                self._add( gateway, interface )
                nAdded += 1
                i -= 1
                
            # Remove the tmp file.
            os.remove( fileName )
        except:
            pass
        
        if nAdded > 0:
            self._load()

    def addDefaultRoute( self, gateway, interface ):
        self._add( gateway, interface )
        self._load()

    def isDefaultRoute( self, interface = None ):
        if interface == None:
            interface = self.newInterface
        if interface != None:
            for entry in self.routes:
                if entry[self.DESTINATION] == '0.0.0.0' and entry[self.IFACE] == interface:
                    return 1
        return 0

    def addRoute( self, ipaddr, netmask, interface ):
        # @fixme:  Right now there isn't any feedback if setting up the
        #          route doesn't work.  Very soon, we should add some
        #          code to use a popen or somesuch to check the output
        #          from the route command to make sure that it succeeds,
        #          so that we can throw an exception if it doesn't.
        # If this the netmask is all set, then assume this is a host route,
        # otherwise, it better be a net route
        if netmask == '255.255.255.255':
            type = 'host'
            opts = ''
        else:
            type = 'net'
            opts = 'netmask %s' % netmask
            
        os.system( '%s add -%s %s %s %s' % ( self.ROUTE_PROG, type,
                                             ipaddr, opts,
                                             interface ) )
##
# Test routine executed if this module is run as main.
##
if __name__ == "__main__":
    rt = RoutingTable( 'eth3' )
    print rt
    
    print "is default route = %s" % rt.isDefaultRoute()
    print "is default route = %s" % rt.isDefaultRoute( 'eth0' )
    
    rt.saveDefaultRoutes()
    print rt
    
    rt.deleteDefaultRoutes()
    print rt
    
    rt.deleteDefaultRoutes( ['eth1'] )
    print rt

    rt.restoreDefaultRoutes()
    print rt

