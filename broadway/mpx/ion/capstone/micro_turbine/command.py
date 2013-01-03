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
# @todo Stub all commands and then implement them.
# @todo Validate WFRAMP
# @fixme Determin if there is a password mode above PROTECT, or if there
#        is an operational difference between the user port and
#        maintanance port regarding command availability.
# @todo Consider making response a package and splitting the responses into
#       logical groups.

import array
import types

from mpx.lib.exceptions import EInvalidValue
from mpx.ion.capstone.micro_turbine import response
from mpx.ion.capstone.micro_turbine.lib import *

def convert_argument(name, value, dict, converter=None):
    try:
        value = converter(value)
        return value
    except:
        pass
    try:
        if type(value) is types.StringType:
            value = value.lower()
        return dict[value]
    except:
        pass
    raise EInvalidValue, (name, value)

class Message:
    ##
    # Instanciate a Capstone MicroTurbine command.
    # @param cmd The six character command.
    # @param turbine The index of the turbine targetted for the command.
    # @param *args The list of command specific arguments.
    def __init__(self, cmd, turbine=None, *args):
        if len(cmd) != 6:
            raise EInvalidValue, ('command', cmd)
        ##
        # The turbine to send the command.
        self._turbine = None
        ##
        # The command for the turbine.
        self._command = None
        ##
        # The list of the command's arguments.
        self._args = []
        ##
        # The Capstone MicroTurbine command, built as a character array.
        self._array = None
        _args = [cmd, turbine]
        # Copy *args tuple into a new list so we can modify them.
        args_clone = []
        args_clone.extend(args)
        args = args_clone
        # Only apply *args if they are not all None.  This allows
        # passing None as an optional argument.
        extend = 0
        for n in range(0,len(args)):
            arg = args[n]
            if arg != None:
                extend = 1   # There is a non-None value in the list, use *args.
            else:
                args[n] = '' # Use an empty argument.
        if extend:
            _args.extend(args)
        apply(self.set_cmd, _args)
        return
    ##
    # Send the command on a serial <code>port</code>.
    # @param port The port to use when sending the command.
    def send(self, port):
        port.write(self.toarray())
    ##
    # Initialize the command.
    # @param cmd The six character command.
    # @param turbine The index of the turbine targetted for the command.
    # @param *args The list of command specific arguments.
    # @note This method assumes that the argument list <code>*args</code>
    #       is literally correct.
    def set_cmd(self, cmd, turbine=None, *args):
        self._command = cmd
        if turbine != None:
            turbine = convert_argument('turbine', turbine, None, int)
        self._turbine = turbine
        self._args = []
        for arg in args:
            self._args.append(arg)
        self._array = None
        return
    ##
    # @return A string that represents the command.
    def command(self):
        return self._command
    ##
    # @return An int that represents the turbine index.
    def turbine(self):
        return self._turbine
    ##
    # @return The command's argument list.
    def argv(self):
        return self._args
    ##
    # @return The command's argument count as an int.
    def argc(self):
        return len(self._args)
    ##
    # @param i The argument index.
    # @return A string that represents the indexed argument.
    def arg(self,i):
        return self._args[i]
    ##
    # @return A string representing this command converted into a valid
    #         Capstone MicroTurbine command.
    def tostring(self):
        return self.toarray().tostring()
    ##
    # @return An array.array('c') representing this command converted into a
    #         valid Capstone MicroTurbine command.
    def toarray(self):
        if not self._array:
            b = array.array('c')
            b.fromstring(self._command)
            if self._turbine == 0 or self._turbine:
                b.fromstring(',')
                b.fromstring(str(self._turbine))
            if self._args:
                initial = 1
                b.fromstring('=')
                for arg in self._args:
                    if not initial:
                        b.fromstring(',')
                    else:
                        initial = 0
                    b.fromstring(str(arg))
            msg_len = len(b)
            append_crc(b)
            self._array = array.array('c')
            self._array.fromstring(SOH)
            self._array.fromstring(chr(msg_len))
            self._array.extend(b)
            self._array.fromstring(EOT)
        return self._array
    ##
    # @return The class to instanciate to receive the response to this command.
    def response_factory(self):
        return response.Response()

##
# Handler for the ALLDAT Capstone MicroTurbine command.
class ALLDAT(Message):
    ##
    # Instanciate an ALLDAT Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'ALLDAT',turbine)
    ##
    # @return The response handler class for the ALLDAT command.
    # @see Message#response_factory
    def response_factory(self):
        return response.ALLDAT()

##
# Handler for the AUTRST Capstone MicroTurbine command.
class AUTRST(Message):
    ##
    # Instanciate an AUTRST Capstone MicroTurbine command.
    # @param turbine Turbine number.
    # @param auto_restart Specifies whether auto-restart is enabled.
    # @value 0,'off' Disable auto-restart.
    # @value 1,'on' Enable auto-restart.
    def __init__(self,turbine=None,auto_restart=None):
        if auto_restart != None:
            auto_restart = convert_argument('auto_restart', auto_restart,
                                         {'off':0, 'on':1,
                                          'no':0, 'yes':1,
                                          'false':0, 'true':1}, int)
            if not auto_restart in (0,1):
                raise EInvalidValue, ('auto_restart', auto_restart)
        Message.__init__(self,'AUTRST',turbine,auto_restart)
    ##
    # @return The response handler class for the AUTRST command.
    # @see Message#response_factory
    def response_factory(self):
        return response.AUTRST()

##
# Handler for the BATDAT Capstone MicroTurbine command.
# @todo Try to get proprietary spec.
class BATDAT(Message):
    ##
    # Instanciate an BATDAT Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'BATDAT',turbine)
    ##
    # @return The response handler class for the BATDAT command.
    # @see Message#response_factory
    def response_factory(self):
        return response.BATDAT()

##
# Handler for the BCDAT1 Capstone MicroTurbine command.
class BCDAT1(Message):
    ##
    # Instanciate an BCDAT1 Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'BCDAT1',turbine)
    ##
    # @return The response handler class for the BCDAT1 command.
    # @see Message#response_factory
    def response_factory(self):
        return response.BCDAT1()

##
# Handler for the CTRLDT Capstone MicroTurbine command.
class CTRLDT(Message):
    ##
    # Instanciate an CTRLDT Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'CTRLDT',turbine)
    ##
    # @return The response handler class for the CTRLDT command.
    # @see Message#response_factory
    def response_factory(self):
        return response.CTRLDT()

##
# Handler for the CMPINT Capstone MicroTurbine command.
class CMPINT(Message):
    ##
    # Instanciate an CMPINT Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'CMPINT',turbine)
    ##
    # @return The response handler class for the CMPINT command.
    # @see Message#response_factory
    def response_factory(self):
        return response.CMPINT()

##
# Handler for the ENGDT1 Capstone MicroTurbine command.
class ENGDT1(Message):
    ##
    # Instanciate an ENGDT1 Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'ENGDT1',turbine)
    ##
    # @return The response handler class for the ENGDT1 command.
    # @see Message#response_factory
    def response_factory(self):
        return response.ENGDT1()

##
# Handler for the ENGDT2 Capstone MicroTurbine command.
class ENGDT2(Message):
    ##
    # Instanciate an ENGDT2 Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'ENGDT2',turbine)
    ##
    # @return The response handler class for the ENGDT2 command.
    # @see Message#response_factory
    def response_factory(self):
        return response.ENGDT2()

##
# Handler for the GENDT1 Capstone MicroTurbine command.
# @todo Try to get proprietary spec.
class GENDT1(Message):
    ##
    # Instanciate an GENDT1 Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'GENDT1',turbine)
    ##
    # @return The response handler class for the GENDT1 command.
    # @see Message#response_factory
    def response_factory(self):
        return response.GENDT1()

##
# Handler for the GENDT2 Capstone MicroTurbine command.
# @todo Try to get proprietary spec.
class GENDT2(Message):
    ##
    # Instanciate an GENDT2 Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'GENDT2',turbine)
    ##
    # @return The response handler class for the GENDT2 command.
    # @see Message#response_factory
    def response_factory(self):
        return response.GENDT2()

##
# Handler for the INVDT1 Capstone MicroTurbine command.
class INVDT1(Message):
    ##
    # Instanciate an INVDT1 Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVDT1',turbine)
    ##
    # @return The response handler class for the INVDT1 command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVDT1()

##
# Handler for the INVDT2 Capstone MicroTurbine command.
class INVDT2(Message):
    ##
    # Instanciate an INVDT2 Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVDT2',turbine)
    ##
    # @return The response handler class for the INVDT2 command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVDT2()

##
# Handler for the INVOIA Capstone MicroTurbine command.
class INVOIA(Message):
    ##
    # Instanciate an INVOIA Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVOIA',turbine)
    ##
    # @return The response handler class for the INVOIA command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVOIA()

##
# Handler for the INVOIB Capstone MicroTurbine command.
class INVOIB(Message):
    ##
    # Instanciate an INVOIB Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVOIB',turbine)
    ##
    # @return The response handler class for the INVOIB command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVOIB()

##
# Handler for the INVOIC Capstone MicroTurbine command.
class INVOIC(Message):
    ##
    # Instanciate an INVOIC Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVOIC',turbine)
    ##
    # @return The response handler class for the INVOIC command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVOIC()

##
# Handler for the INVOVA Capstone MicroTurbine command.
class INVOVA(Message):
    ##
    # Instanciate an INVOVA Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVOVA',turbine)
    ##
    # @return The response handler class for the INVOVA command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVOVA()

##
# Handler for the INVOVB Capstone MicroTurbine command.
class INVOVB(Message):
    ##
    # Instanciate an INVOVB Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVOVB',turbine)
    ##
    # @return The response handler class for the INVOVB command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVOVB()

##
# Handler for the INVOVC Capstone MicroTurbine command.
class INVOVC(Message):
    ##
    # Instanciate an INVOVC Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVOVC',turbine)
    ##
    # @return The response handler class for the INVOVC command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVOVC()

##
# Handler for the INVPWR Capstone MicroTurbine command.
class INVPWR(Message):
    ##
    # Instanciate an INVPWR Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'INVPWR',turbine)
    ##
    # @return The response handler class for the INVPWR command.
    # @see Message#response_factory
    def response_factory(self):
        return response.INVPWR()

##
# Handler for the LFCDAT Capstone MicroTurbine command.
class LFCDAT(Message):
    ##
    # Instanciate an LFCDAT Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'LFCDAT',turbine)
    ##
    # @return The response handler class for the LFCDAT command.
    # @see Message#response_factory
    def response_factory(self):
        return response.LFCDAT()

##
# Handler for the LMDATA Capstone MicroTurbine command.
class LMDATA(Message):
    ##
    # Instanciate an LMDATA Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'LMDATA',turbine)
    ##
    # @return The response handler class for the LMDATA command.
    # @see Message#response_factory
    def response_factory(self):
        return response.LMDATA()

##
# Handler for the LMMODE Capstone MicroTurbine command.
class LMMODE(Message):
    ##
    # Instanciate an LMMODE Capstone MicroTurbine command.
    def __init__(self,turbine=None,mode=None):
        if mode != None:
            mode = convert_argument('mode',mode,
                                    {'disabled':0,
                                     'peak shaving':1,
                                     'load following':2},int)
            if not mode in (0,1,2):
                raise EInvalidValue, ('mode', mode)
        Message.__init__(self,'LMMODE',turbine,mode)
    ##
    # @return The response handler class for the LMMODE command.
    # @see Message#response_factory
    def response_factory(self):
        return response.LMMODE()

##
# Handler for the LMRPFP Capstone MicroTurbine command.
class LMRPFP(Message):
    ##
    # Instanciate an LMRPFP Capstone MicroTurbine command.
    def __init__(self,turbine=None,val=None):
        if val != None:
            val = convert_argument('val', val, {'false':0, 'true':1}, int)
            if not val in (0,1):
                raise EInvalidValue, ('val', val)
        Message.__init__(self,'LMRPFP',turbine,val)
    ##
    # @return The response handler class for the LMRPFP command.
    # @see Message#response_factory
    def response_factory(self):
        return response.LMRPFP()

##
# Handler for the LMUTPW Capstone MicroTurbine command.
class LMUTPW(Message):
    ##
    # Instanciate an LMUTPW Capstone MicroTurbine command.
    def __init__(self,turbine=None,kw=None):
        if kw != None:
            kw = convert_argument('kw', kw, None, float)
        Message.__init__(self,'LMUTPW',turbine,kw)
    ##
    # @return The response handler class for the LMUTPW command.
    # @see Message#response_factory
    def response_factory(self):
        return response.LMUTPW()

##
# Handler for the LOGGOFF Capstone MicroTurbine command.
class LOGOFF(Message):
    ##
    # Instanciate an LOGOFF Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'LOGOFF',turbine)
    ##
    # @return The response handler class for the LOGOFF command.
    # @see Message#response_factory
    def response_factory(self):
        return response.LOGOFF()

##
# Handler for the MEDBTU Capstone MicroTurbine command.
# @todo Try to get proprietary spec.
class MEDBTU(Message):
    ##
    # Instanciate a MEDBTU Capstone MicroTurbine command.
    # @param turbine Turbine number.
    # @param mode Specifies the medium BTU operating mode.
    # @value 0,'normal' Normal BTU operating mode.
    # @value 1,'medium btu' Medium BTU operating mode.
    # @value 2,'low btu' Low BTU operating mode.
    def __init__(self,turbine=None,mode=None):
        if mode != None:
            mode = convert_argument('mode', mode,
                                         {'normal btu':0,
                                          'normal':0,
                                          'medium btu':1,
                                          'medium':1,
                                          'low btu':2,
                                          'low':2}, int)
            if not mode in (0,1,2):
                raise EInvalidValue, ('mode', mode)
        Message.__init__(self,'MEDBTU',turbine,mode)
    ##
    # @return The response handler class for the MEDBTU command.
    # @see Message#response_factory
    def response_factory(self):
        return response.MEDBTU()

##
# Handler for the MLOCKD Capstone MicroTurbine command.
# @todo Try to get proprietary spec.
class MLOCKD(Message):
    ##
    # @return The response handler class for the MLOCKD command.
    # @see Message#response_factory
    def response_factory(self):
        return response.MLOCKD()

##
# Handler for the PSSWRD Capstone MicroTurbine command.
class PSSWRD(Message):
    ##
    # Instanciate an PSSWRD Capstone MicroTurbine command.
    def __init__(self,turbine=None,password=None):
        if password != None:
            if type(password) != types.StringType:
                raise EInvalidValue, ('password', password)
        Message.__init__(self,'PSSWRD',turbine,password)
    ##
    # @return The response handler class for the PSSWRD command.
    # @see Message#response_factory
    def response_factory(self):
        return response.PSSWRD()

##
# Handler for the RFCDAT Capstone MicroTurbine command.
class RFCDAT(Message):
    ##
    # Instanciate an RFCDAT Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'RFCDAT',turbine)
    ##
    # @return The response handler class for the RFCDAT command.
    # @see Message#response_factory
    def response_factory(self):
        return response.RFCDAT()

##
# Handler for the SPVDAT Capstone MicroTurbine command.
class SPVDAT(Message):
    ##
    # Instanciate an SPVDAT Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'SPVDAT',turbine)
    ##
    # @return The response handler class for the SPVDAT command.
    # @see Message#response_factory
    def response_factory(self):
        return response.SPVDAT()

##
# Handler for the STRCMD Capstone MicroTurbine command.
class STRCMD(Message):
    ##
    # Instanciate an STRCMD Capstone MicroTurbine command.
    # @param start Specifies whether to start or stop the generator.
    # @value 0 Stop the turbine.
    # @value 1 Start the turbine.
    # @note The {@link #USRSTR USRSTR} command controls whether a
    #       user can manually start and stop the generator.
    def __init__(self,turbine=None,start=None):
        if start != None:
            start = convert_argument('start', start,
                                     {'off':0, 'on':1}, int)
            if not start in (0,1):
                raise EInvalidValue, ('start', start)
        Message.__init__(self,'STRCMD',turbine,start)
    ##
    # @return The response handler class for the STRCMD command.
    # @see Message#response_factory
    def response_factory(self):
        return response.STRCMD()

##
# Handler for the SYSMOD Capstone MicroTurbine command.
class SYSMOD(Message):
    ##
    # Instanciate an SYSMOD Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'SYSMOD',turbine)
    ##
    # @return The response handler class for the SYSMOD command.
    # @see Message#response_factory
    def response_factory(self):
        return response.SYSMOD()

##
# Handler for the SYSSSL Capstone MicroTurbine command.
class SYSSSL(Message):
    ##
    # Instanciate an SYSSSL Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'SYSSSL',turbine)
    ##
    # @return The response handler class for the SYSSSL command.
    # @see Message#response_factory
    def response_factory(self):
        return response.SYSSSL()

##
# Handler for the SYSSTA Capstone MicroTurbine command.
class SYSSTA(Message):
    ##
    # Instanciate an SYSSTA Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'SYSSTA',turbine)
    ##
    # @return The response handler class for the SYSSTA command.
    # @see Message#response_factory
    def response_factory(self):
        return response.SYSSTA()

##
# Handler for the TETAVG Capstone MicroTurbine command.
class TETAVG(Message):
    ##
    # Instanciate an TETAVG Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'TETAVG',turbine)
    ##
    # @return The response handler class for the TETAVG command.
    # @see Message#response_factory
    def response_factory(self):
        return response.TETAVG()

##
# Handler for the TURBNO Capstone MicroTurbine command.
class TURBNO(Message):
    ##
    # Instanciate an TURBNO Capstone MicroTurbine command.
    def __init__(self, turbine=None):
        if turbine == None:
            Message.__init__(self,'TURBNO')
            return
        try:
            turbine = int(turbine)
        except:
            raise EInvalidValue, ('turbine', turbine)
        Message.__init__(self,'TURBNO',None,turbine)
    ##
    # @return The response handler class for the TURBNO command.
    # @see Message#response_factory
    def response_factory(self):
        return response.TURBNO()

##
# Handler for the USRSTR Capstone MicroTurbine command.
# @fixme Verify that this command takes arguments.
class USRSTR(Message):
    ##
    # Instanciate an USRSTR Capstone MicroTurbine command.
    def __init__(self,turbine=None,can_start=None):
        if can_start != None:
            can_start = convert_argument('can_start', can_start,
                                         {'off':0, 'on':1,
                                          'no':0, 'yes':1}, int)
            if not can_start in (0,1):
                raise EInvalidValue, ('can_start', can_start)
        Message.__init__(self,'USRSTR',turbine,can_start)
    ##
    # @return The response handler class for the USRSTR command.
    # @see Message#response_factory
    def response_factory(self):
        return response.USRSTR()

##
# Handler for the UTLCON Capstone MicroTurbine command.
class UTLCON(Message):
    ##
    # Instanciate an UTLCON Capstone MicroTurbine command.
    # @param turbine Turbine number
    # @param ucn The utility connection number.
    # @value 0,'invalid'
    # @value 1,'stand alone'
    # @value 2,'grid connect'
    # @value 3,'dual mode'
    def __init__(self,turbine=None,ucn=None):
        if ucn != None:
            ucn = convert_argument('ucn', ucn,
                                         {'invalid':0,
                                          'stand alone':1,
                                          'grid connect':2,
                                          'dual mode':1}, int)
            if not ucn in (0,1,2,3):
                raise EInvalidValue, ('ucn', ucn)
        Message.__init__(self,'UTLCON',turbine,ucn)
    ##
    # @return The response handler class for the UTLCON command.
    # @see Message#response_factory
    def response_factory(self):
        return response.UTLCON()

##
# Handler for the WARNTY Capstone MicroTurbine command.
class WARNTY(Message):
    ##
    # Instanciate an WARNTY Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'WARNTY',turbine)
    ##
    # @return The response handler class for the WARNTY command.
    # @see Message#response_factory
    def response_factory(self):
        return response.WARNTY()

##
# Handler for the WFRAMP Capstone MicroTurbine command.
# @note This command is not documented in the specification I have.
# @fixme Turbine does not respond to this command.  It may be a command
#        that requires a password mode higher than protected.  Unfortuanately
#        I can't find any documentation on any higher password modes.
class WFRAMP(Message):
    ##
    # Instanciate an WFRAMP Capstone MicroTurbine command.
    def __init__(self,turbine=None):
        Message.__init__(self,'WFRAMP',turbine)
    ##
    # @return The response handler class for the WFRAMP command.
    # @see Message#response_factory
    def response_factory(self):
        return response.WFRAMP()
