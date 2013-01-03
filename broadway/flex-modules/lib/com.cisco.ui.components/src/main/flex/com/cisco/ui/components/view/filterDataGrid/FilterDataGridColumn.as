package com.cisco.ui.components.view.filterDataGrid
{
	import com.cisco.ui.components.view.filterDataGrid.renderer.FilterHeaderRenderer;
	
	import mx.controls.dataGridClasses.DataGridColumn;
	import mx.core.ClassFactory;
	import mx.core.IFactory;
	import mx.core.mx_internal;
	use namespace mx_internal;


	public class FilterDataGridColumn extends DataGridColumn
	{
		private var _searchMode:Boolean=false;
		private var _searchLabelFunction:Function;

		public function FilterDataGridColumn(columnName:String=null)
		{
			super(columnName);
		}


		public function get searchMode():Boolean
		{
			return _searchMode;
		}

		public function set searchMode(value:Boolean):void
		{
			this._searchMode=value;
		}
		
		public function get searchLabelFunction():Function {
			if ( _searchLabelFunction == null )
				return labelFunction;
			return _searchLabelFunction;
		}
		
		public function set searchLabelFunction(value:Function):void {
			this._searchLabelFunction = value;
		}
		
		public function itemToSearchLabel(item:Object):String {
			if ( _searchLabelFunction != null ) {
				return _searchLabelFunction(item,this);
			}
			return itemToLabel(item);
		}


		override public function get headerRenderer():IFactory
		{
			return new ClassFactory(FilterHeaderRenderer);
		}

		public function get myOwner():FilterDataGrid
		{
			return (owner as FilterDataGrid);
		}
	}
}
