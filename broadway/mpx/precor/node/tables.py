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
# tables.py: Tables used by IcsAppSvcNode to progam mpx.ion.aerocomm.FeuPollThread.

        self.properties = {
            'Version'             :('\x91', self.unpack_version, 0),
            'Serial_Number'       :('\x94', None, 0),
            #'List'                :('\x98', self.hexdump),
            'Utilization'         :('\x99', self.unpack_int24, 0),
            'Odometer'            :('\x9b', self.unpack_int32_units, 0),
            'Error_Code'          :('\x9c', self.unpack_int24, 0),
            'Workout_Time'        :('\xa0', self.unpack_time, 1),
            'Horizontal_Distance' :('\xa1', self.unpack_int16_units, 1),
            'Vertical_Distance'   :('\xa2', self.unpack_int16_units, 1),
            'Calories'            :('\xa3', self.unpack_int16, 1),
            'Program'             :('\xa4', self.unpack_2_bytes, 1),
            'Speed'               :('\xa5', self.unpack_int16_units, 1),
            'Grade'               :('\xa8', self.unpack_int16_units, 1),
            'Gear'                :('\xa9', self.unpack_1_byte, 1),
            #'Uplist'              :('\xaa', self.hexdump),
            'User_Information'    :('\xab', self.unpack_user_data, 1),
            'Current_Heart_Rate'  :('\xb0', self.unpack_1_byte, 1),
            'Time_in_HR_Zone'     :('\xb2', self.unpack_time, 1),
            'Power'               :('\xb4', self.unpack_int16_units, 1),
            'Average_HR'          :('\xb5', self.unpack_1_byte, 1),
            'Maximum_HR'          :('\xb6', self.unpack_1_byte, 1),
            'Status'              :('\x80', self.unpack_status, 0),
            }
        
scan_list_treadmill = ['Utilization',
                       'Odometer',
                       'Workout_Time',
                       'Horizontal_Distance',
                       'Calories',
                       'Program',
                       'Speed',
                       'Grade',
                       'User_Information',
                       'Current_Heart_Rate',
                       'Time_in_HR_Zone',
                       'Power',
                       'Average_HR',
                       'Maximum_HR',
                       ]
                       
scan_list_elliptical = ['Utilization',
                        'Odometer',
                        'Workout_Time',
                        'Horizontal_Distance',
                        'Calories',
                        'Program',
                        'Speed',
                        'Grade',
                        'Gear',
                        'User_Information',
                        'Current_Heart_Rate',
                        'Time_in_HR_Zone',
                        'Power',
                        'Average_HR',
                        'Maximum_HR',
                        ]
                       
scan_list_cycle = ['Utilization',
                   'Odometer',
                   'Workout_Time',
                   'Horizontal_Distance',
                   'Calories',
                   'Program',
                   'Speed',
                   'Gear',
                   'User_Information',
                   'Current_Heart_Rate',
                   'Time_in_HR_Zone',
                   'Power',
                   'Average_HR',
                   'Maximum_HR',
                   ]
                       
scan_list_climber = ['Utilization',
                     'Odometer',
                     'Workout_Time',
                     'Vertical_Distance',
                     'Calories',
                     'Program',
                     'Speed',
                     'Grade',
                     'User_Information',
                     'Current_Heart_Rate',
                     'Time_in_HR_Zone',
                     'Power',
                     'Average_HR',
                     'Maximum_HR',
                     ]
 
                       
                       
                       
                       