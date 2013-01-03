How to wash up with SOAP:

SOAP stands for Simple Object Access Protocol and is used as a XML based protocol 
between a client and a server.  We have implemented a client module only at this time.

There can be three roles present in a SOAP transaction.  The Host, the Client and
the Server.  The Client POSTS a request to the Host.  The Host contacts the Server, 
gathers data and sends back a XML encoded result to the client.  The three roles can be
present on one to three computers.  In the RCK controls test setup, there are three seperate
computers.

The SOAP module presents three types of nodes for your viewing pleasure:

1) A Host node where we specify the URL of the host computer, such as: 
    www.dev1.eraserver.net
2) A SOAP Action node where we specify the host relative URL of the SOAP document,
   the URL of the Server and the Action we would like the server to perform.
3) A SOAP point where we specify the Name of the point and the Type of data.

The test setup includes the following values:

Host = www.dev1.eraserver.net

POST = /RCKCONTROLS/RCKData.asmx
Server = http://RCKServices.com/
Action = GetRequestedData

Name = Differential Pressure 1
Type = analog

other available point names are:

Differential Pressure 2
Differential Pressure 3
Differential Pressure 4

piece of cake!

