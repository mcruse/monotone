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
##
# Defines the base node classes and interfaces.
#
import sys
import lxml.etree as etree

# Borrow some utility functions from moab/linux/bin/mpxconfig.py:
def _getChildElementByName( node, name ):
    for n in node.childNodes:
        if n.nodeType == n.ELEMENT_NODE:
            if n.getAttribute( 'name' ) == name:
                return n
    return None

def _getChildElementByNameLxml( elem, name ):
    for n in range(0, len(elem)):
        child = elem[n]
        if child.tag == 'node':
            if child.get( 'name' ) == name:
                return child
    return None

def _getChildPropertyByNameLxml( elem, name ):
    for n in range(0, len(elem)):
        child = elem[n]
        if child.tag == 'property':
            if child.get( 'name' ) == name:
                return child
    return None

def _getElementByPath( doc, path ):
    elem = doc.documentElement
    for name in path.split( '/' ):
        if name == '':
            name = '/'
        elem = _getChildElementByName( elem, name )
        if elem is None:
            break
    return elem

def _getElementByPathLxml( elemTree, path ):
    elem = elemTree
    for name in path.split( '/' ):
        if name == '':
            name = '/'
        elem = _getChildElementByNameLxml( elem, name )
        if elem is None:
            break
    return elem

def _setElementValueFromConfig( elem, config_parser, section, optName ):
    value = _read_conf_value( config_parser, section, optName )
#    assert( value != None )
    elem.setAttribute( 'value', value )
    
def _setChildValue( parent, childName, value ):
    elem = _getChildElementByName( parent, childName )
    if not elem:
        elem = _createProperty( parent, childName )
    elem.setAttribute( 'value', value )

def _setChildValueFromConfig( parent, childName, config_parser, section, optName = None ):
    if not optName:
        optName = childName
    elem = _getChildElementByName( parent, childName )
    if not elem:
        elem = _createProperty( parent, childName )
    _setElementValueFromConfig( elem, config_parser, section, optName )

sys.argv.pop(0) # fully-qualified name of XML file
strFQN = 'broadway-stripped.xml'
if len(sys.argv):
    strFQN = sys.argv.pop(0) # fully-qualified name of XML file
server_addr = '192.168.2.101'
if len(sys.argv):
    server_addr = sys.argv.pop(0)
client_addr = '192.168.2.100'
if len(sys.argv):
    client_addr = sys.argv.pop(0)
server_interfaces = ['eth0']
if len(sys.argv):
    server_interfaces = eval(sys.argv.pop(0)) # on cmd line, eg: ['eth0', 'eth1']
scheme = 'mpx'
security_level = 'NoSec'
if len(sys.argv):
    scheme = sys.argv.pop(0) # or 'mpxao' or 'mpxfe'
if scheme == 'mpxao':
    security_level = 'Auth-Only'
elif scheme == 'mpxfe':
    security_level = 'Full-Enc'
subscr_mgr = 'noSM'
if len(sys.argv):
    subscr_mgr = sys.argv.pop(0) # 'noSM' or 'yesSM'


# Load Generic minimally-configured broadway.xml file into Client ElementTree:
parser = etree.XMLParser(remove_blank_text=True)
treeClient = etree.parse(strFQN, parser)
rootClient = treeClient.getroot()
# Get "aliases" and "periodic_log_1" Elements from Client tree:
elemAliases = _getElementByPathLxml(rootClient, '/aliases')
elemPerLogCols = _getElementByPathLxml(rootClient, '/services/logger/periodic_log_1/columns')
# Load Generic minimally-configured broadway.xml file into Server ElementTree:
treeServer = etree.parse(strFQN, parser)
rootServer = treeServer.getroot()
# Get "virtuals" and "rna" Elements from Server tree:
elemVirts = _getElementByPathLxml(rootServer, '/interfaces/virtuals')
elemRnaService = _getElementByPathLxml(rootServer, '/services/network/rna')
# Reconfig rna service node right now:
dictPropAttrSecLevel = \
{   'name':'security_level',\
    'value':security_level \
}
elemRnaServiceConfig = elemRnaService.find('config')
elemSecLevel = etree.SubElement(elemRnaServiceConfig, 'property', dictPropAttrSecLevel)
elemInterface = _getChildPropertyByNameLxml(elemRnaServiceConfig, 'interface')
elemInterface.set('value', server_interfaces[0])

# Set up attribute dictionaries:
dictAttrAlias = \
{   'name':'TBD',\
    'node_id':'257',\
    'module':'mpx.service.alias.factory',\
    'config_builder':'',\
    'inherant':'false',\
    'description':'Alias (another name for an existing node)'\
}
dictPropAttrType = \
{   'name':'__type__',\
    'value':'point'\
}
dictPropAttrUrl = \
{   'name':'node_url',\
    'value':'%s://%s:5150/interfaces/virtuals/r' % (scheme, server_addr)\
}
dictPropAttrStatemt = \
{   'name':'statement',\
    'value':'random.randint(0,1000)'\
}
dictPropAttrVars = \
{   'name':'variables'\
}
dictAttrVirt = \
{   'name':'r',\
    'node_id':'780',\
    'module':'mpx.lib.translator.calculator.Calculator',\
    'config_builder':'',\
    'inherant':'false',\
    'description':'Calculated Virtual Point'\
}
dictAttrPerCol = \
{   'name':'periodic_column_', # to be modified \
    'node_id':'264',\
    'module':'mpx.service.logger.periodic_column.factory',\
    'config_builder':'envenergy.wizard.log.LogWizardPlugin_ToColumn',\
    'inherant':'false',\
    'description':'Periodic column'\
}
dictPropAttrDebug = \
{   'name':'debug',\
    'value':'0'\
}
dictPropAttrSM = \
{   'name':'use_subscription_manager',\
    'value':'1'\
}
dictPropAttrSortOrder = \
{   'name':'sort_order',\
    'value':'None'\
}
dictPropAttrPos = \
{   'name':'position',\
    'value':'1' # to be modified \
}
dictPropAttrCtx = \
{   'name':'context',\
    'value':'None'\
}
dictPropAttrArgs = \
{   'name':'args',\
    'value':'()'\
}
dictPropAttrFunc = \
{   'name':'function',\
    'value':'mpx.lib.node.as_node("/aliases/a{0}").get' # to be modified \
}
dictPropAttrConv = \
{   'name':'conversion',\
    'value':'magnitude'\
}
# Loop to create the number of new Alias, Periodic_Column, and Virtual nodes 
# specified on command line:
iElems = 10
if len(sys.argv):
    iElems = int(sys.argv.pop(0)) # Number of aliases to create
for iElem in range(0,iElems):
    # Add New Alias:
    elemNewAlias = etree.SubElement(elemAliases, 'node', dictAttrAlias)
    elemNewAlias.set('name', 'a' + str(iElem))
    # Add a "config" child element:
    elemNewConfig = etree.SubElement(elemNewAlias, 'config', None)
    # Add properties:
    etree.SubElement(elemNewConfig, 'property', dictPropAttrType)
    elemNewPropUrl = etree.SubElement(elemNewConfig, 'property', dictPropAttrUrl)
    elemNewPropUrl.set('value', dictPropAttrUrl['value'] + str(iElem))
    print(etree.tostring(elemNewAlias, pretty_print=True))
    # Corresponding New Virtual:
    elemNewVirt = etree.SubElement(elemVirts, 'node', dictAttrVirt)
    elemNewVirt.set('name', dictAttrVirt['name'] + str(iElem))
    # Add a "config" child element:
    elemNewVirtConfig = etree.SubElement(elemNewVirt, 'config', None)
    # Add properties:
    etree.SubElement(elemNewVirtConfig, 'property', dictPropAttrType)
    etree.SubElement(elemNewVirtConfig, 'property', dictPropAttrStatemt)
    elemNewPropVars = etree.SubElement(elemNewVirtConfig, 'property', dictPropAttrVars)
    etree.SubElement(elemNewPropVars, 'list', None)
    print(etree.tostring(elemNewVirt, pretty_print=True))
    if (subscr_mgr == 'yesSM') and elemPerLogCols:
        # Add New Periodic Log Column (to force inclusion in single-request SubscrMgr updates:
        elemNewPerCol = etree.SubElement(elemPerLogCols, 'node', dictAttrPerCol)
        elemNewPerCol.set('name', dictAttrPerCol['name'] + str(iElem + 1))
        # Add a "config" child element:
        elemNewConfig = etree.SubElement(elemNewPerCol, 'config', None)
        # Add properties:
        etree.SubElement(elemNewConfig, 'property', dictPropAttrType)
        etree.SubElement(elemNewConfig, 'property', dictPropAttrDebug)
        etree.SubElement(elemNewConfig, 'property', dictPropAttrSM)
        etree.SubElement(elemNewConfig, 'property', dictPropAttrSortOrder)
        dictPropAttrPos['value'] = str(iElem + 1)
        etree.SubElement(elemNewConfig, 'property', dictPropAttrPos)
        etree.SubElement(elemNewConfig, 'property', dictPropAttrCtx)
        etree.SubElement(elemNewConfig, 'property', dictPropAttrArgs)
        elemNewPropFunc = etree.SubElement(elemNewConfig, 'property', dictPropAttrFunc)
        elemNewPropFunc.set('value', elemNewPropFunc.get('value').format(str(iElem)))
        etree.SubElement(elemNewConfig, 'property', dictPropAttrConv)

# Write modified trees to files as pretty XML:
treeServer.write('broadway_server.xml',pretty_print=True)
treeClient.write('broadway_client.xml',pretty_print=True)

# SCP modified XML files to respective Mediators:
import subprocess
argsScp = ['scp', 'broadway_server.xml', 'mpxadmin@%s:/var/mpx/config/broadway.xml' % server_addr]
subprocess.call(argsScp)
argsScp = ['scp', 'broadway_client.xml', 'mpxadmin@%s:/var/mpx/config/broadway.xml' % client_addr]
subprocess.call(argsScp)




