"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import time
import string
import inspect
from mpx.lib.persistence import storage
from mpx.lib.persistence import datatypes
from mpx.lib.persistent import PersistentDataObject as PDO
reload(storage)
reload(datatypes)

class PDOData(PDO):
    def __init__(self, *args, **kw):
        self.integer = None
        self.integers = None
        self.letters = None
        self.letterset = None
        self.letterlist = None
        self.letterdict = None
        PDO.__init__(self, *args, **kw)
    def update(self, data):
        items = dict(data).items()
        for name,value in items:
            setattr(self, name, value)
        self.save()




def timed(function, *args, **kw):
    if inspect.ismethod(function):
        name = '%s.%s' % (function.im_self.__class__.__name__, 
                          function.im_func.__name__)
    else:
        name = function.__name__
    tstart = time.time()
    result = function(*args, **kw)
    tend = time.time()
    print 'Took %0.5f seconds to run %s' % (tend - tstart, name)
    return result

def timedset(function, argdict):
    if inspect.ismethod(function):
        name = '%s.%s' % (function.im_self.__class__.__name__, 
                          function.im_func.__name__)
    else:
        name = function.__name__
    tstart = time.time()
    for item in argdict.items():
        function(dict([item]))
    tend = time.time()
    print 'Took %0.5f seconds to run %s' % (tend - tstart, name)

def timed_multiset(pobj, pdict, argdict, batch=False):
    tstart = time.time()
    for key,value in argdict.items():
        pdict[key] = value
    if batch:
        pdict.commit()
    tend = time.time()
    print 'Took %0.5f set PersistentDictionary attributes' % (tend - tstart)
    tstart = time.time()
    for key,value in argdict.items():
        setattr(pobj, key, value)
        if not batch:
            pobj.save()
    if batch:
        pobj.save()
    tend = time.time()
    print 'Took %0.5f set PDO attributes' % (tend - tstart)


pobj = PDOData("testing1")
pdict = datatypes.PersistentDictionary("testing1", autopersist=False)
timed(pobj.load)
timed(pdict.load)
pdict.autopersist = True

data = {'integer': 1, 
        'integers': range(1000), 
        'letters': string.ascii_letters, 
        'letterset': set(string.ascii_letters), 
        'letterlist': list(string.ascii_letters), 
        'letterdict': dict(enumerate(list(string.ascii_letters)))}

timed(pobj.update, data)
timed(pdict.update, data)
timed(pobj.save)
timed(pdict.commit)

timedset(pobj.update, data)
timedset(pdict.update, data)

timed_multiset(pobj, pdict, data, False)
timed_multiset(pobj, pdict, data, True)

timed(pdict.update, {'integers': range(100000)})
timed(pobj.update, {'integers': range(100000)})
timed(pobj.update, {'integer': 2})
timed(pdict.update, {'integer': 2})

data = dict([(str(i), range(10)) for i in range(100)])
timedset(pdict.update, data)
timedset(pobj.update, data)



data = {'integer': 1, 
        'integers': range(1000), 
        'letters': string.ascii_letters, 
        'letterset': set(string.ascii_letters), 
        'letterlist': list(string.ascii_letters), 
        'letterdict': dict(enumerate(list(string.ascii_letters)))}

















import time
import string
import inspect
from mpx.lib.persistence import storage
from mpx.lib.persistence import datatypes
from mpx.lib.persistent import PersistentDataObject as PDO

data = dict([(str(key), string.ascii_letters) for key in range(10000)])
pdo = PDO('many-key-test')
pdict = datatypes.PersistentDictionary('many-key-test')
pdo.load()
pdodict = pdo.__dict__

items = data.items()
pdostart = time.time()
for key,value in items:
    pdodict[key] = value
    pdo.save()


pdostop = time.time()

pdictstart = time.time()
for key,value in items:
    pdict[key] = value


pdictstop = time.time()

print 'Took %0.4f seconds to set/save %d PDO attributes' % (pdostop - pdostart, len(items))
print 'Took %0.4f seconds to set/save %d PDict items' % (pdictstop - pdictstart, len(items))







import time
import string
import inspect
from mpx.lib.persistence import storage
from mpx.lib.persistence import datatypes


pdict = datatypes.PersistentDictionary('subscriptions-test')
start = time.time()
pdict.update(subs)
stop = time.time()


pdict.update()
pdo.load()
pdodict = pdo.__dict__

items = data.items()
pdostart = time.time()
for key,value in items:
    pdodict[key] = value
    pdo.save()


pdostop = time.time()

pdictstart = time.time()
for key,value in items:
    pdict[key] = value


pdictstop = time.time()

print 'Took %0.4f seconds to set/save %d PDO attributes' % (pdostop - pdostart, len(items))
print 'Took %0.4f seconds to set/save %d PDict items' % (pdictstop - pdictstart, len(items))








import time
import string
import inspect
import cPickle
from mpx.lib.persistence import storage
from mpx.lib.persistence import datatypes
from mpx.lib.persistent import PersistentDataObject as PDO

def timed(function, *args, **kw):
    if inspect.ismethod(function):
        name = '%s.%s' % (function.im_self.__class__.__name__, 
                          function.im_func.__name__)
    else:
        name = function.__name__
    tstart = time.time()
    result = function(*args, **kw)
    tend = time.time()
    print 'Took %0.5f seconds to run %s' % (tend - tstart, name)
    return result

def timedset(function, argdict):
    if inspect.ismethod(function):
        name = '%s.%s' % (function.im_self.__class__.__name__, 
                          function.im_func.__name__)
    else:
        name = function.__name__
    tstart = time.time()
    for item in argdict.items():
        function(dict([item]))
    tend = time.time()
    print 'Took %0.5f seconds to run %s' % (tend - tstart, name)

def timed_multiset(p1, p2, argdict, batch=False):
    tstart = time.time()
    for key,value in argdict.items():
        p2[key] = value
    if batch:
        p2.commit()
    tend = time.time()
    print 'Took %0.5f set PersistentDictionary attributes' % (tend - tstart)
    tstart = time.time()
    for key,value in argdict.items():
        setattr(p1, key, value)
        if not batch:
            p1.save()
    if batch:
        p1.save()
    tend = time.time()
    print 'Took %0.5f set PDO attributes' % (tend - tstart)

data = {'integer': 1, 
        'integers': range(1000), 
        'letters': string.ascii_letters, 
        'letterset': set(string.ascii_letters), 
        'letterlist': list(string.ascii_letters), 
        'letterdict': dict(enumerate(list(string.ascii_letters)))}
reprdict = datatypes.PersistentDictionary("repr-test", autopersist=False)
pickledict = datatypes.PersistentDictionary("pickle-test", 
                                            autopersist=False, 
                                            encode=cPickle.dumps, 
                                            decode=cPickle.loads)

timed(reprdict.load)
timed(pickledict.load)
reprdict.autopersist = True
pickledict.autopersist = True

timed(reprdict.update, data)
timed(pickledict.update, data)
ints1 = range(10000)
ints2 = range(10000)
timed(reprdict.__setitem__, 'integers', ints1)
timed(pickledict.__setitem__, 'integers', ints2)

reprdict.close()
pickledict.close()


reprdict = datatypes.PersistentDictionary("repr-test2", encode=repr, 
                                          decode=eval, keyencode=repr, 
                                          keydecode=eval, autopersist=False)
pickledict = datatypes.PersistentDictionary("pickle-test2", 
                                            autopersist=False, 
                                            encode=cPickle.dumps, 
                                            decode=cPickle.loads, 
                                            keyencode=repr, keydecode=eval)



timed(reprdict.load)
timed(pickledict.load)
reprdict.autopersist = True
pickledict.autopersist = True

timed(reprdict.update, data)
timed(pickledict.update, data)
ints1 = range(10000)
ints2 = range(10000)
timed(reprdict.__setitem__, 'integers', ints1)
timed(pickledict.__setitem__, 'integers', ints2)











