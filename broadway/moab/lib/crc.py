# NOTE: This module is implemented in moab.lib.crc because it is shared
#       by both the moab and mpx packages.

##
# <p>
# CREDITS:</p>
# <p>
# The algorythms used in this module are based upon files developed by
# Michael Barr and subsequently placed in the public domain.  Below is
# the copyright notice distributed with those files:</p>
# <pre>
# * Copyright (c) 2000 by Michael Barr.  This software is placed into
# * the public domain and may be used for any purpose.  However, this
# * notice must not be changed or removed and no warranty is either
# * expressed or implied by its publication or distribution.
# </pre>

# 
# Note to anyone using this library or anyone who is thinking of using it:
# It is very slow.  How slow?  Well, on a 2500 board, doing a crc-ccitt it took
# 27ms for a CRC on a 54 byte string.  Not very impressive.
#
# -Mark Carlson, 2006-09-15


# @fixme Name and define WIDTH-8...

# @fixme Use framework Enumerations.
FALSE=0
TRUE=1
DEFAULT=0
BIT=1
BYTE=2
OPTIMIZED=3

##
# Reorder the bits of a binary sequence, by reflecting them
# about the middle position.
# @param data The unsigned integer to reflect.
# @param nBits The number of bits to reflect.
# @return The reflection of the original data.
# @fixme Create optimized versions for 8, 16, and 32 bits.  Possibly
#        for 12 bits as well.
def _reflect(data, nBits):
    reflection = 0x00000000L
    # Reflect the data about the center bit.
    for bit in range(1,nBits+1):
        # If the LSB bit is set, set the reflection of it.
        if data & 0x01:
            reflection |= long(1 << (nBits - bit))
        data = (data >> 1)
    reflection &= long((1 << nBits)-1)
    return reflection
##
#
class CRC(object):
    ##
    # @keyword CRC_NAME
    # @keyword WIDTH
    # @keyword POLYNOMIAL
    # @keyword INITIAL_REMAINDER
    # @keyword FINAL_XOR_VALUE
    # @keyword REFLECT_DATA
    # @keyword REFLECT_REMAINDER
    # @keyword CHECK_VALUE
    def __init__(self, **definition):
        self.CRC_NAME = definition['CRC_NAME']
        self.WIDTH = definition['WIDTH']
        self.POLYNOMIAL = definition['POLYNOMIAL']
        self.INITIAL_REMAINDER = definition['INITIAL_REMAINDER']
        self.FINAL_XOR_VALUE = definition['FINAL_XOR_VALUE']
        self.REFLECT_DATA = definition['REFLECT_DATA']
        self.REFLECT_REMAINDER = definition['REFLECT_REMAINDER']
        self.CHECK_VALUE = definition['CHECK_VALUE']
        # derived values and methods.
        self.TOPBIT = (1L << (self.WIDTH - 1))
        self.BITMASK = (1L << self.WIDTH) - 1 # @fixme Force value truncation.
        if self.REFLECT_DATA:
            self.REFLECT_DATA = self._reflect_data
        else:
            self.REFLECT_DATA = self._mask_value
        if self.REFLECT_REMAINDER:
            self.REFLECT_REMAINDER = self._reflect_remainder
        else:
            self.REFLECT_REMAINDER = self._mask_value
        # Default to the slow but sure implementation.  _init_table()
        # will "upgrade" DEFAULT and OPTIMIZED if it can.
        self._calculation = [
            self.bit_calc,  # DEFAULT=0
            self.bit_calc,  # BIT=1
            self.byte_calc, # BYTE=2
            self.bit_calc,  # OPTIMIZED=3
            ]
        self._init_table()
        return
    ##
    # Populate the partial CRC lookup table.
    # @fixme Reduce the table for WIDTH < 8?
    # @fixme Apply common optimizations (perhaps seperate
    #        reflecting and non-reflecting methods, etc...
    # @fixem If it's possible for the table to return invalid results,
    #        then disable the BYTE implementation.
    def _init_table(self):
        # Preallocate an empty table.
        self._byte_table = [0]*256
        # Compute the remainder of each possible dividend.
        for dividend in range(0,256):
            if self.WIDTH > 16:
                # Avoid shifting into a negiative value.
                dividend = long(dividend)
            # Start with the dividend followed by zeros.
            remainder = dividend << (self.WIDTH - 8)
            # Perform modulo-2 division, a bit at a time.
            for bit in range(8,0,-1):
                # Try to divide the current data bit.
                if remainder & self.TOPBIT:
                    remainder = (remainder << 1) ^ self.POLYNOMIAL
                else:
                    remainder = (remainder << 1)
                remainder &= self.BITMASK # Hack?
            # Store the result into the table.
            self._byte_table[dividend] = remainder
        # Upgrade the DEFAULT and OPTIMIZED implementations.
        self._calculation[DEFAULT] = self.byte_calc
        self._calculation[OPTIMIZED] = self.byte_calc
        return
    ##
    # Do nothing.
    # @return the first argument supplied.
    def _mask_value(self, value, width=None):
        if width is None:
            width = self.WIDTH
        value &= (1 << width) - 1
        return value
    ##
    # @return (unsigned char)
    def _reflect_data(self, byte):
        return _reflect(byte, 8)
    ##
    # @return crc
    def _reflect_remainder(self, remainder):
	return _reflect(remainder, self.WIDTH)
    ##
    # Compute the CRC of a given message.
    # @note This method performs the polynomial division a bit at a time, so
    #       so it's incredibly slow.  But, it should be correct for all WIDTHs,
    #       so it can be used to validate the results of the faster methods
    #       (especially once we add in highly specific optimizations for the
    #       common configurations).
    # @return The CRC of the message
    def bit_calc(self, message):
        remainder = self.INITIAL_REMAINDER
        # Perform modulo-2 division, a byte at a time.
        for byte in xrange(0,len(message)):
            # Bring the next byte into the remainder.
            remainder ^= self.REFLECT_DATA(ord(message[byte]))<<(self.WIDTH-8)
            # Perform modulo-2 division, a bit at a time.
            for bit in range(8,0,-1):
                # Try to divide the current data bit.
                if remainder & self.TOPBIT:
                    remainder = (remainder << 1) ^ self.POLYNOMIAL
                else:
                    remainder = remainder << 1
                remainder &= self.BITMASK # Hack?
        # The final remainder is the CRC result.
        remainder = (self.REFLECT_REMAINDER(remainder) ^ self.FINAL_XOR_VALUE)
        remainder &= self.BITMASK # Hack?
        return remainder
    ##
    # Compute the CRC of a given message.
    # @note This method performs the polynomial division a byte at a time
    #       using a pre-calculated table.  This is significantly faster
    #       than <code>bit_calc</code>.
    # @return The CRC of the message.
    def byte_calc(self, message):
        remainder = self.INITIAL_REMAINDER
        # Divide the message by the polynomial, a byte at a time.
        for byte in xrange(0,len(message)):
            data = self.REFLECT_DATA(ord(message[byte]))^(remainder >>
                                                          (self.WIDTH-8))
            remainder = self._byte_table[data&0xff] ^ (remainder << 8)
        # The final remainder is the CRC.
        remainder = (self.REFLECT_REMAINDER(remainder) ^ self.FINAL_XOR_VALUE)
        remainder &= self.BITMASK # Hack?
        return remainder
    ##
    # Calculate the CRC for <code>text</code>.
    # @param text String of bytes to calculate the CRC.
    # @param calculation
    # @value DEFAULT=0 Use the fastest, reliable code for this CRC's
    #                  definition.
    # @value BIT=1 Calculate the CRC bit-by-bit.  Theoretically, this will
    #              result in the correct result of the CRCs configured
    #              WIDTH.
    # @value BYTE=2 Calculate the CRC a byte at a time using a
    #               pre-calculated table specific to this CRC's
    #               definition.
    # @value OPTIMIZED=3 Use the most optimized code available for this
    #                    CRC's definition.  If there is not a definition
    #                    specific optimization, then this is the same as
    #                    BYTE.
    # @default DEFAULT=0
    # @fixme Determin if there are cases where the byte table will not yield
    #        correct results.  If that is the case, deal with it.
    def __call__(self, text, calculation=OPTIMIZED):
        return self._calculation[calculation](text)

##
# Calculate a CCITT compliant CRC.
# @param text String of data to use to calculate the CCITT CRC.
# @param calculation Optional parameter to specifiy the specific
#                    implementation.  Mostly useful for testing.
# @value DEFAULT=0 Use the fastest, reliable code for this CRC's
#                  definition.
# @value BIT=1 Calculate the CRC bit-by-bit.  Theoretically, this will
#              result in the correct result of the CRCs configured
#              WIDTH.
# @value BYTE=2 Calculate the CRC a byte at a time using a
#               pre-calculated table specific to this CRC's
#               definition.
# @value OPTIMIZED=3 Use the most optimized code available for this
#                    CRC's definition.  If there is not a definition
#                    specific optimization, then this is the same as
#                    BYTE.
# @default DEFAULT=0
# @return The CCITT CRC.
ccitt = CRC(**{'CRC_NAME':'CRC-CCITT',
               'WIDTH':16,
               'POLYNOMIAL':0x1021,
               'INITIAL_REMAINDER':0xFFFF,
               'FINAL_XOR_VALUE':0x0000,
               'REFLECT_DATA':FALSE,
               'REFLECT_REMAINDER':FALSE,
               'CHECK_VALUE':0x29B1
               })

##
# Calculate a CRC-16 compliant CRC.
# @param text String of data to use to calculate the CRC-16 CRC.
# @param calculation Optional parameter to specifiy the specific
#                    implementation.  Mostly useful for testing.
# @value DEFAULT=0 Use the fastest, reliable code for this CRC's
#                  definition.
# @value BIT=1 Calculate the CRC bit-by-bit.  Theoretically, this will
#              result in the correct result of the CRCs configured
#              WIDTH.
# @value BYTE=2 Calculate the CRC a byte at a time using a
#               pre-calculated table specific to this CRC's
#               definition.
# @value OPTIMIZED=3 Use the most optimized code available for this
#                    CRC's definition.  If there is not a definition
#                    specific optimization, then this is the same as
#                    BYTE.
# @default DEFAULT=0
# @return The CRC-16 CRC.
crc16 = CRC(**{'CRC_NAME':'CRC-16',
               'WIDTH':16,
               'POLYNOMIAL':0x8005,
               'INITIAL_REMAINDER':0x0000,
               'FINAL_XOR_VALUE':0x0000,
               'REFLECT_DATA':TRUE,
               'REFLECT_REMAINDER':TRUE,
               'CHECK_VALUE':0xBB3D
               })


# Note: For anyone comtemplating using crc32, you might want to try a less
#       configurable, but much faster version in the binascii module.

##
# Calculate a CRC-32 compliant CRC.
# @param text String of data to use to calculate the CRC-32 CRC.
# @param calculation Optional parameter to specifiy the specific
#                    implementation.  Mostly useful for testing.
# @value DEFAULT=0 Use the fastest, reliable code for this CRC's
#                  definition.
# @value BIT=1 Calculate the CRC bit-by-bit.  Theoretically, this will
#              result in the correct result of the CRCs configured
#              WIDTH.
# @value BYTE=2 Calculate the CRC a byte at a time using a
#               pre-calculated table specific to this CRC's
#               definition.
# @value OPTIMIZED=3 Use the most optimized code available for this
#                    CRC's definition.  If there is not a definition
#                    specific optimization, then this is the same as
#                    BYTE.
# @default DEFAULT=0
# @return The CRC-32 CRC.
crc32 = CRC(**{'CRC_NAME':'CRC-32',
               'WIDTH':32,                     # @fixme If WIDTH > 16:
               'POLYNOMIAL':0x04C11DB7L,       # convert to long & 1<<(WIDTH-1)
               'INITIAL_REMAINDER':0xFFFFFFFFL,# convert to long & 1<<(WIDTH-1)
               'FINAL_XOR_VALUE':0xFFFFFFFFL,  # convert to long & 1<<(WIDTH-1)
               'CHECK_VALUE':0xCBF43926L,      # convert to long & 1<<(WIDTH-1)
               'REFLECT_DATA':TRUE,
               'REFLECT_REMAINDER':TRUE
             })
