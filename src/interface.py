#!/usr/bin/env python2
# -*- encoding: utf-8 -*-

import os
from gi.repository import Gtk

class InterfaceHandler:
	def __init__(self, quitfunc):
		self.quitfunc = quitfunc

	def closeAll(self, *res):
		self.quitfunc()
		Gtk.main_quit()

	def aboutDialog(self, *res):
		# create about info dialog
		aboutDialog = Gtk.AboutDialog()
		aboutDialog.set_program_name("Melodia")
		aboutDialog.set_comments("A music player for Linux")
		aboutDialog.set_version("0.1")
		aboutDialog.set_website("https://github.com/Azure-Vani/melodia")
		aboutDialog.set_website("website")
		aboutDialog.set_authors(["Zekun Ni", "Vani"])
		aboutDialog.set_copyright("Copyright © 2013-2016. All Rights reversed. ")
		aboutDialog.run()
		aboutDialog.destroy()

	def fileChooser(self, widget):
		# create file chooser dialog
		fileDialog = Gtk.FileChooserDialog("Open..", widget, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		fileDialog.set_default_response(Gtk.ResponseType.OK)
		res = fileDialog.run()
		if res == Gtk.ResponseType.OK:
			fileName = fileDialog.get_filename()
			playList.append(fileName)
		fileDialog.destroy()

class Interface:
	def __init__(self):
		# analyze the XML file
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(os.path.dirname(__file__), 'interface.glade'))

	def getObject(self, data):
		return self.builder.get_object(data)

	def start(self):
		self.window = self.getObject('MainWindow')
		self.window.show_all()
		Gtk.main()

	def actionHandler(self, data):
		if data == "PAUSE":
			label = self.getObject('Pause').get_label()
			if label == 'Pause':
				self.getObject('Pause').set_label('Resume')
			else:
				self.getObject('Pause').set_label('Pause')

	def setSpecialCalls(self, func, quitfunc):
		self.getObject('Prev').connect('clicked', func, "PREV")
		self.pauseSig = self.getObject('Pause').connect('clicked', func, "PAUSE")
		self.getObject('Stop').connect('clicked', func, "STOP")
		self.getObject('Next').connect('clicked', func, "NEXT")
		self.builder.connect_signals(InterfaceHandler(quitfunc))

	def connectSignals(self, handler):
		self.builder.connect_signals(handler)

	def showTime(self, nowTime, totalTime):
		self.getObject('timeLabel').set_text("%d:%02d/%d:%02d" % (nowTime / 60, nowTime % 60, totalTime / 60, totalTime % 60))
		if totalTime: self.getObject('scale').set_value(nowTime * 100.0 / totalTime)
		else: self.getObject('scale').set_value(0)

