import re
import copy

from exceptions			import *
from utility_functions	import print_msg,get_input_blocks

class mesRestraint:
	"""
	A basic object for holding information about a restraint
	"""
	def __init__(self, scale, type):
		self.scale = scale
		self.type = type
		self.data = {}
		return

class mesTarget:
	"""
	Contains the various types of experimental data (restraints) that will be used as a target for fitting
	"""

	def __init__(self):
		"""
		Initialize the target

		1. Sets name to an empty string
		2. Sets restraints to an empty list
		3. Sets plugin_data to an empty dict
		"""

		self.name = ''
		self.restraints = []
		self.plugin_data = {}

		return

	def load(self, file, plugins):
		"""
		Load the targets's restraints from a specified file using plugins

		Args:
			file (string): Path to a MESMER target file, see general_functions.get_input_blocks() for more information
			plugins (list): List of mesPlugin modules for interpretation of data and creation of mesRestraint objects

		Returns: True on success, or False on Failure, errors are communicated via the print_msg function
		"""

		# get an array of data blocks from the provided target
		blocks = get_input_blocks(file)

		if( not blocks ):
			print_msg("ERROR:\tCould not read target file \"%s\"." % (file))
			return False

		if( len(blocks) == 0 ):
			print_msg("ERROR:\tTarget file \"%s\" contains no recognizable data." % (file))
			return False

		# find the plugin that handles this type of of data
		for b in blocks:

			if(b['type'] == 'NAME'):
				self.name = b['header'][1]
				continue

			for p in plugins:
				if(b['type'] in p.types):

					# initialize the plugin storage variable for this restraint type
					self.plugin_data[b['type']] = {}

					status = None

					# check that the scaling
					try:
						weighting = float(b['header'][1])
					except:
						print_msg("ERROR:\tRestraint on line %i does not have a weighting value." % (b['l_start']))
						return False

					# create a new restraint
					restraint = mesRestraint(weighting, b['type'])

					try:
						messages = p.load_restraint( restraint, b, self.plugin_data[b['type']] )
					except mesPluginError as e:
						print_msg("ERROR:\tplugin \"%s\" could not create a restraint from the target file \"%s\" lines %i-%i." % (p.name,file,b['l_start'],b['l_end']))
						print_msg("INFO:\tplugin \"%s\" reported: %s" % (p.name,e.msg))
						return False

					self.restraints.append(restraint)
					print_msg("INFO:\tTarget file \"%s\" lines %i-%i - plugin \"%s\" created %.1fx weighted \"%s\" restraint." % (file,b['l_start'],b['l_end'],p.name,weighting,b['type']))
					for m in messages:
						print_msg("INFO:\tplugin \"%s\" reported: %s" % (p.name,m))

					# only allow one plugin per block
					break

		if( self.name == '' ):
			print_msg("ERROR:\tcomponent file \"%s\" has no NAME attribute." % (file) )
			return False

		return True

	def make_bootstrap( self, plugins, ensemble ):
		"""
		Create a bootstrap estimate clone of self

		Args:
			plugins (list): A list of mesPlugin modules
			ensemble: The ensemble used to create the estimate

		Returns: a mesTarget clone with bootstrapped estimates of all restraints

		@TODO@ Error handling
		"""

		dupe = copy.deepcopy(self)

		for r in dupe.restraints:
			for p in plugins:
				if(r.type in p.types):
					p.load_bootstrap( r, r, ensemble.plugin_data[dupe.name][r.type], dupe.plugin_data[r.type] )

		return dupe


