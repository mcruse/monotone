///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import flash.events.Event;

	public class UndoableOperationEvent extends Event
	{
		public static const UNDO_COMPLETE:String = "undoComplete";
		
		public static const REDO_COMPLETE:String = "redoComplete";
		
		public function UndoableOperationEvent(type:String)
		{
			super(type, false, false);
		}
		
	}
}