import os
import shelve
import tempfile
import uuid
import argparse

from exceptions import *

class mesPluginBasic:
	"""Basic data handling plugin for MESMER
	
	Attributes:
		name (string): (Required) Brief name of the plugin
		version (string): (Required) Version string of the plugin
		info (string): (Required) User-friendly information about the plugin
		type (tuple): (Required) Strings (e.g. "CURV", "SAXS") naming data types that this plugin can comprehend
		target_parser (Argparse parser): Argument parser for target file options
		component_parser (Argparse parser): Argument parser for component file options
		path (string): (Optional) Path to a required external executable or library
	"""
	
	def __init__( self, args ):
		"""Initialize the plugin
		
		Args:
			args (argparse namespace): Arguments used to call MESMER, can be used to pass info to the plugin		
		"""
		self.name = ''
		self.version = ''
		self.info = ''
		self.path = None
		self.types = ('NONE',)

		self.target_parser = argparse.ArgumentParser(prog=self.types[0])
		self.component_parser = argparse.ArgumentParser(prog=self.types[0])
		
	def __getstate__(self):
		"""Return the state of plugin
		
		Args: None
		
		Returns: dictionary-based representation of the plugin
		"""
		try:
			del self.target_parser
			del self.component_parser
		except AttributeError:
			pass
		return self.__dict__
			
	def __setstate__(self, d):
		"""Regenerate the plugin from a previously serialized representation
		
		Args:
			d (dict): The dictionary representation previously generated by __getstate__()
		
		Returns: None
		"""
		self.__dict__ = d

	def __str__( self ):
		"""Provide some information about the plugin
				
		Args: None
		Returns: String describing the plugin
		"""
		
		ret = "Help for plugin: \"%s\"" % self.name
		ret+= "\tVersion: %s" % self.version
		ret+= "\tValid data types:"
		for t in self.types:
			ret+= "\t\t%s" % t
		ret+= ""
		ret+= "Target file argument help:"
		try:
			ret+= self.target_parser.format_help()
		except:
			raise mesPluginError("Could not display target argument help for parser \"%s\"" % self.name)
		ret+= ""
		ret+= "Component file argument help:"
		try:
			ret+= self.component_parser.format_help()
		except:
			raise mesPluginError("Could not display component argument help for parser \"%s\"" % self.name)
		
		return ret
		
	# base type stubs to be overwritten

	def ensemble_state( self, restraint, target_data, ensembles, file_path):
		"""Return the status of the plugin for the current generation and target

		Args:
			target_data		- list of data the plugin has saved for the target
			ensemble_data	- list of data the plugin has saved for every ensemble in the run, ordered by overall fitness
			filePath		- an optional file path the plugin can save data to

		Returns: a list of strings
		"""

		return []

	def load_restraint( self, restraint, block, target_data ):
		"""Initialize the provided restraint with information from the target file

		The format for the block dict is:
		"type" (string): Corresponds to a type handled by this plugin
		"header" (string): The first line of the content block
		"content" (list of strings): The rest of the content block (if any), may be absent if the restraint is a single line (e.g. an Rg value or somesuch)
		"l_start": (int): The line index for the start of the content block from the original file
		"l_end": (int): The line index for the end of the content block from the original file

		Args:
			restraint (mesRestraint): The empty restraint object to be filled
			block (dict): A dict constructed from the target file matching the plugin's type (see this object's load_restraint() method)
			target_data (variable): The plugin's free-form data storage variable for this target
			
		Returns: List of strings: Messages to be reported to the user
		
		Raises:
			mesPluginError: Any error that causes the restraint to not be loaded
		
		"""
		return []

	def load_attribute( self, attribute, block, ensemble_data ):
		"""Initialize the provided attribute with information from a component file

		Args:
			attribute (mesAttribute):	The empty attribute object to be filled
			block (dict): A dict constructed from the component file matching the plugin's type (see this object's load_restraint() method)
			ensemble_data (variable): The plugin's free-form data storage variable for this ensemble
			
		Returns: List of strings: Status messages to be reported to the user
			
		Raises:
			mesPluginError: Any error that causes the attribute to not be loaded
		"""
		return []

	def load_bootstrap( self, bootstrap, restraint, ensemble_data, target_data ):
		"""Generate a bootstrap restraint using the provided ensemble data

		Args:
			bootstrap (mesRestraint): The restraint to fill with the bootstrap estimate, a la via load_restraint()
			restraint (mesRestraint): The restraint serving as the template for the sample
			ensemble_data (variable): The plugin's data storage variable for this ensemble
			target_data (variable): The plugin's data storage variable for the target
			
		Returns: List of strings: Messages to be reported to the user
			
		Raises:
			@TODO@ Exceptions
		"""

		return []

	def calc_fitness( self, restraint, target_data, ensemble_data, attributes, ratios ):
		"""Calculate the fitness of a set of attributes against a given restraint

		Args:
			restraint (mesRestraint): The restraint serving as the template for the sample
			target_data (variable): The plugin's data storage variable for the target
			ensemble_data (variable): The plugin's data storage variable for this ensemble
			attributes (list): List of the mesAttributes previously filled by load_attribute, to be averaged together and compared to the restraint
			ratios (list): The relative weighting (ratio) of each attribute

		Returns:
			float: The numeric fitness score.
		"""
		return None

	def close( self ):
		pass

class mesPluginDB( mesPluginBasic ):
	"""An extended data-handling MESMER plugin that provides access to a persistent database"""
	
	def __init__( self, args ):
		"""Initialize the plugin

		Opens a handle to a shelve database for later usage.		
	
		Raises:
			mesPluginError on failure to make a db connection
		"""
		mesPluginBasic.__init__( self, args )
		
		# Use the provided scratch directory, or use system default temporary?
		if( args.scratch ):
			self._db_path = os.path.join(args.scratch,uuid.uuid1().hex)
		else:
			self._db_path = os.path.join(tempfile.gettempdir(),uuid.uuid1().hex)
		
		self._db_handle = None
		try:
			self._db_handle = shelve.open(self._db_path,'c')
		except:
			raise mesPluginError("Could not create temporary scratch DB to store component data: \"%s\"" % self._db_path)
				
	def __getstate__(self):
		"""Return the state of plugin, properly closing the db handle temporarily in anticipation of serialization
		
		The parser objects are removed, since they're not needed once we've started threading. They fail on pickle anyway.
		
		Args: None
		
		Returns: dictionary-based representation of the plugin
		"""
		try:
			del self.target_parser
			del self.component_parser
		except AttributeError:
			pass
			
		# Disconnect from the database
		if (self._db_handle != None):
			self._db_handle.close()
			self._db_handle = None
		return self.__dict__
			
	def __setstate__(self, d):
		"""Regenerate the plugin, and re-open the db handle
		
		Args:
			d (dict): The dictionary representation previously generated by __getstate__()
		
		Returns: None
		
		Raises: mesPluginError if reconnecting to the db fails.
		"""
		self.__dict__ = d
		
		# Reconnect to the database
		try:
			self._db_handle = shelve.open(self._db_path,'r')
		except:
			raise mesPluginError("Could not reconnect to scratch DB containing component data: \"%s\"" % self._db_path)

	def __del__( self ):
		try:
			if (self._db_handle != None):
				self._db_handle.close()

			# some db implementations append a .db to the provided path
			if( os.path.exists(self._db_path)):
				os.unlink(self._db_path)
			elif( os.path.exists("%s%s" % (self._db_path,'.db')) ):
				os.unlink("%s%s" % (self._db_path,'.db'))
	
		except AttributeError:
			pass

	def put( self, data, key=None ):
		"""Put some data into storage
		
		Args:
			data (variable): The data to store
			key (defaults to None): If not provided, generates a unique key for the newly-inserted data
		
		Returns string: Key for the newly-inserted data
		"""
		if( key == None ):
			key = uuid.uuid1().hex
		self._db_handle[key] = data
		return key

	def get( self, key ):
		"""Get some data from storage
		
		Args:
			key (string): Key for the data to return
			
		Returns (variable): The data previously stored
		"""
		return self._db_handle[key]