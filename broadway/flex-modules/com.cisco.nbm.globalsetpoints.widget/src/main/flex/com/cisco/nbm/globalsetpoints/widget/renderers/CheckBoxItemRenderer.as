package com.cisco.nbm.globalsetpoints.widget.renderers
{
	import flash.events.Event;
	import flash.events.MouseEvent;
	import mx.controls.Alert;
	import mx.controls.CheckBox;
	import mx.controls.DataGrid;
	public class CheckBoxItemRenderer extends CheckBox
	{
		[Bindable]
		public var isSelected:Boolean;
		
		public function CheckBoxItemRenderer()
		{
			super();
		}
		override public function validateProperties():void
		{
			super.validateProperties();
			if (listData)
			{
				
				var dg:DataGrid = DataGrid(listData.owner);
	
				var column:CheckBoxHeaderColumn =	dg.columns[listData.columnIndex];
				column.addEventListener("click",columnHeaderClickHandler);
				selected = data[column.dataField];
			}
		}
		private function columnHeaderClickHandler(event:MouseEvent):void
		{
			selected = event.target.selected;
		}
		
	}
}