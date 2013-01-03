package com.cisco.collections
{
	import mx.collections.HierarchicalCollectionView;
	import mx.collections.IHierarchicalData;
	import mx.collections.IViewCursor;

	import mx.core.mx_internal;

	use namespace mx_internal;


	public class HierarchicalCollectionView extends mx.collections.HierarchicalCollectionView
	{
		public function HierarchicalCollectionView(hierarchicalData:IHierarchicalData=null, argOpenNodes:Object=null)
		{
			super(hierarchicalData, argOpenNodes);
		}
		
		override public function createCursor():IViewCursor {
			return new HierarchicalCollectionViewCursor(this, treeData, this.source);
		}
		
	}
}