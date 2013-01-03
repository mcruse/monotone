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
# @todo Consider redisigning around an attribute to argument map, much like the
#       Modbus register cache.
# @todo A lot of multipliers should probably become 'constants'.
# @todo Determin why the micro turbine occasionally sends modem interupt
#       strings ('+++').
# @todo What does RFC mean?
# @todo What does DPC mean?
# @todo Find a better name for multiline format.
# @todo Stub all commands and then implement them.
# @todo Add generic handling of error resonses and raise an appropriate
#       exception.
# @todo Consider making response a package and splitting the responses into
#       logical groups.
import types
import array
import string

from mpx.lib.exceptions import EInvalidResponse

from mpx.ion.capstone.micro_turbine.lib import *

PROMPT_MAP = {'USR>':BASEUSER,
              'MNT>':BASEMAINTENANCE,
              'USRPRT>':PROTECTEDUSER,
              'MNTPRT>':PROTECTEDMAINTENANCE,
              'USRADM>':PROTECTEDUSER,
              'MNTADM>':PROTECTEDMAINTENANCE}
PROMPTS = PROMPT_MAP.keys()

##
# @param line A whitespace trimmed string that represents a
#             line of response data.
# @return True if <code>line</code> matches a known prompt,
#         otherwise false.
def is_prompt(line):
    return line in PROMPTS

##
# @param line A whitespace trimmed string that represents a
#             line of response data.
# @return An instance of a {@link mpx.ion.capstone.lib.PromptType PromptType}
#         describing the prompt.  None is returned if <code>line</code> is
#         not a valid Capston MicroTurbine prompt.
def prompt_type(line):
    if PROMPT_MAP.has_key(line):
        return PROMPT_MAP[line]
    return None

##
# Validates a single 'packet' and returns it as a string.
# @note Packets are defined by an envelope in the form of
#       SOH + count + text + CRC + EOT.  It seems that every line is
#       sent in its own packet and the implementation take advantage
#       of that behavior.
# @return A string that is the textual portion of the packet.
def trim_and_validate(packet):
    if type(packet) == array.ArrayType:
        packet = array.array('c', packet.tostring())
    else:
        packet = array.array('c', packet)
    soh = packet.pop(0)
    cnt = packet.pop(0)
    eot = packet.pop()
    if soh != SOH:
        raise EInvalidResponse, "SOH"
    if eot != EOT:
        raise EInvalidResponse, "EOT"
    if ord(cnt) != (len(packet) - 2): # Ignore CRC
        raise EInvalidResponse, "len"
    if calc_crc(packet):
        raise EInvalidResponse, "crc"
    # Toss the CRC.
    packet.pop()
    packet.pop()
    while len(packet) and packet[-1] in string.whitespace: # Trim whitespace.
        packet.pop()
    while len(packet) and packet[0] in string.whitespace: # Trim whitespace.
        packet.pop(0)
    return packet.tostring()

##
# Base class for all Capstone MicroTurbine command responses.
class Response:
    ##
    # Instanciate a generic capstone response handler.
    # @param rsp An optional response to parse.
    # @default None
    # @fixme Support an array buffer as well is a list of lines.
    def __init__(self, rsp=None):
        ##
        # The turbine that received the command.
        self._turbine = None
        ##
        # The command the turbine received.
        self._command = None
        ##
        # The list of response arguments.
        self._args = []
        if rsp:
            ##
            # The command response, saved as a list of lines (strings)
            # with whitespace trimed from both ends.
            self._response = rsp
            self.extract(self._response)
    ##
    # Reads a single 'packet' from a port and returns its textual contents as
    # a string.
    # @note Packets are defined by an envelope in the form of
    #       SOH + count + text + CRC + EOT.  It seems that every line is
    #       sent in its own packet and the implementation take advantage
    #       of that behavior.
    # @return A string that is the textual portion of the packet.
    def get_packet(self, port, timeout=1.0):
        a = array.array('c')
        port.read_upto(a,SOH,timeout)
        packet = array.array('c', SOH)
        port.read(packet,1,timeout)
        cnt = ord(packet[1]) + 3 # CRC + EOT
        port.read(packet,cnt,timeout)
        return trim_and_validate(packet)
    ##
    # Extract the response as a generic Capstone response.
    # @note Makes assumptions that multi line responses are
    #       generic.  This is not true for HELPME.
    # @note This method can <b>not</b> detect cases where a single line
    #       response is formatted like a multi line response.  That's
    #       one of the reasons for sub-classing the response handlers.
    def extract(self, rsp=None):
        if not rsp:
            rsp = self._response
        else:
            if type(rsp) != types.ListType and \
               type(rsp) != types.TupleType:
                rsp = (rsp,)
        if len(rsp) > 1:
            return self.ml_extract(rsp)
        args = string.split(rsp[0],',')
        self._command = args[0]
        if len(args) > 1:
            self._args = []
            arg = string.split(args[1],'=')
            self._turbine = int(arg[0])
            self._args.append(arg[1])
            for i in range(2,len(args)):
                self._args.append(args[i])
    ##
    # Extract the response using the generic multi-line syntax.
    def ml_extract(self, rsp=None):
        if not rsp:
            rsp = self._response
        self._args = []
        for line in rsp:
            args = string.split(line,',')
            if len(args) >= 3:
                self._command = args[0]
                arg = string.split(args[1],'=')
                self._turbine = int(arg[0])
                first = int(arg[1])
                length = first + int(args[2])
                for i in range(3,len(args)):
                    self._args.append(args[i].rstrip())
    ##
    # Receive a response from the port and <code>extract</code> the response's
    # arguments.
    def receive(self, port, timeout=1.0):
        self._response = []
        while 1:
            line = self.get_packet(port,timeout)
            if is_prompt(line):
                self._pt = prompt_type(line)
                break
            self._response.append(line)
        self.extract()
    ##
    # Returns the type of prompt that terminated the response.
    # @note Only valid after the <code>Response</code> has
    #       <code>receive()</code>d its response.
    # @return A mpx.ion.capstone.micro_turbine.lib.PromptType
    # @value {@link mpx.ion.capstone.micro_turbine.lib.BASEUSER BASEUSER}
    # @value {@link mpx.ion.capstone.micro_turbine.lib.BASEMAINTENANCE BASEMAINTENANCE}
    # @value {@link mpx.ion.capstone.micro_turbine.lib.PROTECTEDUSER PROTECTEDUSER}
    # @value {@link mpx.ion.capstone.micro_turbine.lib.PROTECTEDMAINTENANCE PROTECTEDMAINTENANCE}
    def prompt_type(self):
        return self._pt
    ##
    # Returns the response's command string.
    def command(self):
        return self._command
    ##
    # Returns the response's turbine index.
    def turbine(self):
        return self._turbine
    ##
    # Returns the response's argument list.
    def argv(self):
        return self._args
    ##
    # Returns the response's argument count.
    def argc(self):
        return len(self._args)
    ##
    # Returns a response's argument by index.
    def arg(self,i):
        return self._args[i]

class MultilineResponse(Response):
    ##
    # Force extraction using the generic multi-line syntax.
    def extract(self, rsp=None):
        self.ml_extract(rsp)

##
# The response handler for the Capstone MicroTurbine ALLDAT command.
# The ALLDAT command is a special command that returns a 'batched'
# response from several commands.
# @see #BATDAT
# @see #BCDAT1
# @see #CTRLDT
# @see #ENGDT1
# @see #ENGDT2
# @see #GENDT1
# @see #GENDT2
# @see #INVDT1
# @see #INVDT2
# @see #LFCDAT
# @see #MLOCKD
# @see #RFCDAT
# @see #SPVDAT
class ALLDAT(MultilineResponse):
    ##
    # Instanciate the Capstone MicroTurbine ALLDAT command.
    # @see #MultilineResponse.__init__
    def __init__(self, rsp=None):
        ##
        # Maps sub-commands to response lines.
        self._line_map = {}
        ##
        # Maps sub-commands to response objects.
        self._response_map = {}
        MultilineResponse.__init__(self,rsp)
    ##
    # Extracts the ALLDATA 'sub-commands' to a cache of
    # response lines, indexed by the sub-command.
    def ml_extract(self, rsp=None):
        if not rsp:
            rsp = self._response
        self.command = 'ALLDAT'
        self._line_map = {}
        self._response_map = {}
        for line in rsp:
            args = string.split(line,',')
            command = args[0]
            if not self._line_map.has_key(command):
                self._line_map[command] = []
            self._line_map[command].append(line)
    ##
    # Get the sub-command's response instance, creating it if it
    # does not exist.
    def _get_response(self, sub_cmd):
        if not self._response_map.has_key(sub_cmd):
            response_class = eval(sub_cmd)
            response = response_class(self._line_map[sub_cmd])
            self._response_map[sub_cmd] = response
        return self._response_map[sub_cmd]
    ##
    # Return the response instance to the 'BATDAT' sub-command.
    # @note This command is proprietary and therefore no arguments are
    #       interpreted.
    def batdat_response(self):
        return self._get_response('BATDAT')
    ##
    # Return the response instance to the 'BCDAT1' sub-command.
    def bcdat1_response(self):
        return self._get_response('BCDAT1')
    ##
    # Return the response instance to the 'CTRLDT' sub-command.
    def ctrldt_response(self):
        return self._get_response('CTRLDT')
    ##
    # Return the response instance to the 'ENGDT1' sub-command.
    def engdt1_response(self):
        return self._get_response('ENGDT1')
    ##
    # Return the response instance to the 'ENGDT2' sub-command.
    def engdt2_response(self):
        return self._get_response('ENGDT2')
    ##
    # Return the response instance to the 'GENDT1' sub-command.
    def gendt1_response(self):
        return self._get_response('GENDT1')
    ##
    # Return the response instance to the 'GENDT2' sub-command.
    def gendt2_response(self):
        return self.get_response('GENDT2')
    ##
    # Return the response instance to the 'INVDT1' sub-command.
    def invdt1_response(self):
        return self._get_response('INVDT1')
    ##
    # Return the response instance to the 'INVDT2' sub-command.
    def invdt2_response(self):
        return self._get_response('INVDT2')
    ##
    # Return the response instance to the 'LFCDAT' sub-command.
    # @note This command is proprietary and therefore no arguments are
    #       interpreted.
    def lfcdat_response(self):
        return self._get_response('LFCDAT')
    ##
    # Return the response instance to the 'MLOCKD' sub-command.
    # @note This command is proprietary and therefore no arguments are
    #       interpreted.
    def mlockd_response(self):
        return self._get_response('MLOCKD')
    ##
    # Return the response instance to the 'RFCDAT' sub-command.
    def rfcdat_response(self):
        return self._get_response('RFCDAT')
    ##
    # Return the response instance to the 'SPVDAT' sub-command.
    def spvdat_response(self):
        return self._get_response('SPVDAT')

##
# The response handler for the Capstone MicroTurbine AUTRST command.
class AUTRST(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing the turbine's auto-restart state.
    # @value 0 Auto-restart disabled.
    # @value 1 Auto-restart enabled.
    def auto_restart(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)

##
# The response handler for the Capstone MicroTurbine BATDAT command.
# @todo Try to get proprieetary spec.
class BATDAT(MultilineResponse):
    pass

##
# The response handler for the Capstone MicroTurbine BCDAT1 command.
class BCDAT1(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The battery temperature.
    def battery_temperature(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return from_sh(value)

##
# The response handler for the Capstone MicroTurbine CTRLDT command.
# @note More values are returned than documented.
class CTRLDT(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current system configuration state as an int.
    # @fixme Split into to commands as per tables 32 and 34.
    def system_configuration_state(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The power enable state as an int.
    # @value 0 disabled
    # @value 1 enabled
    def power_enable(self,raw=0):
        value = self.arg(2)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing the power demand in Watts.
    def power_demand(self,raw=0):
        value = self.arg(7)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the power supply in volts.
    def power_supply(self,raw=0):
        value = self.arg(8)
        if raw:
            return value
        return from_h(value) / 16.0
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The start command state as an int.
    # @value 0 Off
    # @value 1 Running
    def start_command(self,raw=0):
        value = self.arg(9)
        if raw:
            return value
        return from_h(value)

##
# The response handler for the Capstone MicroTurbine CMPINT command.
class CMPINT(Response):
    pass

##
# The response handler for the Capstone MicroTurbine ENGDT1 command.
class ENGDT1(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current year as an int.
    def year(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current month as an int.
    def month(self,raw=0):
        value = self.arg(1)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current day as an int.
    def day(self,raw=0):
        value = self.arg(2)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current hour as an int.
    def hour(self,raw=0):
        value = self.arg(3)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current minutes as an int.
    def minutes(self,raw=0):
        value = self.arg(4)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current seconds as an int.
    def seconds(self,raw=0):
        value = self.arg(5)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return The current engine RPM as an int.
    def engine_rpm(self,raw=0):
        value = self.arg(6)
        if raw:
            return value
        return from_h(value) * 2
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float that is the TET average in degrees F.
    # @fixme Determine if the unit is affected by configuration.
    def tet_average(self,raw=0):
        value = self.arg(10)
        if raw:
            return value
        return from_sh(value) / 8.0
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float that is the compressor inlet temperature in degrees F.
    # @fixme Determine if the unit is affected by configuration.
    def compressor_inlet_temp(self,raw=0):
        value = self.arg(11)
        if raw:
            return value
        return from_sh(value) / 8.0
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float that is the ambient pressure in psia.
    # @fixme Determine if the unit is affected by configuration.
    def ambient_pressure(self,raw=0):
        value = self.arg(15)
        if raw:
            return value
        return from_sh(value) / 4096.0

##
# The response handler for the Capstone MicroTurbine ENGDT2 command.
class ENGDT2(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int that is the current fault number.
    # @todo Document fault numbers.
    def fault_ident(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return from_h(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int that is the current system severit level.
    # @todo Document system severity levels as per table 33.
    def system_severity_level(self,raw=0):
        value = self.arg(10)
        if raw:
            return value
        return from_h(value)

##
# The response handler for the Capstone MicroTurbine GENDT1 command.
# @todo Try to get proprietary spec.
class GENDT1(MultilineResponse):
    pass

##
# The response handler for the Capstone MicroTurbine GENDT2 command.
# @todo Try to get proprietary spec.
class GENDT2(MultilineResponse):
    pass

##
# The response handler for the Capstone MicroTurbine INVDT1 command.
class INVDT1(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the AC frequency in Hz.
    def ac_frequency(self,raw=0):
        value = self.arg(3)
        if raw:
            return value
        return from_h(value) / 16.0
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase A current RMS in Amps.
    # @fixme Verify the multiplier, it seems strange at ~ 1/54.6133
    def phase_A_current_rms(self,raw=0):
        value = self.arg(7)
        if raw:
            return value
        return from_h(value) * 1.8310547e-2
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase B current RMS in Amps.
    # @fixme Verify the multiplier, it seems strange at ~ 1/54.6133
    def phase_B_current_rms(self,raw=0):
        value = self.arg(8)
        if raw:
            return value
        return from_h(value) * 1.8310547e-2
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase C current RMS in Amps.
    # @fixme Verify the multiplier, it seems strange at ~ 1/54.6133
    def phase_C_current_rms(self,raw=0):
        value = self.arg(9)
        if raw:
            return value
        return from_h(value) * 1.8310547e-2

##
# The response handler for the Capstone MicroTurbine INVDT2 command.
class INVDT2(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the neutral current RMS in Amps.
    # @fixme Verify the multiplier, it seems strange at ~ 1/54.6133
    def neutral_current_rms(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return from_h(value) * 1.8310547e-2
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase A-N RMS in volts.
    # @fixme Verify the multiplier, it seems strange at ~ 1/54.6133
    def phase_AN_voltage_rms(self,raw=0):
        value = self.arg(1)
        if raw:
            return value
        return from_h(value) * 1.8310547e-2
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase B-N RMS in volts.
    # @fixme Verify the multiplier, it seems strange at ~ 1/54.6133
    def phase_BN_voltage_rms(self,raw=0):
        value = self.arg(3)
        if raw:
            return value
        return from_h(value) * 1.8310547e-2
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase C-N RMS in volts.
    # @fixme Verify the multiplier, it seems strange at ~ 1/54.6133
    def phase_CN_voltage_rms(self,raw=0):
        value = self.arg(3)
        if raw:
            return value
        return from_h(value) * 1.8310547e-2
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase A power average in Watts.
    # @fixme Verify the multiplier, it seems strange at 2.7465820
    # @fixme Value looks signed, although the documentation says it isn't.
    def phase_A_power_average(self,raw=0):
        value = self.arg(4)
        if raw:
            return value
        return from_h(value) * 2.7465820
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase B power average in Watts.
    # @fixme Verify the multiplier, it seems strange at 2.7465820
    # @fixme Value looks signed, although the documentation says it isn't.
    def phase_B_power_average(self,raw=0):
        value = self.arg(5)
        if raw:
            return value
        return from_h(value) * 2.7465820
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the phase B power average in Watts.
    # @fixme Verify the multiplier, it seems strange at 2.7465820
    # @fixme Value looks signed, although the documentation says it isn't.
    def phase_C_power_average(self,raw=0):
        value = self.arg(6)
        if raw:
            return value
        return from_h(value) * 2.7465820
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the total power average in Watts.
    # @fixme Verify the multiplier, it seems strange at 5.4931641.
    def total_power_average(self,raw=0):
        value = self.arg(7)
        if raw:
            return value
        return from_h(value) * 5.4931641

##
# The response handler for the Capstone MicroTurbine INVOIA command.
class INVOIA(Response):
    pass

##
# The response handler for the Capstone MicroTurbine INVOIB command.
class INVOIB(Response):
    pass

##
# The response handler for the Capstone MicroTurbine INVOIC command.
class INVOIC(Response):
    pass

##
# The response handler for the Capstone MicroTurbine INVOVA command.
class INVOVA(Response):
    pass

##
# The response handler for the Capstone MicroTurbine INVOVB command.
class INVOVB(Response):
    pass

##
# The response handler for the Capstone MicroTurbine INVOVC command.
class INVOVC(Response):
    pass

##
# The response handler for the Capstone MicroTurbine INVPWR command.
class INVPWR(Response):
    pass

##
# The response handler for the Capstone MicroTurbine LFCDAT command.
# @todo Try to get specification for this proprietary command.
class LFCDAT(MultilineResponse):
    pass

##
# The response handler for the Capstone MicroTurbine LMDATA command.
# @fixme Map the arguments to names.
class LMDATA(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing the run/stop signal.
    def run_stop_signal(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the positive power.
    def positive_power(self,raw=0):
        value = self.arg(1)
        if raw:
            return value
        return float(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the negative power.
    def negative_power(self,raw=0):
        value = self.arg(2)
        if raw:
            return value
        return float(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the positive kvars.
    def positive_kvars(self,raw=0):
        value = self.arg(3)
        if raw:
            return value
        return float(value)
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the negative kvars.
    def negative_kvars(self,raw=0):
        value = self.arg(4)
        if raw:
            return value
        return float(value)

##
# The response handler for the Capstone MicroTurbine LMMODE command.
class LMMODE(Response):
    pass

##
# The response handler for the Capstone MicroTurbine LMRPFP command.
class LMRPFP(Response):
    pass

##
# The response handler for the Capstone MicroTurbine LMUTPW command.
class LMUTPW(Response):
    pass

##
# The response handler for the Capstone MicroTurbine LOGOFF command.
class LOGOFF(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing whether the password level was reset.
    # @fixme Implemented as per the user comminucation spec, but reset()
    #        seems to always return 0.
    def reset(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)

##
# The response handler for the Capstone MicroTurbine MEDBTU command.
class MEDBTU(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing the turbine's medium BTU operating mode.
    # @value 0 Normal BTU operating mode.
    # @value 1 Medium BTU operating mode.
    # @value 2 Low BTU operating mode.
    def mode(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)

##
# The response handler for the Capstone MicroTurbine MLOCKD command.
# @todo Try to get proprietary spec.
class MLOCKD(MultilineResponse):
    pass

##
# The response handler for the Capstone MicroTurbine PSSWRD command.
class PSSWRD(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A string representing the password mode.
    # @value 'BASE'
    # @value 'PROTECT'
    def mode(self,raw=0):
        value = self.arg(0)
        return value
    ##
    # @return True if the turbine is in base password mode.
    def is_base(self):
        return not self.is_protect()
    ##
    # @return True if the turbine is in protect password mode.
    def is_protect(self):
        return self.mode() == 'PROTECT'

##
# The response handler for the Capstone MicroTurbine RFCDAT command.
class RFCDAT(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the RFC fuel inlet pressure in psig.
    def rfc_fuel_inlet_pressure(self,raw=0):
        value = self.arg(2)
        if raw:
            return value
        return from_h(value) / 16.0

##
# The response handler for the Capstone MicroTurbine SPVDAT command.
class SPVDAT(MultilineResponse):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return A float representing the RFC fuel inlet pressure in psig.
    def fuel_inlet_pressure(self,raw=0):
        value = self.arg(1)
        if raw:
            return value
        return from_h(value) / 16.0

##
# The response handler for the Capstone MicroTurbine STRCMD command.
class STRCMD(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing whether the turbine will start.
    def will_start(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)

##
# The response handler for the Capstone MicroTurbine SYSMOD command.
class SYSMOD(Response):
    pass

##
# The response handler for the Capstone MicroTurbine SYSSSL command.
class SYSSSL(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing the system severity level.
    def system_severity_level(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)

##
# The response handler for the Capstone MicroTurbine SYSSTA command.
class SYSSTA(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing the system severity level.
    def current_system_state_string(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return value

##
# The response handler for the Capstone MicroTurbine TETAVG command.
class TETAVG(Response):
    pass

##
# The response handler for the Capstone MicroTurbine TURBNO command.
class TURBNO(Response):
    pass

##
# The response handler for the Capstone MicroTurbine USRSTR command.
class USRSTR(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing whether the turbine can start.
    def can_start(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)

class UTLCON(Response):
    ##
    # @param raw If true, then the uninterpretted command string
    #            is returned.
    # @default 0
    # @return An int representing the turbine's utility connection number.
    # @value 0 Invalid utility connection value.
    # @value 1 Stand alone utility connection value.
    # @value 2 Grid connect utility connection value.
    # @value 3 Dual mode utility connection value.
    def utility_connection_value(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return int(value)

##
# The response handler for the Capstone MicroTurbine WARNTY command.
class WARNTY(Response):
    ##
    # Return WARNTY arg_0
    # @fixme Map to sensible name...
    def arg_0(self,raw=0):
        value = self.arg(0)
        if raw:
            return value
        return value
    ##
    # Return the hour of operation for the turbine.
    # @return A string in the format 'HH:MM:SS'.
    def hours_of_operation(self,raw=0):
        value = self.arg(1)
        if raw:
            return value
        return value
    ##
    # Return the number of start events for the turbine.
    # @return An int representing the number of start events.
    def start_events(self,raw=0):
        value = self.arg(2)
        if raw:
            return value
        return int(value)
    ##
    # Return WARNTY arg_3
    # @fixme Map to sensible name...
    def arg_3(self,raw=0):
        value = self.arg(3)
        if raw:
            return value
        return value
    ##
    # Return WARNTY arg_4
    # @fixme Map to sensible name...
    def arg_4(self,raw=0):
        value = self.arg(4)
        if raw:
            return value
        return value
