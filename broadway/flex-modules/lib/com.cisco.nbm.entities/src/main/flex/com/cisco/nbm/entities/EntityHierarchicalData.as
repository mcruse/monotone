package com.cisco.nbm.entities
{
	import mx.collections.HierarchicalData;
	import mx.collections.ICollectionView;
	import mx.collections.Sort;
	import mx.collections.SortField;

	public class EntityHierarchicalData extends HierarchicalData
	{
		private var sort:Sort;
		
		public function EntityHierarchicalData(value:Object=null)
		{
			super(value);
			sort = new Sort();
			sort.compareFunction = Entity.sortCompareFunction;
			sort.fields = [new SortField("label",true,false,true)];
		}
		
		override public function getChildren(node:Object):Object {
			var children:ICollectionView = super.getChildren(node) as ICollectionView;
			if ( children == null || children.length == 0 )
				return null;
			children.sort = sort;
			children.refresh();
			return children;
		}
		
	}
}