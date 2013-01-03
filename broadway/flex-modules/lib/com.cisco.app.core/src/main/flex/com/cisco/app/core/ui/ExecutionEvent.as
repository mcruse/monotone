///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.ui
{
	import com.cisco.app.core.commands.Command;
	
	public class ExecutionEvent
	{
		
		private var _command:Command;
		
		private var _parameters:Object;
		
		public function ExecutionEvent(command:Command, parameters:Object=null)
		{
			this._command = command;
			
			if (parameters == null)
			{
				_parameters = {};
			}
			else
			{
				_parameters = parameters;
			}
		}
		
		public function get parameters():Object
		{
			return _parameters;
		}
		
		public function get command():Object
		{
			return _command;
		}
		
		public function toString():String
		{
			return "ExecutionEvent(command=" + _command + ", " +
				"parameters=" + _parameters +")";
		}

	}
}