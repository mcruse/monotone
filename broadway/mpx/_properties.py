"""
Copyright (C) 2002 2003 2004 2005 2006 2009 2010 2011 Cisco Systems

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
#  Central Broadway property repository.
#
#  A property is a name=value pair.  Each property can have
#  an associated default value.
#
#  Any property can be overriden by setting an environment 
#  variable named BROADWAY_propertyname where 'propertyname'
#  is a defined property.   For example, if an option was called
#  'debug' you could override it's value with an environment var
#  called 'BROADWAY_debug'.
#
#  Each option is case sensitive
#
#  Each property is added as an attribute to the class, so they can 
#  be accessed like normal class attributes.   For example, you can 
#  create a new property with properties.set('newattr','value','the
#  description') all access it with properties.newattr.  There are also
#  get and set methods.
#
#  Access the properties through the properties function which
#  returns a singleton instance of Properties. 
#
#  @todo There is no writing of properties back out.   Do we write out the 
#         variables that have been overridden?
# @fixme Indent as per coding standards (4).

import cPickle
import imp
import os
import types

from _const import UNKNOWN
from _hwinfo import moe_hardware_class
from _hwinfo import moe_hardware_codename
from _hwinfo import moe_hardware_id
from _hwinfo import oem_hardware_id
from _hwinfo import oem_serial_number
from _moeinfo import moe_version

PACKAGES=[]

##
# @fixme Merge logic into moab?
def _get_compound_version():
    f = None
    try:
        import mpx
        mpx__init__file = mpx.__file__
        mpx__init__file = os.path.realpath(mpx__init__file)
        mpx_dir = os.path.dirname(mpx__init__file)
        ROOT = os.path.dirname(mpx_dir)
        if ROOT[-4:].lower() == '.zip':
            ROOT=os.path.dirname(ROOT)
        version_file = os.path.join(ROOT, "BROADWAY")
        f = open(version_file, "r")
        version = f.readline().split('\n')[0]
        f.close()
        return version
    except:
        if f: f.close()
    return properties.UNKNOWN

##
# @property RELEASE_VERSION
def _get_release_version():
    compound_version = properties.COMPOUND_VERSION
    release_version = ''
    # Assumes that the compound version is INTEGERS.TEXT.INTEGER, where:
    #     INTEGERS in [0-9\.]* # Integers separated by periods.
    #     TEXT     in .*       # Any characters.
    #     INTEGER  in [0-9]*   # An integer.
    try:
        components = compound_version.split('.')
        # The last entity is the build number in a well formed
        # COMPOUND_VERSION, toss it.
        components.pop()
        # Get the major number (everything up to TEXT).
        release_version = "%s" % (int(components.pop(0)))
        # Add on the minor, revision, sub-revision, etc...
        for component in components:
            release_version = "%s.%s" % (release_version, int(component))
    except:
        if release_version is None:
            release_version = properties.UNKNOWN
    return release_version

##
# @property RELEASE_BUILD The build number of this release.
def _get_release_build():
    compound_version = properties.COMPOUND_VERSION
    # Assumes that the compound version is INTEGERS.TEXT.INTEGER, where:
    #     INTEGERS in [0-9\.]* # Integers separated by periods.
    #     TEXT     in .*       # Any characters.
    #     INTEGER  in [0-9]*   # An integer.
    try:
        # The last entity is the build number in a well formed
        # COMPOUND_VERSION.
        release_build = "%s" % int(compound_version.split('.')[-1])
    except:
        release_build = properties.UNKNOWN
    return release_build

_COMPOUND_TEXT = {
    # @constant Well, at least it was intended for QA.
    "build":"release",
    # @constant Something from a development stream.
    "dev":"development",
    }

##
# @property RELEASE_TYPE The build number of this release.
# @value "release"
# @value "development"
# @value "unofficial(TEXT)"
def _get_release_type():
    compound_version = properties.COMPOUND_VERSION
    # Assumes that the compound version is INTEGERS.TEXT.INTEGER, where:
    #     INTEGERS in [0-9\.]* # Integers separated by periods.
    #     TEXT     in .*       # Any characters.
    #     INTEGER  in [0-9]*   # An integer.
    try:
        components = compound_version.split('.')
        # The last component is the build number in a well formed
        # COMPOUND_VERSION, toss it.
        try:
            int(components[-1])
            components.pop()
        except:
            pass
        # Toss the initial INTEGERS. Once we hit some text
        # we will throw and exception and then we can get the
        # release type from the _COMPOUND_TEXT
        while int(components[0]) > -1:
            components.pop(0)
    except:
        # Whatever is left is TEXT.
        release_text = components.pop(0)
        while components:
            release_text = "%s.%s" % (release_text, components.pop(0))
        if _COMPOUND_TEXT.has_key(release_text):
            return _COMPOUND_TEXT[release_text]
        # Not a none compound text string.
        return "unofficial(%s)" % release_text
    return properties.UNKNOWN

_RELEASE_IS_OFFICIAL = {
    # @constant
    "release":1,
    # @constant
    "development":0,
    }

##
# @property RELEASE
def _get_release():
    unknown = properties.UNKNOWN
    release_version = properties.RELEASE_VERSION
    release_build = properties.RELEASE_BUILD
    release_type = properties.RELEASE_TYPE
    if (release_version is unknown or
        release_build is unknown or
        release_type is unknown):
        return "%s: %s" % (unknown, properties.COMPOUND_VERSION)
    if _RELEASE_IS_OFFICIAL.has_key(release_type):
        if _RELEASE_IS_OFFICIAL[release_type]:
            return "release %s, build %s" % (release_version, release_build)
    return "%s: %s build %s" % (release_type, release_version, release_build)

def _format_to_boxwrap(initial_position, left_position, message,
                       indent_bar='', left_bar = '', wrap_at=78):
    if initial_position != left_position:
        result = indent_bar
    else:
        result = left_bar
    initial_position += len(result)
    current_position = initial_position
    words = message.split()
    while words:
        word = words.pop(0) + ' '
        next_position = current_position + len(word)
        if next_position >= wrap_at and current_position != initial_position:
            result += ('\n' + left_position*' ' + left_bar)
            current_position = left_position + len(left_bar)
            initial_position = current_position
        else:
            current_position = next_position
        result += word
    return result, current_position

def _format_as_columns(start_positions,
                       column_values,
                       column_bars=None, wrap_at=78):
    if column_bars is None:
        column_bars = (('',''),)*len(start_positions)
    if len(start_positions) != len(column_values) != len(column_bars):
        raise "Must have the same number of start_positions, " + \
              "column_values and column_bars"
    result = ''
    current_position = 0
    for i in range(0, len(start_positions)):
        this_column = start_positions[i]
        if i >= len(start_positions)-1:
            next_column = wrap_at
        else:
            next_column = start_positions[i+1]
        message = column_values[i]
        if current_position < this_column:
            result += (this_column - current_position)*' '
            current_position = this_column
        elif current_position > next_column:
            result += ('\n' + this_column*' ')
            current_position = this_column
        temp_result, current_position = _format_to_boxwrap(current_position,
                                                           this_column,
                                                           message,
                                                           column_bars[i][0],
                                                           column_bars[i][1],
                                                           next_column)
        result += temp_result
    result += '\n'
    return result

##
# @fixme split into a generic moab.Properties class, and then implement
#        a moab.properties singleton and an mpx.propoerties singleton
#        with reasonable defaults.  (as well as a MOAB and BROADWAY (MPX?)
#        prefix).
class Properties:
  _bool_dict = {'no':0,'yes':1,
                'n':0,'y':1,
                'false':0,'true':1,
                'off':0, 'on':1}
  def as_boolean(self, value):
      if type(value) == types.StringType:
          _value = value.lower()
          if self._bool_dict.has_key(_value):
              return self._bool_dict[_value]
      try:
          _value = float(value)
          _value = int(_value)
      except TypeError:
          raise TypeError('as_boolean() needs a string or numeric argument.')
      except ValueError:
          raise ValueError('invalid value for as_boolean(): %r' % value)
      if _value in (0,1):
          return _value
      raise ValueError('invalid value for as_boolean(): %r' % value)
  def as_int(self, value):
      try:
          _value = float(value)
          _value = int(_value)
      except TypeError:
          raise TypeError('as_int() needs a string or numeric argument.')
      except ValueError:
          raise ValueError('invalid value for as_int(): %r' % value)
      return _value
  def as_float(self, value):
      try:
          _value = float(value)
      except TypeError:
          raise TypeError('as_float() needs a string or numeric argument.')
      except ValueError:
          raise ValueError('invalid value for as_float(): %r' % value)
      return _value
  ##
  # Create a new Properties object and read
  #  properties from named file.  If file is not
  #  specified then search for 'broadway.properties' 
  #  in the current directory.
  # @param file A file object or the path to a file to read the properties.
  # @fixme Constants should be immutable after defining.
  # @fixme Merge self._properties_desc, self._deferred and self._constants
  #        into a single dictionary of helper objects (they could even
  #        support calculated values that handle annoying locking issues
  #        for the provider).
  def reload(self, file=None):
      # Used to cacluate the ROOT directory of this package.
      import mpx
      mpx__init__file = mpx.__file__
      mpx__init__file = os.path.realpath(mpx__init__file)
      mpx_dir = os.path.dirname(mpx__init__file)
      ROOT = os.path.dirname(mpx_dir)
      if ROOT[-4:].lower() == '.zip':
          ROOT=os.path.dirname(ROOT)
      #
      self._properties_desc = {}
      self._constants = {}
      self._deferred = {}
      if file is None and hasattr(self,'_file_name'):
          file = self._file_name
      if type(file) == types.StringType:
          self._file_name = file
      elif hasattr(file, 'name'):
          self._file_name = file.name
      else:
          self._file_name = file
      self.define_constant('ROOT', ROOT,
                           'The root directory of the framework installation.')
      self._define_defaults()		# Define the default "core" properties.
      try:				# Create the properties from
          self._load_properties(file)	# the properties file.
      except:
          # @fixme "Defer log" the utter and complete failure...
          pass
      self._define_constants()		# Constants override all other previous
                                        # values and are immutable.
      self._load_from_packages()
      return
  def __init__(self, file):
      self.reload(file)
      return
  def __repr__(self):
      s = ''
      names = self._properties_desc.keys()
      names.sort()
      for name in names:
          s += '%s=%s\n' % (name,getattr(self,name))
      return s  
  def __str__(self):
      result = ''
      names = self._properties_desc.keys()
      names.sort()
      for name in names:
          description = self._properties_desc[name]
          if description:
              comment = '# '
          else:
              comment = ''
          result += _format_as_columns((0, 35),
                                       (name + '=' + repr(getattr(self,name)),
                                        description),
                                       (('',''), (comment, '# ')))
      return result
  def _load_from_packages(self):
      import _mpxhooks          # A "namespace" with no reentrancy issues.
      _mpxhooks.properties=self
      pickled_packages = os.path.join(self.INFO_DIR,
                                      'packages.db')
      try:
          installed_packages=cPickle.load(open(pickled_packages,'r'))
          global PACKAGES
          PACKAGES.extend(installed_packages)
          for package in installed_packages:
              properties_pyc=package.get('properties',None)
              if properties_pyc:
                  properties_pyc = os.path.abspath(
                      os.path.join(self.ROOT,properties_pyc)
                      )
                  imp.load_module('package_properties',open(properties_pyc),
                                  '', ('pyc','r',imp.PY_COMPILED))
      except:
          if _mpxhooks.load_properties_warning:
              import warnings
              warnings.warn(
                  "Application not installed,"
                  " can't load package based properties."
                  )
  ##
  # @fixme Provide a default "coerce" to a dict?
  def as_dictionary(self):
      dictionary = {}
      for name in self._properties_desc.keys():
          dictionary[name] = getattr(self,name)
      return dictionary
  ##
  # @note Constants and calculated (deferred) values are not included.
  # @fixme Provide a default "coerce" to a dict?
  def as_environment(self):
      environment = {}
      for name in self._properties_desc.keys():
          if self._constants.has_key(name) or self._deferred.has_key(name):
              # Skip it!
              continue
          environment["BROADWAY_%s" % name] = getattr(self,name)
      return environment
  ##
  # Limitted reverse compatibility.  I've temporarily disabled the reload
  # which, if reimplemented should be a reload method.
  # @depricated
  def __call__(self):
      return self
  ##
  # Find the value for the requested option. 
  #  @return The value of the property or
  #          the default value
  #  @param name The option name (ignore case)
  #  @param default The value to return if property
  #                 is not found
  #
  def get(self, name, default=None):
      if not hasattr(self, name):
          result = os.getenv('BROADWAY_'+name)
          if result is not None:
              setattr(self, name, result)
              return result
      return getattr(self, name, default)
  def get_boolean(self, property_name, default=None):
      return self.as_boolean(self.get(property_name, default))
  def get_float(self, property_name, default=None):
      return self.as_float(self.get(property_name, default))
  def get_int(self, property_name, default=None):
      return self.as_int(self.get(property_name, default))
  def _constant_message(self, name):
      return "%s is a constant and therefore can not be set." % name
  ##
  # Set or create the option with value
  # @name The name of property.
  # @value The string value to set option to.
  # @description A description of this attribute.
  # @exception TypeError Raised if the named property is a constant or
  #                      the value or name is not a string.
  def set(self, name, value, description='',_force=0):
      if self._constants.has_key(name):
          if not _force:
              raise TypeError, self._constant_message(name)
          else:
              pass # deferred log of forcing an existing constant.
      if not (type(name) == type(value) == type(description) ==
              types.StringType):
          if type(name) != types.StringType:
              parameter = "name"
          elif type(value) != types.StringType:
              parameter = "value"
          elif type(description) != types.StringType:
              parameter = "description"
          else:
              parameter = properties.UNKNOWN
          raise TypeError, \
                "The %s parameter must be a string." % parameter
      setattr(self,name,value)
      if description:
          self._properties_desc[name] = description
      elif not self._properties_desc.has_key(name):
          self._properties_desc[name] = description
          
  def __setattr__(self, name, value):
      _dict = self.__dict__
      if _dict.has_key('_constants'):
          _constants = _dict['_constants']
          if _constants.has_key(name):
              if _dict.has_key('_deferred'):
                  _deferred = _dict['_deferred']
                  if _deferred.has_key(name):
                      _dict[name] = value
                      return
              raise TypeError, self._constant_message(name)
      _dict[name] = value
      return
  def __getattr__(self, name):
      if self.__dict__.has_key(name):
          result = os.getenv('BROADWAY_'+name)
          if result is not None:
              self.__dict__[name] = result
              return result
      if self._deferred.has_key(name):
          func = self._deferred[name]
          self.set(name,func(),'',1)
          del self._deferred[name]
          return self.__dict__[name]
      raise AttributeError("Property instance has no attribute %s"
                           % repr(name))
  ##
  # Can be used to define a property at any time, without
  # overriding an existing value.  This is useful for modules
  # that want to add new properties.
  def define_default(self,name, value, description=''):
      if not self._properties_desc.has_key(name):
          # The property does not exist.
          result = os.getenv('BROADWAY_'+name)
          if result is not None:
              # Create it using the environment override.
              setattr(self, name, result)
          else:
              # Create it with a default value.
              setattr(self,name,value)
          self._properties_desc[name] = description
      else:
          # The property already exists, just update it's
          # description.
          self._properties_desc[name] = description
  ##
  # Used to define "readonly" properties that can not be changed after
  # they are defined.
  # @fixme Really make them constant.
  def define_constant(self, name, value, description):
      constant_reminder = 'NOTE: This is a constant'
      if description:
          description = "%s %s" % (description, constant_reminder)
      else:
          description = constant_reminder
      self.set(name, value, description + ' ', 1)
      self._constants[name] = self
  ##
  # Defines a constant that gets its value from a callable object.  The
  # constant's value is lazily initialized the first time it is referrenced.
  # The callable object is only invoked once.
  def deferred_constant(self, name, func, description):
      constant_reminder = 'NOTE: This is a constant'
      if description:
          description = "%s %s" % (description, constant_reminder)
      else:
          description = constant_reminder
      self._properties_desc[name] = description
      self._deferred[name] = func
      self._constants[name] = self
  ##
  # Return the description of named attribute
  #  @param name The name of the attribute 
  #  @return The description of the attribute or empty string
  #
  def get_description(self, name):
      if self.properties_desc.has_key(name):
          return self._properties_desc[name]
      return ''

  ##
  # @return The properties currently defined
  def get_properties(self):
      names = self._properties_desc.keys()
      names.sort()
      return names
  ##
  # Remove the option from the cache
  #  @param name The name of the option to remove
  #
  def remove(self, name):
      if hasattr(self, name):
          del self.name

  ##
  # Write the current properties to a file.
  # @param file Specifies the file to write the properties.  The
  #             <code>file</code> parameter can be either a string
  #             that is the filename to write to, or a Python file
  #             (like) object.
  # @fixme Implement, skipping constants.
  def write(self,file):
      pass

  ##
  # Define the "core" immutable propertes needed to bootstrap framework.
  # @note Packages and modules can lazily create constants when they
  #       are imported by calling mpx.properties.define_constant(...).
  # @see define_default
  def _define_constants(self):
      self.define_constant('PROPERTIES',str(self._file_name),
                           'The file used in loading these properties.')
      # @constant DO NOT CHANGE!
      self.define_constant('UNKNOWN',UNKNOWN,
                           "The value returned when a property's value " +
                           "can not be determined.")
      # @fixme Should propably be loaded later in mpx.lib
      self.deferred_constant('SERIAL_NUMBER', oem_serial_number,
                             'The real serial number, when possible.')
      # @fixme Should propably be loaded later in mpx.lib
      self.deferred_constant('HARDWARE_CLASS', moe_hardware_class,
                             'The class of hardware, when possible.')
      self.deferred_constant('HARDWARE_MODEL', moe_hardware_id,
                             'MFW product ID of the hardware, when possible.')
      self.deferred_constant('HARDWARE_PLATFORM', oem_hardware_id,
                             'OEM NAME and ID for the base hardware.')
      self.deferred_constant('HARDWARE_CODENAME', moe_hardware_codename,
                             'OEM NAME and ID for the base hardware.')
      # @fixme Should propably be loaded later in mpx.lib
      self.deferred_constant('COMPOUND_VERSION', _get_compound_version,
                             "The Framework's internal build version.")
      self.deferred_constant('RELEASE_VERSION', _get_release_version,
                             "The numeric version number of the release.")
      self.deferred_constant('RELEASE_BUILD', _get_release_build,
                             "The build number of the release.")
      self.deferred_constant('RELEASE_TYPE', _get_release_type,
                             "The type of release.")
      self.deferred_constant('RELEASE',
                             _get_release,
                             "A human readable version string.")
      self.deferred_constant('MOE_VERSION', moe_version,
                             "The Mediator's internal build version.")
  ##
  # Define the "core" updatable propertes needed to bootstrap framework.
  # @note Packages and modules can lazily create defaults when they
  #       are imported by calling mpx.properties.define_default(...).
  # @see define_default
  # @fixme Most of these belong in MOAB...
  # @fixme Rationalize names (FILE, DIR, EXT, BASENAME, DIRNAME).
  # @fixme Re-base everything.
  def _define_defaults(self):
      ROOT = self.ROOT
      # @fixme Calculate from current IDS?
      self.define_default('MPX_UID','0',
                          'The user id the framework will use.')
      self.define_default('MPX_GID', '0',
                          'The group id the framework will use.')
      self.define_default('TARGET_ROOT', '/',
                          'Used as the default root for all files created ' +
                          'outside of the installed Python packages ' +
                          'directories.')
      self.define_default('HOME_ROOT',
                          os.path.join(os.path.join(self.TARGET_ROOT,'home')),
                          "Default location for user's home diorectories.")
      self.define_default('BIN_DIR',
                          os.path.join(os.path.join(self.TARGET_ROOT,
                                                    'usr'),'bin'),
                          'Where executables are installed')
      self.define_default('SBIN_DIR',
                          os.path.join(os.path.join(self.TARGET_ROOT,
                                                    'usr'),'sbin'),
                          'Where sbin executables are installed')
      self.define_default('LIB_DIR',
                          os.path.join(os.path.join(self.TARGET_ROOT,
                                                    'usr'),'lib'),
                          'Where /usr/lib are installed')
      # @fixme MPX_PYTHON_LIB + MOAB + SITE-PACKAGES == 'headache'
      self.define_default('MPX_PYTHON_LIB',
                          os.path.join(self.TARGET_ROOT,
                                       'usr/lib/mpx/python'),
                          'Historical raisons.')
      self.define_default('ETC_DIR',
                          os.path.join(os.path.join(self.TARGET_ROOT,'etc')),
                          '/etc')
      self.define_default('TIMEZONE_DIR',
                          os.path.join(self.TARGET_ROOT,'usr/share/zoneinfo'),
                          'Time Zone Information Directory')
      self.define_default('TIMEZONE_FILE',
                          os.path.join(self.ETC_DIR, 'localtime'),
                          'Time Zone file')
      self.define_default('TEMP_DIR', os.path.join(self.TARGET_ROOT, 'tmp'),
                          'Temporary directory where files can be written')
      self.define_default('DATA_DIR', os.path.join(self.TARGET_ROOT,
                                                   'var/mpx'),
                          "The root directory for all of the framework's " +
                          "persistent data.")
      self.define_default('WWW_ROOT', os.path.join(self.DATA_DIR, 'www'),
                          'The root for all the W3 content.')
      self.define_default('HTTP_ROOT', os.path.join(self.WWW_ROOT, 'http'),
                          'The document root for the HTTP file server')
      self.define_default('HTTPS_ROOT', os.path.join(self.WWW_ROOT, 'https'),
                          'The document root for the HTTPS file server')
      self.define_default('CERTIFICATE_PEM_FILE',
                          os.path.join(self.HTTPS_ROOT, 'certificate.pem'),
                          'certificate pem file used for https.')
      self.define_default('LOGFILE_DIRECTORY',
                          os.path.join(self.DATA_DIR, 'log'),
                          'The directory where the presistent data is stored')
      self.define_default('CONFIGURATION_DIR',
                          os.path.join(self.DATA_DIR, 'config'),
                          'The path to the configuration directory.')
      self.define_default('INFO_DIR',
                          os.path.join(self.DATA_DIR, 'info'),
                          'The path to the info directory which contains '
                          'installation specific information.')
      self.define_default('PRIVATE_KEY_FILE',
                          os.path.join(self.CONFIGURATION_DIR, 'private.key'),
                          'SSL private key file.')
      self.define_default('PDO_DIRECTORY', os.path.join(self.CONFIGURATION_DIR,
                                                        'persistent'),
                          'The directory where the presistent data objects ' +
                          'are stored')
      self.define_default('CONFIGURATION_FILE',
                          os.path.join(self.CONFIGURATION_DIR, 'broadway.xml'),
                          'The name and path to the configuration file')
      self.define_default('VERSION_FILE', 'BROADWAY',
                          'The file that contains the version of framework')
      self.define_default('NODEDEF_DBFILE', 'nodedefs.xml',
                          'The name of the nodedef XML file')
      self.define_default('NODEDEF_DBFILE_EN','nodedefs.url',
                          'The name of encoded nodedef file')
      self.define_default('NODEDEF_ZIPFILE','nodedefs.zip',
                          'The name of the ZIPed nodedef file')
      self.define_default('NODEDEF_MD5FILE','nodedefs.md5',
                          'The name of the MD5 of the nodedefs XML file')
      self.define_default('DONT_THREAD_HTTP_SERVICES','false',
                          'Used mainly for debugging in WingIDE')
      self.define_default('DEBUG_LOCKS', 'false',
                          'Used to track lock usage.')
      self.define_default('DEBUG_LOCKS_APPROACH', '2',
                          'Approach to use if DEBUG_LOCKS.')
      self.define_default('DEBUG_LOCKS_TIMEOUT', '300',
                          'Maximum acquire time if DEBUG_LOCKS and '
                          'DEBUG_LOCKS_APPROACH == 2.')
      self.define_default('UPDATE_MOTD', 'true',
                          ('True if the framework should update ' +
                           'message-of-the-day.'))
      self.define_default('MPXINIT_CONF_FILE',
                          os.path.join(self.ETC_DIR, 'mpxinit.conf'),
                          'mpx config information')
      self.define_default('ETH0_CONFIG_MGR_FILE',
                          os.path.join(self.ETC_DIR, 'sysconfig/network-scripts/ifcfg-eth0'),
                          'eth0 configuration file on NBM Manager')
      self.define_default('NETWORK_CONFIG_MGR_FILE', 
                          os.path.join(self.ETC_DIR, 'sysconfig/network'),
                          'network configuration file on NBM Manager')
      self.define_default('MGETTY_DIR',
                          os.path.join(self.ETC_DIR, 'mgetty+sendfax'),
                          'Directory for mgetty configuration files')
      self.define_default('MGETTY_CONFIG_FILE',
                          os.path.join(self.MGETTY_DIR, 'mgetty.config'),
                          'mgetty configutation file')    
      self.define_default('LOGIN_CONFIG_BASE',
                          os.path.join(self.MGETTY_DIR, 'login.config'),
                          'login configutation file')
      self.define_default('PPP_DIR',
                           os.path.join(self.ETC_DIR, 'ppp'),
                          'Directory for pppd configuration files')
      self.define_default('PPP_DIALOUT_OPTIONS_FILE',
                          os.path.join(self.PPP_DIR, 'dial-out-options'),
                          'dial out options file')    
      self.define_default('PPP_DIALIN_OPTIONS_BASE',
                          os.path.join(self.PPP_DIR, 'dial-in-options'),
                          'dial in options file')
      self.define_default('CHAT_SCRIPT_FILE',
                          os.path.join(self.PPP_DIR, 'chat-mpx'),
                          'ppp chat script')
      self.define_default('CHAP_SECRETS_FILE',
                          os.path.join(self.PPP_DIR, 'chap-secrets'),
                          'chap secrets file')
      self.define_default('PAP_SECRETS_FILE',
                          os.path.join(self.PPP_DIR, 'pap-secrets'),
                          'chap secrets file')
      self.define_default('NAMESERVERS_FILE',
                          os.path.join(self.ETC_DIR, 'resolv.conf'),
                          'Domain name server file')
      self.define_default('INITTAB_FILE', os.path.join(self.ETC_DIR, 'inittab'),
                          'Init tab file')      
      self.define_default('VAR_DIR', os.path.join(self.TARGET_ROOT, 'var'),
                          '/var')
      self.define_default('VAR_RUN', os.path.join(self.VAR_DIR, 'run'),
                          '/var/run')
      self.define_default('VAR_RUN_BROADWAY',
                          os.path.join(self.VAR_RUN, 'broadway'),
                          '/var/run/broadway')
      self.define_default('VAR_LOCK', os.path.join(self.TARGET_ROOT,
                                                   'var/lock'),
                          'Directory where lock files are stored')
      self.define_default('VAR_LOG', os.path.join(self.VAR_DIR, 'log'),
                          'Directory for system log files')
      self.define_default('VAR_MPX', os.path.join(self.VAR_DIR, 'mpx'),
                          '/var/mpx')
      self.define_default('VAR_MPX_DB', os.path.join(self.VAR_MPX, 'db'),
                          '/var/mpx/db')
      self.define_default('STRICT_COMPLIANCE','false',
                          'Used to enforce development standards')
      self.define_default('HTTP_PORT','80',
                          'The default port to use for the web-server')
      self.define_default('HTTPS_PORT','443',
                          'The default port to use for the secure web-server')
      self.define_default('INIT_VERBOSITY','0',
                          'Non-zero logs messages while initializing the'
                          ' framework.')
      self.define_default('PAM_ENABLE', '1', 'Use PAM?')
      self.define_default('TRACEBACKS', '0', 'Show Tracebacks in Nodebrowser?')
      # START: SRNA properties:
      # (Admin) Tools dir tree:
      self.define_default('SRNA_TOOLS', os.path.join(self.ROOT,'tools','srna'),
                          'Top SRNA tools directory (scripts for cert/key gen,'\
                          'file distribution, reboot)')
      self.define_default('ADMIN_HOME', os.path.join(self.HOME_ROOT,'mpxadmin'),
                          'Home dir for admin user')
      # Update TGZ file:
      self.define_default('SRNA_UPDATE_TGZ', os.path.join(self.ADMIN_HOME,
                          'srna_update.tgz'),
                          'TGZ file containing updates to SRNA CA, certs, keys')
      self.define_default('SRNA_IP_ADDR_FILE', os.path.join(self.ADMIN_HOME,
                          'ip_addrs'),
                          'Plain text file containing internal, external IP'\
                          'addresses for target NBM')
      # Working data dir tree:
      self.define_default('SRNA_DATA', os.path.join(self.DATA_DIR, 'srna'),
                          'Top SRNA data directory (CA, certs, keys, reqs')
      self.define_default('SRNA_CACERT', os.path.join(self.SRNA_DATA, 
                          'demoCA','cacert.pem'), 'CA certificate')
      self.define_default('SRNA_CAKEY', os.path.join(self.SRNA_DATA, 
                          'demoCA','private','cakey.pem'), 'CA private key')
      self.define_default('SRNA_DH1024', os.path.join(self.SRNA_DATA, 
                          'srna_dh1024.pem'),
                          'Encrypted (1024-bit) Diffie-Helman parameters')
      # Accommodate up to 10 eth interfaces on this NBM (eth0 - eth9):
      for iEth in range(0,10):
          self.define_default('SRNA_CERT_eth%d' % iEth,
                              os.path.join(self.SRNA_DATA,'eth%d' % iEth,
                                           'srna_cert.pem'),
                              'Certificate for eth%d as SRNA server' % iEth)
          self.define_default('SRNA_KEY_eth%d' % iEth, 
                              os.path.join(self.SRNA_DATA, 
                                           'eth%d' % iEth,'srna_key.pem'),
                              'Unencrypted pvt key for eth%d as SRNA server' \
                              % iEth)
      # Temp dir-based paths (for prepping keys before installation reboot):
      self.define_default('SRNATMP_DATA', os.path.join(self.DATA_DIR, 'srnatmp'),
                          'Top SRNA data directory (CA, certs, keys, reqs')
      self.define_default('SRNATMP_CACERT', os.path.join(self.SRNATMP_DATA, 
                          'demoCA','cacert.pem'), 'CA certificate')
      self.define_default('SRNATMP_CAKEY', os.path.join(self.SRNATMP_DATA, 
                          'demoCA','private','cakey.pem'), 'CA private key')
      self.define_default('SRNATMP_DH1024', os.path.join(self.SRNATMP_DATA, 
                          'srna_dh1024.pem'),
                          'Encrypted (1024-bit) Diffie-Helman parameters')
      # Accommodate up to 10 eth interfaces on this NBM (eth0 - eth9):
      for iEth in range(0,10):
          self.define_default('SRNATMP_CERT_eth%d' % iEth,
                              os.path.join(self.SRNATMP_DATA, 
                                           'eth%d' % iEth,'srna_cert.pem'),
                              'Certificate for eth%d as SRNA server' % iEth)
          self.define_default('SRNATMP_KEY_eth%d' % iEth, 
                              os.path.join(self.SRNATMP_DATA, 
                                           'eth%d' % iEth,'srna_key.pem'),
                              'Unencrypted pvt key for eth%d as SRNA server' \
                              % iEth)
      self.define_default('FRAMEWORK_TYPE_DIR', os.path.join(self.LIB_DIR, 
                          'broadway','opt','mfw'),
                          'Parent dir of dir named for type of framework')
      # END: SRNA properties.
  def _load_file_object(self, source):
      next_line = source.readline()
      while next_line:
          next_line = next_line.strip()
          if next_line and next_line[0] != '#':
              try:
                  name, value = next_line.split('=',1)
                  name = name.strip()
                  value = value.strip()
                  assert len(name.split()) == 1, (
                      "Invalid property name: %r, whitespace not acceptable." %
                      (name,)
                      )
                  result = os.getenv('BROADWAY_%s' % name)
                  if result is not None:
                      setattr(self, name, result)
                  else:
                      self.set(name, value)
              except Exception, e:
                  # Figure out why...
                  self.invalid_lines += 1
                  if self.invalid_lines == 1:
                      # @fixme Log (deferred)
                      pass
              except:
                  pass
          next_line = source.readline()
      return

  ##
  #  Intialize the option cache
  #  Create new options for each.
  #  name=value pair in properties file
  #
  #  All lines starting with # are ignored
  #
  # @param file The name of the options file
  # @fixme Log (deferred) the following:
  #        1.  No properties to load (file == None)
  #        2.  If we couldn't open the file named file.
  #        3.  The first bad line.
  def _load_properties(self, source):
      self.invalid_lines = 0
      def _cant_read(object):
          try: object.readline(0)
          except: return 1
          return 0
      close_file = 0
      if source == None:
          # No properties to load.
          # @fixme Log (deferred)
          return
      if type(source) == types.StringType:
          try:
              source = open(source, 'r')
              close_file = 1
          except:
              # We could not open the file.
              # @fixme Log (deferred)
              return
      elif _cant_read(source):
          raise TypeError, "source must be a string or a file-like object."
      try:
          self._load_file_object(source)
      finally:
          if close_file:
              source.close()
      return

# Create the Singleton
_property_file = os.getenv('BROADWAY_PROPERTIES')
properties = Properties(_property_file)
del _property_file
