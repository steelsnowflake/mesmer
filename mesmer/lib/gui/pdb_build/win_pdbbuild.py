import os
import shutil
import Tkinter as tk
import tkMessageBox
import tkFileDialog
import tkFont

from multiprocessing import Queue

from ... setup_functions import open_user_prefs
from .. tools_general import askNewDirectory
from .. tools_multiprocessing import PluginParallelizer
from .. tools_TkTooltip import ToolTip

import mcpdb_generator
import mcpdb_objects
import mcpdb_utilities

_PDB_generator_timer = 500 # in ms
_PDB_generator_format= "%05i.pdb"

class PDBBuildWindow(tk.Frame):
	def __init__(self, master=None):
		self.master = master
		self.master.title('PDB Generator')

		self.master.resizable(width=False, height=False)
		self.master.protocol('WM_DELETE_WINDOW', self.close)

		tk.Frame.__init__(self,master)
		self.pack(expand=True,fill='both',padx=6,pady=6)
		self.pack_propagate(True)
		
		self.createWidgets()
		
		self.Generator = None
		
		try:
			self.prefs = open_user_prefs()
		except Exception as e:
			tkMessageBox.showerror("Error",'Cannot read MESMER preferences file: %s' % (e),parent=self)
			self.master.destroy()
		
	def close(self):
		if self.Generator == None:
			self.master.destroy()
			return
		elif tkMessageBox.askquestion("Cancel", "Stop generating structures?", icon='warning',parent=self) == 'yes':
			self.stopGenerator(abort=True)
			return

	def createWidgets(self):
		self.infoFont = tkFont.Font(slant=tkFont.ITALIC)

		self.pdbLoadButton = tk.Button(self,text='Load PDB...',command=self.loadPDB)
		self.pdbLoadButton.grid(row=0,column=0,sticky=tk.E+tk.W)
		
		self.f_header = tk.LabelFrame(self,text='Info')
		self.f_header.grid(row=1,sticky=tk.E+tk.W)
		self.pdbName = tk.StringVar()
		self.pdbNameLabel = tk.Label(self.f_header,textvariable=self.pdbName,font=self.infoFont)
		self.pdbNameLabel.grid(column=0,row=0,sticky=tk.W)

		self.pdbInfo = tk.StringVar()
		self.pdbInfoLabel = tk.Label(self.f_header,textvariable=self.pdbInfo,font=self.infoFont)
		self.pdbInfoLabel.grid(column=0,row=1,sticky=tk.W)

		self.f_groups = tk.Frame(self)
		self.f_groups.grid(row=2,sticky=tk.E+tk.W)

		self.groupCounter = 0
		self.groupFrames = []
		self.groupLabels = []
		self.groupChainLabels = []
		self.groupChainLabelTTs = []
		self.groupChainStarts = []
		self.groupChainStartEntries = []
		self.groupChainEnds = []
		self.groupChainEndEntries = []
		self.groupRemoveButtons = []
		
		self.addRigidGroupButton = tk.Button(self,text='Add Rigid Group',command=lambda: self.createWidgetRow(),state=tk.DISABLED)
		self.addRigidGroupButton.grid(row=3,column=0,sticky=tk.E+tk.W)
		self.addRigidGroupButtonTT = ToolTip(self.addRigidGroupButton,follow_mouse=0,text='Create a new group of residues to hold rigid relative to one another.')

		self.f_options = tk.LabelFrame(self,text='Options')
		self.f_options.grid(row=4,sticky=tk.E+tk.W)

		self.pdbPrefix = tk.StringVar()
		self.pdbPrefixLabel = tk.Label(self.f_options,text="Output prefix:")
		self.pdbPrefixLabel.grid(row=0,column=0,sticky=tk.W)
		self.pdbPrefixLabelTT = ToolTip(self.addRigidGroupButton,follow_mouse=0,text='Define the prefix to be appended to all generated PDBs.')
		self.pdbPrefixEntry = tk.Entry(self.f_options,textvariable=self.pdbPrefix)
		self.pdbPrefixEntry.grid(row=0,column=1,sticky=tk.W)

		self.pdbNumber = tk.IntVar()
		self.pdbNumber.set( 10 )
		self.pdbNumberLabel = tk.Label(self.f_options,text="Number of PDBs:")
		self.pdbNumberLabel.grid(row=1,column=0,sticky=tk.W)
		self.pdbNumberLabelTT = ToolTip(self.pdbNumberLabel,follow_mouse=0,text='The number of PDBs to be generated.')
		self.pdbNumberEntry = tk.Entry(self.f_options,textvariable=self.pdbNumber)
		self.pdbNumberEntry.grid(row=1,column=1,sticky=tk.W)

		self.fixFirstGroup = tk.IntVar()
		self.fixFirstGroup.set(1)
		self.fixFirstGroupCheckbox = tk.Checkbutton(self.f_options,text='Fix first rigid group',variable=self.fixFirstGroup)
		self.fixFirstGroupCheckbox.grid(row=2,column=0,columnspan=2,sticky=tk.W)
		self.fixFirstGroupCheckboxTT = ToolTip(self.fixFirstGroupCheckbox,follow_mouse=0,text='If checked, the first rigid group will be fixed in space. Otherwise, the final orientation of the entire complex will be randomly tumbled.')

		self.useRamachandran = tk.IntVar()
		self.useRamachandran.set(0)
		self.useRamachandranCheckbox = tk.Checkbutton(self.f_options,text='Use Ramachandran linkers',variable=self.useRamachandran)
		self.useRamachandranCheckbox.grid(row=3,column=0,columnspan=2,sticky=tk.W)
		self.useRamachandranCheckboxTT = ToolTip(self.useRamachandranCheckbox,follow_mouse=0,text='If checked, use Phi and Psi angles for the backbone taken from a ramachandran probability map.')

		self.clashToleranceLabel = tk.Label(self.f_options,text="CA-CA tolerance: ")
		self.clashToleranceLabel.grid(row=4,column=0,sticky=tk.E)
		self.clashToleranceLabelTT = ToolTip(self.clashToleranceLabel,follow_mouse=0,text='Used to remove steric clashes. Ensures that any generated PDB will not have any CA atoms within this cutoff of any other CA atoms.')
		self.clashTolerance = tk.DoubleVar()
		self.clashTolerance.set(3.0)
		self.clashToleranceEntry = tk.Entry(self.f_options,textvariable=self.clashTolerance,width=3)
		self.clashToleranceEntry.grid(row=4,column=1,sticky=tk.W)

		self.f_footer = tk.Frame(self,borderwidth=0)
		self.f_footer.grid(row=5)

		self.generateButton = tk.Button(self.f_footer,text='Generate PDBs...',default=tk.ACTIVE,command=self.startGenerator,state=tk.DISABLED)
		self.generateButton.grid(column=1,row=5,sticky=tk.W,pady=4)
		self.generateButtonTT = ToolTip(self.generateButton,follow_mouse=0,text='Start generating PDBs.')
		self.cancelButton = tk.Button(self.f_footer,text='Close',command=self.close)
		self.cancelButton.grid(column=2,row=5,sticky=tk.E,pady=4)
		self.cancelButtonTT = ToolTip(self.cancelButton,follow_mouse=0,text='Stop PDB generation, and close the window.')
		
	def createWidgetRow(self,initial=False):		
		self.groupFrames.append( tk.LabelFrame(self.f_groups,text="Rigid Group %i"%(self.groupCounter+1)) )
		self.groupFrames[-1].grid(row=self.groupCounter%3,column=int(self.groupCounter/3),ipadx=6,ipady=6)
		
		self.groupLabels.append( [tk.Label(self.groupFrames[-1],text=text) for text in ('Chain:','Start residue:','End residue:')] )
		for i,label in enumerate(self.groupLabels[-1]):
			label.grid(row=i,column=0,sticky=tk.E)
		
		self.groupChainLabels.append( [] )
		self.groupChainLabelTTs.append( [] )
		self.groupChainStarts.append( [] )
		self.groupChainStartEntries.append( [] )
		self.groupChainEnds.append( [] )
		self.groupChainEndEntries.append( [] )

		for i,chain in enumerate(self.pdbChains):
			self.groupChainLabels[-1].append( tk.Label(self.groupFrames[-1],text=chain ) )
			self.groupChainLabels[-1][-1].grid(column=i+1,row=0)
			self.groupChainLabelTTs.append( ToolTip(self.groupChainLabels[-1][-1],follow_mouse=0,text='Section of polypeptide to keep fixed in space with respect to the other polypeptide segments in this Rigid Group.') )

			self.groupChainStarts[-1].append( tk.StringVar() )
			self.groupChainStartEntries[-1].append( tk.Entry(self.groupFrames[-1],width=3,textvariable=self.groupChainStarts[-1][-1]) )
			self.groupChainStartEntries[-1][-1].grid(column=i+1,row=1)
			
			self.groupChainEnds[-1].append( tk.StringVar() )
			self.groupChainEndEntries[-1].append( tk.Entry(self.groupFrames[-1],width=3,textvariable=self.groupChainEnds[-1][-1]) )
			self.groupChainEndEntries[-1][-1].grid(column=i+1,row=2)
			
#			if initial:
			self.groupChainStarts[-1][-1].set( self.pdbChains[chain][0] )
			self.groupChainEnds[-1][-1].set( self.pdbChains[chain][1] )

		nchains = len(self.pdbChains)
		self.groupRemoveButtons.append( tk.Button(self.groupFrames[-1],text='Remove Group') )
		self.groupRemoveButtons[-1].grid(column=0,row=3,columnspan=nchains+1,sticky=tk.E+tk.W)
		self.groupRemoveButtons[-1].bind('<ButtonRelease-1>',self.clearWidgetRow)
		
		self.groupCounter+=1

	def clearWidgetRow(self,event):
		showinfo = True
		for i,button in enumerate(self.groupRemoveButtons):
			if button is event.widget:

				for j,chain in enumerate(self.pdbChains):
					if self.groupChainStarts[i][j].get() != '' or self.groupChainEnds[i][j].get() != '':
						showinfo = False
						
					self.groupChainStarts[i][j].set('')
					self.groupChainEnds[i][j].set('')
					
		if showinfo:
			tkMessageBox.showinfo("Note","Rigid groups without any specified start or end residues are automatically ignored",parent=self)
		
	def destroyWidgetRows(self):
		for i in range(self.groupCounter):
			self.groupFrames[i].destroy()
			
			for j in range(3):
				self.groupLabels[i][j].destroy()
			
			for j in range(len(self.pdbChains)):
				self.groupChainLabels[i][j].destroy()
				self.groupChainStartEntries[i][j].destroy()
				self.groupChainEndEntries[i][j].destroy()

				del self.groupChainStarts[i][j]
				del self.groupChainEnds[i][j]

			self.groupRemoveButtons[i].destroy()
		
		self.groupFrames = []
		self.groupLabels = []
		self.groupChainLabels = []
		self.groupChainStarts = []
		self.groupChainStartEntries = []
		self.groupChainEnds = []
		self.groupChainEndEntries = []
		self.groupRemoveButtons = []

		self.groupCounter = 0
	
	#	
	# action functions
	#
	
	def updatePDBInfo(self,name=None,info=None):
		if name != None:
			self.pdbName.set( name )
		if info != None:
			self.pdbInfo.set( info )
		self.update_idletasks()
	
	def loadPDB(self):
		tmp = tkFileDialog.askopenfilename(title='Select PDB coordinate file:',parent=self,filetypes=[('PDB',"*.pdb")],initialdir=self.prefs['last_open_dir'])
		if(tmp == ''):
			return
		self.prefs['last_open_dir'] = os.path.dirname(tmp)
		
		self.destroyWidgetRows()
		self.updatePDBInfo("Checking PDB:","Looking for discontinuities..." )

		err,msg = mcpdb_utilities.check_PDB(tmp)
		if err > 0:
			tkMessageBox.showerror("Error",'Problem with PDB file: %s' % (msg),parent=self)
			self.updatePDBInfo("PDB check failed.","" )
			return
			
		self.updatePDBInfo(None,"Looking for steric clashes...")
		
		model = mcpdb_objects.TransformationModel( tmp, [], 0 )
		clashes = mcpdb_objects.ModelEvaluator( model, clash_radius=self.clashTolerance.get() ).count_clashes()
		if clashes > 0:
			tkMessageBox.showerror("Error","Problem with PDB file: %i CA-CA clashes already exist. Check your PDB's sterics and try again." % (clashes),parent=self)
			self.updatePDBInfo( "PDB check failed.","")
			return
	
		self.pdbChains = mcpdb_utilities.get_chain_info(tmp)
		self.pdb = tmp
		self.pdbName.set( os.path.basename(self.pdb) )
		
		lchains = self.pdbChains.keys()
		nchains = len(lchains)
		if nchains == 1:
			self.updatePDBInfo(None,"1 chain, %i residues"%(1+self.pdbChains[lchains[0]][1]-self.pdbChains[lchains[0]][0]) )
		else:
			self.updatePDBInfo(None,"%i chains: %s"%(nchains,",".join(lchains)) )
					
		self.createWidgetRow(initial=True)
		self.addRigidGroupButton.config(state=tk.NORMAL)
		self.generateButton.config(state=tk.NORMAL)
	
	def startGenerator(self):
		groups = []
		for i in xrange(self.groupCounter):
			groups.append( [] )
			
			for j,chain in enumerate(self.pdbChains):
				if self.groupChainStarts[i][j].get() != '' and self.groupChainEnds[i][j].get() != '':
					start	= int(self.groupChainStarts[i][j].get())
					end		= int(self.groupChainEnds[i][j].get())
					groups[-1].append( (chain,start,end) )
			
			if groups[-1] == []:
				groups.pop( len(groups) -1 )
			
		error,msg = mcpdb_utilities.check_groups( self.pdb, groups )
		if error:
			tkMessageBox.showerror("Error",'Problem with group definitions: %s' % (msg),parent=self)
			return
		
		path = askNewDirectory(self,title='Select location to save PDBs:',initialfile='PDBs',initialdir=self.prefs['last_open_dir'])
		if path == '':
			return
		self.prefs['last_open_dir'] = os.path.dirname(path)
	
		notified = False
		self.updatePDBInfo(None,"Scanning folder for PDBs...")

		indices = []
		for i in range(self.pdbNumber.get()):
			if os.path.exists(os.path.join(path,self.pdbPrefix.get()+(_PDB_generator_format%(i)))):
				if not notified:
					if not tkMessageBox.askokcancel("Warning", "Folder already contains PDBs, PDB generator will start where previous iterations left off.", icon='warning', parent=self) != 'yes':
						self.updatePDBInfo(None,"Aborted.")				
						return
					notified = True
			else:
				indices.append(i)
		
		self.updatePDBInfo("Generating PDBs:","Initializing generators...")
		self.plugin = mcpdb_generator.PDBGenerator()
		self.plugin.setup(
			self.pdb,
			groups,
			outputdir = path,
			prefix = self.pdbPrefix.get(),
			format = _PDB_generator_format,
			fix_first = (self.fixFirstGroup.get() == 1),
			use_rama = (self.useRamachandran.get() == 1),
			eval_kwargs={'clash_radius':self.clashTolerance.get()})

		self.Generator = PluginParallelizer(self.plugin,threads=self.prefs['cpu_count'])
		self.Generator.put(indices)
		self.counter = 0

		self.updatePDBInfo(None,"Generating structures...")
		self.Generator.afterID = self.after( _PDB_generator_timer, self.updateGenerator )

	def updateGenerator(self):
		for index in self.Generator.get():
			self.counter += 1
		
		if self.counter == self.pdbNumber.get():
			self.stopGenerator()
			return
		
		self.updatePDBInfo(None,"Generated structure %i"%self.counter)
		self.Generator.afterID = self.after( _PDB_generator_timer, self.updateGenerator )
	
	def stopGenerator(self,abort=False):
		if self.Generator != None:
			if abort:
				try:
					self.after_cancel(self.Generator.afterID)
				except AttributeError:
					pass
				self.Generator.abort()
				self.updatePDBInfo("Aborted.","")
			else:
				self.Generator.stop()
				self.updatePDBInfo("Done.","")
			self.Generator = None
