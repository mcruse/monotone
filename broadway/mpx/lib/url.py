"""
Copyright (C) 2001 2002 2003 2008 2009 2010 2011 Cisco Systems

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
# Provides a class to preform Broadway specific URL parsing.
# @todo Deferenciate 'path' from '/path' (only relavant when no host is
#       specified, or when building a URL via the setters).
# @todo Current use is primarily for building legal, correctly escaped "local"
#       URLs for configuration.  Determine if the parameters, query, fragment
#       model is sufficient for our needs.
# @todo Finish implemtation of parameters, query, and fragment.

import copy
import urllib
import string
import urlparse

class ParsedURL(urlparse.ParseResult):
    __slots__ = ()
    def fromstring(klass, url):
        scheme = ""
        if not url.startswith("/"):
            head,delim,tail = url.partition('://')
            if delim:
                scheme = head
                url = "//%s" % tail
        parsed = urlparse.urlparse(url)
        arguments = (scheme,) + parsed[1:]
        return klass(*arguments)
    fromstring = classmethod(fromstring)
    def __str__(self):
        typename = type(self).__name__
        return "%s('%s')" % (typename, self.geturl())
    def __repr__(self):
        return "<%s object at %#x>" % (self, id(self))
    def segments(self):
        return map(urllib.unquote_plus, self.path.split("/"))

##
# This class supplies a Broadway specific URL processor.
# @fixme Deferenciate 'path' from '/path' (only relavant when no host is
#        specified, or when building a URL via the setters).
class URL:
    def __init__(self):
        self._reset()

    def _dirty(self):
        self._local_path = None
        self._path = None
        self._url_path = None
        self._full_url = None

    def _reset(self):
        self._scheme = None
        self._host = None
        self._port = None
        self._segments = []
        self._parameters = None
        self._query = None
        self._fragment = None
        self._final_slash = ''
        self._dirty()
        return
    def __str__(self):
        return """mpx.lib.url.URL:
    scheme:     %(scheme)r
    host:       %(host)r
    port:       %(port)r
    is_absolute:%(is_absolute)r
    segments:   %(segments)r
    final_slash:%(final_slash)r
    parameters: %(parameters)r
    query:      %(query)r
    fragment:   %(fragment)r
    local_path: %(local_path)r
    path:       %(path)r
    url_path:   %(url_path)r
    full_url:   %(full_url)r
""" % {"scheme":self.scheme(),
       "host":self.host(),
       "port":self.port(),
       "is_absolute":self.is_absolute(),
       "segments":self.segments(),
       "final_slash":self.final_slash(),
       "parameters":self.parameters(),
       "query":self.query(),
       "fragment":self.fragment(),
       "local_path":self.local_path(),
       "path":self.path(),
       "url_path":self.url_path(),
       "full_url":self.full_url(),
       }

    ##
    # Get the scheme for this url.
    #
    # @return scheme for this url, like http, mpx, etc.
    #
    def scheme(self):
        return self._scheme
    ##
    # Get the host for this url.
    #
    # @return the host part of the url.
    #
    def host(self):
        return self._host
    ##
    # Get the port for this url.
    #
    # @return The port number for this url.
    #
    def port(self):
        return self._port
    ##
    # Get a list of the segments making up the path for this url after the
    # hostname.
    #
    # @return List of segments for path.
    #
    def segments(self):
        return copy.copy(self._segments)
    ##
    # @return A value that evaluates as 'true' if the parsed URL ended in a
    #         slash.  This makes it possible to make parsing of a URL and
    #         reconstructing a parsed URL completely symmetrical.
    def final_slash(self):
        return self._final_slash
    ##
    # @return A value that evaluates as 'true' if the parsed URL's path
    #         componenet began with a slash.
    def is_absolute(self):
        return len(self._segments) and self._segments[0] == ''
    ##
    # Get the parameters passed to this url.
    #
    # @return Parameters passed to url.
    #
    def parameters(self):
        return self._parameters
    ##
    # Get the query string sent into url.
    #
    # @return Query string.
    #
    def query(self):
        return self._query

    def fragment(self):
        return self._fragment
    ##
    # Get the local path for this url.
    #
    # @return Everything in the url after the hostname and before
    #         any parameters, as a string.
    #
    def local_path(self):
        if not self._local_path:
            semgents = []
            for s in self._segments:
                semgents.append(urllib.quote(s, ''))
            self._local_path = string.join(semgents,'/') + self._final_slash
        return self._local_path

    ##
    # Get url including the hostname but not the scheme.
    #
    # @return Complete url after scheme: before parameters.
    #
    def path(self):
        if self._path is None:
            if self._host is None:
                return self.local_path()
            if self._port:
                elements = ['//',self._host,':',self._port,self.local_path()]
            else:
                elements = ['//',self._host,self.local_path()]
            self._path = string.join(elements,'')
        return self._path

    ##
    # Get the complete url except for parameters.
    #
    # @return Everything in url up to parameters or cgi
    #         as a string.
    #
    def url_path(self):
        if self._url_path is None:
            if not self._scheme:
                return self.path()
            self._url_path = string.join([self._scheme, ':', self.path()],'')
        return self._url_path

    ##
    # Get the complete url including cgi and parameters.
    #
    # @return Everything in url, as a string.
    #
    def full_url(self):
        if self._full_url is None:
            elements = [self.url_path()]
            if self._parameters:
                elements.extend([';',self._parameters])
            if self._query:
                elements.extend(['?',self._query])
            if self._fragment:
                elements.extend(['#',self._fragment])
            self._full_url = string.join(elements,'')
        return self._full_url

    ##
    # Set the scheme for this url.
    #
    # @param scheme  The new scheme to set this url to.
    #
    def set_scheme(self, scheme):
        self._scheme = scheme
        self._dirty()
        return self

    ##
    # Set the host for this url.
    #
    # @param host  The new hostname for this url.
    #
    def set_host(self, host):
        self._host = host
        self._dirty()
        return self

    ##
    # Set the port for this url.
    #
    # @param port  The new port to set this url to.
    #
    def set_port(self, port):
        if port:
            self._port = str(port)
        else:
            self._port = None
        self._dirty()
        return self

    ##
    # Add a segment to this url request path.
    # @param segment  The segment to add to this url.
    # @note Individual segments are NOT URL quouted.  When a path is
    #       assembled from the segments, then each segments is
    #       quoted before being applied to the resulting path.
    def add_segment(self, segment):
        self._segments.append(segment)
        self._dirty()
        return self

    ##
    # Parse the url into its consituant parts.  Setting
    # the scheme, host, port, and the remainder.
    #
    # @param url  The url that is to parsed.  Url may
    #             have a protocol, hostname, port, and path,
    #             or just a path, or a relative path.
    #
    # @return URL object with values set from parsed url.
    #
    def parse(self, url):
        # urllib doesn't work with unknown schemes.
        self._reset()
        # Extract the scheme, if any.
        s = string.split(url, ':', 1)
        remainder = url
        if len(s) == 2:
            scheme = s[0]
            if not '/' in scheme:
                self._scheme = scheme
                remainder = s[1]
        # Extract the host, port and path elements.
        # @note  This will need to be reworked to support parameters,
        #        query and fragment fields.
        s = string.split(remainder, '/')
        if len(s) == 0:
            raise EInvalidValue('url',url)
        if len(s) == 1:
            # Either "" or "element".
            if not s[0]:
                # It's an empty path, pop it.
                s.pop(0)
            else:
                # It's the only element, leave it for element&query-string
                # parsing.
                pass
        elif len(s) == 2:
            # Either "/", "element/", "/element", or "element/element"
            self._segments.append(urllib.unquote_plus(s.pop(0)))
            # Leave last element for element&query-string parsing.
        else:
            # Starts with //, /dir/element, dir//, or dir/dir
            if not s[0] and not s[1]:
                # Starts with //
                s.pop(0) # '/'
                s.pop(0) # '/'
                location = s.pop(0)
                info = string.split(location, ':', 1)
                self._host = info[0]
                if len(info) == 2:
                    self._port = info[1]
                if len(s):
                    # Special case for '//host/' and '//host/element'
                    self._segments.append('')
                elif not location:
                    # The annoying '//' path.  Just pass it through.
                    self._segments.append('')
                    self._segments.append('')
                    self._final_slash = '/'
                    self._host = None
            else:
                # It's /dir/element[/...], dir//[/...], or dir/dir[/...]
                # Primes initial segment correctly.
                self._segments.append(urllib.unquote_plus(s.pop(0)))
        while s:
            e = s.pop(0)
            if len(s):
                self._segments.append(urllib.unquote_plus(e))
            else:
                # This is the last element, handle ending in '/' and
                # query strings.
                if e:
                    # @todo Add query-strings
                    self._segments.append(urllib.unquote_plus(e))
                else:
                    # It's a final '/'.
                    self._final_slash = '/'
        return self
