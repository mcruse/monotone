package com.cisco.nbm.browserbridge
{
	import flash.events.Event;

	public class TopicNotificationEvent extends Event
	{
		private var _topic:String;
		
		public static const TOPIC_NOTIFICATION:String = "topicNotification";
		
		public function TopicNotificationEvent(bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(TOPIC_NOTIFICATION, bubbles, cancelable);
		}
		
		public function get topic():String
		{
			return _topic;
		}
		
	}
}