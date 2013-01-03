package com.cisco.nbm.search
{
	import flash.events.IEventDispatcher;

	public interface ISearchService
	{
		function search(searchQuery:String, searchContext:String):SearchJob;
	}
}