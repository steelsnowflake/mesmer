import os
import glob
import shelve
import Tkinter as tk
import tkMessageBox
import tkFileDialog
import copy

from lib.functions 			import get_input_blocks
from gui.tools_TkTooltip	import ToolTip
from gui.tools_target		import makeTargetFromWindow
from gui.tools_component	import makeComponentsFromWindow
from gui.win_saxscalc		import SAXSCalcWindow

class ComponentsWindow(tk.Frame):
	def __init__(self, master=None):
		self.master = master
		self.master.geometry('540x372+100+100')
		self.master.title('Component Builder')
		self.master.resizable(width=False, height=False)

		tk.Frame.__init__(self,master,width=540,height=372)
		self.grid()
		self.grid_propagate(0)

		self.loadPrefs()

		self.createControlVars()
		self.createWidgets()
		self.createToolTips()
		self.updateWidgets()

	def loadPrefs(self):
		self.Ready = False

		try:
			from gui.plugin_types import types
			self.types = types
		except:
			tkMessageBox.showerror("Error",'Could not load plugin types description. Please reinstall MESMER.',parent=self)
			self.master.destroy()

		try:
			self.prefs = shelve.open( os.path.join(os.getcwd(),'gui','preferences') )
		except:
			tkMessageBox.showerror("Error",'Cannot read or create preferences file. Perhaps MESMER is running in a read-only directory?',parent=self)
			self.master.destroy()

	def loadTarget(self):
		tmp = tkMessageBox.askquestion("Load Target","Are you sure you would like to load an existing target as a template?\nThis will clear your current entries.", icon='warning',parent=self)
		if(tmp != 'yes'):
			return
		tmp = tkFileDialog.askopenfilename(title='Select target file:',parent=self)
		if(tmp == ''):
			return
		blocks = get_input_blocks(tmp)
		if(len(blocks)<2):
			return

		# remove existing rows
		for i in range(self.rowCounter):
			self.widgetRowChecks[i].set(1)
		self.destroyWidgetRows()

		for b in blocks:
			type = b['type'][0:4]
			if type in self.types.keys():
				self.createWidgetRow()
				self.widgetRowTypes[-1].set( type )

	def makeComponents(self):
		if( makeComponentsFromWindow(self) ):
			self.closeWindow()

	def loadComponentPDBs(self):
		tmp = tkFileDialog.askdirectory(title='Select folder containing PDBs:',mustexist=True,parent=self)
		if(tmp != ''):
			self.prefs['last_pdb_dir'] = tmp
			files = glob.glob(os.path.join(tmp,'*.pdb'))
			for f in files:
				self.componentPDBsList.insert(tk.END, f)
		self.setListStates()

	def removeComponentPDBs(self):
		indexes = map(int, self.componentPDBsList.curselection())
		indexes.reverse()
		for i in indexes:
			self.componentPDBsList.delete(i)
		self.setListStates()

	def clearComponentPDBs(self):
		self.componentPDBsList.delete(0,tk.END)
		self.setListStates()

	def updateWidgets(self, evt=None):
		self.Ready = True

		if(self.Ready):
			self.saveButton.config(state=tk.ACTIVE)
		else:
			self.saveButton.config(state=tk.DISABLED)

	def setListStates(self, evt=None):
		indexes = map(int, self.componentPDBsList.curselection())
		all = self.componentPDBsList.get(0,tk.END)
		self.componentFoldersLabel.config(text=("%i/%i" % (len(indexes),len(all))))

		if(len(indexes)>0):
			self.removeComponentsButton.config(state=tk.NORMAL)
		else:
			self.removeComponentsButton.config(state=tk.DISABLED)

		if(len(all)>0):
			self.loadComponentsButton.config(state=tk.DISABLED)
			self.clearComponentsButton.config(state=tk.NORMAL)
		else:
			self.loadComponentsButton.config(state=tk.NORMAL)
			self.clearComponentsButton.config(state=tk.DISABLED)

	def openSAXSCalcWindow(self):
		pdbs = self.componentPDBsList.get(0,tk.END)
		if(len(pdbs)<1):
			return
		self.newWindow = tk.Toplevel(self)
		self.optWindow = SAXSCalcWindow(self.newWindow,pdbs,self.updateSAXSDir)
		self.newWindow.focus_set()
		self.newWindow.grab_set()
		self.newWindow.transient(self)
		self.newWindow.wait_window(self.newWindow)

	def updateSAXSDir(self,dir):
		for i in range(self.rowCounter):
			if(self.widgetRowTypes[i].get() == 'SAXS'):
				self.widgetRowFolders[i].set(dir)

	def attachDataFolder(self,evt):
		tmp = tkFileDialog.askdirectory(title='Select folder containing calculated data:',mustexist=True,parent=self)
		if(tmp == ''):
			return
		for (i,w) in enumerate(self.widgetRowFolderButtons):
			if w == evt.widget:
				break
		self.widgetRowFolders[i].set(tmp)
		self.updateWidgets()

	def closeWindow(self):
		self.prefs.close()
		self.master.destroy()

	def createToolTips(self):
		#self.createTargetTT 	= ToolTip(self.createTargetButton,		follow_mouse=0,text='Create a target file from experimental data')
		pass

	def createControlVars(self):
		self.widgetRowChecks = []
		self.widgetRowTypes = []
		self.widgetRowTypeOptions = []
		self.widgetRowFolders = []

	def createWidgets(self):
		self.f_filelist = tk.LabelFrame(self,text='Component PDBs')
		self.f_filelist.grid(in_=self,column=0,row=0,sticky=tk.W,ipady=4,ipadx=8,padx=8)

		self.componentPDBsList = tk.Listbox(self.f_filelist,width=50,height=10,selectmode=tk.EXTENDED)
		self.componentPDBsList.grid(in_=self.f_filelist,column=0,row=0,rowspan=4,padx=(6,0))
		self.componentPDBsList.bind('<<ListboxSelect>>',self.setListStates)
		self.componentPDBsYScroll = tk.Scrollbar(self.f_filelist,orient=tk.VERTICAL)
		self.componentPDBsYScroll.grid(in_=self.f_filelist,column=1,row=0,rowspan=4,padx=(0,4),sticky=tk.N+tk.S)
		self.componentPDBsList.config(yscrollcommand=self.componentPDBsYScroll.set)
		self.componentPDBsYScroll.config(command=self.componentPDBsList.yview)
		self.componentPDBsXScroll = tk.Scrollbar(self.f_filelist,orient=tk.HORIZONTAL)
		self.componentPDBsXScroll.grid(in_=self.f_filelist,column=0,row=4,sticky=tk.E+tk.W,padx=(6,0))
		self.componentPDBsList.config(xscrollcommand=self.componentPDBsYScroll.set)
		self.componentPDBsXScroll.config(command=self.componentPDBsList.xview)

		self.componentFoldersLabel = tk.Label(self.f_filelist,text='0/0')
		self.componentFoldersLabel.grid(in_=self.f_filelist,column=2,row=0,sticky=tk.NW)
		self.loadComponentsButton = tk.Button(self.f_filelist,text='Load...',command=self.loadComponentPDBs)
		self.loadComponentsButton.grid(in_=self.f_filelist,column=2,row=1,sticky=tk.SW)
		self.removeComponentsButton = tk.Button(self.f_filelist,text='Remove',state=tk.DISABLED,command=self.removeComponentPDBs)
		self.removeComponentsButton.grid(in_=self.f_filelist,column=2,row=2,sticky=tk.SW)
		self.clearComponentsButton = tk.Button(self.f_filelist,text='Clear',state=tk.DISABLED,command=self.clearComponentPDBs)
		self.clearComponentsButton.grid(in_=self.f_filelist,column=2,row=3,sticky=tk.NW)

		self.f_container = tk.LabelFrame(self,borderwidth=2,relief='groove',text='Calculated Data')
		self.f_container.grid(in_=self,sticky=tk.W,ipady=4,ipadx=8,padx=8)

		self.addRowButton = tk.Button(self.f_container,text='Add',command=self.createWidgetRow)
		self.addRowButton.grid(in_=self.f_container,column=0,row=0,sticky=tk.E)
		self.delRowButton = tk.Button(self.f_container,text='Remove',command=self.destroyWidgetRows)
		self.delRowButton.grid(in_=self.f_container,column=1,row=0,sticky=tk.W)
		self.calcSAXSButton = tk.Button(self.f_container,text='Calculate SAXS...',command=self.openSAXSCalcWindow)
		self.calcSAXSButton.grid(in_=self.f_container,column=2,row=0,sticky=tk.W,columnspan=2)

		self.rowHeaderSelectLabel = tk.Label(self.f_container,text='Select')
		self.rowHeaderSelectLabel.grid(in_=self.f_container,column=0,row=1)
		self.rowHeaderTypeLabel = tk.Label(self.f_container,text='Type')
		self.rowHeaderTypeLabel.grid(in_=self.f_container,column=1,row=1)
		self.rowHeaderFileLabel = tk.Label(self.f_container,text='Data Folder')
		self.rowHeaderFileLabel.grid(in_=self.f_container,column=2,row=1,sticky=tk.W)

		self.rowCounter = 0
		self.widgetRowCheckboxes = []
		self.widgetRowTypeMenus = []
		self.widgetRowFolderEntries = []
		self.widgetRowFolderButtons = []
		self.createWidgetRow()

		self.f_footer = tk.Frame(self,borderwidth=0)
		self.f_footer.grid(in_=self,row=2)

		self.openButton = tk.Button(self.f_footer,text='Load Target...',command=self.loadTarget)
		self.openButton.grid(in_=self.f_footer,column=0,row=0,sticky=tk.N+tk.S+tk.E,pady=8)
		self.saveButton = tk.Button(self.f_footer,text='Save Components...',default=tk.ACTIVE,command=self.makeComponents)
		self.saveButton.grid(in_=self.f_footer,column=1,row=0,sticky=tk.N+tk.S+tk.W,pady=8)
		self.cancelButton = tk.Button(self.f_footer,text='Cancel',command=self.closeWindow)
		self.cancelButton.grid(in_=self.f_footer,column=2,row=0,sticky=tk.N+tk.S+tk.E,pady=8,padx=20)

	def createWidgetRow(self):
		self.rowCounter+=1
		self.widgetRowChecks.append( tk.IntVar() )
		self.widgetRowCheckboxes.append( tk.Checkbutton(self.f_container,variable=self.widgetRowChecks[-1]) )
		self.widgetRowCheckboxes[-1].grid(in_=self.f_container,column=0,row=self.rowCounter+1)

		self.widgetRowTypeOptions.append( self.types.keys() )
		self.widgetRowTypes.append( tk.StringVar() )
		self.widgetRowTypes[-1].set( self.types.keys()[0] )
		self.widgetRowTypeMenus.append( tk.OptionMenu(self.f_container,self.widgetRowTypes[-1],*self.widgetRowTypeOptions[-1],command=self.updateWidgets) )
		self.widgetRowTypeMenus[-1].grid(in_=self.f_container,column=1,row=self.rowCounter+1)

		self.widgetRowFolders.append( tk.StringVar() )
		self.widgetRowFolderEntries.append( tk.Entry(self.f_container,width=30,textvariable=self.widgetRowFolders[-1]) )
		self.widgetRowFolderEntries[-1].grid(in_=self.f_container,column=2,row=self.rowCounter+1)

		self.widgetRowFolderButtons.append( tk.Button(self.f_container,text='Set Folder...') )
		self.widgetRowFolderButtons[-1].bind('<ButtonRelease-1>',self.attachDataFolder)
		self.widgetRowFolderButtons[-1].grid(in_=self.f_container,column=3,row=self.rowCounter+1)

		self.master.geometry('540x%i' % (338+self.rowCounter*30))
		self.config(width=540,height=(338+self.rowCounter*30))

		self.delRowButton.config(state=tk.NORMAL)

	def destroyWidgetRows(self):
		index=0
		while(index<self.rowCounter):
			if(self.widgetRowChecks[index].get() > 0):
				self.widgetRowCheckboxes[index].destroy()
				self.widgetRowTypeMenus[index].destroy()
				self.widgetRowFolderEntries[index].destroy()
				self.widgetRowFolderButtons[index].destroy()
				del self.widgetRowCheckboxes[index]
				del self.widgetRowTypeMenus[index]
				del self.widgetRowFolderEntries[index]
				del self.widgetRowFolderButtons[index]
				del self.widgetRowChecks[index]
				del self.widgetRowTypeOptions[index]
				del self.widgetRowTypes[index]
				del self.widgetRowFolders[index]
				self.rowCounter-=1
			else:
				index+=1

		if(self.rowCounter==0):
			self.delRowButton.config(state=tk.DISABLED)

		self.master.geometry('540x%i' % (338+self.rowCounter*30))
		self.config(width=540,height=(338+self.rowCounter*30))