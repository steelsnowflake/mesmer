"""
Contains several useful functions for displaying or saving information/statistics about a MESMER run
"""

import os
import os.path
import operator
import shelve

from datetime			import datetime

from exceptions			import *
from ga_functions_misc	import *
from ga_functions_stats	import *
from utility_functions	import *

_MESMER_ENSEMBLES_FILE_FORMAT	= 'ensembles_%s_%05i.tbl'
_MESMER_STATISTICS_FILE_FORMAT	= 'component_statistics_%s_%05i.tbl'
_MESMER_CORRELATION_FILE_FORMAT	= 'component_correlations_%05i.tbl'
_MESMER_RESTRAINTS_FILE_FORMAT	= 'restraints_%s_%s_%05i.out'
_MESMER_OPT_STATUS_FILE_FORMAT	= 'optimization_state_%s_%05i.tbl'

def print_generation_state( args, counter, ensemble_stats, restraint_stats ):
	"""
	Print the status of the current generation via print_msg()

	Args:
		args (argparse namespace): MESMER argument parameters
		ensemble_stats (dict): A complex dictionary containing ensemble statistics. See get_best_ensembles() for more info.
		restraint_stats (dict): A complex dictionary containing restraint statistics. See get_restraint_stats() for more info.

	Returns: None
	"""

	print_msg( "" )
	print_msg( "\tCurrent time: %s" % datetime.utcnow() )
	print_msg( "\tParent survival percentage: %i%%, %i unique ensembles" % (100*ensemble_stats['ratio'],ensemble_stats['unique']) )
	print_msg( "\n\t\tBest Score\t|\tAverage\t\t|\tStdev" )
	print_msg( "\t\t------------------------------------------------------------" )
	print_msg( "\t\t%.3e\t|\t%.3e\t|\t%.3e" % (
		ensemble_stats['total'][0],
		ensemble_stats['total'][1],
		ensemble_stats['total'][2]) )

	target_names = ensemble_stats['target'].keys()

	# print the per-target breakdown of scores
	for name in target_names:
		if( len(target_names) > 1):
			print_msg( "\n\t%s" % name )
			print_msg( "\tTotal\t%.3e\t|\t%.3e\t|\t%.3e" % (
				ensemble_stats['target'][name][0],
				ensemble_stats['target'][name][1],
				ensemble_stats['target'][name][2]) )

		# print the per-restraint breakdown of scores
		if( len(restraint_stats) > 1):
			for type in sorted(restraint_stats.keys()):
				print_msg( "\t%s\t%.3e\t|\t%.3e\t|\t%.3e" % (
				type,
				restraint_stats[type][name][0],
				restraint_stats[type][name][1],
				restraint_stats[type][name][2]) )

	print_msg( "" )
	sys.stdout.flush()

	# write to MESMER results db
	db = shelve.open( os.path.join(args.dir,'mesmer_log.db') )

	if(db.has_key('ensemble_stats')):
		a,b = db['ensemble_stats'], db['restraint_stats']
	else:
		a,b = [],[]

	# large numbers of ensemble scores makes depickling run *extremely* slow, so no ensemble_stats['ratios']
	a.append( (ensemble_stats['total'],ensemble_stats['ratio'],ensemble_stats['target']) )
	b.append(restraint_stats)

	db['ensemble_stats'], db['restraint_stats'] = a, b
	db.close()

	return

def print_ensemble_state( args, ratio_stats ):
	"""
	Print the components of an ensemble via print_msg()

	Args:
		args (argparse namespace): MESMER argument parameters
		ratio_stats (dict): A dictionary keyed by component names containing a three-component tuple: best weight, average weight, and (optionally) weight stdev
	
	Returns: None
	"""

	for name in ratio_stats:
		print_msg( "\t%s" % (name) )

		for (c,w,d) in ratio_stats[name]:
			if( args.boots > 0 ):
				print_msg( "\t\t%.3f +/- %.3f\t%s" % (w,d,c) )
			else:
				print_msg( "\t\t%.3f\t%s" % (w,c) )

	sys.stdout.flush()

	return

def print_plugin_state( args, counter, plugins, targets, ensembles):
	"""
	Call the ensemble_state function for each plugin if the argument -Pstate is set
	
	This function is called at each generation, and gives plugins a chance to print statistics or other aggregate information
	
	Args:
		args (argparse namespace): MESMER argument parameters
		counter (int): Generation counter used to build output path
		plugins	(list): List of mesPlugins
		targets	(list): List of mesTargets
		ensembles (list): List of mesEnsembles
		
	Returns: always True. Errors from plugins are reported via print_msg()
	"""

	output = []
	for t in targets:
		for r in t.restraints:
			path = os.path.abspath( os.path.join(args.dir,_MESMER_RESTRAINTS_FILE_FORMAT%(t.name,r.type,counter)) )

			for p in plugins:
				if(r.type in p.types):
					# build the ensemble data list from all ensembles
					all_ensemble_data = []
					for e in ensembles:
						all_ensemble_data.append(e.plugin_data[t.name][r.type])

					try:
						messages = p.ensemble_state(r, t.plugin_data[r.type], all_ensemble_data, path)
					except mesPluginError as e:
						print_msg("Plugin \"%s\" returned an error: %s" % e.msg)

					break

	return True

def write_component_stats( args, counter, ensembles ):
	"""
	Write component correlations from the provided ensembles to file

	Args:
		args (argparse namespace): MESMER argument parameters
		counter (int): Generation counter (used to build file path)
		ensembles (list): List of mesEnsembles
	
	Returns: True on success, False on failure
	"""

	(names,relative,absolute) = get_component_correlations( args, ensembles )
	n = len(names)

	# don't bother printing an empty table
	if(n==0):
		return True

	path = os.path.abspath( os.path.join(args.dir,_MESMER_CORRELATION_FILE_FORMAT%(counter)) )

	try:
		f = open( path, 'w' )
	except IOError:
		print_msg( "ERROR:\tCould not write component correlation table to file \"%s\"" % (path) )
		return False

	# print table header
	for name in names:
		f.write("\t%s" % name,)
	f.write("\n")

	toggle = 0
	for i in range(n):
		f.write("%s\t" % names[i])

		for j in range(n):

			# toggle from absolute to relative correlation
			if( i == j ):
				toggle = 1

			if(toggle > 0):
				f.write("%0.3f\t" % relative[i][j])
			else:
				f.write("%0.3f\t" % absolute[i][j])

		f.write("\n")
		toggle = 0

	f.close()

	return True

def write_ensemble_stats( args, counter, targets, ensembles ):
	"""
	Write statistics from the ensemble component ratios to file

	Args:
		args (argparse namespace): MESMER argument parameters
		targets	(list): List of mesTargets
		ensembles (list): List of mesEnsembles

	Returns: True on success, False on failure
	"""

	stats = get_ratio_stats( targets, ensembles )

	# go through each target
	for t in stats:

		path = os.path.abspath( os.path.join(args.dir,_MESMER_STATISTICS_FILE_FORMAT%(t,counter)) )

		try:
			f = open( path, 'w' )
		except IOError:
			print_msg( "ERROR:\tCould not write ensemble statistics to file \"%s\"" % (path) )
			return False

		f.write( "%s\tPrevalence\tAverage\t\tStdev\n" % (''.rjust(32)) )

		# order components by prevalence
		component_counts = []
		for component in stats[t]:
			component_counts.append( (component,len(stats[t][component])) )
		component_counts.sort( key=operator.itemgetter(1), reverse=True )

		for (component,count) in component_counts:
			p = float(count)/args.ensembles
			# don't show stats for components with low prevalence
			if( p*100 < args.Pmin):
				break

			(mean,stdev) = mean_stdv( stats[t][component] )
			f.write( "%s\t%.3f %%\t\t%.3e\t%.3e\n" % (
				component.rjust(32),
				100*p,
				mean,
				stdev) )

		f.write( "" )
	f.close()

	return True

def write_optimization_state( args, counter, targets, ensembles ):
	"""
	Writes the optimizations state for each ensemble to a file

	Args:
		args (argparse namespace): MESMER argument parameters
		counter (int):Generation counter used to build the file output path
		targets (list): List of mesTargets
		ensembles (list): List of mesEnsembles

	Returns: True on success, False on failure (also prints an error message to stdout)
	"""

	for t in targets:

		path = os.path.abspath( os.path.join(args.dir,_MESMER_OPT_STATUS_FILE_FORMAT%(t.name,counter)) )

		try:
			f = open( path, 'w' )
		except IOError:
			print_msg( "ERROR:\tCould not optimization state information to file \"%s\"" % (path) )
			return False

		for (i,e) in enumerate(ensembles):
			f.write("%i\t" % (i))

			a = []
			for t in targets:
				a.append( str(e.opt_status[t.name]) )

			f.write("%s\n" % ("\t".join(a)) )

	f.close()
	return True

def write_ensemble_state( args, counter, targets, ensembles ):
	"""
	Write the current state of ensembles (component makeup, per-target ratios and fitnesses) to the MESMER results directory

	Args:
		args (argparse namespace): MESMER argument parameters
		counter (int): The current generation number
		targets (list): List of mesTargets
		ensembles (list): List of mesEnsembles for which to write status
		
	Returns: True on success, or False on failure (e.g. couldn't write to file) @TODO@: Maybe raise an exception instead?
	"""

	for t in targets:

		path = os.path.abspath( os.path.join(args.dir,_MESMER_ENSEMBLES_FILE_FORMAT%(t.name,counter)) )
		try:
			f = open( path, 'w' )
		except IOError:
			print_msg( "ERROR:\tCould not write ensemble state to file \"%s\" " % (path) )
			return False

		str_list = ['#']
		for i in range(len(ensembles[0].component_names)):
			str_list.append('component')

		str_list.append('fitness')

		for i in range(len(ensembles[0].component_names)):
			str_list.append('ratio')

		str_list.append("\n")

		f.write("\t".join(str_list))
		del str_list[:]

		for (i,e) in enumerate(ensembles):
			str_list.append( "%05i" % (i) )

			for c in e.component_names:
				str_list.append(c)

			str_list.append( "%.3e" % (sum(e.fitness[t.name].itervalues())) )

			for w in e.ratios[t.name]:
				str_list.append( "%.3f" % (w) )

			str_list.append("\n")

			f.write("\t".join(str_list))
			del str_list[:]

		f.close()

	return True
