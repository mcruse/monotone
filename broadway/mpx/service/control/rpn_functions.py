"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

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
from math import *
import time
from array import array

INPUT = 1
CONSTANT = 0
RPN = 2

STACK_SIZE = 32
STACK_MASK = 0x1F

class Rpn(object):
    def __init__(self, app_node=None):
        self.app_node = app_node
        self.init_math_stack()
        self.RPN_functions = RPN_functions
        self.step_number = 0
        self.startup = 1
    def perform(self, *args):
        perform(self, *args) #not a typo, see below
    #*    STACK MANIPULATION FUNCTIONS */
    def init_math_stack(self):
        self.stack = array('f',[0.0]*STACK_SIZE) #use pointers
        self.sp = 0
        self.xreg = 0.0
    def stack_up(self):                   # rotate the stack up */
        self.sp = (self.sp - 1) & STACK_MASK
        return self.sp
    def stack_down(self):                     # rotate the stack down */
        self.sp = (self.sp + 1) & STACK_MASK
        return self.sp
    def pushit(self):  # push rpn.xreg onto stack */
        self.stack[self.stack_up()] = float(self.xreg)
    def yreg(self):   # return the value of the Y register */
        return self.stack[self.sp]
    def zreg(self):   # return the value of the Z register */
        return self.stack[(self.sp + 1) & STACK_MASK];
    def popit(self):  # pop the value of the Y register */
        y = self.yreg()
        self.stack_down()
        return y
    def run(self, template, node): #run template in the instance's context
        self.step_number = 0
        steps = template._steps
        s_len = len(steps)
        while self.step_number < s_len:
            #perform the step's function
            typ, x, s = steps[self.step_number]
            self.step_number += 1
            if typ == RPN:
                x = x(self, node, s) #x is callable function from rpn_functions
                if self.step_number == -1: break
            elif typ == CONSTANT:
                self.pushit()
            else: #must be input
                x = node.get_input(x) #x is pre-hashed xy
                self.pushit()
            self.xreg = x
        node._outputs[0] = self.xreg

# STACK MANIPULATION OPERATIONS */
def _fnInitMathStack (rpn, *args ):
    rpn.init_math_stack()
    return 0.0
def _fnent(rpn, *args):
    rpn.pushit()
    return rpn.xreg  # push stack, y = x, x = x, TOS lost*/
def _fnswp(rpn, *args): # swap x and y registers */
    y = rpn.popit()
    rpn.pushit()
    return y
def _fnup (rpn, *args): # rotate the stack up.  Yreg = rpn.xreg, rpn.xreg = the top of the stack (TOS).
 #Similar to enter, except x is not duplicated and the top of the stack is not lost */
    rpn.stack_up()
    y = rpn.popit()
    rpn.pushit()
    return y
def _fndwn(rpn, *args): # Rotate the stack down. TOS = x, x = y, etc. */
    y = rpn.popit()
    rpn.pushit()
    rpn.stack_down()
    return y

#* BASIC MATH OPERATIONS */

def _fnadd(rpn, *args):    return rpn.popit() + rpn.xreg
def _fnsub(rpn, *args):    return rpn.popit() - rpn.xreg
def _fnmul(rpn, *args):    return rpn.popit() * rpn.xreg
def _fndiv(rpn, *args):    return rpn.popit() / rpn.xreg
def _fnsqt(rpn, *args):    return sqrt(rpn.xreg)
def _fnexp(rpn, *args):    return exp(rpn.xreg)
def _fnln(rpn, *args):     return log(rpn.xreg)
def _fnlog(rpn, *args):    return log10(rpn.xreg)
def _fnpow(rpn, *args):    return pow(rpn.xreg,rpn.popit())
def _fnabs(rpn, *args):    return fabs(rpn.xreg)
def _fnmin(rpn, *args):
    y = rpn.popit()
    if y < rpn.xreg:
        return y
    return rpn.xreg
def _fnmax(rpn, *args):
    y = rpn.popit()
    if y > rpn.xreg:
        return y
    return rpn.xreg
def _fnint(rpn, *args):
    if rpn.xreg < 0.0: return ceil(rpn.xreg)
    return floor(rpn.xreg)
def _fnmod(rpn, *args):    return fmod(rpn.popit(),rpn.xreg)

# TRANSCENDENTAL MATH OPERATIONS*/

def _fncos(rpn, *args):    return cos(rpn.xreg)
def _fnsin(rpn, *args):    return sin(rpn.xreg)
def _fntan(rpn, *args):    return tan(rpn.xreg)
def _fnacs(rpn, *args):    return acos(rpn.xreg)
def _fnasn(rpn, *args):    return asin(rpn.xreg)
def _fnatn(rpn, *args):    return atan(rpn.xreg)
def _fnsnh(rpn, *args):    return sinh(rpn.xreg)
def _fncsh(rpn, *args):    return cosh(rpn.xreg)
def _fntnh(rpn, *args):    return tanh(rpn.xreg)

#* LOGICAL OPERATIONS */

def _fnand(rpn, *args):
    if (rpn.popit() > 0.0) and (rpn.xreg > 0.0): return 1.0
    return 0.0
def _fnnan(rpn, *args):
    if (rpn.popit() > 0.0) and (rpn.xreg > 0.0): return 0.0
    return 1.0
def _fnor (rpn, *args):
    if (rpn.popit() > 0.0) or (rpn.xreg > 0.0): return 1.0
    return 0.0
def _fnnor(rpn, *args):
    if (rpn.popit() > 0.0) or (rpn.xreg > 0.0): return 0.0
    return 1.0
def _fnxor(rpn, *args):
    if rpn.popit() > 0.0:
        if rpn.xreg > 0.0: return 0.0
        return 1.0
    if rpn.xreg > 0.0: return 1.0
    return 0.0
def _fnrs (rpn, node, *args):
    if rpn.popit() > 0.0: return 0.0 #reset input true
    if rpn.xreg > 0.0:    return 1.0 #set input true
    return node._outputs[0] #returns the 1st output register value
def _fnnot(rpn, *args):
    if rpn.xreg > 0.0: return 0.0
    return 1.0
def _fnneg(rpn, *args):    return -rpn.xreg

# IF - THEN OPERATIONS

   # the following functions test the rpn.xreg for a condition
   # if the result is true the next step is executed otherwise
   # it is skipped.  Often used with GOTO. */

# found an error in the math library that prevents equals from working with negative zero....*/
   
def _fnxe0(rpn, *args):
    if rpn.xreg != 0.0:
        rpn.step_number += 1
    return rpn.xreg # if x == 0.0 */
def _fnxn0(rpn, *args):
    if rpn.xreg == 0.0:
        rpn.step_number += 1
    return rpn.xreg # if x != 0.0 */
def _fnxg0(rpn, *args):
    if rpn.xreg <= 0.0:
        rpn.step_number += 1
    return rpn.xreg # if x >  0.0 */
def _fnxl0(rpn, *args):
    if rpn.xreg >= 0.0:
        rpn.step_number += 1
    return rpn.xreg # if x <  0.0 */
def _fnxey(rpn, *args):    
    if rpn.xreg != yreg():
        rpn.step_number += 1
    return rpn.xreg # if x == y   */
def _fnxny(rpn, *args):
    if rpn.xreg == rpn.yreg():
        rpn.step_number += 1
    return rpn.xreg # if x != y   */
def _fnxgy(rpn, *args):
    if rpn.xreg <= rpn.yreg():
        rpn.step_number += 1
    return rpn.xreg # if x >  y   */
def _fnxly(rpn, *args):
    if rpn.xreg >= rpn.yreg():
        rpn.step_number += 1
    return rpn.xreg # if x <  y   */
def _fngo2(rpn, node, step, *args):
# execution resumes at the step number that is encoded into this step */
    rpn.step_number = step - 1
    return rpn.xreg
def _fnBit(rpn, node, step, *args): # return true if the desired bit is set */
    if (int(rpn.xreg) >> step ) & 0x01: return 1.0
    return 0.0
def _fnMux(rpn, *args): # multiplex eight on/off inputs into 0 to 255 */
    rpn.pushit()
    result = 0
    for i in range(8):
        if rpn.popit() > 0.0:
            result += 1
        result = result << 1
    return float(result)

#* OUTPUT / STORAGE REGISTER OPERATIONS */

def _fnsxy(rpn, node, *args): # store x into the output/storage registers at y */
    node._outputs[int(rpn.yreg())] = rpn.xreg
    return rpn.xreg
def _fnsxn(rpn, node, index, *args): # store x into the output/storage registers at the fixed location 'n' */
    node._outputs[int(index)] = rpn.xreg
    return rpn.xreg
def _fnrx (rpn, node, *args): # retrieve x from the output/storage registers at location in x */
    rpn.pushit()
    return node.get_output(int(rpn.xreg))
def _fnrn (rpn, node, index, *args): # retrieve x from the output/storage registers at fixed location 'n' */
    rpn.pushit()
    return node.get_output(int(index))
def _fnpsy(rpn, node, step, *args): # push x into the output/storage registers at fixed location (n) and 
   #return the sum of all numbers in the storage registers starting at (n) */
    rpn.pushit()
    result = 0.0
    if step < len(node._outputs):
        index = len(node._outputs) - 1
        while step < index:
            temp = node._outputs[index - 1]
            node._outputs[index] = temp
            result += temp
            index -= 1
        node._outputs[int(step)] = rpn.xreg
    result += rpn.xreg
    return result
def _fnppx(rpn, node, step, *args): # sum stack starting at 'n' */
    # return the sum of all numbers in the storage registers starting at (n) */
    rpn.pushit()
    result = 0.0
    while step < len(node._outputs):
        result += node.get_output(int(step))
        step += 1
    return result

#* TIME AND DATE OPERATIONS */

def _fntim(rpn, *args): # return the time of day in minutes in x */
    rpn.pushit()
    h,m,s = time.localtime()[3:6]
    return float(h*3600 + m*60 + s)
def _fnday(rpn, *args): # return the day of the week ( sun = 0, mon = 1, etc ) */
    rpn.pushit()
    d = time.localtime()[6]
    return float((d+1) % 7)
def _fndat(rpn, *args):
    rpn.pushit()
    m,d = time.localtime()[1:3]
    return float((m * 31 + d))
def _fnjul(rpn, *args): # return the numbers of days since the beginning of the year */
    rpn.pushit()
    d = time.localtime()[7]
    return float(d)

# SYSTEM STATUS OPERATIONS */

def not_implemented(rpn, *args): 
    return rpn.xreg
_fnHighLine = not_implemented # return true if power line is above high limit ( >= 135 Volts ) */
_fnBattery  = not_implemented # return true if board is running under battery power */
def _fnStartUp(rpn, *args): # return true the first time object runs after power up */
    rpn.pushit()
    return float(rpn.startup)
_fnCarrierDetect = not_implemented # return true when the carrier detect is true */

#* INPUT / OUTPUT OPERATION

_fnaiv     = not_implemented # 0 - 2.4 volts */
_fnaiv11   = not_implemented # 0 - 26.4 volts ( 2.4 * 11 ) */
_fnaic100  = not_implemented  # 0 - 20 ma */
_fnaic1000 = not_implemented # 0 - 2 ma */
_fnair100  = not_implemented # low range resistance */
_fnair1000 = not_implemented # high range resistance */
_fnao      = not_implemented # analog output of volts or ma */
_fndi      = not_implemented # pushes the stack and returns the current digital input status */
_fndiTimer = not_implemented # pushes the stack and returns the current digital input status */
_fndilon   = not_implemented # pushes the stack and returns rpn.xreg = 1.0 if any ON occured during the last second */
_fndiloff  = not_implemented # pushes the stack and returns rpn.xreg = 0.0 if any OFF occured during the last second */
_fndicount = not_implemented # pushes the stack and returns rpn.xreg = the number of OFF to ON and ON to OFF transistions 
_fnhoa     = not_implemented 
_fndo      = not_implemented 
_fnLcp     = not_implemented 

#* COMPLEX FUNCTIONS */

def _fnminon(rpn, node, *args): # minimum on time
    #yreg = minimum time in seconds
    #rpn.xreg = logical on/off input */

    if len(node._outputs) > 1:
        if rpn.xreg > 0.0: # if input is on */
            if node._outputs[0] <= 0.0: # output is off */
                node._outputs[1] = 0.0 #reset timer
            else:
                node._outputs[1] += 1.0 #increment timer
            return 1.0  #will get written to node._outputs[0]
        else: # since input is off */
            if node._outputs[0] > 0.0: # since output was on*/
                node._outputs[1] += 1.0 #count delay
                if node._outputs[1] < rpn.yreg():
                    return 1.0
            return 0.0
    return rpn.xreg
def _fnminoff(rpn, node, *args): # minimum off time */
    #yreg = minimum time in seconds
    #rpn.xreg = logical on/off input */
    if len(node._outputs) > 1:
        if rpn.xreg <= 0.0: # if input is off */
            if node._outputs[0] > 0.0: # output is on */
                node._outputs[1] = 0.0 #reset timer
            else:
                node._outputs[1] += 1.0 #increment timer
            return 0.0
        else: # since input is on */
            if node._outputs[0] <= 0.0: # since output still off*/
                node._outputs[1] += 1.0 #count delay
                if node._outputs[1] < rpn.yreg():
                    return 0.0
            return 1.0
    return rpn.xreg
def _fnhyst(rpn, node, *args): # hysterisys control loop */
    # zreg = deadband
    # yreg = setpoint
    # rpn.xreg = controled variable
    # action is increasing output for decreasing controlled variable
    error = rpn.yreg() - rpn.xreg #calculate error*/
    if error > rpn.zreg(): return 1.0
    if error < -rpn.zreg(): return 0.0
    return node._outputs[0]

# offsets from storage register pointer for pid */
#define OUTPUT 0
#define INPUT 1
#define SUM 2
#define COUNT 3
#define LAST_COUNT 4
#define IOUT 5
#define DOUT 6
#define LAST_DOUT 7
def _fnpid(rpn, node, *args): # pid control loop */
    # rpn.xreg = controlled variable
    # yreg = setpoint
    # zreg = proportional range
    # treg = integral reset time
    # sreg = derivative rate
    # rreg = derivative smoothing time constant
    # action is increasing output for decreasing controlled variable

    input    = rpn.xreg
    setpoint = rpn.popit()
    range    = rpn.popit()
    reset    = rpn.popit()
    rate     = rpn.popit()
    smooth   = rpn.popit()

    error = setpoint - input #calculate error*/
 
    if len(node._outputs) < 8: return 0.0 #error
    sum = 0.0
    if reset > 0.0: #since integral mode active */
        sum = node._outputs[2] # SUM
        if (fabs ( error ) * 2) <= range: sum += error #integrate
        temp = reset * range * 30.0     # 60/2 */  maximum sum value
        if fabs ( sum ) > temp:
            if sum >= 0.0: sum = temp
            else: sum = - temp
        node._outputs[5] = sum / temp #IOUT
    else:
        node._outputs[5] = 0.0 #IOUT
        node._outputs[2] = 0.0 #SUM
    if rate > 0.0: #since derivative mode */
        node._outputs[3] += 1.0 #COUNT
        lastCount = node._outputs[4] #LAST_COUNT 
        temp = node._outputs[7] #LAST_DOUT 
        if error == node._outputs[1]: # INPUT ) ) { #since no change*/
            count = node._outputs[3]
            if count > lastCount:
                temp = temp * lastCount / count
        else: # since a change in the input has occured */
            node._outputs[4] = count #LAST_COUNT
            temp = ((( error - node._outputs[1] ) / count ) * 60.0 ) / rate
            if temp > 1.0:    temp = 1.0
            elif temp < -1.0: temp = -1.0
            node._outputs[7] = temp #LAST_DOUT
            node._outputs[3] = 0.0 #COUNT
        node._outputs[6] = ( node._outputs[6] * smooth + temp ) / ( smooth + 1.0 ) #DOUT=6
    else:
        node._outputs[7] = 0.0 #LAST_DOUT
        node._outputs[6] = 0.0 #DOUT
        node._outputs[3] = 0.0 #COUNT
        node._outputs[4] = 0.0 #LAST_COUNT
    node._outputs[1] = error
    temp = (((error / range) + node._outputs[6] + node._outputs[5]) * 100.0) + 50.0
    if temp < 0.0: temp = 0.0
    elif temp > 100.0: temp = 100.0
    else:
        node._outputs[2] = sum #update sum only while error in proportional range
    return temp
def _fnenthalpy(rpn, *args): # compute enathalpy from temp and rh */
    # rpn.xreg = dry bulb temp
    # yreg = relative humidity %
    # result = btu's / pound of dry air
    return ((exp(-4.3322182 + (.03656619 * rpn.xreg)) * rpn.yreg()) + (.244033 * rpn.xreg))
def _fnPython(rpn, node, *args): #run Python code the appears in the Description field of the template
    #check to see if this template has been compiled yet
    if node._definition_node._python_prim is None:
        return float('nan')
    statement = node._definition_node._python_prim
    local_env = {'stack':rpn.stack, 'outputs':node._outputs, 'node':node, 'rpn':rpn, 'xreg': rpn.xreg}
    exec(statement, globals(), local_env)
    return rpn.xreg
def _fnnop(rpn, *args): #
    return rpn.xreg
_fnPeek   = not_implemented 

# SPECIAL OPERATIONS */

def _fnAlarm (rpn, node, *args):
    if len(node._outputs) > 1:
        if rpn.xreg > 0.0: #if input is on*/
            if node._outputs[0] <= 0.0: # output is off */
                node.trigger_alarm()
        else: #since input is off
            if node._outputs[0] > 0.0: #output was on
                node.clear_alarm()
    return rpn.xreg
def _fnTrendLog (rpn, node, *args):
    print_trigger = rpn.xreg
    if len(node._outputs) > 3:
        log_trigger = rpn.popit()
        if log_trigger > 0.0: #if input is on*/
            if node._outputs[2] <= 0.0: # output is off */
                node._outputs[2] = 1
                node.trigger_log()
        else: #since input is off
            node._outputs[2] = 0
    return print_trigger

_fnProtocol1 = not_implemented 
_fnActMix    = not_implemented
_fnURD905    = not_implemented
_fnLinear    = not_implemented
_fnX10       = not_implemented
_fnMicroStar = not_implemented
_fnAcm3300   = not_implemented
_fnAsi8015   = not_implemented
_fnAsic2     = not_implemented
_fnNat       = not_implemented
_fnCA2100    = not_implemented
_fnAEA       = not_implemented
_fnBC        = not_implemented
_fnFDM       = not_implemented
_fnCardNumber= not_implemented
_fnSpeech    = not_implemented
_fnHydrolab  = not_implemented
_fnMcQuay    = not_implemented
_fnBACnet    = not_implemented
_fnDunham    = not_implemented
_fnCDP       = not_implemented
_fnCDL       = not_implemented
_fnHSQ       = not_implemented
_fnSmartI    = not_implemented
_fnSmartII   = not_implemented
_fnTrane     = not_implemented
_fnCSI       = not_implemented
_fnTriLCP    = not_implemented
_fnTriPOD    = not_implemented
_fnBarb      = not_implemented
_fnGalaxy    = not_implemented
_fnYorkTalk  = not_implemented
_fnSitePlayer= not_implemented
_fnN2        = not_implemented
_fnHHT       = not_implemented
_fnSnvt      = not_implemented

#* LOOK UP TABLE TO CONVERT TYPE CODE TO OPERATION ADDRESS */

_pfb_lookup = [
     _fnadd, _fnsub, _fnmul, _fndiv, _fnmin, _fnmax, _fnsqt, _fnexp,
     _fnln, _fnlog, _fnpow, _fnabs, _fnint, _fncos, _fnsin, _fntan,
     _fnacs, _fnasn, _fnatn, _fnsnh, _fncsh, _fntnh, _fntim, _fnday,
     _fndat, _fnjul, _fnmod, _fnand, _fnnan, _fnor, _fnnor, _fnxor,
     _fnrs, _fnnot, _fnneg, _fnxe0, _fnxn0, _fnxg0, _fnxl0, _fnxey,
     _fnxny, _fnxgy, _fnxly, _fngo2, _fnent, _fnswp, _fnup, _fndwn,
     _fnsxy, _fnsxn, _fnrx, _fnrn, _fnpsy, _fnppx, _fnaiv, _fnaiv11,
     _fnaic100, _fnaic1000, _fnair100, _fnair1000, _fnao,
     _fndi, _fndo, _fnminon, _fnminoff, _fnhyst, _fnpid, _fnenthalpy, 
     _fnnop, _fnhoa, _fnHighLine, _fnBattery, _fndilon, _fndiloff,
     _fndicount, _fnStartUp, _fnAlarm, _fnTrendLog, _fnActMix,
     _fnCardNumber, _fnX10, _fnMicroStar, _fnCarrierDetect,
     _fnAcm3300, _fnAsi8015, _fndiTimer, _fnBC, _fnBit, _fnNat,
     _fnMux, _fnInitMathStack, _fnAsic2, _fnURD905, _fnLinear, 
     _fnCA2100, _fnSpeech, _fnAEA, _fnFDM, _fnHydrolab, _fnMcQuay,
     _fnBACnet, _fnDunham, _fnLcp, _fnCDP, _fnHSQ, _fnSnvt, _fnPeek, 
     _fnHHT, _fnSmartII, _fnCSI, _fnSmartI, _fnTrane, _fnTriLCP, _fnTriPOD,
     _fnBarb, _fnGalaxy, _fnYorkTalk, _fnSitePlayer, _fnN2,
     _fnCDL, _fnPython]


# INVOKE THE SELECTED OPERATION FOR THE PFB MANAGER */
_fnNOP = 68
MAX_FUNCTION = 120

def get_function(function_str):
    function_number = RPN_functions[function_str]
    return _pfb_lookup[function_number]

def perform(function_number, rpn, node, step):
    if function_number > MAX_FUNCTION: function_number = _fnNOP
    rpn.xreg = _pfb_lookup[function_number](rpn, node, step)

RPN_functions = {'di latch on': 72, 'maximum': 5, 'AEA': 96, 'multiplex': 89, 'di pulse count': 74, 'sum=>': 53, 'ln': 8, 'hyster': 65, 'YorkTalk': 116, 'Carrier Datalink': 119, 'swap': 45, 'ai v 11:1': 55, 'do': 62, 'lcp': 102, 'ACM 3300': 83, 'SNVT': 105, 'ai v': 54, 'di timer': 85, 'not': 33, 'Smart_1': 110, 'day': 23, 'nor': 30, 'Smart_2': 108, 'di status': 61, 'ASIC/2': 91, 'Carrier Detect': 82, 'start up': 75, 'ASI 8015': 84, 'X10 Protocol': 80, 'highline': 70, 'modulo': 26, 'min on': 63, 'cosh': 20, 'URD 905': 92, 'rs-ff': 32, 'clear stack': 90, 'bit': 87, 'Triatek LCP Protocol': 112, 'xor': 31, 'HSQ Technology': 104, 'neg': 34, '+': 0, 'nand': 28, '/': 3, 'abs': 11, 'sto=>': 49, 'Carrier Dataport': 103, 'peek': 106, 'rcl=>x': 50, 'Trane Protocol': 111, 'sinh': 19, 'cos': 13, 'MicroStar Protocol': 81, 'sto=>y': 48, 'ai ma 1000': 57, 'shove=>': 52, 'arccos': 16, 'or': 29, 'if x=y': 39, 'battery': 71, 'if x>0': 37, 'down': 47, 'ai ohm 1000': 59, 'Dunham-Bush': 101, 'ACT MIX-1': 78, 'deadband': 65, 'NK Kw2000': 88, 'log': 9, '*': 2, 'Triatek POD Protocol': 113, 'min off': 64, 'time': 22, 'if x>y': 41, 'arcsin': 17, 'Compu-Aire 2100': 94, 'x^y': 10, 'N2': 118, 'LINEAR AC-680': 93, 'HYDROLAB': 98, 'rcl=>': 51, 'tanh': 21, 'up': 46, 'enthalpy': 67, 'CSI Protocol': 109, 'Bell Canada CHP': 86, 'alarm': 76, 'Galaxy': 115, 'and': 27, 'int': 12, 'julian': 25, 'if x<>0': 36, 'pid': 66, 'BACnet': 100, 'minimum': 4, 'tan': 15, 'RZ Web Server': 117, 'goto=>': 43, '-': 1, 'Barber Coleman': 114, 'sqrt': 6, 'arctan': 18, 'if x=0': 35, 'sin': 14, 'if x<y': 42, 'if x<>y': 40, 'card number': 79, 'enter': 44, 'ai ma 100': 56, 'date': 24, 'RZ VAV': 109, 'Hand Held Terminal': 107, 'CD9FDM': 97, 'trendLog': 77, 'McQuay': 99, 'ai ohm 100': 58, 'switch': 69, 'exp': 7, 'if x<0': 38, 'di latch off': 73, 'SpeechModem': 95, 'ao v': 60, 'Python': 120}
