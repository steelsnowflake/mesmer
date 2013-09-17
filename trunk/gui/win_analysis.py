import Tkinter as tk
import tkFileDialog

from gui.tools_analysis	import *

class AnalysisWindow(tk.Frame):
	def __init__(self, master, path=None):
		self.master = master
		self.master.title('MESMER Run / Analysis')
		self.master.resizable(width=False, height=False)

		tk.Frame.__init__(self,master)
		self.grid()

		self.loadPrefs()

		self.createControlVars()
		self.createWidgets()
		self.createToolTips()

		self.updateWidgets()

		loadResultsLog(self,'/Users/ihms/Dropbox/mesmer/docs/tutorial/MESMER_Results')

	def loadPrefs(self):
		try:
			self.prefs = shelve.open( os.path.join(os.getcwd(),'gui','preferences') )
		except:
			tkMessageBox.showerror("Error",'Cannot read or create preferences file. Perhaps MESMER is running in a read-only directory?',parent=self)
			self.master.destroy()

	def close(self):
		self.master.destroy()

	def setWorkFolder(self):
		tmp = tkFileDialog.askdirectory(title='Select Results Directory',mustexist=True,parent=self)
		if(tmp != ''):
			loadResultsLog(self,tmp)

	def setAttributeTable(self):
		tmp = tkFileDialog.askopenfilename(title='Select PDB attribute table',parent=self)
		if(tmp != ''):
			self.attributeTable.set(tmp)
			setWidgetAvailibility(self,0)

	def updateWidgets(self):
		setWidgetAvailibility(self,0)
		pass

	def createControlVars(self):
		self.activeDir = tk.StringVar()
		self.statusText = tk.StringVar()
		self.statusText.set('Finished')
		self.attributeTable = tk.StringVar()

	def createWidgets(self):
		self.container = tk.Frame(self)
		self.container.grid(in_=self,padx=6,pady=6)

		self.f_logo = tk.Frame(self.container)
		self.f_logo.grid(column=0,row=0,columnspan=3,sticky=tk.W,pady=(0,8))
		self.LogoImage = tk.PhotoImage(file='gui/mesmer_logo.gif')
		self.LogoLabel = tk.Label(self.f_logo,image=self.LogoImage)
		self.LogoLabel.pack(side=tk.LEFT)
		self.versionLabel = tk.Label(self.f_logo,text='GUI version 2013.08.26')
		self.versionLabel.pack(side=tk.LEFT,anchor=tk.NE)

		self.activeDirLabel = tk.Label(self.container,text='Work Folder:')
		self.activeDirLabel.grid(in_=self.container,column=0,row=1,sticky=tk.E)
		self.activeDirEntry = tk.Entry(self.container,textvariable=self.activeDir,width=30)
		self.activeDirEntry.grid(in_=self.container,column=1,row=1,sticky=tk.W)
		self.activeDirButton = tk.Button(self.container,text='Set...',command=self.setWorkFolder)
		self.activeDirButton.grid(in_=self.container,column=2,row=1,sticky=tk.W)

		self.statusTextLabel = tk.Label(self.container,text='Run Status:')
		self.statusTextLabel.grid(in_=self.container,column=0,row=2,sticky=tk.E,pady=(0,4))
		self.statusTextEntry = tk.Label(self.container,textvariable=self.statusText)
		self.statusTextEntry.grid(in_=self.container,column=1,row=2,sticky=tk.W,pady=(0,4))
		self.abortButton = tk.Button(self.container,text='Abort',command=self.setWorkFolder,state=tk.DISABLED)
		self.abortButton.grid(in_=self.container,column=2,row=2,sticky=tk.W,pady=(0,4))

		self.f_generations = tk.LabelFrame(text='Generations')
		self.f_generations.grid(in_=self.container,column=0,row=3,columnspan=3)
		self.generationsList = tk.Listbox(self.f_generations,width=48,height=6,selectmode=tk.BROWSE)
		self.generationsList.grid(in_=self.f_generations,sticky=tk.W,padx=(6,0),pady=(2,0),column=0,row=0)
		self.generationsListScroll = tk.Scrollbar(self.f_generations,orient=tk.VERTICAL)
		self.generationsListScroll.grid(in_=self.f_generations,column=2,row=0,sticky=tk.W+tk.N+tk.S,pady=(2,0))
		self.generationsList.config(yscrollcommand=self.generationsListScroll.set)
		self.generationsListScroll.config(command=self.generationsList.yview)
		self.generationsList.bind('<<ListboxSelect>>',lambda evt: setGenerationSel(self,evt))
		self.histogramPlotButton = tk.Button(self.f_generations,text='Ensemble Histogram...')
		self.histogramPlotButton.grid(in_=self.f_generations,column=0,row=2,padx=(6,0),pady=(0,4),sticky=tk.W)

		self.f_targets = tk.LabelFrame(text='Targets')
		self.f_targets.grid(in_=self.container,column=0,row=4,columnspan=3)
		self.targetsList = tk.Listbox(self.f_targets,width=48,height=5,selectmode=tk.BROWSE)
		self.targetsList.grid(in_=self.f_targets,sticky=tk.W,padx=(6,0),pady=(2,0),column=0,row=0,columnspan=5)
		self.targetsListScroll = tk.Scrollbar(self.f_targets,orient=tk.VERTICAL)
		self.targetsListScroll.grid(in_=self.f_targets,column=6,row=0,sticky=tk.W+tk.N+tk.S,pady=(2,0))
		self.targetsList.config(yscrollcommand=self.targetsListScroll.set)
		self.targetsListScroll.config(command=self.targetsList.yview)
		self.targetsList.bind('<<ListboxSelect>>',lambda evt: setTargetSel(self,evt))

		self.attributePlotButton = tk.Button(self.f_targets,text='Attribute Plot...',state=tk.DISABLED)
		self.attributePlotButton.grid(in_=self.f_targets,column=0,row=1,padx=(6,0),sticky=tk.W)
		self.correlationPlotButton = tk.Button(self.f_targets,text='Correlation Plot...',state=tk.DISABLED,command=lambda: makeCorrelationPlot(self))
		self.correlationPlotButton.grid(in_=self.f_targets,column=1,row=1,columnspan=2)
		self.writePDBsButton = tk.Button(self.f_targets,text='Write PDBs...')
		self.writePDBsButton.grid(in_=self.f_targets,column=3,row=1,columnspan=2)

		self.attributeTableEntry = tk.Entry(self.f_targets,textvariable=self.attributeTable,width=30)
		self.attributeTableEntry.grid(in_=self.f_targets,padx=(6,0),pady=(0,4),column=0,row=2,columnspan=2,sticky=tk.W)
		self.attributeTableButton = tk.Button(self.f_targets,text='Set...',command=self.setAttributeTable)
		self.attributeTableButton.grid(in_=self.f_targets,pady=(0,4),column=2,row=2,sticky=tk.W,columnspan=3)

		self.f_restraints = tk.LabelFrame(text='Restraints')
		self.f_restraints.grid(in_=self.container,column=0,row=5,columnspan=3)
		self.restraintsList = tk.Listbox(self.f_restraints,width=48,height=5,selectmode=tk.BROWSE)
		self.restraintsList.grid(in_=self.f_restraints,sticky=tk.W,padx=(6,0),pady=(2,0),column=0,row=0)
		self.restraintsListScroll = tk.Scrollbar(self.f_restraints,orient=tk.VERTICAL)
		self.restraintsListScroll.grid(in_=self.f_restraints,column=1,row=0,sticky=tk.W+tk.N+tk.S,pady=(2,0))
		self.restraintsList.config(yscrollcommand=self.restraintsListScroll.set)
		self.restraintsListScroll.config(command=self.restraintsList.yview)
		self.restraintsList.bind('<<ListboxSelect>>',lambda evt: setRestraintSel(self,evt))

		self.fitPlotButton = tk.Button(self.f_restraints,text='Fit Plot...',width=12)
		self.fitPlotButton.grid(in_=self.f_restraints,column=0,row=1,padx=(6,0),pady=(0,4),sticky=tk.W)

		self.f_footer = tk.Frame(self.container)
		self.f_footer.grid(in_=self.container,column=0,row=6,columnspan=3)

		self.cancelButton = tk.Button(self.f_footer,text='Cancel',width=8,command=self.close)
		self.cancelButton.grid(in_=self.f_footer,column=0,row=0,pady=(4,0))

	def createToolTips(self):
		pass
