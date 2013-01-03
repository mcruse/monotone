///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import flash.events.IEventDispatcher;
	
	/**
	 * Interface that all node must implement.
	 *
	 * @author Robert Cadena <rocadena@cisco.com>
	 */
	public interface IMediatorNode extends IEventDispatcher
	{
		function init(service:XMLRPCService, name:String, path:String):void;
			
		function get configObject():Object;
		
		function getService():XMLRPCService;
		
		function refresh():void;
			
		function getattr(attributeName:String):MediatorNodeCall;
		
		function hasattr(attributeName:String):MediatorNodeCall;
		
		function setattr(attributeName:String, value:*):MediatorNodeCall;
		
		function configure(params:Object):MediatorNodeCall;
		
		function configuration():MediatorNodeCall;
		
		function start():MediatorNodeCall;
		
		function stop():MediatorNodeCall;
		
		function has_child(name:String):MediatorNodeCall;
		
		function get_child(name:String):MediatorNodeCall;
		
		function children_nodes():MediatorNodeCall;
		
		function children_names():MediatorNodeCall;
		
		function get_value():MediatorNodeCall;
		
		function get children():Array;
		
		function set_value(value:*):MediatorNodeCall;
		
		function get callFactory():IMediatorNodeCallFactory;
		
		function set callFactory(value:IMediatorNodeCallFactory):void;
		
		function get name():String;
		
		function get path():String;
		
		function setPath(value:String):void;
		
		function execute(methodName:String, args:Array):MediatorNodeCall;
		
		function destroy():void;
	}
}