import os

import tkMessageBox
import tkFileDialog

from .. exceptions			import *
from tools_plugin			import *

def extractDataFromFile( file ):
	if( file == '' ):
		return ''

	try:
		f = open( file )
	except:
		tkMessageBox.showerror("Missing Data","There was an error reading the data file \"%s\"" % (file))
		return None

	text = ''
	for l in f:
		if(l.strip() != ''):
			text+="%s\n" % l.strip()
			
	f.close()

	return text

def makeTargetFromWindow( w ):
	name	= w.targetName.get().replace(' ','_')
	text = "NAME\t%s\n#\t%s\n\n" % (name,w.targetComments.get())

	type_counters = {}
	for i in range(w.rowCounter):
		type	= w.widgetRowTypes[i].get()
		weight	= w.widgetRowWeights[i].get()
		data	= extractDataFromFile( w.widgetRowFiles[i].get() )
		comment	= os.path.basename( w.widgetRowFiles[i].get() )
		if( data == None ):
			return None

		try:
			for (j,t) in enumerate(w.plugin_types):
				if(type in t):
					opts = ' '.join(makeListFromOptions( w.widgetRowOptions[i][j] ))
		except Exception as e:
			tkMessageBox.showwarning("Missing Option","Error while saving options for \"%s\" data.\n\n%s" % (type,e))
			return None

		if(type in type_counters):
			type_counters[type]+=1
		else:
			type_counters[type]=0

		text+="%s%i\t%f\t%s\t#%s\n%s\n\n" % (type,type_counters[type],weight,opts,comment,data)

	name = w.targetName.get().replace(' ','_')
	handle = tkFileDialog.asksaveasfile(defaultextension='.target',initialfile="%s.target"%(name),parent=w)
	if(handle != None):
		handle.write(text)
		handle.close()
	else:
		return False

	tkMessageBox.showinfo("Saved","Target file saved successfully.",parent=w)
	return True