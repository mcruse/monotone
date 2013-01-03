///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.jobs
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.app.core.operations.IProgressMonitor;
	
	import mx.events.PropertyChangeEvent;
	
	/**
	 * A job is a long running operation that may be 
	 * canceled before or while it is executing.
	 */
	public class Job extends AsyncMethod
	{
		private var _canceled:Boolean = false;
		
		private var _cancellable:Boolean = false;
		
		public function Job()
		{
			
		}
		
		protected function setCancellable(value:Boolean):void
		{
			if (value != _cancellable)
			{
				var oldValue:Boolean = _cancellable;
				_cancellable = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "cancellable", oldValue, _cancellable));
			}
		}
		
		public function get cancellable():Boolean
		{
			return _cancellable;
		}

		public function run(monitor:IProgressMonitor):void
		{
			// Override 
		}
		
		protected function internalCanceled():void
		{
			// Override 
		}
		
		public function cancel():void
		{
			if (_canceled)
			{
				return;
			}
			
			if (!_cancellable)
			{
				return;
			}
			
			_canceled = true;
			
			internalCanceled();
		}
	}
}