package com.cisco.cbsbu.nbm{

	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.IEventDispatcher;
    import mx.controls.Alert;
	import mx.collections.ICollectionView;
	import mx.controls.treeClasses.DefaultDataDescriptor;
    import mx.collections.HierarchicalData;

	public class LazyDataDescriptor extends HierarchicalData {
    
		public function LazyDataDescriptor() {
			super();
		}

		override public function hasChildren(node:Object):Boolean {
			if (node is NodeVO) {
                return (node as NodeVO).hasChildren();
			} else {
				return super.hasChildren(node);
			}
		}
	}
}