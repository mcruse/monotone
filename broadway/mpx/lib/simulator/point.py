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
import time
import random
from mpx.lib.scheduler import scheduler

class RandomNumber(object):
    def __init__(self, min = 0, max = 100):
        self.min = min
        self.max = max
    def set_min(self, value):
        self.min = value
    def set_max(self, value):
        self.max = value
    def get(self, *args, **kw):
        return random.uniform(self.min, self.max)
    def __str__(self):
        return '<Random Floats from %s to %s>' % (self.min, self.max)

class SequentialNumber(RandomNumber):
    def __init__(self, min = 0, max = 100, step = 0.1):
        self.step = step
        self.value = float(min)
        super(SequentialNumber, self).__init__(min, max)
    def get(self, *args, **kw):
        value = self.value
        self.value += self.step
        if self.value >= self.max:
            self.value = self.min
        return value
    def __str__(self):
        message = '<Sequential Floats from %s to %s in increments of %s>'
        return  message % (self.min, self.max, self.step)

class RandomInteger(RandomNumber):
    def __init__(self, min = 0, max = 100, step = 1):
        super(RandomInteger, self).__init__(min, max)
        self.step = step
    def set_step(self, value):
        self.step = value
    def get(self, *args, **kw):
        return random.randrange(self.min, self.max, self.step)
    def __str__(self):
        message = '<Random Integers from %s to %s in increments of %s>'
        return message % (self.min, self.max, self.step)

class SequentialInteger(RandomInteger):
    def __init__(self, min = 0, max = 100, step = 1):
        self.values = []
        super(SequentialInteger, self).__init__(min, max, step)
    def get(self, *args, **kw):
        if not self.values:
            self.values = range(self.min, self.max, self.step)
        return self.values.pop(0)
    def __str__(self):
        message = '<Sequential Integers from %s to %s in increments of %s>'
        return  message % (self.min, self.max, self.step)

class StepwiseModifier(object):
    def __init__(self, source, getcount):
        self.source = source
        self.getcount = getcount
        self.current_count = 0
        self.current_value = self.source.get()
    def get(self):
        if self.current_count >= self.getcount:
            self.current_value = self.source.get()
            self.current_count = 0
        self.current_count += 1
        return self.current_value
    def __str__(self):
        message = '<Stepwise Modifier gets value every %s gets from "%s" >'
        return  message % (self.getcount, str(self.source)[1:-1])

class PeriodicModifier(object):
    def __init__(self, source, frequency):
        self.source = source
        self.frequency = frequency
        self.next_update = 0
    def _refresh(self):
        self.current_value = self.source.get()
        self.next_update = self._next_time()
    def _next_time(self):
        return ((int(time.time()) / self.frequency) * self.frequency) + self.frequency
    def get(self):
        current_time = time.time()
        if current_time >= self.next_update:
            self._refresh()
        return self.current_value
    def __str__(self):
        message = '<Periodic Modifier gets value every %s seconds from "%s" >'
        return  message % (self.frequency, str(self.source)[1:-1])

class AutoPeriodicModifier(PeriodicModifier):
    def __init__(self, source, frequency):
        super(AutoPeriodicModifier, self).__init__(source, frequency)
        self._refresh()
    def get(self):
        return self.current_value
    def _refresh(self):
        self.current_value = self.source.get()
        self._schedule_refresh()
    def _next_time(self):
        return ((int(time.time()) / self.frequency) * self.frequency) + self.frequency
    def _schedule_refresh(self):
        scheduler.at(self._next_time(), self._refresh)
    def __str__(self):
        message = '<Periodic Modifier gets value every %s seconds from "%s" >'
        return  message % (self.frequency, str(self.source)[1:-1])

class RandomEnumeration(object):
    def __init__(self, enumerations):
        self.count = len(enumerations)
        self.enumerations = enumerations
    def get_enumeration(self, index):
        return self.enumerations[index]
    def get(self):
        index = random.randrange(0, self.count)
        return self.get_enumeration(index)
    def __str__(self):
        message = '<Random Enumeration with %s values>'
        return  message % (self.count)

class SequentialEnumeration(SequentialInteger, RandomEnumeration):
    def __init__(self, enumerations):
        RandomEnumeration.__init__(self, enumerations)
        SequentialInteger.__init__(self, 0, len(enumerations), 1)
    def get(self):
        index = SequentialInteger.get(self)
        return self.get_enumeration(index)
    def __str__(self):
        message = '<Sequential Enumeration with %s values>'
        return  message % (self.count)

if __name__ == '__main__':
    def test_random_number():
        testrange = 50
        simulator = RandomNumber(-testrange, testrange)
        for index in range(testrange * 4):
            value = simulator.get()
            if not (value >= -testrange and value <= testrange):
                raise Exception('%s returned %s.' % (simulator, value))
            if not isinstance(value, float):
                raise TypeError('%s returned %s.' % (simulator, value))
        print 'Tested %s %s times: passed.' % (simulator, testrange * 4)
    def test_sequential_number():
        testrange = 25
        simulator = SequentialNumber(-testrange, testrange, 0.5)
        valuerange = range(-testrange, testrange)
        halfvalues = map(lambda x: x + 0.5, valuerange)
        valuerange += halfvalues
        valuerange.sort()
        valuerange += valuerange
        for rangevalue in valuerange:
            value = simulator.get()
            assert value == rangevalue, '%s returned %s instead of %s.' % (simulator, value, rangevalue)
        print 'Tested %s %s times: passed.' % (simulator, len(valuerange))
    def test_random_integer():
        testrange = 50
        simulator = RandomInteger(-testrange, testrange)
        for index in range(testrange * 4):
            value = simulator.get()
            if not (value >= -testrange and value <= testrange):
                raise Exception('%s returned %s.' % (simulator, value))
            if not isinstance(value, int):
                raise TypeError('%s returned %s.' % (simulator, value))
        print 'Tested %s %s times: passed.' % (simulator, testrange * 4)
    def test_sequential_integer():
        testrange = 50
        singlestep = SequentialInteger(-testrange, testrange)
        singlerange = range(-testrange, testrange)
        singlerange += singlerange
        for rangevalue in singlerange:
            value = singlestep.get()
            assert value == rangevalue, '%s returned %s, should be %s.' % (singlestep, value, rangevalue)
        print 'Tested %s %s times: passed' % (singlestep, len(singlerange))
        triplestep = SequentialInteger(-testrange, testrange, 3)
        triplerange = range(-testrange, testrange, 3)
        triplerange += triplerange
        for rangevalue in triplerange:
            value = triplestep.get()
            assert value == rangevalue, '%s returned %s, should be %s.' % (triplestep, value, rangevalue)
        print 'Tested %s %s times: passed' % (triplestep, len(triplerange))
    def test_stepwise_modifier():
        testrange = 50
        singlestep = SequentialInteger(-testrange, testrange)
        stepwise = StepwiseModifier(singlestep, 2)
        singlerange = range(-testrange, testrange)
        singlerange += singlerange
        singlerange.sort()
        for rangevalue in singlerange:
            value = stepwise.get()
            assert value == rangevalue, '%s returned %s, should be %s.' % (stepwise, value, rangevalue)
        print 'Tested %s %s times: passed' % (stepwise, len(singlerange))
        
        triplestep = SequentialInteger(-testrange, testrange, 3)
        stepwise = StepwiseModifier(triplestep, 2)
        triplerange = range(-testrange, testrange, 3)
        triplerange += triplerange
        triplerange.sort()
        for rangevalue in triplerange:
            value = stepwise.get()
            assert value == rangevalue, '%s returned %s, should be %s.' % (stepwise, value, rangevalue)
        print 'Tested %s %s times: passed' % (stepwise, len(triplerange))
    def test_random_enumeration():
        enumerations = [{'value': 1, 'name':'one'}, 
                        {'value': 2, 'name':'two'}, 
                        {'value': 3, 'name':'three'}]
        enumgenerator = RandomEnumeration(enumerations)
        for i in range(0, 100):            
            enum = enumgenerator.get()
            assert enum in enumerations, '%s returned %s.' % (enumgenerator, enum)
        print 'Tested %s 100 times: passed.' % enumgenerator
    def test_sequential_enumeration():
        enumerations = [{'value': 1, 'name':'one'}, 
                        {'value': 2, 'name':'two'}, 
                        {'value': 3, 'name':'three'}]
        enumgenerator = SequentialEnumeration(enumerations)
        for i in range(0, 100):
            enums = [enumgenerator.get(), 
                     enumgenerator.get(), 
                     enumgenerator.get()]
            assert enums == enumerations, '%s returned %s.' % (enumgenerator, enums)
        print 'Tested %s 100 times: passed.' % enumgenerator
    
    test_random_number()
    test_random_integer()
    test_sequential_integer()
    test_stepwise_modifier()
    test_random_enumeration()
    test_sequential_enumeration()
    test_sequential_number()

