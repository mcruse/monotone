package com.cisco.nbm.search
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.cisco_internal;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;

	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.IOErrorEvent;
	import flash.net.URLLoader;

	import mx.collections.ArrayCollection;

	use namespace cisco_internal;

	[Event(type="flash.events.Event", name="running")]
	[Event(type="flash.events.Event", name="added")]
	[Event(type="flash.events.Event", name="complete")]
	[Event(type="flash.events.ErrorEvent", name="error")]


	public class SearchJob extends EventDispatcher
	{
		[Bindable]
		public var results:ArrayCollection = new ArrayCollection();
		public var chunkResults:ArrayCollection = new ArrayCollection();

		private var _service:SearchService;

		private var _query:String;
		private var _context:String;
		private var _queryObj:Object;
		private var _mediatorNodeCall:MediatorNodeCall;
		private var _qid:String;
		private var _counter:int;

		public function SearchJob(searchQuery:String, searchContext:String,service:SearchService)
		{
			_query = searchQuery;
			_context = searchContext;
			_service = service;
			super(null);

		}

		public function get service():SearchService
		{
			return _service;
		}

		public function get query():String
		{
			return _query;
		}

		public function get context():String
		{
			return _context;
		}

		public function checkRunningStatus():void
		{
			trace("Check Query Manager Running Status");
			var node:MediatorNode = service.getNode();
			_mediatorNodeCall = node.execute("is_running",null);
			_mediatorNodeCall.addCallback(handleStatusResult, handleStatusError);
		}

		private function handleStatusResult(method:AsyncMethod, result:Object):void
		{
			if(result)
			dispatchEvent(new Event("RUNNING"));
			else
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, "Query Manager service is not running"));
		}

		private function handleStatusError(method:AsyncMethod, error:Object):void
		{
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, error as String));
		}

		public function execute():void
		{
			//Forcing entities search only for the CDET CSCtg32901
			_counter = 0;
			var node:MediatorNode = service.getNode();
			if(_context != null)
			_queryObj = { query : { 'name' : _query, 'context' : _context, ignoreCase : true, 'entities' : true}};
			else
			_queryObj = { query : { 'name' : _query, ignoreCase : true, 'entities' : true}};
			_mediatorNodeCall = node.execute("fetch", [_queryObj]);
			_mediatorNodeCall.addCallback(handleFetchComplete, handleFetchFail);
		}

		private function executeContinue():void
		{
			var node:MediatorNode = service.getNode();
			_queryObj = {'qid' : _qid};
			_mediatorNodeCall = node.execute("fetch",[_queryObj]);
			_mediatorNodeCall.addCallback(handleFetchComplete, handleFetchFail);
		}

		private function pushIntoResults(inputArray:Array):void
		{
			for each (var item:Object in inputArray)
			{
				results.source.push(item);
			}

		}

		private function handleFetchComplete(method:AsyncMethod, result:Object):void
		{
			trace("done: " + result);
			chunkResults.removeAll();
			if(_counter == 0)
			_qid = result.qid;
			if(result.complete == true)
			{
				if(_counter == 0)
				{
					results.source = result.items;
					dispatchEvent(new Event(Event.COMPLETE));
				}
				else
				{
				chunkResults.source = result.items;
				dispatchEvent(new Event(Event.COMPLETE));
				}
			cleanup();
			}
			else
			{
				_counter++;
				chunkResults.source = result.items;
				dispatchEvent(new Event(Event.CHANGE));
				executeContinue();
			}

		}

		private function handleFetchFail(method:AsyncMethod, error:Object):void
		{
			cleanup();
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, error as String));
		}

		private function handleComplete(event:Event):void
		{
			var loader:URLLoader = event.target as URLLoader;
			var src:String = loader.data;

			parseResults(src);
			dispatchEvent(new Event(Event.COMPLETE));

			cleanup();
		}

		private function parseResults(src:String):void
		{
			var xml:XML = new XML(src);
			for each (var result:XML in xml.result)
			{
				results.addItem( new String(result.@url) );
			}

		}

		private function handleError(event:IOErrorEvent):void
		{
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR));
		}

		private function cleanup():void
		{
			_service = null;
		}
	}
}