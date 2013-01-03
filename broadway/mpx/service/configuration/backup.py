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
""" well known service that allows various components to register files\directories for backups """
import os
from stat import *
from mpx.lib import EnumeratedDictionary
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.persistent import PersistentDataObject
from mpx import properties

from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

# General classifications for backup data with room
# for additional granularity.
backup_class = EnumeratedDictionary({0:'Config', 10:'Web Data', 
                                     20:'PDO', 30:'Other',
                                     100:'All'})

class _PersistentData(PersistentDataObject):
    def __init__(self, node):
        self.entries = None
        PersistentDataObject.__init__(self, node)
        PersistentDataObject.load(self)
        
class BackupRegistry(CompositeNode):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self):
        CompositeNode.__init__(self)
        # dynamic entries represents BackupEntry's added on the fly by other
        # interfaces\services.  As opposed to static entries that are added
        # w\ configTool, these will require pdo's.
        self._dynamic_entries = []
        
    # single use, read -> close -> destroyed wrapper for a file (tarball)
    # object.
    class SimpleFileWrapper:
        def __init__(self, f_name, f_path):
            self.f_name = f_name
            self._f_path = f_path
            self._fd = open(f_path, 'r')
        
        def read(self, size):
            return self._fd.read(size)
        
        def close(self):
            self._fd.close()
            os.unlink(self._f_path)
            
    def start(self):
        CompositeNode.start(self)
        self.pdo = _PersistentData(self)
        if self.pdo.entries:
            self._load_registry()
        
    def register(self, name, path, bc='Other'):
        e = BackupEntry()
        cd = {'name' : name,
              'path' : path,
              'backup_class' : bc}
        # save cd so we can recreate from pdo - not interested in preserving parent
        self._dynamic_entries.append(cd)
        self._save_registry()
        cd['parent'] = self
        e.configure(cd)
        e.start()
        
    def get_registered_classes(self):
        r = {}
        for entry in self.children_nodes():
            r[entry.backup_class] = ''
        return r.keys()
    
    security.protect('generate_backup', 'Configure')    
    def generate_backup(self, backup_name, bc=['All']):
        tar_file_list = ''
        exclude_list = ""
        for entry in self.children_nodes():
            if backup_class['All'] in bc or entry.backup_class in bc:
                tar_file_list += '%s ' % entry.path
                if entry.exclude:
                    exclude_base = entry.path
                    if exclude_base.endswith('*'):
                        exclude_base = exclude_base[:-1]
                    for exclude in entry.exclude.split(','):
                        exclude_list += '--exclude %s ' % (os.path.join(exclude_base, exclude))
        if not tar_file_list:
            return None
        tar_tmp_file_name = '%s/%s.tgz' % (properties.TEMP_DIR, backup_name)
        tar_cmd = 'tar -czPf %s %s --ignore-failed-read %s' % \
            (tar_tmp_file_name, tar_file_list, exclude_list)
        os.system(tar_cmd)
        return self.SimpleFileWrapper(backup_name, tar_tmp_file_name)
        
    def get_exclude_list(self, bc=['All']):
        exclude_list = []
        for entry in self.children_nodes():
            if backup_class['All'] in bc or entry.backup_class in bc:
                if entry.exclude:
                    exclude_base = entry.path
                    if exclude_base.endswith('*'):
                        exclude_base = exclude_base[:-1]
                    for exclude in entry.exclude.split(','):
                        exclude_list.append('--exclude')
                        exclude_list.append((os.path.join(exclude_base, exclude)))
        return exclude_list

    def _extract_path(self, entry):
        path = ''
        try:
            if entry.path.find('*') >= 0:
                # expand wildcards and check for exclusions
                if entry.path.endswith('/*'):
                    path_root = entry.path[:-1]
                    for f in os.listdir(path_root):
                        if entry.exclude:
                            if self._in_exclude_list(f, entry.exclude.split(',')):
                                continue
                        mode = os.stat(os.path.join(path_root, f))[ST_MODE]
                        if S_ISDIR(mode):
                            path += '%s/* ' % (path_root + f)
                        else:
                            path += '%s ' % (path_root + f)
                else:
                    for f in os.listdir(entry.path):
                        if entry.exclude:
                            if f in entry.exclude:
                                continue
                        path += entry.path
            else:
                if os.path.exists(entry.path):
                    path = entry.path
        except:
            path = ''
        return path
        
    def _in_exclude_list(self, target, l):
        for exclude_entry in l:
            while exclude_entry[0] == ' ':
                exclude_entry = exclude_entry[1:]
            if target == exclude_entry:
                return 1
        return 0
        
    def _load_registry(self):
        cfg_entries = eval(self.pdo.entries)
        for cd in cfg_entries:
            cd['parent'] = self
            e = BackupEntry()
            e.configure(cd)
            e.start()
    
    def _save_registry(self):
        self.pdo.entries = repr(self._dynamic_entries)
        self.pdo.save()

class BackupEntry(CompositeNode):
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'path', REQUIRED, cd)
        set_attribute(self, 'backup_class', 'Other', cd)
        set_attribute(self, 'exclude', '', cd)

    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'path', cd, str)
        get_attribute(self, 'backup_class', cd, str)
        get_attribute(self, 'exclude', cd, str)
        return cd
        
def factory():
    return BackupRegistry()
        
