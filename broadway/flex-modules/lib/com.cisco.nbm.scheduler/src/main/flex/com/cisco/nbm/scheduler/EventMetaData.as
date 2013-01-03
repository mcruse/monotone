package com.cisco.nbm.scheduler
{
	import mx.utils.UIDUtil;
	
	public class EventMetaData
	{
		/*
		##
    # Retrieve the meta data associated with an event.
    #
    # @return {'name':'eventname', 'color':'color', 'value':'default_value'}

    def get_event_meta(self):
        return self._event_meta
		*/
		
		[Bindable]
		public var name:String;
		
		[Bindable]
		public var color:int;
		
		[Bindable]
		public var value:String;
		
		/**
		 * @private
		 * 
		 * This is used internally by the UI to match property
		 * mappings to event meta descriptions to prevent bugs
		 * like: CSCth12855 from happening.
		 * 
		 * It is never transfered to the backend and should
		 * not be relied upon after a schedule is initialized
		 * again from the remote.
		 */
		private var _uuid:String = UIDUtil.createUID();
		
		public function EventMetaData()
		{
			
		}
		
		public function get uuid():String {
			return _uuid;
		}
			
		public function fromDictionary(object:Object):void
		{
			name = object['name'];
			color = object['color'];
			value = object['value'];
		}
		
		public function toDictionary():Object
		{
			return { 'name' : name, 'color' : color, 'value' : value };
		}

		public function toString():String
		{
			var str:String = "EventMeta(uuid='"+_uuid+"', name='"+name+"', color="+color+", value='"+value+"')";
			return str;
		}
	}
}