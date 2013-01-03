"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
# Provides a simple Node Browser for Broadway's http server.
#
# @fixme All pages should have a simple navigation tool at the top and bottom.
#        Basically a link for each level in the path:
#        <u>/</u> <u>ion</u> / <u>port2</u> / <u>modbus</u> / <u>dg50</u>
#        / start

import types
import sys
import string
import posixpath
import mpx.lib
import cgi
from mpx.lib import urllib
from mpx.lib import thread
from mpx.lib.rna import NodeFacade
from mpx.lib.node import as_node_url, as_internal_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import as_boolean
from mpx.lib.exceptions import EConfigurationInvalid
from mpx.service.garbage_collector import GARBAGE_COLLECTOR as GC
from mpx.service.garbage_collector import GC_NEVER
from mpx.service.garbage_collector import GC_ONDELETE
from mpx.service.garbage_collector import GC_ASNEEDED
from mpx.service.garbage_collector import GC_ONFAILURE
from mpx import properties
from mpx.lib import msglog

from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response

def nodecmp(a,b):
    facade = False
    #nodecmp over RNA is currently very expensive.  Avoid that.
    if isinstance(a, NodeFacade) or isinstance(b, NodeFacade):
        a_name = a.as_node_url().split('/')[-1]
        b_name = b.as_node_url().split('/')[-1]
        facade = True
    else:
        a_name = a.name
        b_name = b.name
    if a.hasattr('nodecmp') and not facade:
        return a.nodecmp(as_node_url(b))
    return cmp(a_name, b_name)

##
# Guess how to convert a value based on its content.
# @param value A string.
# @return Attempts to return the correct data-type (float, int or string).
# @fixme This is really scary.  The real fix would be to say that
#        all set methods are expected to except string representations
#        as well as native data types.  We should do that and delete
#        this function.
def _holistic_conversion(value):
    value = _unescapevalue(value)
    if value.count('.') == 1:
        try:
            return float(value)
        except:
            pass
    try:
        return int(value)
    except:
        pass
    return value



##
# Serves files from over web.
#
# @implements mpx.service.network.http.RequestHandlerInterface
#
class Browser(RequestHandler):
    def __init__(self, *args):
        self.security_manager = None
        self._secured = None
        self.__registered_pdos = ()
        self.__pdo_map = {}
        self.template = ""
        self.request_path = "/nodebrowser"
        self.page_template = "/templates/nodes.html"
        super(Browser, self).__init__(*args)
        return
    ##
    # Configures HTTP handler.
    #
    # @param config  Dictionary containing parameters and values from
    #                the configuration tool.
    # @key request_path  Regular expression for url requests that
    #                    should be forwarded to this handler.
    # @default /nodebrowser
    #
    # @see mpx.lib.service.RequestHandler#configure
    #
    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', '/nodebrowser', config)
        self.secured = as_internal_node("/services").secured
        RequestHandler.configure(self, config)

    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.SubServiceNode#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        get_attribute(self, 'secured', config, str)
        return config

    def start(self):
        if self.secured:
            try:
                sm = mpx.lib.node.as_node('/services/Security Manager')
            except KeyError:
                mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.WARN,
                           'Node Browser not running in secured mode because '
                           'no Security Manager was found.  Config parameter '
                           '"secured" being overriden to False.')
                mpx.lib.msglog.exception(prefix = 'Handled')
                self._secured = False
            else:
                self.security_manager = sm
                self._secured = True
        else:
            self._secured = False
        self.template = self.parent.read_resource(self.page_template)
        super(Browser, self).start()

    def stop(self):
        self._secured = None
        self.security_manager = None
        super(Browser, self).stop()

    def __provides_security(self):
        # Let request get username/password until error handling can
        #   be cleaned to handled security exceptions without squashing
        #   them like everything else that can possibly go wrong.
        return False
    provides_security = property(__provides_security)

    def _as_node(self, node_url):
        if self._secured is None:
            raise EConfigurationInvalid(
                'Secured flag is None; should be True or '
                'False.  Made indicate node failed to start.')
        elif self._secured:
            as_secured_node = self.security_manager.as_secured_node
            node = as_secured_node(node_url, dereference_aliases=True)
        else:
            node = mpx.lib.node.as_node(node_url)
        return node

    ##
    # Get list of regular expressions for the different
    # request paths that this handler wants to handle.
    #
    # @return List of paths.
    #
    #def listens_for(self):
        #path_list = [self.request_path]
        #return path_list

    def match(self, path):
        return path.startswith(self.request_path)
    def _get_exception_name(self,e):
        msg = '%s' % e.__class__.__name__
        return msg
    def _get_exception_msg(self,e):
        import traceback
        exc_type,exc_value,exc_tb = sys.exc_info()
        exc_lines = traceback.format_exception_only(exc_type,exc_value)
        del exc_type
        del exc_value
        tb_lines = traceback.format_tb(exc_tb)
        tb_lines = map(cgi.escape, tb_lines)
        del exc_tb
        exc_split = exc_lines[0].split(":",1)
        exc_name = exc_split.pop(0)
        if exc_split:
            exc_text = exc_split.pop(0)
        else:
            exc_text = ''
        error_msg = """\
        <span style="color:red"><b>%(name)s:</b>%(text)s</span>
        """ % {
            "name":exc_name,
            "text":exc_text
            }
        if not properties.get_boolean('TRACEBACKS'): 
            return error_msg
        
        return """%(error_msg)s<span style="color:black">
        <br>\n%(traceback)s</span>""" % {
            "error_msg":error_msg,
            "traceback":"<br/>".join(tb_lines)
            }

    def getvalue(self, node):
        if isinstance(node, str):
            node = self._as_node(node)
        if hasattr(node,'nb_get'):
            # if node handles gets from the nb differently than normal gets
            return node.nb_get()
        return node.get()
    def get_breadcrumbs(self, nodeurl):
        """
            Returns list of (name, node-URL) tuples providing the
            unencoded node names and full node URL for each node in
            the hierarchy.
        """
        segurl = '/'
        seglinks = []
        segments = nodeurl.split("/")
        for segment in segments[1:]:
            if segment:
                segurl = posixpath.join(segurl, segment)
                seglinks.append((urllib.unquote(segment), segurl))
        return [("nodes", "/")] + seglinks
    def get_navigation_block(self, nodeurl):
        nodeitems = self.get_breadcrumbs(nodeurl)
        #toplabel,topurl = nodeitems.pop()
        breadcrumbs = []
        for label,nodeurl in nodeitems:
            linkurl = "%s/%s" % (self.request_path, nodeurl[1:])
            breadcrumbs.append('<a href="%s">%s</a>' % (linkurl, label))
        #breadcrumbs.append(toplabel)
        block = ['<div class="breadcrumbs" id="node-navigation">']
        block.append("\n > \n".join(breadcrumbs))
        block.append('</div>')
        return "\n".join(block)

    ##
    # Called by http_server each time a request comes in whose url mathes one of
    # the paths this handler said it was interested in.
    #
    # @param request  <code>Request</code> object from the http_server.  To send
    #                  Create a Response object response = Response(request)
    #                  response.send(html)
    #                  <code>html</code> is the text response you want to send.
    # @fixme Handle exceptions gracefully and report them back to the client.
    # @fixme Don't convert the incoming values (as soon as we refactor the core
    #        ions).
    # @fixme After override, load the parent page instead of displaying the
    #        message.
    def handle_request(self, request):
        request['Cache-Control'] = 'no-cache, no-store'
        request['Content-Type'] = 'text/html; charset=UTF-8'
        self.last_request = request
        user = request.user_object()
        if user is not None and user.name() == 'eweb':
            request.error(401)
        path = request.get_path()
        if path[-1] == '/':
            path = path[0:-1]
        nodeurl = path[len(self.request_path):]
        if nodeurl=='':
            nodeurl = '/'
        parameters = request.get_query_dictionary()
        parameters.update(request.get_post_data())
        sections = {'node-name': "",
                    'node-error': "",
                    'node-action': "",
                    'node-children': "",
                    'node-response': "",
                    'node-hierarchy': "",
                    'node-persistence': "",
                    'node-configuration': ""}
        try:
            node = self._as_node(nodeurl)
            if parameters.has_key("action"):
                action = parameters["action"]
                block = ['<div class="node-section node-action">']
                block.append('<h2 class="section-name">Action</h2>')
                if action == "get_override":
                    block.append(self.get_override_form(nodeurl, parameters))
                elif action == "set_override":
                    block.append(self.get_override_result(nodeurl,parameters))
                elif action.startswith("debug_"):
                    block.append(self.get_setdebug_result(nodeurl,parameters))
                elif action == "invoke":
                    result = self.get_invoke_result(request, nodeurl, parameters)
                    if parameters.has_key('Content-Type'):
                        # force response to be exactly as returned in result
                        # do not render in default nodebrowser page
                        request.push(result)
                        request.done()
                        return
                    # else just insert result into normal page
                    block.append(result)
                else:
                    block.append("Unrecognized action: %s" % cgi.escape(action))
                block.append("</div>")
                sections["node-action"] = "\n".join(block)
                response = self.get_default_action_presentation(node, nodeurl)
                sections.update(response)
            elif hasattr(node, 'nodebrowser_handler'):
                response = node.nodebrowser_handler(self, path, node, nodeurl)
                sections["node-response"] = response
            else:
                response = self.get_default_presentation(node, nodeurl)
                sections.update(response)
        except Exception,e:
            msg = 'Nodebrowser had an error:%s' % str(e)
            mpx.lib.msglog.log('broadway',mpx.lib.msglog.types.ERR,msg)
            mpx.lib.msglog.exception(prefix="handled")
            sections["node-response"] = self._create_error_page(nodeurl,e)
        response = self.template % sections
        request.push(response)
        request.done()
    def get_override_form(self, nodeurl, parameters):
        try:
            value = self.getvalue(nodeurl)
        except Exception,e:
            value = self._get_exception_name(e)
        return "".join(self.override_form(self.request_path + nodeurl, value))
    def get_override_result(self, nodeurl, parameters):
        if parameters.has_key('value'):
            value = parameters['value']
        else:
            value = ""
        value = _holistic_conversion(value)
        self._as_node(nodeurl).set(value)
        message = "Override sent, current value: %s"
        return message % _htmlescape(self.getvalue(nodeurl))
    def get_setdebug_result(self, nodeurl, parameters):
        try:
            node = mpx.lib.node.as_internal_node(nodeurl)
            if parameters['action'] == 'debug_on':
                node.debug = 1
                response = "Debugging turned on."
            else:
                node.debug = 0
                response = "Debugging turned off."
        except Exception,e:
            response = self._get_exception_msg(e)
        return response
    def get_invoke_result(self, request, nodeurl, parameters):
        args = ()
        method = None
        if parameters.has_key('method'):
            method = parameters['method']
        if parameters.has_key('Content-Type'):
            content_type = parameters['Content-Type']
            request['Content-Type'] = content_type
        node = mpx.lib.node.as_internal_node(nodeurl)
        parameters['request']=request
        if method is not None:
            if parameters.get('parameters', 0):
                response = getattr(node,method)(*args, **parameters)
            else:
                response = getattr(node,method)(*args)
        else:
            response = node(*args)
        response = str(response)
        return response
    def _get_simple_error_msg(self):
        html = '<body>'
        html += 'An error occured while processing your request.'
        html += '<a href="javascript:history(1)">Click</a> here to return to the previous page.'
        html += '</body>'
        return html
    def get_default_action_presentation(self, node, node_url):
        navigation = self.get_navigation_block(node_url)
        title = self.get_node_block(node)
        templateargs = {'node-name': title,
                        'node-hierarchy': navigation}
        return templateargs
    def get_default_presentation(self, node, node_url):
        navigation = self.get_navigation_block(node_url)
        title = self.get_node_block(node)
        children = self.get_children_block(node)
        configuration = self.get_configuration_block(node)
        persistence = self.get_pdo_block(node_url)
        templateargs = {'node-name': title,
                        'node-hierarchy': navigation,
                        'node-persistence': persistence,
                        'node-children': children,
                        'node-configuration': configuration}
        return templateargs
    def get_default_view(self, node, node_url):
        return self.get_default_view_for(
            self.get_default_presentation(node, node_url))
    def get_default_view_for(self, sections):
        return '''    %(node-hierarchy)s
     %(node-name)s
     %(node-children)s
     %(node-configuration)s
     %(node-persistence)s''' % sections
    def get_node_block(self, node):
        return '<h1 class="title">Node: %s</h1>' % node.name
    def get_children_block(self, node):
        if not hasattr(node, 'children_names'):
            return ""
        if not len(node.children_names()):
            return ""
        block = ['<div class="node-section node-children">']
        block.append('<h2 class="section-name">Children</h2>')
        block.append('<ul class="children">')
        block.extend(self.children_list(node))
        block.append("</ul>")
        block.append("</div>")
        return "\n".join(block)
    def get_children_html(self, node):
        # backwards compatibility
        return self.get_children_block(node)
    def get_configuration_block(self, node):
        block = ['<div class="node-section node-configuration">']
        block.append('<h2 class="section-name">Configuration</h2>')
        block.append('<ul class="configuration">')
        if hasattr(node, 'configuration'):
            block.extend(self.config_list(node))
        block.append("</ul>")
        block.append("</div>")
        return "\n".join(block)
    def get_configuration_html(self,node):
        # backwards compatibility
        return self.get_configuration_block(node)
    def get_pdo_block(self, node_url):
        node_pdos = self.get_node_pdos(node_url)
        if not node_pdos:
            return ""
        block = ['<div class="node-section node-persistence">']
        block.append('<h2 class="section-name">Persistence</h2>')
        for pdo_info in node_pdos:
            block.append('<ul class="pdo-details">')
            filename = pdo_info['filename']
            gctypes = {GC_NEVER:'GC_NEVER',
                       GC_ONDELETE:'GC_ONDELETE',
                       GC_ASNEEDED:'GC_ASNEEDED',
                       GC_ONFAILURE:'GC_ONFAILURE'}
            gctype = gctypes.get(pdo_info['type'], "unknown")
            block.append("<li>filename = %s</li>" % filename)
            block.append("<li>type = %s</li>" % gctype)
            block.append("</ul>")
        block.append("</div>")
        return "\n".join(block)
    def get_pdo_html(self, node_url):
        # backwards compatibility
        return self.get_pdo_block(node_url)
    def get_node_pdos(self, node_url):
        registered_pdos = GC.registered_pdo_tuple()
        if self.__registered_pdos is not registered_pdos:
            self.__rebuild_pdo_map(registered_pdos)
        return self.__pdo_map.get(node_url,())
    def __rebuild_pdo_map(self, registered_pdos):
        self.__pdo_map = {}
        for pdo_info in registered_pdos:
            node_url = pdo_info['nodename']
            if not self.__pdo_map.has_key(node_url):
                self.__pdo_map[node_url] = []
            self.__pdo_map[node_url].append(pdo_info)
        self.__registered_pdos = registered_pdos
        return registered_pdos
    def _get_show_details_js(self):
        js = '<script type="text/javascript">'
        js += 'function show_details(){'
        js += '    e = document.getElementById("details");'
        js += '    e.style.display="block";'
        js += '    e.style.visibility="visible";'
        js += '}'
        js += '</script>'
        return js
    def _create_error_page(self,node_url,e):
        try:
            #html = '<body>'
            #html += self._make_links(node_url) + '<p>\n'
            html = 'An <span style="color:red;font-weight:bold" >ERROR</span> occured while processing your request.<p>\n'
            html += '<a href="javascript:history.back()">Click</a> here to return to the previous page.<p>\n'
            html += '<a href="javascript:show_details()">Click here to display more details</a>'
            html += '<div id="details" style="display:none;visibility:hidden;color:red">'
            html += '<span style="color:#000000;font-weight:bold;font-size:25px">'
            html += 'Details</span><hr><p>%s</div>' % self._get_exception_msg(e)
            #html += '</body>'
            html += self._get_show_details_js()
            #html += '</html>'
        except Exception,er:
            msg = 'Error while trying to create the error page for the nodebrowser\n'
            msg += 'Error:%s \n' % str(er)
            msg += 'Original Error:%s \n' % str(e)
            mpx.lib.msglog.log('broadway',mpx.lib.msglog.types.ERR,msg)
            html = self._get_simple_error_msg()
        return html

    ##
    # Generate html list of children nodes, where each node is represented as a hyperlink
    # if it itself has children nodes, and each node has its current value displayed
    # if it has a value, and its value is also a hyperlink if it is overridable.
    #
    # @param node  The node whose children are to be displayed.
    # @return list of html lines.
    #
    def children_list(self, node):
        items = []
        nodeobj = mpx.lib.node.as_node(node.as_node_url())
        childnodes = sorted(nodeobj.children_nodes(), cmp=nodecmp)
        for childnode in childnodes:
            content = []
            childname = childnode.name
            childurl = as_node_url(childnode)
            child = node.get_child(childname)
            if hasattr(childnode, 'configuration'):
                line = '<a class="node-link" href="%s%s">%s</a>\n'
                content.append(line % (self.request_path,childurl,childname))
            else:
                content.append(childname)
            # Double has-attribute checks insecured-reference 
            # first to bypass unnecessary authorization calls. 
            # Note that has-attribute call also authorizes access.
            if hasattr(childnode, "get") and hasattr(child, "get"):
                content.append(" = ")
                if hasattr(childnode, "set") and hasattr(child, "set"):
                    html = ('<a href="%s%s?action=get_'
                           'override" class="node_link">')
                    content.append(html % (self.request_path, childurl))
                    fmt = '%s</a>'
                else:
                    fmt = '%s'
                try:
                    # Note access to 'get' authorized already.
                    value = _htmlescape(self.getvalue(childnode))
                except Exception,error:
                    msglog.exception(prefix="handled")
                    value = self._get_exception_msg(error)
                content.append(fmt % (value,))
            items.append("<li>%s</li>" % "".join(content))
        return items


    ##
    # Generate html list of the configuration parameters and their values
    # for <code>node</code>
    #
    # @param node  The node whose configuration to list.
    # @return list of html lines representing the list.
    #
    def config_list(self, node):
        html_lines = []
        config = node.configuration()
        keys = config.keys()
        ##
        # Sort keys that starts with '_' after keys that do not.
        # If both (or neither) key starts with '_', then sort normally.
        def cfg_sort(k1,k2):
            _k1 = int(k1.startswith('_'))
            _k2 = int(k2.startswith('_'))
            if not (_k1 ^ _k2):
                # Both or neither start with '_', use the normal cmp()
                return cmp(k1, k2)
            # OK, only one of the keys starts with '_'.  If _k1 starts with
            # '_', then return 1 so k1 sorts after k2.  If _k2 starts with
            # '_', then return -1 so k1 sorts before k2.
            return _k1 - _k2
        keys.sort(cfg_sort)
        for key in keys:
            # we don't want to show the password
            if key == 'password':
                c = '*****'
            elif key[:5] == 'HTML_':
                c = config[key]
            else:
                c = _htmlescape(config[key])
            html_lines.append('<li>' + key + ' = %s' % c + '</li>')
        return html_lines

    ##
    # Generate html form for overriding a point.
    #
    # @param path  Path to the point being overrode.
    # @param value  The current value of the point.  Will
    #               be used as the default value for the form.
    # @return List of html lines representing the form.
    #
    def override_form(self, path, value):
        html_lines = []
        formtag = '<form action="%s" method="GET" name="setvalue">'
        html_lines.append(formtag % path)
        actiontag = '<input type="hidden" name="action" value="set_override">'
        html_lines.append(actiontag + "</input>")
        fieldtag = '<input type="text" value=%s name="value" id="override" />'
        html_lines.append(fieldtag % _htmlquotevalue(value))
        submittag = '<input type="submit" name="set" value="Override" />'
        html_lines.append(submittag)
        html_lines.append('</form>')
        return html_lines

##
# Escape characters that could confuse the HTML rendering of the value.
def _htmlescape(text):
    if isinstance(text,str) or isinstance(text,unicode):
        text = repr(text)
        text = text.replace("&", "&amp;")
        #text = text.replace("<", "&lt;")
        #text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace(' ', "&nbsp;")
        text = text.replace('\r\n', "<br>")
        text = text.replace('\n\r', "<br>")
        text = text.replace('\n', "<br>")
        text = text.replace('\r', "<br>")
    elif isinstance(text, dict):
        keys = text.keys()
        for key in keys:
            # we don't want to show the password
            if key == 'password':
                text[key] = '*****'
    return text

##
# Surround an HTML TAG attribute value with quotes in an RFC1866
# compliant manner.
def _htmlquotevalue(value):
    value = str(value)
    # So the INPUT doesn't interpret &xxx; sequences in strings...
    value = value.replace('&', '&amp;')
    # rfc1866 says that '>' can confuse some implementations.
    value = value.replace('>', '&gt;')
    if "'" in value:
        # If quoting with double quotes, we need to escape double quotes.
        value = value.replace('"', '&quot;')
        value = '"%s"' % value
    else:
        # No single quotes in the string, use single quotes.
        value = "'%s'" % value
    return value

##
# Unescape an attribute value extracted from the QUERY STRING.
def _unescapevalue(value):
    # The value is already URL DECODED.  This stub is here
    # in case there is a special case we are unaware of...
    return value

##
# Instanciates and returns RequestHandler.  Allows
# for uniform instaciation of all classes defined
# in framework.
#
# @return Instance of RequestHandler defined in this module.
#
def factory():
    return Browser()
