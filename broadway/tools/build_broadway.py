"""
Copyright (C) 2001 2002 2005 2006 2010 2011 Cisco Systems

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
# @todo get cvs to check the BROADWAY file before it gets checked in so that a #.#.#-dev does
# get checked into cvs
# @todo make sure that the BRODWAY file gets cleaned after a dev build or a program interruption
# @note DON'T IMPORT anything from mpx before calling fix_pythonpath and files are in the build
# directory. If you do, it will screw up the function _import_source. _import_source will try an import
# files from mpx directory under the build directory and if it has already been imported, it will 
# have been put into the name space already of another location 

import sys
from string import *
import os
from tools.compile_dir import compile_dir
import md5
import shutil
import py_compile
import traceback
import string
import types
import zipfile
import re
import package

class EBuild(Exception):
    def __init__(self,*args,**keywords):
        Exception.__init__(self, *args)
        self.args = args
        self.keywords = keywords
    
    def __str__(self):
        msg = ''
        space = ' '
        if self.args:
            for arg in self.args:
                msg += space + str(arg) + '\n'
            msg += '\n'
            
        if self.keywords:
            for keyword, value in self.keywords.items():
                msg += '%s%s=%s\n' % (space, keyword, value)    
        return msg
    
class BuildBroadway:
    def __init__(self,path,customers_dir=None,
                 dev=0,verbose=1,
                 ignore_files = None,
                 log_file_name='',
                 include_source=0,
                 ignore_import_errors=0,
                 nodefs_file='',
                 include_customer_source=0):
        if customers_dir is None: customers_dir = []
        if ignore_files is None: ignore_files = []
        self.nodedefs_url = 'http://envenergy.com/mpx_tools/node_def_builder.jsp'
        tgz_filename = ''
        md5_filename = ''
        self.nodefs_file = nodefs_file
        self.ignore_import_errors = ignore_import_errors
        self.include_source = include_source
        self.include_customer_source = include_customer_source
        self.log_file_name = log_file_name
        self.log_file = None
        self.ignore_files = ignore_files
        self.errors = []
        self.warnings = []
        self.cwd = os.getcwd()
        self.verbose = verbose
        if not self.verbose:
            sys.stdout.close()
            sys.stderr.close()      
        self.path= path
        self.customers_dir = customers_dir
        self.dev = dev
        self.tar_file_list = []
        self.tar_file_list_name = os.tempnam(self.path)
        self.product = 'broadway'
        self.build_dir = os.path.join(self.cwd,'.build',self.product)
        self.root = ''
        self._version = ''
        self.nodedefs_md5_file = os.path.join(self.build_dir,self.product,'nodedefs.md5')        
        
        
        #figure out the md5 file name and tgz filename
        filename = str(self.product) + '-' + str(self.version()) 
       
                    
        for customer in customers_dir:
            tmp_str = string.replace(str(customer),'/','_')
            filename += '+' + string.replace(str(tmp_str),'\\','_')
            
        if self.dev:
            md5_filename = filename + '-dev.md5'
            tgz_filename = filename + '-dev.tgz'
        else:
            md5_filename = filename + '.md5'
            tgz_filename = filename + '.tgz'
            
        self.md5_file = os.path.join(str(self.path),str(self.build_dir),str(self.product),\
                                     md5_filename)
        self.tgzfile = os.path.join(self.cwd, tgz_filename)
        self.iscustomer = 0
        
        
    def _create_log_file(self):
        try:
            self.saved_stderr = sys.stderr
            self.saved_stdout = sys.stdout
            self.log_file = open(self.log_file_name,'w')
            sys.stderr = self.log_file
            sys.stdout = self.log_file
        except IOError:
            raise EBuild,EBuild('create_log_file_error')

    def _close_log_file(self):
        try:
            self.log_file.close()
            sys.stdout = self.saved_stdout
            sys.stderr = self.saved_stderr
        except IOError,e:
            raise  EBuild,EBuild('close_log_file_error')

    def build(self):  
        try:
            try:
                if self.log_file_name:
                    self._create_log_file()
                
                if self.verbose:
                    print 'Getting CVSROOT..'
                self.set_root()
                
                if not self.dev:
                    self._build_production()
                else:
                    self._build_dev()               
            
            except EBuild,e:
                self.errors.append(e)
                tb = sys.exc_info()[2]
                for t in traceback.format_tb(tb):
                    self.errors.append(str(t))
                                                                                                                            
        finally:
            if self.verbose:
                print 'Clean Up...'
            self._clean_up()
            self._display_results()
             
    def _display_results(self):
        
        if self.log_file_name:
            self._close_log_file()
        version = ''
        
        
        if self.warnings == []  and self.errors == []:
            print 'BUILD SUCCESSFUL!'
        else:
            if self.warnings != [] :
                print 'WARNING!'
                for r in self.warnings:
                    print r
                print '\n'
            if self.errors != []:
                print 'ERRORS!'
                for e in self.errors:
                    print e
        print '\n'
        
        print '\n'
        print '******************************************************'
        print 'RESULTS'
        print '__________________'
        print 'Source Directory: ' + str(self.path)
        print 'Product: ' + str(self.product)
        print 'Customers:'
        for c in self.customers_dir:
            print '\t' + str(c)

        if self.dev:
            print 'Release Type: Development'
            version = str(self.version()) + '-dev'
        else:
            version = str(self.version())
            print 'Release Type: Production'

        print 'Version: ' + str(version)
        if self.ignore_files:
            print 'Ignoring the following files...'
            for f in self.ignore_files:
                print ' ' + str(f)
        print '\n'
        
        if self.warnings == []  and self.errors == []:
            print 'BUILD SUCCESSFUL!'
        else:
            if self.warnings != [] :
                print 'WARNINGS! Please check above'
                print '\n'
            if self.errors != []:
                    print 'ERRORS! Please check above'
                
                
    def _build_production(self):

        if self.include_source:
            raise  Ebuild,Ebuild('build_production_include_source')
        
        if self.include_customer_source:
            raise  Ebuild,Ebuild('build_production_include_customer_source')
        
        if self.verbose:
            print 'Building a Production build..'

        if self.verbose:
            print 'Change to the source directory ' + str(self.path)
        os.chdir(self.path)

        if self.verbose:
            print 'Checking for locally modifed files...'
        self._check_source()

        if self.verbose:
            print 'Found Version: ' + str(self.version())

        if os.path.isdir(self.build_dir):
            if self.verbose:
                print 'Found a prevoius build directory and removing it'
            self._remove_build_dir()

        if self.verbose:
            print 'Making a build directory..'
        os.mkdir(self.build_dir)

        if self.verbose:
            print 'Checking out source...'
        self._checkout()

        if self.verbose:
            print 'Getting nodef file...'
        self._get_nodefs_file()
        
        if self.verbose:
            print 'Making nodedef md5 file...'
        self._make_nodedef_md5()
        
        if self.verbose:
            print 'Making nodedef zip file..'
        self._make_nodedef_zip()
        
        if self.verbose:
            print 'Compiling source...'
        self._compile()

        if self.verbose:
            print 'Trying to import source..'
        self._import_source()
        
        if self.verbose:
            print 'Creating tar list of files'
        self._create_tar_file_list()

        if self.verbose:
            print 'Making md5 file...'
        self._make_md5()

        if self.verbose:
            print 'Making tgz file...'
        self._make_tgz_file()
     
    def _build_dev(self):
        if self.verbose:
            print 'Building a Dev build..'
    
        if self.verbose:
            print 'Change to the source directory ' + str(self.path)
        os.chdir(self.path)

        if os.path.isdir(self.build_dir):
            if self.verbose:
                print 'Found a prevoius build directory and removing it'
        self._remove_build_dir()

        if self.verbose:
            print 'Making a build directory..'
        os.mkdir(self.build_dir)

        if self.verbose:
            print 'Moving files to build directory..'
        self._move_source_to_build()

        if self.verbose:
            print 'Updating BROADWAY file..'
        self._update_broadway_file(str(self.version()) + '-dev')

        if not self.nodefs_file:
            if self.verbose:
                print 'Getting nodef file...'
            self._get_nodefs_file()
        
        if self.verbose:
            print 'Making nodedef md5 file...'
        self._make_nodedef_md5()
        
        if self.verbose:
            print 'Making nodedef zip file..'
        self._make_nodedef_zip()
        
        if self.verbose:
            print 'Compiling source...'
        self._compile()

        if self.verbose:
            print 'Trying to import source..'
        self._import_source()
         
        if self.verbose:
            print 'Creating tar list of files'
        self._create_tar_file_list()

        if self.verbose:
            print 'Making md5 file...'
        self._make_md5()

        if self.verbose:
            print 'Making tgz file...'
        self._make_tgz_file()
    
    ##
    # @fixme right now we use the zip program to make the zip file
    # and the reason is zipfile.py makes a zip file that is not compatible
    # with jar for some reason.  I dont know if jar has a bug or zipfile.py
    # has the bug, I think that jar is the one with the bug.
    def _make_nodedef_zip(self):        
        popdir = os.getcwd()
        os.chdir(os.path.join(self.path,self.build_dir,self.product))
        command = 'zip nodedefs.zip nodedefs.xml'
        sdtin,sdtout,sdterr = os.popen3(command)
        out = sdtout.readlines()
        err = sdterr.readlines()
        if len(err) > 0:
            raise EBuild,EBuild('Error creating the nodedefs.zip file',err)
        os.chdir(popdir)
        
    def _make_nodedef_md5(self):
        try:        
            f = open(self.nodefs_file,'r')
            m = md5.new()
            m.update(f.read())
            f.close()
            md5_file = open(self.nodedefs_md5_file,'w')
            md5_file.write(str(m.hexdigest()) + '  ' + str(os.path.basename(self.nodefs_file)))
            md5_file.close()
        except IOError,e:
            raise EBuild,EBuild('Error making nodedefs.md5 file',str(e))
        
    def _get_nodefs_file(self):
        import urllib
        popdir = os.getcwd()
        os.chdir(self.build_dir)
        parameter= ''
        self.nodefs_file = os.path.join(self.path,self.build_dir,self.product,'nodedefs.xml')
        url = self.nodedefs_url + '?'
        
        if self.dev:
            url += 'date=now'
        else:
            url += 'tag=' + str(self.product) + '_' + string.replace(str(self.version()),'.','_')
        try:
            print "Fetching nodedefs from:", url
            r = urllib.urlretrieve(url,self.nodefs_file)
            if r[1].dict['content-type'] != 'text/plain':
                raise EBuild,EBuild('Error getting the nodedefs file')
        except IOError,e:
            raise EBuild,EBuild('Unable to contact the web server to get the nodedef file')
        
        os.chdir(popdir)
        
        
    def _is_program(self,file):
        temp = open(file,'r')
        header = temp.read(2)
        temp.close()
        return (header == '#!')

    def _walker(self,arg, dirname, names):
        module_base = dirname.replace('/','.')
        for name in names:
            if name == '__init__.py':
                # Import the package.
                module = module_base
                print 'Importing package: ', module
            elif name[-3:] == '.py':
                # Import the file.
                if not self._is_program(os.path.join(dirname, name)):
                    module = module_base + '.' + name[:-3]
                    print 'Importing file: ', module
            else:
                continue
            command = compile('import ' + module,
                              'import_everything ' + module,
                              'exec')
            eval(command, globals(), locals())

    ##
    # Import every Python file.
    def import_everything(self,directory, packages):
        popdir = os.getcwd()
        directory = os.path.expanduser(directory) # Support ~
        directory = os.path.expandvars(directory) # Support variable expansion.
        os.chdir(directory)
        try:
            if type(packages) == types.StringType:
                packages = [packages]
            for package in packages:
                try:
                    os.path.walk(package, self._walker, None)
                except ImportError,e:
                    if self.ignore_import_errors:
                        tb = sys.exc_info()[2]
                        list = traceback.format_list(traceback.extract_tb(tb))
                        self.warnings.append('IMPORT WARNING:\n')
                        for l in list:
                            self.warnings.append(l)
                        continue
                    else:
                        raise
        finally:
            os.chdir(popdir)
            
            
    def _import_source(self):
        try:
            self.import_everything(os.path.join(self.path,self.build_dir,self.product))
        except ImportError,e:
            raise EBuild,EBuild('Error importing source',e)
        
        except Exception,e:
            if self.ignore_import_errors:
                tb = sys.exc_info()[2]
                list = traceback.format_list(traceback.extract_tb(tb))
                self.warnings.append('IMPORT WARNING:\n')
                for l in list:
                    self.warnings.append(l)
            else:
                raise EBuild,EBuild('Error importing source',e)
            
    def _update_broadway_file(self,text):
        f = None
        try: 
            f_name = os.path.join(self.path,self.build_dir,self.product,'BROADWAY')            
            f = open(f_name,'w')
            f.write(text + '\n')
            f.close()
        except IOError:
            if f:
                if not f.closed():
                    f.close()
            raise EBuild.EBuild('Error updating BROADWAY file')
        
    def _move_source_to_build(self):
        os.chdir(str(self.path))
        dir = os.path.join(self.build_dir,self.product)
        
        if not os.path.isdir(dir):
            os.chdir(self.build_dir)
            os.mkdir(self.product,0744)
        os.chdir(str(self.path))
        command = 'cp -r * .build/%s' % self.product
        sdtin,sdtout,sdterr = os.popen3(command)
        out = sdtout.readlines()
        err = sdterr.readlines()
        if len(err) > 0:
            raise EBuild,EBuild('Error moving source to the build directory',err)
        
    def _clean_up(self):
            if os.path.isfile(self.tar_file_list_name):
                try:
                    os.unlink(self.tar_file_list_name)
                except:
                    pass
            try:
                self._remove_build_dir()
            except:
                pass
    
    def _create_tar_file_list(self):
        packages = ['broadway']
             
        for cust in self.customers_dir:
            packages = packages + string.replace(cust,'/','.')


        manifest = package.walktree(packages,'.',None, [])

        f = open(self.tar_file_list_name,'w')
        for filename in manifest:
            f.write("%s\n"%os.path.join(self.product,filename))
        f.close()
        
    def _make_tgz_file(self):
        dir = os.path.join(str(self.path),str(self.build_dir)) 
        os.chdir(dir)
        
        command = 'tar zcf ' + str(self.tgzfile) + ' -T ' + str(self.tar_file_list_name)
        sdtin,sdtout,sdterr = os.popen3(command)
        out = sdtout.readlines()
        err = sdterr.readlines()
        if len(err) > 0:
            raise EBuild,EBuild('Error making the tgz file',err)
        
    def _make_md5(self):
        os.chdir(os.path.join(self.path,self.build_dir))
        f_name =os.path.join(self.path,self.build_dir,self.md5_file) 
        if os.path.isfile(f_name):
            try:
                os.unlink(f_name)
            except IOError:
                raise EBuild,EBuild('Error deleting %s file' % f_name)
        try:
            f = open(self.tar_file_list_name,'r')
            for line in f.xreadlines():
                m = md5.new()
                tmp_file = open(line[:-1])
                for l in tmp_file.xreadlines():
                    m.update(l)
                tmp_file.close()
                mdf = open(self.md5_file,'a')
                mdf.write(str(m.hexdigest()) + '  ' + str(line[len(self.product)+1:-1]) + '\n') 
                mdf.close()
                m = None
            f.close()   
            tar_list_file = open(self.tar_file_list_name,'a')
            tar_list_file.write(str(self.product) + '/' + str(os.path.basename(self.md5_file)))
            tar_list_file.close()

        except IOError:
            raise EBuild,EBuild('Error making the md5 file')

      
    def _compile(self):
        os.system('./compile')
        compile_dir(os.path.join(self.path,self.build_dir,self.product))

            
    def _checkout(self):
        os.chdir(self.build_dir)
        tag = str(self.product) + '_' + str(replace(self.version(),'.','_'))
        command = 'cvs -d  ' + str(self.root) + ' -q  export -r ' + str(tag) + ' ' + str(self.product)
        sdtin,sdtout,sdterr = os.popen3(command)

        out = sdtout.readlines()
        err = sdterr.readlines()
        if len(err) > 0:
            raise EBuild,EBuild('Error checking out source', err)
        os.chdir('..')
        
    def set_root(self):
        f = None
        try:
            f = open('CVS/Root')
            self.root = split(f.readline(),'-')[0][:-1]
        except IOError:
            if f:
                if not f.closed():
                    f.close()
            raise EBuild,EBuild('Error setting cvs Root')
        
    def _remove_build_dir(self):
        sdtin,sdtout,sdterr = os.popen3('rm -rf ' + str(self.build_dir))
        out = sdtout.readlines()
        err = sdterr.readlines()
        if len(err) > 0:
            raise EBuild,EBuild('Error removing the build directory',err)
        
    def _check_source(self):
        tag = str(self.product) + '_' + str(replace(self.version(),'.','_'))
        command = 'cvs -n -q -d ' + str(self.root) + ' update -r ' + str(tag) + ' | grep -v ?'
        stdin,stdout,stderr= os.popen3(command)
        modifed_files = stdout.readlines()
        errors = stderr.readlines()

        if len(modifed_files) > 0:
            raise EBuild,EBuild('check_source_error', ModifiedFiles=modifed_files)
        
        if len(errors) > 0:
            raise EBuild,EBuild('check_source_error',errors)
        
    def version(self,reload=0 ):
        if not self._version or reload == 1:  
            f = None
            os.chdir(self.path)
            try:
                f = open('BROADWAY')
                line =f.readline()[:-1] 
                self._version = split(line,'-')[0]
            except IOError:
                if f:
                    if not f.closed():
                        f.close()
                raise EBuild,EBuild('Error getting version','Check the file BROADWAY',\
                      'Make sure your source directory is \'broadway\'')
        return self._version
    
