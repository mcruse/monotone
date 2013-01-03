package com.cisco.ui.components
{
	import mx.collections.ICollectionView;
	import mx.controls.treeClasses.DefaultDataDescriptor;

	public class TreeDataDescriptor extends DefaultDataDescriptor
	{
		public function TreeDataDescriptor()
		{
			super();
		}
		
		override public function isBranch(node:Object, model:Object=null):Boolean {
			var children:ICollectionView = super.getChildren(node,model);
			if ( children != null && children.length > 0 )
				return true;
			return false;
		}
		
	}
}