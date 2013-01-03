package com.cisco.nbm.xmlrpc.v2
{
	import com.cisco.nbm.CiscoTestCase;

	public class TestMediatorRPCService extends CiscoTestCase
	{
		private static const MEDIATOR_ADDRESS:String = "http://192.168.20.20";
		
		private static const ROOT_URI:String = "/XMLRPCv2";
		
		private static const USERNAME:String = "mpxadmin";
		
		private static const PASSWORD:String = "baz";
		
		public function testCreateCall():void
		{
			var service:XMLRPCService = createService();
			
			var servicePath:String = "/services/time";
				
			var nodeCall:MediatorNodeCall = service.createCall(servicePath);
			
			assertEquals(nodeCall.uri, MEDIATOR_ADDRESS + ROOT_URI + servicePath); 
		}
		
		public function testCreateNodeInvalidType():void
		{
			var service:XMLRPCService = createService();
			
			var nodePath:String = "/services/time";
			
			try
			{
				var node:MediatorNode = service.getNode(nodePath, String) as MediatorNode;
				fail("Should have thrown an error");
			}
			catch (e:Error)
			{
				
			}
			
			
			
		}
		
		private function createService():XMLRPCService
		{
			var service:XMLRPCService = new XMLRPCService(MEDIATOR_ADDRESS,
				ROOT_URI, USERNAME, PASSWORD);
				
			return service;	
		}
	}
}