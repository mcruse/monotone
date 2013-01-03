package unittests.enterpriseSearchTestSuite.tests
{
	import com.cisco.nbm.search.SearchJob;
	import com.cisco.nbm.search.SearchService;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.XMLRPCService;

	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.TimerEvent;
	import flash.utils.Timer;

	import flexunit.framework.TestCase;

	import mx.collections.ArrayCollection;



	public class EnterpriseSearchTestCase1 extends TestCase
	{

		private var searchService:SearchService;
		private var service:XMLRPCService;
		private var serverAddress:String;
		private var rootURI:String;
		private var username:String;
		private var password:String;
		private var protocol:String;
		private static const SEARCH_SERVICE_URL:String = "/services/Query Manager";
		private var resultCheckTimer:Timer;

		private static const TIMEOUT_MS:int = 5500;
       	private static const RESULT_CHECK_TIMEOUT_MS:int = 6000;

		private var searchResult:ArrayCollection;
		private var fault:Boolean = Boolean(false);


		[BeforeClass]
     	override public function setUp():void
     	{
     	  serverAddress = "/72.163.203.116"
     	  rootURI = "/XMLRPCv2/RNA";
		  username = "mpxadmin";
		  password = "mpxAdmin12345";
		  protocol = "http://";
     	  service = new XMLRPCService(serverAddress, rootURI, username, password, protocol);
		  service.timeout = 60000;
          searchService = new SearchService(service.getNode(SEARCH_SERVICE_URL) as MediatorNode);
          searchResult = new ArrayCollection();
          fault = Boolean(false);
     	}

     	[Before(order = 1)]
     	public function async1setUp():void
     	{
     	  searchResult = new ArrayCollection();
     	}

		/**
		* Unit Test Case to check for exact search with string "RTU01"
		 * Server in 72.163.203.116
		 * Expected is "/aliases/Project1/store1/RTU01"
		 * Expected Search result length is 1
		*/
     	[Test(async1, order = 1, description="Searching for exact RTU01 with single/double quotes")]
    	public function testExactSearchWithDoubleQuotes():void
    	 {
    	 	//Expected
    	 	var passThroughData:Object = new Object();
	       	passThroughData.searchResultString = "/aliases/Project1/store1/RTU01";
	       	passThroughData.searchResultLength = 1;

    	 	var searchInput:String = "RTU01";
          	var searchContext:String = null;
			var searchJob:SearchJob = searchService.search(searchInput,searchContext);
			searchJob.addEventListener(Event.COMPLETE, addAsync(handlePassSearchComplete, RESULT_CHECK_TIMEOUT_MS,passThroughData));
			searchJob.addEventListener(ErrorEvent.ERROR, handleSearchFault);
			searchJob.execute();
     	}

     	[After(order = 1)]
     	public function async1tearDown():void
     	{
          searchResult = null;
     	}

		[Before(order = 2)]
     	public function async2setUp():void
     	{
     	  searchResult = new ArrayCollection();
     	}

     	/**
		* Unit Test Case to check for search with string ?TU?1
		 * Server in 72.163.203.116
		 * Expected is "/aliases/Project1/store1/RTU01"
		 * Expected Search result length is 1
		*/
     	[Test(async2, order = 2, description="Searching for RTU01 with ? in between")]
    	public function testExactSearchWithQuestionMark():void
    	 {
    	 	//Expected
    	 	var passThroughData:Object = new Object();
	       	passThroughData.searchResultString = "/aliases/Project1/store1/RTU01";
	       	passThroughData.searchResultLength = 1;


    	 	var searchInput:String = "?TU?1";
          	var searchContext:String = null;
			var searchJob:SearchJob = searchService.search(searchInput,searchContext);

			searchJob.addEventListener(Event.COMPLETE, addAsync(handlePassSearchComplete, RESULT_CHECK_TIMEOUT_MS,passThroughData));
			searchJob.addEventListener(ErrorEvent.ERROR, handleSearchFault);
			searchJob.execute();
     	}

     	[After(order = 2)]
     	public function async2tearDown():void
     	{
          searchResult = null;
     	}

     	[Before(order = 3)]
     	public function async3setUp():void
     	{
     	  searchResult = new ArrayCollection();
     	}

     	/**
		* Unit Test Case to check for search with string P*
		 * Server in 72.163.203.116
		 * Expected is "/aliases/Project1"
		 * Expected Search result length is 1
		*/
     	[Test(async3, order = 3, description="Searching for P*")]
    	public function testSearchWithOneCharacterAndStar():void
    	 {
    	 	//Expected
    	 	var passThroughData:Object = new Object();
	       	passThroughData.searchResultString = "/aliases/Project1";
	       	passThroughData.searchResultLength = 1;


    	 	var searchInput:String = "P*";
          	var searchContext:String = null;
			var searchJob:SearchJob = searchService.search(searchInput,searchContext);

			searchJob.addEventListener(Event.COMPLETE, addAsync(handlePassSearchComplete, RESULT_CHECK_TIMEOUT_MS,passThroughData));
			searchJob.addEventListener(ErrorEvent.ERROR, handleSearchFault);
			searchJob.execute();
     	}

     	[After(order = 3)]
     	public function async3tearDown():void
     	{
          searchResult = null;
     	}


     	private function handlePassSearchComplete(event:Event,passThroughData:Object):void {
     	trace("Inside handleExactSearchComplete");
       	var searchJob:SearchJob = event.target as SearchJob;
       	searchResult = searchJob.results;
        assertEquals("Returned Search Result Item is " + passThroughData.searchResultString, passThroughData.searchResultString, searchResult.getItemAt(0))
        assertEquals("Size of Return results is " + passThroughData.searchResultLength, passThroughData.searchResultLength , searchResult.length);

       }


		[Before(order = 4)]
     	public function async4setUp():void
     	{
     	  searchResult = new ArrayCollection();
     	}

     	/**
		* Unit Test Case to check for search with string R*
		 * Server in 72.163.203.116
		 * Expected is "/aliases/Project1"
		 * Expected Search result length is 1
		*/
     	[Test(async4, order = 4, description="Searching for *R*")]
    	public function testSearch():void
    	 {
    	 	//Expected
    	 	var passThroughData:Object = new Object();
	       	passThroughData.searchResultFirstItem = "/aliases/Project1";
	       	passThroughData.searchResultSecondItem = "/aliases/Project1/store1/RTU01";
	       	passThroughData.searchResultThirdItem = "/aliases/Project1/store1";
	       	passThroughData.searchResultLength = 3;

    	 	var searchInput:String = "*R*";
          	var searchContext:String = null;
			var searchJob:SearchJob = searchService.search(searchInput,searchContext);
			searchJob.addEventListener(Event.COMPLETE, handlePassSearchComplete,passThroughData);
			searchJob.addEventListener(ErrorEvent.ERROR, handleSearchFault);
			resultCheckTimer = new Timer(1);
	        resultCheckTimer.delay = TIMEOUT_MS;
	        resultCheckTimer.addEventListener(TimerEvent.TIMER, addAsync(searchCheck, RESULT_CHECK_TIMEOUT_MS));
	        resultCheckTimer.start();

			searchJob.execute();
     	}

     	private function handleSearchComplete(event:Event,passThroughData:Object):void {
       	var searchJob:SearchJob = event.target as SearchJob;
       		searchResult = searchJob.results;
           trace("Inside HandleSearchComplete");
                assertEquals("First Item is /aliases/Project1", passThroughData.searchResultFirstItem, searchResult.getItemAt(0));
                assertEquals("First Item is /aliases/Project1", passThroughData.searchResultSecondItem, searchResult.getItemAt(1));
                assertEquals("First Item is /aliases/Project1", passThroughData.searchResultThirdItem, searchResult.getItemAt(2));
                assertEquals("Size of Return results is 3", passThroughData.searchResultLength, searchResult.length);

       }

       private function handleSearchFault (event:ErrorEvent):void {
       	   fault = Boolean(true);
           fail(event.text);
       }


       private function searchCheck(event:Event):void {
           resultCheckTimer.reset();
           if (fault == Boolean(true)) {
               fail("Search failed");
           }
           else
           {
           	trace("Search progressing");
           	if(searchResult.length > 0)
           {
           trace("Items Found: " + searchResult.getItemAt(0));
           assertNotNull(searchResult.getItemAt(0));
           assertNotUndefined(searchResult.getItemAt(0));
           }
           else
            trace("Items not yet added");

           }

       }

       [After(order = 4)]
     	public function async4tearDown():void
     	{
          searchResult = null;
     	}

        [Before(order = 5)]
     	public function async5setUp():void
     	{
     	  searchResult = new ArrayCollection();
     	}

     	/**
		* Unit Test Case to see if unit test fails or not. Check for search with string K*
		 * Server in 72.163.203.116
		 * Expected is nothing
		 * Expected Search result length is 0
		*/
     	[Test(async5, order = 5, description="Searching for K*")]
    	public function testFailSearchWithOneCharacterAndStar():void
    	 {
    	 	//Expected
    	 	var passThroughData:Object = new Object();
	       	passThroughData.searchResultLength = 1;


    	 	var searchInput:String = "K*";
          	var searchContext:String = null;
			var searchJob:SearchJob = searchService.search(searchInput,searchContext);

			searchJob.addEventListener(Event.COMPLETE, addAsync(handleFailSearchComplete, RESULT_CHECK_TIMEOUT_MS,passThroughData));
			searchJob.addEventListener(ErrorEvent.ERROR, handleSearchFault);
			searchJob.execute();
     	}

     	private function handleFailSearchComplete(event:Event,passThroughData:Object):void {
     	trace("Inside handleExactSearchComplete");
       	var searchJob:SearchJob = event.target as SearchJob;
       	searchResult = searchJob.results;
        assertEquals("Size of Return results is " + passThroughData.searchResultLength, passThroughData.searchResultLength,searchResult.length);

       }

     	[After(order = 5)]
     	public function async5tearDown():void
     	{
          searchResult = null;
     	}




       [AfterClass]
     	override public function tearDown():void
     	{
          serverAddress = null;
     	  rootURI = null;
		  username = null;
		  password = null;
		  protocol = null;
     	  service = null;
		  searchService = null;
		  searchResult = null;
     	}


	}

}