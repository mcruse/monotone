///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	public interface IUndoableOperation extends IOperation
	{
		function canUndo():Boolean;
		
		function canRedo():Boolean;
		
		function undo(monitor:IProgressMonitor):void;
		
		function redo(monitor:IProgressMonitor):void;
	}
}