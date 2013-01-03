"""
Copyright (C) 2010 2011 Cisco Systems

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
import xmlrpclib, sys, socket, time
import feedparser
import urllib
import urllib2
import base64


def init():
	global nbm_ip, cloud_config_nbm, cloud_config_peer, alarm_config_nbm, alarm_config_peer
	global peer_ip, peer_ip_hostname, peer_ip, portal_ip, portal_ip_hostname
	global delay_for_portal_propagation,delay_for_peer_propagation

	nbm_ip = '72.163.203.72'
	peer_ip = '72.163.203.59'
	portal_ip = '72.163.203.221'
	peer_ip_hostname = gethostaddr(peer_ip)
	portal_ip_hostname = gethostaddr(portal_ip)
	delay_for_portal_propagation=20
	delay_for_peer_propagation=5
	url_nbm = 'https://mpxadmin:mpxadmin@' + nbm_ip + '/XMLRPCv2/RNA/services/network/https_server/Cloud%20Configurator'
	url_peer = 'https://mpxadmin:mpxadmin@' + peer_ip + '/XMLRPCv2/RNA/services/network/https_server/Cloud%20Configurator'
	cloud_config_nbm = xmlrpclib.ServerProxy(url_nbm)
	cloud_config_peer = xmlrpclib.ServerProxy(url_peer)
	url_nbm = 'https://mpxadmin:mpxadmin@' + nbm_ip + '/XMLRPCv2/RNA/services/network/https_server/Alarm%20Configurator'
	url_peer = 'https://mpxadmin:mpxadmin@' + peer_ip + '/XMLRPCv2/RNA/services/network/https_server/Alarm%20Configurator'
	alarm_config_nbm = xmlrpclib.ServerProxy(url_nbm)
	alarm_config_peer = xmlrpclib.ServerProxy(url_peer)
	cleanup()
	
	
	
	test_one_liners()


def gethostaddr(ip):
	hostname = '0.0.0.0'
	try:
		res = socket.gethostbyaddr(ip)
		hostname = res[0]
	except socket.error , msg :
		print 'Unable to resolve the hostname=%s Error message=%s' % (hostname, msg)
	return(hostname)

def create_alarm(nbm_ip,alarm_name):
	url = 'https://'+nbm_ip+'/alarmconfig'
	values = {
			'configure':alarm_name,
			'debug':0,
			'description':'dddd',
			'enabled':'1',
			'max_accepted':'1000',
			'max_cleared':'1000',
			'max_raised':'1000',
			'name':alarm_name,
			'parent':'/services/Alarm Manager',
			'priority':'P1',
			'source':'Alarm Configurator'
		}

	data = urllib.urlencode(values)
	req = urllib2.Request(url, data)
	username='mpxadmin'
	password='mpxadmin'
	base64string =  base64.encodestring(
					'%s:%s' % (username, password))[:-1]
	authheader =  "Basic %s" % base64string
	req.add_header("Authorization", authheader)

	try:
		response = urllib2.urlopen(req)
		the_page = response.read()
	except urllib2.URLError, e:
		raise TestError("Create Alarm Failed. Exception raised reason=%s" %(e.reason))
	else:
		if(the_page.find(alarm_name) == -1 ):
			raise TestError("Create Alarm Failed. Mediator response=%s" %(the_page))
	
	time.sleep(1)

def trigger_alarm(med_ip,alarm_name):
	values={
		'trigger': alarm_name
		}
	url = 'https://'+med_ip+'/alarmconfig'
	data = urllib.urlencode(values)
	req = urllib2.Request(url, data)
	username='mpxadmin'
	password='mpxadmin'
	base64string =  base64.encodestring(
					'%s:%s' % (username, password))[:-1]
	authheader =  "Basic %s" % base64string
	req.add_header("Authorization", authheader)
	try:
		response = urllib2.urlopen(req)
		the_page = response.read()
	except urllib2.URLError, e:
		raise TestError("Trigger Alarm Failed. Exception raised reason=%s" %(e.reason))
	else:
		if(the_page.find(alarm_name) == -1 ):
			raise TestError("Trigger Alarm Failed. Mediator response=%s" %(the_page))
	
	time.sleep(1)

def ack_alarm_event(med_ip,alarm_name):
	clientid=get_clientid()
	url='https://mpxadmin:mpxadmin@'+med_ip+'/syndication?clientid='+clientid
	d = feedparser.parse(url)
	total_events= len(d['items'])
	i=0
	items_dict=d['items']
	guid=''
	while(i<total_events):
		d1=items_dict[i]
		alarm_event=d1['title']
		if(alarm_event.startswith(alarm_name) ):
			x=alarm_event.split()
			alarm_state=x[-1]
			if(alarm_state == 'RAISED'):
				x=d1['id']
				y=x.split('/')
				guid=y[-1]
				break
		i+=1

	if(guid==''):
		raise TestError("ack_alarm_event Failed:Unable to find an Alarm %s in RAISED state for Acknowledging" )

	#https://10.20.138.87/d5caf154-d3d4-11e0-a7cb-001e7a8ce91c
	clientid=get_clientid()
	values={
			'clientid': clientid,
			'command': 'acknowledge',
			'guid':	guid
		}
	url = 'https://'+med_ip+'/syndication'
	data = urllib.urlencode(values)
	req = urllib2.Request(url, data)
	username='mpxadmin'
	password='mpxadmin'
	base64string =  base64.encodestring(
					'%s:%s' % (username, password))[:-1]
	authheader =  "Basic %s" % base64string
	req.add_header("Authorization", authheader)
	response = urllib2.urlopen(req)
	assert_alarm_event_state(med_ip,alarm_name,'ACCEPTED')

	
def get_clientid():
	time.sleep(1)
	return(str(time.time()))

def get_alarm_name():
	prefix=str(time.time())
	suffix='auto_alrm'
	alarm_name=prefix+suffix
	return(alarm_name)

def is_alarm_event_present_in_state(med_ip,alarm_name,state):
	tries=0
	while(tries < 3):
		clientid=get_clientid()
		url='https://mpxadmin:mpxadmin@'+med_ip+'/syndication?clientid='+clientid
		d = feedparser.parse(url)
		total_events= len(d['items'])
		if(total_events > 0):
			break
		tries +=1
	
	i=0
	items_dict=d['items']
	while(i<total_events):
		d1=items_dict[i]
		alarm_event=d1['title']
		if(alarm_event.startswith(alarm_name) ):
			x=alarm_event.split()
			alarm_state=x[-1]
			if(alarm_state == state):
				return(True)
		i+=1
	return(False)	

def clear_alarm(nbm_ip,alarm_name):
	values={
		'clear': alarm_name
		}
	url = 'https://'+nbm_ip+'/alarmconfig'
	data = urllib.urlencode(values)
	req = urllib2.Request(url, data)
	username='mpxadmin'
	password='mpxadmin'
	base64string =  base64.encodestring(
					'%s:%s' % (username, password))[:-1]
	authheader =  "Basic %s" % base64string
	req.add_header("Authorization", authheader)
	response = urllib2.urlopen(req)
	the_page = response.read()
	assert_alarm_event_state(nbm_ip,alarm_name,'CLOSED')

def poll_on_close(portal_ip,alarm_name):
	t=0
	passed=False
	while(t<300):
		time.sleep(20)
		if(is_alarm_event_present_in_state(portal_ip,alarm_name,'CLOSED') == False):
			passed=True
			break;
		t+=20
	if(passed == False):
		raise TestError("Alarm Event %s has not got CLOSED" %(alarm_name))

def assert_alarm_event_state(med_ip,alarm_name,state):
	if(is_alarm_event_present_in_state(med_ip,alarm_name,state)== False):
			raise TestError("Triggered Alarm %s not in %s State " %(alarm_name,state))
	
	
def create_and_trigger_alarms(alarm_names_list,med_ip):
	for i in alarm_names_list:
		create_alarm(med_ip,i)
		trigger_alarm(med_ip,i)
		assert_alarm_event_state(med_ip,i,'RAISED')

def check_alarm_states(alarm_list,med_ip,state):
	for i in alarm_list:
		assert_alarm_event_state(med_ip,i,state)


def test_one_liners():
	global test_desc
	test_desc = [
			(test2, 'Add a Peer'),
			(test3,'Remove a Peer'),
			(test4,'Add a Peer that already exists'),
			(test5,'Add a Peer using hostname and not IP Address'),
			(test6,'Add a Peer that already exists by using hostname'),
			(test13,'Add self as a Peer'),
			(test7,'Add a invalid IP Address as peer'),
			(test8,'Add a Portal '),
			(test9,'Add a Portal and a Peer,see if the portal is reflected correctly on Peer'),
			(test10,'Add a Portal that already exists'),
			(test11,'Add a Portal using hostname and not IP Address'),
			(test12,'Add a Portal that already exists by using hostname'),
			(test14,'Add self as a Portal'),
			(test15,'Add a invalid IP Address as a Portal'),
			(test16,'Add a Peer and then try to add the same as Portal.It should Fail'),
			(test17,'Events raised on a Peer should be seen on every node in the Cloud'),
			(test18,'Events raised on a peer can be acknowledged in any of the members of the Cloud'),
			(test19,'Events raised on a Peer can be Cleared at the same Peer'),
			(test20,'Events raised on a Peer would be visible on the Portal'),
			(test21,'Events raised on a Peer can be acknowledged from the Portal'),
			(test22,'Events appearing on the Portal should go away after they has been closed Locally'),
			(test23,'When a New peer B is added, the existing events of the B and the cloud C should be in Synced up'),
			(test24,'When a New Portal P is added, the existing events of the Mediator should be Synced up '),
			(test25,'When a New Portal P is added, the existing events of the cloud C should be Synced up ')
		]

class TestError(Exception):
	def __init__(self, failure):
		self.failure = failure
	def __str__(self):
		msg = self.failure
		return repr(msg)

def add_peer():
	try:
		cloud_config_nbm.create_node(peer_ip, {'type':'peer'})
		nodes_in_nbm = cloud_config_nbm.get_node_names()
		nodes_in_peer = cloud_config_peer.get_node_names()
	except xmlrpclib.Fault, e:
		raise TestError("Add peer failed xml rpc failed %s" % (str(e)))
	else:
		if((not peer_ip in nodes_in_nbm) or (not nbm_ip in nodes_in_nbm)):
			raise TestError("Add peer failed. peer and nbm not in sync")

		if((not peer_ip in nodes_in_peer) or (not nbm_ip in nodes_in_peer)):
			raise TestError("Add peer failed peer and nbm not in sync")
		
def remove_peer():
	try:
		cloud_config_nbm.remove_node(peer_ip)
		nodes_in_nbm = cloud_config_nbm.get_node_names()
		nodes_in_peer = cloud_config_peer.get_node_names()
	except xmlrpclib.Fault, e:
		raise TestError("Remove peer failed. xml rpc failed %s" % (str(e)))
	else:
		if(peer_ip in nodes_in_nbm):
			raise TestError("Remove peer failed.peer and nbm not in sync")
		if(nbm_ip in nodes_in_peer):
			raise TestError("Remove peer failed. peer and nbm not in sync")	

def add_portal():
	try:
		cloud_config_nbm.create_node(portal_ip, {'type':'portal'})
		nodes=cloud_config_nbm.get_node_names()
	except xmlrpclib.Fault, e:
		raise TestError("Add portal failed. xml rpc failed %s" % (str(e)))
	else:
		if(portal_ip != nodes[0]):
			raise TestError("Add Portal failed.Portal is not reflected in the gui")

def wait_for_portal_propagation():
	time.sleep(delay_for_portal_propagation)
	
def wait_for_peer_propagation():
	time.sleep(delay_for_peer_propagation)


def cleanup():
	time.sleep(1)
	nodes = cloud_config_nbm.get_node_names()
	for m in nodes:
		if((m != '') and (m != nbm_ip)):
			time.sleep(1)
			cloud_config_nbm.remove_node(m)
	
'''
Test 2: Add a Peer
'''
def test2():
	add_peer()

'''
Test 3: Remove a Peer
'''
def test3():
	add_peer()
	remove_peer()

'''
Test 4: Add a Peer that already exists
'''
def test4():
	add_peer()
	try:
		cloud_config_nbm.create_node(peer_ip, {'type':'peer'})
	except xmlrpclib.Fault, e:
		str_exc = str(e)
		if(str_exc.find('Add peer did nothing') == -1):
			raise TestError("RPC Allows to add a existing peer again")
	else:
		raise TestError("Allows to add a existing peer again")

'''
Test 5: Add a Peer using hostname and not IP Address
'''
def test5():
	try:
		cloud_config_nbm.create_node(peer_ip_hostname, {'type':'peer'})
		nodes_in_nbm = cloud_config_nbm.get_node_names()
		nodes_in_peer = cloud_config_peer.get_node_names()
	except xmlrpclib.Fault, e:
		raise TestError("RPC Failed",'reason %s' %(e))
	else:
		if(not peer_ip_hostname in nodes_in_nbm):
			raise TestError("Adding hostname Failed")	
		if(not peer_ip_hostname in nodes_in_peer):
			raise TestError("Adding hostname Failed")	

'''
Test 6: Add a Peer that already exists by using hostname
'''
def test6():
	add_peer()

	# Added a Peer. Now try adding it again
	try:
		cloud_config_nbm.create_node(peer_ip_hostname, {'type':'peer'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('Add peer did nothing') == -1):
			raise TestError("Allows Adding a Peer that already exists. Unknown exception raised")
	else:
		raise TestError("Allows Adding a Peer that already exists. No exception raised")		

'''
Test 13: Add self as a Peer
'''
def test13():
	try:
		cloud_config_nbm.create_node(nbm_ip, {'type':'peer'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('Add peer did nothing') == -1):
			raise TestError("Allows Adding self as a Peer. Unknown exception raised")
	else:
		raise TestError("Allows Adding self as a Peer. No exception raised")

'''
Test 7: Add a invalid IP Address as peer
'''
def test7():
	try:
		cloud_config_nbm.create_node('12.256.5.6', {'type':'peer'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('is a invalid hostname/IP Address') == -1):
			raise TestError("Allows Adding a invalid IP Address. Unknown exception raised")
	else:
		raise TestError("Allows Adding a invalid IP Address. No exception raised")

'''
Test 8: Add a Portal 
'''
def test8():
	add_portal()

'''
Test 9: Add a Portal and a Peer,see if the portal is reflected correctly on Peer
'''
def test9():
	add_peer()
	add_portal()
	try:
		nodes=cloud_config_peer.get_node_names()
	except xmlrpclib.Fault,e:
		raise TestError("RPC Failed",'reason %s' %(e))
	else:	
		if(portal_ip != nodes[0]):
			raise TestError("The portal is not reflected on the peer")

'''
Test 10: Add a Portal that already exists
'''
def test10():
	add_portal()
	# Added a portal. Now try adding it again
	try:
		cloud_config_nbm.create_node(portal_ip, {'type':'portal'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('Set Portal did nothing') == -1):
			raise TestError("Allows Adding a Portal that already exists. Unknown exception raised",'reason %s' %(e))
	else:
		raise TestError("Allows Adding a Portal that already exists. No exception raised")

'''
Test 11: Add a Portal using hostname and not IP Address
'''
def test11():
	try:
		cloud_config_nbm.create_node(portal_ip_hostname, {'type':'portal'})
		nodes=cloud_config_nbm.get_node_names()
	except xmlrpclib.Fault,e:
		raise TestError("RPC Failed",'reason %s' %(e))
	else:	
		if(portal_ip_hostname != nodes[0]):
			raise TestError("Portal using hostname is not reflected on the nbm")

'''
Test 12: Add a Portal that already exists by using hostname
'''
def test12():
	add_portal()
	# Added a Portal. Now try adding it again with ip
	try:
		cloud_config_nbm.create_node(portal_ip, {'type':'portal'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('Set Portal did nothing') == -1):
			raise TestError("Allows Adding a Portal that already exists by using hostname. Unknown exception raised %s" %(e))
	else:
		raise TestError("Allows Adding a Portal that already exists by using hostname. No exception raised")

'''
Test 14: Add self as a Portal
'''
def test14():
	try:
		cloud_config_nbm.create_node(nbm_ip, {'type':'portal'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('It cannot be added as Portal') == -1):
			raise TestError("Allows Adding self as Portal.Unknown exception raised %s" %(e))
	else:
		raise TestError("Allows Adding self as a Portal.No exception raised")

'''
Test 15: Add a invalid IP Address as Portal
'''
def test15():
	try:
		cloud_config_nbm.create_node('12.256.5.6', {'type':'portal'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('is a invalid hostname/IP Address') == -1):
			raise TestError("Allows Adding a invalid IP Address as Portal. Unknown exception raised %s" %(e))
	else:
		raise TestError("Allows Adding a invalid IP Address as Portal. No exception raised")

'''
( test16,'Add a Peer and then try to add the same as Portal.It should Fail')
'''
def test16():
	add_peer()
	# Try adding the same as Portal
	try:
		cloud_config_nbm.create_node(peer_ip, {'type':'portal'})
	except xmlrpclib.Fault,e:
		str_exc=str(e)
		if(str_exc.find('It cannot be added as Portal') == -1):
			raise TestError("Allows Adding a peer again as a Portal.Unknown exception raised %s" %(e))
	else:
		raise TestError("Allows a peer again as a Portal. No exception raised")
'''
( test17,'Events raised on a Peer should be seen on every node in the Cloud'),
'''
def test17():
	add_peer()
	alarm_name=get_alarm_name()
	create_alarm(peer_ip,alarm_name)
	trigger_alarm(peer_ip,alarm_name)
	wait_for_peer_propagation()
	assert_alarm_event_state(nbm_ip,alarm_name,'RAISED')
	
'''
( test18,'Events raised on a peer can be acknowledged in any of the members of the Cloud'),
'''
def test18():
	add_peer()
	alarm_name=get_alarm_name()
	create_alarm(nbm_ip,alarm_name)
	trigger_alarm(nbm_ip,alarm_name)
	wait_for_peer_propagation()
	assert_alarm_event_state(peer_ip,alarm_name,'RAISED')
	ack_alarm_event(peer_ip,alarm_name)

'''
( test19,'Events raised on a Peer can be Cleared at the same Peer'),
'''
def test19():
	add_peer()
	alarm_name=get_alarm_name()
	create_alarm(nbm_ip,alarm_name)
	trigger_alarm(nbm_ip,alarm_name)
	wait_for_peer_propagation()
	assert_alarm_event_state(peer_ip,alarm_name,'RAISED')
	ack_alarm_event(peer_ip,alarm_name)
	clear_alarm(nbm_ip,alarm_name)

'''
( test20,'Events raised on a mediator would be visible on the Portal'),
'''
def test20():
	add_portal()
	alarm_name=get_alarm_name()
	create_alarm(nbm_ip,alarm_name)
	trigger_alarm(nbm_ip,alarm_name)
	wait_for_portal_propagation()
	assert_alarm_event_state(portal_ip,alarm_name,'RAISED')

'''
( test21,'Events raised on a Peer can be acknowledged from the Portal'),
'''
def test21():
	add_portal()
	alarm_name=get_alarm_name()
	create_alarm(nbm_ip,alarm_name)
	trigger_alarm(nbm_ip,alarm_name)
	wait_for_portal_propagation()
	assert_alarm_event_state(portal_ip,alarm_name,'RAISED')
	ack_alarm_event(portal_ip,alarm_name)

'''
( test22,'Events appearing on the Portal should go away after they has been closed Locally')
'''
def test22():
	add_portal()
	alarm_name=get_alarm_name()
	create_alarm(nbm_ip,alarm_name)
	trigger_alarm(nbm_ip,alarm_name)
	wait_for_portal_propagation()
	assert_alarm_event_state(portal_ip,alarm_name,'RAISED')
	ack_alarm_event(portal_ip,alarm_name)
	clear_alarm(nbm_ip,alarm_name)
	poll_on_close(portal_ip,alarm_name)

'''
( test23,'When a New peer B is added, the existing events of B and the cloud C should be Synced up ')
'''
def test23():
	alarm_name=get_alarm_name()
	m1_names=['m1a1','m1a2','m1a3']
	m1_names=[x+alarm_name for x in m1_names]
	m2_names=['m2a1','m2a2','m2a3']
	m2_names=[x+alarm_name for x in m2_names]
	all_names=m1_names+m2_names
	
	create_and_trigger_alarms(m1_names,nbm_ip)
	create_and_trigger_alarms(m2_names,peer_ip)
	add_peer()
	wait_for_peer_propagation()
	check_alarm_states(all_names,nbm_ip,'RAISED')
	check_alarm_states(all_names,peer_ip,'RAISED')

'''
( test24,'When a New Portal P is added, the existing events of the Mediator should be Synced up ')
'''
def test24():
	alarm_name=get_alarm_name()
	m1_names=['m1a1','m1a2','m1a3']
	m1_names=[x+alarm_name for x in m1_names]
	
	create_and_trigger_alarms(m1_names,nbm_ip)
	add_portal()
	wait_for_portal_propagation()
	check_alarm_states(m1_names,portal_ip,'RAISED')

'''
( test25,'When a New Portal P is added, the existing events of the cloud C should be Synced up ')
'''
def test25():
	alarm_name=get_alarm_name()
	m1_names=['m1a1','m1a2','m1a3']
	m1_names=[x+alarm_name for x in m1_names]
	m2_names=['m2a1','m2a2','m2a3']
	m2_names=[x+alarm_name for x in m2_names]
	all_names=m1_names+m2_names
	
	create_and_trigger_alarms(m1_names,nbm_ip)
	create_and_trigger_alarms(m2_names,peer_ip)
	add_peer()
	wait_for_peer_propagation()
	add_portal()
	wait_for_portal_propagation()
	wait_for_portal_propagation()
	check_alarm_states(all_names,portal_ip,'RAISED')
	
	
def main():
	init()
	cntr = 1
	for entry in test_desc:
		test_fn=entry[0]
		
		#if ( not ((test_fn==main) or (test_fn == test25))):
		#	continue
		
		#if(cntr < 21):
		#	cntr +=1
		#	continue
		
		try:
			test_fn()
		except TestError, e:
			print 'Test ',cntr, ' Failed ',entry[1],'[', e,']'
		else:
			print 'Test :',cntr, ' Passed ',entry[1]
		finally:
			cleanup()
		cntr +=1
	
	print 'All Tests are complete'
		
main()
