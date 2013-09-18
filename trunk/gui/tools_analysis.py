import os
import shelve
import Tkinter as tk
import tkFileDialog
import tkMessageBox

from threading		import Thread
from Queue			import Queue, Empty

from win_options	import OptionsWindow

def openRunDir( w, path ):

	p1 = os.path.join(path,'mesmer_log.db')
	p2 = os.path.join(path,'mesmer_log.db.db')

	if(not os.path.exists(p1) and not os.path.exists(p2)):
		tkMessageBox.showerror("Error","Could not find MESMER results DB in \"%s\"" % path,parent=w)
		return

	w.activeDir.set(path)
	w.currentSelection = [None,None,None]
	w.openLogWindow()
	updateGenerationList(w, path)
	w.statusText.set('Opened existing run')

def connectToRun( w, path, pHandle ):

	p1 = os.path.join(path,'mesmer_log.db')
	p2 = os.path.join(path,'mesmer_log.db.db')

	if(w.connectCounter > 10): # try for ten seconds to find the mesmer results DB
		tkMessageBox.showerror("Error","Could not find MESMER results DB in \"%s\". Perhaps MESMER crashed?" % path,parent=w)
		return

	if(not os.path.exists(p1) and not os.path.exists(p2)):
		w.connectCounter+=1
		w.updateHandle = w.after( 1000, connectToRun, *(w,path,pHandle) )
		return

	try:
		w.resultsDB = shelve.open( os.path.join(path,'mesmer_log.db'), 'r' )
	except:
		tkMessageBox.showerror("Error","Error loading the MESMER log database from \"%s\"." % path,parent=w)
		return

	w.activeDir.set(path)
	w.currentSelection = [None,None,None]

	def getMESMEROutput( out, queue ):
		for line in iter(out.readline, b''):
			queue.put(line)
		out.close()

	w.MESMEROutput_Q = Queue()
	w.MESMEROutput_T = Thread(target=getMESMEROutput, args=(pHandle.stdout, w.MESMEROutput_Q))
	w.MESMEROutput_T.daemon = True
	w.MESMEROutput_T.start()

	w.openLogWindow( True )
	w.updateHandle = w.after( 1000, updateWindowResults, *(w,path,pHandle) )
	w.activeDirEntry.config(state=tk.DISABLED)
	w.activeDirButton.config(state=tk.DISABLED)

def updateWindowResults( w, path, pHandle ):

	pHandle.poll()
	if(pHandle.returncode == None):
		w.abortButton.config(state=tk.NORMAL)
	elif(pHandle.returncode == 0):
		w.abortButton.config(state=tk.DISABLED)
		w.statusText.set('Finished')
		return
	else:
		tkMessageBox.showerror("Error","MESMER exited with error code %i. Please check the output log for more information." % pHandle.returncode,parent=w)
		w.abortButton.config(state=tk.DISABLED)
		w.statusText.set('Error')
		return

	updateGenerationList( w, path )

	w.updateHandle = w.after( 1000, updateWindowResults, *(w,path,pHandle) )

	try:
		while(True):
			line = w.MESMEROutput_Q.get_nowait()
			if( 'Reading target file' in line):
				w.statusText.set('Reading targets...')
			elif( 'Component loading progress' in line):
				w.statusText.set('Loading components...')
			elif( 'Optimizing parent component ratios' in line):
				w.statusText.set('Optimizing component ratios...')
			elif( 'Optimizing offspring component ratios' in line):
				w.statusText.set('Optimizing component ratios...')
			elif( 'Calculating best fit statistics' in line):
				w.statusText.set('Finding best fit intervals...')

			w.logWindow.logText.insert(tk.END,line)
	except:
		return

	return

def updateGenerationList( w, path ):
	try:
		w.resultsDB = shelve.open( os.path.join(path,'mesmer_log.db'), 'r' )
	except:
		return

	# append new generations to the list
	if(w.resultsDB.has_key('ensemble_stats') and len(w.resultsDB['ensemble_stats']) > w.generationsList.size()):
		string = "%s\t\t\t%s\t%s\t%s" % (
			"%05i" % (len(w.resultsDB['ensemble_stats']) -1),
			"%.3e" % w.resultsDB['ensemble_stats'][-1]['total'][0],
			"%.3e" % w.resultsDB['ensemble_stats'][-1]['total'][1],
			"%.3e" % w.resultsDB['ensemble_stats'][-1]['total'][2]
			)
		w.generationsList.insert(tk.END, string )
	return

def setGenerationSel( w, evt=None ):
	if(len(w.generationsList.curselection())<1):
		return
	w.currentSelection[0] = int(w.generationsList.curselection()[0])

	w.targetsList.delete(0, tk.END)
	for name in w.resultsDB['ensemble_stats'][w.currentSelection[0] ]['target']:
		string = "%s\t%s\t%s\t%s" % (
			name[:16].ljust(16),
			"%.3e" % w.resultsDB['ensemble_stats'][ w.currentSelection[0] ]['target'][name][0],
			"%.3e" % w.resultsDB['ensemble_stats'][ w.currentSelection[0] ]['target'][name][1],
			"%.3e" % w.resultsDB['ensemble_stats'][ w.currentSelection[0] ]['target'][name][2]
			)
		w.targetsList.insert(tk.END, string )

	w.targetsList.selection_set(0)
	w.targetsList.see(0)
	setTargetSel( w )
	setWidgetAvailibility( w )

def setTargetSel( w, evt=None ):
	if(len(w.targetsList.curselection())<1):
		return

	for (i,name) in enumerate(w.resultsDB['ensemble_stats'][ w.currentSelection[0] ]['target'].keys()):
		if(i == int(w.targetsList.curselection()[0])):
			w.currentSelection[1] = name

	w.restraintsList.delete(0, tk.END)
	for type in w.resultsDB['restraint_stats'][ w.currentSelection[0] ]:
		if(type == 'Total'):
			break
		string = "%s\t%s\t%s\t%s" % (
		type.ljust(16),
		"%.3e" % w.resultsDB['restraint_stats'][ w.currentSelection[0] ][type][ w.currentSelection[1] ][0],
		"%.3e" % w.resultsDB['restraint_stats'][ w.currentSelection[0] ][type][ w.currentSelection[1] ][1],
		"%.3e" % w.resultsDB['restraint_stats'][ w.currentSelection[0] ][type][ w.currentSelection[1] ][2]
		)
		w.restraintsList.insert(tk.END, string )

	w.restraintsList.selection_set(0)
	w.restraintsList.see(0)
	setRestraintSel( w )
	setWidgetAvailibility( w )

def setRestraintSel( w,evt=None ):
	if(len(w.restraintsList.curselection())<1):
		return

	for (i,type) in enumerate(w.resultsDB['restraint_stats'][ w.currentSelection[0] ].keys()):
		if(i == int(w.restraintsList.curselection()[0])):
			w.currentSelection[2] = type

	path = (os.path.join(w.activeDir.get(), 'restraints_%s_%s_%05i.out' % (w.currentSelection[1],w.currentSelection[2],int(w.currentSelection[0]))))
	if(os.path.exists(path)):
		w.fitPlotButton.config(state=tk.NORMAL)
	else:
		w.fitPlotButton.config(state=tk.DISABLED)

def setWidgetAvailibility( w ):
	if( w.currentSelection[0] == None):
		w.histogramPlotButton.config(state=tk.DISABLED)
	else:
		w.histogramPlotButton.config(state=tk.NORMAL)

	if( w.currentSelection[0] == None or w.currentSelection[1] == None ):
		w.correlationPlotButton.config(state=tk.DISABLED)
		w.writePDBsButton.config(state=tk.DISABLED)
	else:
		w.correlationPlotButton.config(state=tk.NORMAL)
		w.writePDBsButton.config(state=tk.NORMAL)

	if( w.currentSelection[0] == None or w.currentSelection[1] == None or w.attributeTable.get() == ''):
		w.attributePlotButton.config(state=tk.DISABLED)
		w.attributePlotButton.config(state=tk.DISABLED)
	else:
		w.attributePlotButton.config(state=tk.NORMAL)
		w.attributePlotButton.config(state=tk.NORMAL)






