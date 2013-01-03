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
#!/usr/bin/python

##
# @todo: make export period configurable.  Hard coded to 1hr
import sys
import urllib
import time
import os

from optparse import OptionParser

from xml.dom import minidom
from xml.dom import Node

DOC = None
LOG_MIN_SZ = '250'
LOG_MAX_SZ = '750'
# defaults for command line options
XML_IN = 'base-broadway.xml' #-i --infile
XML_OUT = 'broadway.xml' # -o --outfile
USE_SM = 0 # -u --use_sm
BASE_MODULE = 'service.data.enernoc' # -m --factory
CSV_IN = 'logs.csv' # -c --csvfile
FTP_SPEC = '' # -f --ftp_spec
FREQUENCY = '900' # -f --frequency

class FtpSpec(object):
    def __init__(self, **kw):
        self.name_scheme = 'timestamp'
        self.password = 'MeDiaToR'
        self.directory = '/home/csusm'
        self.timeout = '60'
        self.passive_mode = 'on'
        self.host = 'mail.enernoc.net'
        self.file_suffix = '.csv'
        self.username = 'csusm'
        for k,v in kw.items():
            setattr(self, k, v)
        return
    
class Column(object):
    def __init__(self, data_stream_name, measure, commodity, 
                 measurement_type, nodepath, uom):
        self.data_stream_name = data_stream_name
        self.measure = measure
        self.commodity = commodity
        self.measurement_type = measurement_type
        self.nodepath = nodepath
        self.uom = uom
        return

"""
<node name='exporters' node_id='461' module='mpx.lib.node.factory'  
  config_builder='envenergy.wizard.log.LogWizardPlugin_ToExporters'  
  inherant='true' description='Exporters'>
</node>
"""
def make_exporter():
    exporter = new_node(
        'exporters', 
        '461', 
        'mpx.lib.node.factory', 
        'true',
        'Exporters', 
        'envenergy.wizard.log.LogWizardPlugin_ToExporters'
        )
    return exporter

"""
<node name='periodic_exporter' node_id='333' module='mpx.service.data.periodic_exporter.factory'  
  config_builder='envenergy.wizard.log.LogWizardPlugin_ToExporter'  inherant='false' 
  description='Standard periodic data exporter'>
    <config>
      <property name='__type__' value='point'/>
      <property name='debug' value='0'/>
      <property name='days' value='1'/>
      <property name='timeout' value='60'/>
      <property name='connection_attempts' value='1'/>
      <property name='always_export' value='1'/>
      <property name='enabled' value='1'/>
      <property name='synchronize_on' value='00:00'/>
      <property name='hours' value='0'/>
      <property name='gm_time' value='0'/>
      <property name='connection_node' value='/services/network'/>
      <property name='minutes' value='0'/>
</config>
"""
def make_periodic_exporter(name, use_gmt=1):
    global DOC
    pe = new_node(
        name, 
        '333', 
        'mpx.service.data.periodic_exporter.factory', 
        'false',
        'Standard periodic data exporter', 
        'envenergy.wizard.log.LogWizardPlugin_ToExporter'
        )
    config = DOC.createElement('config')
    pe.appendChild(config)
    config.appendChild(add_prop('__type__', 'point'))
    config.appendChild(add_prop('debug', '0'))
    config.appendChild(add_prop('days', '0'))
    config.appendChild(add_prop('timeout', '60'))
    config.appendChild(add_prop('connection_attempts', '1'))
    config.appendChild(add_prop('always_export', '1'))
    config.appendChild(add_prop('enabled', '1'))
    config.appendChild(add_prop('synchronize_on', '00:00'))
    config.appendChild(add_prop('hours', '1'))
    config.appendChild(add_prop('gm_time', str(use_gmt)))
    config.appendChild(add_prop('connection_node', '/services/network'))
    config.appendChild(add_prop('minutes', '0'))
    return pe
    
"""
<node name='ftp_transporter' node_id='332' module='mpx.service.data.ftp_transporter.factory'  
  config_builder=''  inherant='false' description='FTP transporter'>
    <config>
      <property name='__type__' value='service'/>
      <property name='debug' value='0'/>
      <property name='name_scheme' value='timestamp'/>
      <property name='password' value='qwertjkl;69'/>
      <property name='directory' value='/'/>
      <property name='timeout' value='60'/>
      <property name='passive_mode' value='on'/>
      <property name='enabled' value='1'/>
      <property name='host' value='ftp.energyowl.com'/>
      <property name='file_suffix' value='.xml'/>
      <property name='file_prefix' value='WoodlandHillsJHALLMARK'/>
      <property name='username' value='ftpuser'/>
    </config>
</node>
"""
def make_ftp_transporter(file_prefix, options):
    global DOC
    ftp = new_node(
        'ftp_transporter', 
        '332', 
        'mpx.service.data.ftp_transporter.factory', 
        'false', 
        'FTP transporter', 
        ''
        )
    config = DOC.createElement('config')
    ftp.appendChild(config)
    config.appendChild(add_prop('__type__', 'service'))
    config.appendChild(add_prop('debug', '0'))
    config.appendChild(add_prop('name_scheme', options.name_scheme))
    config.appendChild(add_prop('password', options.password))
    config.appendChild(add_prop('directory', options.directory))
    config.appendChild(add_prop('timeout', options.timeout))
    config.appendChild(add_prop('passive_mode', options.passive_mode))
    config.appendChild(add_prop('enabled', '1'))
    config.appendChild(add_prop('host', options.host))
    config.appendChild(add_prop('file_suffix', options.file_suffix))
    config.appendChild(add_prop('file_prefix', urllib.quote(file_prefix)))
    config.appendChild(add_prop('username', options.username))
    return ftp

"""
<node name='csv_formatter' node_id='483' module='mpx.service.data.csv_formatter.factory'  
  config_builder=''  inherant='false' description='CSV formatter'>
    <config>
      <property name='__type__' value='point'/>
      <property name='timestamp_format' value='%Y-%m-%dT%H:%M:%S'/>
    </config>
</node>
"""
def make_formatter(options):
    global DOC
    formatter = new_node(
        'enernoc_formatter', 
        '483',
        options.base_module + '.enernoc_formatter.factory',
        'false',
        'Enernoc Formatter',
        ''
        )
    config = DOC.createElement('config')
    formatter.appendChild(config)
    config.appendChild(add_prop('__type__', 'point'))
    return formatter
  
"""
<node name='vav1_01' node_id='261' module='mpx.service.logger.periodic_log.factory'  
  config_builder='envenergy.wizard.log.LogWizardPlugin_ToLog'  inherant='false' description='Periodic log'>
    <config>
      <property name='__type__' value='point'/>
      <property name='debug' value='0'/>
      <property name='period' value='900'/>
      <property name='enabled' value='1'/>
      <property name='minimum_size' value='250'/>
      <property name='maximum_size' value='500'/>
    </config>
  <node name='columns' node_id='460' module='mpx.lib.node.factory'  
    config_builder='envenergy.wizard.log.LogWizardPlugin_ToColumns'  
    inherant='true' description='Log Columns'>
"""

# creates new log, column w\timestamp and exporter placeholder

def make_log(logName, minSize, maxSize, period, options, trigger=None):
    global DOC
    log = new_node(
        urllib.quote(logName), 
        '261', 
        'mpx.service.logger.periodic_log.factory', 
        'false', 
        'Periodic Log', 
        'envenergy.wizard.log.LogWizardPlugin_ToLog'
        )
    config = DOC.createElement('config')
    log.appendChild(config)
    config.appendChild(add_prop('__type__', 'point'))
    config.appendChild(add_prop('debug', '0'))
    config.appendChild(add_prop('period', str(period)))
    config.appendChild(add_prop('enabled', '1'))
    config.appendChild(add_prop('minimum_size', str(minSize)))
    config.appendChild(add_prop('maximum_size', str(maxSize)))
    if trigger:
        config.appendChild(add_prop('trigger', trigger))
    
    columns = new_node(
        'columns', 
        '460', 
        'mpx.service.logger.column.Columns', 
        'true', 
        'Log Columns', 
        'envenergy.wizard.log.LogWizardPlugin_ToColumns'
        )
    log.appendChild(columns)
    exporter = make_exporter()
    log.appendChild(exporter)
    pe = make_periodic_exporter('periodic_exporter', '0')
    exporter.appendChild(pe)
    pe.appendChild(make_formatter(options))
    pe.appendChild(make_ftp_transporter(logName, options.ftp_details))
    columns.appendChild(
        make_column('timestamp', '', 'self.scheduled_time', '()', 'None', '0')
        ) 
    return (log, columns) 

"""
<node name='periodic_column_2' node_id='264' module='opt.columns.ChannelAttrsColumn'  
  config_builder='envenergy.wizard.log.LogWizardPlugin_ToColumn'  inherant='false' 
  description='Periodic column'>
    <config>
      <property name='__type__' value='point'/>
      <property name='use_subscription_manager' value='1'/>
      <property name='commodity' value='Steam'/>
      <property name='sort_order' value='none'/>
      <property name='uom' value='Degrees Fahrenheit'/>
      <property name='args' value='()'/>
      <property name='position' value='2'/>
      <property name='data_stream_name' value='interfaces.virtuals.value2'/>
      <property name='function' value='mpx.lib.node.as_node(&quot;/interfaces/virtuals/value2&quot;).get'/>
      <property name='debug' value='0'/>
      <property name='measurement_type' value='Actual'/>
      <property name='context' value='None'/>
      <property name='measure' value='Temperature'/>
      <property name='conversion' value='magnitude'/>
    </config>
  </node>
"""

# if conversion == "" then
# 1) don't add conversion config property
# 2) node_id == 462 instead of 264
# 3) config_builder = "" instead of 'envenergy.wizard.log.LogWizardPlugin_ToColumn'
# 4) sort_order == 'ascending' instead of 'none'

def make_column(name, conversion, node_path, args, exec_context, col_pos, options=None):
    global DOC
    if not conversion:
        node_id = '462'
        config_builder = ''
    else:
        node_id = '264'
        config_builder = 'envenergy.wizard.log.LogWizardPlugin_ToColumn'
    if options:
        factory = options.base_module + '.columns.ChannelAttrsColumn'
    else:
        factory = 'mpx.service.logger.periodic_column.factory'
    name = name.strip()
    col = new_node(urllib.quote(name), node_id, factory,
        'false', 'Periodic column', config_builder)
    config = DOC.createElement('config')
    col.appendChild(config)
    config.appendChild(add_prop('__type__', 'point'))
    config.appendChild(add_prop('debug', '0'))
    if not conversion: 
        config.appendChild(add_prop('sort_order', 'ascending'))
    else:
        config.appendChild(add_prop('sort_order', 'none'))
        config.appendChild(add_prop('conversion', conversion))
    config.appendChild(add_prop('position', str(col_pos)))
    config.appendChild(add_prop('context', exec_context))
    config.appendChild(add_prop('args', args))
    if name != 'timestamp':
        node_path = 'mpx.lib.node.as_node("%s").get' % node_path
    config.appendChild(add_prop('function', node_path))
    config.appendChild(add_prop('use_subscription_manager', '0'))
    if options:
        config.appendChild(
            add_prop('data_stream_name', options.data_stream_name)
            )
        config.appendChild(add_prop('measure', options.measure))
        config.appendChild(add_prop('commodity', options.commodity))
        config.appendChild(
            add_prop('measurement_type', options.measurement_type)
            )
        config.appendChild(add_prop('uom', options.uom))
    return col
    
def add_prop(name, value):
    global DOC
    prop = DOC.createElement('property')
    prop.setAttribute('name', name)
    if value != None:
        prop.setAttribute('value', value)
    return prop

def new_node(name, node_id, module, inherant, description, config_builder):
    global DOC
    node = DOC.createElement('node')
    node.setAttribute('name', name)
    node.setAttribute('node_id', node_id)
    node.setAttribute('module', module)
    node.setAttribute('config_builder', config_builder)
    node.setAttribute('inherant', inherant)
    node.setAttribute('description', description)
    return node

def get_config_prop_value(node, propName):
    ret = ""
    for config in node.childNodes:
        if config.nodeType == Node.ELEMENT_NODE:
            break
    for props in get_all_element_nodes(config):
        if props.getAttribute('name') == propName:
            ret = props.getAttribute('value')
            return ret
    return ret
	
def get_node(node, name, inherantNode):
    for child in node.childNodes:
        if child.nodeType == Node.ELEMENT_NODE and \
            child.getAttribute('name') == name:
            return child	
    if inherantNode:
        print 'Error finding "%s"\n' % name
        sys.exit()
    else:
        return None
        
def get_node_r(root, node_path):
    for n in node_path.split('/'):
        if n == '':
            continue
        node = get_node(root, n, True)
        root = node
    return node
	
def get_all_element_nodes(node):
    nodes = []
    for child in node.childNodes:
        if child.nodeType == Node.ELEMENT_NODE:
            nodes.append(child)
    return nodes

def _open_file(path):
    try:
        fd = open(path, 'r')
    except:
        print 'Unable to open %s' % path
        raise
    return fd

def parse_csv(path):
    try:
        fd = _open_file(path)
    except:
        sys.exit()
    # cvs file format:
    logs = {}
    # logname, nodepath, data_stream_name, measure, commodity, measurement_type, uom
    for line in fd:
        if not line: 
            continue
        line = line.strip()
        try:
            l, np, ds, m, c, mt, uom = line.split(',')
        except:
            print 'Unable to parse line %s\n' % line
            continue
        for x in [l, np, ds, m, c, mt, uom]:
            x = x.strip()
        col_list = logs.get(l)
        if col_list is None:
            col_list = []
            logs[l] = col_list
        col_list.append(Column(ds, m, c, mt, np, uom))       
    fd.close()
    return logs
        
def load_ftp_spec(path):
    try:
        fd = _open_file(path)
    except:
        return FtpSpec()
    lines = fd.readlines()
    ftp_opt = {}
    for l in lines:
        if not l or l.startswith('#'):
            continue
        l = l.strip
        try:
            k,v = l.strip('=')
        except:
            print 'Unable to parse FTP option: %s\n' % l
            continue
        ftp_opt[k] = v
    return FtpSpec(ftp_opt)
    
def add_logs(logs, options, logger):
    global LOG_MIN_SZ
    global LOG_MAX_SZ
    conv = 'magnitude'
    args_ = '()'
    exc = 'None'
    for logname, col_list in logs.items():
        log, col_holder = make_log(
            logname, 
            LOG_MIN_SZ, 
            LOG_MAX_SZ, 
            options.frequency, 
            options
            )
        logger.appendChild(log)
        i = 1      
        for col_obj in col_list:
            # the make_column api is a bit strange given the use
            # of col_obj here - it's copied and pasted from existing code.
            # @todo: rework this.
            col_obj.base_module = options.base_module
            col_node = make_column(
                col_obj.data_stream_name,
                conv,
                col_obj.nodepath,
                args_,
                exc,
                str(i),
                col_obj
                )
            col_holder.appendChild(col_node)
            i += 1

parser = OptionParser(usage="""\
@todo
""")

parser.add_option('-i', '--infile', action='store', type='string', 
    dest='xml_in', metavar='XML_IN', default=XML_IN, 
    help='The file name of the broadway.xml to build from.'
    )
parser.add_option('-o', '--outfile', action='store', type='string', 
    dest='xml_out', metavar='XML_OUT', default=XML_OUT,
    help='The file name to ouput to.'
    )
parser.add_option('-u', '--use_sm', action='store', type='int',
    dest='use_sm', metavar='USE_SM', default=USE_SM, 
    help='Use the subscription manager (0 or 1)'
    )
parser.add_option('-m', '--module', action='store', type='string',
    dest='base_module', metavar='BASE_MODULE', default=BASE_MODULE,
    help='If you need help, you shouldn\'t change it.'
    )
parser.add_option('-c', '--csvfile', action='store', type='string',
    dest='csv_in', metavar='CSV_IN', default=CSV_IN,
    help='The name of the csv configuration file.'
    )
parser.add_option('-s', '--spec', action='store', type='string',
    dest='ftp_spec', metavar='FTP_SPEC', default=FTP_SPEC,
    help='The name of the ftp specification file.'
    )
parser.add_option('-f', '--frequency', action='store', type='int',
    dest='frequency', metavar='FREQUENCY', default=FREQUENCY,
    help='Log sampling frequency'
    )

(options, args) = parser.parse_args()
if len(args) > 7:
    raise Exception("Wrong number of arguments.  Use -h for more information.")

print 'Loading base broadway.xml ...\n'
DOC = minidom.parse(options.xml_in)
print '...done\n'
root = get_node(DOC.childNodes[0], '/', True)
services = get_node(root, 'services', True)
logger = get_node(services, 'logger', True)
print options.csv_in
open(options.csv_in)
logs = parse_csv(options.csv_in)
options.ftp_details = load_ftp_spec(options.ftp_spec)
# need to load ftp specs, first
add_logs(logs, options, logger)
try:
    out = open(options.xml_out, 'w')
    out.write(DOC.toxml())
except:
    print 'Unable to write to %s' % options.xml_out
    raise
    sys.exit()
out.close()
print 'File %s created\n' % options.xml_out



