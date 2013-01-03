"""
Copyright (C) 2001 2002 2006 2010 2011 Cisco Systems

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

# TODO:  --argfile file to get arguments from a pi file, simple quoting, skip lines starting
#                       '#', treat CRs and LFs as whitespace.
#        --root_directory dir, Override the initial directory.
#        --root for playback.
#        --ignore files...
#        --pythonpath - Could be a bit tricky...
#        --directory - Needs to update the python path, replacing '' with the --directory.
#        --ignore file, where file is a relative filename, wildcard, fullish path.
#        --follow - See --directory TODO.
#
# BUGS:  Need to support --continue with good stack traces.
#        Doesn't handle partial relative paths well.  E.g.  'this/that'
#        It gets confused by file and module names the match option names.  I don't care...
import sys
import os

class Arguments:
    """pi.py [options] files..."""
    class Option:
        def __init__(self, attribute, value, description=None):
            self.attribute = attribute
            self.value = value
            self.description = description
        def handler(self, args):
            setattr(args, self.attribute, self.value)
    class Reset:
        def handler(self, args):
            print '--reset'
            args.reset()
    class Invoke:
        def handler(self, args):
            args.invoke()
            print '--invoke'
            args.reset()
    scan = 'scan'
    get_dir = 'get dir'
    get_path = 'get path'
    get_modules = 'get modules'
    get_files = 'get files'
    get_root = 'get root'
    get_ignore = 'get ignore'
    get_skipped = 'get skipped'
    options = {'--follow':Option('follow', 1), '-f':Option('follow', 1),
               '--nofollow':Option('follow', 0),
               '--recurse':Option('recurse', 1), '-r':Option('recurse', 1),
               '--norecurse':Option('recurse', 0),
               '--continue':Option('quit', 0), '-c':Option('quit', 0),
               '--nocontinue':Option('quit', 1),
               '--directory':Option('state', get_dir), '-d':Option('state', get_dir),
               '--pythonpath':Option('state', get_path), '-p':Option('state', get_path),
               '--modules':Option('state', get_modules), '-m':Option('start', get_modules),
               '--root_directory':Option('state', get_root),
               '--files':Option('state', get_files),
               '--ignore':Option('state', get_ignore),
               '--reset':Reset(),
               '--invoke':Invoke(),
               '--skipping':Option('state', get_skipped),
               '--':Option('state', scan)}
    def reset(self):
        self.follow = 0		# --nofollow:   Don't import from the file's directory.
        self.recurse = 0	# --norecurse:  Don't recursively import files.
        self.quit = 1		# --nocontinue: Quit on error.
        self.directory = None	# --directory dir:   Start processing from dir.
        self.pythonpath = None	# --pythonpath path: Replace PYTHONPATH with path.
        self.filenames = []	# files...:          Files and directories to import.
        self.modules = []	# modules...:        Modules to import.  Follow is ignored.
        self.ignore = ['__init__.py', 'CVS']
        if self.root_directory is self.run_directory:
            os.chdir(self.run_directory)
        else:
            print '--root_directory', self.root_directory
            os.chdir(self.root_directory)
        self.state = self.scan
    def __init__(self, g, l):
        self.globals = g
        self.locals = l
        self.run_directory = os.getcwd()
        self.root_directory = self.run_directory
        self.reset()
        self.parse_args()
    def parse_arg(self, arg):
        try:
            self.options[arg].handler(self)
        except:
            if self.state == self.get_dir:
                self.directory = arg
                self.state = self.scan
            elif self.state == self.get_path:
                self.pythonpath = arg
                self.state = self.scan
            elif self.state == self.get_root:
                self.root_directory = arg
                self.state = self.scan
            elif self.state == self.get_modules:
                self.modules.append(arg)
            elif self.state == self.get_files:
                self.filenames.append(arg)
            elif self.state == self.get_ignore:
                if arg not in self.ignore:
                    self.ignore.append(arg)
            elif self.state == self.get_skipped:
                pass
            else:
                self.filenames.append(arg)
    def parse_args(self):
        for i in range(1,len(sys.argv)):
            arg = sys.argv[i]
            self.parse_arg(arg)
    def import_module(self, module):
        print '--module', module
        command = compile('import ' + module, 'pi.py ' + module, 'exec')
        eval(command, self.globals, self.locals)
        #         try:
        #             command = compile('import ' + module, 'pi.py ' + module, 'exec')
        #             eval(command, self.globals, self.locals)
        #         except Exception, e:
        #             print e
        #             if self.quit:
        #                 raise
    def import_modules(self):
        for module in self.modules:
            self.import_module(module)
    def import_files_from_list(self, files, root=''):
        for node in files:
            if node not in self.ignore:
                if os.path.isdir(node):
                    if os.path.isfile(node + '/__init__.py'):
                        self.import_module(root + node)
                        if self.recurse:
                            popdir = os.getcwd()
                            try:
                                os.chdir(node)
                                self.import_files_from_list(os.listdir('.'), root + node + '.')
                            finally:
                                os.chdir(popdir)
                        continue
                elif os.path.isfile(node):
                    import_file = 0
                    try:
                        import_file = (node[-3:] == '.py')
                        if import_file:
                            # Skip 'executable' files.
                            temp = open(node,'r')
                            header = temp.read(2)
                            temp.close()
                            import_file = (header != '#!')
                    except:
                        pass
                    if import_file:
                        self.import_module(root + node[:-3])
                        continue
            print '--skipping', node
    def import_files(self):
        self.import_files_from_list(self.filenames)
    def invoke(self):
        if self.directory:
            print '--directory', self.directory
            dir = os.path.expanduser(self.directory) # Support ~
            dir = os.path.expandvars(dir)            # Support variable expansion.
            os.chdir(dir)
        self.import_modules()
        self.import_files()

# Hold on boy's and girls, here we go!
arguments = Arguments(globals(), locals())
arguments.invoke()

