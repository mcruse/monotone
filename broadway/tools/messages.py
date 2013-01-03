"""
Copyright (C) 2005 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
from optparse import *
import time
import os

def print_row(row,time_format):
	print '%s %s %s %s' % (time.strftime(
		time_format,time.localtime(row[1])),row[2],row[3],row[4])
##
# @bug If the DB is removed after viewer is run, 
#   there are some problems I don't understand.
def run_viewer(options,args):
	import sqlite
	time_format = options.tformat
	sql = "select * from msglog where rowid>"
	sql += "(select max(rowid) from msglog) - %s" % (options.tail,)
	run = 1
	last_id = 0
	failures = 0
	DB = sqlite.connect(options.db)
	cursor = DB.cursor()
	while run:
		if not os.path.exists(options.db):
			# Must do this because removing watched msglog
			#   causes all cpu to be used and machine crash.
			raise IOError('Database does not exist.  Exiting.')
		try:
			try:
				cursor.execute(sql)
				failures = 0
			except sqlite.OperationalError,e:
				if failures >= 10:
					print 'Got OperationalError 10+ times: %r' % e
				failures += 1
			except sqlite.DatabaseError,e:
				print 'Got DatabaseError "%s".  Retrying in 5 seconds.' % e
				time.sleep(5)
				reload(sqlite)
				continue
			for row in cursor:
				print_row(row,time_format)
				last_id = row[0]
			run = options.follow
			sql = 'select * from msglog where rowid>%s' % (last_id)
		except Exception,error:
			if isinstance(error,KeyboardInterrupt):
				raise
			print 'Got unexpected exception "%s".  Continuing to run.' % error
		time.sleep(1)

if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option("-D", "--Database", dest="db",
			default='/var/mpx/db/msglog.db',
			help="Database file", metavar="DATABASE")
	parser.add_option("-d", "--debug",dest="DEBUG",
			default=0, help="Turn on debug")
	parser.add_option("-f", "--follow",dest="follow",
			default=0,action="store_true", help="Follow the log")
	parser.add_option("-t", "--tail",dest="tail", default=20,
			help="Print out the last few rows")
	parser.add_option("-F", "--TimeFormat",dest="tformat",
			default='%m/%d/%y %H:%M:%S',help="Follow the log")
	options,args = parser.parse_args()
	try:
		run_viewer(options,args)
	except KeyboardInterrupt:
		pass

