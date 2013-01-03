"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
# PySNMP SMI module. Autogenerated from smidump -f python IANAifType-MIB
# by libsmi2pysnmp-0.0.7-alpha at Sat Sep  8 12:43:24 2007,
# Python version (2, 2, 3, 'final', 0)

# Imported just in case new ASN.1 types would be created
from pyasn1.type import constraint, namedval

# Imports

( Integer, ObjectIdentifier, OctetString, ) = mibBuilder.importSymbols('ASN1', 'Integer', 'ObjectIdentifier', 'OctetString')
( Bits, Counter32, Counter64, Gauge32, Integer32, IpAddress, ModuleIdentity, MibIdentifier, Opaque, TimeTicks, Unsigned32, mib_2, ) = mibBuilder.importSymbols('SNMPv2-SMI', 'Bits', 'Counter32', 'Counter64', 'Gauge32', 'Integer32', 'IpAddress', 'ModuleIdentity', 'MibIdentifier', 'Opaque', 'TimeTicks', 'Unsigned32', 'mib-2')
( TextualConvention, ) = mibBuilder.importSymbols('SNMPv2-TC', 'TextualConvention')

# Types

class IANAifType(Integer):
    subtypeSpec = Integer.subtypeSpec+constraint.SingleValueConstraint(109,101,194,184,181,64,24,118,69,175,135,102,154,199,4,129,26,165,216,114,190,78,143,146,43,152,88,62,113,210,47,225,170,51,156,35,223,68,5,214,121,230,202,140,11,86,72,229,50,157,124,179,2,177,180,84,188,219,215,182,201,89,187,173,222,90,49,193,57,38,46,159,85,204,74,117,40,227,196,17,100,41,172,162,167,141,136,153,221,185,224,110,132,95,33,19,7,198,176,104,149,30,81,18,151,128,174,92,191,54,213,52,12,163,61,82,97,171,83,23,32,87,99,160,79,200,208,206,116,150,125,144,228,138,58,75,108,60,16,59,77,76,119,122,34,8,42,14,139,145,137,134,21,13,10,186,205,195,6,131,168,44,166,71,55,39,73,56,67,29,147,203,155,209,80,22,45,65,120,126,178,20,66,36,106,192,28,183,94,107,63,31,218,37,142,127,53,1,207,103,226,115,70,211,130,217,93,105,212,9,197,111,158,220,96,112,15,189,123,169,25,164,3,148,27,161,91,98,133,48,)
    namedValues = namedval.NamedValues(('other', 1), ('iso88026Man', 10), ('voiceEM', 100), ('voiceFXO', 101), ('voiceFXS', 102), ('voiceEncap', 103), ('voiceOverIp', 104), ('atmDxi', 105), ('atmFuni', 106), ('atmIma', 107), ('pppMultilinkBundle', 108), ('ipOverCdlc', 109), ('starLan', 11), ('ipOverClaw', 110), ('stackToStack', 111), ('virtualIpAddress', 112), ('mpc', 113), ('ipOverAtm', 114), ('iso88025Fiber', 115), ('tdlc', 116), ('gigabitEthernet', 117), ('hdlc', 118), ('lapf', 119), ('proteon10Mbit', 12), ('v37', 120), ('x25mlp', 121), ('x25huntGroup', 122), ('trasnpHdlc', 123), ('interleave', 124), ('fast', 125), ('ip', 126), ('docsCableMaclayer', 127), ('docsCableDownstream', 128), ('docsCableUpstream', 129), ('proteon80Mbit', 13), ('a12MppSwitch', 130), ('tunnel', 131), ('coffee', 132), ('ces', 133), ('atmSubInterface', 134), ('l2vlan', 135), ('l3ipvlan', 136), ('l3ipxvlan', 137), ('digitalPowerline', 138), ('mediaMailOverIp', 139), ('hyperchannel', 14), ('dtm', 140), ('dcn', 141), ('ipForward', 142), ('msdsl', 143), ('ieee1394', 144), ('if-gsn', 145), ('dvbRccMacLayer', 146), ('dvbRccDownstream', 147), ('dvbRccUpstream', 148), ('atmVirtual', 149), ('fddi', 15), ('mplsTunnel', 150), ('srp', 151), ('voiceOverAtm', 152), ('voiceOverFrameRelay', 153), ('idsl', 154), ('compositeLink', 155), ('ss7SigLink', 156), ('propWirelessP2P', 157), ('frForward', 158), ('rfc1483', 159), ('lapb', 16), ('usb', 160), ('ieee8023adLag', 161), ('bgppolicyaccounting', 162), ('frf16MfrBundle', 163), ('h323Gatekeeper', 164), ('h323Proxy', 165), ('mpls', 166), ('mfSigLink', 167), ('hdsl2', 168), ('shdsl', 169), ('sdlc', 17), ('ds1FDL', 170), ('pos', 171), ('dvbAsiIn', 172), ('dvbAsiOut', 173), ('plc', 174), ('nfas', 175), ('tr008', 176), ('gr303RDT', 177), ('gr303IDT', 178), ('isup', 179), ('ds1', 18), ('propDocsWirelessMaclayer', 180), ('propDocsWirelessDownstream', 181), ('propDocsWirelessUpstream', 182), ('hiperlan2', 183), ('propBWAp2Mp', 184), ('sonetOverheadChannel', 185), ('digitalWrapperOverheadChannel', 186), ('aal2', 187), ('radioMAC', 188), ('atmRadio', 189), ('e1', 19), ('imt', 190), ('mvl', 191), ('reachDSL', 192), ('frDlciEndPt', 193), ('atmVciEndPt', 194), ('opticalChannel', 195), ('opticalTransport', 196), ('propAtm', 197), ('voiceOverCable', 198), ('infiniband', 199), ('regular1822', 2), ('basicISDN', 20), ('teLink', 200), ('q2931', 201), ('virtualTg', 202), ('sipTg', 203), ('sipSig', 204), ('docsCableUpstreamChannel', 205), ('econet', 206), ('pon155', 207), ('pon622', 208), ('bridge', 209), ('primaryISDN', 21), ('linegroup', 210), ('voiceEMFGD', 211), ('voiceFGDEANA', 212), ('voiceDID', 213), ('mpegTransport', 214), ('sixToFour', 215), ('gtp', 216), ('pdnEtherLoop1', 217), ('pdnEtherLoop2', 218), ('opticalChannelGroup', 219), ('propPointToPointSerial', 22), ('homepna', 220), ('gfp', 221), ('ciscoISLvlan', 222), ('actelisMetaLOOP', 223), ('fcipLink', 224), ('rpr', 225), ('qam', 226), ('lmp', 227), ('cblVectaStar', 228), ('docsCableMCmtsDownstream', 229), ('ppp', 23), ('adsl2', 230), ('softwareLoopback', 24), ('eon', 25), ('ethernet3Mbit', 26), ('nsip', 27), ('slip', 28), ('ultra', 29), ('hdh1822', 3), ('ds3', 30), ('sip', 31), ('frameRelay', 32), ('rs232', 33), ('para', 34), ('arcnet', 35), ('arcnetPlus', 36), ('atm', 37), ('miox25', 38), ('sonet', 39), ('ddnX25', 4), ('x25ple', 40), ('iso88022llc', 41), ('localTalk', 42), ('smdsDxi', 43), ('frameRelayService', 44), ('v35', 45), ('hssi', 46), ('hippi', 47), ('modem', 48), ('aal5', 49), ('rfc877x25', 5), ('sonetPath', 50), ('sonetVT', 51), ('smdsIcip', 52), ('propVirtual', 53), ('propMultiplexor', 54), ('ieee80212', 55), ('fibreChannel', 56), ('hippiInterface', 57), ('frameRelayInterconnect', 58), ('aflane8023', 59), ('ethernetCsmacd', 6), ('aflane8025', 60), ('cctEmul', 61), ('fastEther', 62), ('isdn', 63), ('v11', 64), ('v36', 65), ('g703at64k', 66), ('g703at2mb', 67), ('qllc', 68), ('fastEtherFX', 69), ('iso88023Csmacd', 7), ('channel', 70), ('ieee80211', 71), ('ibm370parChan', 72), ('escon', 73), ('dlsw', 74), ('isdns', 75), ('isdnu', 76), ('lapd', 77), ('ipSwitch', 78), ('rsrb', 79), ('iso88024TokenBus', 8), ('atmLogical', 80), ('ds0', 81), ('ds0Bundle', 82), ('bsc', 83), ('async', 84), ('cnr', 85), ('iso88025Dtr', 86), ('eplrs', 87), ('arap', 88), ('propCnls', 89), ('iso88025TokenRing', 9), ('hostPad', 90), ('termPad', 91), ('frameRelayMPI', 92), ('x213', 93), ('adsl', 94), ('radsl', 95), ('sdsl', 96), ('vdsl', 97), ('iso88025CRFPInt', 98), ('myrinet', 99), )
    pass

class IANAtunnelType(Integer):
    subtypeSpec = Integer.subtypeSpec+constraint.SingleValueConstraint(8,14,13,6,11,7,9,2,12,3,5,10,1,4,)
    namedValues = namedval.NamedValues(('other', 1), ('msdp', 10), ('sixToFour', 11), ('sixOverFour', 12), ('isatap', 13), ('teredo', 14), ('direct', 2), ('gre', 3), ('minimal', 4), ('l2tp', 5), ('pptp', 6), ('l2f', 7), ('udp', 8), ('atmp', 9), )
    pass


# Objects

ianaifType = ModuleIdentity((1, 3, 6, 1, 2, 1, 30)).setRevisions(('2005-10-10 00:00','2005-09-09 00:00','2005-05-27 00:00','2005-03-03 00:00','2004-11-22 00:00','2004-06-17 00:00','2004-05-12 00:00','2004-05-07 00:00','2003-08-25 00:00','2003-08-18 00:00','2003-08-07 00:00','2003-03-18 00:00','2003-01-13 00:00','2002-10-17 00:00','2002-07-16 00:00','2002-07-10 00:00','2002-06-19 00:00','2002-01-04 00:00','2001-12-20 00:00','2001-11-15 00:00','2001-11-06 00:00','2001-11-02 00:00','2001-10-16 00:00','2001-09-19 00:00','2001-05-11 00:00','2001-01-12 00:00','2000-12-19 00:00','2000-12-07 00:00','2000-12-04 00:00','2000-10-17 00:00','2000-10-02 00:00','2000-09-01 00:00','2000-08-24 00:00','2000-08-23 00:00','2000-08-22 00:00','2000-04-25 00:00','2000-03-06 00:00','1999-10-08 14:30','1994-01-31 00:00',))

# Augmentions

# Exports

# Module identity
mibBuilder.exportSymbols('IANAifType-MIB', PYSNMP_MODULE_ID=ianaifType)

# Types
mibBuilder.exportSymbols('IANAifType-MIB', IANAifType=IANAifType, IANAtunnelType=IANAtunnelType)

# Objects
mibBuilder.exportSymbols('IANAifType-MIB', ianaifType=ianaifType)
