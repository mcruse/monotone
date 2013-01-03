package com.cisco.ui.components.view.filterDataGrid
{
	import com.cisco.ui.components.event.UIDataEvent;
	import com.cisco.ui.components.view.ExportDataGrid;
	import com.cisco.ui.components.view.filterDataGrid.vo.FilterDataGridListData;
	import com.cisco.ui.components.view.filterDataGrid.vo.FilterItemVO;
	import com.cisco.ui.components.view.filterDataGrid.vo.FilterVO;
	import com.cisco.ui.components.vo.Dictionary;
	
	import flash.display.Sprite;
	import flash.events.Event;
	
	import mx.controls.dataGridClasses.DataGridColumn;
	import mx.controls.listClasses.BaseListData;
	import mx.core.EventPriority;
	import mx.core.mx_internal;
	import mx.events.DataGridEvent;
	use namespace mx_internal;
	
	[Event(name="filterChanged", type="com.cisco.nbmm.components.events.UIDataEvent")]
	[Event(name="resetFilters", type="flash.events.Event")]
	
	public class FilterDataGrid extends ExportDataGrid
	{
		public static const EVENT_FILTER_CHANGED : String = "filterChanged";
		public static const EVENT_RESET_FILTERS : String = "resetFilters";
		
		private var filterItems:Dictionary = new Dictionary();
		protected var sortIndex:int = -1;
		private var selectedFilter:FilterVO;
		public var enableResetFilter:Boolean=true;
		
		public function FilterDataGrid()
		{
			super();
	        addEventListener(DataGridEvent.HEADER_RELEASE,headerReleaseHandler);
	        addEventListener(EVENT_FILTER_CHANGED,filterChangeHandler,false,EventPriority.DEFAULT_HANDLER);
	        this.draggableColumns = false;
		}
		
		
		
		private function headerReleaseHandler(event:DataGridEvent):void {
			sortIndex = event.columnIndex;
		}
		
		public function filterColumn(column:DataGridColumn,itemName:String):void {
			if ( this.columns.indexOf(column) == -1 )	return;
			
			selectedFilter = getFilter(column);
			selectedFilter.selectedItem = new FilterItemVO(itemName);
			selectedFilter.manualFilterRefresh = true;
			invalidateDisplayList();
		}
		
		private function getFilter(column:DataGridColumn):FilterVO {
			var filterVO:FilterVO = filterItems.find(column.headerText) as FilterVO;
			if (filterVO == null ) {
				filterVO = new FilterVO(column as FilterDataGridColumn,this);
				filterItems.add(filterVO);
			}
			return filterVO;
		}
		
		override protected function makeListData(data:Object, uid:String, rowNum:int, columnNum:int, column:DataGridColumn):BaseListData {
			var listData:BaseListData;
			
			var filterVO:FilterVO;
			if ( column is FilterDataGridColumn ) {
				filterVO = getFilter(column);
			}
			
			if ( data is DataGridColumn )
			{
				listData = new FilterDataGridListData(filterVO,column,
					(column.headerText != null) ? column.headerText : column.dataField,
					column.dataField, 
					columnNum, 
					uid, 
					this, 
					rowNum);
			}
			else
			{ 
				listData = super.makeListData(data,uid,rowNum,columnNum,column);
				if ( column is FilterDataGridColumn && !(column as FilterDataGridColumn).searchMode ) {
					filterVO.addFilterItem(listData.label);
				}
			}
			return listData;
		}
		
		public function filterFunction(item:Object):Boolean {
			for each ( var filter:FilterVO in filterItems ) {
				var flag:Boolean = filter.canShowItem(item);
				if (!flag)
					return false;
			}
			return true;
		}
		
		public function resetFilters():void {
			dispatchEvent(new UIDataEvent(FilterDataGrid.EVENT_RESET_FILTERS,null));
		}
		
		public function get isFiltered():Boolean {
			for each ( var filter:FilterVO in filterItems ) {
				var flag:Boolean = filter.isFiltered;
				if (flag)
					return true;
			}
			return false;
		}
		
		override public function set dataProvider(value:Object):void
		{
			if ( enableResetFilter && !isFiltered ) {
				resetFilters();
			}
			
			super.dataProvider = value;
			filterChangeHandler();
		}
		
		public function filterChangeHandler(event:UIDataEvent=null):void {
			
			if ( event != null && event.isDefaultPrevented() )	return;
			
			collection.filterFunction = filterFunction;
			collection.refresh();
			invalidateProperties();
			invalidateDisplayList();
		}
		
		override protected function placeSortArrow():void {
			super.placeSortArrow();
			
			if (sortIndex == -1) return;
			
	        var n:int;
	        var i:int;
	        if (listItems && listItems.length && listItems[0])
	        {
	            n = listItems[0].length;
	            for (i = 0; i < n; i++)
	            {
	                if (visibleColumns[i].colNum == sortIndex)
	                {
	                    listItems[0][i].setActualSize(visibleColumns[i].width, listItems[0][i].height);
	                    break;
					}
				}   
			}
			var sortArrowHitArea:Sprite = Sprite(listContent.getChildByName("sortArrowHitArea"));
			if (sortArrowHitArea)
				sortArrowHitArea.graphics.clear();
			if (sortArrow) {
				var c:DataGridColumn = columns[sortIndex];
	        	var desc:Boolean = c.sortDescending;
				sortArrow.y = 5 + (desc ? 0 : sortArrow.measuredHeight);
			}
		}
	}
}