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
import os

from clu import CommandLineUtility, SubCommand
from clu import EArgument, EOption, EInput, ECommand

from popen2 import Popen4

class CVS_Mixin(object):
    def tagname_from_version(source_version):
        """
        Unit Tests
        ----------
        >>> x = CVS_Mixin()
        >>> x.tagname_from_version("1.2.3.build.4")
        'broadway_1_2_3_build_4'
        >>> x.tagname_from_version("1.2.3")
        'mediator_1_2_3_branch'
        >>> x.tagname_from_version("broadway_1_2_4_build_2")
        'broadway_1_2_4_build_2'
        >>> x.tagname_from_version("broadway_1_2_4_build_2.1")
        Traceback (most recent call last):
        ...
        EArgument: Malformed version or tag, 'broadway_1_2_4_build_2.1'
        """
        if '.' in source_version and '_' not in source_version:
            if (source_version.find('.build.') is not -1 or
                source_version.find('.dev.') is not -1 or
                source_version.find('.dev-') is not -1):
                source_tag = "broadway_%s" % source_version.replace('.','_')
            else:
                source_tag = "mediator_%s_branch" % (
                    source_version.replace('.','_')
                    )
        else:
            if '.' in source_version:
                raise EArgument('Malformed version or tag, %r' %
                                (source_version,))
            source_tag = source_version
        return source_tag
    tagname_from_version = staticmethod(tagname_from_version)
    def validate_tag(source_tag):
        """
        Unit Tests
        ----------
        >>> x = CVS_Mixin()
        >>> x.validate_tag('xxx')
        Traceback (most recent call last):
        ...
        ECommand: 'xxx' is not a valid cvs tag.
        >>> x.validate_tag('broadway_1_3_0_build_8')
        >>>
        """
        command = ('cvs -n update -r %s BROADWAY >/dev/null 2>&1' %
                   source_tag)
        result = os.system(command)
        if result:
            raise ECommand('%r is not a valid cvs tag.' % source_tag)
        return
    validate_tag = staticmethod(validate_tag)
    def validate_cwd():
        """
        Unit Tests
        ----------
        >>> push_dir = os.getcwd()
        >>> os.chdir('/tmp')
        >>> f = open('BROADWAY', 'w')
        >>> f.write('\\n')
        >>> f.close()
        >>> x = CVS_Mixin()
        >>> x.validate_cwd()
        >>> os.unlink('BROADWAY')
        >>> x.validate_cwd()
        Traceback (most recent call last):
        ...
        ECommand: Command must be executed in the 'broadway' directory.
        >>> os.chdir(push_dir)
        """
        if not os.path.exists('BROADWAY'):
            raise ECommand("Command must be executed in the 'broadway'"
                           " directory.")
        return
    validate_cwd = staticmethod(validate_cwd)
    def brief_diff(source_tag):
        """
        Unit Tests
        ----------
        >>> x = CVS_Mixin()
        >>> r = x.brief_diff()
        Traceback (most recent call last):
        ...
        TypeError: brief_diff() takes exactly 1 argument (0 given)
        >>> r = x.brief_diff(None, None)
        Traceback (most recent call last):
        ...
        TypeError: brief_diff() takes exactly 1 argument (2 given)
        """
        command = ('cvs diff -N --brief -r %s' % source_tag)
        child = Popen4(command)
        result = child.fromchild.readlines()
        child.wait()
        return result
    brief_diff = staticmethod(brief_diff)

class MergeReport(SubCommand, CVS_Mixin):
    def __str__(self):
        return ("source_version    The build or branch version to use as the"
                " source to merge into the current directory.  Versions"
                " specified as 1.2.3.build.4 will be mapped to a build tag"
                " of broadway_1_2_3_build_4.  Versions specified as 1.2.3"
                " will be mapped to a branch tag of mediator_1_2_3_branch")
    def __call__(self, *args):
        source_version = self.arguments()
        if not source_version:
            raise EArgument("cvstool merge_report command requires a source"
                            " version for the merge.")
        if len(source_version) > 1:
            raise EArgument("cvstool merge_report command accepts a single"
                            " argument.")
        source_version = source_version[0]
        source_tag = self.tagname_from_version(source_version)
        self.validate_cwd()
        self.validate_tag(source_tag)
        report_lines = self.brief_diff(source_tag)
        for line in report_lines:
            self.put_stdout_msg("%s", line)
        return 0

class CVS_Tool(CommandLineUtility):
    HELP = """
cvstool:  Command-line utility to help with common cvs commands.
"""
    OVERVIEW = """
"""
    def __init__(self,  argv=None):
        CommandLineUtility.__init__(self, self.HELP, argv)
        MergeReport(self, "merge_report")
        return
    def run_command(self, command):
        raise EArgument('cvstool requires a sub-command.')

if __name__ == '__main__':
    main = CVS_Tool()
    main()
