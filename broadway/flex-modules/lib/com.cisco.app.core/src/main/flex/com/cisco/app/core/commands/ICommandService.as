///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.commands
{
	import mx.collections.ArrayCollection;
	
	/**
	 * Interface implemented by the CommandManager
	 * 
	 * @author Robert Cadena
	 */
	public interface ICommandService
	{
		/**
		 * Get the command with the given identifier.  If no such command 
		 * currently exists, then the command will be created but undefined.
		 * 
		 * @param id The identifier to find.  Must not be <code>null</code>  and must not be zero-length.
		 * @return The command with the given identifier.  This will never be <code>null</code> but it might be undefined.
		 * 
		 */
		function getCommand(id:String):Command;
		
		/**
		 * Get all the commands managed by the service
		 * 
		 * @return All the commands managed by the service.
		 */
		function getAllCommands():ArrayCollection;
	}
}