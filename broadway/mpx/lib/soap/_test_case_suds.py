"""
Copyright (C) 2003 2010 2011 Cisco Systems

This program is free software; you can redistribute it and/or         
modify it under the terms of the GNU General Public License         
as published by the Free Software Foundation; either version 2         
of the License, or (at your option) any later version.         
    
This program is distributed in the hope that it will be useful,         
but WITHOUT ANY WARRANTY; without even the implied warranty of         
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
GNU General Public License for more details.         
    
You should have received a copy of the GNU General Public License         
along with this program; if not, write to:         
The Free Software Foundation, Inc.         
59 Temple Place - Suite 330         
Boston, MA  02111-1307, USA.         
    
As a special exception, if other files instantiate classes, templates  
or use macros or inline functions from this project, or you compile         
this file and link it with other works to produce a work based         
on this file, this file does not by itself cause the resulting         
work to be covered by the GNU General Public License. However         
the source code for this file must still be made available in         
accordance with section (3) of the GNU General Public License.         
    
This exception does not invalidate any other reasons why a work         
based on this file might be covered by the GNU General Public         
License.
"""
from mpx_test import DefaultTestFixture, main
import suds
from suds import parse_response, build_point_request

class TestCase(DefaultTestFixture):
    def test_case_build_point_request(self):
        list = []
        list.append([['Name','Differential Pressure 1'], ['Type','analog']])
        list.append([['Name','Differential Pressure 3'], ['Type','analog']])
        x = build_point_request(list)
        s = """
<Request>
  <DataRequest>
    <Request>
      <Name>Differential Pressure 1</Name>
      <Type>analog</Type>
    </Request>
    <Request>
      <Name>Differential Pressure 3</Name>
      <Type>analog</Type>
    </Request>
  </DataRequest>
</Request>
"""
        if x != s: 
            raise 'SOAP point request failed'
        
    def test_case_parse_response(self):
        s = """<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><GetAllDataResponse xmlns="http://RCKServices.com/"><GetAllDataResult><SimData xmlns="http://RCKServices.com/CHWData.xsd"><PointData><Name>Differential Pressure 1</Name><Type>analog</Type><Value>17.67489</Value><Address>0</Address><Channel>0</Channel><ScaledZero>0</ScaledZero><ScaledFull>30</ScaledFull></PointData><PointData><Name>Differential Pressure 2</Name><Type>analog</Type><Value>19.72186</Value><Address>1</Address><Channel>1</Channel><ScaledZero>0</ScaledZero><ScaledFull>20</ScaledFull></PointData><PointData><Name>Differential Pressure 3</Name><Type>analog</Type><Value>27.32893</Value><Address>2</Address><Channel>2</Channel><ScaledZero>0</ScaledZero><ScaledFull>30</ScaledFull></PointData><PointData><Name>Differential Pressure 4</Name><Type>analog</Type><Value>11.3433</Value><Address>3</Address><Channel>3</Channel><ScaledZero>0</ScaledZero><ScaledFull>50</ScaledFull></PointData></SimData></GetAllDataResult></GetAllDataResponse></soap:Body></soap:Envelope>"""
        p = parse_response(s)
        x = {'Differential Pressure 3': {'Value': '27.32893', 
                                         'ScaledFull': '30', 
                                         'Name': 'Differential Pressure 3', 
                                         'Address': '2', 
                                         'ScaledZero': '0', 
                                         'Type': 'analog', 
                                         'Channel': '2'}, 
             'Differential Pressure 2': {'Value': '19.72186', 
                                         'ScaledFull': '20', 
                                         'Name': 'Differential Pressure 2', 
                                         'Address': '1', 
                                         'ScaledZero': '0', 
                                         'Type': 'analog', 
                                         'Channel': '1'}, 
             'Differential Pressure 1': {'Value': '17.67489',
                                         'ScaledFull': '30', 
                                         'Name': 'Differential Pressure 1', 
                                         'Address': '0', 
                                         'ScaledZero': '0', 
                                         'Type': 'analog', 
                                         'Channel': '0'}, 
             'Differential Pressure 4': {'Value': '11.3433', 
                                         'ScaledFull': '50', 
                                         'Name': 'Differential Pressure 4', 
                                         'Address': '3', 
                                         'ScaledZero': '0', 
                                         'Type': 'analog', 
                                         'Channel': '3'}}
        if x !=p:
            raise 'failed to parse xml response string'
         
def _integration_test_send_request_GetAllData():
    host = 'www.dev1.eraserver.net'
    post = '/RCKCONTROLS/RCKData.asmx'
    action_server = 'http://RCKServices.com/'
    action = 'GetAllData'
    request = ''
    envelope_start = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <""" + action + ' xmlns="' + action_server + '" />'
    envelope_end = """
      </soap:Body>
    </soap:Envelope>
    """
    r = suds.send_request(host, post, action_server + action, envelope_start + request + envelope_end)
    print r
    rsp = parse_response(r)
    print rsp
    return rsp

def _integration_test_send_request_GetRequestedData():
    host = 'www.dev1.eraserver.net'
    post = '/RCKCONTROLS/RCKData.asmx'
    action_server = 'http://RCKServices.com/'
    action = 'GetRequestedData'
    list = []
    list.append([['Name','Differential Pressure 1'], ['Type','analog']])
    list.append([['Name','Differential Pressure 3'], ['Type','analog']])
    request = build_point_request(list)
    print request
    envelope_start = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <""" + action + ' xmlns="' + action_server + '" >'
    envelope_end = """
        </""" + action + """>
      </soap:Body>
    </soap:Envelope>
    """
    r = suds.send_request(host, post, action_server + action, envelope_start + request + envelope_end)
    print r
    rsp = parse_response(r)
    print rsp
    return rsp

#_integration_test_send_request_GetAllData()
#_integration_test_send_request_GetRequestedData()

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
