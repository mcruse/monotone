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
from mpx.lib import edtlib
from mpx.lib import factory
from mpx.lib.node import as_internal_node
from mpx.lib.node import is_node

class PropertyDefinition(object):
    edt__cls = 'mpx.lib.entity.properties.PropertyDefinition'
    ptype = 'Property'
    def __init__(self, **kw):
        self._attrs = ['name', 'type', 'label', 'description']
        self._reference = None
        self.set_attrs(**kw)
        
    def supported_attrs(self):
        return self._attrs
    
    def get_attr(self, attr):
        return self._attrs[attr]
    
    def get_attrs(self):
        attrs = {}
        for attr in self.supported_attrs():
            attrs[attr] = self.get_attr(attr)
        return attrs
    
    def set_attr(self, attr, value):
        if attr == 'reference':
            self._reference = value
        else:
            self._attrs[attr] = value
            
    def set_attrs(self, **kw):
        for attr in self._attrs:
            setattr(self, attr, kw.get(attr))
        self._reference = kw.get('reference', self._reference)
        
    @classmethod
    def edt_encode(cls, obj):
        if not isinstance(obj, cls):
            obj = cls(obj)
        try:
            url = obj.reference.as_node_url()
        except:
            url = ''
        edt_map = {'edt__typ':'object',
                   'edt__cls':obj.edt__cls,
                   'reference':url}
        for k in obj._attrs:
            edt_map[k] = getattr(obj, k)
        return edt_map
        
    @classmethod
    def edt_decode(cls, edt_map, obj=None):
        module = edt_map['edt__cls']
        del edt_map['edt__cls']
        del edt_map['edt__typ']
        if obj is None:
            obj = factory(module)
        obj.set_attrs(**edt_map)
        return obj

    def as_dict(self):
        return self.edt_encode(self)
    
    def __repr__(self):
        return repr(self.as_dict())
    from_dict = edt_decode

    def _get_reference(self):
        if not is_node(self._reference):
            try:
                self._reference = as_internal_node(self._reference)
            except:
                self._reference = None
        return self._reference
        
    reference = property(_get_reference)
edtlib.register_class(PropertyDefinition)

class EntityProp(PropertyDefinition):
    edt__cls = 'mpx.lib.entity.properties.EntityProp'
    ptype = 'Entity'
    def __init__(self, **kw):
        PropertyDefinition.__init__(self, **kw)
        self._attrs += ['url', 'entity']
        self.url = kw.get('url', '')
        self.entity = kw.get('entity', '')
edtlib.register_class(EntityProp)
      
class PropWithUnits(PropertyDefinition):
    edt__cls = 'mpx.lib.entity.properties.PropWithUnits'
    def __init__(self, **kw):
        PropertyDefinition.__init__(self, **kw)
        self._attrs += ['units']
        self.units = kw.get('units', 'SI Units')
edtlib.register_class(PropWithUnits)

class PropWithEnum(PropertyDefinition):
    edt__cls = 'mpx.lib.entity.properties.PropWithEnum'
    def __init__(self, **kw):
        PropertyDefinition.__init__(self, **kw)
        self._attrs += ['enumeration']
        self.enumeration = kw.get('enumeration', ('Inactive', 'Active'))
edtlib.register_class(PropWithEnum)
        
class SchedProp(PropertyDefinition):
    edt__cls = 'mpx.lib.entity.properties.SchedProp'
    ptype = 'Sched'
edtlib.register_class(SchedProp)
    
class AlarmProp(PropertyDefinition):
    edt__cls = 'mpx.lib.entity.properties.AlarmProp'
    ptype = 'Alarm'
edtlib.register_class(AlarmProp)
    
class LogProp(PropertyDefinition):
    edt__cls = 'mpx.lib.entity.properties.LogProp'
    ptype = 'Log'
edtlib.register_class(LogProp)
        
class AIProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.AIProp'
    ptype = 'AI'
edtlib.register_class(AIProp)
        
class AOProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.AOProp'
    ptype = 'AO'
edtlib.register_class(AOProp)
        
class AVProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.AVProp'
    ptype = 'AV'
edtlib.register_class(AVProp)
        
class BIProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.BIProp'
    ptype = 'BI'
edtlib.register_class(BIProp)

class BOProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.BOProp'
    ptype = 'BO'
edtlib.register_class(BOProp)
        
class BVProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.BVProp'
    ptype = 'BV'
edtlib.register_class(BVProp)
        
class MIProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.MIProp'
    ptype = 'MI'
edtlib.register_class(MIProp)
        
class MOProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.MOProp'
    ptype = 'MO'
edtlib.register_class(MOProp)

class MVProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.MVProp'
    ptype = 'MV'
edtlib.register_class(MVProp)
    
class IProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.IProp'
    ptype = 'I'
edtlib.register_class(PropertyDefinition)

class OProp(PropWithUnits):
    edt__cls = 'mpx.lib.entity.properties.Oprop'
    ptype = 'O'
edtlib.register_class(PropertyDefinition)
    
class BOProp(PropWithUnits, PropWithEnum):
    edt__cls = 'mpx.lib.entity.properties.BOProp'
    ptype = 'BO'
    def __init__(self, **kw):
        PropWithUnits.__init__(self, **kw)
        PropWithEnum.__init__(self, **kw)
edtlib.register_class(BOProp)
        
class BVProp(PropWithUnits, PropWithEnum):
    edt__cls = 'mpx.lib.entity.properties.BVProp'
    ptype = 'BV'
    def __init__(self, **kw):
        PropWithUnits.__init__(self, **kw)
        PropWithEnum.__init__(self, **kw)
edtlib.register_class(BVProp)
        
class MOProp(PropWithUnits, PropWithEnum):
    edt__cls = 'mpx.lib.entity.properties.MOProp'
    ptype = 'MO'
    def __init__(self, **kw):
        PropWithUnits.__init__(self, **kw)
        PropWithEnum.__init__(self, **kw)
edtlib.register_class(MOProp)

class MVProp(PropWithUnits, PropWithEnum):
    edt__cls = 'mpx.lib.entity.properties.MVProp'
    ptype = 'MV'
    def __init__(self, **kw):
        PropWithUnits.__init__(self, **kw)
        PropWithEnum.__init__(self, **kw)
edtlib.register_class(MVProp)
        
class OProp(PropWithUnits, PropWithEnum):
    edt__cls = 'mpx.lib.entity.properties.OProp'
    ptype = 'O'
    def __init__(self, **kw):
        PropWithUnits.__init__(self, **kw)
        PropWithEnum.__init__(self, **kw)
edtlib.register_class(OProp)
        
POINTS = (AIProp, AOProp, AVProp, BIProp, BOProp, \
          BVProp, MIProp, MOProp, MVProp, IProp, OProp)
COMMANDABLE = (AOProp, AVProp, BOProp, BVProp, MOProp, MVProp, OProp)
SCHEDULES = (SchedProp,)
ALARMS = (AlarmProp,)
LOGS = (LogProp,)
PTYPE_MAP = {
    'AI':AIProp, 
    'AO':AOProp, 
    'AV':AVProp, 
    'BI':BIProp, 
    'BO':BOProp, 
    'BV':BVProp, 
    'MI':MIProp, 
    'MO':MOProp, 
    'MV':MVProp, 
    'I':IProp, 
    'O':OProp, 
    'Sched':SchedProp, 
    'Alarm':AlarmProp, 
    'Log':LogProp
}
BAC_PTYPE_MAP = {
    'AI':'0', 
    'AO':'1', 
    'AV':'2', 
    'BI':'3', 
    'BO':'4', 
    'BV':'5', 
    'MI':'13', 
    'MO':'14', 
    'MV':'19', 
    'Sched':'17'
}

 