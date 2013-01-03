///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	/**
	 * @author Robert Cadena <rocadena@cisco.com>
	 */ 
	public interface IMediatorNodeCallFactory
	{
		function createCall(node:IMediatorNode, name:String, args:Array=null, type:Class=null):MediatorNodeCall;
	}
}