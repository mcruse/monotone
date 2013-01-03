"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
# coding: iso-8859-1
# This is derived from the Trane tsenum file.  It contains a subset of data with all Trane specific info removed

# DO NOT EDIT - created by 'cat *.cpp *.CPP *.h *.H | indent -brs -nbc -nbad -sob -st -l120 | ./enumstrtable.py > tsstrings.py'
# RUN enum.py first

tsenum = {
    (0, 36): 188,
    (0, 72): 1011,    
    (0, 79): 400, 
    (0, 81): 18, 
    (0, 103): 184, 
    (0, 117): 186, 

    (1, 72): 1011,    
    (1, 79): 400, 
    (1, 81): 18, 
    (1, 103): 184, 
    (1, 117): 186, 

    (2, 72): 1011,    
    (2, 79): 400, 
    (2, 81): 18, 
    (2, 103): 184, 
    (2, 117): 186, 

    (3, 36): 188, 
    (3, 72): 1011,    
    (3, 79): 400, 
    (3, 81): 18, 
    (3, 84): 191, 
    (3, 85): 185, 
    (3, 103): 184, 

    (4, 72): 1011,    
    (4, 79): 400, 
    (4, 81): 18, 
    (4, 84): 191, 
    (4, 85): 185, 
    (4, 87): 185, 
    (4, 103): 184, 
    (4, 104): 185, 

    (5, 72): 1011,    
    (5, 79): 400, 
    (5, 81): 18, 
    (5, 85): 185, 
    (5, 87): 185, 
    (5, 103): 184, 
    (5, 104): 185, 

    (6, 72): 1011,    
    (6, 79): 400, 
    (6, 85): 185,
    (6, 103): 184, 
    (6, 104): 185, 

    (8, 79): 400,
    (8, 107): 1001,
    (8, 112): 192,
    (8, 122): 1003,    

    (13, 72): 1011,    
    (13, 79): 400, 
    (13, 81): 18, 
    (13, 103): 184, 

    (14, 72): 1011,    
    (14, 79): 400, 
    (14, 81): 18, 
    (14, 103): 184, 

    (17, 72): 1011,    
    (17, 79): 400, 
    (17, 81): 18, 
    (17, 103): 184, 

    (19, 72): 1011,    
    (19, 79): 400,
    (19, 81): 18, 
    (19, 103): 184, 

#bitstrings 
    (0, 0): 2001,
    (0, 35): 2001,
    (0, 52): 2008,    
    (0, 111): 2002,
    (1, 0): 2001,
    (1, 35): 2001,
    (1, 52): 2008,    
    (1, 111): 2002,
    (2, 0): 2001,
    (2, 35): 2001,
    (2, 52): 2008,    
    (2, 111): 2002,
    (3, 0): 2001,
    (3, 35): 2001,
    (3, 111): 2002,
    (4, 0): 2001,
    (4, 35): 2001,
    (4, 111): 2002,
    (5, 0): 2001,
    (5, 35): 2001,
    (5, 111): 2002,
    (8, 96): 2005,
    (8, 97): 2003,
    (13, 0): 2001,
    (13, 35): 2001,
    (13, 111): 2002,
    (14, 0): 2001,
    (14, 35): 2001,
    (14, 111): 2002,
    (17, 111): 2002,
    (19, 0): 2001,
    (19, 35): 2001,
    (19, 111): 2002,
}

est = {
    18 : { # boolInServiceOutServiceStr [18] ref=5
        0 : "In Service",
        1 : "Out of Service",
        },
    184 : { # BACnetReliabilityStr [184] ref=3
        0 : "No Fault Detected",
        1 : "No Sensor",
        2 : "Over Range",
        3 : "Under Range",
        4 : "Open Loop",
        5 : "Shorted Loop",
        6 : "No Output",
        7 : "Unreliable Other",
        8 : "Process Error",
        9 : "Multi State Fault",
        10: "Configuration Error",
        },
    185 : { # BACnetBinaryPVStr [185] ref=10
        0 : "Inactive",
        1 : "Active",
        },
    186 : { # BACnetEngUnitsStr [186] ref=4
        0 : "Square Meters",
        1 : "Square Feet",
        2 : "Milliamperes",
        3 : "Amperes",
        4 : "Ohms",
        5 : "Volts",
        6 : "Kilovolts",
        7 : "Megavolts",
        8 : "Volt Amperes",
        9 : "Kilovolt Amperes",
        10 : "Megavolt Amperes",
        11 : "Volt Amperes Reactive",
        12 : "Kilovolt Amperes Reactive",
        13 : "Megavolt Amperes Reactive",
        14 : "Degrees Phase",
        15 : "Power Factor",
        16 : "Joules",
        17 : "Kilo Joules",
        18 : "Watt Hours",
        19 : "Kilowatt Hours",
        20 : "BTU",
        21 : "Therm",
        22 : "Ton Hour",
        23 : "Joules per Kilogram Dry Air",
        24 : "BTU per Pound Dry Air",
        25 : "Cycles per Hour",
        26 : "Cycles per Minute",
        27 : "Hertz",
        28 : "Grams Water per Kilogram Dry Air",
        29 : "Percent Relative Humidity",
        30 : "Millimeters",
        31 : "Meters",
        32 : "Inch",
        33 : "Feet",
        34 : "Watts per Square Foot",
        35 : "Watts per Square Meter",
        36 : "Lumen",
        37 : "LUX",
        38 : "Foot Candles",
        39 : "Kilograms",
        40 : "Pounds Mass",
        41 : "Tons",
        42 : "Kilograms Mass per Second",
        43 : "Kilograms Mass per Minute",
        44 : "Kilograms Mass per Hour",
        45 : "Pounds Mass per Minute",
        46 : "Pounds Mass per Hour",
        47 : "Watts",
        48 : "Kilowatts",
        49 : "Megawatts",
        50 : "Btu per Hour",
        51 : "Horsepower",
        52 : "Tons Refrigeration",
        53 : "Pascals",
        54 : "Kilopascals",
        55 : "Bar",
        56 : "Pounds Force per Square Inch",
        57 : "Centimeters Of Water",
        58 : "Inches of Water",
        59 : "Millimeters of Mercury",
        60 : "Centimeters of Mercury",
        61 : "Inches of Mercury",
        62 : "Degrees Celsius",
        63 : "Degrees Kelvin",
        64 : "Degrees Fahrenheit",
        65 : "Degree Days Celsius",
        66 : "Degree Days Fahrenheit",
        67 : "Year",
        68 : "Month",
        69 : "Week",
        70 : "Day",
        71 : "Hour",
        72 : "Minute",
        73 : "Second",
        74 : "Meters per Second",
        75 : "Kilometers per Hour",
        76 : "Feet per Second",
        77 : "Feet per Minute",
        78 : "Miles per Hour",
        79 : "Cubic Feet",
        80 : "Cubic Meters",
        81 : "Imperial Gallons",
        82 : "Liters",
        83 : "Gallons",
        84 : "Cubic Feet per Minute",
        85 : "Cubic Meters per Second",
        86 : "Imperial Gallons per Minute",
        87 : "Liters per Second",
        88 : "Liters per Minute",
        89 : "Gallons per Minute",
        90 : "Degrees",
        91 : "Degrees Celsius per Hour",
        92 : "Degrees Celsius per Minute",
        93 : "Degrees Fahrenheit per Hour",
        94 : "Degrees Fahrenheit per Minute",
        95 : " ",
        96 : "Parts per Million",
        97 : "Parts per Billion",
        98 : "Percent",
        99 : "Percent per Second",
        100 : "Per Minute",
        101 : "Per Second",
        102 : "PSI per Degree Fahrenheit",
        103 : "Radians",
        104 : "Revolutions per Minute",
        105 : "MBH: Thousands of BTUH",
        110 : "Minutes per Degree Fahrenheit",
        111 : "Minutes per Degree Celsius",
        112 : "Kilograms Force per Square Centimeter",
        113 : "Feet of Water Column",
        114 : "Millimeters of Water",
        115 : "Cubic Meters per Minute",
        116 : "Cubic Meters per Hour",
        117 : "Kilocalories per Kilogram Dry Air",
        118 : "Kilojoules per Kilogram Dry Air",
        119 : "Units Unknown",
        260 : "Percent Open",
        261 : "Percent Heating",
        262 : "Percent Cooling",
        258 : "Fahrenheit Temperature Differential",
        257 : "Thousands of CFM",
        259 : "Celsius Temperature Differential",
        256 : "Hundreds of CFM",
        },
    187 : { # BACnetEngUnitsShortStr [187] ref=3
        0 : "m2",
        1 : "ft2",
        2 : "mA",
        3 : "A",
        4 : "ohms",
        5 : "V",
        6 : "kV",
        7 : "MV",
        8 : "VA",
        9 : "kVA",
        10 : "MVA",
        11 : "V A reactive",
        12 : "kV A reactive",
        13 : "MV A reactive",
        14 : "deg phase",
        15 : "power factor",
        16 : "J",
        17 : "kJ",
        18 : "WH",
        19 : "kWH",
        20 : "Btu",
        21 : "therm",
        22 : "ton hr",
        23 : "J/kg",
        24 : "BTU/lb",
        25 : "CPH",
        26 : "CPM",
        27 : "Hz",
        28 : "g H2O/kg",
        29 : "% RH",
        30 : "mm",
        31 : "m",
        32 : "in",
        33 : "ft",
        34 : "W/ft2",
        35 : "W/m2",
        36 : "lumen",
        37 : "LUX",
        38 : "ft Candles",
        39 : "kg",
        40 : "lbs",
        41 : "tons",
        42 : "kg/sec",
        43 : "kg/min",
        44 : "kg/hr",
        45 : "lb mass/min",
        46 : "lb mass/hr",
        47 : "W",
        48 : "kW",
        49 : "MW",
        50 : "Btu/hr",
        51 : "hp",
        52 : "tons",
        53 : "Pa",
        54 : "kPa",
        55 : "bar",
        56 : "PSI",
        57 : "cm W.C.",
        58 : "in W.C.",
        59 : "mm Hg",
        60 : "cm Hg",
        61 : "in Hg",
        62 : "øC",
        63 : "øK",
        64 : "øF",
        65 : "deg days C",
        66 : "deg days F",
        67 : "yr",
        68 : "mon",
        69 : "wk",
        70 : "day",
        71 : "hr",
        72 : "min",
        73 : "sec",
        74 : "m/sec",
        75 : "km/hr",
        76 : "ft/sec",
        77 : "ft/min",
        78 : "MPH",
        79 : "ft3",
        80 : "m3",
        81 : "imp gal",
        82 : "l",
        83 : "gal",
        84 : "CFM",
        85 : "m3/s",
        86 : "imp GPM",
        87 : "L/s",
        88 : "L/min",
        89 : "GPM",
        90 : "deg",
        91 : "øC/hr",
        92 : "øC/min",
        93 : "øF/hr",
        94 : "øF/min",
        95 : " ",
        96 : "ppm",
        97 : "ppb",
        98 : "%",
        99 : "%/sec",
        100 : "per min",
        101 : "per sec",
        102 : "PSI/F",
        103 : "rad",
        104 : "RPM",
        105 : "MBTUH",
        110 : "min/øF",
        111 : "min/øC",
        112 : "cg/cm2",
        113 : "ft W.C.",
        114 : "mm W.C.",
        115 : "m3/min",
        116 : "m3/h",
        117 : "kcal/kg",
        118 : "kJ/kg",
        119 : " ",
        260 : "%open",
        261 : "%heat",
        262 : "%cool",
        258 : "øFd",
        257 : "KCFM",
        259 : "øCd",
        256 : "CCFM",
        },
    188 : { # BACnetEventStateStr [188] ref=3
        0 : "Normal",
        1 : "Alarm",
        2 : "Low Warning",
        3 : "High Warning",
        4 : "Low Alarm",
        5 : "High Alarm",
        },
    191 : { # BACnetPolarityStr [191] ref=2
        0 : "Normal Polarity",
        1 : "Reverse Polarity",
        },
    192 : { # BACnetDeviceStatusStr [192] ref=1
        0 : "Operational",
        1 : "Operational Read Only",
        2 : "Download Required",
        3 : "Download In Progress",
        4 : "Non-Operational",
        },
    198 : { # ApexOpModeStr [198] ref=85
        0 : "Unoccupied",
        1 : "Optimal Start",
        2 : "Occupied",
        3 : "Optimal Stop",
        4 : "Demand Limit",
        5 : "Duty Cycle",
        6 : "Priority Shutdown",
        7 : "Night Economize",
        8 : "Night Heat Cool",
        },
    400 : { # BACnetObjectTypeStr [400] ref=70
        0 : "Analog Input",
        1 : "Analog Output",
        2 : "Analog Value",
        3 : "Binary Input",
        4 : "Binary Output",
        5 : "Binary Value",
        6 : "Calendar",
        7 : "Command",
        8 : "Device",
        9 : "Event Enrollment",
        10 : "File",
        11 : "Group",
        12 : "Loop",
        13 : "MultiState Input",
        14 : "MultiState Output",
        16 : "Program",
        17 : "BACnet Schedule",
        18 : "Averaging",
        19 : "MultiState Value",
        },
    1001 : { # RZ BACnetSegmentation
        0:'segmented_both',
        1:'segmented_transmit',
        2:'segmented_receive',
        3:'no_segmentation',
        },
    1002 : { # RZ BACnetAction
        0:'direct',
        1:'reverse',
        },
    1003 : { # RZ BACnetVTClass
        0:'default_terminal',
        1:'ansi_x3_64',
        2:'dec_vt52',
        3:'dec_vt100',
        4:'dec_vt220',
        5:'hp_700_94',
        6:'ibm_3130',
        },
    1004 : { # RZ BACnetEventType
        0:'change_of_bitstring',
        1:'change_of_state',
        2:'change_of_value',
        3:'command_failure',
        4:'floating_limit',
        5:'out_of_range',
        6:'complex_event_type',
        7:'buffer_ready',
        8:'change_of_life_safety',
        },
    1005 : { # RZ BACnetFileAccessMethod
        0:'record_access',
        1:'stream_access',
        },
    1006 : { # RZ BACnetLifeSafetyMode
        0:'off',
        1:'on',
        2:'test',
        3:'manned',
        4:'unmanned',
        5:'armed',
        6:'disarmed',
        7:'prearmed',
        8:'slow',
        9:'fast',
        10:'disconnected',
        11:'enabled',
        12:'disabled',
        13:'automatic_release_disabled',
        14:'default',
        },
    1007 : { # RZ BACnetLifeSafetyOperation
        0:'none',
        1:'silence',
        2:'silence_audible',
        3:'silence_visual',
        4:'reset',
        5:'reset_alarm',
        6:'reset_fault',
        },
    1008 : { # RZ BACnetLifeSafetyState
        0:'quiet',
        1:'pre_alarm',
        2:'alarm',
        3:'fault',
        4:'fault_pre_alarm',
        5:'fault_alarm',
        6:'not_ready',
        7:'active',
        8:'tamper',
        9:'test_alarm',
        10:'test_active',
        11:'test_fault',
        12:'test_fault_alarm',
        13:'holdup',
        14:'duress',
        15:'tamper_alarm',
        16:'abnormal',
        17:'emergency_power',
        18:'delayed',
        19:'blocked',
        20:'local_alarm',
        21:'general_alarm',
        22:'supervisory',
        23:'test_supervisory',
        },
    1009 : { # RZ BACnetMaintenance
        0:'none',
        1:'periodic_test',
        2:'need_service_operational',
        3:'need_service_inoperative', 
        },
    1010 : { # RZ BACnetSilencedState
        0:'unsilenced',
        1:'audible_silenced',
        2:'visible_silenced',
        3:'all_silenced',
        },
    1011 : { # RZ BACnetNotifyType
        0:'alarm',
        1:'event',
        2:'ack_notification',
        },
    1012 : { # RZ BACnetProgramRequest
        0:'ready',
        1:'load',
        2:'run',
        3:'halt',
        4:'restart',
        5:'unload',
        },
    1013 : { # RZ BACnetProgramState
        0:'idle',
        1:'loading',
        2:'running',
        3:'waiting',
        4:'halted',
        5:'unloading',
        },
    1014 : { # RZ BACnetProgramError
        0:'normal',
        1:'load_failed',
        2:'internal',
        3:'program',
        4:'other',
        },
    1015 : { # BACnetCalendar
        0:'Unoccupied',
        1:'Occupied',
        },
    2001 : { # RZ BACnetEventTransitionBits
        0: 'to_offnormal', 
        1: 'to_fault', 
        2: 'to_normal',
        },
    2002 : { # BACnetStatusFlags
        0: 'in-alarm',
        1: 'fault',
        2: 'overridden',
        3: 'out-of-service',
        },
    2003 : { # BACnetServicesSupported
        0: 'AcknowledgeAlarm',
        1: 'ConfirmedCOVNotification',
        2: 'ConfirmedEventNotification',
        3: 'GetAlarmSummary',
        4: 'GetEnrollmentSummary',
        5: 'SubscribeCOV',
        6: 'AtomicReadFile',
        7: 'AtomicWriteFile',
        8: 'AddListElement',
        9: 'RemoveListElement',
        10: 'CreateObject',
        11: 'DeleteObject',
        12: 'ReadProperty',
        13: 'ReadPropertyConditional',
        14: 'ReadPropertyMultiple',
        15: 'WriteProperty', 
        16: 'WritePropertyMultiple',
        17: 'DeviceCommunicationControl',
        18: 'ConfirmedPrivateTransfer',
        19: 'ConfirmedTextMessage',
        20: 'ReinitializeDevice',
        21: 'VtOpen',
        22: 'VtClose',
        23: 'VtData',
        24: 'Authenticate',
        25: 'RequestKey',
        26: 'I_Am',
        27: 'I_Have',
        28: 'UnconfirmedCOVNotification',
        29: 'UnconfirmedEventNotification',
        30: 'UnconfirmedPrivateTransfer',
        31: 'UnconfirmedTextMessage',
        32: 'TimeSynchronization',
        33: 'Who_Has',
        34: 'Who_Is',
        35: 'ReadRange',
        36: 'UtcTimeSynchronization',
        37: 'LifeSafetyOperation',
        38: 'SubscribeCOVProperty',
        39: 'GetEventInformation',
        },
    2004 : { # BACnetResultsFlags
        0: 'firstitem',
        1: 'lastitem',
        2: 'moreitems',
        },
    2005 : { # BACnetObjectTypesSupported
        0: 'analog_input',
        1: 'analog_output',
        2: 'analog_value',
        3: 'binary_input',
        4: 'binary_output',
        5: 'binary_value',
        6: 'calendar',
        7: 'command',
        8: 'device',
        9: 'event_enrollment',
        10: 'file',
        11: 'group',
        12: 'loop',
        13: 'multi_state_input',
        14: 'multi_state_output',
        15: 'notification_class',
        16: 'program',
        17: 'schedule',
        18: 'averaging',
        19: 'multi_state_value',
        20: 'trend_log',
        21: 'life_safety_point',
        22: 'life_safety_zone',
        },
    2006 : { # BACnetDaysOfWeek
        0: 'monday', 
        1: 'tuesday', 
        2: 'wednesday', 
        3: 'thursday', 
        4: 'friday', 
        5: 'saturday', 
        6: 'sunday',
        },
    2007 : { # BACnetLogStatus
        0: 'log-disabled', 
        1: 'buffer-purged',
        },
    2008 : { # BACnetLimitEnable
        0:'lowLimitEnable',
        1:'highLimitEnable',
        },
}

data_type_enum = {
    1 : "PTYPE_BOOLEAN",
    2 : "PTYPE_UNSIGNEDINT",
    3 : "PTYPE_SIGNEDINT",
    4 : "PTYPE_REAL",
    6 : "PTYPE_OCTETSTRING",
    7 : "PTYPE_CHARSTRING",
    8 : "PTYPE_BITSTRING",
    9 : "PTYPE_ENUMERATED",
    10 : "PTYPE_DATE",
    11 : "PTYPE_TIME",
    50 : "PTYPE_BACNET_OBJECT_ID",
    54 : "PTYPE_BACNET_EVENT_STATE",
    60 : "PTYPE_BACNET_DATE_TIME",
    61 : "PTYPE_BACNET_DATE_RANGE",
    89 : "PTYPE_BACNET_SERVICES_SUPPORTED",
    114 : "PTYPE_BACNET_OBJ_TYPES_SUPPORTD",
    122 : "PTYPE_BACNET_STATUS_FLAGS",
    200 : "PTYPE_BACNET_ADDRESS_BINDING",
    201 : "PTYPE_BACNET_VT_SESSION",
    202 : "PTYPE_BACNET_RECIPIENT",
    204 : "PTYPE_BACNET_COV_SUBSCRIPTION",
    205 : "PTYPE_BACNET_TIME_STAMP",
    206 : "PTYPE_BACNET_SESSION_KEY",
    500 : "PTYPE_BACNET_DAILY_SCHEDULE",
    501 : "PTYPE_BACNET_TIME_VALUE",
    502 : "PTYPE_BACNET_SPECIAL_EVENT",
    503 : "PTYPE_BACNET_DEV_OBJ_PROP_REFERENCE",
    504 : "PTYPE_BACNET_CALENDAR_ENTRY",
    -1  : "PTYPE_ABSTRACT", #DATA TYPE NOT IMPLEMENTED
}

#
# format: {object_type:{property_id:(data_type_enum_key, array_limit, is_array, is_list, ucm page, optional)}}
#
# optional enum
#     required=0, simple optional=1, cov=2, intrinsic reporting=3

object_property_data = {
    0 : { #analog input
        0  : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        17 : (2, 0, 0, 0, 0, 3),  #Notification Class
        22 : (4, 0, 0, 0, 0, 2),  #COV Increment
        25 : (4, 0, 0, 0, 0, 3),  #Deadband
        28 : (7, 0, 0, 0, 0, 1),  #Description
        31 : (7, 0, 0, 0, 0, 1),  #Device Type
        35 : (8, 0, 0, 0, 0, 3),  #Event Enable
        36 : (54, 0, 0, 0, 0, 0), #Event State
        45 : (4, 0, 0, 0, 0, 3),  #High Limit
        52 : (8, 0, 0, 0, 0, 3),  #Limit Enable
        59 : (4, 0, 0, 0, 0, 3),  #Low Limit
        65 : (4, 0, 0, 0, 0, 1),  #Maximum Present Value
        69 : (4, 0, 0, 0, 0, 1),  #Minimum Present Value
        72 : (9, 0, 0, 0, 0, 3),  #Notify Type
        75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        77 : (7, 0, 0, 0, 0, 0),  #Object Name
        79 : (9, 0, 0, 0, 0, 0),  #Object Type
        81 : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85 : (4, 0, 0, 0, 0, 0),  #Present Value
        103 : (9, 0, 0, 0, 0, 1), #Reliability
        106 : (4, 0, 0, 0, 0, 1), #Resolution
        111 : (8, 0, 0, 0, 0, 0), #Status Flags
        113 : (2, 0, 0, 0, 0, 3), #Time Delay
        117 : (9, 0, 0, 0, 0, 0), #Units
        118 : (2, 0, 0, 0, 0, 1), #Update Interval
        130 : (2, 3, 1, 0, 0, 3), #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1), #Profile Name
        },
    1 : { #analog output
        0  : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        17 : (2, 0, 0, 0, 0, 3),  #Notification Class
        22 : (4, 0, 0, 0, 0, 2),  #COV Increment
        25 : (4, 0, 0, 0, 0, 3),  #Deadband
        28 : (7, 0, 0, 0, 0, 1),  #Description
        31 : (7, 0, 0, 0, 0, 1),  #Device Type
        35 : (8, 0, 0, 0, 0, 3),  #Event Enable
        36 : (54, 0, 0, 0, 0, 0), #Event State
        45 : (4, 0, 0, 0, 0, 3),  #High Limit
        52 : (8, 0, 0, 0, 0, 3),  #Limit Enable
        59 : (4, 0, 0, 0, 0, 3),  #Low Limit
        65 : (4, 0, 0, 0, 0, 1),  #Maximum Present Value
        69 : (4, 0, 0, 0, 0, 1),  #Minimum Present Value
        72 : (9, 0, 0, 0, 0, 3),  #Notify Type
        75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        77 : (7, 0, 0, 0, 0, 0),  #Object Name
        79 : (9, 0, 0, 0, 0, 0),  #Object Type
        81 : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85 : (4, 0, 0, 0, 0, 0),  #Present Value
        87 : (4, 16, 1, 0, 0, 0), #Priority Array
        103 : (9, 0, 0, 0, 0, 1), #Reliability
        104 : (4, 0, 0, 0, 0, 0), #Relinquish Default
        106 : (4, 0, 0, 0, 0, 1), #Resolution
        111 : (8, 0, 0, 0, 0, 0), #Status Flags
        113 : (2, 0, 0, 0, 0, 3), #Time Delay
        117 : (9, 0, 0, 0, 0, 0), #Units
        130 : (2, 3, 1, 0, 0, 3), #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1), #Profile Name
        },
    2 : { #analog value
        0  : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        17 : (2, 0, 0, 0, 0, 3),  #Notification Class
        22 : (4, 0, 0, 0, 0, 2),  #COV Increment
        25 : (4, 0, 0, 0, 0, 3),  #Deadband
        28 : (7, 0, 0, 0, 0, 1),  #Description
        35 : (8, 0, 0, 0, 0, 3),  #Event Enable
        36 : (54, 0, 0, 0, 0, 0), #Event State
        45 : (4, 0, 0, 0, 0, 3),  #High Limit
        52 : (8, 0, 0, 0, 0, 3),  #Limit Enable
        59 : (4, 0, 0, 0, 0, 3),  #Low Limit
        72 : (9, 0, 0, 0, 0, 3),  #Notify Type
        75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        77 : (7, 0, 0, 0, 0, 0),  #Object Name
        79 : (9, 0, 0, 0, 0, 0),  #Object Type
        81 : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85 : (4, 0, 0, 0, 0, 0),  #Present Value
        87 : (4, 16, 1, 0, 0, 1), #Priority Array
        103 : (9, 0, 0, 0, 0, 1), #Reliability
        104 : (4, 0, 0, 0, 0, 1), #Relinquish Default
        111 : (8, 0, 0, 0, 0, 0), #Status Flags
        113 : (2, 0, 0, 0, 0, 3), #Time Delay
        117 : (9, 0, 0, 0, 0, 0), #Units
        130 : (2, 3, 1, 0, 0, 3), #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1), #Profile Name
        },
    3 : { #binary input
        0  : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        4  : (7, 0, 0, 0, 0, 4),  #Active Text
        6  : (9, 0, 0, 0, 0, 3),  #Alarm Value
        15 : (2, 0, 0, 0, 0, 5),  #Change of State Count
        16 : (60, 0, 0, 0, 0, 5), #Change of State Time
        17 : (2, 0, 0, 0, 0, 3),  #Notification Class
        28 : (7, 0, 0, 0, 0, 1),  #Description
        31 : (7, 0, 0, 0, 0, 1),  #Device Type
        33 : (2, 0, 0, 0, 0, 6),  #Elapsed Active Time
        35 : (8, 0, 0, 0, 0, 3),  #Event Enable
        36 : (54, 0, 0, 0, 0, 0), #Event State
        46 : (7, 0, 0, 0, 0, 4),  #Inactive Text
        72 : (9, 0, 0, 0, 0, 0),  #Notify Type
        75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        77 : (7, 0, 0, 0, 0, 0),  #Object Name
        79 : (9, 0, 0, 0, 0, 0),  #Object Type
        81 : (1, 0, 0, 0, 0, 0),  #Out Of Service
        84 : (9, 0, 0, 0, 0, 0),  #Polarity
        85 : (9, 0, 0, 0, 0, 0),  #Present Value
        103 : (9, 0, 0, 0, 0, 1), #Reliability
        111 : (8, 0, 0, 0, 0, 0), #Status Flags
        113 : (2, 0, 0, 0, 0, 3), #Time Delay
        114 : (60, 0, 0, 0, 0, 6),#Time Of Active Time Reset
        115 : (60, 0, 0, 0, 0, 5),#Time Of State Count Reset
        130 : (2, 3, 1, 0, 0, 3), #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1), #Profile Name
        },
    4 : { #binary output
        0  : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        4  : (7, 0, 0, 0, 0, 4),  #Active Text
        15 : (2, 0, 0, 0, 0, 5),  #Change of State Count
        16 : (60, 0, 0, 0, 0, 5), #Change of State Time
        17 : (2, 0, 0, 0, 0, 3),  #Notification Class
        28 : (7, 0, 0, 0, 0, 1),  #Description
        31 : (7, 0, 0, 0, 0, 1),  #Device Type
        33 : (2, 0, 0, 0, 0, 6),  #Elapsed Active Time
        35 : (8, 0, 0, 0, 0, 3),  #Event Enable
        36 : (54, 0, 0, 0, 0, 0), #Event State
        40 : (9, 0, 0, 0, 0, 3),  #Feedback Value
        46 : (7, 0, 0, 0, 0, 4),  #Inactive Text
        66 : (2, 0, 0, 0, 0, 1),  #Minimum Off Time
        67 : (2, 0, 0, 0, 0, 1),  #Minimum On Time
        72 : (9, 0, 0, 0, 0, 0),  #Notify Type
        75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        77 : (7, 0, 0, 0, 0, 0),  #Object Name
        79 : (9, 0, 0, 0, 0, 0),  #Object Type
        81 : (1, 0, 0, 0, 0, 0),  #Out Of Service
        84 : (9, 0, 0, 0, 0, 0),  #Polarity
        85 : (9, 0, 0, 0, 0, 0),  #Present Value
        87 : (9, 16, 1, 0, 0, 0), #Priority Array
        103 : (9, 0, 0, 0, 0, 1), #Reliability
        104 : (9, 0, 0, 0, 0, 0), #Relinquish Default
        111 : (8, 0, 0, 0, 0, 0), #Status Flags
        113 : (2, 0, 0, 0, 0, 3), #Time Delay
        114 : (60, 0, 0, 0, 0, 6),#Time Of Active Time Reset
        115 : (60, 0, 0, 0, 0, 5),#Time Of State Count Reset
        130 : (2, 3, 1, 0, 0, 3), #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1), #Profile Name
        },
    5 : { #binary value
        0  : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        4  : (7, 0, 0, 0, 0, 4),  #Active Text
        6  : (9, 0, 0, 0, 0, 3),  #Alarm Value
        15 : (2, 0, 0, 0, 0, 5),  #Change of State Count
        16 : (60, 0, 0, 0, 0, 5), #Change of State Time
        17 : (2, 0, 0, 0, 0, 3),  #Notification Class
        28 : (7, 0, 0, 0, 0, 1),  #Description
        33 : (2, 0, 0, 0, 0, 6),  #Elapsed Active Time
        35 : (8, 0, 0, 0, 0, 3),  #Event Enable
        36 : (54, 0, 0, 0, 0, 0), #Event State
        46 : (7, 0, 0, 0, 0, 4),  #Inactive Text
        66 : (2, 0, 0, 0, 0, 1),  #Minimum Off Time
        67 : (2, 0, 0, 0, 0, 1),  #Minimum On Time
        72 : (9, 0, 0, 0, 0, 0),  #Notify Type
        75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        77 : (7, 0, 0, 0, 0, 0),  #Object Name
        79 : (9, 0, 0, 0, 0, 0),  #Object Type
        81 : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85 : (9, 0, 0, 0, 0, 0),  #Present Value
        87 : (9, 16, 1, 0, 0, 1), #Priority Array
        103 : (9, 0, 0, 0, 0, 1), #Reliability
        104 : (9, 0, 0, 0, 0, 1), #Relinquish Default
        111 : (8, 0, 0, 0, 0, 0), #Status Flags
        113 : (2, 0, 0, 0, 0, 3), #Time Delay
        114 : (60, 0, 0, 0, 0, 6),#Time Of Active Time Reset
        115 : (60, 0, 0, 0, 0, 5),#Time Of State Count Reset
        130 : (2, 3, 1, 0, 0, 3), #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1), #Profile Name
        },
    6 : { #calendar
        23 : (504, 0, 0, 1, 0, 0), #Date List
        28 : (7, 0, 0, 0, 0, 1),  #Description
        75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        77 : (7, 0, 0, 0, 0, 0),  #Object Name
        79 : (9, 0, 0, 0, 0, 0),  #Object Type
        85 : (9, 0, 0, 0, 0, 0),  #Present Value
        168 : (7, 0, 0, 0, 0, 1), #Profile Name
        },
    8 : { #device optional enum follows footnotes on page #169 + 10=simple optional
        5  : (201, 0, 0, 0, 0, 2), #Active VT Sessions
        10 : (2, 0, 0, 0, 0, 1),   #APDU Segment Timeout
        11 : (2, 0, 0, 0, 0, 0),   #APDU Timeout
        12 : (7, 0, 0, 0, 0, 0),   #Application Software Version
        24 : (1, 0, 0, 0, 0, 4),   #Daylight Savings Status
        28 : (7, 0, 0, 0, 0, 10),   #Description
        30 : (200, 0, 0, 1, 0, 0), #Device Address Binding
        44 : (7, 0, 0, 0, 0, 0),   #Firmware revision
        55 : (206, 0, 0, 1, 0, 10), #List of Session Keys
        56 : (10, 0, 0, 0, 0, 3),  #Local Date
        57 : (11, 0, 0, 0, 0, 3),  #Local Time
        58 : (7, 0, 0, 0, 0, 10),   #Location
        62 : (2, 0, 0, 0, 0, 0),   #Max APDU length
        63 : (2, 0, 0, 0, 0, 6),   #Max Info Frames
        64 : (2, 0, 0, 0, 0, 6),   #Max Master
        70 : (7, 0, 0, 0, 0, 0),   #Model Name
        73 : (2, 0, 0, 0, 0, 0),   #Number of APDU Retries
        75 : (50, 0, 0, 0, 0, 0),  #Object Identifier
        76 : (50, 0, 1, 0, 0, 0),  #Object List (actually an Array... go figure, 0)
        77 : (7, 0, 0, 0, 0, 0),   #Object Name
        79 : (9, 0, 0, 0, 0, 0),   #Object Type
#        95 : (2, 0, 0, 0, 0, 0),  #Protocol Conformance Class
        96 : (8, 0, 0, 0, 0, 0), #Protocol Object Types supported
        97 : (8, 0, 0, 0, 0, 0),    #Protocol Services supported
        98 : (2, 0, 0, 0, 0, 0), #Protocol Version
        107: (9, 0, 0, 0, 0, 0),    #Segmentaion Supported
        116: (202, 0, 0, 1, 0, 5), #Time Synchronization Recipients
        112: (9, 0, 0, 0, 0, 0), #System status
        119: (3, 0, 0, 0, 0, 4),    #UTC Offset
        120: (2, 0, 0, 0, 0, 0), #Vendor Indentifier
        121: (7, 0, 0, 0, 0, 0), #Vendor Name
        122: (9, 0, 0, 1, 0, 2), #VT_Classes Supported
        139: (2, 0, 0, 0, 0, 0), #Protocol Revision
        152: (204, 0, 0, 1, 0, 9), #Active COV Subscriptions
        153: (2, 0, 0, 0, 0, 8),    #Backup Failure Timeout
        154: (50, 0, 1, 0, 0, 7), #Configuration Files
        155: (2, 0, 0, 0, 0, 0), #Database Revision
        157: (205, 0, 0, 0, 0, 7), #Last Restore Time
        167: (2, 0, 0, 0, 0, 1), #Max Segments Accepted
        168: (7, 0, 0, 0, 0, 10),#Profile Name
        },
    13 : { #multistate input
        0   : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        7   : (9, 0, 0, 1, 0, 3),  #Alarm Values
        17  : (2, 0, 0, 0, 0, 3),  #Notification Class
        28  : (7, 0, 0, 0, 0, 1),  #Description
        31  : (7, 0, 0, 0, 0, 1),  #Device Type
        35  : (8, 0, 0, 0, 0, 3),  #Event Enable
        36  : (54, 0, 0, 0, 0, 0), #Event State
        39  : (2, 0, 0, 1, 0, 0),  #Fault Values
        72  : (9, 0, 0, 0, 0, 3),  #Notify Type
        74  : (2, 0, 0, 0, 0, 0),  #Number Of States
        75  : (50, 0, 0, 0, 0, 0), #Object Identifier
        77  : (7, 0, 0, 0, 0, 0),  #Object Name
        79  : (9, 0, 0, 0, 0, 0),  #Object Type
        81  : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85  : (2, 0, 0, 0, 0, 0),  #Present Value
        103 : (9, 0, 0, 0, 0, 2),  #Reliability
        110 : (7, 0, 0, 1, 0, 0),  #State Text
        111 : (8, 0, 0, 0, 0, 0),#Status Flags
        113 : (2, 0, 0, 0, 0, 3),  #Time Delay
        130 : (2, 3, 1, 0, 0, 3),  #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1),  #Profile Name
        },
    14 : { #multistate output
        0   : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        17  : (2, 0, 0, 0, 0, 3),  #Notification Class
        28  : (7, 0, 0, 0, 0, 1),  #Description
        31  : (7, 0, 0, 0, 0, 1),  #Device Type
        35  : (8, 0, 0, 0, 0, 3),  #Event Enable
        36  : (54, 0, 0, 0, 0, 0), #Event State
        40  : (2, 0, 0, 1, 0, 3),  #Feedback
        72  : (9, 0, 0, 0, 0, 3),  #Notify Type
        74  : (2, 0, 0, 0, 0, 0),  #Number Of States
        75  : (50, 0, 0, 0, 0, 0), #Object Identifier
        77  : (7, 0, 0, 0, 0, 0),  #Object Name
        79  : (9, 0, 0, 0, 0, 0),  #Object Type
        81  : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85  : (2, 0, 0, 0, 0, 0),  #Present Value
        87  : (2, 16, 1, 0, 0, 0), #Priority Array
        103 : (9, 0, 0, 0, 0, 1),  #Reliability
        104 : (2, 0, 0, 0, 0, 0),  #Relinquish Default
        110 : (7, 0, 0, 1, 0, 1),  #State Text
        111 : (8, 0, 0, 0, 0, 0),#Status Flags
        113 : (2, 0, 0, 0, 0, 3),  #Time Delay
        130 : (2, 3, 1, 0, 0, 3),  #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 0),  #Profile Name
        },
    19 : { #multistate value
        0   : (8, 0, 0, 0, 0, 3),  #Acked Transistions
        7   : (9, 0, 0, 1, 0, 3),  #Alarm Values
        17  : (2, 0, 0, 0, 0, 3),  #Notification Class
        28  : (7, 0, 0, 0, 0, 1),  #Description
        35  : (8, 0, 0, 0, 0, 3),  #Event Enable
        36  : (54, 0, 0, 0, 0, 0), #Event State
        39  : (2, 0, 0, 1, 0, 3),  #Fault Values
        72  : (9, 0, 0, 0, 0, 3),  #Notify Type
        74  : (2, 0, 0, 0, 0, 0),  #Number Of States
        75  : (50, 0, 0, 0, 0, 0), #Object Identifier
        77  : (7, 0, 0, 0, 0, 0),  #Object Name
        79  : (9, 0, 0, 0, 0, 0),  #Object Type
        81  : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85  : (2, 0, 0, 0, 0, 0),  #Present Value
        87  : (2, 16, 1, 0, 0, 1), #Priority Array
        103 : (9, 0, 0, 0, 0, 3),  #Reliability
        104 : (2, 0, 0, 0, 0, 1),  #Relinquish Default
        110 : (7, 0, 0, 1, 0, 1),  #State Text
        111 : (8, 0, 0, 0, 0, 0),  #Status Flags
        113 : (2, 0, 0, 0, 0, 3),  #Time Delay
        130 : (2, 3, 1, 0, 0, 3),  #Event Time Stamps
        168 : (7, 0, 0, 0, 0, 1),  #Profile Name
        },
    17 : { #schedule
        28  : (7, 0, 0, 0, 0, 1),  #Description
        32  : (61, 0, 0, 0, 0, 0), #Effective_Period
        38  : (502, 0, 1, 0, 0, 1), #Exception_Schedule
        54  : (503, 0, 0, 1, 0, 0), #List_Of_Device_Object_Property_References
        75  : (50, 0, 0, 0, 0, 0), #Object Identifier
        77  : (7, 0, 0, 0, 0, 0),  #Object Name
        79  : (9, 0, 0, 0, 0, 0),  #Object Type
        81  : (1, 0, 0, 0, 0, 0),  #Out Of Service
        85  : (-1, 0, 0, 0, 0, 0),  #Present Value
        88  : (2, 0, 0, 0, 0, 0), #Priority_For_Writing
        103 : (9, 0, 0, 0, 0, 3),  #Reliability
        111 : (8, 0, 0, 0, 0, 0),  #Status Flags
        123 : (500, 7, 1, 0, 0, 1), #Weekly_Schedule
        168 : (7, 0, 0, 0, 0, 1),  #Profile Name
        174 : (-1, 0, 0, 0, 0, 0), #Schedule_Default
        },
    # 20 : { #trendlog
        # 0 : (8, 0, 0, 0, 0, 3), # Acked_Transitions BACnetEventTransitionBits O3
        # 17 : (2, 0, 0, 0, 0, 3), # Notification_Class Unsigned O3
        # 28 : (7, 0, 0, 0, 0, 1),  #Description
        # 35 : (8, 0, 0, 0, 0, 3), # Event_Enable BACnetEventTransitionBits O3
        # 36 : (?, 0, 0, 0, 0, 0), # Event_State BACnetEventState R
        # 72 : (?, 0, 0, 0, 0, 3), # Notify_Type BACnetNotifyType O3
        # 75 : (50, 0, 0, 0, 0, 0), #Object Identifier
        # 77 : (7, 0, 0, 0, 0, 0),  #Object Name
        # 79 : (9, 0, 0, 0, 0, 0),  #Object Type
        # 126 : (2, 0, 0, 0, 0, 0), # Buffer_Size Unsigned32 R
        # 127 : (?, 0, 0, 0, 0, 1), # Client_COV_Increment BACnetClientCOV O
        # 128 : (2, 0, 0, 0, 0, 1), # COV_Resubscription_Interval Unsigned O
        # 130 : (?, 3, 1, 0, 0, 3), # Event_Time_Stamps BACnetARRAY[3] of BACnetTimeStamp O3
        # 131 : (?, 0, 0, 1, 0, 0), # Log_Buffer List of BACnetLogRecord R
        # 132 : (503, 0, 0, 0, 0, 1), # Log_DeviceObjectProperty BACnetDeviceObjectPropertyReference O1
        # 133 : (1, 0, 0, 0, 0, 0), # Log_Enable BOOLEAN W
        # 134 : (2, 0, 0, 0, 0, 2), # Log_Interval Unsigned O1,2
        # 137 : (2, 0, 0, 0, 0, 3), # Notification_Threshold Unsigned32 O3
        # 140 : (2, 0, 0, 0, 0, 3), # Records_Since_Notification Unsigned32 O3
        # 141 : (2, 0, 0, 0, 0, 0), # Record_Count Unsigned32 W
        # 142 : (60, 0, 0, 0, 0, 2), # Start_Time BACnetDateTime O1,2
        # 143 : (60, 0, 0, 0, 0, 2), # Stop_Time BACnetDateTime O1,2
        # 144 : (1, 0, 0, 0, 0, 0), # Stop_When_Full BOOLEAN R
        # 145 : (2, 0, 0, 0, 0, 0), # Total_Record_Count Unsigned32 R
        # 168 : (7, 0, 0, 0, 0, 1), #Profile Name
        # 173 : (2, 0, 0, 0, 0, 3), # Last_Notify_Record Unsigned32 O3
        # },
}
# object_property_node_id_data = {
    # 0 : {  'id': '521',
        # },
    # 1 : {  'id': '563',
        # },
    # 2 : {  'id': '1081',
        # },
    # 3 : {  'id': '593',
        # },
    # 4 : {  'id': '594',
        # },
    # 5 : {  'id': '1082',
        # },
    # 6 : {  'id': None,
        # },
    # 8 : {  'id': None,
        # },
    # 13 : {  'id': None,
        # },
    # 14 : {  'id': None,
        # },
    # 19 : {  'id': None,
        # },
# }
#
# format: {property id:name string}
#
property_ids = {
        0 : 'Acked Transistions',
        1 : 'Ack Required',
        2 : 'Action',
        3 : 'Action Text',
        4 : 'Active Text',
        5 : 'Active VT Sessions',
        6 : 'Alarm Value',
        7 : 'Alarm Values',
        8 : 'All',
        9 : 'All Writes Successful',
        10 : 'APDU Segment Timeout',
        11 : 'APDU Timeout',
        12 : 'Application Software Revision',
        13 : 'Archive',
        14 : 'Bias',
        15 : 'Change Of State Count',
        16 : 'Change Of State Time',
        17 : 'Notification Class',
        #removed properties
        19 : 'Controlled Variable Reference',
        20 : 'Controlled Variable Units',
        21 : 'Controlled Variable Value',
        22 : 'COV Increment',
        23 : 'Date List',
        24 : 'Daylight Savings Status',
        25 : 'Deadband',
        26 : 'Derivative Constant',
        27 : 'Derivative Constant Units',
        28 : 'Description',
        29 : 'Description Of Halt',
        30 : 'Device Address Binding',
        31 : 'Device Type',
        32 : 'Effective Period',
        33 : 'Elapsed Active Time',
        34 : 'Error Limit',
        35 : 'Event Enable',
        36 : 'Event State',
        37 : 'Event Type',
        38 : 'Exception Schedule',
        39 : 'Fault Values',
        40 : 'Feedback Value',
        41 : 'File Access Method',
        42 : 'File Size',
        43 : 'File Type',
        44 : 'Firmware Revision',
        45 : 'High Limit',
        46 : 'Inactive Text',
        47 : 'In Process',
        48 : 'InstanceOf',
        49 : 'Integral Constant',
        50 : 'Integral Constant Units',
        51 : 'Issue Confirmed Notifications',
        52 : 'Limit Enable',
        53 : 'List Of Group Members',
        54 : 'List Of Object Property References',
        55 : 'List of Session Keys',
        56 : 'Local Date',
        57 : 'Local Time',
        58 : 'Location',
        59 : 'Low Limit',
        60 : 'Manipulated Variable Reference',
        61 : 'Maximum Output',
        62 : 'Max Message Length Supported',
        63 : 'Max Info Frames',
        64 : 'Max Master',
        65 : 'Maximum Present Value',
        66 : 'Minimum Off Time',
        67 : 'Minimum On Time',
        68 : 'Minimum Output',
        69 : 'Minimum Present Value',
        70 : 'Model Name',
        71 : 'Modification Date',
        72 : 'Notify Type',
        73 : 'Number of APDU Retries',
        74 : 'Number Of States',
        75 : 'Object Identifier',
        76 : 'Object List',
        77 : 'Object Name',
        78 : 'Object Property Reference',
        79 : 'Object Type',
        80 : 'Optional',
        81 : 'Out Of Service',
        82 : 'Output Units',
        #see event parameters
        84 : 'Polarity',
        85 : 'Present Value',
        86 : 'Priority',
        87 : 'Priority Array',
        88 : 'Priority For Writing',
        89 : 'Process Identifier',
        90 : 'Priority Array',
        91 : 'Program Location',
        92 : 'Program State',
        93 : 'Proportional Constant',
        94 : 'Proportional Constant Units',
        95 : 'Protocol Conformance Class',
        96 : 'Protocol Object Types Supported',
        97 : 'Protocol Services Supported',
        98 : 'Protocol Version',
        99 : 'Read Only',
        100 : 'Reason For Halt',
        101 : 'Recipient',
        102 : 'Recipient List',
        103 : 'Reliability',
        104 : 'Relinquish Default',
        105 : 'Required',
        106 : 'Resolution',
        107 : 'Segmentation Supported',
        108 : 'Setpoint',
        109 : 'Setpoint Reference',
        110 : 'State Text',
        111 : 'Status Flags',
        112 : 'Mode: System Status',
        113 : 'Time Delay',
        114 : 'Time of Active Time Reset',
        115 : 'Time of State Count Reset',
        116 : 'Time Synchronization Recipients',
        117 : 'Units',
        118 : 'Update Interval',
        119 : 'UTC Offset',
        120 : 'BACnet Vendor ID',
        121 : 'Vendor Name',
        122 : 'VT Classes Supported',
        123 : 'Weekly Schedule',
        124 : 'Attempted Values',
        125 : 'Average Value',
        126 : 'Buffer Size',
        127 : 'Client COV Increment',
        128 : 'COV Resubscription Interval',
        129 : 'Current Notify Time',
        130 : 'Event Time Stamps',
        131 : 'Log Buffer',
        132 : 'Log Device Object Property',
        133 : 'Log Enable',
        134 : 'Log Interval',
        135 : 'Maximum Value',
        136 : 'Minimum Value',
        137 : 'Notification Threshold',
        138 : 'Previous Notify Time',
        139 : 'Protocol Revision',
        140 : 'Records Since Notification',
        141 : 'Record Count',
        142 : 'Start Time',
        143 : 'Stop Time',
        144 : 'Stop When Full',
        145 : 'Total Record Count',
        146 : 'Valid Samples',
        147 : 'Window Interval',
        148 : 'Window Samples',
        149 : 'Maximum Value Timestamp',
        150 : 'Minimum Value Timestamp',
        151 : 'Variance Value',
        152 : 'Active COV Subscriptions',
        153 : 'Backup Failure Timeout',
        154 : 'Configuration Files',
        155 : 'Database Revision',
        156 : 'Direct Reading',
        157 : 'Last Restore Time',
        158 : 'Maintenance Required',
        159 : 'Member Of',
        160 : 'Mode',
        161 : 'Operation Expected',
        162 : 'Setting',
        163 : 'Silenced',
        164 : 'Tracking Value',
        165 : 'Zone Members',
        166 : 'Life Safety Alarm Values',
        167 : 'Max Segments Accepted',
        168 : 'Profile Name',
        169 : 'Auto Slave Discovery',
        170 : 'Manual Slave Address Binding',
        171 : 'Slave Address Binding',
        172 : 'Slave Proxy Enable',
        173 : 'Last Notify Time',
        174 : 'Schedule Default',
        175 : 'Accepted Modes',
        176 : 'Adjust Value',
        177 : 'Count',
        178 : 'Count Before Change',
        179 : 'Count Change Time',
        180 : 'Cov Period',
        181 : 'Input Reference',
        182 : 'Limit Monitoring Interval',
        183 : 'Logging Device',
        184 : 'Logging Record',
        185 : 'Prescale',
        186 : 'Pulse Rate',
        187 : 'Scale',
        188 : 'Scale Factor',
        189 : 'Update Time',
        190 : 'Value Before Change',
        191 : 'Value Set',
        192 : 'Value Change Time', 
}
# (node_def_id, server_attribute, server_conversion, server_default)
# from mpx import properties as mp
# from mpx.lib.configure import REQUIRED

# property_node_data = {
        # 4 : (None, 'active_text',str, REQUIRED),
        # 10 : ('549', 'timeout', int, REQUIRED),
        # 11 : ('550', 'timeout', int, REQUIRED),
        # 12 : ('533', 'sw_version', str, mp.RELEASE_VERSION),
        # 16 : (None, None, int, REQUIRED),
        # 23 : (None, None, int, REQUIRED),
        # 28 : (None, 'description',str, REQUIRED),
        # 31 : (None, None , int, REQUIRED),
        # 32 : (None, None , int, REQUIRED),
        # 36 : ('557', 'event_state', int, REQUIRED),
        # 38 : (None, None , int, REQUIRED),
        # 44 : ('532', 'revision',str, REQUIRED), #_MoeVersion
        # 46 : (None, 'inactive_text',str, REQUIRED),
        # 56 : (None, None, int, REQUIRED),
        # 57 : (None, None, int, REQUIRED),
        # 62 : ('541', 'max_length', int, REQUIRED),
        # 65 : (None, None, int, REQUIRED),
        # 66 : (None, None, int, REQUIRED),
        # 67 : (None, None, int, REQUIRED),
        # 69 : (None, None, int, REQUIRED),
        # 70 : (None, None, str, REQUIRED),
        # 73 : ('551', 'retries', int, REQUIRED), #'Number of APDU Retries',
        # 74 : (None, None, int, REQUIRED),
        # 75 : ('523', 'instance', int, REQUIRED), #'Object Identifier',
        # 76 : ('540', None, int, REQUIRED), #'Object List',
        # 77 : ('524', 'obj_name', str, REQUIRED), #'Object Name',
        # 79 : ('527', 'obj_type', int, REQUIRED), #'Object Type',
        # 81 : ('559', 'service', int, REQUIRED), #'Out Of Service',
        # 84 : ('595', 'polarity', int, REQUIRED), #'Polarity',
        # 85 : ('522', 'value', float, REQUIRED), #'Present Value', 799
        # 86 : ('798', 'priority', int, 16), #'priority',
        # 87 : (None, None, int, REQUIRED), #'Priority Array',
        # 91 : (None, None, int, REQUIRED), #'Program Location',
        # 92 : (None, None, int, REQUIRED), #'Program State',
        # 95 : ('537', None, int, REQUIRED), #'Protocol Conformance Class',
        # 96 : ('539', None, None, (1,1,0,1,1,0,0,0,\
            # 1,0,0,0,0,0,0,0,\
            # 0,0,0,0,0,0,0)), #'Protocol Object Types Supported',
        # 97 : ('538', 'services', None, (0,0,0,0,0,0,0,0,\
            # 0,0,0,0,1,0,1,1,\
            # 0,0,1,0,0,0,0,0,\
            # 0,0,1,0,0,0,0,0,\
            # 0,0,1,0,0,0,0,0)), #'Protocol Services Supported',
        # 98 : ('536', None, int, 1), #'Protocol Version',
        # 103 : (None, None, int, REQUIRED), #'Reliability',
        # 104 : ('562', 'relinquish', float, REQUIRED), #'Relinquish Default',
        # 107 : ('542', 'segmentation', int, REQUIRED), #'Segmentation Supported',
        # 108 : ('34c1bdcc-68f6-45b0-9d67-4d4bd6725888', 'setpoint', float, REQUIRED), #'Setpoint',
        # 110 : (None, 'state_text',str, REQUIRED), #'State Text',
        # 111 : ('556', 'status_flags', None, (0,0,0,0)), #'Status Flags',
        # 112 : ('528', 'status', int, REQUIRED), #'Mode: System Status',
        # 117 : ('560', 'units', int, REQUIRED), #'Units',
        # 120 : ('530', 'vendor', int, REQUIRED), #'BACnet Vendor ID',
        # 121 : ('529', 'vendor',str, REQUIRED), #'Vendor Name',
        # 123 : (None, None, None, None), #'Weekly Schedule',
# }
#
BACnetObjectTypeStr = est[400]
#
# def opd2csv():
    # answer = []
    # objs = object_property_data.keys()[:]
    # objs.sort()
    # pids = property_ids.keys()[:]
    # pids.sort()
    # s = 'id,property'
    # for i in objs:
        # s += ',' + BACnetObjectTypeStr[i]
    # answer.append(s)
    # s = ','
    # for i in objs:
        # s += ',' + str(i)
    # answer.append(s)
    # for pid in pids:
        # s = str(pid) + ',' + property_ids[pid]
        # for o in objs:
            # s += ','
            # if pid in object_property_data[o].keys():
                # s += '1'
        # answer.append(s)
    # import string
    # return string.join(answer,'\n')

# def server_opd2csv():
    # answer = []
    # objs = object_property_data.keys()[:]
    # objs.sort()
    # pids = property_node_data.keys()[:]
    # pids.sort()
    # s = 'id,property'
    # for i in objs:
        # s += ',' + BACnetObjectTypeStr[i]
    # answer.append(s)
    # s = ','
    # for i in objs:
        # s += ',' + str(i)
    # answer.append(s)
    # for pid in pids:
        # s = str(pid) + ',' + property_ids[pid]
        # for o in objs:
            # s += ','
            # if pid in object_property_data[o].keys():
                # s += '1'
        # answer.append(s)
    # import string
    # return string.join(answer,'\n')

