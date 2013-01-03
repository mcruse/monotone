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
STATUSCODES = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Moved Temporarily",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Time-out",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request-URI Too Large",
    415: "Unsupported Media Type",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Time-out",
    505: "HTTP Version not supported"
}

ERROR = """<html>
    <head> 
        <title>Error response</title> 
    </head> 
    <body> 
        <h1>Error response</h1>
        <p>Error code %(code)d.</p>
        <p>Message: %(message)s.</p> 
    </body>
</html>
"""

REDIRECT = """<html>
    <head>
        <META HTTP-EQUIV="Window-target" CONTENT="_top">
        <META http-equiv="Refresh" content="0; Url=%s" >
        <title>%s</title>
    </head>
    <body></body>
</html>
"""

def isinfo(code):
    """
        Informational status code.
    """
    return code >= 100 and code < 200

def issuccess(code):
    """
        Request handled successfully.
    """
    return code >= 200 and code < 300

def isredirect(code):
    """
        Send client to different resource.
    """
    return code >= 300 and code < 400

def iserror(code):
    """
        Client-side error prevented successful request handling.
    """
    return code >= 400 and code < 500

def isfailure(code):
    """
        Server-side error prevented successful request handling.
    """
    return code >= 500 and code < 600

def getstatus(code):
    return HTTPRESPONSES[code]

def geterror(code, message=None):
    if message is None:
        message = getstatus(code)
    return ERROR % {'code': code,'message': message}

def getredirect(target, title=""):
    if title is None:
        title = "Redirect resource"
    return REDIRECT % (target, title)
