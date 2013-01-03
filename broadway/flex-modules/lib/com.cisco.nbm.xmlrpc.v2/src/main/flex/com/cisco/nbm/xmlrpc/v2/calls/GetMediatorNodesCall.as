///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2.calls
{
	import com.cisco.nbm.xmlrpc.v2.IMediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	import com.cisco.nbm.xmlrpc.v2.XMLRPCService;

	/**
	 * TBD
	 */
	public class GetMediatorNodesCall extends MediatorNodeCall
	{
		public function GetMediatorNodesCall(service:XMLRPCService, node:IMediatorNode, name:String=null, args:Array=null)
		{
			super();
			init(service, node, "children_names", 5000);
		}
		
		override protected function parseResult(data:String):Object
		{
			var names:Array = super.parseResult(data) as Array
			var nodes:Array = [];
			
			for each (var name:String in names)
			{
				var newNode:IMediatorNode = _service.getNode(_node.path + "/"+ name);
				nodes.push(newNode);
				
			}
			
			return nodes; 
		}
	}
}