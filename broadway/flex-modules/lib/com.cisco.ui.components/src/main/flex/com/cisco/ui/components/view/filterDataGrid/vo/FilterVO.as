package com.cisco.ui.components.view.filterDataGrid.vo
{
	import com.cisco.ui.components.util.Util;
	import com.cisco.ui.components.view.filterDataGrid.FilterDataGrid;
	import com.cisco.ui.components.view.filterDataGrid.FilterDataGridColumn;
	import com.cisco.ui.components.vo.AdvancedDictionary;
	import com.cisco.ui.components.vo.Dictionary;
	import com.cisco.ui.components.vo.IComparator;
	
	import flash.events.Event;
	import flash.events.EventDispatcher;
	
	import mx.controls.dataGridClasses.DataGridColumn;
	import mx.utils.StringUtil;

	[Bindable]
	public class FilterVO extends EventDispatcher implements IComparator
	{
		private var _headerText:String;
		private var _filterItems:Dictionary = new AdvancedDictionary();
		private var _selectedItem:FilterItemVO = FilterItemVO.ALL;
		public var column:DataGridColumn;
		public var searchMode:Boolean=false;
		public var searchString:String="";
		public var manualFilterRefresh:Boolean;
		
		


		public function FilterVO(column:FilterDataGridColumn, grid:FilterDataGrid)
		{
			this.column=column;
			searchMode=column.searchMode;
			_headerText=column.headerText;
			_filterItems.add(FilterItemVO.ALL);
		}

		public function get headerText():String
		{
			return _headerText;
		}

		public function get filterItems():Dictionary
		{
			return _filterItems;
		}

		public function set filterItems(value:Dictionary):void
		{
			this._filterItems=value;
		}

		public function get selectedItem():FilterItemVO
		{
			return _selectedItem;
		}

		public function set selectedItem(value:FilterItemVO):void
		{
			this._selectedItem=value;
		}

		public function addFilterItem(label:String):void
		{

			if (label != null && StringUtil.trim(label) != "" && !filterItems.existsWithUniqueID(label) )
			{
				filterItems.add(new FilterItemVO(label));
			}

		}
		
		public function getFilterItem(label:String):FilterItemVO {
			return filterItems.find(label) as FilterItemVO;
		}

		public function canShowItem(item:Object):Boolean
		{
			var label:String;

			if (searchMode)
			{
				if (searchString == null || searchString == "")
					return true;
				label = (column as FilterDataGridColumn).itemToSearchLabel(item);
				return (Util.search(label, searchString) == -1) ? false : true;
			}
			if (selectedItem == FilterItemVO.ALL)
				return true;
			label = column.itemToLabel(item);

			return selectedItem.name == label;
		}
		
		public function get isFiltered():Boolean {
			if (searchMode) {
				if (searchString == null || searchString == "")
					return false;
			} else {
				if (selectedItem == FilterItemVO.ALL)
				return false;
			}
			return true;
		}
		
		public function uniqueIdentifier():String
		{
			return headerText;
		}
		
		public function resetAll(event:Event=null):void
		{
			selectedItem = FilterItemVO.ALL;
			filterItems=new AdvancedDictionary();
			filterItems.add(FilterItemVO.ALL);
		}

		public function reset(event:Event=null):void
		{
			if (selectedItem != FilterItemVO.ALL)
				return;
			filterItems=new AdvancedDictionary();
			filterItems.add(FilterItemVO.ALL);
		}

	}
}
