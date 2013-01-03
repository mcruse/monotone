#!/usr/bin/env python-mpx
#
# better !pout !cry
# better watchout
# lpr why
# santa claus < north pole > town
# 
# cat /etc/passwd > list
# ncheck list
# ncheck list
# cat list | grep naughty > nogiftlist
# cat list | grep nice > giftlist
# santa claus < north pole > town
# 
# who | grep sleeping
# who | grep awake
# who | grep bad || good
# for (goodness sake) {
#     be good
# }

import os, string, glob, sys, popen2, time
import getopt
from getpass import getuser
from string import split, join
from fnmatch import filter

import _mpxhooks
_mpxhooks.load_properties_warning = False

from mpx.install import run_install_script, build_pkg_db

PSOURCE=os.popen("psource 2>/dev/null").readlines()[0].strip()
PBUILD=os.popen("proot 2>/dev/null").readlines()[0].strip()

class BuildHelper:
    def __init__(self):
        self._srcdir = PSOURCE
        self._builddir = PBUILD
        self._tag_and_changelog = 0
        self._generate_buildset = 0
        self._validatepkgs = 0
        self._debug = 0
        self._help = 0
        self._revision_string = None
        self._previous_revision_string = None
        self._package_db = None
        self._cwd = os.getcwd()  # This should be the build directory

    def debug(self):
        return self._debug

    def _get_version_file(self):
        if not hasattr(self, '_version_file'):
            self._version_file = os.path.realpath(os.path.join(self._srcdir,
                                                               'BROADWAY'))
        return self._version_file

    def _get_previous_version_file(self):
        if not hasattr(self, '_previous_version_file'):
            self._previous_version_file = os.path.realpath(
                os.path.join(self._srcdir, 'BROADWAY.prev'))
        return self._previous_version_file

    def _get_original_version(self):
        return self._original_version

    def _get_package_db(self):
        if not self._package_db:
            self._package_db = self._build_pkg_db()
        return self._package_db

    def _get_version_from_file(self):
        f = None
        version = "unknown"
        f = open(self._get_version_file())
        version = f.readline().strip()
        if f:
            f.close()
        return version

    def _put_version(self, version):
        if self._debug:
            print 'DEBUG: _put_version: new version would be %s' % version
            return

        fname = self._get_version_file()
        f = open(fname, 'w+')
        f.write(version)
        f.write('\n')
        f.close()

    def _put_previous_version(self, version):
        if self._debug:
            print 'DEBUG: _put_previous_version: new previous version would be %s' % version
            return

        fname = self._get_previous_version_file()
        f = open(fname, 'w+')
        f.write(version)
        f.write('\n')
        f.close()

    def _get_previous_revision(self):
        if not self._previous_revision_string:
            f = open(self._get_previous_version_file())
            self._previous_revision_string = f.readline().strip()
            f.close()
        return self._previous_revision_string

    def _get_revision(self):
        if not self._revision_string:
            if '+' in self._revision:
                r = self._revision.split('.')
                v = self._original_version.split('.')
                for j in range(0, len(r)):
                    if r[j][0] == '+':
                        v[j] = str( int( v[j] ) + int( r[j][1:] ) )
                    self._revision_string = join(v, '.')
            else:
                self._revision_string = self._original_version

        return self._revision_string

    def _system_with_output(self, cmd):
        child = popen2.Popen4( cmd )
        answer = string.strip(child.fromchild.read())
        status = child.wait()
        return (answer, status)

    def _generate_changelog(self):
        print ('Generating changelog between %s and %s in ./changelog.html...' %
               (self._get_previous_revision(), self._get_revision())
               )
        cmd  = 'cd %s;' % self._srcdir
        cmd += 'buildsup/changelog -s'
        cmd += 'broadway_$(echo "%s" | ' % self._get_previous_revision()
        cmd += 'sed \'s/[$$,.:;@]/_/g\') -e'
        cmd += 'broadway_$(echo "%s" | ' % self._get_revision()
        cmd += 'sed \'s/[$$,.:;@]/_/g\') > changelog.html'
        if self._debug:
            print 'DEBUG: ACTION: %s' % cmd
        else:
            os.system(cmd)

    def _tag_release(self):
        print 'Tagging release in SVN...'
        cmd  = 'cd %s;' % self._srcdir
        cmd += 'svn commit -m \'CSCtj92552 %s\' BROADWAY BROADWAY.prev' % self._get_revision()
        print '_tagandrelease: (148) %s' % cmd
        if self._debug:
            print 'ACTION: %s' % cmd
        else:
            os.system(cmd)
        cmd  = 'cd %s;' % self._srcdir
        cmd += ' svn copy ../broadway/ ' 
	cmd += ' https://wwwin-svn-sjc.cisco.com/cbsbu/broadway/tags/'
	cmd += 'broadway_$(echo "%s" | sed \'s/[$$,.:;@]/_/g\')' % self._get_revision()
	cmd += ' -m "CSCtj92552 release tag for %s"' % self._get_revision()
	print '_tagandrelease: (157) %s' % cmd

	if self._debug:
		print 'ACTION: %s' % cmd
	else:
		print '_tagandrelease: executing: %s' % cmd    
		os.system(cmd)


    def _mail_changelog(self):
        cmd  = 'metasend -b -m text/html -f %s/changelog.html -s ' % self._builddir
        cmd += '"Changelog for Broadway'
        cmd += '%s" -t eng@envenergy.com' % self._get_revision()
        if self._debug:
            print 'ACTION: %s' % cmd
        else:
            os.system(cmd)

    def _build_pkg_db(self):
        # Get a list of all package install scripts in the directory tree.
        package_db = {}
        build_pkg_db(self._cwd, None, package_db)
        return package_db

    def _open_build_info(self, xfile):
        xfile.write('    <buildinfo>\n')
        return

    def _add_buildinfo_param(self, xfile, name, value):
        xfile.write('        <param name="%s" value="%s"/>\n' % (name, value))
        return
    def _close_build_info(self, xfile):
        xfile.write('    </buildinfo>\n')
        return

    def _as_search_path(self, list):
        path = ''
        for p in list:
            if not p: p = '.'
            if path:
                path += ':'
            path += p
        return path

    def _as_command_line(self, list):
        line = ''
        for t in list:
            token = ''
            for c in t:
                if c.isspace: t += '\\' # Is this special in XML?
                token += c
            if line: line += ' '
            line += token
        return line

    # Store the package database in XML format for use by extraction tools.
    # The database looks something like this:
    #
    #  <?xml version="1.0" encoding="ASCII"?>
    #  <buildset release="1.0.0">
    #     <buildinfo>
    #          <param name="release" value="1.0.84"/>
    #          <param name="user" value="mevans"/>
    #          <param name="host" value="fearfactory.envenergy.com"/>
    #          <param name="buildpath" value="/home/mevans/source/broadway"/>
    #          <param name="pythonpath" value=".:/home ... source-packages"/>
    #          <param name="command" value="./prelease -D -p"/>
    #          <param name="timestamp" value="Fri, 12 Jul 2002 01:05:32 +0000"/>
    #      </buildinfo>
    #      <package name="broadway">
    #          <description>The Mediator Framework</description>
    #      </package>
    #      <package name="trane.tsws">
    #          <description>Trane Tracer Summit Web Server</description>
    #          <requirement>broadway</requirement>
    #      </package>
    #  </buildset>
    #
    def _save_pkg_db_as_xml(self, file_name, revision, package_db):
        package_names = package_db.keys()
        package_names.sort()

        xfile = open(file_name, "w+")

        xfile.write('<?xml version="1.0" encoding="ASCII"?>\n')
        xfile.write('<buildset')
        xfile.write(' release="%s"' % revision)
        xfile.write('>\n')

        self._open_build_info(xfile)
        self._add_buildinfo_param(xfile, 'timestamp', # RFC 2822 compliant date-time.
                                  time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                                time.gmtime()))
        self._add_buildinfo_param(xfile, 'user', getuser())
        self._add_buildinfo_param(xfile, 'host', os.uname()[1])
        self._add_buildinfo_param(xfile, 'buildpath', self._cwd)
        self._add_buildinfo_param(xfile, 'pythonpath', self._as_search_path(sys.path))
        self._add_buildinfo_param(xfile, 'command', self._as_command_line(sys.argv))
        self._add_buildinfo_param(xfile, 'pythonshell', sys.executable)
        self._close_build_info(xfile)

        for p in package_names:
            infomap = package_db[p]
            xfile.write( '    <package name="%s">\n' % infomap['package'] )
            xfile.write( '        <description>%s</description>\n'
                         % infomap['description'] )
            for req in infomap['dependencies']:
                xfile.write( '        <requirement>%s</requirement>\n' % req )
            xfile.write( '    </package>\n' )
        xfile.write( '</buildset>\n' )
        xfile.close()

    ##
    # Note:  do_tag_and_changelog has the side-effect of changing the version
    #        string in BROADWAY and in BROADWAY.prev
    def do_tag_and_changelog(self):
        # Force a read of the previous revision before we write the new one
        self._get_previous_revision()

        self._put_version(self._get_revision())
        self._put_previous_version(self._get_revision())
        self._tag_release()
        self._generate_changelog()

    def do_generate_buildset(self):
        buildset_name = 'prelease.d/buildset.xml'
        self._save_pkg_db_as_xml(buildset_name, self._get_revision(), self._get_package_db())

    def compute_targetdir(self, srcdir):
        tmpdir = srcdir[0:]
        adddir = []
        while 1:
            x,y=os.path.split(tmpdir)
            if y == 'broadway':
                break
            else:
                tmpdir = x
                adddir.append(y)
        adddir.reverse()
        retdir = self._cwd
        for d in adddir:
            retdir = os.path.join(retdir, d)
        return retdir

    def parse_version_file(self):
        self._original_version = self._get_version_from_file()

        # Set PYTHONPATH to the build directory so that the various install
        # files will be able to find their imports, etc.
        os.environ['PYTHONPATH'] = self._cwd

        template = []
        for place in self._get_version_from_file().split('.'):
            template.append('0')

        ###
        # 'tagandchangelog' should be the only operation that increments
        # the version...
        if self._tag_and_changelog:
            template[-1] = '+1'
        else:
            template[-1] = '0'

        self._revision = join(template, '.')

        if self._debug:
            print 'DEBUG: self._original_version is %s' % self._original_version
            print 'DEBUG: self._revision is %s' % self._revision

        return

    def validate_packages(self):
        if self._debug:
            print "DEBUG: Validating all packages in the build directory."
        pkg_db = {}
        build_pkg_db(self._builddir, None, pkg_db)
        nerrors = 0
        for pkg_key,pkg_info in pkg_db.items():
            pkg_file = pkg_info['script_name']
            pkg_name = pkg_info['package']
            pkg_props = pkg_info.get('properties','')
            if self._debug:
                print "DEBUG: key=%r, name=%r\nDEBUG: file=%r" % (
                    pkg_key, pkg_name,pkg_file
                    )
                if pkg_props:
                    print "DEBUG: properties_pyc=%r" % pkg_props
            if pkg_key != pkg_name:
                print "ERROR: Package DB key (%s)" % pkg_key,
                print "does not match it's internal",
                print "name package name (%s)" % pkg_name
                nerrors += 1
            pkg_basename = pkg_file.split('/')[-1]
            if pkg_name != pkg_basename[:-len('.install.pyc')]:
                print "ERROR: Package name (%s)" % pkg_name,
                print "is not consistant with it's",
                print "filename (%s)" % pkg_basename
                nerrors += 1
            if nerrors:
                raise SystemExit("ERROR: Package validation failed.")
        return

    def parse_cmdline(self):
        try:
            opts, args = getopt.getopt( sys.argv[1:], 'b:dghVs:t',
                                                      [
                    "builddir=",
                    "debug",
                    "generatebuildset",
                    "help",
                    "sourcedir=",
                    "tagandchangelog",
                    "validatepkgs",
])
        except getopt.GetoptError, e:
            print e
            return 0

        for o, a in opts:
            if o in ("-t", "--tagandchangelog"):
                self._tag_and_changelog = 1

            if o in ("-g", "--generatebuildset"):
                self._generate_buildset = 1

            if o in ("-d", "--debug"):
                self._debug = 1

            if o in ("-s", "--sourcedir"):
                self._srcdir = a
                if self._debug:
                    print 'Setting sourcedir to \"%s\"' % self._srcdir

            if o in ("-b", "--builddir"):
                self._builddir = a
                if self._debug:
                    print 'Setting builddir to \"%s\"' % self._builddir

            if o in ("-h", "--help"):
                self._help = 1

            if o in ("-V", "--validatepkgs"):
                self._validatepkgs = 1

        return 1

    def usage(self):
#--------1---------2---------3---------4---------5---------6---------7-------x-#
        print """
BUILD_HELPER version $Revision: 20164 $, $Date: 2011-03-16 05:01:03 -0700 (Wed, 16 Mar 2011) $
Usage: build_helper.py [options]

Options are:
     --sourcedir=SRCDIR  Specify source path as SRCDIR %(sourcedir)s
     --builddir=BLDDIR   Specify build path as BLDDIR %(builddir)s

     --debug             Process debug. Print, but don't execute CVS commands
     --generatebuildset  Generate buildset.xml
     --help              You're looking at it
     --tagandchangelog   Tag the source tree with the new version
     --validatepkgs      Run consistancy checks on the packages
""" % { "sourcedir" : ("\n"+25*" "+"[%s]")%PSOURCE if PSOURCE else "[REQUIRED]",
        "builddir" : ("\n"+25*" "+"[%s]" )%PBUILD if PBUILD else "[REQUIRED]" }
#--------1---------2---------3---------4---------5---------6---------7-------x-#

    def run(self):
        if not self.parse_cmdline():
            return 0

        if self._help:
            self.usage()
            return 1

        if not self._srcdir:
            print "ERROR: No source directory specified\n"
            return 0

        if not self._builddir:
            print "ERROR: No build directory specified\n"
            return 0

        self.parse_version_file()

        if self._tag_and_changelog:
            self.do_tag_and_changelog()

        if self._generate_buildset:
            self.do_generate_buildset()

        if self._validatepkgs:
            self.validate_packages()

        return 1

#=----------------------------------------------------------------------------

def main():
    main = BuildHelper()

    result = not main.run()

    return result

if __name__ == '__main__':
    exit_status = main()
    sys.exit(exit_status)
