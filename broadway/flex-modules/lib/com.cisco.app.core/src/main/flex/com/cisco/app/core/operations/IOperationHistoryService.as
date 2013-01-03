///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import flash.events.IEventDispatcher;
	
	public interface IOperationHistoryService extends IEventDispatcher
	{
		function execute(operation:IUndoableOperation, monitor:IProgressMonitor=null, info:Object=null):void;
		function undo(monitor:IProgressMonitor=null):void;
		function redo(monitor:IProgressMonitor=null):void;
		
		function closeUndoGroup():void
		function openUndoGroup():void;
		
		function get canUndo():Boolean;
		
		// Setter only there for binding
		function set canUndo(value:Boolean):void;
		
		function get canRedo():Boolean;
		function set canRedo(value:Boolean):void;
		
		function set undoActionName(value:String):void;
		function get undoActionName():String;
		
		function set redoActionName(value:String):void;
		function get redoActionName():String;
		
	}
}