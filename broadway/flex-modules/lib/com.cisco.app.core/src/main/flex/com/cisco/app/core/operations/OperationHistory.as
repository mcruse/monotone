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
	
	import mx.collections.ArrayCollection;
	import mx.core.Application;
	import mx.events.PropertyChangeEvent;
	
	[Event(name="complete", type="flash.events.Event")]
	[Event(name="error", type="flash.events.ErrorEvent")]
	[Event(name="beginUndoing", type="com.cisco.app.core.operations.OperationHistoryEvent")]
	[Event(name="beginAsync", type="com.cisco.app.core.operations.OperationHistoryEvent")]
	[Event(name="endAsync", type="com.cisco.app.core.operations.OperationHistoryEvent")]
	public class OperationHistory extends EventDispatcher implements IOperationHistoryService
	{
		public var debug:Boolean;
		
		private var undoStack:ArrayCollection = new ArrayCollection();
		
		private var redoStack:ArrayCollection = new ArrayCollection();
		
		private var openGroup:UndoGroup;
		
		private var _redoActionName:String;
		
		private var _undoActionName:String;
		
		private var _canUndo:Boolean = false;
		
		private var _canRedo:Boolean = false;
		
		private var _isExecuting:Boolean = false;
		
		private var _isUndoing:Boolean = false;
		
		private var _isRedoing:Boolean = false;
		
		private var _isAsync:Boolean = false;
		
		// Set to true if the closeGroup was called but it could not be closed because the isExecuting flag was set to true
		private var _askedToCloseGroup:Boolean = false;
		
		public function clear():void
		{
			if (openGroup != null)
			{
				closeUndoGroup();
			}
			
			undoStack.removeAll();
			redoStack.removeAll();
			
			setCanRedo(false);
			setCanUndo(false);
			setIsExecuting(false, false);
			
		}
		
		public function execute(operation:IUndoableOperation, monitor:IProgressMonitor=null, info:Object=null):void
		{
			if (openGroup == null)
			{
				openUndoGroup();
			}
			
			
			setCanUndo(false);
			setCanRedo(false);
			setIsExecuting(true, operation.isAsync);
			
			
			if (operation.isAsync)
			{
				// execute asyncs in the next frame so that all stuff below is done executing before the operation finishes
				setIsAsync(true);
				Application.application.callLater(operation.execute, [ monitor, info ]);
			}
			else
			{
				try
				{
					operation.execute(monitor, info);
				}
				catch (e:Error)
				{
					operationError(e.message, e.message);
				}
			}
			
			
			if (operation.canUndo())
			{	
				if (operation.isAsync)
				{
					configureOperation(operation);
					return;
				}
				
				operationFinishedExecuting(operation);
			}
			else
			{
				// dispose the operation right away
				operation.dispose();
			}
			
		}

		private function operationFinishedExecuting(operation:IUndoableOperation):void
		{			
			if (_isExecuting)
			{
				setIsExecuting(false, false);
				setIsAsync(false);
				openGroup.addOperation(operation);

				if (_askedToCloseGroup)
				{
					closeUndoGroup();
				}
			} 
			
			removeOperationListeners(operation);
			
			
			updateProperties();
			dispatchComplete();
		}
		
		private function dispatchComplete():void
		{
			dispatchEvent(new Event(Event.COMPLETE));
		}
		
		private function configureOperation(operation:IUndoableOperation):void
		{
			operation.addEventListener(Event.COMPLETE, handleOperationComplete, false, 0, true);
			operation.addEventListener(Event.CANCEL, handleOperationCancel, false, 0, true);
			operation.addEventListener(ErrorEvent.ERROR, handleOperationError, false, 0, true);
		}
		
		private function handleOperationError(event:ErrorEvent):void
		{
			var operation:IUndoableOperation = event.target as IUndoableOperation;
			operationError(operation, event.text);
		}
		
		private function dispatchError(text:String):void
		{
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, text));
			updateProperties();
		}
		
		private function operationError(operation:IUndoableOperation, text:String):void
		{
			setIsExecuting(false, false);
			removeOperationListeners(operation);
			
			if (openGroup)
			{
				// remove openGroup
				clearUndoGroup(openGroup);
				openGroup = null;
			}
						
			updateProperties();
			dispatchError(text);
		}
		
		private function handleOperationCancel(event:Event):void
		{
			var operation:IUndoableOperation = event.target as IUndoableOperation;
			setIsExecuting(false, false);
			removeOperationListeners(operation);
		}
		
		private function removeOperationListeners(operation:IUndoableOperation):void
		{
			operation.removeEventListener(Event.COMPLETE, handleOperationComplete, false);
			operation.removeEventListener(Event.CANCEL, handleOperationCancel, false);
			operation.removeEventListener(ErrorEvent.ERROR, handleOperationError, false);
		}
		
		private function handleOperationComplete(event:Event):void
		{
			var operation:IUndoableOperation = event.target as IUndoableOperation;
			
			operationFinishedExecuting(operation);
		}
		
		
		/**
		 * Close a currently open undo group.  
		 * 
		 * If the currently open undo group has no operations then no 
		 * undo group is pushed to the stack.
		 */
		public function closeUndoGroup():void
		{
			if (_isExecuting)
			{
				_askedToCloseGroup = true;
				return;
			}
			
			_askedToCloseGroup = false;
			
			if (openGroup != null && openGroup.operations.length > 0)
			{
				undoStack.addItem(openGroup);
				clearRedoStack();
			}
			
			openGroup = null
			
			updateProperties();
		}
		
		private function clearUndoGroup(group:UndoGroup):void
		{
			if (attachedGroups[group] == true)
			{
				group.removeEventListener(Event.COMPLETE, handleGroupComplete);
				group.removeEventListener(ErrorEvent.ERROR, handleGroupError);
				
				delete attachedGroups[group];
			}
			
			group.dispose();
		}
		
		/**
		 * Called when a group is done unoding or redoing
		 */
		private function handleGroupComplete(event:Event):void
		{
			var group:UndoGroup = event.target as UndoGroup;
			
			if (_isRedoing)
			{
				finishRedoing(group);
			}
			else if (_isUndoing)
			{
				finishUndoing(group);
			}
		}
		
		private function handleGroupError(event:ErrorEvent):void
		{
			setIsExecuting(false, false);
			updateProperties();
			dispatchError(event.text);
		}

		private function clearRedoStack():void
		{	
			if (redoStack.length == 0)
			{
				return;
			}
			
			for each (var group:UndoGroup in redoStack) 
			{
				clearUndoGroup(group);	
			}
			
			redoStack.removeAll();
			
			redoActionName = null;
			
			updateProperties();
		}
		
		/**
		 * Opens a new undo group.  
		 * 
		 * Any existing undo groups are closed.  The undo action name is
		 * set to null. 
		 */
		public function openUndoGroup():void
		{
			closeUndoGroup();
						
			openGroup = new UndoGroup();
			
			
			_undoActionName = null;
		}
		// Map of attached undo groups
		private var attachedGroups:Object = {};
		
		private function addGroupListeners(group:UndoGroup):void
		{
			attachedGroups[group] = true;
			
			group.addEventListener(Event.COMPLETE, handleGroupComplete, false, 0, true);
			group.addEventListener(ErrorEvent.ERROR, handleGroupError, false, 0, true)
		}
		
		public function undo(monitor:IProgressMonitor=null):void
		{
			if (undoStack.length == 0)
			{
				return;
			}
		
				
			var group:UndoGroup = undoStack[undoStack.length-1] as UndoGroup;
			
			if (attachedGroups[group] != true && group.async)
			{
				addGroupListeners(group);
			}
			
			var lastError:Error;
			
			_isUndoing = true;
			
			setIsExecuting(true, group.async);
			setCanUndo(false);
			setCanRedo(false);
			
			try
			{
				group.undo(monitor);
			}
			catch (e:Error)
			{
				trace("Error undoing operation: " + e.message);
				lastError = e;
			}
			
			if (!group.async)
			{
				finishUndoing(group);
			}
			else
			{
				setIsAsync(true);
			}
		
			if (lastError != null)
			{
				dispatchError(lastError.message);
				throw lastError;
			}
		}
		
		private function finishUndoing(group:UndoGroup):void
		{
			undoStack.removeItemAt(undoStack.length-1);
			
			redoStack.addItem(group);
			_isUndoing = false;
			
			setIsExecuting(false, false);
			
			updateProperties();
			setIsAsync(false);
			
			dispatchComplete();
		}
		
		public function redo(monitor:IProgressMonitor=null):void
		{
			if (redoStack.length == 0)
			{
				return;
			}
			
			var group:UndoGroup = redoStack[redoStack.length-1] as UndoGroup;
			
			var lastError:Error;
			
			_isRedoing = true;
			
			setIsExecuting(true, group.async);
			setCanUndo(false);
			setCanRedo(false);
			
			
			try
			{
				group.redo(monitor);
			}
			catch (e:Error)
			{
				lastError = e;
			}
			
			if (!group.async)
			{
				finishRedoing(group);
			}
			else
			{
				setIsAsync(true);
			}
			
			if (lastError != null)
			{
				dispatchError(lastError.message);
				throw lastError;
			}
		}
		
		public function finishRedoing(group:UndoGroup):void
		{
			redoStack.removeItemAt(redoStack.length-1);
			undoStack.addItem(group);
			_isRedoing = false;
			
			setIsExecuting(false, false);
			setIsAsync(false);
			
			updateProperties();
			
			dispatchComplete();
		}

		
		private function updateProperties():void
		{
			if (openGroup == null)
			{
				setCanUndo(undoStack.length > 0);
				setCanRedo(redoStack.length > 0);
				
				var group:UndoGroup;
				
				if (redoStack.length > 0) 
				{
					group = redoStack[redoStack.length-1] as UndoGroup;
					redoActionName = group.operations[0].label;
				}

				if (undoStack.length > 0)
				{
					group = undoStack[undoStack.length-1] as UndoGroup;
					undoActionName = group.operations[0].label;
				}
				
			}
			
		}
		
		private function setCanUndo(value:Boolean):void
		{
			if (value != _canUndo)
			{
				var oldValue:Boolean = _canUndo;
				_canUndo = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "canUndo", oldValue, _canUndo));
			}
		}

		
		private function setCanRedo(value:Boolean):void
		{
			if (value != _canRedo)
			{
				var oldValue:Boolean = _canRedo;
				_canRedo = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "canRedo", oldValue, _canRedo));
			}
		}
		
		private function setIsExecuting(value:Boolean, asyncValue:Boolean):void
		{
			setIsAsync(asyncValue);
			trace("setIsExecuting and saync value: " + value + ", " + asyncValue);
			if (_isExecuting != value)
			{
				var oldValue:Boolean = _isExecuting;
				_isExecuting = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "isExecuting", oldValue, _isExecuting));
				
				if (value == true)
				{
					dispatchBeginUndoing();
				}
			
			}
		}
		
		private function dispatchBeginUndoing():void
		{
			var event:Event = new OperationHistoryEvent(OperationHistoryEvent.BEGIN_UNDOING);
			dispatchEvent(event);
		}
		
		// #pragma mark Properties
		[Bindable]		
		public function set undoActionName(value:String):void
		{
			if (value != _undoActionName)
			{
				var oldValue:String = _undoActionName;
			
				_undoActionName = value;
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "undoActionName", oldValue, _undoActionName));
			}
		}
		
		public function get undoActionName():String
		{
			return _undoActionName;
		}
		
		[Bindable]
		public function set redoActionName(value:String):void
		{
			if (value !== _redoActionName)
			{
				var oldValue:String = _redoActionName;
			
				_redoActionName = value;
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "redoActionName", oldValue, _redoActionName));
			}
		}
		
		public function get redoActionName():String
		{
			return _redoActionName;
		}
		
		public function set canUndo(value:Boolean):void
		{
			throw new Error("This is a read-only property");
		}
		
		[Bindable] 
		public function get canUndo():Boolean
		{
			return _canUndo;
		}

		public function set canRedo(value:Boolean):void
		{
			throw new Error("This is a read-only property");
		}
		
		[Bindable] 
		public function get canRedo():Boolean
		{
			return _canRedo;
		}
		
		[Bindable]
		public function set isExecuting(value:Boolean):void
		{
			throw new Error("This is a read-only property");
		}
		
		public function get isExecuting():Boolean
		{
			return _isExecuting;
		}
		
		[Bindable]
		public function get isAsync():Boolean
		{
			return _isAsync;
		}
		
		public function set isAsync(value:Boolean):void
		{
			throw new Error("This is a read-only property");
		}
		
		private function setIsAsync(value:Boolean):void
		{
			if (value != _isAsync)
			{
				var oldValue:Boolean = _isAsync;
				_isAsync = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "isAsync", oldValue, _isAsync));
			}
		}

		// #pragma mark Misc. methods
		public function dumpStack():void
		{
			trace("****************");
			trace("undo stack: " + undoStack);
			trace("redo stack: " + redoStack);
			trace("****************");
		}

	}
}