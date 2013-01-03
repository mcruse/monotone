from __future__ import with_statement
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
"""
    Tools and types useful for deferred actions, such as 
    responses to asynchronous commands.
"""
from threading import Lock
from threading import Event
Undefined = object()

class Deferred(object):
    """
        Represent a pending response to action, notifying 
        listeners once the response is ready.
        
        Deferred instances can be returned by methods in place 
        of a result.  The instance allows registration of call-backs 
        to will notify listeners when the result of the action is 
        ready.  
        
        The call-backs must be callable objects, and they 
        are passed the result that would have been passed by the 
        method had it not returned a deferred instance.
        
        Methods returning Deferred instances use the instance's 
        succeeded(result) method to notify the deferred, and all 
        registered result call-backs, that he result is now ready.  
        
        Methods returning Deferred instances use the instance's 
        failed(error) method to notify the deferred, and all 
        registered error call-backs, that an exception has occurred. 
        
        Call-backs registered for success are passed a single 
        parameter by the deferred when a result is ready.  The 
        single parameter passed is the result object.
        
        Call-backs registered for errors are passed a single 
        parameter by the deferred when the result is ready.  
        The single parameter passed is the error object.
                
        Multiple call-backs can be registered on a single 
        Deferred instance.  These call-backs form a processing 
        chain that will be used in a pipe-and-filters manner.
        
        Each call-back is expected to return a value.  This 
        value becomes the current value of the deferred.  The 
        current value of the deferred is what is passed by the 
        deferred to each call-back.  In this manner, the result 
        returned by one call-back, becomes the value passed to 
        the next call-back.
        
        The order in which call-backs are invoked is determined 
        by the order in which they are registered.  There is no 
        mechanism for manipulating the ordering once registered.
        The most common cases of call-back chaining will be 
        setup and managed based on some particular task, so 
        modifying the order may not be a common need.
        
        The actions taken by a deferred depend upon the context 
        and value of the deferred.  When a failure is being handled, 
        the deferred uses all registered error call-backs exactly as 
        it would normal call-backs.  
        
        If, in the course of handling an error, an error handler 
        runs without raising an exception, or returning an instance 
        of Exception, the deferred switches from invoking registered 
        error handlers, to invoking registered success handlers.  If, 
        in the course of handling a valid result, a call-back returns 
        a value that is an instance of Exception, or a call-back 
        invocation results in the throwing of an exception, the 
        deferred switches from invoking registered success call-backs, 
        to invoking registered error call-backs.
        
        Both these behaviours are the result of the fact that, whether 
        processing successful responses or failure responses, the 
        deferred assumes the value returned by each successive 
        call-back.  The next action taken by the deferred is always 
        based on the deferred's current value, and so exceptions 
        are passed to registered error-handlers and valid results 
        are passed to registered success-handlers, even if doing so 
        causes the deferred to switch between them during processing.
        
        Any time an instance of Deferred is returned by a call-back, 
        the deferred automatically chains its own execution to the 
        completion the returned deferred.  This means that any 
        call-back may return an instance of deferred itself.  When 
        this is done, any subsequent call-backs will not be invoked 
        until the returned deferred has indicated completion and 
        given a result to the initial deferred.  Just like with 
        normal call-backs, the outer deferred assumes whatever 
        value is returned by the inner-deferred, and handling 
        proceeds as it would have if the result were returned 
        directly.
 
        Deferred instances are either incomplete or complete.  The 
        invocation of a deferred's "succeeded(result)" or its 
        "failed(error)" method both result in the deferred's state 
        changing to completed.  An exception is raised if either of 
        these methods are invoked on a deferred which is already 
        in the complete state.
        
        It is not an error, however, to attach additional handlers 
        to a completed deferred.  If the deferred is already complete, 
        the call-back will be invoked immediately following its 
        registration (and before the registration call itself returns).
        
        This allows continued processing of a deferred's value 
        to take place after the deferred itself has been completed.
        It also allows clients of a deferred to interact with the 
        deferred without concern for the deferred's state.  Whether 
        the deferred's value has been set or not, clients can 
        always register handlers and will always be notified of 
        completion and the current value.
    """
    def __init__(self):
        self.value = Undefined
        self.error = Undefined
        self.current = Undefined
        self._handlers = []
        self._synclock = Lock()
        self._initiated = Event()
        super(Deferred, self).__init__()
    def iserror(self):
        return self.error is not Undefined
    def isvalue(self):
        return self.value is not Undefined
    def initiated(self):
        return self._initiated.isSet()
    def register(self, callback=None, errback=None):
        with self._synclock:
            self._handlers.appned((callback, errback))
        if self.initiated():
            self._unwind()
    def unregister(self, callback=None, errback=None):
        with self._synclock:
            self._handlers.remove((callback, errback))
    def register_callback(self, handler):
        return self.register(callback, None)
    def unregister_callback(self, callback):
        return self.unregister(callback, None)
    def register_errback(self, errback):
        return self.register(None, errback)
    def unregister_errback(self, errback):
        return self.unregister(None, errback)
    def callback(self, result):
        self._initiate()
        self._callback(result)
    succeeded = callback
    def errback(self, error):
        self._initiate()
        self._errback(error)
    failed = errback
    def _initiate(self):
        with self._synclock:
            if self.initiated():
                raise TypeError("Deferred already complete.")
            self._initiated.set()
    def _callback(self, result):
        self.error = Undefined
        self.current = result
        self.value = result
        self._unwind()
    def _errback(self, error):
        self.value = Undefined
        self.current = error
        self.error = error
        self._unwind()
    def _unwind(self):
        with self._synclock:
            handler = None
            while self._handlers and not handler:
                callback,errback = self._handlers.pop(0)
                if self.iserror():
                    handler = errback
                else:
                    handler = callback
        if handler:
            try:
                result = handler(self.value)
            except Exception, error:
                # Called within exception context for trace ability.
                self._errback(error)
            else:
                if isinstance(result, Exception):
                    # Callback returned exception, so 
                    # handle as an error would be handled.
                    self._errback(result)
                elif isinstance(result, Deferred):
                    # Callback returned a deferred, indicating 
                    # that the callback has not yet generated 
                    # its return value.  Register with the 
                    # deferred and exit unwinding.  Unwinding 
                    # will pick up where it left off when the 
                    # deferred gives us the callback's result.
                    result.register(self._callback, self._errback)
                else:
                    self._callback(result)
        return len(self._handlers)
    def getvalue(self, blocking=True, timeout=None):
        """
            Return deferred's value.  If it is an 
            exception, raise the exception.
        """
        if blocking:
            self._initiated.wait(timeout)
        with self._synclock:
            if not self.initiated():
                raise TypeError("Deferred is not complete.")
            current = self.current
            exception = self.iserror()
        if exception:
            raise current
        return current
