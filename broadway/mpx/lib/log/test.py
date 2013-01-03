"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture

from time import mktime,strptime,ctime,time
import os
from mpx.lib.log import Log

class TestLogFixture(DefaultTestFixture):

    def correct_end_slice_date(self,a_date):
        
        rtValue = self.get_next_scheduled_date(a_date)

        if a_date + self.log_period == rtValue:
            rtValue = a_date - self.log_period
        elif a_date + self.log_period > rtValue:
            rtValue = rtValue - self.log_period
            
        return rtValue

    def correct_end_range_date(self,a_date):

        rtValue = self.get_next_scheduled_date(a_date)
        if rtValue > a_date:
            rtValue = rtValue - self.log_period
        return rtValue

    def correct_start_slice_date(self,a_date):
        return self.correct_start_range_date(a_date)
    
    def correct_start_range_date(self,a_date):

        rtValue = self.get_next_scheduled_date(a_date)
        if a_date + self.log_period == rtValue:
            rtValue = a_date
        elif a_date + self.log_period > rtValue:
            rtValue = rtValue
        return rtValue
    
    def get_next_scheduled_date(self,a_date):
        rtDate = a_date + (self.log_period - (a_date%self.log_period))
       
        return rtDate

    def _get_range_slice_results(self,column,start_date,end_date,type):
        rtValue = {}
        
        e_date = mktime(strptime(end_date,'%m/%d/%Y %H:%M:%S'))
        s_date = mktime(strptime(start_date,'%m/%d/%Y %H:%M:%S'))
        log_start_date = mktime(strptime(self.log_start_date,'%m/%d/%Y %H:%M:%S'))
        log_end_date = mktime(strptime(self.log_end_date,'%m/%d/%Y %H:%M:%S'))
        
        #check to see if we have a valid range:
        if e_date > s_date:

            #check to see if range falls in the log file dates
            if s_date >= log_start_date and \
               e_date <= log_end_date:
                
                if type == 'range':
                    rtValue['number_of_records'] = \
                      ((self.correct_end_range_date(e_date) \
                        - self.correct_start_range_date(s_date))/self.log_period) + 1
                    rtValue['last_record'] = self.correct_end_range_date(e_date)
                    rtValue['first_record'] = self.correct_start_range_date(s_date)

                elif type == 'slice':
                    rtValue['number_of_records'] = \
                      ((self.correct_end_slice_date(e_date) \
                        - self.correct_start_slice_date(s_date))/self.log_period) + 1 

                    rtValue['first_record'] = self.correct_start_slice_date(s_date)
                    rtValue['last_record'] = self.correct_end_slice_date(e_date)

            elif e_date < log_start_date:
                rtValue['number_of_records'] = 0
                rtValue['first_record'] = None
                rtValue['last_record'] = None

            elif s_date > log_end_date:
                 rtValue['number_of_records'] = 0
                 rtValue['first_record'] = None
                 rtValue['last_record'] = None
                 
            elif s_date < log_start_date and \
                 e_date <= log_end_date and \
                 e_date >= log_start_date:
                if type == 'range':
                    rtValue['number_of_records'] = \
                            ((self.correct_end_range_date(e_date) \
                              - log_start_date)/self.log_period) + 1
                    rtValue['first_record'] = log_start_date
                    rtValue['last_record'] = self.correct_end_range_date(e_date)

                elif type == 'slice':
                    rtValue['number_of_records'] = \
                            ((self.correct_end_slice_date(e_date) \
                              - log_start_date)/self.log_period) + 1
                    rtValue['first_record'] = log_start_date
                    rtValue['last_record'] = self.correct_end_slice_date(e_date)
                    
            elif s_date >= log_start_date and \
                 s_date <= log_end_date and \
                 e_date > log_end_date:

                if type == 'range':
                    rtValue['number_of_records'] = \
                           ((log_end_date - \
                           self.correct_start_range_date(s_date))/self.log_period) + 1
                    rtValue['first_record'] = self.correct_start_range_date(s_date)
                    rtValue['last_record'] = log_end_date

                elif type == 'slice':
                    rtValue['number_of_records'] = \
                           ((log_end_date - \
                           self.correct_start_slice_date(s_date))/self.log_period) + 1
                    rtValue['first_record'] = self.correct_start_slice_date(s_date)
                    rtValue['last_record'] = log_end_date
                    
            elif s_date < log_start_date \
                 and e_date > log_end_date:

                if type == 'range':
                    rtValue['number_of_records'] = \
                      ((log_end_date - log_start_date)/self.log_period) + 1
                    rtValue['first_record'] = log_start_date
                    rtValue['last_record'] = log_end_date

                elif type == 'slice':
                    rtValue['number_of_records'] = \
                      ((log_end_date - log_start_date)/self.log_period) + 1
                    rtValue['first_record'] = log_start_date
                    rtValue['last_record'] = log_end_date
        else:
            rtValue['number_of_records'] = 0
            rtValue['first_record'] = None
            rtValue['last_record'] = None

        return rtValue   
    ##
    # @note right now this method assumes that intColumn and fltColumn
    #  start at 1 and increase by 1 and assumes the timestamp is
    # the column that we are getting the range on
    def get_range_results(self,column,start_date,end_date):
        return self._get_range_slice_results(column,start_date,end_date,'range')

    def get_slice_results(self,column,start_date,end_date):
        return self._get_range_slice_results(column,start_date,end_date,'slice')

    def get_trim_le_timestamp_results(self,trimDate):
        d = mktime(strptime(trimDate,'%m/%d/%Y %H:%M:%S'))
           
    def get_log(self,start_date='1/1/2001 00:00:00',\
                end_date='1/30/2001 00:00:00',period=900):

        self.log_start_date = start_date
        self.log_end_date = end_date
        self.log_period = period

        int_column_start = 1
        int_column_increment = 1
        flt_column_start = 1.0
        flt_column_increment = 1.0

        int_column = int_column_start
        flt_column = flt_column_start

        tmp = ''
        log = None
        f = None
        column_names = ('timestamp','intColumn','fltColumn')
        log_name = 'test'
        s_date = mktime(strptime(start_date,'%m/%d/%Y %H:%M:%S'))
        e_date = mktime(strptime(end_date,'%m/%d/%Y %H:%M:%S'))
          
        # add save off the current
        tmp = properties.LOGFILE_DIRECTORY
        try:
            f = open(os.path.join(tmp,log_name + '.log'),'w')
            #create the file
            while s_date <= e_date:
                f.write('{\'timestamp\':' + str(s_date) + ',' + \
                        '\'intColumn\':' + str(int_column) + ',' + \
                        '\'fltColumn\':' + str(flt_column) + '}\n')
                int_column = int_column + int_column_increment
                flt_column = flt_column + flt_column_increment
                s_date = s_date + period

            l = Log(log_name)
            l.configure(column_names,max_return_length=200000)

        finally:      
            # switch back the environment variable
            properties.set('LOGFILE_DIRECTORY', tmp)
            f.close()
        return l
        
