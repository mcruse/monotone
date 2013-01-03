"""
Copyright (C) 2002 2003 2004 2007 2009 2010 2011 Cisco Systems

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
# @fixme add sys wrapper to tools.lib
# @fixme add shutil wrapper to tools.lib

import StringIO
import imp
import os
import sys

from glob import glob
from shutil import copyfile

from mpx import properties
from tools.lib import getopt, GetoptError, CommandKeywords, os

def create_pyscript(target_script, pyc_file, pre_exec_script=None, **keywords):
    # Get an easy to use opbject...
    keywords = CommandKeywords('create_pyscript()', keywords,
                               {'ROOT':properties.ROOT,
                                'UID':properties.MPX_UID,
                                'GID':properties.MPX_GID,
                                'EXEC':'exec',
                                'ENV':{}})
    exec_command = keywords.EXEC
    template = '%s: Creating %s script for %s, PYTHONPATH=%s'
    header = 'PROGRESS'
    output = keywords.normal_message
    if keywords.test:
        header = 'TEST'
        output = keywords.test_message
    output(template, 'PROGRESS', target_script, pyc_file, keywords.ROOT)
    if not keywords.test:
        script_file = open(target_script, 'w+')
    else:
        script_file = open('/dev/null', 'w')
    try:
        # Generate the standard UNIX "#!/bin/sh" program loader.
        # Export properties required by moab.
        # @fixme Move property support to moab...
        script_text='#!/bin/sh\n'
        script_text='%sexport PYTHONPATH=%r\n' % (script_text, keywords.ROOT)
        script_text='%sexport BROADWAY_VAR_RUN=%r\n' % (script_text,
                                                        properties.VAR_RUN)
        script_text='%sexport BROADWAY_VAR_RUN_BROADWAY=%r\n' % (
            script_text, properties.VAR_RUN_BROADWAY
            )
        script_text='%sPYTHON_VIA_ENV="/usr/bin/env python-mpx"\n' % (
            script_text,
            )
        script_file.write(script_text)
        if keywords.ENV:
            script_text=('# Force the following environment variables:\n')
            script_file.write(script_text)
        for key, value in keywords.ENV.items():
            script_text=('export %s=%r\n' % (key, value))
            script_file.write(script_text)
        if pre_exec_script is not None:
            script_text='%s\n' % (pre_exec_script,)
        else:
            script_text='\n'
        script_text='%s%s ${PYTHON_VIA_ENV} %r "$@"\n' % (script_text,
                                                          exec_command,
                                                          pyc_file)
        script_file.write(script_text)
    finally:
        script_file.close()
    os.system('chown %s.%s %r' % (keywords.UID, keywords.GID,
                                  target_script),
              **keywords.keywords)
    os.system('chmod 775 %r' % target_script, **keywords.keywords)
    return

##
# Walk a directory tree looking for files that match a given pattern.
# @fixme Support precompiled REs in ignore_re_list.
def walktree(dir, pattern, ignore_re_list=None):
    if ignore_re_list is None:
        ignore_re_list=["CVS", "penvironment.d", "prelease.d"]
    filelist = []
    filelist.extend(glob(os.path.join(dir, pattern)))
    for f in os.listdir(dir):
        if f in ignore_re_list:
            # Do not recurse directories that match ignore_re_list items.
            continue
        pathname = os.path.join(dir, f)
        if os.path.isdir(pathname):
            filelist.extend(walktree(pathname, pattern, ignore_re_list))
    return filelist

# Return a list of intall scripts.
def get_install_scripts(dir):
    return walktree(dir, '*.install.pyc')

##
# @fixme Support the standard "verbosity" levels: 0, 1, and 2 (see prelease).
#        This would depricate -Q.
# @fixme Use inheritance instead of 6x10^24 keywords...
class InstallOptions:
    _usage_message = "Usage: %s [options]"
    _help_message = """
Options:
  -h or --help                Displays this help message and exits.
  -u or --upgrade             Process as an upgrade.
  -t or --test                Don't really do anything.
  -v or --verbose             Output messages that describe the script's
                              progress.  This is the default.
  -p or --packages            Specify a list of packages to be co-installed.
  -Q or --quiet               Override -v|--verbose.
  -q or --query               Print the script's information dictionary in
                              repr() syntax.
  -D or --debug               Ouput extra debugging information to stderr.
  -F or --debug-file filename Ouput extra debugging information to filename.
                              This is primarily useful for communications
                              between the root install script and the
                              package specific scripts.
  BUGS:
    @fixme Support the standard \"verbosity\" levels: 0, 1, and 2 (see 
#          prelease).  This would depricate -Q.
"""
    default_short_options = 'hvutqQp:F:D'
    default_long_options = ['help', 'verbose', 'upgrade', 'test', 'query',
                            'quiet', 'packages=', 'debug-file=', 'debug']
    def __str__(self):
        return """%s:
verbose: %s
upgrade: %s
debug: %s
other_options: %s
arguments: %s
command_name: %s
command_arguments: %s
short_options: %s
long_options: %s
error_on_arguments: %s
query_and_exit: %s
help_message:
------------------------------------------------------------------------
%s
------------------------------------------------------------------------""" \
            % (self.package,
               self.verbose,
               self.upgrade,
               self.test,
               self.other_options,
               self.arguments,
               self.command_name,
               self.command_arguments,
               self.short_options,
               self.long_options,
               self.error_on_arguments,
               self.query_and_exit,
               self.help_message)
    
    def __init__(self, package,
                 more_short_opts='',
                 more_long_opts=None,
                 more_help='',
                 **keywords):
        if more_long_opts is None:
            more_long_opts = []
        self.package = package
        self.verbose = 1
        self.upgrade = 0
        self.test = 0
        self.debug = 0
        self.debugfiles = []
        self.query = 0
        self.other_options = []
        self.arguments = []
        self.command_name = os.path.basename(sys.argv[0])
        self.command_arguments = sys.argv[1:]
        self.short_options = self.default_short_options + more_short_opts
        self.long_options = self.default_long_options + more_long_opts
        self.usage_message = InstallOptions._usage_message % self.command_name
        self.help_message = InstallOptions._help_message + more_help
        self.error_on_arguments = 1
        self.query_and_exit = 1
        self.copackages = []
        self.truncate_debug_file = 1
        self.stderr = sys.stderr
        self.stdout = sys.stdout        
        # Override any default specified in the keyword list.
        for attribute,value in keywords.items():
            if hasattr(self, attribute):                               
                setattr(self, attribute, value)
            else:
                raise GetoptError(
                    "Internal error, %s is not an overridable attribute"
                    "of the %s class." % (attribute, self.__class__.__name__),
                    "Invalid keyword argument.")
    def help_string(self):
        return self.usage_message + self.help_message
    
    def _write_message_to(self, file, format, *args):
        if hasattr(format, 'readline'):
            line = format.readline()
            while line:
                self._write_message_to(file, line)
        if args:
            file.write(format % args)
        else:
            file.write(format)
        file.write('\n')
        file.flush()
        
    def fatal_message(self, format, *args):
        self._write_message_to(self.stderr, format, *args)
        
    def error_message(self, format, *args):
        self._write_message_to(self.stderr, format, *args)
        
    def normal_message(self, format, *args):
        self._write_message_to(self.stdout, format, *args)
        
    def debug_message(self, format, *args):
        for file in self.debugfiles:
            self._write_message_to(file, format, *args)
            
    def verbose_message(self, format, *args):
        if self.verbose:
            self._write_message_to(self.stdout, format, *args)

    def parse(self):
        exception_message = """
ERROR: There was an error parsing the command line options:
       %s

Use -h for help."""
        try:
            optlist, self.arguments = getopt(self.command_arguments,
                                             self.short_options,
                                             self.long_options)
            for o,a in optlist:
                if  o in ('-h','--help'):
                    self.normal_message(self.help_string())
                    sys.exit(0)
                elif o in ('-u', '--upgrade'):
                    self.upgrade = 1
                elif o in ('-v','--verbose'):
                    self.verbose = 1
                elif o in ('-Q','--quiet'):
                    self.verbose = 0
                elif o in ('-t', '--test'):
                    self.test = 1
                elif o in ('-q', '--query'):
                    self.query = 1
                elif o in ('-p', '--packages'):
                    self.copackages = a.split(',')
                elif o in ('-D', '--debug'):
                    self.debug = 1
                    self.debugfiles.append(self.stderr)
                elif o in ('-F', '--debug-file'):
                    self.debug = 1
                    if self.truncate_debug_file:                        
                        self.debugfiles.append(open(a, 'w+', 0))
                    else:
                        self.debugfiles.append(open(a, 'a+', 0))
                else:
                    self.other_options.append((o,a))
            if self.arguments and self.error_on_arguments:
                template = "Unexpected argument%s following the options: %s"
                argument = repr(self.arguments)[1:-1]
                if len(self.arguments) > 1:
                    plural = 's'
                else:
                    plural = ''
                raise GetoptError(template % (plural,argument), argument)
    
        except GetoptError,e:
            # @todo This should be configurable behavior.
            self.error_message(exception_message, e)
            sys.exit(2) # Error exit.
    
        return self

class InstallWorkingDirectory:
    def __init__(self, install_options):
        self._dirstack = [os.getcwd()]
        self.options = install_options
        
    def cwd(self):
        return self._dirstack[len(self._dirstack) - 1]
        
    def pushd(self, newdir):
        os.chdir(newdir)
        cwd = os.getcwd()
        self._dirstack.append(cwd)
        self.options.verbose_message("pushd, cwd = %s", cwd)
    
    def popd(self):
        assert(len(self._dirstack) > 1)
        self._dirstack.pop()
        cwd = self.cwd()
        os.chdir(cwd)
        self.options.verbose_message("popd, cwd = %s", cwd)

class InstallFile:
    def __init__(self, install_options, path_name, read_only = 0):
        self.path = path_name
        self.options = install_options
        self.read_only = read_only

    def chmod(self, mode):
        self.options.verbose_message("chmod %o %s", mode, self.path)
        if not self.options.test:
            os.chmod(self.path, mode)

    def _chown(self, uid, gid):
        if not self.options.test:
            os.chown(self.path, uid, gid)

    def chown(self, uid, gid):
        self.options.verbose_message("chown %s.%s %s", uid, gid, self.path)
        self._chown(uid, gid)
    
    def _chown_tree(self, uid, gid):
        self._chown(uid, gid)  
        for f in os.listdir(self.path):
            pkgpath = InstallFile(self.options, os.path.join(self.path, f))
            if pkgpath.isfile():
                pkgpath._chown(uid, gid)
            elif pkgpath.isdir():
                pkgpath._chown_tree(uid, gid)

    def chown_tree(self, uid, gid):
        assert(self.isdir())
        self.options.verbose_message("chown -R %s.%s %s", uid, gid, self.path)
        self._chown_tree(uid, gid)
                
    def isdir(self):
        return os.path.isdir(self.path)
    
    def isfile(self):
        return os.path.isfile(self.path)

    ##
    # @note relocate() looks EXACLTY the same as duplicate:
    #       1. Why are they the same?
    #       2. Why do we ever copy the files?  Why not always link?
    #       3. Why would we fix relocate() and lose the ability to
    #          reinstall in place?
    #       4. Why?  WHY?  WHYYYYYYYYYYYYYYYYYYYYYYYY?
    def relocate(self, dest):
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.split(self.path)[1])
            
        # Copy, or link, file based on its modifiabilty.
        if self.read_only:
            if os.path.isfile(dest):
                # @note isfile is a file OR a link to a file (NOT a link to
                #       a directory.)
                self.options.verbose_message("unlinking %s", dest)
                if not self.options.test:
                    os.unlink(dest)
            self.options.verbose_message("link %s -> %s", self.path, dest)
            if not self.options.test:
                os.symlink(os.path.realpath(self.path), dest)
        else:
            if os.path.isfile(dest):
                # @note isfile is a file OR a link to a file (NOT a link to
                #       a directory.)
                # Writing to an existing symlink writes to the target of the
                # link which is NEVER what we want.
                self.options.verbose_message("unlinking %s", dest)
                if not self.options.test:
                    os.unlink(dest)
            self.options.verbose_message("copy %s -> %s", self.path, dest)
            if not self.options.test:
                copyfile(self.path, dest)
            
        self.path = dest

    def duplicate(self, dest):
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.split(self.path)[1])
            
        # Copy, or link, file based on its modifiabilty.
        if self.read_only:
            if os.path.isfile(dest):
                # @note isfile is a file OR a link to a file (NOT a link to
                #       a directory.)
                self.options.verbose_message("unlinking %s", dest)
                if not self.options.test:
                    os.unlink(dest)
            self.options.verbose_message("link %s -> %s", self.path, dest)
            if not self.options.test:
                os.symlink(os.path.realpath(self.path), dest)
        else:
            if os.path.isfile(dest):
                # @note isfile is a file OR a link to a file (NOT a link to
                #       a directory.)
                # Writing to an existing symlink writes to the target of the
                # link which is NEVER what we want.
                self.options.verbose_message("unlinking %s", dest)
                if not self.options.test:
                    os.unlink(dest)
            self.options.verbose_message("copy %s -> %s", self.path, dest)
            if not self.options.test:
                copyfile(self.path, dest)
            
        self.path = dest

class InstallPackage:
    def __init__(self, name, description, dependencies=None, conflicts=None,
                 is_application=False):
        if dependencies is None:
            dependencies = []
        if conflicts is None:
            conflicts = []
        install_options = InstallOptions(name)
        self.options = install_options.parse()
        self.cwd = InstallWorkingDirectory(self.options)
        self.name = name
        self.description = description
        self.dependency_list = list(dependencies)
        self.conflict_list = list(conflicts)
        self.is_application = is_application
        return
    def get_conflicts(self):
        self.options.debug_message('%s.get_conflicts():', self.name)
        return tuple(self.conflict_list)
    def information_dictionary(self):
        if properties.MPX_UID != 0:
            # UGLY, but if not run as root ...
            script_dir = os.path.normpath(self.cwd._dirstack[0])
            next_dir = script_dir
            test_dir = os.path.basename(os.path.dirname(next_dir))
            # ... is there a penvironment.d variable in our path ...
            while test_dir:
                if test_dir in ('penvironment.d',):
                    # ... that is NOT our "package source" as well.
                    # @fixme Make the above check...
                    bogus = "IGNORE.%s:%s" % (script_dir, self.name)
                    return {'package'     : bogus,
                            'dependencies': [],
                            'conflicts'   : [],
                            'description' : bogus + self.description}
                # Look-up one directory in the path.
                next_dir = os.path.dirname(next_dir)
                test_dir = os.path.basename(next_dir)
        return {'package'       : self.name,
                'dependencies'  : self.dependency_list,
                'conflicts'     : self.get_conflicts(),
                'description'   : self.description,
                'is_application': self.is_application,
                }

    def install(self):
        raise NotImplementedError

    def _install(self):
        self.options.normal_message("Starting installation of %s", self.name)
        exit_status = self.install()
        self.options.normal_message("%s installation complete", self.name)
        return exit_status
    
    def uninstall(self):
        # Undo what install did, and (optionally?) things that may have been
        # done by the package after it was installed.
        raise NotImplementedError
    
    def reinstall(self):
        if self.uninstall() == 0:
            return self.install()
        return 0
        
    def upgrade(self):
        # do nothing, let each package do it
        return  
    
    def _upgrade(self):
        self.options.normal_message("Starting Upgrade of %s", self.name)
        exit_status = self.upgrade()
        self.options.normal_message("%s Upgrade complete", self.name)
        return exit_status
    
    def execute(self):
        if self.options.query:
            self.options.normal_message(repr(self.information_dictionary()))
            if self.options.query_and_exit:
                return 0        
        rt = None    
        # Process the install options.
        if self.options.upgrade ==1:
            rt = self._upgrade()
        else:
            rt = self._install()        
        return rt

def _debug_file_name(install_pyc):
    install_pyc = os.path.basename(install_pyc)
    return os.path.join(properties.TEMP_DIR, (
        "%s-%s.dbg" % (os.getpid(),install_pyc[:-4])
        ))

def build_pkg_db(cwd, options, package_db_out):
    from string import join
    # Get a list of all package install scripts in the directory tree.
    installers = get_install_scripts('.')
    package_names = []
    if options is None:
        class _Options:
            def __init__(self):
                self.debug = 0
                return
            def debug_message(self, *args):
                return
            def error_message(self, fmt, *args):
                raise fmt % args
        options = _Options()
    #
    # Build a list of package names.
    #
    for install_pyc in installers:
        script = os.path.realpath(install_pyc)
        args = (script, "-q",)
        debugfile = ''
        if options.debug:
            debugfile = _debug_file_name(install_pyc)
            args = (script, "-F", debugfile, "-q")
        options.debug_message("run_install_script(%r, %r)", script, args)
        answer = run_install_script(script, args, options)
        if debugfile:
            f = open(debugfile, 'r')
            os.unlink(debugfile)
            options.debug_message(f.read())
            f.close()
        else:
            options.debug_message(answer)
        infomap = eval(answer)
        pname = infomap['package']
        if not pname in package_names:
            package_names.append( pname )

    # Convert the package list to a string of comma-seperated names.
    joined_pnames = join( package_names, ',' )
    
    #
    # Build a package database containing information about all the packages.
    # This process fails if there are duplicate package names.
    # NOTE:  Second pass allows install scripts to analyze all other
    #        package names for collisions.
    for install_pyc in installers:
        script = os.path.realpath(install_pyc)
        args = (script, "-q","-p",joined_pnames)
        debugfile = ''
        if options.debug:
            debugfile = _debug_file_name(install_pyc)
            args = (script, "-F",debugfile,"-q","-p",joined_pnames)
        options.debug_message("run_install_script(%r, %r)", script, args)
        answer = run_install_script(script, args, options)
        if debugfile:
            f = open(debugfile, 'r')
            os.unlink(debugfile)
            options.debug_message(f.read())
            f.close()
        else:
            options.debug_message(answer)
        infomap = eval(answer)
        infomap['script_name'] = install_pyc
        pname = infomap['package']
        if pname in package_db_out.keys():
            options.error_message( "duplicate package '%s' in %s and %s"
                                   % (pname,
                                      package_db_out[pname]['script_name'],
                                      install_pyc) )
            return 1
        # For any package PKG.install.py, there could an optional
        # PKG.properties.pyc file.
        properties_pyc = '.'.join((install_pyc[:-12],'properties.pyc'))
        if os.path.exists(properties_pyc):
            infomap['properties'] = properties_pyc
        package_db_out[pname] = infomap
    return 0

def _stringio_to_string(sio):
    sio.seek(0)
    result = ''
    next = sio.read()
    while next:
        result += next
        next = sio.read()
    return result

def run_install_script(script, args, options=None):
    dir = os.path.dirname(script)
    script_output = StringIO.StringIO()
    install_script = imp.load_module('install_script',open(script),'',
                                     ('pyc','r',imp.PY_COMPILED))
    pop_dir = os.getcwd()
    os.chdir(dir)
    try:
        result = install_script.MAIN(args,
                                     stdout=script_output,
                                     stderr=script_output)
        if result:
            raise 'script failed', _stringio_to_string(script_output)
        return _stringio_to_string(script_output)
    finally:
        os.chdir(pop_dir)
