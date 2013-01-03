package com.cisco.ui.components.view.filterDataGrid.vo
{
	import com.cisco.ui.components.vo.IComparator;
	
	[Bindable]
	public class FilterItemVO implements IComparator
	{
		private var _name:String;
		
		public static var ALL :FilterItemVO = new FilterItemVO("ALL");
		
		public function FilterItemVO(name:String) {
			this._name = name;
		}
		
		public function get name():String {
			return _name;
		}
		
		public function set name(value:String):void {
			this._name = name;
		}
		
		public function uniqueIdentifier():String
		{
			return _name;
		}
		
	}
}