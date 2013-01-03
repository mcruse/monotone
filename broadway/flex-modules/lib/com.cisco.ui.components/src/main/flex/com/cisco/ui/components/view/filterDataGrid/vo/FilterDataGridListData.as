package com.cisco.ui.components.view.filterDataGrid.vo
{
	import com.cisco.ui.components.view.filterDataGrid.FilterDataGridColumn;
	
	import mx.controls.dataGridClasses.DataGridColumn;
	import mx.controls.dataGridClasses.DataGridListData;
	import mx.core.IUIComponent;

	public class FilterDataGridListData extends DataGridListData
	{
		public var filter:FilterVO;
		public var column:FilterDataGridColumn;

		public function FilterDataGridListData(filter:FilterVO, column:DataGridColumn, text:String, dataField:String, columnIndex:int, uid:String, owner:IUIComponent, rowIndex:int=0.0)
		{
			super(text, dataField, columnIndex, uid, owner, rowIndex);
			this.filter=filter;
			this.column=column as FilterDataGridColumn;
		}

	}
}
