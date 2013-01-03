///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	
	import mx.core.Application;
	
	[Event(name="complete", type="flash.events.Event")]
	[Event(name="error", type="flash.events.ErrorEvent")]
	internal class UndoGroup extends EventDispatcher
	{
		/**
		 * An array of <code>IUndoableOperation</code>s.
		 */
		public var operations:Array = [];
		
		public var _async:Boolean = false;
		
		private var currentOperationIndex:int = 0;
		
		// True if attached as a listener to the asynch operations
		private var _attached:Boolean = false;
		
		// True if the operation history is attached to this undo group
		public var historyAttached:Boolean = false;
		
		public function UndoGroup()
		{
		}
		
		public function addOperation(operation:IOperation):void
		{
			if (operation.isAsync)
			{
				_async = true;
			}
			
			operations.push(operation);
		}
		
		public function get async():Boolean
		{
			return _async;
		}
		
		private function internalUndoOrRedo(isUndo:Boolean, monitor:IProgressMonitor):void
		{
			if (!_attached)
			{
				attachListeners();
			}
			
			
			
			for each (var operation:IUndoableOperation in (isUndo ? operations : operations.reverse()))
			{
				if (operation.isAsync)
				{
					Application.application.callLater(isUndo ? operation.undo : operation.redo, [monitor]);
					continue;
				}
				else 
				{
					try
					{
						if (isUndo)
						{
							operation.undo(monitor);
						}
						else
						{
							operation.redo(monitor);
						}
						operationComplete(operation);
					}
					catch (e:Error)
					{
						operationError(e.message);
						throw e;
						return;
					}
				}
			}
		}
		
		public function undo(monitor:IProgressMonitor):void
		{
			internalUndoOrRedo(true, monitor);
		}
		
		public function redo(monitor:IProgressMonitor):void
		{
			internalUndoOrRedo(false, monitor);
		}
		
		public function attachListeners():void
		{
			for each (var operation:IOperation in operations)
			{
				if (operation.isAsync)
				{
					operation.addEventListener(Event.COMPLETE, handleOperationComplete);
					operation.addEventListener(ErrorEvent.ERROR, handleOperationError);
				}
			}
			
			_attached = true;
		}
		
		public function dispose():void
		{
			for each (var operation:IOperation in operations)
			{
				if (_attached)
				{
					if (operation.isAsync)
					{
						removeListeners(operation);
					}
				}
				
				operation.dispose();
			}
		}
		
		public function removeListeners(operation:IOperation):void
		{
			trace("remove group listeners");
			operation.removeEventListener(Event.COMPLETE, handleOperationComplete);
			operation.removeEventListener(ErrorEvent.ERROR, handleOperationError);
		}
		
		private function handleOperationComplete(event:Event):void
		{
			var operation:IOperation = event.target as IOperation;
			
			operationComplete(operation);
		}
		
		private function handleOperationError(event:ErrorEvent):void
		{
			operationError(event.text);
		}
		
		private function operationError(text:String):void
		{
			trace("error handling operation: text");
			finishedAllOperations();
			dispatchError(text);
		}
		
		private function dispatchError(text:String):void
		{
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, text));
		}
		
		public function operationComplete(operation:IOperation):void
		{
			
			currentOperationIndex++;
			
			if (currentOperationIndex == operations.length)
			{
				finishedAllOperations();
			}
		}
		
		private function dispatchComplete():void
		{
			var event:Event = new Event(Event.COMPLETE);
			dispatchEvent(event);
		}
		
		private function finishedAllOperations():void
		{
			currentOperationIndex = 0;
			dispatchComplete();
		}
	}
}