package com.cisco.ui.components.vo
{
	import mx.collections.ICollectionView;
	
	public interface IAdvancedSearchTarget
	{
		function get searchfields():ICollectionView;
		function searchLabel(item:Object,dataField:String):*;
		function get searchFunction():Function;
	}
}