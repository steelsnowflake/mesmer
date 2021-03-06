import os
import sys
import tkMessageBox
import argparse
import Tkinter as tk
import tkFileDialog

from subprocess		import Popen,PIPE

from .. exceptions import *
from .. ga_functions_output import _MESMER_CORRELATION_FILE_FORMAT,_MESMER_STATISTICS_FILE_FORMAT,_MESMER_RESTRAINTS_FILE_FORMAT

from tools_plugin	import convertParserToOptions,makeListFromOptions
from tools_general	import getColumnNames
from win_options	import OptionsWindow

def makeCorrelationPlot( w ):
	generation_count,target_name,data_type = w.currentSelection
	
	p1 = os.path.join(w.activeDir.get(), _MESMER_CORRELATION_FILE_FORMAT%generation_count )
	p2 = os.path.join(w.activeDir.get(), _MESMER_STATISTICS_FILE_FORMAT%(target_name,generation_count) )
	
	cmd = ['make_correlation_plot']
	if( w.prefs['mesmer_base_dir'] != '' ):
		cmd = [sys.executable,os.path.join(w.prefs['mesmer_base_dir'],'utilities','make_correlation_plot.py')]
	
	if( os.access( p1, os.R_OK ) and os.access( p2, os.R_OK ) ):
		cmd.extend( [p1,p2,'-size','20'] )
	elif( os.access( p1, os.R_OK ) ):
		tkMessageBox.showwarning("Warning","Component statistics not available, plotting only unweighted correlations",parent=w)
		cmd.extend( [p1,'-size','20'] )
	else:
		tkMessageBox.showerror("Error","Could not open generation correlation file \"%s\"" % p1,parent=w)
		return
				
	try:
		Popen(cmd)
	except Exception as e:
		tkMessageBox.showerror("Error","Could not open the correlation plot: %s" % (e),parent=w)
		return

def plotRestraint( w ):
	generation_count,target_name,data_type = w.currentSelection
	
	for p in w.plot_plugins:
		if (data_type in p.types):
			path = (os.path.join(w.activeDir.get(), _MESMER_RESTRAINTS_FILE_FORMAT%(target_name,data_type,generation_count)))

			if( not os.access( path, os.R_OK ) ):
				tkMessageBox.showerror("Error","Could not open the restraint file \"%s\"" % path ,parent=w)
				return

			if( p.parser ): # get options for the plugin
				if( p.name in w.pluginOptions ):
					options = w.pluginOptions[ p.name ]
				else:
					w.pluginOptions[ p.name ] = convertParserToOptions( p.parser )
				w.optWindowMaster = tk.Toplevel(w.master)
				w.optWindow = OptionsWindow(w.optWindowMaster, w.pluginOptions[ p.name ] )
				w.optWindowMaster.focus_set()
				w.optWindowMaster.grab_set()
				w.optWindowMaster.transient(w)
				w.optWindowMaster.wait_window(w.optWindowMaster)
				if w.optWindow.returncode != 0:
					return

			try:
				if( p.parser ):
					p.plot( path, w.pluginOptions[ p.name ], title="Best fit to %s %s data at generation %i"%(target_name,data_type,generation_count) )
				else:
					p.plot( path, None, title="Best fit to %s %s data at generation %i"%(target_name,data_type,generation_count) )
				return
			except (Exception,mesPluginError) as e:
				tkMessageBox.showerror("Error","Plotting plugin returned an error: %s" % (e))
	return
	
def plotAttributes( w ):
	p1 = w.attributeTable.get()
	if( not os.access( p1, os.R_OK ) ):
		tkMessageBox.showerror("Error","Could not read attribute table \"%s\"" % p1,parent=w)
		return
		
	column_names = getColumnNames( p1 )
	generation_count,target_name,data_type = w.currentSelection

	if(generation_count == None or target_name == None):
		return

	p2 = os.path.join(w.activeDir.get(), _MESMER_STATISTICS_FILE_FORMAT%(target_name,generation_count) )
	if( not os.access( p1, os.R_OK ) ):
		tkMessageBox.showerror("Error","Could not read component statistics table \"%s\"" % p2,parent=w)
		return

	if( 'attributePlotter' not in w.pluginOptions ):
		parser = argparse.ArgumentParser()
#		parser.add_argument('-nCol',	type=int,	default=0,		help='Column containing component names')
		if column_names == None or len(column_names) < 3:
			parser.add_argument('-xCol', metavar="X column",	type=int,	default=1,		help='Column to use as the plot\'s X axis')
			parser.add_argument('-yCol', metavar="Y column",	type=int,	default=2,		help='Column to use as the plot\'s Y axis')
			parser.add_argument('-zCol', metavar="Z column",				default='',		help='Column to use as the plot\'s Z axis. Leave blank for regular 2D scatter plot')
		else:
			parser.add_argument('-xCol', metavar="X column",	default=column_names[1],	choices=column_names,	help='Attribute to use as the plot\'s X axis')
			parser.add_argument('-yCol', metavar="Y column",	default=column_names[2],	choices=column_names,	help='Attribute to use as the plot\'s Y axis')
			parser.add_argument('-zCol', metavar="Z column",	default='',					choices=['']+column_names,	help='Attribute to use as the plot\'s Z axis. Leave blank for regular 2D scatter plot')

		parser.add_argument('-xLabel',	metavar="X axis label",	default='',		help='The label for the x-axis')
		parser.add_argument('-yLabel',	metavar="Y axis label",	default='',		help='The label for the y-axis')
		parser.add_argument('-zLabel',	metavar="Z axis label",	default='',		help='The label for the z-axis')
		parser.add_argument('-axes',	metavar="Axis scales",	default='',		help='Axes scale (Xmin Xmax Ymin Ymax)')
		parser.add_argument('-statNorm',	action='store_true', 				help='Normalize variable color saturation for component prevalence')
		parser.add_argument('-statSame',	action='store_true',				help='Do not use variable color saturation for component prevalence')
		parser.add_argument('-statWeight',			type=float, default='',		help='When plotting MESMER statistics, drop components weighted lower than this amount')
		parser.add_argument('-statPrevalence',		type=float,	default='',		help='When plotting MESMER statistics, drop components with prevalences lower than this amount')
		parser.add_argument('-statSubsample',		type=float,	default='',		help='Randomly subsample selected conformers by a percentage.')
		w.pluginOptions['attributePlotter'] = convertParserToOptions( parser )

	w.newWindow = tk.Toplevel(w.master)
	w.optWindow = OptionsWindow(w.newWindow, w.pluginOptions['attributePlotter'] )
	w.newWindow.focus_set()
	w.newWindow.grab_set()
	w.newWindow.transient(w)
	w.newWindow.wait_window()
	
	# convert column names into indices
	if column_names != None and len(column_names) > 2:
		for k,group in w.pluginOptions['attributePlotter'].iteritems():
			if group['dest'] == 'xCol':
				group['value'] = column_names.index(group['value'])
			elif group['dest'] == 'yCol':
				group['value'] = column_names.index(group['value'])
			elif group['dest'] == 'zCol' and group['value'] != '':
				group['value'] = column_names.index(group['value'])
		
	if w.optWindow.returncode == 0:
		cmd = ['make_attribute_plot']
		if( w.prefs['mesmer_base_dir'] != '' ):
			cmd = [sys.executable,os.path.join(w.prefs['mesmer_base_dir'],'utilities','make_attribute_plot.py')]
		cmd.extend( [p1,'-stats',p2] )
		cmd.extend( ['-title',"Attributes %s ensembles at generation %i"%(target_name,generation_count)] )
		cmd.extend( makeListFromOptions( w.pluginOptions['attributePlotter'] ) )
		
		try:
			Popen(cmd)
		except OSError:
			tkMessageBox.showerror("Error","Could not open the attribute plotter",parent=w)
			return

def plotHistogram( w ):
	if( not w.resultsDB.has_key('ensemble_stats') ):
		return

	generation_count,target_name,data_type = w.currentSelection
	if(generation_count == None):
		return

	try:
		import pylab as P
	except:
		tkMessageBox.showerror("Error","Could not import matplotlib's pylab",parent=w)
		return

	n, bins, patches = P.hist(w.resultsDB['ensemble_stats'][generation_count]['scores'], 50, normed=1, histtype='stepfilled')
	P.setp(patches, 'facecolor', 'r', 'alpha', 0.75)
	P.show()

def plotScoreProgress( w ):
	if not w.resultsDB.has_key('ensemble_stats'):
		return

	try:
		import pylab as P
	except:
		tkMessageBox.showerror("Error","Could not import matplotlib's pylab",parent=w)
		return

	generations, best_scores, avg_scores, score_deviations = [],[],[],[]
	for (i,(scores,ratio,targets)) in enumerate(w.resultsDB['ensemble_stats']):
		generations.append( i )
		best_scores.append( scores[0] )
		avg_scores.append( scores[1] )
		score_deviations.append( scores[2] )

	P.plot( generations, avg_scores, lw=2, c='b' )
	P.errorbar( generations, avg_scores, yerr=score_deviations, fmt='o', c='b', label='Average' )
	P.plot( generations, best_scores, lw=2, c='r')
	P.scatter( generations, best_scores, label='Best', marker='o', c='r' )
	P.ion()
	P.show()

	return

