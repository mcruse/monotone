package com.cisco.nbm.navigator
{
	import com.cisco.nbm.xmlrpc.v2.XMLRPCService;
	
	import flash.events.EventDispatcher;
	
	public class LocationNavigationService extends EventDispatcher
	{
		private var service:XMLRPCService;
		
		public function LocationNavigationService(service:XMLRPCService)
		{
			this.service = service;
		}

		public function loadNode(path:String, force:Boolean=false):Callback
		{
			
		}
	}
}