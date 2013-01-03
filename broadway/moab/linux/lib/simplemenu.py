"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import curses
import curses.ascii
import ConfigParser
import signal
import sys
import os
import zoneinfo


# TODO:
# 1.  Figure out why curses isn't more helpful.  See SimpleMenu.xlat_esq_seq().
# 2.  If 1 can't be avoided, then add terminal specific xlation tables.
# 3.  Enhance MessageBox to make it more useful for displaying error verbose error messages.
# 4.  Better error handling and more comments.
# 5.  Active clock in set date/time dialog.

#
# Module constants.
#
_DEFAULT_TIME_ZONE = 'current'
SIMPLEMENU_VERSION = "$Revision: 20101 $"      # Revision number assigned by CVS

#
# Text attributes.
#
ATTR_NORMAL = curses.A_NORMAL
ATTR_BLINK = curses.A_BLINK

#
# Module variables.
#
_is_simple_mode = 0    # Non-zero to enable simpler GUI
_is_debug = 0          # Non-zero to enable debug code


##############################################################################
#
# _set_cursor
#
# Wrapper function to set the cursor state.  Calls the equivalent curses
# function and swallows any exceptions.
#
# Input parameters:
#   mode    - visibility mode; can be set to 0, 1, or 2, for
#             invisible, normal, or very visible.  On many terminals,
#             the "visible" mode is an underline cursor and the
#             "very visible" mode is a block cursor.
#
##############################################################################
def _set_cursor( mode ):
    # If the terminal supports the visibility requested, the previous
    # cursor state is returned; otherwise, an exception is raised. 
    try:
        return curses.curs_set( mode )
    except:
        pass
    return 0


##############################################################################
#
# _set_date_time_action
#
# Set the system date, time, and time zone from control values.
#
# Input parameters:
#   args - (SimpleDateControl, SimpleTimeControl, SimpleDropDownListControl)
#
##############################################################################
def _set_date_time_action( args ):
    assert( len( args ) == 3 )
    zone_selection = args[2].get()
    if zone_selection == _DEFAULT_TIME_ZONE:
        zone_selection = None
    return zoneinfo.set_time( args[0].get(), args[1].get(), zone_selection )

 
##############################################################################
#
# SimpleMenuConfigParser class
#
# Class drived from the ConfigParser class defined in the standard Python
# library.  Used to read and write the configuration file.
#
##############################################################################
class SimpleMenuConfigParser( ConfigParser.ConfigParser ):
    
    filename = None
    
    ##############################################################################
    #
    # SimpleMenuConfigParser.__init__
    #
    # Read the configuration file.
    #
    # Input parameters:
    #    filename    - the name of the config file
    #    defaults    - dictionary of default options
    #
    ##############################################################################
    def __init__( self, filename, defaults=None ):
        if defaults is None:
            defaults={}
        ConfigParser.ConfigParser.__init__( self, defaults )
        self.filename = filename
        try:
            fp = open( filename, 'r' )
        except:
            # If the file doesn't exist, create it.
            fp = open( filename, 'w+' )
        self.readfp( fp )
        fp.close()
        return
    
    ##############################################################################
    #
    # SimpleMenuConfigParser.save
    #
    # Save the current configuration options in the config file.
    #
    ##############################################################################    
    def save( self ):
        fp = open( self.filename, 'w' )
        self.write( fp )
        fp.close()
        return


##############################################################################
#
# SimpleInputHandler class
#
# Base class to handle keyboard input and character translation.
#
##############################################################################
class SimpleInputHandler:
    # Common ESC mappings for PC keyboards and VT102 emulation.
    # I still don't know why CURSES/keypad doesn't handle this better...
    ESC_MAP = {
        '[1~'  : curses.KEY_HOME,
        '[2~'  : curses.KEY_IC,
        '[3~'  : curses.KEY_DC,
        '[4~'  : curses.KEY_END,
        '[5~'  : curses.KEY_PPAGE,
        '[6~'  : curses.KEY_NPAGE,
        '[16~' : curses.KEY_F5,
        '[17~' : curses.KEY_F6,
        '[18~' : curses.KEY_F7,
        '[19~' : curses.KEY_F8,
        '[20~' : curses.KEY_F9,
        '[21~' : curses.KEY_F10,
        '[23~' : curses.KEY_F11,
        '[24~' : curses.KEY_F12,
        '[A'   : curses.KEY_UP,
        '[B'   : curses.KEY_DOWN,
        '[C'   : curses.KEY_RIGHT,
        '[D'   : curses.KEY_LEFT
    }
    
    IS_ESC_XLATE_ON = 0         # Set to enable extended escape sequence translation
    
    # Additional controls for editing and cursor movement.  Some emulators have
    # problems with the function and arrow keys.
    KEY_CTL_B = 2               # Back one char (left-arrow)
    KEY_CTL_D = 4               # Delete one char (DEL)
    KEY_CTL_F = 6               # Forward one char (right arrow)
    KEY_CTL_J = 10              # Enter
    KEY_CTL_N = 14              # Next line (down arrow)
    KEY_CTL_P = 16              # Previous line (up arrow)
    
    ##############################################################################
    #
    # SimpleInputHandler.__init__
    #
    # Initialize the input handler.
    #
    # Input parameters:
    #    window      - the curses window that input will come from.
    #
    ##############################################################################
    def __init__( self, window ):
        self.window = window
        # Enable keypad mode to get special keys, such as the arrow keys.
        window.keypad( 1 )

    ##############################################################################
    #
    # SimpleInputHandler.debug_write
    #
    # Write a debug message to the window.  Derived classes are expected to do
    # something more useful with this if they want debug messages displayed.
    #
    # Input parameters:
    #    msg         - message to display.
    #
    ##############################################################################
    def debug_write( self, msg ):
        pass
    
    ##############################################################################
    #
    # SimpleInputHandler.xlat_esc_seq
    #
    # Translate common ESC sequences.  Time out to handle the lone ESC character
    # as well.
    #
    # Returns:
    #   The translated escape sequence, or ESC if translation was not performed.
    #
    ##############################################################################    
    def xlat_esc_seq( self ):
        if self.IS_ESC_XLATE_ON:
            def handler( signum, frame ):
                return
    
            esc_seq = ''
            try:
                old_handler = signal.signal( signal.SIGALRM, handler )
                signal.alarm( 1 )
                
                while 1:
                    ch = self.window.getch()
                    self.debug_write( "+0x%x" % ch )
                    esc_seq += chr( ch )
                    try:
                        # Quick escape!
                        ch = self.ESC_MAP[esc_seq]
                        signal.alarm( 0 )
                        signal.signal( signal.SIGALRM, old_handler )
                        return ch
                    except:
                        pass
            except:
                pass
    
            signal.alarm( 0 )
            signal.signal(signal.SIGALRM, old_handler)
            try:
                ch = self.ESC_MAP[esc_seq]
                # Return the key that represents the escape sequence.
                return ch
            except:
                pass
    
            # When confused, return ESC.
            self.debug_write('<' + esc_seq + '>')
            
        return curses.ascii.ESC
        
    ##############################################################################
    #
    # SimpleInputHandler.xlate_ch
    #
    # Translate an input character or escape sequence.
    #
    # Returns:
    #   The translated character.
    #
    ##############################################################################    
    def xlate_ch( self, ch ):
        if ch == curses.ascii.ESC:
            return self.xlat_esc_seq()
        elif ch == self.KEY_CTL_J:
            return curses.KEY_ENTER
        elif ch == curses.ascii.DEL or ch == self.KEY_CTL_D:
            return curses.KEY_DC
        elif ch == self.KEY_CTL_B:
            return curses.KEY_LEFT
        elif ch == self.KEY_CTL_F:
            return curses.KEY_RIGHT
        elif ch == curses.KEY_DOWN or ch == self.KEY_CTL_N:
            return curses.KEY_NEXT
        elif ch == curses.KEY_UP or ch == self.KEY_CTL_P:
            return curses.KEY_PREVIOUS
        return ch
    
    ##############################################################################
    #
    # SimpleInputHandler.getch
    #
    # Get one character of input from the associated window, performing any
    # required translations.
    #
    # Returns:
    #   The character.
    #
    ##############################################################################    
    def getch( self ):
        try:
            ch = self.window.getch()
        except KeyboardInterrupt:
            sys.exit( 0 )
            
        self.debug_write( "GOT:0x%x" % ch )
        ch = self.xlate_ch( ch )    
        self.debug_write( "RET:0x%x" % ch )
        return ch
           
 
##############################################################################
#
# SimpleField class
#
# Class to manage text fields.  Text is entered and edited within a field.
# A field has a fixed display width, but a scrolling-enabled field can hold
# text strings that are longer than the field width.
#
# TODO: right justification?
#
##############################################################################
class SimpleField:
    
    KEY_CTL_A = 1
    KEY_CTL_E = 5
    KEY_CTL_K = 11
    
    ##############################################################################
    #
    # SimpleField.__init__
    #
    # Initialize the field.
    #
    # Input parameters:
    #   parent_menu       - the menu which contains this field
    #   x_pos             - x-coordinate, relative to the parent menu's window
    #   y_pos             - y-coordinate, relative to the parent menu's window
    #   width             - field width
    #   name              - optional friendly name, used for error reporting
    #   validation_action - optional function to invoke to validate the field
    #   isScrollable      - true to enable scrolling; scrolling is disabled by
    #                       default.
    #
    ##############################################################################    
    def __init__( self, parent_menu, x_pos, y_pos, width,
                  name = "",
                  validation_action = None,
                  isScrollable = 0 ):
        self.parent = parent_menu
        self.window = parent_menu.window
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.width = width
        self.name = name
        if validation_action:
            assert callable( validation_action )
        self.validation_action = validation_action
        self.isScrollable = isScrollable
        self.text_list = []        # Character array for storing field contents
        self.iText = 0             # Cursor position within the field
        self.iStart = 0            # First character to be painted
        self.ifInsert = 0          # True if in insert mode
        self.isEntered = 0         # True if currently entered
    
    ##############################################################################
    #
    # SimpleField.__str__
    #
    # Returns:
    #   The current value of the field as a text string.
    #
    ##############################################################################
    def __str__( self ):
        text = ""
        for c in self.text_list:
            text += c
        return text
    
    ##############################################################################
    #
    # SimpleField.enter
    #
    # Method called when the field is entered.
    #
    # Input parameters:
    #   at_end       - true if the cursor should be positioned at the end of the
    #                  field; it is positioned at the beginning by default.
    #
    ##############################################################################    
    def enter( self, at_end = 0 ):
        if at_end:
            self.iText = len( self.text_list ) - 1
        else:
            self.iText = 0
        self.ifInsert = 0
        self.isEntered = 1
        self.paint()

    ##############################################################################
    #
    # SimpleField.exit
    #
    # Called to exit the field.  Validation, if any, is performed at this time.
    # If validation fails then a beep is emitted and the exit operation is not
    # completed (i.e., the field remains highlighted).
    #
    # Returns:
    #    1 if the field is valid, 0 otherwise.
    #
    ##############################################################################
    def exit( self ):
        if self.validation_action:
            if not self.validation_action( self.get() ):
                msg = "'%s' is not a valid value for " % self.get()
                if self.name:
                    msg += "field '%s'" % self.name
                else:
                    msg += "this field"
                curses.beep()
                self.parent.status_write( msg )
                return 0
        self.isEntered = 0
        self.paint()
        return 1

    ##############################################################################
    #
    # SimpleField.paint
    #
    # Called to display the field.  The field is highlighted if it is in the
    # entered state and the cursor is positioned over the current character.
    #
    ##############################################################################
    def paint( self ):
        # Adjust for scrolling if needed.
        if self.isScrollable:
            if self.iText < self.iStart:
                self.iStart = self.iText
            elif self.iText >= self.iStart + self.width:
                self.iStart = self.iText - self.width + 1
            
        # Select the appropiate text attribute.
        attr = curses.A_NORMAL
        if self.isEntered and not self.ifInsert and not _is_simple_mode:
            attr = curses.A_STANDOUT
            
        # Display the text
        x_pos = self.x_pos
        i = 0
        for c in self.text_list:
            if x_pos >= self.x_pos + self.width:
                break
            if i >= self.iStart:
                self.window.addch( self.y_pos, x_pos, ord( c ), attr )
                x_pos += 1
            i += 1

        # Pad with spaces if the field shrank since last painted.
        nPad = self.width - len( self.text_list ) + self.iStart
        while nPad > 0:
            self.window.addch(  self.y_pos, x_pos, ord( ' ' ) )
            x_pos += 1
            nPad -= 1
        
        # Position the cursor.
        x_cursor = self.x_pos + self.iText - self.iStart
        if x_cursor >= self.x_pos + self.width:
            x_cursor = self.x_pos + self.width - 1
        self.window.move( self.y_pos, x_cursor )
        _set_cursor( self.isEntered )

    ##############################################################################
    #
    # SimpleField.handlech
    #
    # Handle the input character and perform any necessary editing.  The field is
    # repainted if it's state changed.
    #
    # Input parameters:
    #   ch    - the input character
    #
    # Returns:
    #   None if the character was handled, i.e., it was a text or editing
    #   character.  The character is returned if the field couldn't handle it.
    #
    ##############################################################################
    def handlech( self, ch ):
        if ch == curses.KEY_RIGHT and self.iText < len( self.text_list ):
            self.iText += 1
        elif ch == curses.KEY_LEFT and self.iText > 0:
            self.iText -= 1
        elif ch == curses.KEY_IC:
            if self.ifInsert:
                self.ifInsert = 0
            else:
                self.ifInsert = 1
        elif ch == curses.KEY_DC:
            if self.iText < len( self.text_list ):
                self.text_list.pop( self.iText )
        elif ch == curses.KEY_BACKSPACE:
            if self.iText > 0:
                self.iText -= 1
            if len( self.text_list) > 0:
                self.text_list.pop( self.iText )
        elif ch == SimpleField.KEY_CTL_A:
            # Move cursor to beginning of field.
            self.iText = 0
        elif ch == SimpleField.KEY_CTL_E:
            # Move cursor to end of field.
            self.iText = len( self.text_list )
        elif ch == SimpleField.KEY_CTL_K:
            # Clear from cursor to end of field.
            while len( self.text_list ) > self.iText:
                self.text_list.pop( self.iText )
        elif curses.ascii.isprint( ch ):
            if self.ifInsert:
                if self.isScrollable or len( self.text_list ) < self.width:
                    self.text_list.insert( self.iText, chr( ch ) )
                    self.iText += 1
            else:
                if self.iText < len( self.text_list ):
                    self.text_list[self.iText] = chr( ch )
                    self.iText += 1
                elif self.isScrollable or len( self.text_list ) < self.width:
                    self.text_list.append( chr( ch ))
                    self.iText += 1
                else:
                    self.text_list[self.width - 1] = chr( ch )
        else:
            return ch

        self.paint()
        return None

    ##############################################################################
    #
    # SimpleField.get
    #
    # Return the value of the field.
    #
    # Returns:
    #   Field contents represented as a text string.
    #
    ##############################################################################
    def get( self ):
        return self.__str__()
    
    ##############################################################################
    #
    # SimpleField.set
    #
    # Set the value of the field.
    #
    # Input parameters:
    #   text   - string representing the new field value.
    #
    ##############################################################################
    def set( self, text ):
        self.text_list = []
        for c in text:
            self.text_list.append( c )
    
    ##############################################################################
    #
    # SimpleField.is_eof
    #
    # Test for end-of-field.
    #
    # Returns:
    #   1 if current character is at end-of-field, 0 otherwise.
    #
    ##############################################################################
    def is_eof( self ):
        return self.iText >= self.width
    
    ##############################################################################
    #
    # SimpleField.is_bof
    #
    # Test for beginning-of-field.
    #
    # Returns:
    #   1 if current character is at beginning-of-field, 0 otherwise.
    #
    ##############################################################################
    def is_bof( self ):
        return self.iText == 0


##############################################################################
#
# SimpleNumericField class
#
# A specialization of SimpleField that only allows the digits 0-9 to be
# entered.
#
##############################################################################
class SimpleNumericField( SimpleField ):
    
    ##############################################################################
    #
    # SimpleNumericField.__init__
    #
    # Initialize the field.
    #
    # Input parameters:
    #   parent_menu       - the menu which contains this field
    #   x_pos             - x-coordinate, relative to the parent menu's window
    #   y_pos             - y-coordinate, relative to the parent menu's window
    #   width             - field width
    #   name              - optional friendly name, used for error reporting
    #   validation_action - optional function to invoke to validate the field
    #   zeropad           - true if the field should be padded with zeroes; the
    #                       default is false.
    #   isScrollable      - true to enable scrolling; scrolling is disabled by
    #                       default.
    #
    ##############################################################################    
    def __init__( self, parent_menu, x_pos, y_pos, width,
                  name = "", validation_action = None, zeropad = 0, isScrollable = 0 ):
        SimpleField.__init__( self, parent_menu, x_pos, y_pos, width,
                              name, validation_action, isScrollable )
        self.zeropad = zeropad
    
    ##############################################################################
    #
    # SimpleNumericField.handlech
    #
    # Handle the input character and perform any necessary editing.  Only the
    # the digits 0-9 are accepted, other values are ignored. The field is
    # repainted if it's state changed.
    #
    # Input parameters:
    #   ch    - the input character
    #
    # Returns:
    #   None if the character was handled, i.e., it was a digit or editing
    #   character.  The input character is returned if the field couldn't handle
    #   it.
    #
    ##############################################################################
    def handlech( self, ch ):
        if curses.ascii.isprint( ch ) and not curses.ascii.isdigit( ch ):
            curses.beep()
            return None
        return SimpleField.handlech( self, ch )

    ##############################################################################
    #
    # SimpleNumericField.get
    #
    # Return the value of the field.
    #
    # Returns:
    #   Integer value of the field.
    #
    ##############################################################################
    def get( self ):
        value = 0
        if len( self.text_list ):
            text = ""
            for c in self.text_list:
                text += c
            value = int( text )
        return value
    
    ##############################################################################
    #
    # SimpleNumericField.set
    #
    # Set the value of the field.
    #
    # Input parameters:
    #   n   - an integer representing the new field value.
    #
    ##############################################################################
    def set( self, n ):
        # Must be an integer
        assert( type( n ) == type( 0 ) )
        
        if not self.zeropad:
            SimpleField.set( self, "%d" % n )
        else:
            SimpleField.set( self, "%0*d" % ( self.width, n ) )
    

##############################################################################
#
# SimpleMenuItem class
#
# Base class to represent an item displayed on the menu.
#
##############################################################################
class SimpleMenuItem:

    ##############################################################################
    #
    # SimpleMenuItem.__init__
    #
    # Initalize a menu item.
    #
    # Input parameters:
    #    parent   - parent menu
    #    x_pos    - x coordinate
    #    y_pos    - y coordinate
    #    label    - label
    #
    ##############################################################################
    def __init__( self, parent, x_pos, y_pos, label ):
        self.parent = parent
        self.window = parent.window
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.label = label
        self.isEntered = 0
        self.active_attr = curses.A_BOLD
        self.attr = self.inactive_attr = curses.A_NORMAL
        
    ##############################################################################
    #
    # SimpleMenuItem.enter
    #
    # Called when an item is entered.  Change the text attribute to indicate that
    # the item is selected.
    #
    ##############################################################################
    def enter( self ):
        self.isEntered = 1
        self.attr = self.active_attr
        self.paint( 0 )
        
    ##############################################################################
    #
    # SimpleMenuItem.exit
    #
    # Called when an item is exitted.  Restore the normal text attribute.
    #
    # Returns:
    #   1 if the exit was successful, 0 otherwise.
    #
    ##############################################################################
    def exit( self ):
        self.isEntered = 0
        self.attr = self.inactive_attr
        self.paint( 0 )
        return 1
        
    ##############################################################################
    #
    # SimpleMenuItem.paint
    #
    # Repaint this menu item.
    #
    # Input paramters:
    #    isFirstTime - true if this is the first time the item is being painted;
    #                  the default is false.  Some items may need to do special
    #                  initialization the first time they are displayed.
    #
    ##############################################################################
    def paint( self, isFirstTime = 0 ):
        if self.label:
            self.window.addstr( self.y_pos, self.x_pos, self.label, self.attr )
        
    ##############################################################################
    #
    # SimpleMenuItem.commit
    #
    # Called when a menu is accepted.
    #
    ##############################################################################
    def commit( self ):
        pass
        
    ##############################################################################
    #
    # SimpleMenuItem.cancel
    #
    # Called when a menu is cancelled.
    #
    ##############################################################################
    def cancel( self ):
        pass
        
    ##############################################################################
    #
    # SimpleMenuItem.handlech
    #
    # Handle an input character.
    #
    # Returns:
    #   None if the character was handled, otherwise return the input character.
    #
    ##############################################################################
    def handlech( self, ch ):
        return ch

    ##############################################################################
    #
    # SimpleMenuItem.status_write
    #
    # Write a message to the parent menu's status line.
    #
    # Input parameters:
    #   msg   - message to write
    #   attr  - text attribute for message
    #
    ##############################################################################
    def status_write( self, msg = '', attr = ATTR_NORMAL ):
        self.parent.status_write( msg, attr )

    ##############################################################################
    #
    # SimpleMenuItem.debug_write
    #
    # Write a debug message to the parent menu's debug line.
    #
    # Input parameters:
    #   msg   - message to write
    #
    ##############################################################################
    def debug_write( self, msg ):
        self.parent.debug_write( msg )


##############################################################################
#
# SimpleMenuButton class
#
# A specialization of SimpleMenuItem that represents a push button displayed
# on a menu.
#
##############################################################################
class SimpleMenuButton( SimpleMenuItem ):  

    ##############################################################################
    #
    # SimpleMenuButton.__init__
    #
    # Initalize the button.
    #
    # Input parameters:
    #    parent   - parent menu
    #    x_pos    - x coordinate
    #    y_pos    - y coordinate
    #    label    - label
    #    shortcut - a "shortcut" key to be associated with the button
    #    action   - a function to be executed when the button is activated
    #    args     - arguments to be passed to the action function
    #
    ##############################################################################
    def __init__( self, parent, x_pos, y_pos, label, shortcut, action, *args ):
        SimpleMenuItem.__init__( self, parent, x_pos, y_pos, label )
        
        self.action = action
        self.args = args
        self.shortcut = shortcut
        
        if not _is_simple_mode:
            self.attr = self.inactive_attr = self.active_attr \
                      = curses.A_REVERSE | curses.A_BOLD
    
    ##############################################################################
    #
    # SimpleMenuButton.handlech
    #
    # Handle an input character.  Runs the button action if the character is the
    # ENTER key, otherwise does nothing.
    #
    # Input parameters:
    #    ch     - the input character
    #
    # Returns:
    #    None if action was run, otherwise the input character is returned.
    #
    ##############################################################################
    def handlech( self, ch ):
        if ch == curses.KEY_ENTER:
            self.run()
            return None
        return ch
    
    ##############################################################################
    #
    # SimpleMenuButton.is_shortcut
    #
    # Test a character to see if it's the button's shortcut.
    #
    # Input parameters:
    #    ch     - the input character
    #
    # Returns:
    #    1 if the button is the shortcut, 0 otherwise.
    #
    ##############################################################################
    def is_shortcut( self, test_key ):
        return test_key == self.shortcut

    ##############################################################################
    #
    # SimpleMenuButton.run
    #
    # Run the action associated with the button.
    #
    # Returns:
    #    The result of the action.
    #
    ##############################################################################
    def run( self ):
        return apply( self.action, self.args )


##############################################################################
#
# SimpleConfigItem class
#
# A mix-in class used to associate a menu item with an option stored in a
# configuration file.
#
##############################################################################
class SimpleConfigItem:

    ##############################################################################
    #
    # SimpleConfigItem.__init__
    #
    # Initalize the configuration item.
    #
    # Input parameters:
    #   config_parser  - configuration file parser
    #   section        - name of the section this item's option is found in
    #   option         - the name of the option
    #   default_value  - default value for the item if the option isn't found
    #
    ##############################################################################
    def __init__( self, config_parser, section, option, default_value = "" ):
        self.config_parser = config_parser
        self.section = section
        self.option = option
        
        # Don't set the default until after we have the real saved value.
        self.default_value = ""
        self.saved_value = self.read_value()
        self.default_value = default_value
        
        # Set the current value to the saved one, or the default if none saved.
        if self.saved_value:
            self.current_value = self.saved_value
        else:
            self.current_value = self.default_value
    
    ##############################################################################
    #
    # SimpleConfigItem.read_value
    #
    # Read the item's option value from the configuration file.
    #
    # Returns:
    #    The configuration option's value, or the item's default value if the
    #    option was missing.
    #
    ##############################################################################
    def read_value( self ):
        if self.config_parser:
            if self.config_parser.has_option( self.section, self.option ):
                return self.config_parser.get( self.section, self.option )
        return self.default_value
        
    ##############################################################################
    #
    # SimpleConfigItem.save
    #
    # Save the item's current value in the configuration file.
    #
    ##############################################################################
    def save( self ):
        if self.config_parser:# and self.is_changed(): #need to ensure all attrs present
            if not self.config_parser.has_section( self.section ):
                self.config_parser.add_section( self.section )
            self.config_parser.set( self.section, self.option, self.current_value )
            self.saved_value = self.current_value
        
    ##############################################################################
    #
    # SimpleConfigItem.revert
    #
    # Restore the item's value back to the last saved one.
    #
    ##############################################################################
    def revert( self ):
        self.current_value = self.saved_value
        
    ##############################################################################
    #
    # SimpleConfigItem.get_value
    #
    # Returns:
    #    The item's current value.
    #
    ##############################################################################
    def get_value( self ):
        return self.current_value
        
    ##############################################################################
    #
    # SimpleConfigItem.set_value
    #
    # Set the item's current value.
    #
    # Input parameters:
    #   value  - the new value for the item
    #
    ##############################################################################
    def set_value( self, value ):
        self.current_value = value
        
    ##############################################################################
    #
    # SimpleConfigItem.is_changed
    #
    # Returns:
    #    1 if the item's value has changed since it was last saved, 0 otherwise.
    #
    ##############################################################################
    def is_changed( self ):
        return self.current_value != self.saved_value


##############################################################################
#
# SimpleCycleMenu class
#
# A control that presents sets the value of a field based on a small number
# of possible choices.  The user makes a choice by pressing the space bar to
# cycle through the possible values.  The value is stored in a configuration
# file.
#
##############################################################################
class SimpleCycleMenu( SimpleMenuItem, SimpleConfigItem ):

    ##############################################################################
    #
    # SimpleCycleMenu.__init__
    #
    # Initalize the cycle menu.  The parent menu is expected to have a
    # config_parser attribute.
    #
    # Input parameters:
    #   parent     - parent menu, from which a window and config parser is obtained
    #   x_pos      - x-coordinate relative to the parent menu's window
    #   y_pos      - y-coordinate relative to the parent menu's window
    #   label      - text label to prefix the field with
    #   cycle_list - the list of choices
    #   section    - name of the section this item's option is found in
    #   option     - the name of the option
    #
    ##############################################################################
    def __init__( self, parent, x_pos, y_pos, label, cycle_list, section, option ):
        self.cycle_list = cycle_list
        self.iChoice = 0
        SimpleMenuItem.__init__( self, parent, x_pos, y_pos, label )
        SimpleConfigItem.__init__( self, parent.config_parser, section, option,
                                   self.cycle_list[self.iChoice] )

        # Set maxLength to the length of the longest value in the value list.
        self.maxLength = 0
        for item in cycle_list:
            if len( item ) > self.maxLength:
                self.maxLength = len( item )
               
        self.load_value()

    ##############################################################################
    #
    # SimpleCycleMenu.load_value
    #
    # Set the displayed value to the current value.
    #
    ##############################################################################
    def load_value( self ):
        for item in self.cycle_list:
             if item == self.get_value():
                self.iChoice = self.cycle_list.index( item )
        
    ##############################################################################
    #
    # SimpleCycleMenu.commit
    #
    # Commit this menu item, i.e., save the current value in the config file.
    #
    ##############################################################################
    def commit( self ):
        SimpleConfigItem.save( self )

    ##############################################################################
    #
    # SimpleCycleMenu.cancel
    #
    # Cancel this menu item, i.e., reset the value to the last saved value.
    #
    ##############################################################################
    def cancel( self ):
        SimpleConfigItem.revert( self )
        self.load_value()

    ##############################################################################
    #
    # SimpleCycleMenu.enter
    #
    # Enter this menu item.  Repaint the item and turn off the cursor.
    #
    ##############################################################################
    def enter( self ):
        SimpleMenuItem.enter( self )
        _set_cursor( 0 )
        
    ##############################################################################
    #
    # SimpleCycleMenu.paint
    #
    # Repaint this menu item.
    # TODO: should limit the size of the display to stay inside the window.
    #
    # Input paramters:
    #    isFirstTime - true if this is the first time the item is being painted;
    #                  the default is false.  Ignored by this method.
    #
    ##############################################################################
    def paint( self, isFirstTime = 0 ):
        # Paint the label
        SimpleMenuItem.paint( self )
        
        # Display current choice
        attr = curses.A_UNDERLINE
        if self.isEntered and not _is_simple_mode:
            attr |= curses.A_STANDOUT
        self.window.addstr( self.y_pos, self.x_pos + len( self.label ),
                            self.cycle_list[self.iChoice], attr )
        
        # Pad with blanks if current choice is shorter than than the max.
        nPad = self.maxLength - len( self.cycle_list[self.iChoice] )
        while nPad > 0:
            self.window.addch( ord( ' ' ) )
            nPad -= 1
        
    ##############################################################################
    #
    # SimpleCycleMenu.handlech
    #
    # Handle an input character.  Display the next choice if the space bar is
    # pressed, otherwise an error message if the input is not valid.
    #
    # Input parameters:
    #    ch     - the input character
    #
    # Returns:
    #    None if the input was handled, otherwise the input character is returned.
    #
    ##############################################################################
    def handlech( self, ch ):
        if ch == curses.ascii.SP:
            self.iChoice = ( self.iChoice + 1 ) % len( self.cycle_list )
            self.paint( 0 )
            return None
        elif not self.parent.is_navigation( ch ):
            self.status_write( "Use space bar to select a value" )
            return None
        return SimpleMenuItem.handlech( self, ch )

    ##############################################################################
    #
    # exit
    #
    # Called to exit the item.  Set the item's value to the current selection
    # and proceed with normal item exit.
    #
    # Returns 1 if the exit was successful, 0 otherwise.
    #
    ##############################################################################
    def exit( self ):
        self.set_value( self.cycle_list[self.iChoice] )
        return SimpleMenuItem.exit( self )


##############################################################################
#
# SimpleTextMenu class
#
# A control that sets the value of a field based text typed in by the user.
# The value is stored in a configuration file.
#
##############################################################################
class SimpleTextMenu( SimpleMenuItem, SimpleConfigItem ):
    
    ##############################################################################
    #
    # SimpleTextMenu.__init__
    #
    # Initalize the cycle menu.  The parent menu is expected to have a
    # config_parser attribute.
    #
    # Input parameters:
    #   parent     - parent menu, from which a window and config parser is obtained
    #   x_pos      - x-coordinate relative to the parent menu's window
    #   y_pos      - y-coordinate relative to the parent menu's window
    #   label      - text label to prefix the field with
    #   section    - name of the section this item's option is found in
    #   option     - the name of the option
    #   vfcn       - validation function used to test the field value
    #
    ##############################################################################
    def __init__( self, parent, x_pos, y_pos, label, section, option, vfcn ):
        SimpleMenuItem.__init__( self, parent, x_pos, y_pos, label )
        SimpleConfigItem.__init__( self, parent.config_parser, section, option )
        
        # Calculate the width of the field.  It will extend from the label to the rightmost
        # position within the containing window, minus a small margin.
        maxyx = parent.window.getmaxyx()
        fwidth = maxyx[1] - x_pos - len( label ) - 3
        assert fwidth > 0
        
        self.text_field = SimpleField( self, x_pos + len( label ), y_pos, fwidth,
                                       validation_action = vfcn, isScrollable = 1 )
        self.load_value()
    
    ##############################################################################
    #
    # SimpleCycleMenu.load_value
    #
    # Set the displayed value to the current value.
    #
    ##############################################################################
    def load_value( self ):
        self.text_field.set( self.get_value() )
    
    ##############################################################################
    #
    # SimpleTextMenu.commit
    #
    # Commit this menu item, i.e., save the current value in the config file.
    #
    ##############################################################################
    def commit( self ):
        SimpleConfigItem.save( self )

    ##############################################################################
    #
    # SimpleTextMenu.cancel
    #
    # Cancel this menu item, i.e., reset the value to the last saved value.
    #
    ##############################################################################
    def cancel( self ):
        SimpleConfigItem.revert( self )
        self.load_value()
    
    ##############################################################################
    #
    # SimpleTextMenu.enter
    #
    # Called when the item is entered.  Updates the display of the label and the
    # text field.
    #
    ##############################################################################
    def enter( self ):
        self.text_field.enter()
        SimpleMenuItem.enter( self )
    
    ##############################################################################
    #
    # SimpleTextMenu.exit
    #
    # Called to exit the item.  Set the item's value to the text entered and
    # proceed with normal item exit.
    #
    # Returns 1 if the exit was successful, 0 otherwise.
    #
    ##############################################################################
    def exit( self ):
        self.set_value( self.text_field.get() )
        if self.text_field.exit():
            return SimpleMenuItem.exit( self )
        return 0

    ##############################################################################
    #
    # SimpleTextMenu.paint
    #
    # Repaint this menu item.
    #
    # Input paramters:
    #    isFirstTime - true if this is the first time the item is being painted;
    #                  the default is false.  Ignored by this method.
    #
    ##############################################################################
    def paint( self, isFirstTime = 0 ):
        SimpleMenuItem.paint( self )
        self.text_field.paint()
        return
    
    ##############################################################################
    #
    # SimpleTextMenu.handlech
    #
    # Handle an input character.
    #
    # Input parameters:
    #    ch     - the input character
    #
    # Returns:
    #    None if the input was handled, otherwise the input character is returned.
    #
    ##############################################################################
    def handlech( self, ch ):
        if self.text_field.handlech( ch ):
            # The field rejects the left and right arrow keys if the cursor
            # would be moved outside the field, so swallow those keys here.
            if ch != curses.KEY_RIGHT and ch != curses.KEY_LEFT:
                return SimpleMenuItem.handlech( self, ch )
        return None
    

##############################################################################
#
# SimpleDropDownListControl class
#
# A control that presents the user with an arbitrarily long list of choices.
# The control looks like a CycleMenuControl, but when the space bar is
# pressed a list box is displayed from which the user makes a selection.
#
##############################################################################
class SimpleDropDownListControl( SimpleMenuItem ):
    
    ##############################################################################
    #
    # SimpleDropDownListControl.__init__
    #
    # Initalize the list control.
    #
    # Input parameters:
    #   parent       - parent menu, from which a window is obtained
    #   x_pos        - x-coordinate relative to the parent menu's window
    #   y_pos        - y-coordinate relative to the parent menu's window
    #   label        - text label to prefix the field with
    #   intial_value - initial value to display in the field
    #   list_source  - callable object that returns a list of items to display
    #   lines        - the number of lines in the list
    #   cols         - the number of columns in the list
    #
    ##############################################################################
    def __init__( self, parent, x_pos, y_pos, label, intial_value, list_source, lines, cols ):
        SimpleMenuItem.__init__ ( self, parent, x_pos, y_pos, label )
        self.value = self.initial_value = intial_value
        assert callable( list_source )
        self.list_source = list_source
        self.list = []
        self.iSelection = 0
        
        self.listwin = None
        self.listxy = ( self.x_pos + len( self.label ) + 1, self.y_pos + 2 )
        
        self.maxLength = 0
        self.nLines = lines
        self.nCols = cols
        self.blank_line = ' ' * self.nCols
        if _is_simple_mode:
            self.hline = '-'
        else:
            self.hline = curses.ACS_HLINE
                                 
    ##############################################################################
    #
    # SimpleDropDownListControl._box
    #
    # Draw a box around the list.
    #
    ##############################################################################
    def _box( self ):
        if _is_simple_mode:
            self.listwin.border( '|', '|', '-', '-', '+', '+', '+', '+' )
        else:
            self.listwin.box()

    ##############################################################################
    #
    # SimpleDropDownListControl.paint
    #
    # Repaint this menu item.
    #
    # Input paramters:
    #    isFirstTime - true if this is the first time the item is being painted;
    #                  the default is false.
    #
    ##############################################################################
    def paint( self, isFirstTime = 0 ):
        if isFirstTime:
            self.value = self.initial_value
            
        # Paint the label
        SimpleMenuItem.paint( self )
        
        # Display the current value.
        value_len = 0
        if self.value:
            attr = curses.A_UNDERLINE
            if self.isEntered:
                attr |= curses.A_STANDOUT
            self.window.addstr( self.y_pos, self.x_pos + len( self.label ),
                                self.value, attr )
            value_len = len( self.value )
        
        # Pad the field with blanks if it has shrunk.
        nPad = self.maxLength - value_len
        while nPad > 0:
            self.window.addch( ord( ' ' ) )
            nPad -= 1
        self.maxLength = value_len
   
    ##############################################################################
    #
    # SimpleDropDownListControl.enter
    #
    # Enter this menu item.  Repaint the item and turn off the cursor.
    #
    ##############################################################################
    def enter( self ):
        SimpleMenuItem.enter( self )
        _set_cursor( 0 )

    ##############################################################################
    #
    # SimpleDropDownListControl._scroll
    #
    # Scroll the list box (couldn't get curses scroll regions to work).
    #
    # Input parameters:
    #   nLines  - the number of lines to scroll.  A positive number scrolls up,
    #             and a negative number scrolls down.
    #
    ##############################################################################
    def _scroll( self, nLines ):
        if nLines > 0 and nLines <= self.nLines - 3:
            dest = 1
            for source in range( nLines + 1, self.nLines - 1 ):
                str = self.listwin.instr( source, 1 )
                self.listwin.addnstr( dest, 1, str, self.nCols - 2 )
                dest += 1
        elif nLines < 0:
            dest = self.nLines - 2
            for source in range( self.nLines + nLines - 2, 0, -1 ):
                str = self.listwin.instr( source, 1 )
                self.listwin.addnstr( dest, 1, str, self.nCols - 2 )
                dest -= 1
        self.listwin.addnstr( dest, 1, self.blank_line, self.nCols - 2 )
    
    ##############################################################################
    #
    # SimpleDropDownListControl._display_list
    #
    # Displays the current contents of the list starting with the item indicated
    # by self.first_displayed.
    #
    # Returns:
    #   The number of items in the list.
    #
    ##############################################################################
    def _display_list( self ):
        self.listwin.erase()
        self._box()
        self.isMoreUp = self.isMoreDown = 0
        
        iList = self.first_displayed
        for line in range( 1, self.nLines - 1 ):
            attr = curses.A_NORMAL
            if iList == self.iSelection:
                attr = curses.A_REVERSE
            self.listwin.addnstr( line, 1, self.list[iList], self.nCols - 2, attr )
            iList += 1
            if iList >= len( self.list ):
                break
        return iList - self.first_displayed
    
    ##############################################################################
    #
    # SimpleDropDownListControl._run_list
    #
    # Displays the current contents of the list starting with the item indicated
    # by self.first_displayed.
    #
    # Returns:
    #   The value selected from the list.
    #
    ##############################################################################
    def _run_list( self ):
        # Populate the list box.
        selection = None
        self.list = self.list_source()
        if len( self.list ) == 0:
            return selection
            
        # Create the window if this is the first time the list box was run.
        if self.listwin == None:
            # newwin([nlines, ncols,] begin_y, begin_x)
            self.listwin = curses.newwin( self.nLines, self.nCols, self.listxy[1], self.listxy[0] )

        self.iSelection = self.first_displayed = 0
        self.last_displayed = self.first_displayed + self._display_list() - 1

        self.listwin.keypad( 1 )
        _set_cursor( 0 )
        
        #
        # Loop until ENTER or ESC is pressed.
        #
        isActive = 1
        self.isMoreUp = self.isMoreDown = 0
        
        while isActive:
            # Update list indicators. Flags prevent unneccessary painting.
            if self.first_displayed > 0:
                if not self.isMoreUp:
                    self.listwin.addstr( 0, self.nCols - 5, '[+]', curses.A_REVERSE )
                    self.isMoreUp = 1
            elif self.isMoreUp:
                self.listwin.hline( 0, self.nCols - 5, self.hline, 3 )
                self.isMoreUp = 0
            if self.last_displayed < len( self.list ) - 1:
                if not self.isMoreDown:
                    self.listwin.addstr( self.nLines - 1, self.nCols - 5, '[+]', curses.A_REVERSE )
                    self.isMoreDown = 1
            elif self.isMoreDown:
                self.listwin.hline( self.nLines - 1, self.nCols - 5, self.hline, 3 )
                self.isMoreDown = 0

            ch = self.parent.xlate_ch( self.listwin.getch() )
            
            if ch == curses.ascii.ESC:
                 selection = self.value
                 isActive = 0
            elif ch == curses.KEY_ENTER:
                selection = self.list[self.iSelection]
                isActive = 0
            elif ch == curses.KEY_NEXT or ch == curses.ascii.SP:
                if self.iSelection < len( self.list ) - 1:
                    line = self.iSelection - self.first_displayed + 1
                    self.listwin.addnstr( line, 1, self.list[self.iSelection],
                                          self.nCols - 2, curses.A_NORMAL )
                    self.iSelection += 1
                    if self.iSelection <= self.last_displayed:
                        self.listwin.addnstr( line + 1, 1, self.list[self.iSelection],
                                              self.nCols - 2, curses.A_REVERSE )
                    else:
                        self._scroll( 1 )  # curses scroll doesn't work?
                        self.first_displayed += 1
                        self.last_displayed += 1
                        self.listwin.addnstr( line, 1, self.list[self.iSelection],
                                              self.nCols - 2, curses.A_REVERSE )
            elif ch == curses.KEY_PREVIOUS:
                if self.iSelection > 0:
                    line = self.iSelection - self.first_displayed + 1
                    self.listwin.addnstr( line, 1, self.list[self.iSelection],
                                          self.nCols - 2, curses.A_NORMAL )
                    self.iSelection -= 1
                    if self.iSelection >= self.first_displayed:
                        self.listwin.addnstr( line - 1, 1, self.list[self.iSelection],
                                              self.nCols - 2, curses.A_REVERSE )
                    else:
                        self._scroll( -1 )  # curses scroll doesn't work?
                        self.first_displayed -= 1
                        self.last_displayed -= 1
                        self.listwin.addnstr( line, 1, self.list[self.iSelection],
                                              self.nCols - 2, curses.A_REVERSE )
            elif ch == curses.KEY_RIGHT:
                # NEXT PAGE
                remaining = len( self.list ) - 1 - self.last_displayed
                if remaining > 0:
                    page_size = self.nLines - 2
                    if remaining > page_size:
                        self.first_displayed = self.last_displayed + 1
                    else:
                        self.first_displayed = len( self.list ) - self.nLines + 2
                    
                    self.iSelection = self.first_displayed
                    self.last_displayed = self.first_displayed + self._display_list() - 1
            elif ch == curses.KEY_LEFT:
                # PREVIOUS PAGE
                preceding = self.first_displayed
                if preceding > 0:
                    page_size = self.nLines - 2
                    if preceding > page_size:
                        self.first_displayed -= page_size
                    else:
                        self.first_displayed = 0
                    
                    self.last_displayed = self.first_displayed + page_size - 1
                    self.iSelection = self.first_displayed
                    self._display_list()
            elif curses.ascii.isprint( ch ):
                # Search for and select the first list entry starting with the specified character.
                for i in range( 0, len( self.list ) ):
                    entry = self.list[i]
                    if entry[0] == chr( ch ):
                        if i < self.first_displayed:
                            self.first_displayed = self.iSelection = i
                            self.last_displayed = self.first_displayed + self._display_list() - 1
                        elif i > self.last_displayed:
                            self.iSelection = i
                            if len( self.list ) - i >= self.nLines - 2:
                                self.first_displayed = i
                            else:
                                self.first_displayed = len( self.list ) - self.nLines + 2
                            self.last_displayed = self.first_displayed + self._display_list() - 1
                        else:
                            line = self.iSelection - self.first_displayed + 1
                            self.listwin.addnstr( line, 1, self.list[self.iSelection],
                                                  self.nCols - 2, curses.A_NORMAL )
                            self.iSelection = i
                            line = i - self.first_displayed + 1
                            self.listwin.addnstr( line, 1, entry,
                                                  self.nCols - 2, curses.A_REVERSE )
                        break
        else:
            # Refresh the menu stack.
            self.parent.refresh()
            curses.doupdate()
            
        return selection
    
    ##############################################################################
    #
    # SimpleDropDownListControl.get
    #
    # Returns:
    #    The item's current value.
    #
    ##############################################################################
    def get( self ):
        return self.value

    ##############################################################################
    #
    # SimpleDropDownListControl.commit
    #
    # Commit this menu item, i.e., set the new initial value to the current value.
    #
    ##############################################################################
    def commit( self ):
        self.initial_value = self.value
    
    ##############################################################################
    #
    # SimpleDropDownListControl.cancel
    #
    # Cancel this menu item, i.e., restore the current value to the initial value.
    #
    ##############################################################################
    def cancel( self ):
        self.value = self.initial_value
    
    ##############################################################################
    #
    # SimpleDropDownListControl.handlech
    #
    # Handle an input character.  If the space bar is pressed then run the list
    # box.
    #
    # Input parameters:
    #    ch     - the input character
    #
    # Returns:
    #    None if the input was handled, otherwise the input character is returned.
    #
    ##############################################################################
    def handlech( self, ch ):
        if ch == curses.ascii.SP:
            self.value = self._run_list()
            self.paint( 0 )
            return None
        elif not self.parent.is_navigation( ch ):
            self.status_write( "Use space bar to select a value" )
            return None
        return SimpleMenuItem.handlech( self, ch )


##############################################################################
#
# SimpleMultiFieldControl class
#
# A control that manages a group of related fields, all displayed in the
# same row and separated by a specifed seperator character.
#
##############################################################################
class SimpleMultiFieldControl( SimpleMenuItem ):

    ##############################################################################
    #
    # SimpleMultiFieldControl.__init__
    #
    # Initalize the control.
    #
    # Input parameters:
    #   parent       - parent menu, from which a window is obtained
    #   x_pos        - x-coordinate relative to the parent menu's window
    #   y_pos        - y-coordinate relative to the parent menu's window
    #   label        - text label to prefix the field group with
    #   seperator    - seperator character
    #
    ##############################################################################
    def __init__( self, parent, x_pos, y_pos, label, field_list, seperator ):
        SimpleMenuItem.__init__ ( self, parent, x_pos, y_pos, label )
        self.seperator_ch = ord( seperator )
        self.field_list = field_list
        self.iField = 0 

    ##############################################################################
    #
    # SimpleMultiFieldControl.__str__
    #
    # Returns:
    #   The current value of the control as a text string.
    #
    ##############################################################################
    def __str__( self ):
        text = ""
        for f in self.field_list:
            text = text + str( f )
            if self.field_list.index( f ) < len( self.field_list ) - 1:
                text = text + chr( self.seperator_ch )
        return text


    ##############################################################################
    #
    # SimpleMultiFieldControl.enter
    #
    # Called to enter the field group, which implies entering the first field in
    # the group.
    #
    ##############################################################################
    def enter( self ):
        # Repaint the label
        SimpleMenuItem.enter( self )
        
        self.iField = 0
        self.field_list[0].enter()
      
    ##############################################################################
    #
    # SimpleMultiFieldControl.exit
    #
    # Called to exit the item.  Exit from the current field and proceed with
    # normal item exit.
    #
    # Returns 1 if the exit was successful, 0 otherwise.
    #
    ##############################################################################
    def exit( self ):
        if self.field_list[self.iField].exit():
            return SimpleMenuItem.exit( self )
        return 0
      
    ##############################################################################
    #
    # SimpleMultiFieldControl.paint
    #
    # Called to paint the field group.
    #
    ##############################################################################
    def paint( self, isFirstTime = 0 ):
        # Repaint the label
        SimpleMenuItem.paint( self, isFirstTime )
        
        # Repaint each field, with a separator after all but the last field.
        for i in range( len( self.field_list ) ):
            self.field_list[i].paint()
            if i < len( self.field_list ) - 1:
                self.window.addch( self.y_pos,
                                   self.field_list[i].x_pos + self.field_list[i].width,
                                   self.seperator_ch )
                
    ##############################################################################
    #
    # SimpleMultiFieldControl.get
    #
    # Returns:
    #   The current value of the control as a tuple of values, one for each field.
    #
    ##############################################################################
    def get( self ):
        result = ()
        for field in self.field_list:
            result = result + ( field.get(), )
        return result
    
    ##############################################################################
    #
    # SimpleMultiFieldControl._next_field
    #
    # Exit the current field and enter another in the group.
    #
    # Input parameters:
    #   delta  - specified the next field to enter, as a delta from the current
    #            field; positive to move foward to the beginning of a field,
    #            negetaive to move backwards to the end of a field.
    #
    # Returns 1 if the operation was successful, 0 if the current field cannot
    # be exitted due to validation failure.
    #
    ##############################################################################
    def _next_field( self, delta = 1 ):
        if self.field_list[self.iField].exit():
            self.iField = ( self.iField + delta ) % len( self.field_list )
            at_end = 0
            if delta < 0:
                at_end = 1
            self.field_list[self.iField].enter( at_end )
            return 1
        return 0
    
    ##############################################################################
    #
    # SimpleMultiFieldControl.handlech
    #
    # Handle an input character and perform any necessary navigation between
    # fields in the group.
    #
    # Input parameters:
    #    ch     - the input character
    #
    # Returns:
    #    None if the input was handled, otherwise the input character is returned.
    #
    ##############################################################################
    def handlech( self, ch ):
        if ch == curses.ascii.TAB:
            # Next field, with wrap.
            self._next_field()
        elif ch == self.seperator_ch:
            # Handle the seperator if not positioned at the last field.
            if self.iField < len( self.field_list ) - 1:
                # Unless it would leave the current field empry, clear the field from the
                # cursor forward and proceed to the next field.
                if not self.field_list[self.iField].is_bof():
                    self.field_list[self.iField].handlech( SimpleField.KEY_CTL_K )
                    self._next_field()
        else:
            # Let the field try to handle the char.
            if self.field_list[self.iField].handlech( ch ):
                # The field rejects the left and right arrow keys if the cursor
                # would be moved outside the field, so handle those keys here.
                if ch == curses.KEY_RIGHT:
                    self._next_field()
                elif ch == curses.KEY_LEFT:
                    self._next_field( -1 )
                else:
                    return SimpleMenuItem.handlech( self, ch )
            elif self.field_list[self.iField].is_eof():
                # The field accepted the char.  Automatically jump to the next field
                # if the current one is full.
                self._next_field()
        return None



##############################################################################
#
# SimpleDateControl class
#
# A specialization of SimpleMultiFieldControl to manage the three numeric
# fields that comprise a date.
#
##############################################################################
class SimpleDateControl( SimpleMultiFieldControl ):

    def __init__( self, parent, x_pos, y_pos, label ):
        # Create fields for month, day, and year.
        mmddyyyy = []
        
        field_x_pos = x_pos + len( label )
        mmddyyyy.append( SimpleNumericField( parent, field_x_pos, y_pos, 2,
                                             zeropad = 1,
                                             name = 'month',
                                             validation_action = lambda m: m >= 1 and m <= 12 ) )
        mmddyyyy.append( SimpleNumericField( parent, field_x_pos + 3, y_pos, 2,
                                             zeropad = 1,
                                             name = 'day',
                                             validation_action = lambda d: d >= 1 and d <= 31 ) )
        mmddyyyy.append( SimpleNumericField( parent, field_x_pos + 6, y_pos, 4,
                                             name = 'year',
                                             validation_action = lambda y: y >= 1970 ) )
        for n in range( 3 ) : mmddyyyy[n].set( 0 )
        
        SimpleMultiFieldControl.__init__ ( self, parent, x_pos, y_pos, label, mmddyyyy, '/' )        

    def paint( self, isFirstTime = 0 ):
        # If this is the first time the field is being painted then get the current date.
        if isFirstTime:
            t = zoneinfo.get_time()
            self.field_list[0].set( t[0] )  # month
            self.field_list[1].set( t[1] )  # day
            self.field_list[2].set( t[2] )  # year
        
        SimpleMultiFieldControl.paint( self, isFirstTime )


##############################################################################
#
# SimpleTimeControl class
#
# A specialization of SimpleMultiFieldControl to manage the three numeric
# fields that comprise the time.
#
##############################################################################
class SimpleTimeControl( SimpleMultiFieldControl ):

    def __init__( self, parent, x_pos, y_pos, label ):
        # Create fields for month, day, and year.
        field_names = ['hours', 'minutes', 'seconds' ]
        hhmmss = []
        
        field_x_pos = x_pos + len( label )
        for n in range( len( field_names ) ):
            hhmmss.append( SimpleNumericField( parent, field_x_pos, y_pos, 2,
                                               zeropad = 1,
                                               name = field_names[n],
                                               validation_action = lambda v: v >= 0 and v <= 59 ) )
            hhmmss[n].set( 0 )
            field_x_pos += 3
            
        self.zone_x_pos = field_x_pos + 3
        
        SimpleMultiFieldControl.__init__ ( self, parent, x_pos, y_pos, label, hhmmss, ':' )

    def paint( self, isFirstTime = 0 ):
        # If this is the first time the field is being painted then get the current time.
        t = zoneinfo.get_time()
        if isFirstTime:
            self.field_list[0].set( t[3] )  # hours
            self.field_list[1].set( t[4] )  # minutes
            self.field_list[2].set( t[5] )  # seconds
        
        SimpleMultiFieldControl.paint( self, isFirstTime )
        self.window.addstr( self.y_pos, self.zone_x_pos, t[6] )


##############################################################################
#
# SimpleIpAddressControl class
#
# A specialization of SimpleMultiFieldControl to manage the four numeric
# fields that comprise an IP address.
#
##############################################################################
class SimpleIpAddressControl( SimpleMultiFieldControl ):

    def __init__( self, parent, x_pos, y_pos, label, text_value = None ):
        
        # Default initial value
        if ( text_value == None ):
            text_value = "0.0.0.0"
        
        addr_fields = text_value.split( '.' )
        assert( len( addr_fields ) == 4 )
        
        # Intialize address
        address = []
        
        field_x_pos = x_pos + len( label )
        for n in range( 4 ):
            address.append( SimpleNumericField( parent, field_x_pos, y_pos, 3 ) )
            address[n].set( int( addr_fields[n] ) )
            field_x_pos += 4
            
        SimpleMultiFieldControl.__init__ ( self, parent, x_pos, y_pos, label, address, '.' )        


##############################################################################
#
# SimpleIpConfigItem class
#
# A specialization of SimpleMultiFieldControl to manage the four numeric
# fields that comprise an IP address.  The value of the item is stored in a
# configuration file.
#
##############################################################################
class SimpleIpConfigItem( SimpleIpAddressControl, SimpleConfigItem ):

    ##############################################################################
    #
    # SimpleIpConfigItem.__init__
    #
    # Initalize the menu item.  The parent menu is expected to have a
    # config_parser attribute.
    #
    # Input parameters:
    #   parent     - parent menu, from which a window and config parser is obtained
    #   x_pos      - x-coordinate relative to the parent menu's window
    #   y_pos      - y-coordinate relative to the parent menu's window
    #   label      - text label to prefix the field with
    #   section    - name of the section this item's option is found in
    #   option     - the name of the option
    #
    ##############################################################################
    def __init__( self, parent, x_pos, y_pos, label, section, option ):
        SimpleIpAddressControl.__init__ ( self, parent, x_pos, y_pos, label )        
        SimpleConfigItem.__init__( self, parent.config_parser, section, option )
        self.load_value()

    ##############################################################################
    #
    # SimpleIpConfigItem.load_value
    #
    # Set the displayed value to the current value.
    #
    ##############################################################################
    def load_value( self ):
        # Split aaa.bbb.ccc.ddd into fields
        addr_fields = self.get_value().split( '.' )

        i = 0       
        for f in addr_fields:
            if f.isdigit():
                self.field_list[i].set( int( f ) )
            i += 1
            if i > len( self.field_list ) - 1:
                break
    
    ##############################################################################
    #
    # SimpleIpConfigItem.commit
    #
    # Commit this menu item, i.e., save the current value in the config file.
    #
    ##############################################################################
    def commit( self ):
        SimpleConfigItem.save( self )

    ##############################################################################
    #
    # SimpleIpConfigItem.cancel
    #
    # Cancel this menu item, i.e., reset the value to the last saved value.
    #
    ##############################################################################
    def cancel( self ):
        SimpleConfigItem.revert( self )
        self.load_value()
    
    ##############################################################################
    #
    # SimpleIpConfigItem.exit
    #
    # Called to exit the item.  Set the item's value to the current IP address
    # and proceed with normal item exit.
    #
    # Returns 1 if the exit was successful, 0 otherwise.
    #
    ##############################################################################
    def exit( self ):
        self.set_value( "%d.%d.%d.%d" % ( self.field_list[0].get(),
                                          self.field_list[1].get(),
                                          self.field_list[2].get(),
                                          self.field_list[3].get() ) )
        return SimpleMultiFieldControl.exit( self )

    
##############################################################################
#
# SimpleActionControl class
#
# A control that represents an action to be executed at a later time.
# TODO: is this class really needed?
#
##############################################################################
class SimpleActionControl:

    ##############################################################################
    #
    # SimpleActionControl.__init__
    #
    # Initialize the control.
    #
    # Input parameters:
    #   action   - a callable object to assiciate with this action
    #   args     - the argumentss to be passed to the called object.
    #
    ##############################################################################
    def __init__( self, action, *args ):
        assert callable( action )
        self.action = action
        self.args = args

    ##############################################################################
    #
    # SimpleActionControl.execute
    #
    # Execute the action associated with the control.
    #
    # Returns:
    #    The result of the action.
    #
    ##############################################################################
    def execute( self ):
        return self.action( self.args )


##############################################################################
#
# SimpleMenuNavigator class
#
# Base class that performs navigation from one menu item to another based on
# user input.  Input translation is inherited from SimpleInputHandler.
#
# All menus contain a title in the top border, a single-line preamble at the
# top of the menu, and a row at the bottom of the menu for status messages.
# Optionally, menus may contain function keys.
#
##############################################################################
class SimpleMenuNavigator( SimpleInputHandler ):
    TITLE_ROW = 0               # Menu title starts here
    TITLE_COLUMN = 2            # ...
    HEADING_ROW = 2             # Preamble starts here
    HEADING_COLUMN = 2          # ...
    FIRST_ITEM_ROW = 4          # Menu items start here
    ITEM_COLUMN = 4             # ...
    STATUS_COLUMN = 2           # Status messages, debug msgs, and fcn keys start here
    
    ##############################################################################
    #
    # SimpleMenuNavigator.__init__
    #
    # Initialize the menu handler.
    #
    # Input parameters:
    #   window   - curses window that the menu lives in
    #   title    - title for the menu, placed within the top border.
    #
    ##############################################################################
    def __init__( self, window, title ):
        SimpleInputHandler.__init__( self, window )
        self.debug_xpos = self.STATUS_COLUMN
        self.last_status_len = 0
        self.fcn_key_list = []
        self.menu_list = []
        self.i_menu = 0
        self.title = title
        
        self._box( self.title )

    ##############################################################################
    #
    # SimpleMenuNavigator.add_fcn_key
    #
    # Add a function key to the menu handler.  All function keys are lined up in
    # one row near the bottom of the menu.
    #
    # Input parameters:
    #   label     - label for the function key
    #   action    - function to execute when the key is pressed.
    #
    ##############################################################################
    def add_fcn_key( self, label, action ):
        # Calculate the new key's x-coordinate.
        nkeys = len( self.fcn_key_list )
        if nkeys > 0:
            prev_key = self.fcn_key_list[nkeys - 1]
            next_x_pos = prev_key.x_pos + len( prev_key.label ) + 3
        else:
            next_x_pos = 2
 
        # Create the function key 3 rows from the bottom of the window and add it to
        # the key list.
        fcn_key_row = self.window.getmaxyx()[0] - 3
        shortcut = curses.KEY_F1 + nkeys
        key = SimpleMenuButton( self, next_x_pos, fcn_key_row, label, shortcut, action, self )
        self.fcn_key_list.append( key )
        
        # In simple mode function keys are part of the navigation sequence to account for
        # crappy terminal emulators with broken function keys.
        if _is_simple_mode:
            self.menu_list.append( key )
        
        return key

    ##############################################################################
    #
    # SimpleMenuNavigator._box
    #
    # Draw a box around the menu.
    #
    ##############################################################################
    def _box( self, title ):
        # Create a box with a title. Do some padding to make the display prettier.
        if _is_simple_mode:
            self.window.border( '|', '|', '=', '-', '+', '+', '+', '+' )
            self.window.addstr( self.TITLE_ROW, self.TITLE_COLUMN, '[ ' + title + ' ]',
                                curses.A_BOLD )
        else:
            self.window.box()
            self.window.addstr( self.TITLE_ROW, self.TITLE_COLUMN, ' ' + title + ' ',
                                curses.A_REVERSE )

    ##############################################################################
    #
    # SimpleMenuNavigator.deactivate
    #
    # Halt menu processing.
    #
    ##############################################################################
    def deactivate( self ):
        self.active = 0
    
    ##############################################################################
    #
    # SimpleMenuNavigator.status_write
    #
    # Display a message in the menu's status line.  New messages overwrite old
    # ones.
    #
    # Input parameters:
    #   str    - message to display, '' to erase the line.
    #   attr   - character attrubute for string.
    #
    ##############################################################################
    def status_write( self, str = '', attr = ATTR_NORMAL ):
        w = self.window
        saved_cursor = w.getyx()
        maxyx = w.getmaxyx()
        status_row = maxyx[0] - 2
        status_eol = maxyx[1] - 2
        status_len = len( str )
        if status_len > 0:
            if status_len + self.STATUS_COLUMN > status_eol:
                status_len = status_eol - self.STATUS_COLUMN
            w.addnstr( status_row, self.STATUS_COLUMN, str, status_len, attr )
        while status_len < self.last_status_len:
            sp = curses.ascii.SP
            w.addch( status_row, self.STATUS_COLUMN + status_len, sp, attr )
            status_len += 1
        self.last_status_len = status_len
        w.move( saved_cursor[0], saved_cursor[1] )
        w.refresh()
    
    ##############################################################################
    #
    # SimpleMenuNavigator.debug_write
    #
    # Display a message in the menu's debug line.  New messages are appended to
    # previous ones, separated by a highlighted '*'.  The messages wrap when the
    # end of the line is eached.
    #
    # Input parameters:
    #   str    - message to display.
    #
    ##############################################################################
    def debug_write( self, str ):
        if _is_debug:
            w = self.window
            maxyx = w.getmaxyx()
            debug_row = maxyx[0] - 1
            debug_eol = maxyx[1] - 3
            istr = 0
            while istr < len( str ):
                w.addch( debug_row, self.debug_xpos, str[istr] )
                istr += 1
                self.debug_xpos += 1
                if self.debug_xpos >= debug_eol:
                    self.debug_xpos = self.STATUS_COLUMN
            w.addstr( debug_row, self.debug_xpos, '*', curses.A_REVERSE )
            w.refresh()
    
    ##############################################################################
    #
    # SimpleMenuNavigator.run
    #
    # Display the menu and perform the common navigation functions.
    #
    ##############################################################################
    def run( self ):       
        # Expect at least one munu item.
        assert len( self.menu_list ) != 0
         
        # Paint the list of menu selections.
        for menu_item in self.menu_list:
            menu_item.paint( 1 )
        
        # Paint the functions keys
        for fcn_key in self.fcn_key_list:
            fcn_key.paint( 1 )
            
        # Enter the first selection.
        self.i_menu = 0
        menu_item = self.menu_list[self.i_menu]
        menu_item.enter()
                   
        # Process input until the menu is deactivated.
        self.active = 1
        while self.active:
            self.window.refresh()
            
            ch = self.getch()
            self.status_write()   # Clear stale messages from the status line
            
            ch = self.handlech( ch )
            if ch == None: continue
            
            ch = menu_item.handlech( ch )
            if ch == None: continue

            if ch == curses.KEY_NEXT or ch == curses.ascii.TAB:
                if menu_item.exit():
                    self.i_menu = (self.i_menu + 1) % len( self.menu_list )
                    menu_item = self.menu_list[self.i_menu]
                    menu_item.enter()
            elif ch == curses.KEY_PREVIOUS:
                if menu_item.exit():
                    self.i_menu = (self.i_menu - 1) % len( self.menu_list )
                    menu_item = self.menu_list[self.i_menu]
                    menu_item.enter()
            else:
                self.status_write( "Use the UP/DOWN arrow keys to select an item " )

    ##############################################################################
    #
    # SimpleMenuNavigator.is_navigation
    #
    # Utility function to test if a character is a navigation character, i.e., one
    # that is used to navigate from one menu item to another.
    #
    # Input parameters:
    #   ch  - character to test
    #
    # Returns:
    #   1 if the character is a navigation character, 0 otherwise.
    #
    ##############################################################################
    def is_navigation( self, ch ):
        if ch == curses.KEY_NEXT or \
           ch == curses.ascii.TAB or \
           ch == curses.KEY_PREVIOUS or \
           ch == curses.KEY_ENTER or \
           ch == curses.ascii.ESC:
            return 1
        return 0

    ##############################################################################
    #
    # SimpleMenuNavigator.handlech
    #
    # Handle an input character.  If the character is associated with a function
    # key then execute the key's action.
    #
    # Input parameters:
    #   ch     - the input character
    #
    # Returns:
    #   None if the input matched a function key, otherwise the input character
    #   is returned.
    #
    ##############################################################################
    def handlech( self, ch ):
        for key in self.fcn_key_list:
            # Is the char associated with this function key?
            if key.is_shortcut( ch ):
                key.run()
                return None
            # Is this function key the currently selected menu item?
            # This may be the case if running in simple mode.
            if key is self.menu_list[self.i_menu]:
                return key.handlech( ch )

        return ch

    def get_next_row( self ):
        return len( self.menu_list ) + self.FIRST_ITEM_ROW
    
    def get_next_col( self ):
        return self.ITEM_COLUMN
    
    def refresh( self ):
        self.window.redrawwin()
        self.window.noutrefresh()


##############################################################################
#
# SimpleOptionsMenu class
#
# A specialization of SimpleMenuNavigator that manages a list of menu items
# that may have values stored in a configuraton file.
#
# All menus contain a title in the top border, a single-line preamble at the
# top of the menu, and a row at the bottom of the menu for status messages.
# Optionally, menus may contain function keys.
#
##############################################################################
class SimpleOptionsMenu( SimpleMenuNavigator ):
    
    ##############################################################################
    #
    # SimpleOptionsMenu.__init__
    #
    # Parse the configuration file, if any, and initialize the menu handler.
    #
    ##############################################################################
    def __init__( self, parent, window, title, config_parser ):
        SimpleMenuNavigator.__init__( self, window, title )
        self.parent = parent
        self.config_parser = config_parser
        self.changes = 0
        self.action_list = []
        # fixme: allow more than one sub menu
        self.submenu = None
        
        window.addstr( self.HEADING_ROW, self.HEADING_COLUMN,
                       "Press ENTER if OK, ESC to cancel" )
    
    def add_control( self, ctl ):
        self.menu_list.append( ctl )
        return ctl
        
    def add_action_control( self, ctl ):
        self.action_list.append( ctl )
        return ctl
        
    def add_text_option( self, label, section_name, opt_name, validation_action = None ):
        option = SimpleTextMenu( self, self.get_next_col(), self.get_next_row(),
                                 label, section_name, opt_name, validation_action )
        self.menu_list.append( option )
        return option
    
    def add_ip_option( self, label, section_name, opt_name ):
        option = SimpleIpConfigItem( self, self.get_next_col(), self.get_next_row(),
                                     label, section_name, opt_name )
        self.menu_list.append( option )
        return option
    
    def add_pick_option( self, label, choice_list, section_name, opt_name ):
        option = SimpleCycleMenu( self, self.get_next_col(), self.get_next_row(),
                                  label, choice_list, section_name, opt_name )
        self.menu_list.append( option )
        return option
    
    def add_datetime_control( self ):
        zone_ctl = self.add_control( SimpleDropDownListControl( self,
                                                                self.get_next_col(), self.get_next_row(),
                                                                'Time zone        : ',
                                                                _DEFAULT_TIME_ZONE,
                                                                zoneinfo.get_time_zones, 18, 34 ) )
        date_ctl = self.add_control( SimpleDateControl( self,
                                                        self.get_next_col(), self.get_next_row(),
                                                        'Date (mm/dd/yyyy): ' ) )
        time_ctl = self.add_control( SimpleTimeControl( self,
                                                        self.get_next_col(), self.get_next_row(),
                                                        'Time (hh:mm:ss)  : ' ) )
        self.add_action_control( SimpleActionControl( _set_date_time_action, date_ctl, time_ctl, zone_ctl ) )
    
    def is_changed( self ):
        return self.changes > 0
    
    def handlech( self, ch ):
        if SimpleMenuNavigator.handlech( self, ch ) == None:
            return None
        
        if ch == curses.KEY_ENTER:
            # Exit from the current item.  The menu remains active if the
            # current item is not valid.
            if not self.menu_list[self.i_menu].exit():
                return 0
            
            # Commit all items.
            for option in self.menu_list:
                # Count configuration items that have changed.
                if hasattr( option, 'is_changed' ) and option.is_changed():
                    self.changes += 1
                option.commit()
                
            # Check submenu
            if self.submenu and self.submenu.is_changed():
                self.changes += 1
                
            # Execute any action items.  The menu remains active if any action raises
            # an exception.
            try:
                for act in self.action_list:
                    act.execute()
            except EnvironmentError, e:
                msg = "Error: "
                if e.strerror: msg += e.strerror + ": "
                self.status_write( msg )
            except zoneinfo.ESystemFailure, e:
                self.status_write( "%s" % e )
            else:
                self.active = 0
            return None
        elif ch == curses.ascii.ESC:
            self.menu_list[self.i_menu].exit()
            for option in self.menu_list:
                option.cancel()
            self.active = 0
            return None
        return ch
    
    def refresh( self ):
        self.parent.refresh()
        self.window.redrawwin()
        self.window.noutrefresh()

    def create_submenu( self, lines, cols, label ):
        yx = self.window.getbegyx()
        sub_window = curses.newwin( lines, cols, yx[0] + 2, yx[1] + 2 )
        self.submenu = SimpleOptionsMenu( self, sub_window, label, self.config_parser )
        return self.submenu
    
    def run_submenu( self, submenu ):
        submenu.run()
        submenu.window.erase()
        self.refresh()
        curses.doupdate()

        
    ##############################################################################
    #
    # SimpleOptionsMenu.run
    #
    ##############################################################################
    def run( self ):
        SimpleMenuNavigator.run( self )


##############################################################################
#
# SimpleMessageBox class
#
# A really brain-dead implementation of message boxes just to get the ball
# rolling. This class inherits input translation from SimpleInputHandler.
# TODO: derive from SimpleMenuNavigator so push buttons can be easily added.
#
##############################################################################
class SimpleMessageBox( SimpleInputHandler ):
    
    MB_ANY_CHAR = 0
    MB_OK = 1
    MB_OK_CANCEL = 2
    
    ##############################################################################
    #
    # SimpleMessageBox.__init__
    #
    # Initialize the message box.  The width and height of the message box
    # is determined by the message to be displayed.
    #
    # Input parameters:
    #    w           - the curses window of the parent dialog
    #    title       - title for the message box
    #    message     - message to display, with lines separated by \n. No line
    #                  should exceed 60 characters.
    #    type        - type of message box; MB_ANY_CHAR, MB_OK, MB_OK_CANCEL.
    #
    ##############################################################################
    def __init__( self, w, title, message, type = MB_ANY_CHAR ):
        self.type = type
        self.parentwin = w
        
        # Width is the length of the longest line of the message, including the title,
        # plus room for margins and borders.
        self.width = len( title ) + 2
        lines = message.splitlines()
        for line in lines:
            if len(line ) > self.width:
                self.width = len( line )
        assert( self.width <= 60 )
        self.width += 4
        
        # Height is the number of lines plus room for the title, margins, and borders.
        self.height = len( lines ) + 5
            
        # Create a new window for the message box, located at fixed y and x coordinates.
        # TODO: calculate a window position relative to the parent window.
        SimpleInputHandler.__init__( self,
                                     curses.newwin( self.height, self.width, 5, 15 ) )

        # Draw the box and title.
        self._box( title )

        # Put the message in the window.
        y_pos = 3
        for line in lines:
            self.window.addstr( y_pos, 2, line )
            y_pos += 1
        
 
    ##############################################################################
    #
    # SimpleMessageBox.run
    #
    # Get a single character of user input, as appropriate for the type of message 
    # box.  Beep if the input is invalid, otherwise dismiss the message box.
    #
    # Returns:
    #    The character entered by the user.
    #
    ##############################################################################
    def run( self ):
        
        # Loop until we have a valid character.
        ch = None
        while 1:
            ch = self.getch()
            if self.type == SimpleMessageBox.MB_ANY_CHAR:
                break
            elif self.type == SimpleMessageBox.MB_OK:
                if ch == curses.KEY_ENTER:
                    break
            elif self.type == SimpleMessageBox.MB_OK_CANCEL:
                if ch == curses.KEY_ENTER or ch == curses.ascii.ESC:
                    break
            else:
                curses.beep()
        
        # Dismiss the message box and return the character.
        self.window.erase()
        self.parentwin.redrawwin()
        self.parentwin.refresh()
        return ch
    
    ##############################################################################
    #
    # SimpleMessageBox._box
    #
    # Draw a box around the message box and add the title.
    #
    ##############################################################################
    def _box( self, title ):
        # Create a box with a title.
        if _is_simple_mode:
            self.window.border( '[', ']', '=', '=', '[', ']', '[', ']' )
        else:
            self.window.box()
         
        # Center the title.
        centered_title = title.center( self.width - 4 ).rstrip()
        self.window.addstr( 2, 2, centered_title, curses.A_BOLD )
    

##############################################################################
#
# SimpleMenuSelection class
#
# Specialization of a SimpleMenuItem, representing a top-level menu selection.
# A top-level menu selection invokes a sub-menu when it is activated by
# pressing the ENTER key.  This class contains methods used to define the
# associated sub-menu, which is an SimpleOptionsMenu object.
#
##############################################################################
class SimpleMenuSelection( SimpleMenuItem ):

    SUBMENU_LINES = 15
    SUBMENU_COLS = 50
    SUBMENU_XPOS = 2
    SUBMENU_YPOS = 2
    
    def __init__( self, parent, x_pos, y_pos, label ):
        SimpleMenuItem.__init__( self, parent, x_pos, y_pos, label )
        
        # Ugly coupling...
        self.config_parser = parent.config_parser
        
        self.option_window = curses.newwin( self.SUBMENU_LINES, self.SUBMENU_COLS,
                                            self.SUBMENU_YPOS, self.SUBMENU_XPOS )
        self.option_menu = SimpleOptionsMenu( parent, self.option_window, label, self.config_parser)
        
    def get_submenu( self ):
        return self.option_menu
           
    def enter( self ):
        SimpleMenuItem.enter( self )
        _set_cursor( 0 )

    def is_changed( self ):
       return self.option_menu.is_changed()
    
    def handlech( self, ch ):
        if ch == curses.KEY_ENTER:
            self.option_window.redrawwin()
            self.option_menu.run()
            _set_cursor( 0 )
            self.window.redrawwin()
            self.window.refresh()
            return None
        
        return SimpleMenuItem.handlech( self, ch )


##############################################################################
#
# SimpleMainMenu class
#
# Specialization of a SimpleMenuNavigator, representing a top-level menu.
# A top-level menu is, primarily, a list of SimpleMenuSelection objects.
# It also performs application-specific pre- and post-processing.
# TODO: to make this module more general purpose, this class should be
# defined somewhere else, or the application-specific stuff needs to be
# abstracted out here.
#
##############################################################################
class SimpleMainMenu( SimpleMenuNavigator ):
    
    ##############################################################################
    #
    # SimpleMainMenu.__init__
    #
    # Parse the configuration file, if any, and initialize the menu handler.
    #
    # Input parameters:
    #   window           - window to draw menu in
    #   title            - menu title, displayed in the top border
    #   config_file_name - the name of the configuration file to store values in;
    #                      None if not using a configuration file.
    #   save_hook        - function called when a save operation is perfomed.
    #
    ##############################################################################
    def __init__( self, window, title, config_file_name = None, save_hook = None ):      
        SimpleMenuNavigator.__init__( self, window, title )
        
        window.addstr( self.HEADING_ROW, self.HEADING_COLUMN,
                       "Select an item and press enter. ESC to exit." )
        
        self.config_file_name = config_file_name
        self.config_parser = None
        self.is_saved = 0
        self.reboot_requested = 0
        self.save_hook = save_hook
        
        if config_file_name:
            try:
                self.config_parser = SimpleMenuConfigParser( config_file_name )
            except IOError:
                self.status_write( "Unable to open file %s, permission denied!" % self.config_file_name )
        
        # Display initial status line.
        import getpass
        if _is_simple_mode:
            mode = 'Simple'
        else:
            mode = 'Normal'
        status = "USER: %s  MODE: %s  TERMINAL: %s" % ( getpass.getuser(), mode, os.environ['TERM'] )
        self.status_write( status )
        
    ##############################################################################
    #
    # SimpleMainMenu.add_item
    #
    # Add a top level menu selection.
    #
    # Input parameters:
    #   label  - label (or name) for the selection.
    #
    # Returns:
    #   The newly created selection, ready to have options added to it.
    #
    ##############################################################################
    def add_item( self, label ):
        row = len( self.menu_list ) + self.FIRST_ITEM_ROW
        menu_item = SimpleMenuSelection( self, self.ITEM_COLUMN, row, label )
        self.menu_list.append( menu_item )
        return menu_item
    
    ##############################################################################
    #
    # SimpleMainMenu.stop
    #
    # Stop menu processing. No-op if processing already stopped.
    #
    # Returns:
    #   1 if the system should be rebooted, 0 otherwise.
    #
    ##############################################################################
    def stop( self ):
        if self.active:
            if self.config_parser:
                is_changed = 0;
                for menu in self.menu_list:
                    if hasattr( menu, 'is_changed' ) and menu.is_changed():
                        is_changed = 1
        
                if is_changed:
                    mb = SimpleMessageBox( self.window, 'NOTICE',
                                           "Configuration changes have been made!\n"
                                           "Press ENTER to save changes.\n"
                                           "Press ESC to discard changes.",
                                           SimpleMessageBox.MB_OK_CANCEL )
                    ch = mb.run()
                    if ch == curses.KEY_ENTER:
                        self.save()

                if self.is_saved:
                    mb = SimpleMessageBox( self.window, 'NOTICE',
                                           "Saved changes do not take effect\n"
                                           "until the system is rebooted.\n"
                                           "Type R now to reboot the system now.\n"
                                           "Type anything else to exit." )
                    ch = mb.run()
                    if ch == ord('R') or ch == ord('r'): self.reboot_requested = 1
             
            self.deactivate()

        return self.reboot_requested


    ##############################################################################
    #
    # SimpleMainMenu.save
    #
    # Save the current configuration options.
    #
    # Returns:
    #   1 if the operation was successful, 0 otherwise.
    #
    ##############################################################################
    def save( self ):
        if self.config_parser:
            try:
                os.rename( self.config_file_name, self.config_file_name + '.bak' )
                self.config_parser.save()
                self.status_write( "Changes saved in %s" % self.config_file_name )
                if self.save_hook:
                    self.save_hook( self )
                self.is_saved = 1
                return 1
            except OSError, e:
                msg = "Save error: "
                if e.strerror: msg += e.strerror + ": "
                if e.filename: msg += e.filename
                self.status_write( msg )
            except IOError:
                self.status_write( "Save error: unable to write %s!" % self.config_file_name )
        else:
            self.status_write( "Configuration file not available. Changes NOT saved!" )
        return 0
    
    ##############################################################################
    #
    # SimpleMainMenu.handlech
    #
    # Handle an input character.  If the character is associated with a function
    # key then execute the key's action.  If the character is Esc, then stop
    # processing.
    #
    # Input parameters:
    #   ch     - the input character
    #
    # Returns:
    #   None if the input matched a function key or Esc, otherwise the input
    #   character is returned.
    #
    ##############################################################################
    def handlech( self, ch ):
        if ch == curses.ascii.ESC:
            self.stop()
            return None
        return SimpleMenuNavigator.handlech( self, ch )
    

##############################################################################
#
# simple_menu
#
# Main entry point. Initialize curses, runs a caller-supplied hook,
# and de-initalize curses.
#
# Input parsmeters:
#    func        - hook to run inside the curses wrapper
#    option_list - command line options; extraneous options are ignored.
#
##############################################################################
def simple_menu( func, option_list ):
    # Process command-line options.
    for opt in option_list:
        if opt[0] == '--terminal':
             os.environ['TERM'] = opt[1]
        elif opt[0] == '--debug':
            global _is_debug
            _is_debug = 1
        elif opt[0] == '--simple':
            global _is_simple_mode
            _is_simple_mode = 1

    curses.wrapper( func )
