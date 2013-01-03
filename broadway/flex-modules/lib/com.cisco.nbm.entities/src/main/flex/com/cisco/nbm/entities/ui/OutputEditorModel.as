package com.cisco.nbm.entities.ui
{
	import com.cisco.nbm.entities.EntityProperty;
	
	import mx.collections.ArrayCollection;

	public class OutputEditorModel extends ArrayCollection
	{
		public static const COUNT_LEVELS:int = 16;
		
		public var property:EntityProperty;
		
		public function OutputEditorModel()
		{
			super();
			
			createEntries();
		}
		
		/**
		 * This receiveds a result straight from an XMLRPC
		 * call.
		 */
		public function updateValues(result:Object):void
		{
			var activeNumber:int = result['active'];
			
			for (var i:int = 0; i < COUNT_LEVELS; i++)
			{
				var levelValue:Object = result[i+1];
				
				var entry:OutputEditorModelEntry = getItemAt(i) as OutputEditorModelEntry;
				entry.value = levelValue;
				
				if (activeNumber == (i+1))
				{
					entry.active = true;
				}
				else
				{
					entry.active = false;
				}
			}
		}
		
		private function createEntries():void
		{
			for (var i:int = 0; i < COUNT_LEVELS; i++)
			{
				addItem(new OutputEditorModelEntry(i+1));
			} 
		}
	}
}