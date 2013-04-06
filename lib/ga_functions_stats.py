import copy

from operator import itemgetter

from lib.functions import mean_stdv
from lib.ga_functions_misc import *
from lib.plugin_objects import mesRestraint

def get_ratio_stats( targets, ensembles ):
	"""
	Return the components and their weights in the provided ensembles
	
	Arguments:
	targets		- list of mesTargets ensembles have been fitted against
	ensembles	- list of ensembles to run error estimation on
	"""
	unique = get_unique_ensembles( ensembles )
	
	# make a list of the components observed in the unique ensembles
	components = []
	for e in unique:
		for c in e.component_names:
			if( not c in components ):
				components.append( c )
			else:
				break
				
	# go through *all* ensembles and get the relative weighting for that component
	component_weights = {}
	for t in targets:
		component_weights[t.name] = {}
		
		for c in components:
			component_weights[t.name][c] = []
			
			for e in ensembles:
				if(c in e.component_names): 
					i = e.component_names.index(c)
					component_weights[t.name][c].append( e.ratios[t.name][i] )
	
	return component_weights
	
def get_restraint_stats( args, targets, ensembles ):
	"""
	Generate the per-restraint scores for the provided ensembles

	Arguments:
	args		- MESMER argument parameters	
	targets		- list of mesTargets ensembles have been fitted against
	ensembles	- list of ensembles to run error estimation on
	"""
	
	# initialize the return dict structure
	stats = {}
	for r in targets[0].restraints:
		stats[r.type] = {}
		for t in targets:
			stats[r.type][t.name] = []
	
	# extract the fitness values from the ensembles
	for t in targets:
		for r in targets[0].restraints:
			for e in ensembles:
				stats[r.type][t.name].append(e.fitness[t.name][r.type])
				
	#  replace the return dict values with the best ensemble restraint score, mean and stdev
	for r in targets[0].restraints:
		for t in targets:
			temp = mean_stdv( stats[r.type][t.name] )
			stats[r.type][t.name] = (ensembles[0].fitness[t.name][r.type],temp[0],temp[1])
	
	return stats

def get_ratio_errors( args, components, plugins, targets, ensembles ):
	"""
	Determine the component ratio statistics for ensembles against each target 

	Returns a list of ensemble componet ratio statistic dicts:
	[ensemble]
		|-{target}
			|-(component, weight, stdev)
				
	Arguments:
	args		- MESMER argument parameters
	plugins		- MESMER plugin modules
	targets		- list of mesTargets ensembles have been fitted against
	ensembles	- list of ensembles to run error estimation on
	"""
	
	stats = []
	for e in ensembles:
		
		ratios = {}
		for t in targets:
			ratios[t.name] = []

		if(args.boots < 1):
			# no component ratio uncertainty analysis, just return the current ratios for each ensemble
			for t in targets:
				ratios[t.name].append( e.ratios[t.name] )
		else:
			# perform component ratio uncertainty analysis via bootstrap estimates				

			for i in range(args.boots):
		
				# make estimation of target restraints via bootstrapping
				estimates = []
				for t in targets:
					estimates.append( t.make_bootstrap(plugins,e) )
				
					# unset optimization flag!
					e.optimized[t.name] = False
			
				# optimize the component ratios
				optimized = mp_optimize_ratios( args, components, plugins, estimates, [e] )
				
				for t in targets:
					ratios[t.name].append( optimized[0].ratios[t.name] )

		# calculate the component ratio mean and standard deviation for each target
		temp = {}
		for t in targets:
		
			unzipped = zip(*ratios[t.name])
			
			temp[t.name] = []
			for i in range(args.size):
				mean,stdev = mean_stdv(unzipped[i])
				temp[t.name].append( [e.component_names[i],mean,stdev] )
					
			stats.append( temp )

	return stats
	
def get_best_ensembles( args, targets, parents, offspring ):
	"""
	Return only the best-scoring ensembles from parent and offspring populations

	Arguments:
	args		- MESMER argument parameters	
	targets		- list of mesTargets ensembles have been fitted against
	parents		- list of ensembles
	offspring	- list of ensembles
	
	Returns a tuple of best scoring ensembles and some collected statistics
	(best_scored,stats)
	"""

	# calculate total fitness values for each population
	p_scores = calculate_fitnesses( targets, parents )
	o_scores = calculate_fitnesses( targets, offspring )
	
	# combine the overall parent and offspring score sums into a list of key-score pairs
	scores = []
	
	for i in range( args.ensembles ):
		scores.append( [i, 0.0] )
		for t in targets:
			scores[-1][1] += p_scores[t.name][i]
	
	for i in range( args.ensembles ):
		scores.append( [i +args.ensembles, 0.0] )
		for t in targets:
			scores[-1][1] += o_scores[t.name][i]
	
	# sort the array by the fitness scores
	sorted_scores = sorted(scores, key=itemgetter(1))

	# keep track of per-target scores as well
	target_scores = {}
	for t in targets:
		target_scores[t.name] = []

	# select only the 1/2 best scoring from the combined parent and offspring ensembles for the next step
	best_scored, total_scores = [], []
	counter = 0
	for (i, (key,score) ) in enumerate(sorted_scores):
		total_scores.append( score )
		
		if( key < args.ensembles ):
			best_scored.append( parents[key] )
			for t in targets:
				target_scores[t.name].append( p_scores[t.name][key] )
		else:
			counter += 1
			best_scored.append( offspring[key % args.ensembles] )
			for t in targets:
				target_scores[t.name].append( o_scores[t.name][key % args.ensembles] )
		
		# quit once we've reached the required number of offspring
		if( i == (args.ensembles -1) ):
			break
	
	# calculate the minimum, average and stdev scores for the total and also for each target individually
	total_stats = [total_scores[0]]
	total_stats.extend(mean_stdv(total_scores))
	
	target_stats = {}
	for t in targets:
		target_stats[t.name] = [target_scores[t.name][0]]
		target_stats[t.name].extend(mean_stdv(target_scores[t.name]))

	# create the statistics dict
	stats = {
	'scores':	sorted_scores,
	'total':	total_stats,
	'target':	target_stats,
	'ratio':	float(args.ensembles - counter) / args.ensembles
	}

	return (best_scored,stats)