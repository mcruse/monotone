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
# This module exists to support any upgrade issues related to NodeDefs.

MAP = {
    '1.1.6': { 'META': { 'data-source':'SELF',
                         'implementation':1 },
               'renamed_node_ids': { '1248':'115248',
                                     '1249':'115249',
                                     '1250':'115250',
                                     '1251':'115251',
                                     '1252':'115252',
                                     '1253':'115253',
                                     '1254':'115254',
                                     '1255':'115255',
                                     '1256':'115256',
                                     '1257':'115257',
                                     '1258':'115258',
                                     '1259':'115259',
                                     '1260':'115260',
                                     '1261':'115261', },
               },
    }
