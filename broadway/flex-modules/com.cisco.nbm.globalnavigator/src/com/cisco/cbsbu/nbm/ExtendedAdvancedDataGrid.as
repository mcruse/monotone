package com.cisco.cbsbu.nbm
{
	import mx.collections.CursorBookmark;
	import mx.collections.IHierarchicalCollectionView;
	import mx.controls.AdvancedDataGrid;
	import mx.core.mx_internal;
	import mx.events.CollectionEvent;
	import mx.events.CollectionEventKind;

	use namespace mx_internal;

	public class ExtendedAdvancedDataGrid extends AdvancedDataGrid
	{
		public function ExtendedAdvancedDataGrid()
		{
			super();
			hierarchicalCollectionView = new ExtendedHierarchicalCollectionView();
		}
		
		public override function expandAll():void
		{
			fastExpandAll();
			postExpandAllCollectionEvents();
		}
		
		public override function collapseAll():void
		{
			fastCollapseAll();
			postExpandAllCollectionEvents();
		}
		
		
		public function fastCollapseAll():void
	    {
	        if (dataProvider is IHierarchicalCollectionView && iterator)
	        {
	            // clear the selected items
	            clearSelected();
	            
	            //dispatch events
	            for each (var item:* in IHierarchicalCollectionView(collection).openNodes)
	            {
	                ExtendedHierarchicalCollectionView(collection).fastCloseNode(item);
	            }
	            
	            var oldValue:int = verticalScrollPosition;
	            verticalScrollPosition = 0;
	        }
	    }
		
		
		public function fastExpandAll():void
    	{
        if (dataProvider is IHierarchicalCollectionView && iterator)
	        {
	            // move to the first item
	            iterator.seek(CursorBookmark.FIRST);
	            while(!iterator.afterLast)
	            {
	                fastExpandChildrenOf(iterator.current, true);
	                iterator.moveNext();
	            }
	            // seek to the correct position
	            iterator.seek(CursorBookmark.FIRST, verticalScrollPosition);
	        }
    	}
		
		public function fastExpandChildrenOf(item:Object, open:Boolean):void
	    {
	        //if the iterator is null, that indicates we have not been 
	        //validated yet, so we will not continue. 
	        if (iterator == null)
	            return;
	
	        // if it is not a branch item there's nothing to do
	        if (isBranch(item))
	        {
	        	
	        	//expandItem(item, true, false, false, null);
	        	fastExpandItem(item);
				if (!open) {
					return;
				}
			
	            var i:int = 0;
	            var childItems:Object
	                if (item != null &&
	                    _rootModel.canHaveChildren(item) &&
	                    _rootModel.hasChildren(item))
	                {
	                    childItems = getChildren(item, iterator.view);
	                }
	            if (childItems && open)
	            {
	                var childItem:Object = childItems[i];
	                while (childItem)
	                {
	                    if (isBranch(childItem))
	                        fastExpandChildrenOf(childItem, open);
	 
	                    try
	                    {
	                        childItem = childItems[i++];
	                    }
	                    catch (e:RangeError)
	                    {
	                        childItem = null;
	                    }
	                }
	            }
	        }
	    }
		
		public function fastExpandItem(item:Object):void
    	{
            ExtendedHierarchicalCollectionView(collection).fastOpenNode(item);
    	}
		
		private function postExpandAllCollectionEvents():void
	    {
	    	var ce:CollectionEvent;
	        ce = new CollectionEvent(CollectionEvent.COLLECTION_CHANGE);
	        ce.kind = CollectionEventKind.RESET;
	        ExtendedHierarchicalCollectionView(collection).collectionChangeHandler(ce); 
	    }
		
		
	}
}