"""
Copyright (C) 2001 2002 2003 2004 2007 2008 2009 2010 2011 Cisco Systems

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

from mpx.lib import urllib
from mpx.lib import thread
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
    if a.hasattr('nodecmp'):
        return a.nodecmp(as_node_url(b))
    return cmp(a.name,b.name)

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
        set_attribute(self, 'secured', False, config, as_boolean)
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
            try: sm = mpx.lib.node.as_node('/services/Security Manager')
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
        else: self._secured = False
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
        if path.startswith(self.request_path):
            return 1
        return 0

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
       
    def _get(self,node):
        if isinstance(node, str):
            node = self._as_node(node)
        value = node.get()
        return value

    def _make_links(self,path):
        slash = '<font color="#FFFFFF">/</font><wbr>'
        links = path.split("/")
        html = """<table width="100%%">
<tr>
    <td align="left" width="639px">
    <img src="/mpx/images/nodebrowser_logo.png" width="175" height="142">
    </td>
    <td align="right" valign="top">
    <a class="home" href="/index.html">Home</a>&nbsp;
    </td>
</tr>
</table>
<table cellpadding="4" width="100%%">
<tr>
    <td align="left"
        bgcolor="%(bgcolor)s">%(slash)s<a href="/nodebrowser"
        class="node_path_link">nodebrowser</a>""" % {
            'slash':slash,
            'bgcolor':'#999999',
            }
        link = ""
        a = '/nodebrowser/'
        for l in links[1:]:
            a = posixpath.join(a, l)
            link = (
                '%s<a href="%s"\n   class="node_path_link">%s</a>' %
                (slash, a, urllib.unquote(l))
                )
            html += link
        html += '</td>\n</tr>\n</table>\n'
        html = html[:-1]
        return html

    def _get_pre_body_tag(self):
        stylesheets = ["/stylesheets/main.css","/stylesheets/nodebrowser.css"]
        html  = '<html>\n'
        html += '<head>\n'
        for s in stylesheets:
            html += '<link rel="stylesheet" '
            html += 'href="%s" ' % s
            html += 'type="text/css" >\n'
        html += '</head>\n'
        return html
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
        user = request.user_object()
        if user is not None and user.name() == 'eweb':
            request.error(401)
        response = Response(request)
        response_sent = 0
        try:
            html = self._get_pre_body_tag()
            html += '<body>'
            if self.debug:
                mpx.lib.msglog.log('broadway',mpx.lib.msglog.types.INFO,
                                    'handler_request called for device_viewer')
            if not self.enabled:
                html += '<span class="disabled_msg">Sorry, the handler for your request is currently disabled.</span>\n'
            else:
                path = request.get_path()
                if path[-1] == '/':
                    path = path[0:-1]
                node_url = path[len(self.request_path):]
                if node_url=='':
                    node_url = '/'
                html += self._make_links(node_url) + '<p>\n'
                if request.has_query():
                    # This request was for an action becuause it has
                    # parameters.
                    parameters = request.get_query_dictionary()
                    if parameters['action'] == 'get_override':
                        try:
                            value = self._get(node_url)
                        except Exception,e:
                            value = self._get_exception_name(e)
                        html  += string.join(self.override_form(path,value))
                    elif parameters['action'] == 'set_override':
                        if parameters.has_key('value'):
                            value = parameters['value']
                        else:
                            value = ""
                        value = _holistic_conversion(value)
                        self._as_node(node_url).set(value)
                        html += '<h3>Your override has been sent</h3>'
                    elif parameters['action'] == 'debug_on' or parameters['action'] == 'debug_off':
                        try:
                            node = mpx.lib.node.as_internal_node(node_url)
                            if parameters['action'] == 'debug_on':
                                node.debug = 1
                                html += 'Debugging turned on'
                            else:
                                node.debug = 0
                                html += 'Debugging turned off'
                        except Exception,e:
                            msg = self._get_exception_msg(e)
                            html += msg
                    elif parameters['action'] == 'invoke':
                        args = ()
                        method = None
                        if parameters.has_key('method'):
                            method = parameters['method']
                        if parameters.has_key('Content-Type'):
                            content_type = parameters['Content-Type']
                        else:
                            content_type = 'text/plain'
                        try:
                            node = mpx.lib.node.as_internal_node(node_url)
                            if method is not None:
                                if parameters.get('parameters',0):
                                    result = getattr(node,method)(*args, **parameters)
                                else:
                                    result = getattr(node,method)(*args)
                            else:
                                result = node(*args)
                            if hasattr(result,'read'):
                                from mpx.service.network.http import producers
                                if hasattr(result,'close'):
                                    result = producers.FileProducer(result)
                                else:
                                    result = producers.StreamingProducer(
                                        result
                                        )
                            else:
                                result = str(result)
                            response['Content-Type'] = content_type
                            response.send(result)
                            response_sent = 1
                            return
                        except Exception,e:
                            message = "%s: %s" % (e.__class__, str(e))
                            response['Content-Type'] = 'text/plain'
                            response.send_error(400,message)
                            response_sent = 1
                            return
                    else:
                        html += (
                            '<h3>Sorry, your request is not recognized</h3>\n'
                            )
                else:
                    node = self._as_node(node_url)
                    if hasattr(node, 'nodebrowser_handler'):
                        html += node.nodebrowser_handler(self, path,
                                                         node, node_url)
                    else:
                        html += self.get_default_view(node, node_url)
            html += '</body></html>\n'
            response.send(html)
            response_sent = 1
        except Exception,e:
            html = self._create_error_page(node_url,e)
            if response_sent == 0:
                response.send(html)
            else:
                msg = 'Nodebrowser had an error:%s' % str(e)
                mpx.lib.msglog.log('broadway',mpx.lib.msglog.types.ERR,msg)
        return
    def _get_simple_error_msg(self):
        html =  self._get_pre_body_tag()
        html += '<body>'
        html += 'An error occured while processing your request.'
        html += '<a href="javascript:history(1)">Click</a> here to return to the previous page.'
        html += '</body></html>'
        return html
    def get_default_view(self, node, node_url):
        html = self.get_children_html(node)
        html += self.get_configuration_html(node)
        html += self.get_pdo_html(node_url)
        return html
    def get_children_html(self, node):
        if hasattr(node, 'children_nodes'):
            if len(node.children_names()):
                return ('<h4>Children</h4>\n%s\n' %
                        string.join(self.children_list(node), '\n'))
        return ''
    def get_configuration_html(self, node):
        if hasattr(node, 'configuration'):
            return ('<h4>Configuration</h4>\n%s\n' %
                    string.join(self.config_list(node), '\n'))
        return ''
    def get_pdo_html(self, node_url):
        node_pdos = self.get_node_pdos(node_url)
        if not node_pdos:
            return ''
        pdo_html = '<h4>PDO Details</h4>\n'
        for pdo_info in node_pdos:
            pdo_html += (
                '<ul><li>filename = %s</li>'
                '<li>type = %s</li></ul>'
                ) % (
                pdo_info['filename'],
                {GC_NEVER:'GC_NEVER',
                 GC_ONDELETE:'GC_ONDELETE',
                 GC_ASNEEDED:'GC_ASNEEDED',
                 GC_ONFAILURE:'GC_ONFAILURE',}.get(pdo_info['type'],
                                                      'unknown')
                )
        return pdo_html
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
            html = self._get_pre_body_tag()
            html += '<body>'
            html += self._make_links(node_url) + '<p>\n'
            html += 'An <span style="color:red;font-weight:bold" >ERROR</span> occured while processing your request.<p>\n'
            html += '<a href="javascript:history.back()">Click</a> here to return to the previous page.<p>\n'
            html += '<a href="javascript:show_details()">Click here to display more details</a>'
            html += '<div id="details" style="display:none;visibility:hidden;color:red">'
            html += '<span style="color:#000000;font-weight:bold;font-size:25px">'
            html += 'Details</span><hr><p>%s</div>' % self._get_exception_msg(e)
            html += '</body>'
            html += self._get_show_details_js()
            html += '</html>'
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
        html_lines = ['<ul>']
        sorted_nodes = node.children_nodes()
        sorted_nodes.sort(nodecmp)
        for child in sorted_nodes:
            html_lines.append('<li>')
            if hasattr(child, 'configuration'):
                line = ('<a href="' + '/nodebrowser' + child.as_node_url() +
                        '"\n   class="node_link">')
                line += child.name + '</a>'
                html_lines.append(line)
            else:
                html_lines.append(child.name)

            if hasattr(child, 'get'):
                line = ' = '
                if hasattr(child, 'set'):
                    line += ('<a href="' + '/nodebrowser' +
                                child.as_node_url() +
                                '?action=get_override"\n   class="node_link">')
                    fmt = '%s</a>'
                else:
                    fmt = '%s'
                try:
                    value = _htmlescape(self._get(child))
                except Exception,e:
                    msglog.exception()
                    value = self._get_exception_msg(e)
                line += fmt % (value,)
                html_lines.append(line)
            html_lines.append('</li>')
        html_lines.append('</ul>')
        return html_lines

    ##
    # Generate html list of the configuration parameters and their values
    # for <code>node</code>
    #
    # @param node  The node whose configuration to list.
    # @return list of html lines representing the list.
    #
    def config_list(self, node):
        html_lines = ['<ul>']
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
        html_lines.append('</ul>')
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
        html_lines.append('<form action="' + path + '" method=get name=setvalue>\n')
        html_lines.append('<input type=hidden name=action value="set_override">\n')
        html_lines.append(
            '<input type=text value=%s name=value size="35"><br>\n' %
            _htmlquotevalue(value)
            )
        html_lines.append('<input type=submit name=set value="Set Value">')
        html_lines.append('<input type=reset name=reset value="Clear">')
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
    from mpx.lib.node.nodes import Browser
    return Browser()
