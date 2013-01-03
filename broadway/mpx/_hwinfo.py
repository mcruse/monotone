"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
import os

from _const import UNKNOWN

_biosinfo = {}
_biosinfo_supported = True
_biosinfo_command = "/opt/IBM/DSA/bin/biosinfo 2>/dev/null"
_system_serial_number = None

_system_product_map = {
    "System x3550 M2 -[7946AC1]-":"IBM-x3550-M2-7946AC1",
    " -[7946AC1]-":"IBM-x3550-M2-7946AC1",
    "-[7946PAX]-":"IBM-x3550-M2-7946AC1",
    "IBM Corp.":"IBM-x3550-M2-7946AC1",
    "VMware Virtual Platform":"VMware-Virtual-Platform",
    }

def _rz2500_hwid_proc():
    # @FIXME:  Need to check the license manager, and then return
    #          "NBM-2400" or "NBM-4800".
    return "NBM-4800"

def _megatron_hwid_proc():
    # @FIXME:  Need to check the license manager, and then return
    #          "NBM-2500" or "NBM-5000".
    megatron_models = ['NBM-2500', 'NBM-5000']
    try:
        from mpx.lib.node import as_internal_node
        hwid = 'NBM-' + str(as_internal_node('/interfaces/AI1').coprocessor.udi[3:7])
        if hwid not in megatron_models:
            # return the default hwid, i.e., NBM5000
            hwid = 'NBM-5000'
    except Exception, error:
        # Do nothing, can't use msglog here ...
        # return the default hwid, i.e., NBM5000
        hwid = 'NBM-5000'
    return hwid 

_moe_hardware_map = {
    "IBM-x3550-M2-7946AC1":"NBM-MGR-6300",
    "VMware-Virtual-Platform":"NBM-VM",
    "RZ-2500":_rz2500_hwid_proc,
    "Megatron":_megatron_hwid_proc,
    }

def biosinfo(reread=False):
    global _biosinfo
    global _biosinfo_supported
    global _biosinfo_command
    if not reread:
        if _biosinfo or not _biosinfo_supported:
            return dict(_biosinfo)
    else:
        _biosinfo_supported = True
    try:
        for line in os.popen(_biosinfo_command, 'r').readlines():
            k,v = line.strip().split('=',1)
            _biosinfo[k] = v
    except:
        _biosinfo = {}
        _biosinfo_supported = False
    return dict(_biosinfo)

_system_cpu_info = None
def cpu_info(reread=False):
    global _system_cpu_info
    if _system_cpu_info and not reread:
        return _system_cpu_info
    result_dict = {}
    cpu_dict = {}
    for line in open('/proc/cpuinfo').readlines():
        items = line.split(':', 1)
        key = items[0].strip()
        if key:
            value = items[1].strip()
            if key == 'processor' or key == 'Processor':
                cpu_dict = {}
                if key == 'processor':
                    result_dict[int(value)] = cpu_dict
                else:
                    # /proc/cpuinfo has a different format for sheevaplug
                    # based devices.
                    result_dict[0] = cpu_dict
            cpu_dict[key] = value
    keys = result_dict.keys()
    keys.sort()
    result_list = []
    for key in keys:
        result_list.append(result_dict[key])
    _system_cpu_info = tuple(result_list)
    return _system_cpu_info

def _rz_2500_probe():
    try:
        if cpu_info()[0].get('vendor_id') == 'Geode by NSC':
            model_path = '/proc/mediator/model'
            if os.path.exists(model_path):
                model = open(model_path).readlines()[0].strip()
                if model == '2500':
                    return 'RZ-2500'
    except:
        pass
    return None

def _megatron_probe():
    try:
        if cpu_info()[0].get('platform') == 'Megatron':
            return 'Megatron'
    except:
        pass
    return None

_oem_hardware_id = None
def oem_hardware_id(reread=False):
    global _oem_hardware_id
    if _oem_hardware_id and not reread:
        return _oem_hardware_id
    bi = biosinfo(reread)
    system_product = bi.get("SystemProduct", None)
    if system_product:
        _oem_hardware_id = _system_product_map.get(system_product, UNKNOWN)
        if _oem_hardware_id == UNKNOWN:
            # SystemProduct appears to be extremely inconsistent in the values
            # that it returns.  3 variations have been discovered already...
            system_vendor = bi.get("BiosVendor", None)
            _oem_hardware_id = _system_product_map.get(system_vendor, UNKNOWN)
        return _oem_hardware_id
    for probe in (_megatron_probe, _rz_2500_probe):
        _oem_hardware_id = probe()
        if _oem_hardware_id:
            return _oem_hardware_id
    return UNKNOWN

def moe_hardware_id(reread=False):
    global _moe_hardware_map
    moe_hwid = _moe_hardware_map.get(oem_hardware_id(reread), UNKNOWN)
    if callable(moe_hwid):
        try:
            moe_hwid = moe_hwid()
        except:
            moe_hwid = UNKNOWN
    return moe_hwid

def moe_hardware_codename(reread=False):
    return {
        "IBM-x3550-M2-7946AC1":"Laserbeak",
        "Megatron":"Megatron",
        "RZ-2500":"Geode",
        }.get(oem_hardware_id(reread), UNKNOWN)

def moe_hardware_class(reread=False):
    # CSCtd52249: Removed printed warning.
    # @fixme Need to clearify use of hardware platform and product id.
    moe_hwid = moe_hardware_id(reread)
    if moe_hwid in ('NBM-2400', 'NBM-4800'):
        # @fixme Hack to maintain historical behaivor.
        moe_hwid = '2500'
    return moe_hwid

def oem_serial_number(reread=False):
    global _system_serial_number
    if _system_serial_number and not reread:
        return _system_serial_number
    bi = biosinfo()
    _system_serial_number = bi.get("SystemSerialNumber", None)
    if not _system_serial_number:
        try:
            _system_serial_number = open(
                '/proc/mediator/serial'
                ).readlines()[0].strip()
        except:
            pass
    if not _system_serial_number:
        try:
            from mpx.lib.ifconfig import mac_address
            _system_serial_number = mac_address('eth0')
        except:
            _system_serial_number = UNKNOWN
    return _system_serial_number
