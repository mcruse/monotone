"""
Copyright (C) 2001 2002 2003 2004 2006 2007 2008 2009 2010 2011 Cisco Systems

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
import string
import warnings
import re
import stat
import time
import os
import gzip
import imghdr
import pdb
from urllib import unquote
from producers import FileProducer
from _filesys import os_filesystem
from mpx.service.network.utilities.counting import Counter
from _utilities import get_content_type
from _http_date import parse_http_date,build_http_date
from mpx.service import SubServiceNode
from mpx.lib import msglog
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.configure import set_attribute,\
     get_attribute,as_boolean,REQUIRED

from mpx import properties
from mpx.lib import rzutils

ONE_DAY = int(24*60*60)
NOT_CACHED = int(0)

dir_list_header = (
    """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
    <html><head><title>%s</title></head><body>
    <h1>%s</h1>
    <pre>
    <table width="100%%">
        <tr><td></td><td width="70%%"> Name</td><td>Last Modified</td>
            <td>Size</td></tr>
        <tr><td colspan=4><hr></td></tr>
        <tr><td><img src="/mpx/images/back.gif" alt="[DIR]" /></td>
            <td><a href="%s">Parent Directory</a></td><td></td><td></td></tr>
        <tr><td colspan=4><img src="/mpx/images/blank.gif" alt="Icon" /></td></tr>"""
    )
dir_entry = (
    """<tr><td valign="top"><img src="/mpx/images/folder.gif" alt="[DIR]" /></td>
           <td valign="top"><a href="%s/">%s/</a></td>
           <td valign="middle">%s</td><td valign="middle">-</td>
       </tr>""")
file_entry = (
    """<tr><td valign="top"><img src="/mpx/images/text.gif" alt="[TXT]" /></td>
           <td valign="top"><a href="%s">%s</a></td>
           <td valign="middle">%s</td><td valign="middle">%s</td>
       </tr>""")
dir_list_footer = (
    """</pre></table>
    </body></html>""")

def _lm_first_sort(a,b):
    return b[1][stat.ST_MTIME] - a[1][stat.ST_MTIME]
def directory_browser(path,file_system):
    directories = []
    files = []
    contents = file_system.listdir(path).file_list
    for entry in contents:
        stats = file_system.stat(os.path.join(path,entry))
        mode = stats[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            directories.append((entry,stats))
        else:
            files.append((entry,stats))
    directories.sort(_lm_first_sort)
    files.sort(_lm_first_sort)
    index = path[0:-1].rfind('/')
    if index == -1:
        parent = '/'
    else:
        parent = '/' + path[0:index] + '/'
    content = dir_list_header % (path, path, parent)
    for directory,stats in directories:
        name = ''
        for i in range(0,len(directory),64):
            name += directory[i:i+64] + '<br>'
        ts = time.strftime('%d-%b-%Y %H:%M',time.localtime(stats[stat.ST_MTIME]))
        content += dir_entry % (directory,name[0:-4],ts)
    for file,stats in files:
        name = ''
        for i in range(0,len(file),64):
            name += file[i:i+64] + '<br>'
        ts = time.strftime('%d-%b-%Y %H:%M',time.localtime(stats[stat.ST_MTIME]))
        content += file_entry % (file,name[0:-4],ts,stats[stat.ST_SIZE])
    return content + dir_list_footer
class RequestHandler(SubServiceNode):
    def __init__(self):
        # Overrideable flag to tell Servers to leave authenticating to you.
        self.requires_authentication = 0
        SubServiceNode.__init__(self)
    def match(self, path):
        raise ENotImplemented()
    def handle_request(self, request):
        raise ENotImplemented()
class RedirectHandler(RequestHandler):
    REDIRECT = ('<html>\n<head>\n' +
                '<META HTTP-EQUIV="Window-target" CONTENT="_top">\n' +
                '<META http-equiv="Refresh" content="0; Url=%s" >\n' +
                '<title>%s</title>\n</head>\n<body></body>\n</html>')
    def configure(self,config):
        RequestHandler.configure(self,config)
        set_attribute(self,'request_path',REQUIRED,config)
        set_attribute(self,'target_path',REQUIRED,config)
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self,'request_path',config)
        get_attribute(self,'target_path',config)
        return config
    def match(self,path):
        if path == self.request_path:
            return 1
        return 0
    def handle_request(self,request):
        request.push(RedirectHandler.REDIRECT % (self.target_path,self.name))
        request.done()
class FileRequestHandler(RequestHandler):
    valid_commands = ['get','head']
    directory_defaults = ['index.html','default.html','index.htm','default.htm']

    def __init__(self, *args):
        self._filesystem = None
        self._hit_counter = Counter()
        self._file_counter = Counter()
        self._cache_counter = Counter()
        self.cache_info = {'html': {'max_age': ONE_DAY, 'extensions': ['html', 'htm', 'xml']}, 
                      'javascript': {'max_age': ONE_DAY, 'extensions': ['js', 'wjs']},
                      'css': {'max_age': ONE_DAY, 'extensions': ['css']},
                      'images': {'max_age': ONE_DAY, 'extensions': ['png', 'jpg', 'gif']},
                      'flash': {'max_age': NOT_CACHED, 'extensions': ['swf']},
                      'others': {'max_age': ONE_DAY, 'extensions': []},}
        super(FileRequestHandler, self).__init__(*args)
    def configure(self, config):
        RequestHandler.configure(self, config)
        set_attribute(self,'request_path','/',config)
        set_attribute(self,'put_enabled',1,config,as_boolean)
        set_attribute(self,'delete_enabled',1,config,as_boolean)
        set_attribute(self,'browse_enabled',0,config,as_boolean)
        set_attribute(self, "compress", True, config, as_boolean)
        for file_type in self.cache_info:
            self.cache_info[file_type]['max_age'] = int(config.get(file_type, self.cache_info[file_type]['max_age']))
        self.valid_commands = FileRequestHandler.valid_commands[0:]
        if self.put_enabled:
            self.valid_commands.append('put')
        if self.delete_enabled:
            self.valid_commands.append('delete')
        root = '${mpx.properties.%s_ROOT}' % self.parent.server_type
        set_attribute(self,'server_root',root,config)
        return
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        get_attribute(self, 'server_root', config)
        get_attribute(self,'put_enabled',config,str)
        get_attribute(self,'delete_enabled',config,str)
        get_attribute(self,'browse_enabled',config,str)
        get_attribute(self,'compress',config,str)
        get_attribute(self, 'cache_info', config)
        return config
    def setup_filesystem(self):
        self._filesystem = os_filesystem(self.server_root)
    def start(self):
        self._hit_counter.reset()
        self._file_counter.reset()
        self._cache_counter.reset()
        if self._filesystem is None:
            self.setup_filesystem()
        RequestHandler.start(self)
    def __repr__(self):
        return '<%s (%s hits) at %x>' % (self.name,self._hit_counter,id(self))
    def match(self, request):
        return 1
    def handle_request(self, request):
        command = request.get_command().lower()
        if self.debug:
            msg = ('got command:<%s>' % command)
            msglog.log(self.name,msglog.types.DB,msg)
        if command not in self.valid_commands:
            request.error(400) # bad request
            return
        self._hit_counter.increment()
        path, params, query, fragment = request.split_uri()
        if '%' in path:
            path = unquote(path)
        while path and path[0] == '/':
            path = path[1:]
        if command in ('put','delete'):
            if command == 'put':
                operation = self._process_put
            else:
                operation = self._process_delete
            return self._process_securely(operation, path, request)
        # implicitly 'elif'...
        if self._filesystem.isdir(path):
            if path and path[-1] != '/':
                name = request.server_name()
                # Try to get the real name from the HTTP header
                if request._headers[0].find("Host: ") == 0:
                    name = request._headers[0][6:]
                request['Location'] = 'http://%s/%s/' % (name,path)
                request.error(301)
                return
            for default in self.directory_defaults:
                if self._filesystem.isfile(path + default):
                    path = path + default
                    break
        return self._process_read(path, request)
    def _process_securely(self, operation, path, request, *args, **kw):
        user = request.user_object()
        groups = os.getgroups()
        is_root = not os.getuid()
        uid = os.geteuid()
        gid = os.getegid()
        if not is_root:
            msg = ('Framework is not running as root so effective uid '
                   'and gid are not being changed prior to doing %s: '
                   '%s' % (request.get_command(),path))
            msglog.log('FileRequestHandler', msglog.types.WARN, msg)
        else:
            if self.debug:
                msg = ('%s command: file %s, user %s' %
                       (request.get_command(),path,user.name()))
                msglog.log(self.name,msglog.types.DB,msg)
            os.setgroups(user.group_ids())
            os.setegid(user.gid())
            os.seteuid(user.uid())
        try:
            result = operation(path, request, *args, **kw)
        finally:
            if is_root:
                os.seteuid(uid)
                os.setegid(gid)
                os.setgroups(groups)
        return result
    def _process_read(self, path, request):
        if not self._filesystem.isfile(path):
            if not self._filesystem.isdir(path):
                return request.error(404)
            return self._process_directory_read(path, request)
        return self._process_file_read(path, request)

    def _process_directory_read(self, path, request):
        if self.browse_enabled and self._filesystem.isdir(path):
            request.push(directory_browser(path, self._filesystem))
            request.done()
        else: request.error(404)
    
    def get_cache_control_header(self, filename, user_agent=None):
        if self.checkIfUrlAccessibleHtml(filename):
            return 'no-cache, no-store'
        file_ext = filename.split('.')[-1].lower()
        is_IE = None
        # a request over https from IE will fail if 
        # response headers prevent caching. So, set
        # the cache info header to 1s for IE
        if user_agent:
            is_IE = re.search('MSIE', user_agent)
        
        cache_control_header = None
        for file_type in self.cache_info:
            if file_ext in self.cache_info[file_type]['extensions']:
                if self.cache_info[file_type]['max_age'] != NOT_CACHED:
                    cache_control_header = ('public,max-age=%d, must - revalidate' % 
                        (int(self.cache_info[file_type]['max_age']*ONE_DAY)))
                else:
                    if not is_IE:
                        cache_control_header = 'no-cache, no-store'
                    else:
                        cache_control_header = 'public,max-age=1, must - revalidate'
                break
        if not cache_control_header:
            msglog.log("broadway", msglog.types.INFO, 
                       "HTTP File Handler: unknown file ext: %s"%file_ext)
            if not is_IE:
                cache_control_header = 'no-cache, no-store'
            else:
                cache_control_header = 'public,max-age=1, must - revalidate'

        return cache_control_header

    def checkRequestAcceptGzip(self, request):
        #pdb.set_trace()
        if (request.get_header('Accept-Encoding') is not None):
            encodings = request.get_header('Accept-Encoding')
            #encodings = "gzip"
            #if encodings != None:
            return (string.find(encodings, "gzip") != -1)
        else:
            return 0

    def checkAndCreateGzipDirectory(self, absFilepath):
        dirname = os.path.dirname(absFilepath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except Exception, e:
                msglog.log("broadway", msglog.types.INFO, "EXCEPTION in creating directory: %r" % e)


    def compressFile(self, relativeFilePath, relativeGzipPath):
        gzipped = False
        absoluteGzipFilePath = self._filesystem.translate(relativeGzipPath)
        self.checkAndCreateGzipDirectory(absoluteGzipFilePath)
        try:
            r_file = self._filesystem.open(relativeFilePath, 'rb')
        except Exception, e:
            msglog.log("broadway", msglog.types.INFO, "EXCEPTION in opening file in R mode: %r" % e)
        try:
            w_file = gzip.open(absoluteGzipFilePath, 'wb', 9)
        except Exception, e:
            msglog.log("broadway", msglog.types.INFO, "EXCEPTION in opening zip file in W mode by Gzip: %r" % e)
        try:
            w_file.write(r_file.read())  
            gzipped = True      
        except Exception, e:
            msglog.log("broadway", msglog.types.INFO, "EXCEPTION in writing zip file by Gzip: %r" % e)
        w_file.close()
        r_file.close()
        #Match times of actual file and newly created gzipped file
        if (gzipped == True):
            self._filesystem.match_times(relativeFilePath,relativeGzipPath)
        #w_file.flush()

    def checkIfUrlAccessibleHtml(self,filename):
        # Use set-type collection so that membership test is hash-based
        accessible = set(["login.html","index.html",
                          "system.html","events.html",
                          "trends.html","schedules.html",
                          "security.html","energywise.html"])
        return filename in accessible

    def _process_file_read(self, path, request):
        file_length = self._filesystem.stat(path)[stat.ST_SIZE]
        last_modified = self._filesystem.stat(path)[stat.ST_MTIME]
        ims_header = request.get_header_match(_IF_MODIFIED_SINCE)
        user_agent = request.get_header('user-agent')
        filename = os.path.basename(path)
        if ims_header:
            length = file_length
            if ims_header.group(4):
                try:
                    length = string.atoi(ims_header.group(4))
                except:
                    pass
            ims_time = parse_http_date(ims_header.group(1))
            if (length == file_length) and (last_modified <= ims_time):
                self._cache_counter.increment()
                request['Cache-Control'] = self.get_cache_control_header(filename, user_agent)
                # Finish by calling reply() method, which queues
                # response immediately, to include cache-controls.
                request.reply(304)
                return
        try:
            file = self._openread(path, 'rb')
        except IOError:
            request.error(404)
            return
        request['Cache-Control'] = self.get_cache_control_header(filename, user_agent)
        request['Last-Modified'] = build_http_date(last_modified)
        request['Content-Length'] = file_length
        self._set_content_type(path, request)
        if request.get_command() in ('get', 'GET'):
            #Check if compression mode is set to True
            ext = filename.split('.')[-1].lower()
            compressable = ['html', 'htm', 'js', 'css']
            
            if self.compress and ext in compressable and self.checkRequestAcceptGzip(request):
                gzipDir = "gzipped/"
                relativeGzipPath = gzipDir + path + '.gz'
                absGzipFilePath = self._filesystem.translate(relativeGzipPath)
                absFilePath = self._filesystem.translate(path)
                            
                last_mtime_File = self._filesystem.modified(path)
                ctime_File = self._filesystem.created(path)
                #Check whether the Gzipped requested file exists on the gzipped directory or not
                if not os.path.isfile(absGzipFilePath):
                    self.compressFile(path, relativeGzipPath)
                else:
                    #If gzipped requested file already exists
                    ctime_GzipFile = self._filesystem.created(relativeGzipPath)
                    last_mtime_GzipFile = self._filesystem.modified(relativeGzipPath)
                     #Check whether the gzipped requested file which exists is old or not
                    if ((last_mtime_GzipFile != last_mtime_File) or (ctime_GzipFile != ctime_File)):
                        self.compressFile(path, relativeGzipPath)
                #Send gzipped file    
                gzipFile_length = self._filesystem.stat(relativeGzipPath)[stat.ST_SIZE]
                try:
                    gzipfileRead = self._filesystem.open(relativeGzipPath, 'rb')
                    request['Content-Encoding'] = 'gzip'
                    request['Content-Length'] = gzipFile_length
                    request.push(FileProducer(gzipfileRead))
                    self._file_counter.increment()
                    request.done()
                    return
                except Exception, e:
                    msglog.log("broadway", msglog.types.INFO, "EXCEPTION in opening ZIP file in R mode: %r" % e)
                    # There was an error while opening the zip file.
                    # Log and suppress error to send normal file.
        # Sending actual file.
        request.push(FileProducer(file))
        self._file_counter.increment()
        request.done()

    def _openread(self, path, mode = 'rb'):
        return self._filesystem.open(path, mode)
    def _openwrite(self, path, mode = 'wb'):
        return self._filesystem.open(path, mode)
    def _process_put(self,path,request):
        if self.debug:
            msg = ('putting <%s>' % path)
            msglog.log(self.name,msglog.types.DB,msg)
        try:
            if self._filesystem.isdir(path):
                request.error(405,'A PUT request must specify'
                              ' a file, not a directory.')
                return
            update = self._filesystem.isfile(path)
            file = self._openwrite(path,'wb')
        except IOError:
            request.error(405)
            return
        data = request.get_data()
        read = data.read(1024,60)
        if not read:
            request.error(411)
            return
        while read:
            file.write(read)
            read = data.read(1024)
        else:
            file.close()
            rzutils.wefs_cache(os.path.join(self.server_root, path))
        if update:
            request.reply(204)
        else:
            request.reply(201)
    def _process_delete(self,path,request):
        try:
            if self._filesystem.isdir(path):
                request.error(405,'A DELETE request can only be '
                              'performed on a file, not a directory.')
                return
            if not self._filesystem.isfile(path):
                request.error(404)
                return
            # Unecessary from a function perspective, but hooks in security.
            file = self._openwrite(path,'wb')
            file.close()
            self._filesystem.unlink(path)
            rzutils.wefs_uncache(path)
        except IOError:
            request.error(405)
        request.reply(204)
    def _set_content_type(self,path,request):
        try:
            request['Content-Type'] = get_content_type(path)
        except KeyError:
            # We couldn't determine the file type by it's extension, so read
            # the first 500 bytes or so of the file and see if we can find
            # some binary characters.  If so, then set the content type of
            # application/octet-stream to let the browser know it is a
            # binary file, otherwise go with the default of text/plain.
            # Note: For now, if we find a byte with the high bit set or
            #       a null-character, assume we've got a binary file.
            try:
                file = self._filesystem.open (path, 'rb')
                data = file.read(500)
                file.close()
                for c in data:
                    b = ord(c)
                    if b == 0 or b > 127:
                        request['Content-Type'] = 'application/octet-stream'
                        return
            except:
                # Well, we couldn't determine if this file was text or
                # binary, so just return text.
                pass
            request['Content-Type'] = 'text/plain'
_IF_MODIFIED_SINCE = re.compile('If-Modified-Since: ([^;]+)'
                                '((; length=([0-9]+)$)|$)',
                                re.IGNORECASE)

def factory():
    from mpx.service.network.http.handlers.filespace import FileSpace
    return FileSpace()