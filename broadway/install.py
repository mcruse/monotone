"""
Copyright (C) 2003 2005 2007 2009 2010 2011 Cisco Systems

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

# @fixme Support the standard "verbosity" levels: 0, 1, and 2 (see prelease).
#        This would depricate -Q.
# @fixme More intellegent setting of sys.path...

import cPickle
import imp
import os
import sys

from stat import *
from string import split,join

import _mpxhooks
_mpxhooks.load_properties_warning = False

from mpx import properties
from moab.linux.lib.statusled import StatusLED

# Ensure that the search path is correct for this script and all sub-scripts.
path = properties.ROOT
if path not in sys.path:
    # Broadway goes in front emulate a correcty set PYTHONPATH.
    sys.path.insert(0, path)
    if os.environ.has_key('PYTHONPATH'):
        os.environ['PYTHONPATH'] = "%s:%s" % (path, os.environ['PYTHONPATH'])
    else:
        os.environ['PYTHONPATH'] = path

REQUIRED_DIRECTORIES = (
    properties.DATA_DIR,
    properties.HTTPS_ROOT,
    properties.HTTP_ROOT,
    properties.INFO_DIR,
    properties.LOGFILE_DIRECTORY,
    properties.PDO_DIRECTORY,
    properties.VAR_DIR,
    properties.VAR_LOCK,
    properties.VAR_LOG,
    properties.VAR_MPX,
    properties.VAR_MPX_DB,
    properties.VAR_RUN,
    properties.WWW_ROOT,
    )

from mpx.install import *
from tools.lib import GetoptError, DecodeStatus
from mpx.lib import msglog

###
# Parse the command line and return an instance of InstallOptions.
# 
def get_my_options(command_name=sys.argv[0], command_arguments=sys.argv[1:],stdout=sys.stdout,stderr=sys.stderr):
    ##
    # Derived version of InstallOptions to manage logging and displaying input.
    class MyOptions( InstallOptions ):
        more_help = """\
  -d or --display            Display the results to stderr and stdout.  By
                             default, the results are not sent to stderr and
                             stdout.
  -l or --log                Log the results to the Framework's message log.
                             This is the default.
  -n or --no-log             Do not log the results to the Framework's
                             message log.
  -V or --very-verbose       Potentially overwhelming amounts of output.  Not
                             a good idea if logging is enabled.
  -L or --list               List all available packages and quit.
"""
        def __init__( *args, **keywords ):
            self = args[0]
            InstallOptions.__init__( *args, **keywords )
            self.usage_message += " [package1 package2 ... packageN]"
            self.log = 1
            self.display = 0
            self.very_verbose = 0
            return
        def _log_it( self, type, format, *args ):
            message = format % args
            message.rstrip() # Remove all trailing whitespace (including the
                             # final \n).
            if self.log:
                msglog.log( 'install', type, message )
            return
        def fatal_message( self, format, *args ):
            InstallOptions.error_message( self, format, *args )
            self._log_it( msglog.types.FATAL, format, *args )
            return
        def error_message( self, format, *args ):
            InstallOptions.error_message( self, format, *args )
            self._log_it( msglog.types.ERR, format, *args )
            return
        def normal_message( self, format, *args ):
            if self.display:
                InstallOptions.normal_message( self, format, *args )
            self._log_it( msglog.types.INFO, format, *args )
            return            
        def verbose_message( self, format, *args ):
            if self.verbose:
                if self.display:
                    InstallOptions.verbose_message( self, format, *args )
            self._log_it( msglog.types.INFO, format, *args )
            return

    #
    # get_my_options()
    #
    options = MyOptions('', 'dlLn', ['display', 'log', 'list', 'no-log',
                                     'nolog', # For backwards compatibility.
                                     ],
                        MyOptions.more_help,
                        error_on_arguments = 0,
                        query_and_exit = 0,
                        command_name = command_name,
                        command_arguments = command_arguments,
                        stdout=stdout,stderr=stderr)
    options.parse()
    options.display = 0
    options.show_list = 0
    
    if options.test:
        options.action = 'test install'
    else:
        options.action = 'install'

    # Check for our additional options were included.
    for o,a in options.other_options:
        if o in ('-d','--display'):
            options.display = 1
        elif o in ('-l','--log'):
            options.log = 1
        elif o in ('-n','--no-log','--nolog'):
            options.log = 0
        elif o in ('-L','--list'):
            options.show_list = 1
            options.display = 1
        elif o in ('-V','--very-verbose'):
            options.very_verbose = 1
            options.verbose = 1
            options.display = 1
            
    return options

def script_error( options, status ):
    decoded_status = DecodeStatus( status )
    options.error_message( decoded_status.message ) 
    options.fatal_message( "%s failed, contact customer support"
                           " for information on resolving the problem.",
                           options.action.capitalize() )
    return decoded_status.exit_code

def display_pgk_db( options, package_db ):
    package_names = package_db.keys()
    package_names.sort()
    
    for p in package_names:
        i = package_db[p]
        output = "%s -- %s\n  script : %s\n  needs  : %s\n  rejects: %s\n" \
               % (p, i['description'], i['script_name'], repr( i['dependencies'] ),
                  repr( i['conflicts'] ))
        options.normal_message( output )
        
def add_pkg_to_graph(graph, options, package_db, pkg_name):
    pkg_infomap = package_db[pkg_name]
    for vertex_name in graph.get_vertice_names():
        if vertex_name in pkg_infomap['conflicts']:
            options.error_message( "package '%s' conflicts with package '%s'"
                                   % (pkg_name, vertex_name) )
            return 2
        vertex_infomap = package_db[vertex_name]
        if pkg_name in vertex_infomap['conflicts']:
            options.error_message( "package '%s' conflicts with package '%s'"
                                   % (pkg_name, vertex_name) )
            return 2
        if pkg_infomap['is_application'] and vertex_infomap['is_application']:
            options.error_message(("package '%s' conflicts with package '%s'"
                                   " as both are top level applications.")
                                   % (pkg_name, vertex_name) )
            return 2
    graph.add_vertex(Vertex(pkg_infomap['package'],
                            pkg_infomap['dependencies']))
    for dependency in pkg_infomap['dependencies']:
        if not dependency in package_db.keys():
            options.error_message("package '%s' depends on missing package '%s'"
                                  % (pkg_name, dependency))
            return 1
        if not graph.has_vertex( dependency ):
            result = add_pkg_to_graph(graph, options, package_db, dependency)
            if result != 0:
                return result 
    return 0

def install( options ):
    led = StatusLED()
    led.setInstalling()

    # Current working directory.
    cwd = os.getcwd()

    # Get the package database.
    package_db = {}
    status = build_pkg_db( cwd, options, package_db )
    if status:
        led.setError()
        return status

    # Display the database if that's what the user wants.
    if options.show_list:
        display_pgk_db( options, package_db )
        return 0

    #
    # Get the list of packages to install from the command line.  If none were
    # specified, then install all available packages.
    #
    packages = options.arguments
    if 'rz.omega' in packages:
        for mfw_nbm in packages:
            if mfw_nbm.startswith('mfw.nbm'):
                break
        else:
            options.normal_message(
                "package 'rz.omega' is no longer a top level package, "
                "defaulting to 'mfw.nbm' for reverse compatibility."
                )
            packages.remove('rz.omega')
            packages.append('mfw.nbm')
    if not packages:
        packages = package_db.keys()
    #
    # Check for errors and build the dependency graph.
    #
    graph = DirectedGraph()
    for p in packages:
        if not p in package_db.keys():
            options.error_message( "package '%s' not found" % p )
            return 1
        result = add_pkg_to_graph( graph, options, package_db, p )
        if result != 0:
            led.setError()
            return result

    #
    # Determine the package installation order.
    #
    try:
        sorted_packages = graph.sort()
    except ECycleDetected, e:
        options.error_message( str( e ) )
        led.setError()
        return 3
    except EMissingVertex, e:
        # Internal error! Ill-defined graph!
        options.error_message( str( e ) )
        led.setError()
        return 4

    #
    # Install the packages.
    #
    install_options = ''
    if options.upgrade:
        install_options = '-u'
    if options.verbose:
        install_options += ' -v'
    else:
        install_options += ' -Q'
    if options.test:
        install_options += ' -t'
    if options.debug:
        install_options += ' -D'

    installed_packages = []
    for p in sorted_packages:
        infomap = package_db[p]
        script = os.path.join(cwd, infomap['script_name'])
        script = os.path.realpath(script)
        args = [script,]
        args.extend(install_options.split())
        options.verbose_message("run_install_script(%r, %r)", script, args)
        try:
            properties_pyc = infomap.get('properties',None)
            if properties_pyc:
                imp.load_module('package_properties',open(properties_pyc),'',
                                ('pyc','r',imp.PY_COMPILED))
            message = run_install_script(script, args, options)
            options.verbose_message(message)
            installed_packages.append(infomap)
        except:
            msglog.exception(msglog.types.FATAL, None,
                             "Install script %r failed." % script)
            led.setError()
            return -1
    elements = []
    for element in properties.INFO_DIR.split('/'):
        elements.append(element)
        path='/'.join(elements)
        if path and not os.path.exists(path):
            os.mkdir(path, 0770)
    pickled_packages = os.path.join(properties.INFO_DIR,
                                    'packages.db')
    if os.path.exists(pickled_packages):
        os.unlink(pickled_packages)
    cPickle.dump(installed_packages,
                 open(pickled_packages,'w'),
                 cPickle.HIGHEST_PROTOCOL)
    options.normal_message("%s completed sucessfully.  Have a great day!",
                           options.action.capitalize())
    led.setIdle()
    return 0

#########################  M A I N  #########################

def MAIN(args=sys.argv,stdout=sys.stdout,stderr=sys.stderr):
    for d in REQUIRED_DIRECTORIES:
        if not os.path.exists(d):
            os.makedirs(d, 0770)

    options = get_my_options(command_name=args[0],command_arguments=args[1:],stdout=stdout,stderr=stderr)
    options.verbose_message("Running install process:  args=%r", tuple(args))

    exit_code = -1
    try:
        exit_code = install( options )
    except SystemExit, e:
        # This is how Python cleans up...
        raise e
    except GetoptError,e:
        exit_code = 2
        options.error_message( exception_message, e )
    except:
        # If testing, let the exception continue to propogate.
        if options.test:
            raise
        exit_code = 1
        try:
            options.fatal_message("%s failed due to an unexpected exception.",
                                  options.action.capitalize())
        except:
            pass
        msglog.exception(msglog.types.FATAL, None,
                          "Internal error:  Unexpected")
        return exit_code

if __name__ == '__main__':
    MAIN()
