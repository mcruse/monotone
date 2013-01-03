package unittests.enterpriseSearchTestSuite.tests
{
	import com.cisco.nbm.browserbridge.ui.connection.AuthenticationDialog;
	import com.cisco.nbm.navigator.EnterpriseNavigation;

	import flash.events.MouseEvent;

	import mx.collections.ArrayCollection;
	import mx.core.Application;
	import mx.events.CollectionEvent;
	import mx.events.FlexEvent;

	import net.digitalprimates.fluint.sequence.SequenceEventDispatcher;
	import net.digitalprimates.fluint.sequence.SequenceRunner;
	import net.digitalprimates.fluint.sequence.SequenceSetter;
	import net.digitalprimates.fluint.sequence.SequenceWaiter;
	import net.digitalprimates.fluint.tests.TestCase;
	import net.digitalprimates.fluint.ui.TestEnvironment;

	import org.fluint.uiImpersonation.UIImpersonator;



	public class EnterpriseSearchTestCase2 extends TestCase
	{
		private var searchAuthPanel:AuthenticationDialog;
		private var searchPanel:EnterpriseNavigation;
		/* private var searchService:SearchService;
		private var service:XMLRPCService;
		private var serverAddress:String;
		private var rootURI:String;
		private var username:String;
		private var password:String;
		private var protocol:String;
		private static const SEARCH_SERVICE_URL:String = "/services/Query Manager";
		private var resultCheckTimer:Timer;

		private static const TIMEOUT_MS:int = 3000;
       	private static const RESULT_CHECK_TIMEOUT_MS:int = 3500; */

		[Before(async, order=1)]
		override protected function setUp():void
		{
		searchPanel = new EnterpriseNavigation();
		searchPanel.addEventListener( FlexEvent.CREATION_COMPLETE, asyncHandler( pendUntilComplete, 500 ), false, 0, true );
        UIImpersonator.addChild(searchPanel);

		}

		/* [BeforeClass]
     	public function setUp():void
     	{
     	  serverAddress = "10.64.78.171"
     	  rootURI = "/XMLRPCv2/RNA";
		  username = "mpxadmin";
		  password = "mpxadmin";
		  protocol = "http://";
     	  service = new XMLRPCService(serverAddress, rootURI, username, password, protocol);
		  service.timeout = 60000;
          searchService = new SearchService(service.getNode(SEARCH_SERVICE_URL) as MediatorNode);
     	}

     	[AfterClass]
     	public function tearDown():void
     	{
          serverAddress = null;
     	  rootURI = null;
		  username = null;
		  password = null;
		  protocol = null;
     	  service = null;
		  searchService = null;
     	} */


     	/* [Test(async, description="enterpriseSearchTestCase1 Example")]
    	public function testSearch():void
    	 {
    	 	var searchInput:String = "*R*";
          	var searchQuery:String = createQuery(searchInput);
          	var searchContext:String = null;
			var searchJob:SearchJob = searchService.search(searchQuery,searchContext);
			//searchJob.addEventListener(Event.CHANGE, handleSearchAdded);
			searchJob.execute.addEventListener("result", handleSearchComplete);
			searchJob.execute.addEventListener("fault", handleSearchFault);
			resultCheckTimer = new Timer(1);
	        resultCheckTimer.delay = TIMEOUT_MS;
	        resultCheckTimer.addEventListener(TimerEvent.TIMER, addAsync(searchCheck, RESULT_CHECK_TIMEOUT_MS));
	        resultCheckTimer.start();

			searchJob.execute();
     	}

       private function handleSearchComplete(event:ResultEvent):void {
           user = event.result as User;
           trace("user: " + user);
       }

       private function faultHandler (event:FaultEvent):void {
           fault = Boolean(true);
           fail(event.fault.faultString);
       }


       private function searchCheck(event:Event):void {
           resultCheckTimer.reset();
           trace("loginCheck: " + user);
           if (fault == Boolean(true)) {
               fail("login failed");
           }
           assertNotNull(user);
           assertNotUndefined(user);
       }
       */

	   [Test(order=1)]
       public function testSearch():void
       {
       	var passThroughData:Object = new Object();
       	//Search Authentication Dialog
       	passThroughData.serverAddress = "72.163.203.116"
     	passThroughData.username = "mpxadmin";
		passThroughData.password = "mpxAdmin12345";
		//Search String and Context
		passThroughData.searchInput = '*P*';
        passThroughData.searchContext = null;

        var sequence:SequenceRunner = new SequenceRunner( this );

         sequence.addStep( new SequenceSetter( searchPanel.authPanel.tiUsername, {text:passThroughData.username} ) );
        sequence.addStep( new SequenceWaiter( searchPanel.authPanel.tiUsername, FlexEvent.VALUE_COMMIT, 100 ) );

        sequence.addStep( new SequenceSetter( searchPanel.authPanel.tiPassword, {text:passThroughData.password} ) );
        sequence.addStep( new SequenceWaiter( searchPanel.authPanel.tiPassword, FlexEvent.VALUE_COMMIT, 100 ) );

        sequence.addStep( new SequenceSetter( searchPanel.authPanel.tiServerAddress, {text:passThroughData.serverAddress} ) );
        sequence.addStep( new SequenceWaiter( searchPanel.authPanel.tiServerAddress, FlexEvent.VALUE_COMMIT, 5000 ) );

        sequence.addStep( new SequenceEventDispatcher( searchPanel.authPanel.okBtn, new MouseEvent( 'click', true, false ) ) );
		trace("Auth Panel click Done");

        sequence.addStep( new SequenceSetter( searchPanel.searchTxtInput, {text:passThroughData.searchInput} ) );
        sequence.addStep( new SequenceWaiter( searchPanel.searchTxtInput, FlexEvent.VALUE_COMMIT,100 ) );

        sequence.addStep( new SequenceEventDispatcher( searchPanel.searchBtn, new MouseEvent( 'click', true, false ) ) );
        sequence.addStep( new SequenceWaiter( searchPanel.searchResults, CollectionEvent.COLLECTION_CHANGE, 1000 ) );
		trace("Search Panel click Done");

		trace("Sequence Add Assert Handler");
        sequence.addAssertHandler( handleModelChanged, passThroughData);
        trace("Sequence Going to Run");
        sequence.run();
		trace("Sequence Run Done");
       }

        protected function handleModelChanged( event:CollectionEvent, passThroughData:Object ):void {
        		trace("Inside Handle Model Changed");
        		var searchRes:ArrayCollection = event.target as ArrayCollection;
        		assertEquals( searchRes.getItemAt(0), 'aliases/Project1');
        }

       [After(order=1)]
     	override protected function tearDown():void
     	{
           UIImpersonator.removeChild( searchPanel );
           searchPanel = null;
        }

	}
}