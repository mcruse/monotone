package com.cisco.ui.components
{
	import flash.events.TimerEvent;
	
	import mx.collections.IHierarchicalCollectionViewCursor;
	import mx.controls.AdvancedDataGrid;
	import mx.controls.advancedDataGridClasses.AdvancedDataGridColumn;
	import mx.controls.advancedDataGridClasses.AdvancedDataGridListData;
	import mx.controls.listClasses.BaseListData;
	import mx.core.EventPriority;
	import mx.events.AdvancedDataGridEvent;
	import mx.events.DragEvent;
	import mx.events.ListEvent;
	import mx.logging.ILogger;
	import mx.logging.Log;
	import mx.managers.CursorManager;
	import mx.managers.DragManager;
	import mx.styles.CSSStyleDeclaration;
	import mx.styles.StyleManager;
	
	[Event(name="changing", type="com.cisco.ui.components.CiscoTreeEvent")]
	[Event(name="changed", type="com.cisco.ui.components.CiscoTreeEvent")]
	
	/**
	 * This implementation supports the following additional behaviors:
	 * 
	 * <ul>
	 * 	<li>Spring-loaded Folders: Automatically opens folders if the user is dragging
	 * 	 	an item onto the tree and hovers for some amount of time over a folder that is closed.</li>
	 * </ul>
	 * 
	 * The Spring-loaded source is based on this code:
	 * 
	 * http://flexibleexperiments.wordpress.com/2007/02/26/flex-201-tree-with-spring-loaded-folders-update-2/
	 * 
	 * <b>NOTE</b>: This implementation assumes that the items in the dataprovider
	 * have a children property and that the children property has a length 
	 * property.  Future versions will fix this so that this is not a requirement.
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 */
	public class CiscoTree extends AdvancedDataGrid
	{
		protected var logger:ILogger = Log.getLogger("cisco.ui.components.CiscoTree");
				
		private var _delayedTimer:DelayedTimer = new DelayedTimer();
		
		private var _lastNodeOver:Object = null;
		
		private var _cleanupDelayedTimer:DelayedTimer = new DelayedTimer();
		
		private var openedFolderHierarchy:Object;
		
		private var oldSelections:Array;
		
		private var nextSelections:Array;
		
		public var _canDropFunction:Function = null;
		
		public function CiscoTree()
		{
			super();
			
			
			addEventListener(DragEvent.DRAG_OVER, handleDragOver);
			addEventListener(DragEvent.DRAG_DROP,handleDragDrop, false, 99, false);
			addEventListener(DragEvent.DRAG_COMPLETE,handleDragComplete);
            addEventListener(DragEvent.DRAG_EXIT,handleDragExit);
            addEventListener(DragEvent.DRAG_START,handleDragStart);
            
			addEventListener(AdvancedDataGridEvent.ITEM_CLOSE,handleItemClose);
            addEventListener(ListEvent.CHANGE, handleItemChange);
            
		}

		public function set canDropFunction(value:Function):void
		{
			_canDropFunction = value;
		}
		
		public function get canDropFunction():Function
		{
			return _canDropFunction;
		}
		
		private function handleItemChange(event:ListEvent):void
		{
			trace("selections: " + selectedItems);
			trace("\t" + selectedIndices);
			nextSelections = selectedItems;
			
			
			var newEvent:CiscoTreeEvent = new CiscoTreeEvent(CiscoTreeEvent.CHANGING, false, true);
			newEvent.nextSelections = nextSelections;
			
			if (dispatchEvent(newEvent)) {
				oldSelections = nextSelections;
				dispatchEvent(new CiscoTreeEvent(CiscoTreeEvent.CHANGED));
			}
			else
			{
				selectedItems = oldSelections;
				
			}
		}
		
		private function handleDragDrop(event:DragEvent):void
		{
			//event.preventDefault();
			
			if (CursorManager.currentCursorID == rejectCursorID)
			{
				event.preventDefault();
				event.stopImmediatePropagation();	
			}
			hideDropFeedback(event);
		}
		
		/*
		 * Fixing drag start bug not yet fixed! http://bugs.adobe.com/jira/browse/FLEXDMV-2100
		 */
		public override function set dragEnabled(value:Boolean):void
		{
			if (dragEnabled && !value)
			{
				removeEventListener(DragEvent.DRAG_START, dragStartWorkingHandler, false);
			}
			
			super.dragEnabled = value;
			
			if (value)
			{
				addEventListener(DragEvent.DRAG_START, dragStartWorkingHandler, false, EventPriority.DEFAULT_HANDLER);
			}
		}
		
		/*
		 * Part of fix for http://bugs.adobe.com/jira/browse/FLEXDMV-2100
		 */
		protected function dragStartWorkingHandler(event:DragEvent):void
		{
			super.dragStartHandler(event);
		}
		
		/*
		 * Part of fix for http://bugs.adobe.com/jira/browse/FLEXDMV-2100
		 */
		protected override function dragStartHandler(event:DragEvent):void
		{
			dispatchEvent(event);
		}
	
		private function handleDragStart(event:DragEvent):void
		{
			var nodes:Object = dataProvider.openNodes;
			
			// The documentation on openNodes is unclear and it makes it sound
			// as if the value is an array of objects but it is, instead, an 
			// object with UUIDs as the keys and the nodes as the values of the
			// object.  For convenience, we convert it to an array here
			openedFolderHierarchy = [];
			for each (var name:Object in nodes)
			{
				openedFolderHierarchy.push(name);
			}
			
			var sel:Object = event.currentTarget.selectedItems;
			
			for (var i:int = 0; i < sel.length; i++)
			{
				/// determine if any of the items cannot be dragged
			}
		}
	
		private function handleDragOver(event:DragEvent):void
		{
			var idx:int = calculateDropIndex(event);
			var currNodeOver:Object = indexToItemRenderer(idx);
			if (draggingOverSelf(event))
			{
				showRejectDropCursor(true);
				_delayedTimer.cancelDelayedTimer();
				return;
			}
			
			if (canDropFunction != null && !internalCanDrop(event))
			{
				showRejectDropCursor(true);
				return;
			}
			
			if (currNodeOver != _lastNodeOver)
			{
				_delayedTimer.cancelDelayedTimer();
				
			}
			
			showRejectDropCursor(false);
			if (currNodeOver != null)
			{
				if (isItemOpen(currNodeOver.data) == false)
				{
					if (_delayedTimer.running == true && _delayedTimer.item == currNodeOver.data)
					{
						return;
					}
					else if (_delayedTimer.running == true)
					{
						_delayedTimer.cancelDelayedTimer();
					}
					
					_lastNodeOver = currNodeOver;
					
					
					_delayedTimer.startDelayedTimer(dispatchDelayOpen, null, null, 1000, 1, currNodeOver.data);
				}
			}
			else
			{
				if (_lastNodeOver != null)
				{
					_delayedTimer.cancelDelayedTimer();
					_lastNodeOver = null;
				}
			}
			
			
		}
		
		private var rejectCursorID:int;
		
		private function showRejectDropCursor(value:Boolean):void
		{
			if (value == true && cursorManager.currentCursorID != rejectCursorID)
			{
				var newCursorClass:Class;
				var styleSheet:CSSStyleDeclaration = StyleManager.getStyleDeclaration("DragManager");
				newCursorClass = styleSheet.getStyle("rejectCursor");
				
				rejectCursorID = CursorManager.setCursor(newCursorClass, 0);
			}
			else if (value == false)
			{
				CursorManager.removeCursor(rejectCursorID);
				rejectCursorID = -1;
			}
			
		}
		
		private function dispatchDelayOpen(event:TimerEvent):void
		{
			if (event.currentTarget.item.children.length != 0)
			{
				expandItem(event.currentTarget.item, true, true, true, event);
			}
			else
			{
				expandItem(event.currentTarget.item, true, false, true, event);
			}
		}
		
		private function handleItemClose(event:AdvancedDataGridEvent):void
		{
			if (DragManager.isDragging)
			{
				if (_lastNodeOver != null)
				{
					//closeNodes(_lastNodeOver.data);
				}
				else
				{
					closeNodes(null);
				}
			}
		}
		
		/*
		private function handleItemOpen(event:AdvancedDataGridEvent):void
		{
			if (DragManager.isDragging)
			{
				if (_lastNodeOver != null)
				{
					//closeNodes(_lastNodeOver.data);
				}
				else
				{
					closeNodes(null);
				}
			}
			
			logger.debug("open items: " + dataProvider.openNodes);
		}
		*/
		
		private function handleDragComplete(event:DragEvent):void
		{
			showRejectDropCursor(false);
			_delayedTimer.cancelDelayedTimer();
			_lastNodeOver = null;
			
			closeNodes(null);
			hideDropFeedback(event);
		}
		
		private function handleDragExit(event:DragEvent):void
		{
			showRejectDropCursor(false);
			logger.debug("handle drag exit");
			_delayedTimer.cancelDelayedTimer();
			_lastNodeOver = null;
			
			hideDropFeedback(event);
			closeNodes(null);
		}
		
		private function closeNodes(item:Object):void
		{
			logger.debug("closeNodes(" + (item == null ? "null" : item.label) + ")");
			if (item == null && _lastNodeOver == null)
			{
				_cleanupDelayedTimer.startDelayedTimer(restoreState, null, null, 1000, 1, null);
			}
			else
			{
				_cleanupDelayedTimer.startDelayedTimer(closeOpenNodes, null, null, 1000, 1, item);
			}
		}
		
		private function closeOpenNodes(event:TimerEvent):void
		{
			logger.debug("closeOpenNodes");
			var parentItems:Object = getParentStack(event.currentTarget.item);
			
			logger.debug("parent stack: " + parentItems);
			
			var nodes:Object = dataProvider.openNodes;
			var currentOpenFolders:Object = [];

			for each (var node:Object in nodes)
			{
				currentOpenFolders.push(node);
			}			
			
			logger.debug("opened folder hierarchy is:");
			for each (var thing:Object in openedFolderHierarchy)
			{
				logger.debug("\t" + thing);
			}
			
			for (var i:int = 0; i < currentOpenFolders.length; i++)
			//for each (var node:Object in currentOpenFolders) 
			{
				var nodeObj:Object = currentOpenFolders[i];
				
				if (openedFolderHierarchy.indexOf(nodeObj) == -1)
				{
					if (nodeObj != event.currentTarget.item &&
						parentItems.indexOf(nodeObj) == -1)
						{
							// would test if it's branch, but we not at the moment
							// if (isBranch(currentOpenFolders[i])) {
								
								if (nodeObj.children.length == 0)
								{
									expandItem(nodeObj, false, true, true);
								}
								else
								{
									expandItem(nodeObj, false, false, true);
								}
							// }
						}
				}
			}
		}
		
		private function draggingOverSelf(event:DragEvent):Boolean
		{
			var idx:int = calculateDropIndex(event);
			
			var currNodeOver:Object = indexToItemRenderer(idx);
			
			if (currNodeOver == null)
			{
				return false;
			}
			
			var draggingNode:Object = itemToItemRenderer(event.dragSource.dataForFormat("treeDataGridItems")[0]);
			
			if (currNodeOver != draggingNode)
			{
				return false;
			}
			
			return true;
		}
		
		private function internalCanDrop(event:DragEvent):Boolean
		{
			var idx:int = calculateDropIndex(event);
			var currNodeOver:Object = indexToItemRenderer(idx);
			var draggingNode:Object = itemToItemRenderer(event.dragSource.dataForFormat("treeDataGridItems")[0]);
			return canDropFunction(draggingNode.data, currNodeOver != null ? currNodeOver.data : null);
		}
		
		private function restoreState(event:TimerEvent):void
		{
			logger.debug("restoreState");
			if (_lastNodeOver != null)
			{
				return;
			}
			
			if (openedFolderHierarchy.length > 0)
			{
				// do some fix but may not be needed
			}
			
			var cofObj:Object = dataProvider.openNodes;
			var currentOpenFolders:Array = [];
			
			for each (var thing:Object in cofObj)
			{
				currentOpenFolders.push(thing);
			}
			
			for (var i:int = 0; i < currentOpenFolders.length; i++)
			{
				if (openedFolderHierarchy.indexOf(currentOpenFolders[i]) == -1)
				{
					if (!currentOpenFolders[i].children.length == 0)
					{
						expandItem(currentOpenFolders[i], false, true, true);
					}
					else
					{
						expandItem(currentOpenFolders[i], false, false, true);
					}
				}
			}
			
		}
				
		private function getParentStack(item:Object):Array
		{
			var stack:Array = [];
			
			if (item == null)
			{
				return stack;
			}
			
			var parent:* = getParentItem(item);
			logger.debug("le parent: " + parent);
			while (parent)
			{
				stack.push(parent);
				parent = getParentItem(parent);
				logger.debug("more parent: " + parent);
			}
			
			
			return stack;
		}
		
		
			/**
		 * Workarounds the FLEXDMV-2155 (Occurs if custom a <code>IHierarchicalCollectionViewCursor</code> instance is used)
		 */
		override protected function makeListData(data : Object, uid : String, rowNum : int,
			columnNum : int, column : AdvancedDataGridColumn) : BaseListData
		{
			var advancedDataGridListData : AdvancedDataGridListData = super.makeListData(data,
				uid, rowNum, columnNum, column)as AdvancedDataGridListData;

			if (iterator && iterator is IHierarchicalCollectionViewCursor && columnNum ==
				treeColumnIndex && !(data is AdvancedDataGridColumn))
			{
				initListData(data, advancedDataGridListData);
			}
			else
			{
				advancedDataGridListData.item = data;
			}

			return advancedDataGridListData;
		}
	}
}