"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
import re
import os
import os.path
import stat
import md5
from mpx.lib import msglog
from mpx.lib.configure import set_attribute, get_attribute, as_boolean, REQUIRED
from mpx.service.network.http._http_date import parse_http_date, build_http_date
from mpx.service.network.http.producers import FileProducer
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response
from mpx import properties


##
# Reads and writes configuration files via HTTP.
#
# @implements mpx.service.network.http.handlers.configfile_handler interface
#
class ConfigFileHandler( RequestHandler ):

    def configure( self, config ):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute( self, 'request_path', '/configfile', config ) 
        set_attribute( self, 'debug', 0, config, as_boolean )
        set_attribute( self, 'safe_save', 1, config, as_boolean )
        set_attribute( self, 'keep_backup', 0, config, as_boolean )
        set_attribute( self, 'authentication', "BASIC", config)
        RequestHandler.configure( self, config )

    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.SubServiceNode#configuration
    #
    def configuration( self ):
        config = RequestHandler.configuration( self )
        get_attribute( self, 'request_path', config )
        get_attribute( self, 'debug', config )
        get_attribute( self, 'safe_save', config )
        get_attribute( self, 'keep_backup', config )
        get_attribute( self, 'authentication', config )
        return config

    def start( self ):
        RequestHandler.start( self )

    def match( self, path ):
        if re.match( '^%s' % self.request_path, path ):
            return 1
        return 0
   
    def handle_request( self, request ):
        if not request.user_object().is_admin():
            request.error(401, 'Unauthorized Access')
            return

        command = request.get_command()

        if self.debug:
            msg = ( 'got command:<%s>' % command )
            msglog.log( self.name, msglog.types.DB, msg )

        if command not in ('GET', 'PUT', 'HEAD'):
            request.error( 400 ) # bad request
            return

        # This stuff is ignored for now, but may be useful in the future for accessing
        # nodedefs and MD5 checksums.
        (path, params, query, fragment) = request.split_uri()
        if '%' in path:
            path = unquote( path )
        while path and path[0] == '/':
            path = path[1:]
            
        path = properties.get( 'CONFIGURATION_FILE' );

        if command == 'PUT':
            user = request.user_object()
            groups = os.getgroups()
            is_root = not os.getuid()
            uid = os.geteuid()
            gid = os.getegid()
            if not is_root:
                msg = ('Framework is not running as root so effective uid '
                       'and gid are not being changed prior to doing %s: '
                       '%s' % (request.get_command(), path))
                msglog.log( self.name, msglog.types.WARN, msg )
            else:
                if self.debug:
                    msg = ('%s command: file %s, user %s' % (request.get_command(), path, user.name()))
                    msglog.log( self.name, msglog.types.DB, msg)
                os.setgroups( user.group_ids() )
                os.setegid( user.gid() )
                os.seteuid( user.uid() )
            try:
                self._process_put( path, request )
                return
            finally:
                if is_root:
                    os.seteuid( uid )
                    os.setegid( gid )
                    os.setgroups( groups )
                    
        # Must be GET or HEAD command
        file_length = os.stat( path )[stat.ST_SIZE]
        last_modified = os.stat( path )[stat.ST_MTIME]
        ims_header = request.get_header_match( _IF_MODIFIED_SINCE )
        if ims_header:
            length = file_length
            if ims_header.group( 4 ):
                try:
                    length = string.atoi( ims_header.group( 4 ) )
                except:
                    pass
            ims_time = parse_http_date( ims_header.group( 1 ) )
            if (length == file_length) and (last_modified <= ims_time):
                request.reply( 304 )
                return
        try:
            file = open( path, 'rb' )
        except IOError, ioe:
            msglog.log( self.name, msglog.types.DB, ioe.strerror )
            request.error( 404 )
            return

        request['Last-Modified'] = build_http_date( last_modified )
        request['Content-Length'] = file_length
        request['Content-Type'] = 'text/xml'
        if command == 'GET':
            request.push( FileProducer( file ) )
        request.done()


    def _process_put(self, path, request):
        # If save safe is enabled, then don't overwrite the current configuration
        # until the new one has been saved without problems.
        if self.safe_save:
            newpath = path + "-new"
        else:
            newpath = path
            
        if self.debug:
            msg = ( 'putting <%s>' % newpath )
            msglog.log( self.name, msglog.types.DB, msg )

        try:
            file = open( newpath, 'wb' )
        except IOError, ioe:
            msglog.log( self.name, msglog.types.DB, ioe.strerror )
            request.error( 405 )
            return

        data = request.get_data()
        read = data.read( 1024, 60 )
        if not read:
            request.error( 411 )
            return
        while read:
            file.write( read )
            read = data.read( 1024 )
        else:
            file.close()

        # Rename files as dictated by options.
        if self.safe_save:
            try:
                if self.keep_backup:
                    os.rename( path, path + '-bak' )
                os.rename( newpath, path )
            except OSError, ose:
                msglog.log( self.name, msglog.types.DB, ose.strerror )
                request.error( 405 )
                return
                
        request.reply( 204 )


_IF_MODIFIED_SINCE = re.compile('If-Modified-Since: ([^;]+)'
                                '((; length=([0-9]+)$)|$)',
                                re.IGNORECASE)

# Instanciates and returns RequestHandler.  Allows
# for uniform instaciation of all classes defined
# in framework.
#
# @return Instance of RequestHandler defined in this module.
#
def factory():
    return ConfigFileHandler()
