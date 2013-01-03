package com.cisco.ui.components
{
	import flash.utils.Timer;
	
	import mx.controls.AdvancedDataGrid;
	import mx.events.AdvancedDataGridEvent;

	public class CiscoAdvancedDataGrid extends AdvancedDataGrid
	{
		private var doubleClickTimer:Timer = new Timer(400, 1);
		
		public function CiscoAdvancedDataGrid()
		{
			super();
			
			addEventListener(AdvancedDataGridEvent.ITEM_EDIT_BEGIN,
				handleItemEditBegin);
		}
		
		private function handleItemEditBegin(event:AdvancedDataGridEvent):void
		{
			selectedIndex = event.rowIndex;
			
			if (!doubleClickTimer.running)
			{
				doubleClickTimer.start();
				event.stopImmediatePropagation();
			}
		}
		
		/**
		 * Returns the root nodes of the selectedItems.
		 * 
		 * @return An array that contains only the root nodes of the <code>selectedItems</code> property 
		 */
		public function get selectedRootNodes():Array
		{
			var newSelection:Array = [];
			var sel:Array = selectedItems;
			
			for each (var item:Object in sel)
			{
				var itemParent:Object = getParentItem(item);
				
				// If the items parent is not in the selection then it's a root
				// And if it's not in the current selection of roots then 
				// add it.
				if (sel.indexOf(itemParent) == -1 
					&& newSelection.indexOf(item)==-1)
				{
					newSelection.push(item);
				}
			}
			
			return newSelection;
		}		
	}
}