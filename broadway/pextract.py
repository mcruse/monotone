"""
Copyright (C) 2003 2005 2007 2010 2011 Cisco Systems

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

import sys
import os
import errno
import getopt
import xml.dom.minidom
import popen2

def get_xml_data_from_archive( archive_file ):
    import popen2
    
    cmd = "tar -xOf %s buildset.xml" % archive_file
    child = popen2.Popen4( cmd )
    xml_data = child.fromchild.read()
    status = child.wait()
    if status:
        raise IOError( status, xml_data )
    return xml_data

def get_package_db_from_xml( xml_data ):
    assert( xml_data != None )
    
    doc = xml.dom.minidom.parseString( xml_data )
    package_db = {}

    for node in doc.getElementsByTagName( "package" ):
        infomap = {}
            
        name = str( node.getAttribute( "name" ) )
        infomap['package'] = name
        
        elems = node.getElementsByTagName( "description")[0]
        infomap['description'] = str( elems.childNodes[0].data )
        
        dependencies = []
        elems = node.getElementsByTagName( "requirement" )
        for req in elems:
                dependencies.append( str( req.childNodes[0].data ) )
        infomap['dependencies'] = dependencies
        
        package_db[name] = infomap

    return package_db
    

def save_reduced_xml( fileName, xml_data, package_list ):
    xfile = open( fileName, 'w' )
    doc = xml.dom.minidom.parseString( xml_data )

    buildsetNode = doc.getElementsByTagName( "buildset" )[0]
    
    for node in doc.getElementsByTagName( "package" ):
        name = str( node.getAttribute( "name" ) )
        if name not in package_list:
            buildsetNode.removeChild( node )
            node.unlink()

    doc.writexml( xfile )
    xfile.close()


def _display_help( msg = None ):
    if msg:
        print msg
        
    print 'Usage: pextract [options] archive [package1 package2 ... packageN]'
    print 'Options:'
    print '  -h or --help               displays this help message'
    print '  -l or --list               list packages in archive and exit'
    print '  -v or --verbose            display names of extracted files'
    print '  -b or --base       <dir>   extract packages to specified base directory'
    print '  -t or --trimmer    <dir>   the nodedef trimmer directory'
    print '  -d or --dist       <file>  create distribution file; -b can be used to'
    print '                             specify dir used for temporary files.'
    print '  -u or --uid        <uid>   set the user and group id to <uid>'
    print '\nThe default action is to extract all packages from the archive.\n'

    
def _system( cmd ):
    status = os.system( cmd )
    if os.WIFEXITED(status) and os.WEXITSTATUS(status):
        # Raise SystemExit
        sys.exit( os.WEXITSTATUS(status) )
    assert( status == 0 )


# Do the trimming of the nodedefs.xml
def _trim( baseDir, broadway, trimmer, packages ):
    print 'Trimming nodedefs...'
    extractedBroadway = os.path.join( baseDir, 'broadway' )
    _system( "java -jar %s -broadway=%s -trim=%s"
             % (os.path.join( trimmer, 'nodedef_trimmer.jar' ), broadway, extractedBroadway) )
    #
    # Post-process Nodedef trimming.
    #
    # The node trimmer updates the <created> tag with the current
    # timestamp.  Unfortunately, this guarantees that there will
    # never be two extracted nodedefs from the same release with
    # the same md5.  To resolve this, the following POST-PROCESSING
    # updates the extracted nodedefs and resets the <created> tag
    # to match the original nodedefs from the release.
    #
    # The version stored in the trimmed nodedefs is identified with
    # a "_trimmed" suffix on the version which is stored in the
    # nodedefs themselves.  The unencoded version is "ugly enough",
    # adding the _trimmed extension while honest, is not helpful to
    # the typical user.  To fix this, the REAL release version is
    # parsed and then a new version string is created in the form:
    #    application major.minor.revision (code), where:
    #       application          = MPX|Evaluation Kit
    #       major.minor.revision = The standard, dot separated version.
    #       code                 = Encodes the release type and build number
    #                              so we can tell if the build is official
    #                          R#      = 'Official release', build #.
    #                          E#      = 'Engineering release', build #.
    #                          D#-name = Development release, build #, built
    #                                    by user 'name'.
    #
    # @fixme This is ugly and should be moved into the actual trimming
    #        code and all of these scripts should be in the tools
    #        "package" which should be used to make releases completely
    #        self-describing...
    #
    _app_text = 'Custom'
    if 'envenergy.eval_system' in packages:
        _app_text = 'Evaluation System'
    elif 'envenergy.mpx' in packages:
        _app_text = 'MPX'
    _system(('cd broadway/nodedef ;'
             ' DATE=$(grep \<created\> nodedefs.xml_Old |'
             '        sed "s:.*<created>\(.*\)</created>.*:\\1:g") ;'
             ' mv nodedefs.xml nodedefs.xml-orig ;'
             ' echo "POST-PROCESSING: Reset <created> tag to \'$DATE\'." ;'
             ' RELVER="<version>$(cat ../BROADWAY 2>/dev/null)</version>" ;'
             ' [ "$RELVER" == "" ] && '
             '   RELVER=$(grep \<version\> nodedefs.xml_Old) ;'
             ' APPVER=$(echo $RELVER |'
             '  sed "{\n'
             '   s:.*<version>\(.*\)\.build\.\([0-9]\+\)</version>.*:'
             '\\1 (R\\2):g\n'
             '   s:.*<version>\(.*\)\.dev\.\([0-9]\+\)</version>.*:'
             '\\1 (E\\2):g\n'
             '   s:.*<version>\(.*\)\.build\.\([0-9]\+\)-\(.*\)</version>.*:'
             '\\1 (D\\2-\\3):g\n'
             '   s:.*<version>\(.*\)\.dev\.\([0-9]\+\)-\(.*\)</version>.*:'
             '\\1 (D\\2-\\3):g\n'
             '   }") ;'
             ' APPVER="%s ${APPVER}" ;'
             ' sed "{\n'
             '  s|\(.*<created>\)\(.*\)\(</created>.*\)|\\1$DATE\\3|g\n'
             '  s|\(.*<version>\)\(.*\)\(</version>.*\)|\\1$APPVER\\3|g\n'
             '}" nodedefs.xml-orig > nodedefs.xml ;'
             ' echo "POST-PROCESSING: Changed <version> tag to \'$APPVER\'." ;'
             ' echo "POST-PROCESSING: Updating MD5." ;'
             ' rm nodedefs.md5 ;'
             ' md5sum nodedefs.xml | awk \'{print $1}\' > nodedefs.md5 ;'
             ' echo POST-PROCESSING: Recreating ZIP. ;'
             ' rm nodedefs.zip ;'
             ' zip nodedefs.zip nodedefs.xml ;'
             ' echo POST-PROCESSING: Deleting nodedefs.xml* ;'
             ' rm nodedefs.xml*') % _app_text)

################################  M A I N  ################################

def main():
    #
    # Process command line options.
    #
    
    list = 0
    isVerbose = 0
    baseDir = None
    distributionFile = None
    trimmer = ''
    broadway = popen2.Popen3( 'psource' ).fromchild.readline()[:-1]
    
    try:
        optlist, args = getopt.getopt( sys.argv[1:],
                                       'hlvb:t:d:u:r:',
                                       ['help', 'list', 'verbose', 'base=',
                                        'trimmer=', 'dist=', 'uid=', 'root='] )
        root = None
        for o, a in optlist:
            if  o in ('-h','--help'):
                _display_help()
            elif o in ('-l','--list'):
                list = 1
            elif o in ('-v','--verbose'):
                isVerbose = 1
            elif o in ('-b','--base'):
                baseDir = a
            elif o in ('-t', '--trimmer'):
                trimmer = os.path.abspath( a )
            elif o in ('-d', '--dist'):
                distributionFile = a
            elif o in ('-u', '--uid'):
                os.setgid( int( a ) )
                os.setuid( int( a ) )
            elif o in ('-r', '--root'):
                # handles case where cur dir is NOT in a broadway src or bld tree:
                curDir = os.getcwd()
                proc_cmd = '(cd %s; psource; cd %s)' %(a,curDir)
                broadway = popen2.Popen3(proc_cmd).fromchild.readline()[:-1]
                if (broadway is None) or (len(broadway) < 1):
                    raise Exception('broadway value is invalid: %s' % broadway)
    except getopt.GetoptError,data:
        _display_help( data )
        return 0
    
    # Normalize the distribution file name, if any.
    if distributionFile:
        if not distributionFile.endswith( '.tgz' ):
            distributionFile += '.tgz'
        realDistributionFile = os.path.realpath( distributionFile )

    if len( args ) > 0:
        archive = os.path.realpath( args[0] )
        packages = args[1:]
    else:
        _display_help( 'no archive specified' )
        return 0
    
    #
    # Pull the package database from the archive.
    #
    
    xml_data = get_xml_data_from_archive( archive )
    package_db = get_package_db_from_xml( xml_data )
    archived_packages = package_db.keys()
    archived_packages.sort()
    
    #
    # Display the list of archived packages if requested to do so.
    #
    
    if list:
        field_with = 0
        for p in archived_packages:
            if len( p ) > field_with:
                field_with = len( p )
        for p in archived_packages:
            print "%-*s: %s" % (field_with + 1, p, package_db[p]['description'])
        return 0
    
    #
    # Extract the requested packages.
    #
    
    # Default to all if none specified.
    if not len( packages ):
        packages = archived_packages
    
    # Add dependencies to the package list.  This process is reiterated until no
    # more dependencies are added.  Not as efficient as recursion, but so what?
    errors = 0
    n = 0
    while n < len( packages ):
        n = len( packages )
        for p in packages:
            if package_db.has_key( p ):
                for req in package_db[p]['dependencies']:
                    if not req in packages:
                        print "Adding package '%s' as required by '%s'" % (req, p)
                        packages.append( req )
            else:
                print "No such package: ", p
                errors += 1
    
    if errors:
        print "Extraction terminated due to errors."
        return errno.ENOPKG
        
    # Determine name of the directory where files will be extracted to.  When creating
    # distributions, the default is to create an extraction directory in the directory
    # specified by TEMP_DIR.  The extraction directory is removed after the distribution
    # is created.
    if distributionFile:
        if not baseDir:
            baseDir = os.getenv( 'TEMP_DIR' )
            if not baseDir:
                baseDir = '/tmp'
        if not os.path.isdir( baseDir ):
            print "no such directory: ", baseDir
            sys.exit( 1 )
        baseDir = os.path.join( baseDir, 'pextract' + str( os.getpid() ) )
    else:
        if not baseDir:
            baseDir = './'
    
    # Create the extraction directory if it doesn't exist.
    if not os.path.exists( baseDir ):
        os.makedirs( baseDir )
    baseDir = os.path.realpath( baseDir )
    
    # Determine the path of the nodedef trimmer tool.
    if not trimmer:
        trimmer = os.path.join( broadway, 'buildsup' )
        trimmer = os.path.abspath( trimmer )
    if not os.path.isdir( trimmer ):
        print 'The location of the nodedef trimmer is unknown.'
        print 'Expected to find directory %s.' % trimmer
        print 'Use the --trimmer option.'
        return errno.ENOENT
    
    # Change to the extraction directory.
    cwd = os.getcwd()
    os.chdir( baseDir )
    
    flag = ''
    if isVerbose:
        flag = 'v'
    
    # Extract the packages.
    for p in packages:
        print "Extracting %s..." % p
        _system( 'tar Oxf %s %s-pkg.tgz | tar -x%sz' % (archive, p, flag) )
    
    save_reduced_xml( 'broadway/buildset.xml', xml_data, packages )
    
    if os.path.isdir( os.path.join( baseDir, 'nodedef' )):
        _trim( baseDir, broadway, trimmer, packages )
    
    # Create a ditribution file, if so directed.
    if distributionFile:
        print 'Creating distribution file %s...' % distributionFile
        _system( 'tar cz%sf %r ./' % (flag, realDistributionFile) )
    
    # Back to where we started.
    os.chdir( cwd )
    
    # Remove the extraction directory if a distribution was built.
    if distributionFile:
        print 'Removing temporary files...'
        _system( 'rm -rf %s' % baseDir )

    return 0
        
try:
    sys.exit( main() )
except SystemExit:
    raise
except EnvironmentError, e:
    print str( e )
    sys.exit( e.errno )
except Exception, e:
    print str( e )
    sys.exit( -1 )

