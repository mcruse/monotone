"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
from xml import sax 
import types
import string
import re
from urllib import quote_plus, unquote_plus

def quote(string,safe=''):
    #if safe is None:
        #safe = "()#"
    return quote_plus(string, safe)

def get_line(dict, y): #answer a dict of items from a given line
    keys = filter(lambda xy: xy[1] == y, dict.keys())
    if keys:
        answer = {}
        for k in keys:
            answer[k]=dict[k]
        return answer
    return None

def split_file_into_pages_and_fields(lines):
    #read the file and break it up into individual pages, each keyed by its url
    #with a value of a dictionary keyed by (x,y) location and text value
    #split lines into a list
    at = {}
    atk=None
    for l in lines:
        if l.startswith('/services'):
            atk, key_path, timeout = l[l.find('CPC')+4:].split(',')
            #atk = unquote_plus(atk)
            at[atk]={} #atk is full path to node
            at[atk]['__key_path__']=key_path
            at[atk]['__timeout__']=timeout
        if l.startswith('('):
            #line contains points: 
            #(138,280)=B-COND. OAT, (266,280)=61.1, (338,280)=OFF
            #break line up into individual text fields
            pts=l[1:].split(', (')
            for p in pts:
                k,v = p.split(')=')
                x,y = k.split(',')
                at[atk][(int(x),int(y))]=v
    return at

def convert_pages_into_cpc_config_data(at):
    pages = {}
    keys = at.keys()
    keys.sort() #this will make sure child pages sort after their parent
    #examine each page, determine type and parent.
    for k in keys:
        page = at[k]
        #prepare node config dictionary
        ks = k.split('/')
        name = unquote_plus(ks[-1]) #page name, unencoded
        key_path = page['__key_path__']
        timeout = page['__timeout__']
        config = {'name':name, 'key_path':key_path, 'timeout':timeout}
        page_url = k.replace('%20','+') #change to encode_plus form
        #determine page types by looking for particular fields that can be used
        #to tell them apart
        points = None
        line = get_line(page, 72)
        if line:
            if 'Ctrl Val' in line.values(): #Sensor Controls
                pages[k]=(config, process_sensor_controls_list_page(page, page_url))
                continue
        if page.has_key((10,56)): #Suction group or Condenser
            if page[(10,56)] == 'Enhanced Suction Group Name:':
                pages[k]=(config, process_suction_group_page(page, page_url))
                continue
            if page[(10,56)] == 'CONDENSER GROUP NAME:':
                pages[k]=(config, process_condenser_group_page(page, page_url))
                continue        
        if page.has_key((90,72)): #Condensers
            if page[(90,72)].startswith('Condensers:'):
                pages[k]=(config, process_condenser_detail_page(page, page_url))
                continue
        if page.has_key((66,72)): #Circuits
            if page[(66,72)] == 'Name':
                pages[k]=(config, process_circuits_page(page, page_url))
                continue
        if page.has_key((30,72)): #output status
            #process Output Status page
            pages[k]=(config, process_outputs_status_page(page, page_url))
            continue
        if page.has_key((26,72)): #input status
            #process Input Status page
            pages[k]=(config, process_inputs_status_page(page, page_url))
            continue
        if page.has_key((202,40)): #Analog Combiners
            if page[(202,40)] == 'Summary For Analog Combiners':
                #process Summary For Analog Combiners
                #don't do anything for these.  We use the detail page
                pages[k]=(config, {})
                continue
        if page.has_key((10,72)): #Analog Combiner
            if page[(10,72)] == 'Analog Combiner Name:':
                pages[k]=(config, process_analog_combiner(page, page_url))
                continue
        if page.has_key((210,40)): #Multiflex
            if page[(210,40)] == 'Summary For MultiFlex ESR':
                pages[k]=(config, process_multiflex_page(page, page_url))
                #process Multflex page
                continue
        #still need to do globals
        #we did not recognize the page
        print 'did not recognize page: ', k
        pass
    return pages
def process_circuits_page(page, page_url):
    def point_config(sub_name, x):
        #put together config data for the CPC point
        #currently using x,y coords.  Could use text matching
        config = {'name':name + ' - ' + sub_name, 'x':str(x), 'y':str(y)}
        #put together config data for Alias point
        #parent_name is "application" and will be an alias group node name
        #name is "association" and will be individual alias node name
        alias = {'application':name, 'name':sub_name, 
                 'link':page_url + '/' + quote(config['name'])}
        points[config['name']] = {'config':config, 'alias':alias}
    #(66,88)=A01 10DRS FF, (194,88)=Refrigeration, (306,88)=-13.8, (362,88)=-12.0, (418,88)=.., (466,88)=ON, (514,88)=OFF
    points = {}
    for y in range(88,377,16): #go though each line on page
        if page.has_key((66,y)):
            name = page[(66,y)] #circuit name
            point_config('State', 194)
            point_config('Temp' , 306)
            point_config('Setpt', 362)
            point_config('Alarm', 418)
            point_config('Refr' , 466)
            point_config('Defr' , 514)
    return points
def process_outputs_status_page(page, page_url):
    #(26,56)=Type, (82,56)=Brd, (154,56)=Point, (234,56)=Type, 
    #(290,56)=Application, (426,56)=Association, (562,56)=Value
    #(30,72)=8RO, (90,72)=1, (170,72)=1, (246,72)=D, 
    #(286,72)=A-27 (R404A), (430,72)=STAGE OUT1, (578,72)=ON
    points = {}
    keys = page.keys()
    for y in range(72,409,16): #go though each line on page
        #application name can be anywhere in x range of 278 to 290
        line_keys = filter(lambda k:k[1]==y, keys)
        line_keys.sort()
        app_keys = filter(lambda k:k[0] > 250 and k[0] < 300, line_keys)
        if len(app_keys) > 0: #found an "application" name field
            x = app_keys[0][0]
            application  = page[(x,y)]
            assoc_keys = filter(lambda k:k[0] > x, line_keys)
            #first assoc_keys element's x value will give assoc name
            association = page[(assoc_keys[0][0],y)]
            #use name method to ID fields since they move around
            config = {'name':application + ' - ' + association,
                      'match_text':application + ',' + association}
            alias = {'application':application, 'name':association,
                     'link':page_url + '/' + quote(config['name'])}
            points[config['name']] = {'config':config, 'alias':alias}
    return points
def process_inputs_status_page(page, page_url):
    #(26,56)=Type, (82,56)=Brd, (154,56)=Point, (234,56)=Type, 
    #(290,56)=Application, (426,56)=Association, (562,56)=Value
    #(30,72)=8RO, (90,72)=1, (170,72)=1, (246,72)=D, 
    #(286,72)=A-27 (R404A), (430,72)=STAGE OUT1, (578,72)=ON
    points = {}
    keys = page.keys()
    for y in range(72,409,16): #go though each line on page
        #application name can be anywhere in x range of 278 to 290
        line_keys = filter(lambda k:k[1]==y, keys)
        line_keys.sort()
        app_keys = filter(lambda k:k[0] > 250 and k[0] < 300, line_keys)
        if len(app_keys) > 0: #found an "application" name field
            x = app_keys[0][0]
            application  = page[(x,y)]
            assoc_keys = filter(lambda k:k[0] > x, line_keys)
            #first assoc_keys element's x value will give assoc name
            association = page[(assoc_keys[0][0],y)]
            #check for presence of value field
            value_keys = filter(lambda k:k[0] > 500, line_keys)
            if value_keys: #there is a value field
                #use name method to ID fields since they move around
                config = {'name':application + ' - ' + association,
                          'match_text':application + ',' + association}
                alias = {'application':application, 'name':association,
                         'link':page_url + '/' + quote(config['name'])}
                points[config['name']] = {'config':config, 'alias':alias}
    return points

def process_suction_group_page(page, page_url):
    def point_config(name, x, y):
        #put together config data for the CPC point
        #currently using x,y coords.  Could use text matching
        config = {'name':name, 'x':str(x), 'y':str(y)}
        #put together config data for Alias point
        #parent_name is "application" and will be an alias group node name
        #name is "association" and will be individual alias node name
        alias = {'application':application, 'name':name, 
                 'link':page_url + '/' + quote(config['name'])}
        points[config['name']] = {'config':config, 'alias':alias}
    #get page info
    #(10,72)=B2+18 (R22)
    application = page[(10,72)] #suction group name is "application"
    points = {}
    keys = page.keys()
    #process single points
    #(266,56)=Suct:, (354,56)=38.8, (474,56)=[      ], (490,56)=42.0
    point_config('Suct', 354, 56)
    point_config('Suct Setpnt', 490, 56)
    #(266,88)=Dsch:, (354,88)=136.9
    point_config('Dsch', 354, 88)
    #(450,120)=Control Status
    #(458,136)=Observing-Float
    point_config('Control Status', 458, 136)
    #(458,312)=Sat Suct Temp :, (586,312)=15.9
    point_config('Sat Suct Temp', 586, 312)
    #(458,328)=Suction Temp  :, (586,328)=49.4
    point_config('Suction Temp', 586, 328)
    #(458,360)=Rack Failure  :, (586,360)=OK
    point_config('Rack Failure', 586, 360)
    #(458,376)=Capacity      :, (586,376)=226.0
    point_config('Capacity', 586, 376)
    #(458,392)=Capacity %    :, (586,392)=49.3
    point_config('Capacity %', 586, 392)
    #process array of stages info
    #(10,136)=Stages,           (106,136)=Cap, (154,136)=State, (218,136)=Cycles, 
    # (282,136)=Status
    #(10,152)=#1 :, (50,152)=Comp, (98,152)=90.0, (154,152)=ON, (218,152)=29,
    # (282,152)=Ready
    for y in range(152,297,16): #go though each line on page
        if page.has_key((10,y)):
            name  = page[(10,y)] #stage name, something like "#1 :"
            name = 'Stage ' + name[:-1].strip() #clean up and format stage name
            point_config(name + ' Mode', 50, y)
            point_config(name + ' Cap', 98, y)
            point_config(name + ' State', 154, y)
            point_config(name + ' Cycles', 218, y)
            point_config(name + ' Status', 282, y)
    return points

def process_condenser_group_page(page, page_url):
    def point_config(name, x, y):
        #put together config data for the CPC point
        #currently using x,y coords.  Could use text matching
        config = {'name':name, 'x':str(x), 'y':str(y)}
        #put together config data for Alias point
        #parent_name is "application" and will be an alias group node name
        #name is "association" and will be individual alias node name
        alias = {'application':application, 'name':name, 
                 'link':page_url + '/' + quote(config['name'])}
        points[config['name']] = {'config':config, 'alias':alias}

    #get page info
    #(10,72)=A-CONDENSER
    application = page[(10,72)] #condenser name is "application"
    points = {}
    keys = page.keys()
    #process single points
    #(266,56)=Ctrl:, (354,56)=75.3, (474,56)=[      ], (490,56)=72.8
    point_config('Ctrl', 354, 56)
    point_config('Ctrl Setpnt', 490, 56)
    #(266,88)=FstR:, (354,88)=161.3, (474,88)=[      ], (490,88)=300.0
    point_config('FstR', 354, 88)
    point_config('FstR Setpnt', 490, 88)
    #(434,136)=Outside Air:, (538,136)=62.8
    point_config('Outside Air', 538, 136)
    #(434,184)=State :, (498,184)=Fan(s) On
    point_config('State', 498, 184)
    #(434,200)=Mode  :, (498,200)=Differential
    point_config('Mode', 498, 200)
    #(434,216)=PID % :, (498,216)=100.0
    point_config('PID %', 498, 216)
    #(434,232)=Split :, (498,232)=INACTV
    point_config('Split', 498, 232)
    #(434,248)=DISCH :, (498,248)=161.5
    point_config('DISCH', 498, 248)
    #(434,328)=Refrig:, (498,328)=R404A
    point_config('Refrig', 498, 328)
    #process array of stages info
    #(10,136)=FANS,      (130,136)=STATUS, (194,136)=RUNTIME, (274,136)=CYCLES, 
    #(10,184)=Fan #1       :,(130,184)=ON, (194,184)=32:59, (274,184)=6, 
    for y in range(184,350,16): #go though each line on page
        if page.has_key((10,y)):
            name  = page[(10,y)] #stage name, something like "Fan #1      :"
            name = name[:-1].strip() #clean up and format stage name
            point_config(name + ' Status', 130, y)
            point_config(name + ' Runtime', 194, y)
            point_config(name + ' Cycles', 274, y)
    return points

def process_condenser_detail_page(page, page_url):
    # (42,120)=SPLIT VALVE    :, (178,120)=INACTV,
    # (42,136)=SPLIT FAN      :, (178,136)=INACTV,
    # get the condenser name from the url
    #/services/network/CPC/RKAB/B-CONDENSER/Details
    #/services/network/CPC/RKAB/B-CONDENSER/Details/other_outs,F1,10
    #it's ugly, but pick out 'B-CONDENSER' portion of page_url
    application = page_url[page_url.find('CPC')+4:].split('/')[1]
    points = {}
    keys = page.keys()
    for y in range(120,450,16): #go though each line on page
        if page.has_key((42,y)):
            association  = page[(42,y)][:-1].strip() #point name
            #use name method to ID fields since they move around
            config = {'name':association, 'x':'178', 'y':str(y)}
            alias = {'application':application, 'name':association,
                     'link':page_url + '/' + quote(config['name'])}
            points[config['name']] = {'config':config, 'alias':alias}
    return points

def process_analog_combiner(page, page_url):
    # (10,88)=A-COND SUBCLNG
    # (18,168)=INPUTS, (330,168)=SPECIAL INPUTS
    # (18,200)=Analog Input #1  :, (170,200)=75.1
    # (18,216)=Analog Input #2  :, (170,216)=67.4
    # (330,296)=OUTPUTS
    # (338,328)=OUTPUT           :, (490,328)=7.7
    application = page[(10,88)]
    points = {}
    keys = page.keys()
    # do inputs
    for y in range(200,450,16): #go though each line on page
        if page.has_key((18,y)):
            association  = page[(18,y)][:-1].strip() #point name
            config = {'name':association, 'x':'170', 'y':str(y)}
            alias = {'application':application, 'name':association,
                     'link':page_url + '/' + quote(config['name'])}
            points[config['name']] = {'config':config, 'alias':alias}
    # do outputs
    for y in range(328,450,16): #go though each line on page
        if page.has_key((338,y)):
            association  = page[(338,y)][:-1].strip() #point name
            config = {'name':association, 'x':'490', 'y':str(y)}
            alias = {'application':application, 'name':association,
                     'link':page_url + '/' + quote(config['name'])}
            points[config['name']] = {'config':config, 'alias':alias}
    return points

def process_sensor_controls_list_page(page, page_url):
    # (138,72)=Name, (266,72)=Ctrl Val, (338,72)=Command
    # (138,88)=1-O.A. TEMP, (266,88)=62.7, (338,88)=OFF
    # (138,104)=A-COND. OAT, (266,104)=62.7, (338,104)=OFF
    # (138,376)=IRLDS01 CMP RM, (266,376)=0, (338,376)=OFF
    def point_config(sub_name, x):
        #put together config data for the CPC point
        #currently using x,y coords.  Could use text matching
        config = {'name':name + ' - ' + sub_name, 'x':str(x), 'y':str(y)}
        #put together config data for Alias point
        #parent_name is "application" and will be an alias group node name
        #name is "association" and will be individual alias node name
        alias = {'application':name, 'name':sub_name, 
                 'link':page_url + '/' + quote(config['name'])}
        points[config['name']] = {'config':config, 'alias':alias}
    points = {}
    for y in range(88,377,16): #go though each line on page
        line = get_line(page, y)
        if line:
            cols = line.keys()
            cols.sort()
            name  = page[cols[0]] #sensor name
            point_config('Ctrl Val', cols[1][0]) #pass x of 2nd col
            point_config('Command' , cols[2][0]) #pass x of 3rd col
    return points

def process_multiflex_page(page, page_url):
    def point_config(name, x, y):
        #put together config data for the CPC point
        #currently using x,y coords.  Could use text matching
        config = {'name':name, 'x':str(x), 'y':str(y)}
        #put together config data for Alias point
        #parent_name is "application" and will be an alias group node name
        #name is "association" and will be individual alias node name
        alias = {'application':application, 'name':name, 
                 'link':page_url + '/' + quote(config['name'])}
        points[config['name']] = {'config':config, 'alias':alias}
    application = 'multiflex' #"application"
    points = {}
    keys = page.keys()
    #process array of stages info
    #(26,72)=MultiFlex ESR, (154,72)=Valve1, (210,72)=Valve2, (266,72)=Valve3,
    # (322,72)=Valve4, (378,72)=Valve5, (434,72)=Valve6, (490,72)=Valve7,
    # (546,72)=Valve8
    #(26,88)=1-ESR8#1, (154,88)=5.6, (210,88)=12.1, (266,88)=24.3,
    #(322,88)=24.0, (378,88)=12.0, (434,88)=20.5, (490,88)=0.09,
    #(546,88)=100.0
    for y in range(88,297,16): #go though each line on page
        if page.has_key((26,y)):
            name  = page[(26,y)] #stage name, something like "1-ESR8#1"
            point_config(name + ' - Valve1', 154, y)
            point_config(name + ' - Valve2', 210, y)
            point_config(name + ' - Valve3', 266, y)
            point_config(name + ' - Valve4', 322, y)
            point_config(name + ' - Valve5', 378, y)
            point_config(name + ' - Valve6', 434, y)
            point_config(name + ' - Valve7', 490, y)
            point_config(name + ' - Valve8', 546, y)
    return points

def generate_node_urls(dh):
    urls = {}
    for k in dh.objects_dict.keys():
        name = k.split(':')[1] #clean off the beginning of the object name
        name = name.replace('.','/') #convert the .'s into /'s (like a url)
        object_id = int(dh.objects_dict[k]['objectid']) #id portion of bacnet id
        object_type = class_obj[int(dh.objects_dict[k]['classid'])] #look up object type by class id
        #object_type = dh.object_type_map[object_id] #obj type portion of bacnet id
        urls[name] = '/%d/%d' % (object_type, object_id) #this dict contains all we need to construct xml for alias
    return urls

def convert_node_urls_to_tree(urls):
    root = {}
    for url in urls.keys():
        current_dict = root
        for u in url.split('/'):
            if not current_dict.has_key(u):
                current_dict[u]={}
            current_dict = current_dict[u]
        current_dict['__link__'] = urls[url]
    return root

def convert_tree_to_xml(file, tree, name, bacnet_path, depth=0):
    if tree.has_key('__link__'):
        if len(tree.keys()) == 1: #is regular alias point
            s = alias_point % (name, bacnet_path + tree['__link__'])
            s = s.split('\n')
            for l in s:
                file.write('  ' * depth)
                file.write(l + '\n')
            return
        #since an alias group with a link
        file.write('  ' * depth)
        file.write(alias_group_header % (name,))
        s = alias_group_link % (bacnet_path + tree['__link__'],)
        s = s.split('\n')
        for l in s:
            file.write('  ' * depth)
            file.write(l + '\n')
        for k in tree.keys():
            if k == '__link__': continue
            convert_tree_to_xml(file, tree[k], k, bacnet_path, depth+1)
            file.write('  ' * (depth + 1))
            file.write(close_node)
        return
    if name is None:
        file.write(xml_header)
    else:
        file.write('  ' * depth)
        file.write(alias_group_header % (name,))
    for k in tree.keys():
        convert_tree_to_xml(file, tree[k], k, bacnet_path, depth+1)
        file.write('  ' * (depth + 1))
        file.write(close_node)
    return
def write_xml(file, string, depth=0):
    strings = string.split('\n')
    for s in strings:
        file.write('  ' * depth)
        file.write(s)
        file.write('\r\n')

def convert_config_to_cpc_xml(file, config, device_config):
    #create the xml snippet that is imported under the CPC node for a device
    device_config = eval(device_config)
    write_xml(file, cpc_device % (device_config['name'],
                             device_config['password'],
                             device_config['user'],
                             device_config['device_name']))
    keys = config.keys() #url of cpc pages
    keys.sort()
    #typical keys:
    # /services/network/CPC/RKAB/Sensor%20Controls
    # /services/network/CPC/RKAB/Sensor%20Controls/pgdn
    #use number of elements in url to determine parentage (or childage...)
    base_depth = len(keys[0].split('/'))-1 #depth of device node url
    old_depth = 0
    for k in keys:
        page = config[k]
        page_config = page[0]
        depth = len(k.split('/')) - base_depth
        if (depth <= old_depth):
            #close out previous node(s)
            for d in range(old_depth + 1 - depth):
                write_xml(file, close_node, old_depth - d)
        old_depth = depth
        write_xml(file, 
                  cpc_page % (page_config['name'],
                              page_config['timeout'],
                              page_config['key_path']),
                  depth)
        points = page[1]
        point_names = points.keys()
        point_names.sort()
        for pn in point_names:
            point_config = points[pn]['config']
            write_xml(file,
                      cpc_point % (pn,
                                   point_config.get('match_text',''),
                                   point_config.get('y',0),
                                   point_config.get('x',0)),
                      depth + 1)
    for d in range(old_depth):
        write_xml(file, close_node, old_depth-d)
    write_xml(file, close_node)
def convert_config_to_alias_xml(file, config):
    #go through each page and collect "applications" and "associations"
    #applications become alias groups and associations are simple aliases
    applications = {}
    for page in config.values():
        for point in page[1].values():
            alias_config = point['alias']
            a = alias_config['application']
            n = alias_config['name']
            l = alias_config['link']
            if not applications.has_key(a):
                print 'create application: ',a
                applications[a] = {}
            app = applications[a]
            if app.has_key(n):
                print ' alias duplication: ', a, n, l, app[n]
                if len(app[n]) < len(l): #stay with shorter link
                    l = app[n]
            app[n] = l
    #create an xml snippet
    cpc_root = '/services/network/CPC/'
    write_xml(file, alias_group_header % ('cpc',))
    depth = 0
    keys = applications.keys()
    keys.sort()
    print 'applications keys: ', keys
    for k in keys: #application names are keys
        app = applications[k]
        write_xml(file, alias_group_header % (k,),1)
        point_names = app.keys()
        point_names.sort()
        for point in point_names:
            write_xml(file, alias_point % (point, cpc_root + app[point],), 2)
            write_xml(file, close_node, 2)
        write_xml(file, close_node, 1)
    write_xml(file, close_node, 0)

def convert_file(all_texts_file):
    f=open(all_texts_file)
    lines = f.read()
    f.close()
    lines = lines.split('\n')
    o = split_file_into_pages_and_fields(lines) #, ol)
    c = convert_pages_into_cpc_config_data(o)

    #take the text filename and insert 'alias.' for the output file name
    path = f.name.split('/') #break apart the path name
    file_name = path.pop().split('.')[0] #basic name
    file_name += '.alias.xml' #make it 'whatever.alias.xml'
    path.append(file_name) #add changed name to any path
    result_file_name = '/'.join(path) #presto chango
    x = open(result_file_name,'w')
    x.write(xml_header)

    convert_config_to_alias_xml(x, c)

    x.write('</mpxconfig>\r\n')
    x.close()
 
    #take the text filename and insert 'cpc.' for the output file name
    path = f.name.split('/') #break apart the path name
    file_name = path.pop().split('.')[0] #basic name
    file_name += '.cpc.xml' #make it 'whatever.alias.xml'
    path.append(file_name) #add changed name to any path
    result_file_name = '/'.join(path) #presto chango
    x = open(result_file_name,'w')
    x.write(xml_header)

    convert_config_to_cpc_xml(x, c, lines[1]) #lines[1]=repr of device config

    x.write('</mpxconfig>\r\n')
    x.close()
 
xml_header = "<mpxconfig node_version='1.5.0.dev.11'>\r\n"

alias_group_header = '''<node name="%s" node_id='452' module='mpx.service.aliases.factory'  config_builder=''  inherant='false' description='Alias group'>'''

alias_group_link = '''<config>
  <property name='__type__' value='point'/>
  <property name='node_url' value="%s"/>
</config>'''
alias_point = '''<node name="%s" node_id='257' module='mpx.service.alias.factory'  config_builder=''  inherant='false' description='Alias (another name for an existing node)'>
  <config>
    <property name='__type__' value='point'/>
    <property name='node_url' value="%s"/>
  </config>'''
cpc_point = '''<node name="%s" node_id='7e686a75-99f5-4f96-bf99-95d29e9c8382' module='mpx.ion.cpc.cpc.Point'  config_builder=''  inherant='false' description='CPC point'>
  <config>
    <property name='__type__' value='point'/>
    <property name='match_text' value="%s"/>
    <property name='y' value='%s'/>
    <property name='x' value='%s'/>
  </config>
</node>'''
cpc_page = '''<node name="%s" node_id='76e3bf4d-8f05-464e-9eb5-e0bcf309b619' module='mpx.ion.cpc.cpc.Screen'  config_builder=''  inherant='false' description='CPC screen'>
  <config>
    <property name='__type__' value='point'/>
    <property name='timeout' value='%s'/>
    <property name='key_path' value="%s"/>
  </config>'''
cpc_device = '''<node name="%s" node_id='0930fb0e-f40d-437b-8e9a-b9f9e696abae' module='mpx.ion.cpc.cpc.Device'  config_builder=''  inherant='false' description='CPC device'>
  <config>
    <property name='__type__' value='point'/>
    <property name='password' value='%s'/>
    <property name='user' value='%s'/>
    <property name='device_name' value="%s"/>
  </config>'''

close_node = "</node>"

if __name__ == '__main__':
    import sys
    if '-h' in sys.argv or len(sys.argv) < 2:
        print
        print 'Generates xml snippets for Aliases and CPC protocol nodes from'
        print 'from a text file containing the capture of the "all_texts"'
        print 'command. The command is run in the nodebrowser by adding the'
        print 'following text after the CPC Device node url:'
        print
        print '?action=invoke&method=all_texts'
        print
        print 'Save the response to a text file which is then the first'
        print 'parameter to this command.  Two files with xml snippets will be'
        print 'created are then imported, in the config tool, under /aliases/'
        print 'and under /services/network/cpc/'
        #print 'Server Device name must be set to a number.'
        print
        print 'Syntax:'
        print 'cpc_broadway_generator all_texts_filename'
        print
        print 'the resulting xml files are named after the all_texts file with'
        print 'the addition of _aliases.xml and _protocol.xml respectively'
        print
    else:
        cpc_path = '/services/network/CPC'
        all_texts_file = sys.argv[1]
        convert_file( all_texts_file )

"""
from nae_xml2alias import *

f=open('NAE2export.xml')
ol=open('object_list.txt')
o = parse_xml(f, ol)
f.close()
ol.close()
n = generate_node_urls(o)
t = convert_node_urls_to_tree(n)
x = open('result.xml','w')
convert_tree_to_xml(x, t, None, '/services/network/BACnet/internetwork/Devices/123')
x.write('</mpxconfig>\r\n')
x.close()

"""
