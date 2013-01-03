Modbus Readme

Modbus is an old protocol designed around an early Programmable Logic Controller.
Several (most, all?) of the conventions followed are historical and non-sensical.

Information is transferred between a master and one or more slaves.
Only one master is allowed on a modbus network.
Slaves only respond to commands from masters, otherwise they are silent.
Both RS-485 and RS-232 are used.  There are two variations of of data encoding,
binary and ascii.  The binary type is called RTU and all modern devices seem to
support it.

The basic units of data exchagned are the 'bit' and the 'word' (16 bits).  
Bit type info is called 'coils' and 'status'.  Word type info are 'registers'.

The four variations are:
    bits
        coil - read and write - typically meant to drive a relay coil output
        status - read only - used for switch type inputs
    registers
        holding register - read and write
        input register - read only

Read and write are from the standpoint of the master to the slave.

Registers are often used in combinations to represent data more complicated
than 16 bit words.  The following data types are supported:

word    16 or 32 bit unsigned integer
int     16 bit signed integer
loint   8 bit signed integer (low byte of register)
hiint   8 bit signed integer (high byte of register)
lobyte  8 bit unsigned integer (low byte of register)
hibyte  8 bit unsigned interer (high byte of register)
lochar  8 bit python char (low byte of register)
hichar  8 bit python char (high byte of register)
IEEE float 32 bit and 64 bit versions
dword   32 bit unsigned integer (same as word with length of 2)
string  variable length
zstring same as string but terminated with a zero character
modulo  16, 32, 48, 64 bits.  each 16 bits represents 0-9999. 
        16 bit range -9999 to 9999
        32 bit range -99,999,999 to 99,999,999
        48 bit range -999,999,999,999 to 999,999,999,999
        64 bit range -9,999,999,999,999,999 to 9,999,999,999,999,999
        pretty big huh?
power logic 48 and 64 bit versions
        48 same as 48 bit modulo / 1000.0 as a 64 bit IEEE float
        64 same as 64 bit modul0 / 1000.0 as a 64 bit IEEE float 
time    48 and 96 bit versions
        48 bit version:
            day  = low byte first register
            month = high byte first register
            hour = low byte second register
            year = high byte second register
            second = low byte third register
            minute = high byte third register
        96 bit version
            second = first register as word
            minute = second register as word
            hour  = third register as word
            day  = forth register as word
            month  = fifth register as word
            year = sixth register as word
        Both version represented internally as float seconds since epoch
DL06 Energy 64 bit
        megawatts = first 32 bits as word (unsigned int)
        kilowatts = second 32 bits as float
        
Now for the fun part.  The order registers are stored in a modbus device can be
in several possible orders.  The order of indvidual bits, bytes or words can be
in either big-endian (network) order or little-endian (intel) order.  Big-endian
places everything in left to right, most significant to least significant order.
Little-endian is the opposite.  Most of the time register are in big-endian order
but float types are often in little-endian word order with big-endian byte order.
Go figure.  So far bit orders have all been big-endian.

Each type of coil, status, register has it's own address range.
  Coils 1-9999
  Status 10001-29999
  Input Registers 30001-39999
  Holding Registers 40001-65535 (?)
  
Caching:

  The Holding Registers can be grouped into lists of contiguous points called a cache.
  All the points in a cache are read with one command.
  There can be gaps of between registers within a cache but there cannot be any
  overlap between caches.
  Caching for the most part is automatic with caches set up for each maximum block
  size of registers.  Manual cache boundries can be set if it is known if certain
  groups of registers will be read at the same time.  For instance, one group of 
  registers might be read frequently and others less often.  If they are physically
  located together, the frequent group can be put in a seperate cache to optimize
  the transfer speed by getting only those registers with a read command.
  Each node has a time-to-live (TTL) value.  If the value in the cache for a node
  has been read within the TTL time, the value will be retrieved from the cache
  rather than generate an actual modbus network read.  If the TTL has expired, the
  list of registers in a cache will be updated with a single read, reseting their
  respective TTL timers.





