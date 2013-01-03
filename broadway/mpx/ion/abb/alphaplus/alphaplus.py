"""
Copyright (C) 2001 2004 2010 2011 Cisco Systems

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
# @todo Resovle duplicate names.
# @todo Comment.

import sys
import array
import string
from time import time

import mpx.lib
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import CompositeNode,ConfigurableNode
from mpx.lib.exceptions import EIOError

def _hexb(value):
    return string.zfill(string.upper(hex(value)[2:]),2)

def _bcdint(buf):
    result = ''
    for b in buf:
        result = result + _hexb(b)
    return int(result)

def _bcdfloat(buf,n=0):
    result = ''
    for b in buf:
        result = result + _hexb(b)
    return float(result)/pow(10,n)

def _td(buf):
    result = ''
    for b in buf:
        result = result + _hexb(b)
    return result

def _make16(buf):
    return (buf[0]<<8)|buf[1]

def _from16(num):
    return [(num>>8)&0x0FF,num&0x0FF]

def _make32(buf):
    return (buf[0]<<24)|(buf[1]<<16)|(buf[2]<<8)|buf[3]

def _from32(num):
    return [(num>>24)&0x0FF,(num>>16)&0x0FF,(num>>8)&0x0FF,num&0x0FF]

def _encrypt_password(p,ek):
    ek += 0xAB41
    i = ((ek&0x0FF)+((ek>>8)&0x0FF)+((ek>>16)&0x0FF)+((ek>>24)&0x0FF))&0x0F
    j = 0
    while (i >= 0):
        prev = ek
        ek = (ek<< 1)|j
        if (prev&0x80000000L):
            j = 1
        else:
            j = 0
        p ^= ek;
        i = i-1;
    return p

def _checksum(buf):
    crc = 0
    for c in buf:
        crc ^= (c<<8)
        for b in range(0,8):
            if (crc & 0x8000):
                crc = (crc<<1)^0x1021
            else:
                crc = crc<<1
            crc &= 0xFFFF
    return (crc>>8),(crc&0xff)


class_size = {0:40,
             1:5,
             2:64,
             3:196,
             4:176,
             6:288,
             7:304,
             8:64,
             9:48,
             10:24,
             11:212,
             12:212,
             13:212,
             14:42,
             15:15,
             19:5,
             20:64,
             21:196,
             22:176,
             28:62,
             #29:34,
             31:46,
             32:46,
             33:64,
             34:24}


class _DataItem:
    def __init__(self,abbclass,start,end,func,*args):
        self.abbclass = abbclass
        self.start = start
        self.end = end
        self.func = func
        self.args = args

    def get(self,classdata):
        if self.func:
            args = [classdata[self.start:self.end]]
            args.extend(self.args)
            return apply(self.func,args)
        else:
            return classdata[self.start:self.end]
                             

##
# AlphaPlus device <code>ION</code> class.
#
# @note Values for this device come from inherent children.
#
class AlphaPlus(CompositeNode):

    cache = {}

    def __init__(self):
        CompositeNode.__init__(self)
        self._datadict = {
            # Class 0: Computational Configuration [40]
            'UKH':_DataItem(0,0,3,_bcdfloat,3),
            'UPR':_DataItem(0,3,4,_bcdfloat),
            'UKE':_DataItem(0,4,9,_bcdfloat,6),
            'INTNORM':_DataItem(0,9,10,None),
            'INTTEST':_DataItem(0,10,11,None),
            'DPLOCE':_DataItem(0,11,12,_bcdint),
            'DPLOCD':_DataItem(0,12,13,_bcdint),
            'NUMSBI':_DataItem(0,13,14,None),
            'VTRATIO':_DataItem(0,14,17,_bcdfloat,2),
            'CTRATIO':_DataItem(0,17,20,_bcdfloat,2),
            'XFACTOR':_DataItem(0,20,24,_bcdfloat),
            'SPARE':_DataItem(0,24,39,None),
            'CL0CKS':_DataItem(0,39,40,None),
            # Class 1: Password Data [5]
            'PSWORD':_DataItem(1,0,4,_bcdfloat),
            'CL1CKS':_DataItem(1,4,5,None),
            # Class 2: Identification and Demand Data [64]
            'UMTRSN':_DataItem(2,0,5,_bcdfloat),
            'ACCTID':_DataItem(2,5,19,None),
            'USER':_DataItem(2,19,30,None),
            'DFOVAL':_DataItem(2,30,31,None),
            'DFGVAL':_DataItem(2,31,32,None),
            'DRLVAL':_DataItem(2,32,33,None),
            'KWOVRL':_DataItem(2,33,36,None),
            'KWTHRSA':_DataItem(2,36,39,None),
            'KWTHRSB':_DataItem(2,39,42,None),
            'KWTHRSC':_DataItem(2,42,45,None),
            'KWTHRSD':_DataItem(2,45,48,None),
            'E2KYZDV':_DataItem(2,48,49,None),
            'EMETFLG':_DataItem(2,49,51,None),
            'EATRVAL':_DataItem(2,51,52,None),
            'EBLKCF1':_DataItem(2,52,53,None),
            'EBLKCF2':_DataItem(2,53,54,None),
            'SPARE':_DataItem(2,54,63,None),
            'CL2CKS':_DataItem(2,63,64,None),
            # Class 3: Display Table [196]
            'EDHDTIM':_DataItem(3,0,1,None),
            'DATFMT':_DataItem(3,1,2,None),
            'DISFLG':_DataItem(3,2,3,None),
            'DISTAB':_DataItem(3,3,195,None),
            'CL3CKS':_DataItem(3,195,196,None),
            # Class 4: TOU Rate Schedule [176]
            'SMSEAS':_DataItem(4,0,1,None),
            'SEASFLG':_DataItem(4,1,2,None),
            'ENDRSP':_DataItem(4,2,3,None),
            'ENDCDT':_DataItem(4,3,4,None),
            'ENDSDT':_DataItem(4,4,5,None),
            'RATET':_DataItem(4,5,161,None),
            'RATEYR':_DataItem(4,161,162,None),
            'SPARE':_DataItem(4,162,163,None),
            'DTYPE':_DataItem(4,163,175,None),
            'CL4CKS':_DataItem(4,175,176,None),
            # Class 6: Metering Function Block #1 [288]
            'XREV':_DataItem(6,0,1,None),
            'RESERVED':_DataItem(6,1,2,None),
            'XUOM':_DataItem(6,2,4,None),
            'XUOM1':_DataItem(6,4,5,None),
            'RESERVED':_DataItem(6,5,283,None),
            'CL6CKS':_DataItem(6,283,284,None),
            # Class 7: Metering Function Block #2 [304]
            'XMTRSN':_DataItem(7,0,5,None),
            'XKH':_DataItem(7,5,8,None),
            'XPR1':_DataItem(7,8,9,None),
            'XKE1':_DataItem(7,9,14,None),
            'XKHDIV':_DataItem(7,14,15,None),
            'XKE2':_DataItem(7,15,20,None),
            'RESERVED':_DataItem(7,20,303,None),
            'CL7CKS':_DataItem(7,303,304,None),
            # Class 8: Firmware Configuration [64]
            'MKTPROD':_DataItem(8,0,1,None),
            'SSPEC1':_DataItem(8,1,4,None),
            'GROUP1':_DataItem(8,4,5,None),
            'REVNO1':_DataItem(8,5,6,None),
            'PCODE':_DataItem(8,6,7,None),
            'PSERIES1':_DataItem(8,7,8,None),
            'RESERVED':_DataItem(8,8,11,None),
            'SSPEC2':_DataItem(8,11,14,None),
            'GROUP2':_DataItem(8,14,15,None),
            'REVNO2':_DataItem(8,15,16,None),
            'PCODE2':_DataItem(8,16,17,None),
            'PSERIES2':_DataItem(8,17,18,None),
            'RESERVED':_DataItem(8,18,21,None),
            'SSPEC3':_DataItem(8,21,24,None),
            'GROUP3':_DataItem(8,24,25,None),
            'REVNO3':_DataItem(8,25,26,None),
            'XUOM':_DataItem(8,26,28,None),
            'SCRATCH':_DataItem(8,28,58,None),
            'LPLMEM':_DataItem(8,58,60,None),
            'INTERNAL_NUM':_DataItem(8,60,61,None),
            'SPARE':_DataItem(8,61,64,None),
            # Class 9: Status #1 [48]
            'XUOM':_DataItem(9,0,1,None),
            'SYSERR':_DataItem(9,1,4,None),
            'SYSWARN':_DataItem(9,4,5,None),
            'SYSSTAT':_DataItem(9,5,6,None),
            'CUMDDR':_DataItem(9,6,7,None),
            'CUMDPUL':_DataItem(9,7,8,None),
            'PWRLOG':_DataItem(9,8,12,None),
            'PSTART':_DataItem(9,12,18,None),
            'PEND':_DataItem(9,18,24,None),
            'SEARAT':_DataItem(9,24,25,None),
            'DOY':_DataItem(9,25,27,None),
            'TD':_DataItem(9,27,33,_td),
            'TRI':_DataItem(9,33,35,_bcdint),
            'DATATR':_DataItem(9,35,38,None),
            'DATREP':_DataItem(9,38,41,None),
            'DATMOD':_DataItem(9,41,44,None),
            'CUMDR':_DataItem(9,44,45,None),
            'CUMCOMM':_DataItem(9,45,46,None),
            'CUMOUT':_DataItem(9,46,48,None),
            # Class 10: Status #2 (Active Constants) [24]
            'KH':_DataItem(10,0,3,None),
            'PR':_DataItem(10,3,4,None),
            'PULDEF':_DataItem(10,4,5,None),
            'MTRSN':_DataItem(10,5,10,None),
            'KEADJ':_DataItem(10,10,15,None),
            'KDADJ':_DataItem(10,15,20,None),
            'ENEWCON':_DataItem(10,20,23,None),
            'ENEWACT':_DataItem(10,23,24,None),
            # Class 11: Billing Data [212]
            'AKWH1':_DataItem(11,0,7,self._dploce),
            'AKW1':_DataItem(11,7,10,self._dplocd),
            'ATD1':_DataItem(11,10,15,_td),
            'AKWCUM1':_DataItem(11,15,18,self._dplocd),
            'AKWC1':_DataItem(11,18,21,self._dplocd),
            'BKWH1':_DataItem(11,21,28,self._dploce),
            'BKW1':_DataItem(11,28,31,self._dplocd),
            'BTD1':_DataItem(11,31,36,_td),
            'BKWCUM1':_DataItem(11,36,39,self._dplocd),
            'BKWC1':_DataItem(11,39,42,self._dplocd),
            'CKWH1':_DataItem(11,42,49,self._dploce),
            'CKW1':_DataItem(11,49,52,self._dplocd),
            'CTD1':_DataItem(11,52,57,_td),
            'CKWCUM1':_DataItem(11,57,60,self._dplocd),
            'CKWC1':_DataItem(11,60,63,self._dplocd),
            'DKWH1':_DataItem(11,63,70,self._dploce),
            'DKW1':_DataItem(11,70,73,self._dplocd),
            'DTD1':_DataItem(11,73,78,_td),
            'DKWCUM1':_DataItem(11,78,81,self._dplocd),
            'DKWC1':_DataItem(11,81,84,self._dplocd),
            'AKWH2':_DataItem(11,84,91,self._dploce),
            'AKW2':_DataItem(11,91,94,self._dplocd),
            'ATD2':_DataItem(11,94,99,_td),
            'AKWCUM2':_DataItem(11,99,102,self._dplocd),
            'AKWC2':_DataItem(11,102,105,self._dplocd),
            'BKWH2':_DataItem(11,105,112,self._dploce),
            'BKW2':_DataItem(11,112,115,self._dplocd),
            'BTD2':_DataItem(11,115,120,_td),
            'BKWCUM2':_DataItem(11,120,123,self._dplocd),
            'BKWC2':_DataItem(11,123,126,self._dplocd),
            'CKWH2':_DataItem(11,126,133,self._dploce),
            'CKW2':_DataItem(11,133,136,self._dplocd),
            'CTD2':_DataItem(11,136,141,_td),
            'CKWCUM2':_DataItem(11,141,144,self._dplocd),
            'CKWC2':_DataItem(11,144,147,self._dplocd),
            'DKWH2':_DataItem(11,147,154,self._dploce),
            'DKW2':_DataItem(11,154,157,self._dplocd),
            'DTD2':_DataItem(11,157,162,_td),
            'DKWCUM2':_DataItem(11,162,165,self._dplocd),
            'DKWC2':_DataItem(11,165,168,self._dplocd),
            'EKVARH4':_DataItem(11,168,175,_bcdfloat,6),
            'EKVARH3':_DataItem(11,175,182,_bcdfloat,6),
            'EKVARH2':_DataItem(11,182,189,_bcdfloat,6),
            'EKVARH1':_DataItem(11,189,196,_bcdfloat,6),
            'ETKWH1':_DataItem(11,196,203,_bcdfloat,6),
            'ETKWH2':_DataItem(11,203,210,_bcdfloat,6),
            'EAVGPF':_DataItem(11,210,212,_bcdfloat,3),
            # Class 12: Previous Month's Billing Data [212]
            # Class 13: Previous Season's Billing Data [212]
            # Class 14: Load Profile Configuration [42]
            'SPARE':_DataItem(14,0,3,None),
            'RLPSCAL':_DataItem(14,3,4,None),
            'LPLEN':_DataItem(14,4,5,None),
            'DASIZE':_DataItem(14,5,7,None),
            'LPMEM':_DataItem(14,7,8,None),
            'CHANS':_DataItem(14,8,9,None),
            'IO01FLG':_DataItem(14,9,10,None),
            'IO02FLG':_DataItem(14,10,11,None),
            'IO03FLG':_DataItem(14,11,12,None),
            'IO04FLG':_DataItem(14,12,13,None),
            'SPARE':_DataItem(14,13,41,None),
            'CL14CKS':_DataItem(14,41,42,None),
            # Class 15: Event Log Configuration [15]
            #'EVSIZE':_DataItem(15,0,2,None),
            #'EVSEL1':_DataItem(15,2,3,None),
            #'SPARE':_DataItem(15,3,14,None),
            #'CL15CKS':_DataItem(15,14,15,None),
            #'EVREC':_DataItem(15,15,22,None),
            #'DAYHDR':_DataItem(15,22,28,None),
            #'CHANREC':_DataItem(15,28,30,None),
            # Class 28: Outage Reporting Configuration [62]
            'DS3':_DataItem(28,0,36,None),
            'PFDLY':_DataItem(28,36,37,None),
            'AVGDLY':_DataItem(28,37,38,None),
            'CALLDLY':_DataItem(28,38,39,None),
            'ANSDLY':_DataItem(28,39,40,None),
            'UPDELAY':_DataItem(28,40,41,None),
            'MAXTRY':_DataItem(28,41,42,None),
            'OUTFLG':_DataItem(28,42,43,None),
            'CTO':_DataItem(28,43,44,None),
            'ABSWAIT':_DataItem(28,44,45,None),
            'RESERVED':_DataItem(28,45,61,None),
            'CL28CKS':_DataItem(28,61,62,None),
            # Class 29: Outage Call Status [34]
            #'ACCTID':_DataItem(29,0,14,None),
            #'MTRSN':_DataItem(29,14,19,None),
            #'TDOUT':_DataItem(29,19,22,None),
            #'SPARE':_DataItem(29,22,26,None),
            #'MOSTAT':_DataItem(29,26,27,None),
            #'SSPEC3':_DataItem(29,27,32,None),
            #'MFGDT':_DataItem(29,32,34,None),
            # Class 31: Modem Billing Call Configuration [46]
            'DS1':_DataItem(31,0,36,None),
            'SPARE':_DataItem(31,36,42,None),
            'TWIND1':_DataItem(31,42,44,None),
            'AUTODAY':_DataItem(31,44,45,None),
            'CL31CKS':_DataItem(31,45,46,None),
            # Class 32: Modem Alarm Call Configuration [46]
            'DS2':_DataItem(32,0,36,None),
            'SPARE':_DataItem(32,36,40,None),
            'TWIND2':_DataItem(32,40,42,None),
            'SYSMSK':_DataItem(32,42,43,None),
            'WARNMSK':_DataItem(32,43,44,None),
            'EVENMSK':_DataItem(32,44,45,None),
            'CL32CKS':_DataItem(32,45,46,None),
            # Class 33: Modem Configuration Information [64]
            'COMID':_DataItem(33,0,8,None),
            'INITSTR':_DataItem(33,8,44,None),
            'TWIND3':_DataItem(33,44,46,None),
            'AUTOANS':_DataItem(33,46,47,None),
            'INITDEL':_DataItem(33,47,48,None),
            'TRYDEL':_DataItem(33,48,49,None),
            'RSPEED':_DataItem(33,49,50,None),
            'DEVNUM':_DataItem(33,50,51,None),
            'RESERVED':_DataItem(33,51,63,None),
            'CL33CKS':_DataItem(33,63,64,None),
            # Class 34: Modem Communication's Status [24]
            'RBAUD':_DataItem(34,0,1,None),
            'PWLEVEL':_DataItem(34,1,2,None),
            'EVENTS':_DataItem(34,2,3,None),
            'AUTODAT':_DataItem(34,3,6,None),
            'MODSTAT':_DataItem(34,6,7,None),
            'LASTPS1':_DataItem(34,7,12,None),
            'LASTPS2':_DataItem(34,12,17,None),
            'LASTPS3':_DataItem(34,17,22,None),
            'DS1SCHD':_DataItem(34,22,23,None),
            'DS2SCHD':_DataItem(34,23,24,None)
            }
    
        for k in self._datadict.keys():
            AlphaPlusValue().configure({'name':k,'parent':self})

    ##
    # Configure object.
    #
    # @param config  Configuration dictionary.
    # @key devnum  The device number.
    # @default 0
    # @key passwd  The password for the device.
    # @default 0
    #
    def configure(self, config):
        CompositeNode.configure(self,config)
        self.port = self.parent
        set_attribute(self, 'devnum', 0, config, int)
        set_attribute(self, 'passwd', 0, config)
        self.port.open()

    ##
    # Get the configuration of this object.
    #
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        config['port'] = config['parent']
        get_attribute(self, 'devnum', config, str)
        get_attribute(self, 'passwd', config)
        return config


    def _command(self,cmd,len,timeout,attempts):
        while (attempts > 0):
            buf = array.array('B',cmd)
            crch,crcl = _checksum(buf)
            buf.append(crch)
            buf.append(crcl)
            self.port.drain()
            self.port.write(buf)
            self.port.flush()
            
            try:
                buf = array.array('B')
                self.port.read(buf,len,timeout)
                crch,crcl = _checksum(buf[0:-2])
                if (crch==buf[-2])and(crcl==buf[-1]):
                    return buf.tolist()
            except IOError:
                pass
            attempts = attempts-1
        raise EIOError

    def _classread(self,abbclass,skipCache,timeout=3,maxattempts=3):
        if (not skipCache) and self.cache.has_key(abbclass):
            (timeval,data) = self.cache[abbclass]
            if (time() < timeval+30):
                return data
        
        result = []
        cbread = 0
        attempt = 0
        while (attempt < maxattempts):
            tx = array.array('B',[0x02,0x05,0x00,0x00,0x00]+ _from16(cbread)+[abbclass])
            crch,crcl = _checksum(tx)
            tx.append(crch)
            tx.append(crcl)
            self.port.drain()
            self.port.write(tx)
            self.port.flush()

            try:
                rx = array.array('B')
                self.port.read(rx,4,timeout)
                if (rx[2] == 0):
                    self.port.read(rx,1,timeout)
                    len = (rx[-1]&0x7F)
                    self.port.read(rx,len+2,timeout)
                    crch,crcl = _checksum(rx[0:-2])
                    if (crch==rx[-2])and(crcl==rx[-1]):
                        cbread = cbread + len
                        result = result + rx.tolist()[5:-2]
                        if (cbread < class_size[abbclass]):
                            attempt = 0
                        else:
                            self.cache[abbclass] = (time(),result[0:class_size[abbclass]])
                            return result[0:class_size[abbclass]]
            except IOError:
                if attempt==0:
                    self._end_session()
                    self._begin_session()
            attempt = attempt+1
        raise EIOError

    def _readvalue(self,name,skipCache=0):
        dataitem = self._datadict[name]
        return dataitem.get(self._classread(dataitem.abbclass,skipCache))

    def _dploce(self,buf):
        return _bcdfloat(buf,self._readvalue('DPLOCE'))

    def _dplocd(self,buf):
        return _bcdfloat(buf,self._readvalue('DPLOCD'))

    def _begin_session(self):
        resp = self._command([0x02,0x18,0x06,0x00,0x01,self.devnum],15,0.5,10)
        epass = _from32(_encrypt_password(int(self.passwd,16),_make32(resp[9:14])))
        self._command([0x02,0x18,0x01,0x00,0x04] + epass,6,0.5,3)

    def _end_session(self):
        self.port.write(array.array('B',[0x02,0x08,0xF7,0xEA]))

    def _getvalue(self,name, skipCache=0):
        return self._readvalue(name, skipCache)

##
# Inherent children of AlphaPlus, used for the different
# points on the AlphaPlus device.
#
class AlphaPlusValue(ConfigurableNode):
    ##
    # Get the value of this point.
    #
    # @param skipCache  May or may not use cached value.
    # @value 0  May use cached value
    # @value 1  May not use cached value.
    # @default 0
    #
    def get(self, skipCache=0):
        return self.parent._getvalue(self.name, skipCache)


def factory():
    return AlphaPlus()

