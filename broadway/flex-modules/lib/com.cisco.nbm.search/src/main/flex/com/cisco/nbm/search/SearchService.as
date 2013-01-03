package com.cisco.nbm.search
{
	import com.cisco.cisco_internal;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;


	public class SearchService implements ISearchService
	{
		private var _node:MediatorNode;


		public function SearchService(node:MediatorNode)
		{
			_node = node;
		}

		public function checkStatus():SearchJob
		{
			return new SearchJob(null,null,this);
		}

		public function search(query:String, searchContext:String):SearchJob
		{
			return new SearchJob(query,searchContext,this);
		}

		cisco_internal function getNode():MediatorNode
		{
			return _node;
		}

	}
}