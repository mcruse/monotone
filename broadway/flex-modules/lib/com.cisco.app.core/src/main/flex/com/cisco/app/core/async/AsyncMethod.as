///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.async
{
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.utils.Dictionary;

	/**
	 * Executs a method asynchronously.  You can add two functions that can
	 * be called back when the method finishes executing (or ends in an error)
	 * and you can register as an event listener for Event.COMPLETE, and 
	 * Event.ERROR
	 * 
	 * You can add callback/errbacks after the call has completed and they
	 * will be called immediately after being added.  So, there is no need
	 * to worry about when callback/errbacks can be added.
	 * 
	 * <b>Callback/Errback Signature</b>
	 * Both the callback and errback  must have the following signature:
	 * 
	 * <code>
	 * 	function my_callback(method:AsyncMethod, result:Object):void;
	 * 	function my_errback(method:AsyncMethod, error:Object):void;
	 * </code>
	 * 
	 * The <b>method</b> parameter will contain the method that is
	 * calling the callback/errback.  
	 * 
	 * The <b>result</b> object contains any result returned by the call.  
	 * It may be null.
	 * 
	 * The <b>error</b> object contains some object describing the error.
	 * It may be an Error object or a string.  The type is specific to the call.
	 */
	public class AsyncMethod extends EventDispatcher
	{
		/**
		 * Callers can set a token on the method.  Note
		 * that the token is not attached to a listener
		 * so if another listener or interested party
		 * sets the token then the initial value may be 
		 * overriden.
		 */
		public var token:Object = null;
		
		/*
		 * Result is stored here
		 */
		protected var _result:Object = null
		
		/*
		 * Dictionary of weak values of callback functions
		 * that will be called when the method results in 
		 * a regular result and not an error.
		 */
		protected var callbacks:Dictionary = new Dictionary(true);
		
		/*
		 * Dictionary of weak values of callback functions
		 * that will be called when an error happens.
		 */
		protected var errbacks:Dictionary = new Dictionary(true);
		
		/*
		 * Flag indicating if the result of the call was an error.
		 */
		protected var wasError:Boolean = false;
		
		/*
		 * The error object if the result was an error.
		 */
		protected var _error:Object = null;
		
		/*
		 * Flag indicating if the call has completed.
		 * If a callback/errback is added after the call
		 * has completed then they will be called 
		 * immediately after they are added and then discarded.
		 */
		protected var finished:Boolean = false;
		
		public function AsyncMethod()
		{
			super();
		}
		
		//------------------------------------------
		// Public methods
		//------------------------------------------
		
		/**
		 * Add a pair of callback/errback functions.
		 * 
		 * If the call has completed, then the appropriate function
		 * will be called immediately.
		 * 
		 * See the documentation for this class for information about the
		 * callback/errback signature.
		 * 
		 * @param callback  The function to call if the method is succesful
		 * @param errback The function to call if the method results in an error. 
		 */
		public function addCallback(callback:Function, errback:Function):void
		{
			if (finished)
			{
				notifyAttached();	
				return;
			}
			
			if (callback != null)
			{
				callbacks[callback] = callback;
			}
			
			if (errback != null)
			{
				errbacks[errback] = errback;
			}
		}
		
		//------------------------------------------
		// Property getters and setters
		//------------------------------------------
		
		/**
		 * The error object is the call resulted in an error
		 */
		public function get error():Object
		{
			return _error;
		}

		//------------------------------------------
		// Protected methods
		//------------------------------------------
		
		/*
		 * Set the error object
		 */
		protected function setError(value:Object):void
		{
			_error = value;
		}
		
		/* 
		 * Set the result object
		 */
		protected function setResult(value:Object):void
		{
			_result = value;
		}
		
		/**
		 * Override to perform functions after the call is completed.
		 */
		protected function internalHandleComplete():void
		{
			// Override with own function
		}
		
		/**
		 * Dispatches an error if the call was unsuccesful.
		 */
		protected function dispatchError():void
		{
			wasError = true;
			notifyAttached();
			cleanup();
			
			// TODO Should dispatch from the system?
			//Application.application.dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, new String(_error)));
		}
		
		/**
		 * Override to cleanup the call.
		 */
		protected function cleanup():void
		{
			// Override
		}

		//------------------------------------------
		// Private functions
		//------------------------------------------
		
		/*		
		 * Notify all attached callbacks or errbacks of the
		 * result of the method call.
		 */
		private function notifyAttached():void
		{
			if (wasError)
			{
				for each (var errback:Function in errbacks)
				{
					try {	
						errback(this, _error);
					} catch (e:Error) {
						trace("error thrown while executing errback: " + e.message);
						trace(e.getStackTrace());
					}
				}
			}
			else
			{
				for each (var callback:Function in callbacks)
				{
					try {
						callback(this, _result); // I don't like this but we'll keep it for now
					} catch (e:Error) {
						trace("error thrown while executing callback: " + e.message);
						trace(e.getStackTrace());
					}
				}
			}
			
			removeAllAttached();
		}
		
		private function removeAllAttached():void
		{
			for each (var thing:Function in errbacks)
			{
				delete errbacks[thing];
			}
			
			for each (thing in callbacks)
			{
				delete callbacks[thing];
			}
		}
		
		
		public function handleComplete():void
		{
			finished = true;
			
			try
			{
				internalHandleComplete();
				dispatchComplete();
			}
			catch (e:Error)
			{
				wasError = true;
				setError(e.message);
				dispatchError();
			}
			
			notifyAttached();			
		}
		
		private function dispatchComplete():void
		{
			cleanup();
			dispatchEvent(new Event(Event.COMPLETE));
		}
		
	}
}