'''
README.TXT for TCS protocol

NOTE: the RS-485 A/B labeling used by
TCS is the opposite of the standard.  Our A goes to their B
and visa-versa.

The line handler supports both static and self discovered nodes.

To use it:  Create a TCS protocol node under a RS-485 comm port.
To use auto-discovery, enable it for either 'always' or 'new'. 
Always will always search for and create node trees for any devices
it finds.  New will only instantiate nodes for devices that are not
statically defined allready.

Each TCS device has a seperate node under which are point nodes or groups of 
point nodes.

Most TCS devices come from the factory set to address 1 or 248.  
248 is a broadcast address (which we do not include in the auto-discovery
search).  It is not possible to actually read the 
address of a controller, you can only attempt to send a packet to it and
see if it responds.  If the system is an existing system, the addresses will
already be defined and can be discovered.  
If it is a new system and addresses need to be assigned
to the controllers, set up a single device node for address 248 and a value
node for parameter 'a', position '1' and then 'set' the value to the desired
address.  The value read from that location is the 'type' number for the device,
not the address, so you cannot see what was written.  Go figure.

The node tree for an auto discovered tcs device follows the way the protocol 
command structure is setup.  This results in a grouping of points for each
'parameter' (group), each point is called a 'position'.  This word comes from
the way a bitmap is used to map values to positions in a read or write packet.

Time values are displayed as 'HH:MM:SS' and can be set using the same format or 
the number of seconds since midnight

