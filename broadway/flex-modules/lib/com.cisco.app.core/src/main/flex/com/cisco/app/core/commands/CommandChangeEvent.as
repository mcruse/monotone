///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.commands
{
	import flash.events.Event;
	
	/**
	 * This event is published when a command changes a property.
	 * 
	 */
	public class CommandChangeEvent extends Event
	{
		public static const COMMAND_CHANGE:String = "commandChange";
		
		public var command:Command;
		
		public var propertyName:String;
		
		public var oldValue:Object;
		
		public var newValue:Object;
		
		public function CommandChangeEvent(command:Command, propertyName:String, oldValue:Object, newValue:Object)
		{
			super(COMMAND_CHANGE);
			
			this.command = command;
			this.propertyName = propertyName;
			this.oldValue = oldValue;
			this.newValue = newValue; 
		}
		
		override public function toString():String
		{
			return "CommandChangeEvent(command="+command+", propertyName="+propertyName+", " +
				"oldValue="+oldValue+", newValue="+newValue+")";
		}
		
		override public function clone():Event
		{
			var newEvent:CommandChangeEvent = new CommandChangeEvent(command, propertyName, oldValue, newValue);
			
			return newEvent;
		}
	}
}