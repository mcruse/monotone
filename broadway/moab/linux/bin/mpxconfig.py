"""
Copyright (C) 2002 2003 2004 2010 2011 Cisco Systems

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
# @fixme Replace all hard coded paths with properties.
# @fixme Log actions.
# @fixme Interface to the configuration service and to the running Broadway
#        application (if any).
# @fixme No changes should require a reboot.

import sys
import getopt
import socket, struct


# Local constants.
COMMAND = 'mpxconfig'
_MODULE_VERSION = "$Revision: 20426 $" # Revision number assigned by CVS
_HELP_MSG = """\
%s [options] [configuration_file]

  OPTIONS:
    --help                Displays this help message
    --simple              Enable simple mode (no graphics characters in menu).
    --path LIB_PATH       Appends LIB_PATH to the python library search path.
    --terminal TYPE       Sets the terminal type to TYPE.
    --color               Enable the default color scheme to aid readability.
    --debug               Enable debugging code (for developer use only).

  ARGUMENTS:
    configuration_file    Specify the configuration file.  The default
                          configuration file is '/etc/mpxinit.conf'.
""" % (COMMAND,)

# Lists used for multiple-choice options
on_off_list   = ["disabled", "enabled"]
speed_list    = ["57600", "115200", "230400", "460800", "2400", "9600", "19200", "38400"]
flow_list     = ["hardware", "XON/XOFF", "none"]
databits_list = ["8", "7", "6", "5" ]
stopbits_list = ["1", "2" ]
parity_list   = ["none", "odd", "even"]

# Global flag to indicate if the system should be rebooted.
_reboot_requested = 0
_host_name = None
_modem_menu = None

_do_color = 0

# Global vars to store command line options and arguments.
_options = []
_args = []

def _read_conf_value( config_parser, section, option ):
    if config_parser:
        if config_parser.has_option( section, option ):
            return config_parser.get( section, option )
    return None

def dottedQuadToNum(ip):
    "convert decimal dotted quad string to long integer"
    return struct.unpack('L',socket.inet_aton(ip))[0]

def numToDottedQuad(n):
    "convert long int to dotted quad string"
    return socket.inet_ntoa(struct.pack('L',n))
      
def network(address, netmask):
    n = dottedQuadToNum(address)
    m = dottedQuadToNum(netmask)
    net = n & m
    return numToDottedQuad(net)

#
# Handle Megatron configuration
#

def generate_megatron_config(p):
    p = menu.config_parser

    os.system('rm -f /etc/resolv.conf')
    f = open('/etc/resolv.conf', 'w+')
    f.write('search %s\n' % p.get('host', 'domain_name'))
    f.write('nameserver %s\n' % p.get('host', 'nameserver'))
    f.close()

    f = open('/etc/network/interfaces', 'w+')
    f.write('# /etc/network/interfaces -- configuration file for ifup(8), ifdown(8)\n\n')
    f.write('auto lo\n')
    f.write('iface lo inet loopback\n\n')

    address = p.get('eth0', 'ip_addr')
    netmask = p.get('eth0', 'netmask')
    gateway = p.get('host', 'gateway')

    f.write('auto eth0\n')
    if p.get('eth0', 'dhcp') == 'enabled':
        f.write('iface eth0 inet dhcp\n\n')
    else:
        f.write('iface eth0 inet static\n')
        f.write('        address %s\n' % address)
        f.write('        netmask %s\n' % netmask)
        f.write('        network %s\n' % network(address, netmask))
        if network(gateway, netmask) == network(address, netmask):
            f.write('        gateway %s\n\n' % gateway)
        
    address = p.get('eth1', 'ip_addr')
    netmask = p.get('eth1', 'netmask')

    f.write('auto eth1\n')
    if p.get('eth1', 'dhcp') == 'enabled':
        f.write('iface eth1 inet dhcp\n\n')
    else:
        f.write('iface eth1 inet static\n')
        f.write('        address %s\n' % address)
        f.write('        netmask %s\n' % netmask)
        f.write('        network %s\n' % network(address, netmask))
        if network(gateway, netmask) == network(address, netmask):
            f.write('        gateway %s\n\n' % gateway)
        
    f.close()

    # Set hostname
    f = open('/etc/hostname', 'w+')
    f.write(p.get('host', 'hostname') + '.' + p.get('host', 'domain_name'))
    f.close()

    # Add hostname to the end of /etc/hosts so that flexlm doesn't barf
    hosts_entry = '127.0.0.1       localhost.localdomain           localhost %s.%s\n' 
    f = open('/etc/hosts', 'w+')
    f.write('# Generated by mpxconfig. Contents will be overwritten!\n')
    f.write(hosts_entry % (p.get('host', 'hostname'), p.get('host', 'domain_name')))
    f.close()

    # Now tell the kernel about the change so we don't have to wait for reboot
    os.system('hostname %s.%s' % (p.get('host', 'hostname'), p.get('host', 'domain_name')))

    sysctl = open('/etc/sysctl.conf').read().split('\n')
    f = open('/etc/sysctl.conf', 'w+')
    for l in sysctl:
        if 'net.ipv4.ip_forward' in l:
            if p.get('host', 'ip_forward') == 'enabled': 
                ip_forward = 1
            else:
                ip_forward = 0
            f.write('net.ipv4.ip_forward=%d\n' % ip_forward)
        else:
            f.write(l + '\n')
    f.close()
                 
 
################################ BEGIN ROUTING HACK #########################

_route_list = None

def _get_routes():
    return _route_list.get_routes()

def _edit_action( args ):
    global _route_values
    assert( len( args ) == 4 )
    
    # Convert to ("net addr", "net mask", "gateway addr")
    new_value = ( str( args[1] ), str( args[2] ), str( args[3] ) )
    
    route_menu = args[0]
    list = route_menu.menu_list[0]
    list.paint( 1 )
    old_route = list.get()
    list.replace_current_route( new_value )
    route_menu.status_write( "Route %s modified" % old_route )

def _add_action( args ):
    global _route_values
    assert( len( args ) == 4 )
    
    # Convert to ("net addr", "net mask", "gateway addr")
    new_value = ( str( args[1] ), str( args[2] ), str( args[3] ) )
    route_menu = args[0]
    list = route_menu.menu_list[0]
    list.paint( 1 )
    list.add_route( new_value )
    route_menu.status_write( "Route %s added" % new_value[0] )

def _add_route( route_menu ):
    edit_menu = route_menu.create_submenu( 9, 42, "Add route" )
    addr_ctl = edit_menu.add_control( SimpleIpAddressControl( edit_menu,
                                                              edit_menu.get_next_col(), edit_menu.get_next_row(),
                                                              'Network Address : ' ) )      
    mask_ctl = edit_menu.add_control( SimpleIpAddressControl( edit_menu,
                                                              edit_menu.get_next_col(), edit_menu.get_next_row(),
                                                              'Network Mask    : ' ) )      
    gate_ctl = edit_menu.add_control( SimpleIpAddressControl( edit_menu,
                                                              edit_menu.get_next_col(), edit_menu.get_next_row(),
                                                              'Gateway Address : ' ) )
    # Action called when the changes are committed.
    edit_menu.add_action_control( SimpleActionControl( _add_action, route_menu, addr_ctl, mask_ctl, gate_ctl ) )

    # Run the editor.
    route_menu.run_submenu( edit_menu )

def _del_route( route_menu ):
    # Get the list control, which is the one and only control in the route management menu, and
    # extract its value.
    list = route_menu.menu_list[0]
    if not list.have_selection():
        route_menu.status_write( "No route selected" )
    else:
        value = list.get()
        list.replace_current_route()
        list.paint( 1 )
        route_menu.status_write( "Route %s deleted" % value )

def _edit_route( route_menu ):
    # Get the list control, which is the one and only control in the route management menu, and
    # extract its value.
    list = route_menu.menu_list[0]
    if not list.have_selection():
        route_menu.status_write( "No route selected" )
    else:
        edit_menu = route_menu.create_submenu( 9, 42, "Edit route" )
        rv = list.get_current_route()
        addr_ctl = edit_menu.add_control( SimpleIpAddressControl( edit_menu,
                                                                  edit_menu.get_next_col(),
                                                                  edit_menu.get_next_row(),
                                                                  'Network Address : ',
                                                                  rv[0] ) )      
        mask_ctl = edit_menu.add_control( SimpleIpAddressControl( edit_menu,
                                                                  edit_menu.get_next_col(),
                                                                  edit_menu.get_next_row(),
                                                                  'Network Mask    : ',
                                                                  rv[1] ) )      
        gate_ctl = edit_menu.add_control( SimpleIpAddressControl( edit_menu,
                                                                  edit_menu.get_next_col(),
                                                                  edit_menu.get_next_row(),
                                                                  'Gateway Address : ',
                                                                  rv[2] ) )
        # Action called when the changes are committed.
        edit_menu.add_action_control( SimpleActionControl( _edit_action,
                                                           route_menu, addr_ctl, mask_ctl, gate_ctl ) )
        route_menu.run_submenu( edit_menu )

def _manage_routes( port_menu ):
    global _route_list
    
    class RouteList( SimpleDropDownListControl, SimpleConfigItem ):
        _DEFAULT_ROUTE = "select a route"
        _ROUTES_OPTION = "routes"
        
        def __init__( self, parent, x_pos, y_pos ):
            SimpleDropDownListControl.__init__( self, parent, x_pos, y_pos, 'Route : ', self._DEFAULT_ROUTE,
                                                _get_routes, 12, 18 )
            if parent.parent.title == "Ethernet port 0":
                section = 'eth0'
            else:
                section = 'eth1'
            SimpleConfigItem.__init__( self, parent.config_parser, section, self._ROUTES_OPTION, [] )
    
            self._eval_values = None
            if self.current_value:
                self._eval_values = self._eval( self.current_value )
         
        # Convert configuration value to list of tuples.
        def _eval( self, value ):
            result = []
            routes = value.split( ';' )
            for r in routes:
                route = r.split( ',' )
                # We have seen a case where a line was terminated with a semi-colon, resulting in an
                # empty route.  Avoid crashing if this happens.
                if len( route ) >= 3:
                    result.append( (route[0], route[1], route[2]) )
            return result
        
        # Convert list of tuples to configuration value.
        def _repr( self, list ):
            result = ""
            for r in list:
                result = result + "%s,%s,%s" % r
                if list.index( r ) < len( list ) - 1:
                    result = result + ';'
            return result
                    
        # Test to see if user has made a selection.
        def have_selection( self ):
            return self.get() != self._DEFAULT_ROUTE
        
        # Get the routes to display in the list.
        def get_routes( self ):
            routes = []
            if self._eval_values:
                for r in self._eval_values:
                    routes.append( r[0] )
            return routes
        
        def get_current_route( self ):
            return self._eval_values[self.iSelection]
        
        # Replace, or remove, the current route.
        def replace_current_route( self, new_value = None ):
            if new_value:
                self._eval_values[self.iSelection] = new_value
            else:
                del self._eval_values[self.iSelection]
            self.current_value = self._repr( self._eval_values )
    
        # Add a new route.
        def add_route( self, new_value ):
            if self._eval_values:
                self._eval_values.append( new_value )
            else:
                self._eval_values = [new_value]
            self.current_value = self._repr( self._eval_values )

        def commit( self ):
            SimpleDropDownListControl.commit( self)
            SimpleConfigItem.save( self )

        def cancel( self ):
            SimpleDropDownListControl.cancel( self )
            SimpleConfigItem.revert( self )
 
    route_menu = port_menu.create_submenu( 12, 42, "Route Management" )
    _route_list = RouteList( route_menu, route_menu.get_next_col(), route_menu.get_next_row() )
    route_menu.add_control( _route_list )
    route_menu.add_fcn_key( " F1: Add  ", _add_route )
    route_menu.add_fcn_key( " F2: Del  ", _del_route )
    route_menu.add_fcn_key( " F3: Edit ", _edit_route )
                            
    # Run the route manager
    port_menu.run_submenu( route_menu )
    
################################ END ROUTING HACK ####################################

######################### BEGIN DIAL-IN/DIAL-OUT SUPPORT #############################

##
# Enable or disable ppp dial-in.
#
# @param args A tuple of arguments: (SimpleCycleMenu<state>,
#             SimpleCycleMenu<user>, SimpleTextMenu<pswd>).
def _set_dailin_action( args ):
    assert( len( args ) == 3 )

    # Set the password for the ppp user.
    user   = args[1].get_value()
    pswd   = args[2].get_value()
    cmd    = "echo %s | passwd --stdin %s 1>/dev/null 2>&1" % (pswd, user)
    result = os.system( cmd )
    if result:
        raise ESystemFailure( "passwd %s" % user )

    # Update inittab.
    inittab = InittabManager()
    modem = get_modem()
    gname = 'MPX_MGETTY_TTY%s' % modem[-2:].upper()
    if gname != 'MPX_MGETTY_TTYS1':
        # For reverse compatibility with older mpxconfigs, remove the spurious
        # reference to MPX_MGETTY_TTYS1.
        inittab.remgroup( 'MPX_MGETTY_TTYS1' )
    if args[0].get_value() == 'enabled':
        if not inittab.findgroup( gname ):
            inittab.addgroup(
                InittabGroup(
                    gname,
                    '%s:2345:respawn:/sbin/mgetty -x 0 -n 1 %s' % (
                        modem[-2:].upper(), modem
                        )
                    )
                )
    else:
        inittab.remgroup( gname )
    inittab.commit()

def _createProperty( parent, childName ):
    # Find doc node, which has no parent node.
    dn = parent
    while dn.parentNode: dn = dn.parentNode
    
    # Create new property element
    elem = dn.createElement( 'property' )
    elem.setAttribute( 'name', childName )
    parent.appendChild( elem )
    return elem
    
def _getChildElementByName( node, name ):
    for n in node.childNodes:
        if n.nodeType == n.ELEMENT_NODE:
            if n.getAttribute( 'name' ) == name:
                return n
    return None

def _getElementByPath( doc, path ):
    elem = doc.documentElement
    for name in path.split( '/' ):
        if name == '':
            name = '/'
        elem = _getChildElementByName( elem, name )
        assert( elem != None )
    return elem

def _setElementValueFromConfig( elem, config_parser, section, optName ):
    value = _read_conf_value( config_parser, section, optName )
    assert( value != None )
    elem.setAttribute( 'value', value )
    
def _setChildValue( parent, childName, value ):
    elem = _getChildElementByName( parent, childName )
    if not elem:
        elem = _createProperty( parent, childName )
    elem.setAttribute( 'value', value )

def _setChildValueFromConfig( parent, childName, config_parser, section, optName = None ):
    if not optName:
        optName = childName
    elem = _getChildElementByName( parent, childName )
    if not elem:
        elem = _createProperty( parent, childName )
    _setElementValueFromConfig( elem, config_parser, section, optName )

def _sync_modem( configDoc, config_parser ):
    section = 'modem'
    modem_elem = _getElementByPath( configDoc, '/interfaces/modem' )
    for n in modem_elem.childNodes:
        if n.nodeName == 'config':
            _setChildValueFromConfig( n, 'baud', config_parser, section, 'connect_speed' )
            _setChildValueFromConfig( n, 'flow_control', config_parser, section )
            _setChildValueFromConfig( n, 'bits', config_parser, section )
            _setChildValueFromConfig( n, 'stop_bits', config_parser, section )
            _setChildValueFromConfig( n, 'parity', config_parser, section )
    
def _sync_dailout( configDoc, config_parser ):
    section = 'dialout'
    outgoing_elem = _getElementByPath( configDoc, '/interfaces/modem/ppp0/outgoing' )
    for n in outgoing_elem.childNodes:
        if n.nodeName == 'config':
            _setChildValueFromConfig( n, 'password', config_parser, section )
            _setChildValueFromConfig( n, 'user_id', config_parser, section, 'userid' )
            _setChildValueFromConfig( n, 'secondary_name_server', config_parser, section, 'dns2' )
            _setChildValueFromConfig( n, 'primary_name_server', config_parser, section, 'dns1' )
            _setChildValueFromConfig( n, 'phone_number', config_parser, section, 'phone' )
            value = _read_conf_value( config_parser, section, 'state' )
            if value == 'enabled':
                value = '1'
            else:
                value = '0'
            _setChildValue( n, 'enable', value )

def _sync_dailin( configDoc, config_parser ):
    section = 'dialin'
    incoming_elem = _getElementByPath( configDoc, '/interfaces/modem/ppp0/incoming' )
    for n in incoming_elem.childNodes:
        if n.nodeName == 'config':
            _setChildValueFromConfig( n, 'password', config_parser, section )
            _setChildValueFromConfig( n, 'user_id', config_parser, section, 'userid' )
            _setChildValueFromConfig( n, 'client_ip', config_parser, section, 'client_addr' )
            _setChildValueFromConfig( n, 'local_ip', config_parser, section, 'local_addr' )
            value = _read_conf_value( config_parser, section, 'state' )
            if value == 'enabled':
                value = '1'
            else:
                value = '0'
            _setChildValue( n, 'enable', value )

#
# Synchronize the framework's configuration database with mpxinit.conf, if necessary.
#
def _sync_with_xml( menu, fileName ):
    if not os.path.isfile( fileName ):
        # No XML file!  Probably testing on a PC.
        return
    
    # Some systems don't have a modem.
    if _modem_menu and _modem_menu.is_changed():
        # Parse configuration file.
        menu.status_write( 'Updating system configuration...please wait', ATTR_BLINK )
        configDoc = xml.dom.minidom.parse( fileName )

        _sync_modem( configDoc, menu.config_parser )
        if hasattr( _modem_menu, 'dialout_menu' ) and _modem_menu.dialout_menu.is_changed():
            state = _read_conf_value( menu.config_parser, 'dialout', 'state' )
            if state != None:    
                _sync_dailout( configDoc, menu.config_parser )
        if hasattr( _modem_menu, 'dialin_menu' ) and _modem_menu.dialin_menu.is_changed():
            state = _read_conf_value( menu.config_parser, 'dialin', 'state' )
            if state != None:    
                _sync_dailin( configDoc, menu.config_parser )

        # Save configuration file.
        xfile = open( fileName, 'w' )
        configDoc.writexml( xfile )
        xfile.close()
        menu.status_write( 'Done.' )
        
def _manage_dialout( modem_menu ):
    # Configuration section for modem dial-out.
    config_section = 'dialout'

    submenu = modem_menu.create_submenu( 12, 45, "Dial out" )
    
    # Save for exit code.
    modem_menu.dialout_menu = submenu

    submenu.add_pick_option( "State                : ", on_off_list, config_section, "state" )
    submenu.add_text_option( "Phone number         : ", config_section, "phone", _is_valid_phone_number )
    submenu.add_text_option( "User ID              : ", config_section, "userid" )
    submenu.add_text_option( "Password             : ", config_section, "password" )
    submenu.add_ip_option  ( "Primary name server  : ", config_section, "dns1" )
    submenu.add_ip_option  ( "Secondary name server: ", config_section, "dns2" )
                            
    # Run the dail-out manager
    modem_menu.run_submenu( submenu )
    
def _manage_dialin( modem_menu ):
    # Configuration section for modem dial-out.
    config_section = 'dialin'

    submenu = modem_menu.create_submenu( 12, 45, "Dial in" )
    
    # Save for exit code.
    modem_menu.dialin_menu = submenu

    state_opt = \
    submenu.add_pick_option( "State                : ", on_off_list, config_section, "state" )
    user_opt = \
    submenu.add_pick_option( "User ID              : ", ["pppuser"], config_section, "userid" )
    pswd_opt = \
    submenu.add_text_option( "Password             : ", config_section, "password" )
    submenu.add_ip_option  ( "Local IP address     : ", config_section, "local_addr" )
    submenu.add_ip_option  ( "Client IP address    : ", config_section, "client_addr" )
    submenu.add_action_control( SimpleActionControl( _set_dailin_action, state_opt, user_opt, pswd_opt ) )

    # Run the dail-out manager
    modem_menu.run_submenu( submenu )

######################### END DIAL-IN/DIAL-OUT SUPPORT #############################
    
def _mpx_save( menu ):
    _sync_with_xml( menu, '/var/mpx/config/broadway.xml' )
    
    new_host_name = _read_conf_value( menu.config_parser, 'host', 'hostname' )
    if new_host_name != _host_name:
        try:
            # Leave file for rc.mpx to find
            fd = open( '/etc/mpx_hostnamechanged.tmp', 'w' )
            fd.write( "%s --> %s\n" % ( _host_name, new_host_name ) )
            fd.close()
        except EnvironmentError, e:
            msg = "Error: "
            if e.strerror: msg += e.strerror + ": "
            if e.filename: msg += e.filename
            menu.status_write( msg )
    # Not sure what problem the following line fixes.  It should probably be in rc.mpx.
    os.system( 'rm -f /etc/dhcpc/dhcpcd-eth?.{info,cache} 1>/dev/null 2>/dev/null' )

def _is_valid_phone_number( str ):
    # Some special characters allowed in the "phone number."  See modem command reference
    # manual for details.
    other_chars = ['-', ',', '*', '#', 'W', '@', '&']
    
    for ch in str:
        if not ch.isdigit() and not ch.isspace() and not ch in other_chars:
            return 0
    return 1

##
# Check for valid host name, as per RFC2396.
# Name can contain only alphanumerics and '-', and '-' cannot be first
# or last character. An empty host name is considered valid in this
# context, so caller should handle that.
##
def _is_valid_hostname( str ):
    if len(str) > 255:
        return 0
    disallowed = re.compile("[^A-Z0-9\d-]", re.IGNORECASE)	
    if disallowed.search(str):
        return 0
    return 1

# Returns 'S1' or '1200' or '1500' or '2400' or '2500' or None
def get_model():
    model = None
    try:
        f = open( '/proc/mediator/model' )
        model = f.read().strip()
        f.close()
    except:
        pass
    return model

def get_modem():
    if get_model() in ['1500', '2500']:
        return '/dev/ttySe'
    return '/dev/ttyS1'

#####################################################################
# Hook function called back by the tty handler.
#  Input:
#    w        - window handle for the screen
#####################################################################
def mpx_config( w ):
    global menu
    # Strip extraneous text from the revision number and append simplemenu's version.
    version = _MODULE_VERSION.replace( '$Revision: ', '' )[:-2]
    
    # Sole argument, if present, is the configuration file name.
    if len( _args ) > 0:
        config_file_name = _args[0]
    else:
        config_file_name = '/etc/mpxinit.conf'

    # Configuration option names.
    dhcp_option = "dhcp"
    ip_addr_option = "ip_addr"
    netmask_option = "netmask"
    forward_option = "ip_forward"
    
    # Parse the config file and intialize the menu handler.
    menu = SimpleMainMenu( w, "%s v%s" % (COMMAND, version), config_file_name, _mpx_save )
    
    # Save the host name.
    global _host_name
    _host_name = _read_conf_value( menu.config_parser, 'host', 'hostname' )

    # Configuration section for global settings.
    config_section = 'host'

    submenu = menu.add_item( "Global settings" ).get_submenu()
    submenu.add_text_option( "Host name    : ", config_section, "hostname", _is_valid_hostname )
    submenu.add_text_option( "Domain       : ", config_section, "domain_name" )
    submenu.add_ip_option  ( "Gateway      : ", config_section, "gateway" )
    submenu.add_ip_option  ( "Name server  : ", config_section, "nameserver" )
    submenu.add_ip_option  ( "Proxy server : ", config_section, "proxyserver" )
    submenu.add_pick_option( "IP forwarding: ", on_off_list, config_section, forward_option )
    submenu.add_text_option( "Location     : ", config_section, "location" )
                             
    # Configuration section for eth0, if it exists.
    if os.access( '/proc/mediator/mac0', os.F_OK ):
        config_section = 'eth0'
    
        submenu = menu.add_item( "Ethernet port 0" ).get_submenu()
        submenu.add_pick_option( "DHCP      : ", on_off_list, config_section, dhcp_option )
        submenu.add_ip_option  ( "IP address: ", config_section, ip_addr_option )
        submenu.add_ip_option  ( "Net mask  : ", config_section, netmask_option )
        submenu.add_fcn_key    ( " F1: Routing ", _manage_routes )

    # Configuration section for eth1, if it exists.
    if os.access( '/proc/mediator/mac1', os.F_OK ):
        config_section = 'eth1'
    
        submenu = menu.add_item( "Ethernet port 1" ).get_submenu()
        submenu.add_pick_option( "DHCP      : ", on_off_list, config_section, dhcp_option )
        submenu.add_ip_option  ( "IP address: ", config_section, ip_addr_option )
        submenu.add_ip_option  ( "Net mask  : ", config_section, netmask_option )
        submenu.add_fcn_key    ( " F1: Routing ", _manage_routes )

    # Configuration section for modem if it exists.
    config_section = None
    menu_title = 'Modem'
    if get_model() != 'Megatron':
        print 'Probing for Modem'
        try:
            if test_modem( get_modem(), 3 ):
                config_section = 'modem'
        except EPortInUse, e:
            # Maybe it exists, maybe it doesn't?
            config_section = 'modem'
            menu_title += " (in use by process %s)" % e.in_use_by_pid
        except OSError, e:
            # Error, assume modem doesn't exist.
            pass
        if config_section:
            submenu = menu.add_item( menu_title ).get_submenu()
            submenu.add_pick_option( "Connection speed  : ", speed_list, config_section, "connect_speed" )
            submenu.add_pick_option( "Flow control      : ", flow_list, config_section, "flow_control" )
            submenu.add_pick_option( "Data bits         : ", databits_list, config_section, "bits" )
            submenu.add_pick_option( "Stop bits         : ", stopbits_list, config_section, "stop_bits" )
            submenu.add_pick_option( "Parity            : ", parity_list, config_section, "parity" )
            submenu.add_fcn_key    ( " F1: Dial-in  ", _manage_dialin )
            submenu.add_fcn_key    ( " F2: Dial-out ", _manage_dialout )
    
            # Save for exit code.
            global _modem_menu
            _modem_menu = submenu

    # Set system date and time.
    submenu = menu.add_item( "Set system date and time" ).get_submenu()
    submenu.add_datetime_control()

    # Change the color scheme if requested.  The MPX login banner leaves the terminal
    # colors in a state that is not flattering to Mpxconfig.
    if _do_color:
        if os.environ['TERM'] in ['vt100', 'linux']:
            # Red foreground, white background.
            print "\033[31;47m"

    menu.run()

    # For a Megatron generate appropriate entries in /etc/network/interfaces
    
    if get_model() == 'Megatron':
        generate_megatron_config(menu.config_parser)

    
    global _reboot_requested
    _reboot_requested = menu.stop()

#####################################################################
#
# M A I N
#
#####################################################################

if __name__ == '__main__':
    # Get the command line options.
    try:
        _options, _args = getopt.getopt( sys.argv[1:], '',
                                         ['help', 'simple', 'debug',
                                          'color', 'path=', 'terminal='] )
    except getopt.GetoptError, e:
        print e, ", use --help for help"
        sys.exit( 1 )

    # Check to see if help was requested.
    for opt in _options:
        if opt[0] == '--help':
            print _HELP_MSG
            sys.exit( 0 )

    # Process the command line options that this module cares about.  The
    # remainder are passed on to the menu system.
    for opt in _options:
        if opt[0] == '--path':
            sys.path.append( opt[1] )
            _options.remove( opt )
        elif opt[0] == '--color':
            _do_color = 1
            _options.remove( opt )

    # Import now that the library path is, or at least should be, set up.
    # This can take more than five seconds, so beg for patience.
    print "Please wait while %s examines the system..." % COMMAND
    import os
    import ConfigParser
    import xml.dom.minidom
    from zoneinfo import ESystemFailure
    from servicemgr import *
    from devicemgr import test_modem, EPortInUse
    from simplemenu import *

    # Run the menu using the hook function defined above.
    # Afterwards, force a reboot if one was requested.
    simple_menu( mpx_config, _options )
        
    if _reboot_requested:
        os.system( "reboot -f" )
