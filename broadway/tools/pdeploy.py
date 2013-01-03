"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
import os, thread, sys, getopt, string, signal, pwd
import ConfigParser
from popen2 import Popen4
from select import select
from time import sleep
from glob import glob
from stat import *
from Tkinter import *
from tkFileDialog import askopenfilename, asksaveasfilename
from tkMessageBox import *

import mpx

from _pdeploy import flash

_PROGRAM_NAME = os.path.basname(sys.argv[0])
_PROGRAM_VER  = mpx.properties.RELEASE

_progress_log = ""
_LOGO_FILE    = os.path.dirname(sys.argv[0])
_LOGO_FILE    = os.path.join(_LOGO_FILE, "_pdeploy")
_LOGO_FILE    = os.path.join(_LOGO_FILE, "logo.png")
_LOGO_FILE    = os.path.realpath(_LOGO_FILE)

# Background colors for list box.
_TEST_COLOR   = "lightblue"
_DEV_COLOR    = "red"
_GOLD_COLOR   = "gold"
_DFLT_COLOR   = "white"  # lightgray is also a good choice

##############################################################################
#
# Helper functions for verifying config values.
#
##############################################################################

# Return true if the block mode disk device exists.
def _isdisk( value ):
    try:
        return S_ISBLK( os.stat( value )[ST_MODE] )
    except:
        pass
    return 0
    

##############################################################################
#
# Names of configuration options.  These appear in the options dialog in
# alphabetical order, thus the funny names.
#
##############################################################################
_MOE_DIR     = '00moe_dir'
_DEVREL_DIR  = '02development_dir'

_RELEASE_DIR = '01release_dir'
_GOLDREL_DIR = '03product_dir'
_DISTRIB_DIR = '04distrib_dir'
_FLASH_DEV   = '05flash_dev'
_MOUNT_POINT = '06mount_point'

##
#
# <pre>
#                 option name  : [label,
#                                 default value,
#                                 verifier]
# </pre>
_CONFIG_MAP  = { _MOE_DIR     : ['MOE directory',
                                 '/home/moe',
                                 os.path.isdir],
                 _RELEASE_DIR : ['Test release directory',
                                 '/home/mediator/test',
                                 os.path.isdir],
                 _DEVREL_DIR  : ['Dev release directory',
                                 '/home/mediator/dev',
                                 os.path.isdir],
                 _GOLDREL_DIR : ['Gold release directory',
                                 '/home/mediator/gold',
                                 os.path.isdir],
                 _DISTRIB_DIR : ['Distribution directory',
                                 '/usr/home/netinstall/distributions',
                                 os.path.isdir],
                 _FLASH_DEV   : ['Flash device',
                                 '/dev/hda',
                                 _isdisk],
                 _MOUNT_POINT : ['Mount point for flash device',
                                 '/mnt',
                                 os.path.isdir],
               }

##############################################################################
#
# Helper functions for dealing with release archive's XML database.
#
##############################################################################

def get_xml_data_from_archive( archive_file ):
    import popen2
    
    child = popen2.Popen4( "tar -xOf %s buildset.xml" % archive_file )
    xml_data = child.fromchild.read()
    status = child.wait()
    if status:
        return None
    return xml_data


def get_package_db_from_xml( xml_data ):
    if xml_data == None:
        return None
    
    import xml.dom.minidom
    
    doc = xml.dom.minidom.parseString( xml_data )
    package_db = {}
    
    # Note: should be exactly one buildset.
    buildsets = doc.getElementsByTagName( "buildset" )
    release = str( buildsets[0].getAttribute( "release" ) )

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

    return (release, package_db)


##############################################################################
#
# Helper function to extract information from the passwd file.
# See pwd module documentation for valid values of infoID.
#
##############################################################################
def getUserInfo( userName, infoID ):
    try:
        return pwd.getpwnam( userName )[infoID]
    except:
        pass
    return None
        

##############################################################################
#
# Return the name of the directory where tool is located, or None if not found.
#
##############################################################################
def find_tool( releaseFileName, tool ):
    if releaseFileName:
        reldir = os.path.dirname( releaseFileName )
        if os.path.isfile( os.path.join( reldir, tool ) ):
            return reldir

    return None

class ScrolledText( Frame ):
    def __init__( self, parent ):
        Frame.__init__( self, parent )
        self.pack( expand = YES, fill = BOTH )
        
        sbar = Scrollbar( self )
        text = Text( self, relief = SUNKEN )
        sbar.config( command = text.yview )
        text.config( yscrollcommand = sbar.set )
        sbar.pack( side = RIGHT, fill = Y )
        text.pack( side = LEFT, expand = YES, fill = BOTH )
        self.text = text
        
        self.focus_set()
        self.grab_set()
        
    def displayText( self, text ):   
        self.text.config( state = NORMAL )
        self.text.delete( '1.0', END )
        self.text.insert( '1.0', text )
        self.text.mark_set( INSERT, '1.0' )
        self.text.focus()
        self.text.config( state = DISABLED )

    def displayFile( self, fileName ):   
        text = open( fileName, 'r').read()
        self.displayText( text )
        
        
class ConfigDialog( Toplevel ):
    def __init__( self, parent ):
        Toplevel.__init__( self, parent )
        self.cfg_keys = _CONFIG_MAP.keys()
        self.cfg_keys.sort()

        max_width = 0
        max_height = 30
        for cfg_key in self.cfg_keys:
            cfg_item = _CONFIG_MAP[cfg_key]
            label_len = len( cfg_item[0] )
            if label_len > max_width:
                max_width = label_len
            max_height += 25
        
        self.transient( parent )
        geo = "500x%d+%d+%d" % ( max_height,
                                 parent.winfo_rootx() + 50,
                                 parent.winfo_rooty() + 50 )
        self.geometry( geo )
        self.protocol( 'WM_DELETE_WINDOW', self.destroy )
        self.title( "Configuration options" )
        
        self.entries = []
        
        for cfg_key in self.cfg_keys:
            cfg_item = _CONFIG_MAP[cfg_key]
            rowFrame = Frame( self )
            lab = Label( rowFrame, width = max_width, text = cfg_item[0] )
            ent = Entry( rowFrame, bg = 'white' )
            lab.pack( side = LEFT )
            ent.pack( side = RIGHT, expand = YES, fill = X )
            rowFrame.pack( side = TOP, fill = X )
            
            ent.insert( 0, cfg_item[1] )
            self.entries.append( ent )
        
        buttonFrame = Frame( self )
        Button( buttonFrame, text = 'OK', command = self._ok ).pack( side = LEFT )
        Button( buttonFrame, text = 'Cancel', command = self._cancel ).pack( side = LEFT )
        buttonFrame.pack( side = BOTTOM )
        
        self.focus_set()
        self.grab_set()
        self.wait_window()
        
    def _cancel( self ):
        self.destroy()
        
    def _verifiy_config( self ):
        errors = 0
        i = 0
        while i < len( self.entries ):
            optionName = self.cfg_keys[i]
            optionValue = self.entries[i].get()
            verifier = _CONFIG_MAP[optionName][2]
            if verifier:
                if not apply( verifier, [optionValue] ):
                    showerror( "Configuration Error",
                               "'%s' is not a valid value for option '%s'" % (optionValue, _CONFIG_MAP[optionName][0]) )
                    errors += 1
            i += 1
        return errors
        
    def _ok( self ):
        if self._verifiy_config() == 0:
            global cfg_parser

            i = 0
            while i < len( self.entries ):
                optionName = self.cfg_keys[i]
                optionValue = self.entries[i].get()
                _CONFIG_MAP[optionName][1] = optionValue
                cfg_parser.set( 'DEFAULT', optionName, optionValue )
                i += 1

            cfg_parser.save()
            self.destroy()
        

class RootDialog( Toplevel ):
    BUSY = "BUSY"
    OK = "OK"
    CANCEL = "CANCEL"
    def __init__( self, parent ):
        Toplevel.__init__( self, parent )
        self.exit_action = self.BUSY
        self.transient( parent )
        geo = "225x125+%d+%d" % ( parent.winfo_rootx() + 100, parent.winfo_rooty() + 100 )
        self.geometry( geo )
        self.protocol( 'WM_DELETE_WINDOW', self.destroy )
        self.title( "Login as root" )
        
        msgFrame = Frame( self )
        msgLabel = Label( msgFrame, text = """
You must be running as the
root user to use this program
""" )
        msgLabel.pack( side = LEFT )
        msgFrame.pack( side = TOP )

        passwdFrame = Frame( self )
        passwdLabel = Label( passwdFrame, text = 'Root password' )
        self.passwd = StringVar()
        self.passwd.set( '' )
        passwdEntry = Entry( passwdFrame, bg = 'white', show = '*',
                             textvariable = self.passwd )
        passwdLabel.pack( side = LEFT )
        passwdEntry.pack( side = RIGHT, expand = YES, fill = X )
        passwdFrame.pack( side = TOP, fill = X )
        
        buttonFrame = Frame( self )
        Button( buttonFrame, text = 'OK', command = self._ok ).pack( side = LEFT )
        Button( buttonFrame, text = 'Cancel', command = self._cancel ).pack( side = LEFT )
        buttonFrame.pack( side = BOTTOM )
        
        # Make the dialog modal and set focus to the password field for convenience.
        self.grab_set()
        passwdEntry.focus_set()
        self.wait_window()
        return

    def _cancel( self ):
        self.exit_action = self.CANCEL
        self.destroy()
        return

    def _ok( self ):
        self.exit_action = self.OK
        self.destroy()
        return


class ProcessingDialog( Toplevel ):
    def __init__( self, parent, title, function, args ):
        Toplevel.__init__( self, parent )
        self.transient( parent )
        self.geometry( "400x140+%d+%d" % (parent.winfo_rootx() + 50,
                                          parent.winfo_rooty() + 50 ))
        self.protocol( 'WM_DELETE_WINDOW', self.destroy )
        self.title( title )
        
        self.prog_frame = Frame( self, width = 400, height = 80 )
        self.prog_frame.pack( expand = YES, fill = BOTH )
        self.label = Label( self.prog_frame )

        self.progress_var = IntVar()
        self.progress_scale = Scale( self.prog_frame, variable = self.progress_var,
                                     from_ = 0, to = 100, length = 300,
                                     tickinterval = 10 ,
                                     orient = 'horizontal' )
        
        self.progress_scale.pack( side = BOTTOM )
        self.label.pack( side = BOTTOM )
        
        Button( self, text = 'Cancel', command = self._cancel ).pack( side = BOTTOM )
        
        self.focus_set()
        self.grab_set()
        
        self.lock = thread.allocate_lock()
        self.percentDone = 0
        self.stage = ''
        self.isCancelled = 0
        self.done = 0
        self.completionStatus = None
        
        global _progress_log
        _progress_log = ""

        thread.start_new_thread( function, args )
        
        while 1:
            self.label.config( text = self.stage )
            
            self.lock.acquire()
            self.progress_var.set( self.percentDone )
            self.lock.release()
            
            self.update()
            if self.done:
                break;
            self.after( 250 )
            
        if self.completionStatus:
            isError = self.completionStatus[0]
            if self.completionStatus[1] != None:
                title = self.completionStatus[1]
            msg = self.completionStatus[2]
            if isError:
                showerror( title, msg + '\nView log for details.' )
            else:
                showinfo( title, msg )
            
        self.destroy()
        
    def _set_progress( self, percent, msg = '' ):
        isCancelled = 0
        
        self.lock.acquire()
        if self.isCancelled:
            isCancelled = 1
        else:
            self.stage = msg
            if percent >= 100:
                percent = 100
            self.percentDone = percent
        self.lock.release()
        
        if isCancelled:
            raise KeyboardInterrupt

    def _proc_message( self, msg ):
        global _progress_log
        _progress_log += msg

    def _cancel( self ):
        self.lock.acquire()
        self.isCancelled = 1
        self.lock.release()
        

class FlashingDialog( ProcessingDialog ):
    def __init__( self, parent, moeFileName, releaseFileName, package_info ):
        self.etitle = 'Flash Error'
        ProcessingDialog.__init__( self, parent,
                                   "Flashing " + package_info['package'],
                                   self._flashProcess, (moeFileName, releaseFileName, package_info) )

    def _flash_progress( self, flash, step, of ):
        pass

    def _flash_message( self, flash, msg ):
        self._proc_message( msg + '\n' )
        
    def _flash( self, moeFileName, releaseFileName, package_info ):
        isMounted = 0
        try:
            pextractDir = find_tool( releaseFileName, 'pextract' )
            if not pextractDir:
                self.completionStatus = (1, self.etitle,
                                         "Unable to locate pextract tool.\n"
                                         "Check config options and try again.")
                return

            dev = _CONFIG_MAP[_FLASH_DEV][1]
            mnt = _CONFIG_MAP[_MOUNT_POINT][1]
            flasher = flash.Flash( dev, mnt,
                                   self._flash_progress,   # Progress reports
                                   self._flash_message,    # stdout
                                   self._flash_message )   # stderr

            self._set_progress( 0, "Creating partition" )
            flasher.make_partition()
            
            self._set_progress( 5, "Initializing file system" )
            flasher.make_filesystem()
            
            self._set_progress( 15, "Mounting file system" )
            flasher.mount()
            isMounted = 1
            
            self._set_progress( 25, "Installing Mediator Operating Environment" )
            flasher.extract_moe( moeFileName )
            
            self._set_progress( 50, "Creating boot record" )
            flasher.make_bootrecord()
            
            pkgName = package_info['package']
            self._set_progress( 60, "Installing package " + pkgName )
            flasher.extract_packages( releaseFileName, pkgName, pextractDir )  
            
            self._set_progress( 90, "Unmounting file system" )
            flasher.umount()
            isMounted = 0
            
            self._set_progress( 100 )
            self.completionStatus = (0, None, "Flashing complete.")
               
        except KeyboardInterrupt:
            self._proc_message( 'Flash operation cancelled by user request.\n' )
        
        except flash.FlashCommandError, fce:
            self.completionStatus = (1, self.etitle, str( fce ))

        except Exception, e:
            self.completionStatus = (1, self.etitle, str( e ))
         
        if isMounted:
            flasher.umount()


    # This function is run in a seperate thread, and therefore cannot update
    # the GUI directly.
    def _flashProcess( self, moeFileName, releaseFileName, package_info ):
        self._flash( moeFileName, releaseFileName, package_info )
        self.done = 1
        thread.exit()
                

class ExtractingDialog( ProcessingDialog ):
    def __init__( self, parent, releaseFileName, distFileName, package_info ):
        pkgName = package_info['package']
        self.etitle = 'Extraction Error'
        ProcessingDialog.__init__( self, parent,
                                   "Extracting " + pkgName,
                                   self._extractProcess,
                                   (releaseFileName, distFileName, pkgName) )

    def _extract( self, releaseFileName, distFileName, pkgName, uid ):
        pextract = find_tool( releaseFileName, 'pextract' )
        if not pextract:
            self.completionStatus = (1, self.etitle,
                                     "Unable to locate pextract tool.\n"
                                     "Check config options and try again.")
            return

        cmd = os.path.join( pextract, 'pextract' )
        if uid:
            cmd += " -u %d" % uid
        cmd += " -d %s %s %s" % (distFileName, releaseFileName, pkgName)
        child = Popen4( cmd )
        outfile = child.fromchild

        progress = 0
        self._set_progress( progress, "Creating distribution" )
        self._proc_message( "Executing %s\n" % cmd )
        
        try:
            while 1:
                result = select( [outfile], [], [] )
                if result[0]:
                    line = outfile.readline()
                    if line:
                        self._proc_message( line )
                        if progress < 95:
                            progress += 5
                        self._set_progress( progress, "Creating distribution" )
                    else:
                        self.completionStatus = (0, None, "Extraction complete.")
                        break
    
            self._set_progress( 100 )
            status = child.wait()
            if os.WIFEXITED( status ):
                exit_code = os.WEXITSTATUS( status )
                if exit_code:
                    self.completionStatus = (1, self.etitle, os.strerror( exit_code ))
            else:
                self.completionStatus = (1, self.etitle,
                                         "Extraction forcibly stopped, status = %d" % status)
        except KeyboardInterrupt:
            os.kill( child.pid, signal.SIGTERM )
            self._proc_message( "Extraction cancelled by user request.\n" )

    # This function is run in a seperate thread, and therefore cannot update
    # the GUI directly.
    def _extractProcess( self, releaseFileName, distFileName, pkgName ):
        try:
            # Switch to netinstall user if a netinstall user account exists.
            netinstall_uid = getUserInfo( 'netinstall', 2 )
            self._extract( releaseFileName, distFileName, pkgName, netinstall_uid )
            
        except Exception, e:
            self.completionStatus = (1, self.etitle, str( e ))
            
        self.done = 1
        thread.exit()
        

class TopMenu( Menu ):
    PKG_NAME_MODE = 0
    PKG_DESC_MODE = 1
    PKG_TOP_MODE  = 2
    PKG_ALL_MODE  = 3
    PKG_TEST_MODE = 4
    PKG_DEV_MODE  = 5
    PKG_GOLD_MODE = 6
    
    def __init__( self, application, parent, rel_mode ):
        Menu.__init__( self, parent )       
        parent.config( menu = self )
        self.application = application
        
        self.view_mode = IntVar()
        self.view_mode.set( TopMenu.PKG_DESC_MODE )
        
        self.rel_mode = IntVar()
        self._set_mode( rel_mode )
        
        self.top_mode = IntVar()
        self.top_mode.set( TopMenu.PKG_TOP_MODE )
        
        m = Menu( self, tearoff = 0 )
        m.add_command( label = 'Open MOE...', command = self.openMOE, underline = 5 )
        m.add_command( label = 'Open release...', command = self.openBuild, underline = 5 )
        m.add_separator()
        m.add_command( label = 'Open latest', command = self.openLatest, underline = 5 )
        m.add_separator()
        m.add_command( label = 'Initialize flash', command = self.application.flashit, underline = 0 )
        m.add_command( label = 'Make distribution', command = self.application.extractit, underline = 3 )
        m.add_separator()
        # OpenBuild() depends on the next entry being at menu index 8
        m.add_command( label = 'Promote release', command = self.application.promote, underline = 0 )
        # OpenBuild() depends on the next entry being at menu index 9
        m.add_command( label = 'Demote release', command = self.application.demote, underline = 0 )
        m.add_separator()
        m.add_command( label = 'Exit', command = parent.quit, underline = 1 )
        self.add_cascade( label = 'File', menu = m, underline = 0 )
        self.file_menu = m

        
        m = Menu( self, tearoff = 0 )
        m.add_radiobutton( label = "Test", variable = self.rel_mode, value = TopMenu.PKG_TEST_MODE,
                           command = self.openBuildAuto )
        m.add_radiobutton( label = "Development", variable = self.rel_mode, value = TopMenu.PKG_DEV_MODE,
                           command = self.openBuildAuto )
        m.add_radiobutton( label = "Gold", variable = self.rel_mode, value = TopMenu.PKG_GOLD_MODE,
                           command = self.openBuildAuto )
        self.add_cascade( label = 'Mode', menu = m, underline = 0 )

        m = Menu( self, tearoff = 0 )
        m.add_radiobutton( label = "Names", variable = self.view_mode, value = TopMenu.PKG_NAME_MODE,
                           command = application.refresh_listbox )
        m.add_radiobutton( label = "Descriptions", variable = self.view_mode, value = TopMenu.PKG_DESC_MODE,
                           command = application.refresh_listbox )
        m.add_separator()
        m.add_radiobutton( label = "All packages", variable = self.top_mode, value = TopMenu.PKG_ALL_MODE,
                           command = application.refresh_listbox )
        m.add_radiobutton( label = "Top-level packages", variable = self.top_mode, value = TopMenu.PKG_TOP_MODE,
                           command = application.refresh_listbox )
        m.add_separator()
        m.add_command( label = 'Log file', command = self.displayLog, underline = 0 )
        m.add_command( label = 'XML data', command = application.displayXML, underline = 0 )
        m.add_command( label = 'Options...', command = self.showOptions, underline = 0 )
        self.add_cascade( label = 'View', menu = m, underline = 0 )
        
        m = Menu( self, tearoff = 0 )
        m.add_command( label = "About %s" % _PROGRAM_NAME, command = self.about, underline = 5 )
        self.add_cascade( label = 'Help', menu = m, underline = 0 )

    def _set_mode( self, rel_mode = None ):
        if rel_mode == 'test':
            self.rel_mode.set( TopMenu.PKG_TEST_MODE )
        elif rel_mode == 'dev':
            self.rel_mode.set( TopMenu.PKG_DEV_MODE )
        elif rel_mode == 'gold':
            self.rel_mode.set( TopMenu.PKG_GOLD_MODE )
        else:
            self.rel_mode.set( 0 )
            
    def get_mode( self ):
        return self.rel_mode.get()
        
    def _cmp( self, a, b ):
        if a > b: return 1
        if a < b: return -1
        return 0
    
    ##
    # Compare file names of the form: basename-0.0.0.ext or basename-0.0.0-note.ext
    #
    def _compare_file_names( self, file1, file2 ):
        # Determine file format.
        ftuple1 = file1.split( '-' )
        ftuple2 = file2.split( '-' )
        
        # File names that are not one of the supported formats always go to the
        # bottom of the barrel.
        if len( ftuple1 ) < 2 or len( ftuple1 ) > 3:
            return -1
        if len( ftuple2 ) < 2 or len( ftuple2 ) > 3:
            return 1
        
        # Compare base names.
        if ftuple1[0] > ftuple2[0]:
            return 1
        if ftuple1[0] < ftuple2[0]:
            return -1
        
        # Base names are equal, so compare versions.
        vtuple1 = ftuple1[1].split( '.' )
        vtuple2 = ftuple2[1].split( '.' )
        
        # Version numbers that are not one of the supported formats always go to
        # the bottom of the barrel.
        if len( vtuple1 ) < 3:
            return -1
        if len( vtuple2 ) < 3:
            return 1
        for n in [0, 1, 2]:
            if not vtuple1[n].isdigit():
                return -1
            if not vtuple2[n].isdigit():
                return 1
            
        # Compare versions.
        for n in [0, 1, 2]:
            result = self._cmp( int( vtuple1[n] ), int( vtuple2[n] ) )
            if result != 0:
                return result
            
        # Versions are the same, so settle for regular compare.
        return self._cmp( file1, file2 )
    
    def _findLatestFile( self, dir, pattern ):
        files = glob( os.path.join( dir, pattern ) )
        if files:
            files.sort( self._compare_file_names )
            return os.path.split( files[ len( files ) - 1] )
        return None

    def openMOE( self, auto = 0 ):
        pattern = 'moe-*.tgz'
        inidir = _CONFIG_MAP[_MOE_DIR][1]
        inifile = None
        latest = self._findLatestFile( inidir, pattern )
        if latest:
            inidir = latest[0]
            inifile = latest[1]
            if auto:
                self.application.openMOE( os.path.join( inidir, inifile ) )
                return
        file = askopenfilename( parent = self.application,
                                title = "Open Mediator Operating Environment",
                                initialdir = inidir,
                                initialfile = inifile,
                                filetypes = [("MOE's", pattern)] )
        if file:
            self.application.openMOE( file )

    def openBuild( self, auto = 0 ):
        # Enable or disable the promote/demote menu items based on the release mode.
        self.file_menu.entryconfig( 8, state = DISABLED )
        self.file_menu.entryconfig( 9, state = DISABLED )
        if self.rel_mode.get() == TopMenu.PKG_TEST_MODE:
            self.file_menu.entryconfig( 8, state = NORMAL )
        elif self.rel_mode.get() == TopMenu.PKG_GOLD_MODE:
            self.file_menu.entryconfig( 9, state = NORMAL )

        pattern = 'release-*.tar'
        
        inidir = _CONFIG_MAP[_RELEASE_DIR][1]
        if self.get_mode() == TopMenu.PKG_DEV_MODE:
            inidir = _CONFIG_MAP[_DEVREL_DIR][1]
        elif self.get_mode() == TopMenu.PKG_GOLD_MODE:
            inidir = _CONFIG_MAP[_GOLDREL_DIR][1]
            
        file = None
        latest = self._findLatestFile( inidir, pattern )
        if latest:
            inidir = latest[0]
            file = latest[1]
            if auto:
                self.application.openBuild( os.path.join( inidir, file ) )
                return
            
        if auto:
            showwarning( 'Open release', 'No releases available in current mode.' )
        else:
            file = askopenfilename( parent = self.application,
                                    title = "Open Release",
                                    initialdir = inidir,
                                    initialfile = file,
                                    filetypes = [('Builds', pattern)] )
            if file:
                dir = os.path.realpath( os.path.split( file )[0] )
                if dir == os.path.realpath( _CONFIG_MAP[_RELEASE_DIR][1] ):
                    self._set_mode( 'test' )
                elif dir == os.path.realpath( _CONFIG_MAP[_DEVREL_DIR][1] ):
                    self._set_mode( 'dev' )
                elif dir == os.path.realpath( _CONFIG_MAP[_GOLDREL_DIR][1] ):
                    self._set_mode( 'gold' )
                else:
                    self._set_mode()
                
        self.application.openBuild( file )
            
    def openBuildAuto( self ):
        return self.openBuild( 1 )
    
    def openLatest( self ):
        self.openMOE( 1 )
        self.openBuild( 1 )
            
    def about( self ):
        # Strip extraneous text from the revision number.
        version = _PROGRAM_VER.replace( '$Revision: ', '' )[:-2]
        showinfo( "About %s" % _PROGRAM_NAME,
                  "      Version: %s\nHandcrafted with pride\n      in the U.S.A." % version )
        
    def displayLog( self ):
        top = Toplevel()
        top.geometry( "+%d+%d" % (self.application.winfo_rootx() + 50,
                                  self.application.winfo_rooty() + 50 ))
        top.title( 'Flash Log' )
        st = ScrolledText( top )
        st.displayText( _progress_log )

    def showOptions( self ):
        ConfigDialog( self.application )


class Application( Frame ):
    def __init__( self, root, mode ):
        Frame.__init__( self, root )
        self.root = root
        root.title( _PROGRAM_NAME )
        
        self.moeFileName = None
        self.releaseFileName = None
        self.xml_data = None
        self.package_db = []
        self.package_names = None
        self.release = None
        
        self.topMenu = TopMenu( self, root, mode )
        self.pack( expand = YES, fill = BOTH )
        
        frame = Frame( self, height = 100 )
        Label( frame, text = "Using MOE: " ).pack( side = LEFT )
        self.moe_entry = Entry( frame, bg = 'white' )
        self.moe_entry.pack( side = LEFT, expand = YES, fill = X )
        self.moe_entry.config( state = DISABLED )
        frame.pack( side = TOP, fill = X )

        frame = Frame( self )
        self.package_listbox_label = Label( frame, text = "" )
        self.package_listbox_label.pack( side = LEFT )
        frame.pack( side = TOP, fill = X )
        
        list = Listbox( self, relief = SUNKEN, bg = 'white' )
        sbar = Scrollbar( list )
        sbar.config( command = list.yview )
        list.config( yscrollcommand = sbar.set, selectmode = SINGLE )
        sbar.pack( side = RIGHT, anchor = E, expand = YES, fill = Y )
        list.pack( side = TOP, expand = YES, fill = BOTH )
        self.package_listbox = list
        
        self.exit_button = Button( self )
        self.exit_button["text"] = "Exit"
        self.exit_button["fg"]   = "red"
        self.exit_button["command"] =  self.quit
        self.exit_button.pack( side = RIGHT )

        self.flash_button = Button( self )
        self.flash_button["text"] = "Initialize Flash"
        self.flash_button["command"] =  self.flashit
        self.flash_button.pack( side = RIGHT )
        
        if os.path.isfile( _LOGO_FILE ):
            self.logo = PhotoImage( file = _LOGO_FILE )
            Label( self, image = self.logo ).pack( side = LEFT )

        # Wait for the main window to become visible before proceding, otherwise
        # we may experience geometry problems, i.e., the following dialogs may not
        # display where expected relative to the main window.
        self.wait_visibility()
        
        # We want validated configuration options or else we'll take our toys
        # and go home.
        global cfg_parser
        if cfg_parser.nParams == 0:
            showinfo( 'Configuration not found',
                      'You must confirm configuration information '
                      'before you can start using this program' )
            cd = ConfigDialog( self )
            cfg_parser = PDeplyTkConfigParser( _cfgFileName )

        # If there still isn't any configuration, the user canceled out of the
        # config dialog.
        if cfg_parser.nParams == 0:
            # Can't call quit() here because mainloop isn't running, yet.
            raise SystemExit
        # 
        # Must be root to run...  This is a bit scary, but the idea is pretty
        # simple.  The su command insists on stdin being a TTY (I don't know
        # why).  So we preform an os.forkpty() which returns the psuedo-TTY's
        # fd.  Now the wierd part:  The parent dups the psuedo-TTY's fd to
        # stdin, and then execs an su root -c "pdeploytktk args ...".  The
        # child write the password to stdout, which is now the parent's stdin.
        # Since the parent is running 'su', it validates the password and
        # then execs the -c command.  Simple...
        #
        if os.getuid() != 0:
            r = RootDialog( self )
            if r.exit_action == r.OK:
                pid, fd = os.forkpty()
                if pid:
                    self.destroy()
                    # Parent, execs with input from child.
                    os.dup2( fd, 0 ) # Now the PTY master fd is out STDIN
                    # Possible workaround for xlib connect error: argv = ['xhost +; ']
                    argv = []
                    argv.extend( sys.argv )
                    argv.append( '--config' )
                    argv.append( cfg_parser.filename )
                    args = ['su', 'root', '-c', string.join( argv )]
                    os.execvp( 'su', args )
                else:
                    # Child just outputs the password and then it's done.
                    sys.stdout.write( r.passwd.get() )
            raise SystemExit

        self.topMenu.openLatest()
        
    def openMOE( self, moeFileName ):
        self.moeFileName = os.path.realpath( moeFileName )
        self.moe_entry.config( state = NORMAL )
        self.moe_entry.delete( 0, END )
        self.moe_entry.insert( 0, os.path.split( self.moeFileName )[1] )
        self.moe_entry.config( state = DISABLED )
        
    def openBuild( self, releaseFileName ):
        if releaseFileName:
            # Pull the package database from the archive.
            self.releaseFileName = os.path.realpath( releaseFileName )
            self.xml_data = get_xml_data_from_archive( releaseFileName )
            self.release, self.package_db = get_package_db_from_xml( self.xml_data )
            
            self.root.title( "%s - %s" % (_PROGRAM_NAME, os.path.split( releaseFileName )[1]) )
        else:
            self.releaseFileName = None
            self.xml_data = None
            self.release = None
            self.package_db = []
            
            self.root.title( _PROGRAM_NAME )
            
        self.refresh_listbox()

    def _set_lb_color( self ):
        rel_mode = self.topMenu.get_mode()
        if rel_mode == TopMenu.PKG_TEST_MODE:
            color = _TEST_COLOR
        elif rel_mode == TopMenu.PKG_DEV_MODE:
            color = _DEV_COLOR
        elif rel_mode == TopMenu.PKG_GOLD_MODE:
            color = _GOLD_COLOR
        else:
            color = _DFLT_COLOR

        self.package_listbox.config( bg = color )
        
    def refresh_listbox( self ):
        tmode = self.topMenu.top_mode.get()
        if tmode == TopMenu.PKG_ALL_MODE:
            self.package_names = self.package_db.keys()
        elif tmode == TopMenu.PKG_TOP_MODE:
            dependents = []
            for pkey in self.package_db:
                for req in self.package_db[pkey]['dependencies']:
                    if not req in dependents:
                        dependents.append( req )
            self.package_names = []
            for pkey in self.package_db:
                if not pkey in dependents:
                    self.package_names.append( pkey )
        self.package_names.sort()

        item = '?'
        line = 0
        self.package_listbox.delete( 0, END )
        self._set_lb_color()
        for p in self.package_names:
            vmode = self.topMenu.view_mode.get()
            if  vmode == TopMenu.PKG_DESC_MODE:
                item = self.package_db[p]['description']
            elif vmode == TopMenu.PKG_NAME_MODE:
                item = p
            self.package_listbox.insert( line, item )
            line += 1
        
        if self.release:
            if tmode == TopMenu.PKG_TOP_MODE:
                intro = 'Top-level p'
            else:
                intro = 'P'
            self.package_listbox_label.config(
                text = "%sackages available in release %s:" % (intro, self.release) )
        else:
            self.package_listbox_label.config( text = "No packages available" )


    def flashit( self ):
        if self.moeFileName == None:
            showerror( 'Flash', 'No MOE is open.' )
            return
        
        if self.package_names == None:
            showerror( 'Flash', 'No release is open.' )
            return
        
        items = self.package_listbox.curselection()
        if items:
            try:
                index = int( items[0] )
            except ValueError:
                pass
            FlashingDialog( self,
                            self.moeFileName,
                            self.releaseFileName,
                            self.package_db[self.package_names[index]] )
        else:
            showwarning( 'Flash', 'No package selected.  Please select a package and try again.' )

    def displayXML( self ):
        if self.xml_data:
            top = Toplevel()
            top.geometry( "+%d+%d" % (self.root.winfo_rootx() + 50,
                                      self.root.winfo_rooty() + 50 ))
            top.title( 'XML data' )
            st = ScrolledText( top )
            st.displayText( self.xml_data )
        else:
            showerror( 'XML data', 'No release is open.')
            
    def _get_dist_file( self, pkg_name ):
        pattern = '*.tgz'
        inifile = '%s-%s.tgz' % (pkg_name, self.release )
        inidir = _CONFIG_MAP[_DISTRIB_DIR][1]
        file = asksaveasfilename( parent = self,
                                  title = "Make Distribution",
                                  initialdir = inidir,
                                  initialfile = inifile,
                                  filetypes = [('Distributions', pattern)] )
        return file
             
    def extractit( self ):
        if self.package_names == None:
            showerror( 'Make distribution', 'No release is open.' )
            return
        
        items = self.package_listbox.curselection()
        if items:
            try:
                index = int( items[0] )
            except ValueError:
                pass
            file = self._get_dist_file( self.package_names[index] )
            if file:
                ExtractingDialog( self,
                                  self.releaseFileName,
                                  file,
                                  self.package_db[self.package_names[index]] )
        else:
            showwarning( 'Make distribution',
                         'No package selected.  Please select a package and try again.' )

    def promote( self ):
        if self.package_names == None:
            showerror( 'Promote release', 'No release is open.' )
            return

        cmd = 'mv %s %s' % (self.releaseFileName, _CONFIG_MAP[_GOLDREL_DIR][1])
        errno = os.system( cmd )
        if errno:
            showerror( 'Promote release', 'Unable to promote, error code = %d' % errno )
        else:
            showinfo( 'Promote release', 'Release %s has been promoted to Golden' % self.release )
            # Refresh current mode.
            self.topMenu.openLatest()

    def demote( self ):
        if self.package_names == None:
            showerror( 'Demote release', 'No release is open.' )
            return

        cmd = 'mv %s %s' % (self.releaseFileName, _CONFIG_MAP[_RELEASE_DIR][1])
        errno = os.system( cmd )
        if errno:
            showerror( 'Demote release', 'Unable to demote, error code = %d' % errno )
        else:
            showinfo( 'Demote release', 'Release %s has been demoted to Test' % self.release )
            # Refresh current mode.
            self.topMenu.openLatest()

#####################################################################
#
# M A I N
#
#####################################################################

# Local constants.
_HELP_MSG = """The command format is:
  %s [--help | --config=<config-file> | --mode=<test|dev|gold>]
Where:
  --help displays this help message
  --config sets the file name for the configuration options file;
    the default is ./.pdeploytk.conf
  --mode sets the initial startup mode; the default is 'test'.
""" % _PROGRAM_NAME

_cfgFileName = None
_mode = 'test'

# Get the command line options.
try:
    _options, _args = getopt.getopt( sys.argv[1:], '',
                                     ['help', 'config=', 'mode='] )
    
except getopt.GetoptError, e:
    print e, ", use --help for help"
    sys.exit( 1 )

# Check to see if help was requested.
for opt in _options:
    if opt[0] == '--help':
        print _HELP_MSG
        sys.exit( 0 )
    elif opt[0] == '--config':
        _cfgFileName = opt[1]
    elif opt[0] == '--mode':
        _mode = opt[1]

if not _mode in ['test', 'dev', 'gold']:
    print "No such mode: ", _mode
    sys.exit( 1 )

root = Tk()
root.geometry( "500x300+200+200" )

app = Application( root, _mode )
app.mainloop()
