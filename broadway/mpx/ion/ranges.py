"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
# Common units used by IONs.
#
class Unit:
    V = 'V'
    mV = 'mV'
    mA = 'mA'
    percent = '%'
    ohms = 'Ohms'
    degC = 'C'

##
# Common ranges used by IONs.
#
class Range:
    zero_to_twenty_mA = '0 to 20 mA'
    four_to_twenty_mA = '4 to 20 mA'
    zero_to_ten_V = '0 to 10V'
    pm_10V = '+/- 10 V'
    pm_5V = '+/- 5 V'
    pm_1V = '+/- 1 V'
    pm_500mV = '+/- 500 mV'
    pm_150mV = '+/- 150 mV'
    pm_20mA = '+/- 20 mA'
    plat_0_to_100 = 'Platinum 100, 0C - 100C'
    plat_m_100_to_100 = 'Platinum 100, -100C - 100C'
    plat_0_to_200 = 'Platinum 100, 0C - 200C'
	
    map = {}

    ##
    # Add a new Range
    #
    # @param range  Range object holding new Range.
    #
    def add(range):
        Range.map[range.name] = range

    ##
    # Initialize object.
    #
    # @param name  The name of the range.
    # @param unit  The units for the range.
    # @param min  The minimum value for the range.
    # @parm max  The maximum value for the range.
    #
    def __init__(self, name, unit, min, max):
        self.name = name
        self.unit = unit
        self.min  = min
        self.max  = max

Range.add(Range(Range.zero_to_twenty_mA, Unit.mA, 0.0, 20.0))
Range.add(Range(Range.four_to_twenty_mA, Unit.mA, 4.0, 20.0))
Range.add(Range(Range.zero_to_ten_V, Unit.V, 0.0, 10.0))
Range.add(Range(Range.pm_10V, Unit.V, -10.0, 10.0))
Range.add(Range(Range.pm_5V, Unit.V, -5.0, 5.0))
Range.add(Range(Range.pm_1V, Unit.V, -1.0, 1.0))
Range.add(Range(Range.pm_500mV, Unit.mV, -500.0, 500.0))
Range.add(Range(Range.pm_150mV, Unit.mV, -150.0, 150.0))
Range.add(Range(Range.pm_20mA, Unit.mA, -20.0, 20.0))
Range.add(Range(Range.plat_0_to_100, Unit.degC, 0.0, 100.0))
Range.add(Range(Range.plat_m_100_to_100, Unit.degC, -100.0, 100.0))
Range.add(Range(Range.plat_0_to_200, Unit.degC, 0, 200.0))
