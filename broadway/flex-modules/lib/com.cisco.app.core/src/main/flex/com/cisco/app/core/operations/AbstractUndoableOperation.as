///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	public class AbstractUndoableOperation extends AbstractOperation implements IUndoableOperation
	{
		public function AbstractUndoableOperation(label:String)
		{
			super(label);
		}
		
		public function canUndo():Boolean
		{
			return true;
		}
		
		public function canRedo():Boolean
		{
			return true;
		}
		
		public function undo(monitor:IProgressMonitor):void
		{
			throw new Error("undo not implemented");
		}
		
		public function redo(monitor:IProgressMonitor):void
		{
			throw new Error("redo not implemented");
		}
		
	}
}