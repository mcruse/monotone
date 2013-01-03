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
from mpx.lib.node import as_node, as_node_url
from mpx.lib.exceptions import *
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib import deprecated

from _translator import Translator

class SimpleDeadband(Translator):
    def _setup(self):
        if self.activation == self.deactivation:
            raise EConfigurationInvalid(
                "The activation and deactivation values can not be the same."
                )
        if self.activation > self.deactivation:
            self._high = self.activation
            self._low = self.deactivation
            self._high_value = 1
            self._low_value = 0
        else:
            self._high = self.deactivation
            self._low = self.activation
            self._high_value = 0
            self._low_value = 1
        self._in_value = self.intial_in_band
        return
    def _get_using(self, value):
        self._in_value = self.evaluate(value)
        return self._in_value
    def configure(self, config):
        Translator.configure(self, config)
        set_attribute(self, 'activation', REQUIRED, config, float)
        set_attribute(self, 'deactivation', REQUIRED, config, float)
        set_attribute(self, 'intial_in_band', 0, config, int)
        return
    def configuration(self):
        config = Translator.configuration(self)
        get_attribute(self, 'activation', config, str)
        get_attribute(self, 'deactivation', config, str)
        get_attribute(self, 'intial_in_band', config, str)
        return config
    def start(self):
        Translator.start(self)
        self._setup()
        return
    ##
    # @return The deadband's translation as if the last input were
    #         <code>value</code>.
    def evaluate(self, value):
        if value >= self._high:
            return self._high_value
        elif value <= self._low:
            return self._low_value
        return self._in_value
    def get_result(self, skipCache=0, **keywords):
        result = self.ion.get_result(skipCache)
        result.value = self._get_using(result.value)
        return result
    ##
    # @return True (1) if ...
    def get(self, skipCache=0):
        value = self.ion.get(skipCache)
        return self._get_using(value)
    ##
    # Setter/getter for the "threshold" of the deadband, being treated as
    # a (threshold, deadband) pair.  This moves the activation point
    # to the threshold and moves to deativation point to maintain
    # the current separation (aka deadband).
    #
    # @param threshold The value at which the deadband will activate.
    # @default None Do not change the current setting, otherwise update
    #               the current threshold.
    # @return The current (possibly updated) threshold.
    def threshold(self, threshold=None):
        if threshold is None:
            return self.activation
        deadband = self.deadband()
        # Move the activation point the the "threshold."
        self.activation = threshold
        # Now update the deactivation point to maintain the
        # original "deadband" seperation.
        self.deadband(deadband) # This will call _setup().
        return self.activation
    ##
    # Setter/getter for the "deadband" of a deadband, being treated as
    # a (threshold, deadband) pair.  This moves the deactivation point
    # relative to the current activation point.
    #
    # @param deadband The differential below the threshold the value must
    #                 drop before exiting the deadband.
    # @default None Do not change the current setting, otherwise update
    #               the current deadband.
    # @note If <code>deadband</code> is a negative value, then the "direction"
    #       of the deadband is reversed (the value drops "below" the threshold
    #       to activate and raises "above" the threshold + abs(deadband) to
    #       deactivate.
    def deadband(self, deadband=None):
        if deadband is None:
            return (self.activation - self.deactivation)
        self.deactivation = (self.activation - deadband)
        self._setup()
        return (self.activation - self.deactivation)

    #
    # Deprecated methods.  They work as they did, but you really should stop
    # using them.
    #
    
    ##
    # @deprecated
    def from_threshold(self, threshold):
        deprecated("from_threshold() deprecated, use threshold().")
        self.activation = threshold
        self._setup()
        return
    ##
    # @deprecated
    def as_threshold(self):
        deprecated("as_threshold() deprecated, use threshold().")
        return self.activation
    ##
    # @deprecated
    def from_deadband(self, deadband):
        deprecated("from_deadband() deprecated, use deadband().")
        self.deactivation = (self.activation - deadband)
        return
    ##
    # @deprecated
    def as_deadband(self):
        deprecated("as_deadband() deprecated, use deadband().")
        return (self.activation - self.deactivation)
    #
    # Soon to be depricated...  :-)
    # @fixme Convert to the standard getter/setter method.
    #

    ##
    # Set the <code>deactivation</code> value as if the deadband were a
    #         set point + differential pair.
    def from_differential(self, differential):
        self.deactivation = (self.activation + differential)
        return
    ##
    # @return A calculated differential, as if the deadband were a
    #         set point + differential.
    def as_differential(self):
        return (self.deactivation - self.activation)
    ##
    # Set the <code>activation</code> value as if the deadband were a
    #         set point + differential pair.
    def from_setpoint(self, setpoint):
        self.activation = setpoint
        self._setup()
        return
    ##
    # @return The <code>activation</code> value.
    def as_setpoint(self):
        return self.activation
