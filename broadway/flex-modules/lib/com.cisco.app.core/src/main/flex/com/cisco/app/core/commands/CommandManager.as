///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.commands
{
	import flash.events.EventDispatcher;
	import flash.events.IEventDispatcher;
	
	import mx.collections.ArrayCollection;
	import mx.events.PropertyChangeEvent;
	import mx.events.PropertyChangeEventKind;


	[Event(name="commandChange", type="com.cisco.app.core.commands.CommandChangeEvent")]
	
	/**
	 * The CommandManager serves as a directory of commands and
	 * the creator of commands. Do not create command classes
	 * directly, instead <code>getCommand</code> from an instance
	 * of this class and use it.  
	 */
	public class CommandManager extends EventDispatcher implements ICommandService
	{
		private var _commands:ArrayCollection = new ArrayCollection();
		
		private var _definedCommands:ArrayCollection = new ArrayCollection();
		
		private var _cachedDefinedCommandIds:ArrayCollection = new ArrayCollection();
		
		public function CommandManager()
		{
			super();
		}
		
		/**
		 * Get a command from the manager.  If the command has not 
		 * been previously created it will be created.  Note
		 * that the command is left in an undefined state.
		 * 
		 * @param id The command identifier
		 * @return A command, possibly undefined.
		 */
		public function getCommand(id:String):Command
		{
			var command:Command = findCommandById(id);
			
			if (command == null)
			{
				command = new Command(id);
				_commands.addItem(command);
				
				// Add selves to command to listen for defined updates
				command.addEventListener(PropertyChangeEvent.PROPERTY_CHANGE, handleCommandPropertyChange);
			}
			
			return command;
		}
		
		/**
		 * Get a list of all the commands.
		 */
		public function getAllCommands():ArrayCollection
		{
			return _commands;
		}
		
		/*
		 * Convenience function to find the command with
		 * <code>commandId</code>.
		 */ 
		private function findCommandById(commandId:String):Command
		{
			for each (var command:Command in _commands)
			{
				if (command.id == commandId)
				{
					return command;
				}
			}
			
			return command;
		}
		
		private function handleCommandPropertyChange(event:PropertyChangeEvent):void
		{
			var command:Command = event.source as Command;
			
			if (event.kind == PropertyChangeEventKind.UPDATE)
			{
				if (event.property == "defined")
				{
					if (event.newValue == true)
					{
						if (!_definedCommands.contains(command))
						{
							_definedCommands.addItem(command);
						}
					}
					else
					{
						if (_definedCommands.contains(command))
						{
							_definedCommands.removeItemAt(_definedCommands.getItemIndex(command));
						}
					}
				}
			}
			
			dispatchEvent(new CommandChangeEvent(command, event.property as String, 
				event.oldValue, event.newValue));
		}
	}
}