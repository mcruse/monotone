///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.ui
{
	import com.cisco.app.core.commands.Command;
	import com.cisco.app.core.commands.CommandManager;
	
	import flash.events.EventDispatcher;
	
	import mx.collections.ArrayCollection;

	public class HandlerManager extends EventDispatcher implements IHandlerService
	{
		private var _activeHandlers:ArrayCollection = new ArrayCollection();
		
		private var commandManager:CommandManager;
		
		public function HandlerManager(commandManager:CommandManager)
		{
			super(null);
			
			this.commandManager = commandManager;
		}
		
		public function activateHandler(commandId:String, handler:IHandler):void
		{
			var command:Command = commandManager.getCommand(commandId);
			
			if (!command.defined)
			{
				trace("command is not defined, handler cannot handle command: " + commandId + ", " + handler);
				return;
			}
			
			command.handler = handler;
		}
		
		public function executeCommand(commandId:String, parameters:Object=null, event:Object=null):Object
		{
			var command:Command = commandManager.getCommand(commandId);
			
			if (!command.defined)
			{
				trace("Command " + commandId + " is not defined");
				return null;
			}
			
			if (!command.handler)
			{
				trace("Command " + commandId + " does not have a handler");
				return null;
			}
			
			var executionEvent:ExecutionEvent = new ExecutionEvent(command, parameters);
			
			return command.execute(executionEvent);
		}
		
		
		
	}
}