#!/usr/bin/python2
# -*- encoding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk

import socket

def sendSignal(widget, signal):
	print signal, "recieved."
	return None

class MainWindow:

	def AboutInfo(self, widget):
		aboutDialog = gtk.AboutDialog()
		aboutDialog.set_program_name("Melodia")
		aboutDialog.set_comments("A music player for Linux")
		aboutDialog.set_version("0.1")
		aboutDialog.set_website("https://github.com/Azure-Vani/melodia")
		aboutDialog.set_website("website")
		aboutDialog.set_authors(["Zekun Ni", "Vani"])
		aboutDialog.set_copyright("Copyright © 2013-2016. All Rights reversed. ")
		aboutDialog.run()
		aboutDialog.destroy()

	def initWindow(self):
		# Initialize main window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title("Melodia")
		self.window.set_size_request(500, 70)
		self.window.set_position(gtk.WIN_POS_CENTER)
		self.window.connect("delete_event", gtk.main_quit)	

	def createMenu(self):
		# Create Menu
		self.mb = gtk.MenuBar()
		self.fileMenu = gtk.Menu()
		self.editMenu = gtk.Menu()
		self.viewMenu = gtk.Menu()
		self.helpMenu = gtk.Menu()

		# Create Menu Item
		self.File = gtk.MenuItem('File')
		self.Edit = gtk.MenuItem('Edit')
		self.View = gtk.MenuItem('View')
		self.Help = gtk.MenuItem('Help')
		self.File.set_submenu(self.fileMenu)
		self.Edit.set_submenu(self.editMenu)
		self.View.set_submenu(self.viewMenu)
		self.Help.set_submenu(self.helpMenu)

		# Add Menu Item
		self.openFile = gtk.MenuItem('Open...')
		self.openFolder = gtk.MenuItem('Open Folder...')
		self.Exit = gtk.MenuItem('Exit')
		self.Exit.connect('activate', gtk.main_quit)
		self.fileMenu.append(self.openFile)
		self.fileMenu.append(self.openFolder)
		self.fileMenu.append(gtk.SeparatorMenuItem())
		self.fileMenu.append(self.Exit)

		self.loopPlay = gtk.RadioMenuItem(None, 'Loop Play')
		self.loopPlay.set_active(True)
		self.shufflePlay = gtk.RadioMenuItem(self.loopPlay, 'Shuffle Play')
		self.preference = gtk.MenuItem('Preferences...')
		self.editMenu.append(self.loopPlay)
		self.editMenu.append(self.shufflePlay)
		self.editMenu.append(gtk.SeparatorMenuItem())
		self.editMenu.append(self.preference)

		self.changeSkin = gtk.MenuItem('Change Skin...')
		self.showLyric = gtk.CheckMenuItem('Show Lyric')
		self.showLyric.set_active(True)
		self.viewMenu.append(self.showLyric)
		self.viewMenu.append(gtk.SeparatorMenuItem())
		self.viewMenu.append(self.changeSkin)

		self.About = gtk.MenuItem('About...')
		self.About.connect('activate', self.AboutInfo)
		self.helpMenu.append(self.About)

		self.mb.append(self.File)
		self.mb.append(self.Edit)
		self.mb.append(self.View)
		self.mb.append(self.Help)

	def createButton(self):
		# Creating Buttons
		self.nextButton = gtk.Button('Next')
		self.nextButton.connect('clicked', sendSignal, "NEXT")
		self.prevButton = gtk.Button('Prev')
		self.prevButton.connect('clicked', sendSignal, "PREV")
		self.pauseButton = gtk.Button('Pause')
		self.pauseButton.connect('clicked', sendSignal, "PAUSE")

	def Packing(self):
		self.globalBox = gtk.VBox(False, 10)
		self.buttonAlign = gtk.Alignment(0, 0, 0, 0)
		self.tmpAlign = gtk.Alignment(0, 1, 0, 0)

		self.globalBox.pack_start(self.mb, False, False, 0)
		self.globalBox.pack_start(self.buttonAlign)
		self.globalBox.pack_start(self.tmpAlign, True, True, 0)

		self.tmpHBox = gtk.HBox(True, 2)
		self.tmpHBox.pack_start(self.prevButton, True, True, 5)
		self.tmpHBox.pack_start(self.pauseButton, True, True, 5)
		self.tmpHBox.pack_start(self.nextButton, True, True, 5)
		self.buttonAlign.add(self.tmpHBox)

	def __init__(self):
		self.initWindow()
		self.createMenu()
		self.createButton()
		self.Packing()

		self.window.add(self.globalBox)
		self.window.show_all()

def run():
	gtk.main()

if __name__ == "__main__":
	mainWindow = MainWindow()
	run()

