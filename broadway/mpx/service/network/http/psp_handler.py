"""
Copyright (C) 2003 2004 2008 2010 2011 Cisco Systems

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
import sys
import re
import os
import StringIO
import types
import cgi
import imp
import py_compile
from traceback import format_exception
from mpx import properties
from mpx.lib.node import as_node, as_internal_node
from mpx.lib.exceptions import Unauthorized
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.user_manager import EAuthenticationFailed
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute, as_boolean
from mpx.service.network.http.response import Response
from mpx.service.network.http.handlers.filespace import FileSpace, FileChild
from mpx.lib import msglog
from _psp_converter import PSPConverter
from string import join as join
from stat import ST_MTIME


class CompileError(Exception):
    pass

class PSPHandler(RequestHandler):
    def __init__(self):
        RequestHandler.__init__(self)
        self.security_manager = None
        self.provides_security = None
        self.filespace = None
        self.cache = {}
        self.html = ''
        self.ROOT_DIR = None
    ##
    # Configures HTTP handler.
    #
    # @param config  Dictionary containing parameters and values from
    #                the configuration tool.
    # @key request_path  Regular expression for url requests that
    #                    should be forwarded to this handler.
    # @default ^/trane/vista/
    #
    # @see mpx.lib.service.SubServiceNode#configure
    def configure(self,config):
        RequestHandler.configure(self,config)
        set_attribute(self,'request_path','.*\.psp$',config)
        set_attribute(self, 'provides_security', 1, config, as_boolean)
        self.secured = as_boolean(as_internal_node("/services").secured)
        self.request_regex = re.compile(self.request_path)

    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.SubServiceNode#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        get_attribute(self, 'secured', config)
        get_attribute(self, 'provides_security', config)
        return config
    def start(self):
        RequestHandler.start(self)
        self.WEB_ROOT = properties.HTTP_ROOT
        if self.parent.server_type == 'HTTPS':
            self.WEB_ROOT = properties.HTTPS_ROOT
        for handler in self.parent.children_nodes():
            if isinstance(handler, FileSpace):
                self.filespace = handler
                break
        err_message = 'PSP handler not running in secured mode because \
                      no %s was found.  Config parameter "secured" \
                      being overriden to False'
        if self.secured and self.filespace:
            try: sm = as_node('/services/Security Manager')
            except KeyError:
                msglog.log('broadway', msglog.types.WARN,
                           err_message % 'Security Manager')
                msglog.exception(prefix = 'Handled')
                self.provides_security = self._secured = False
            else:
                self.security_manager = sm
                self.provides_security = self._secured = True
        else:
            if self.secured:
                # not secured because we could not locate filespace object.
                msglog.log('broadway', msglog.types.WARN,
                           err_message % 'FileSpace manager')
            self.provides_security = self._secured = False
    ##
    # @param path the path to match to see if we handle this request
    def match(self, path):
        if self.request_regex.match(path):
            return 1
        return 0
    def _use_cache(self,file):
        rt = 1
        if self.cache and self.cache.has_key(file.name):
            if os.stat(file.name)[ST_MTIME]  \
                > self.cache[file.name]['psp_last_modified'] :
                    rt=0
            if rt==1:
                for f in self.cache[file.name]['include_files'].keys():
                    if os.stat(f)[ST_MTIME] > self.cache[file.name]['include_files'][f]:
                        rt=0
                        break
        else:
            rt=0
        return rt
    def compile(self,file,dp,force_reload=0):
        sourcefile_name = '%spy' % file.name[:-3]
        if not self._use_cache(file):
            # Process all the directives
            dp = _DirectiveProcessor(file,self.WEB_ROOT)
            include_files = dp.get_include_filenames()
            file = dp.process()
            # Convert to psp to py file
            psp_convert = PSPConverter(file)
            psp_convert.convert()
            sourcefile = open(sourcefile_name,'w' )
            # add all the imports to the source file
            self._add_imports(sourcefile,dp.get_imports())
            sourcefile.write(psp_convert.get())
            sourcefile.close()
            targetfile = '%spyc' % file.name[:-3]
            if os.path.isfile(targetfile):
                os.remove(targetfile)
            _sdterr = sys.stderr
            stderr = StringIO.StringIO()
            sys.stderr = stderr
            py_compile.compile(sourcefile_name, targetfile)
            sys.stderr = _sdterr
            stderr.seek(0)
            err = ''
            for l in stderr.readlines():
                err += '%s<br>' % l
            if err != '':
                raise CompileError(err)
            module_name =os.tmpnam()
            psp_module = imp.load_module(module_name,open(targetfile),'',
                                         ('pyc','r',imp.PY_COMPILED))
            self.cache[file.name] = {'module':psp_module,
                             'psp_last_modified':os.stat(file.name)[ST_MTIME],
                             'py_last_modified':os.stat(sourcefile_name)[ST_MTIME],
                             'include_files':{},
                              'dp':dp}
            for f in include_files:
                self.cache[file.name]['include_files'][f] = os.stat(f)[ST_MTIME]
        else:
            if os.stat(sourcefile_name)[ST_MTIME] > self.cache[file.name]['py_last_modified']:
                targetfile = '%spyc' % file.name[:-3]
                if os.path.isfile(targetfile):
                    os.remove(targetfile)
                _sdterr = sys.stderr
                stderr = StringIO.StringIO()
                sys.stderr = stderr
                py_compile.compile(sourcefile_name, targetfile)
                sys.stderr = _sdterr
                stderr.seek(0)
                err = ''
                for l in stderr.readlines():
                    err += '%s<br>' % l
                if err != '':
                    raise CompileError(err)
                module_name =os.tmpnam()
                psp_module = imp.load_module(module_name,open(targetfile),'',
                                                 ('pyc','r',imp.PY_COMPILED))
                self.cache[file.name]['py_last_modified'] = os.stat(sourcefile_name)[ST_MTIME]
    def _add_imports(self,fp,imports):
        for ip in imports:
            fp.writelines('%s\n' % ip)

    def checkIfPspIsTobeSendWithNoCache(self,filename):
        noCachePspList = ["webexpress.psp"]
        try:
            i = noCachePspList.index(filename)
        except ValueError:
            i = -1 # no match
        return i

    def handle_request(self,request):
        path = request.get_path()[1:]
        filename = os.path.basename(path)
        if self.checkIfPspIsTobeSendWithNoCache(filename) != -1:
            request['Cache-Control'] = 'no-cache, no-store'
        response = Response(request)
        try:
            qs = request.get_query_dictionary()
            force_reload = 0
            psp = PSP(response)
            path = request.get_path()[1:]
            f = os.path.join(self.WEB_ROOT, path)
            if self.filespace:
                file_node = self.filespace.as_node(path)
                if self._secured:
                    file_node = self.security_manager.as_secured_node(
                                    file_node.as_node_url()
                                )
                try:
                    file = file_node.openread()
                except Unauthorized:
                    if not request._has_minimum_authentication():
                        authenticate = request._default_authentication
                        authenticate(request._channel.server.realm)
                    else:
                        raise
                    file = file_node.openread()
            else:
                file = open(f, 'r')
            # If this is in the Query String the page will get reparsed

            if qs.has_key('PSPForceReload'):
                force_reload = 1
            self.compile(file,force_reload)
            psp_module = self.cache[f]['module']
            if qs.has_key('PSPUseNewPY'):
                sourcefile_name = '%spy' % file.name[:-3]
                targetfile = '%spyc' % file.name[:-3]
                py_compile.compile(sourcefile_name, targetfile)
                _sdterr = sys.stderr
                stderr = StringIO.StringIO()
                sys.stderr = stderr
                module_name =os.tmpnam()
                psp_module = imp.load_module(module_name,open(targetfile),'',
                                         ('pyc','r',imp.PY_COMPILED))
                self.cache[file.name]['module'] = psp_module
                sys.stderr = _sdterr
                stderr.seek(0)
                err = ''
                for l in stderr.readlines():
                    err += '%s<br>' % l
                if err != '':
                    raise CompileError(err)
            psp_module.run(psp,request,response)
            psp.send()
        except EAuthenticationFailed:
            raise
        except CompileError,e:
            err = '%s' % e
            if response == None:
                response = Response(request)
            response.send('<html><body>%s</body></html>' % e)
        except Exception,e:
            err = ''
            etype, value, tb = sys.exc_info()
            err = ''.join(format_exception(etype, value, tb))
            html = '<html><body style="color:red"><b>Error</b>'
            html += '<br>&nbsp;&nbsp;<pre>%s</pre></body></html>' % err
            if response == None:
                response = Response(request)
            response.send(html)

class _DirectiveProcessor:
    def __init__(self,file,WEB_ROOT):
        self.file = file
        self.WEB_ROOT = WEB_ROOT
        self.regx_directive = re.compile('^\s*<%@.*%>')
        self.directive_handlers = [_Include(self.WEB_ROOT),_Page()]
        self._include_filenames = []
        self._imports = []
    def _find_directive_handler(self,l):
        rt = None
        for dh in self.directive_handlers:
            if dh.match(l):
                rt = dh
                break
        return rt
    def _add_include_files(self,include_filenames):
        for f in include_filenames:
            if f not in self._include_filenames:
                self._include_filenames.append(f)
    def _add_import(self,ip):
        if ip not in self._imports:
            self._imports.append(ip)
    def _add_imports(self,imports):
        for ip in imports:
            self._add_import(ip)
    def process(self):
        new_file = StringIO.StringIO()
        new_file.name = self.file.name
        # This could probably be made for efficent
        # but it
        for l in self.file.readlines():
            if self.regx_directive.search(l):
                dh = self._find_directive_handler(l)
                if dh != None:
                    dh.process(new_file,l)
                    if isinstance(dh,_Include):
                        self._include_filenames.append(dh.get_filename())
                        if dh.get_include_filenames() != []:
                            self._add_include_files(dh.get_include_filenames())
                        if dh.get_imports() != []:
                            self._add_imports(dh.get_imports())
                    if isinstance(dh,_Page):
                        new_file = dh.process(new_file,l)
                        self._add_import(dh.get_import())
            else:
                new_file.write(l)
        return new_file
    def get_include_filenames(self):
        return self._include_filenames
    def get_imports(self):
        return self._imports
class _Directive:
    def __init__(self):
        pass
    def match(self,line):
        return self.regx.match(line)
class _Page(_Directive):
    def __init__(self):
        _Directive.__init__(self)
        self._import = ''
        self.regx = re.compile('\s*<%@\s+page\s+import=.*%>')
        self.regx_import = re.compile('([\'|"]+.*[\'|"])')
    def process(self,file,line):
        self._import = self._get_import(line)
        return file
    def get_import(self):
        return self._import
    def _get_import(self,line):
        iport = ''
        result = self.regx_import.findall(line)
        if len(result) == 1:
            iport = result[0]
            if iport.find("'") > -1:
                iport = iport.split("'")[1]
            elif iport.find('"') > -1:
                iport = iport.split('"')[1]
            else:
                raise Error('Inculde Directive format error')
        return iport
class _Include(_Directive):
    def __init__(self,web_root):
        _Directive.__init__(self)
        self.web_root = web_root
        self.regx = re.compile('\s*<%@\s+include\s+file=.*%>')
        self.regx_file = re.compile('([\'|"]+.*[\'|"])')
        self.regx_indent_level = re.compile('<%@')
        self.filename = ''
        self._include_filenames = []
        self._imports = []
        self.regx_psp = re.compile('\.psp$')
    def _get_filename(self,line):
        result = self.regx_file.findall(line)
        filename = ''
        if len(result) == 1:
            filename = result[0]
            if filename.find("'") > -1:
                filename = filename.split("'")[1]
            elif filename.find('"') > -1:
                filename = filename.split('"')[1]
            else:
                raise Error('Inculde Directive format error')
        else:
            raise Error('Inculde Directive format error')
        return filename
    def _get_indent_level(self,l):
        il = ''
        m = self.regx_indent_level.search(l)
        if m:
            il = l[:m.start()]
        return il
    def get_filename(self):
        return self.filename
    def get_include_filenames(self):
        return self._include_filenames
    def get_imports(self):
        return self._imports
    def process(self,file,line):
        fn = self._get_filename(line)
        il = self._get_indent_level(line)
        if fn[0:1] == '/':
            self.filename = os.path.join(self.web_root,fn[1:])
        else:
            self.filename = os.path.join(os.path.dirname(file.name),fn)
        fp = open(self.filename,'r')
        dp = _DirectiveProcessor(fp,self.web_root)
        fp = dp.process()
        self._include_filenames = dp.get_include_filenames()
        self._imports = dp.get_imports()
        # check to see if this is a psp file
        if self.regx_psp.search(fp.name):
            converter = PSPConverter(fp,standalone=0,indent_level=il)
            converter.convert()
            file.writelines('<%\n' + str(converter.get()) +  '%>\n')
        # if this is a regular file
        else:
            fp.seek(0)
            file.writelines(fp.readlines())
        return file

class PSP:
    def __init__(self,response):
        self.response = response
        self.response['Content-Type'] = 'text/html'
        self.html = ''
    def write(self,text):
        self.html += '%s' % text
        ##self.response.push(text)
    def entity_replacement(self,text):
        if type(text) == types.StringType:
            return cgi.escape(text)
        else:
            return text
    def send(self):
        self.response.send(self.html)

def factory():
    return PSPHandler()
