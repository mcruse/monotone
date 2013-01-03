///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.clipboard
{
	import flash.events.Event;
	import flash.events.EventDispatcher;


	[Event(name="change", type="flash.events.Event")]
	/**
	 * This is an internal clipboard service used for browser based flex
	 * applications.  It does not currently work with the system clipboard
	 * though this is in the works.   
	 */
	public class InternalClipboardService extends EventDispatcher implements IInternalClipboardService
	{
		private var _data:Object = null;
		
		public function InternalClipboardService()
		{
			
		}
		
		
		public function clear():void
		{
			_data = null;
			dispatchChangeEvent();
		}
		
		public function getData():Object
		{
			return _data;	
		}
		
		public function setData(data:Object):void
		{
			if (_data !== data)
			{
				_data = data;
				
				dispatchChangeEvent();
			}
		}
		
		private function dispatchChangeEvent():void
		{
			var event:Event = new Event(Event.CHANGE);
			dispatchEvent(event);
		}
		
	}
}