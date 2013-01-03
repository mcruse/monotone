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
from mpx._python.urllib import *
from mpx._python import urllib as _urllib
from types import StringType

_urlopener = None
def urlopen(url,data=None,timeout=None):
    """urlopen(url [, data]) -> open file-like object"""
    global _urlopener
    if not _urlopener:
        _urlopener = FancyURLopener()
    return _urlopener.open(url,data,timeout)

class URLopener(_urllib.URLopener):
    def open(self,fullurl,data=None,timeout=None):
        fullurl = unwrap(toBytes(fullurl))
        if self.tempcache and self.tempcache.has_key(fullurl):
            filename, headers = self.tempcache[fullurl]
            fp = open(filename, 'rb')
            return addinfourl(fp, headers, fullurl)
        urltype, url = splittype(fullurl)
        if not urltype:
            urltype = 'file'
        if self.proxies.has_key(urltype):
            proxy = self.proxies[urltype]
            urltype, proxyhost = splittype(proxy)
            host, selector = splithost(proxyhost)
            url = (host, fullurl) # Signal special case to open_*()
        else:
            proxy = None
        name = 'open_' + urltype
        self.type = urltype
        if '-' in name:
            # replace - with _
            name = '_'.join(name.split('-'))
        if not hasattr(self, name):
            if proxy:
                return self.open_unknown_proxy(proxy,fullurl,data,timeout)
            else:
                return self.open_unknown(fullurl,data,timeout)
        try:
            if urltype.startswith('http'):
                return getattr(self, name)(url,data,timeout)
            else:
                if timeout is not None:
                    ##
                    # todo Generate warning that urltype 
                    # does not support timeout.
                    pass
                if data is None:
                    return getattr(self, name)(url)
                else:
                    return getattr(self, name)(url,data)
        except socket.error, msg:
            raise IOError, ('socket error', msg), sys.exc_info()[2]
    def open_http(self,url,data=None,timeout=None):
        from mpx.lib import httplib
        user_passwd = None
        if type(url) is StringType:
            host, selector = splithost(url)
            if host:
                user_passwd, host = splituser(host)
                host = unquote(host)
            realhost = host
        else:
            host, selector = url
            urltype, rest = splittype(selector)
            url = rest
            user_passwd = None
            if urltype.lower() != 'http':
                realhost = None
            else:
                realhost, rest = splithost(rest)
                if realhost:
                    user_passwd, realhost = splituser(realhost)
                if user_passwd:
                    selector = "%s://%s%s" % (urltype, realhost, rest)
                if proxy_bypass(realhost):
                    host = realhost

            #print "proxy via http:", host, selector
        if not host: raise IOError, ('http error', 'no host given')
        if user_passwd:
            import base64
            auth = base64.encodestring(user_passwd).strip()
        else:
            auth = None
        h = httplib.HTTP(host,None,timeout)
        if data is not None:
            h.putrequest('POST', selector)
            h.putheader('Content-type', 'application/x-www-form-urlencoded')
            h.putheader('Content-length', '%d' % len(data))
        else:
            h.putrequest('GET', selector)
        if auth: h.putheader('Authorization', 'Basic %s' % auth)
        if realhost: h.putheader('Host', realhost)
        for args in self.addheaders: apply(h.putheader, args)
        h.endheaders()
        if data is not None:
            h.send(data)
        errcode, errmsg, headers = h.getreply()
        fp = h.getfile()
        if errcode == 200:
            return addinfourl(fp, headers, "http:" + url)
        else:
            if data is None:
                return self.http_error(url, fp, errcode, errmsg, headers)
            else:
                return self.http_error(url, fp, errcode, errmsg, headers, data)
    if hasattr(_urllib.URLopener,'open_https'):
        def open_https(self,url,data=None,timeout=None):
            from mpx.lib import httplib
            user_passwd = None
            if type(url) is StringType:
                host, selector = splithost(url)
                if host:
                    user_passwd, host = splituser(host)
                    host = unquote(host)
                realhost = host
            else:
                host, selector = url
                urltype, rest = splittype(selector)
                url = rest
                user_passwd = None
                if urltype.lower() != 'https':
                    realhost = None
                else:
                    realhost, rest = splithost(rest)
                    if realhost:
                        user_passwd, realhost = splituser(realhost)
                    if user_passwd:
                        selector = "%s://%s%s" % (urltype, realhost, rest)
                #print "proxy via https:", host, selector
            if not host: raise IOError, ('https error', 'no host given')
            if user_passwd:
                import base64
                auth = base64.encodestring(user_passwd).strip()
            else:
                auth = None
            h = httplib.HTTPS(host,0,timeout,
                              key_file=self.key_file,
                              cert_file=self.cert_file)
            if data is not None:
                h.putrequest('POST', selector)
                h.putheader('Content-type',
                            'application/x-www-form-urlencoded')
                h.putheader('Content-length', '%d' % len(data))
            else:
                h.putrequest('GET', selector)
            if auth: h.putheader('Authorization: Basic %s' % auth)
            if realhost: h.putheader('Host', realhost)
            for args in self.addheaders: apply(h.putheader, args)
            h.endheaders()
            if data is not None:
                h.send(data)
            errcode, errmsg, headers = h.getreply()
            fp = h.getfile()
            if errcode == 200:
                return addinfourl(fp, headers, "https:" + url)
            else:
                if data is None:
                    return self.http_error(url, fp, errcode, errmsg, headers)
                else:
                    return self.http_error(url,fp,errcode,errmsg,headers,data)

class FancyURLopener(URLopener):
    for name in _urllib.FancyURLopener.__dict__.keys():
        attribute = getattr(_urllib.FancyURLopener,name)
        if callable(attribute):
            setattr(FancyURLopener,name,attribute)
