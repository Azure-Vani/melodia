#!/usr/bin/python
# -*- encoding: utf-8 -*-

import socket
import time
from gi.repository import GObject
from gi.repository import Gtk

class _Song:
	def __init__(self, info):
		self.totalTime = info["time"]
		self.artist = info["artist"]
		self.album = info["album"]

class PlayList:
	def __init__(self):
		self.List = []
		self.SHUFFLE = 1
		self.LOOP = 0
		self.palyType = self.LOOP
	
	def append(self, data):
		self.List.append(data)
		# debug
		print "Current play list is", self.List

	def getNext(self):
		return self.List.pop(0)

class _Socket:
	def Send(data):
		print data

class InterfaceHandler:
	def closeAll(self, *res):
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
	
	def connectServer(self, widget, data):
		global interface
		if data == "PAUSE":
			interface.getObject('Pause').set_label('Resume')
			interface.getObject('Pause').disconnect(interface.pauseSig)
			interface.resumeSig = interface.getObject('Pause').connect('clicked', InterfaceHandler().connectServer, "RESUME")
		if data == "RESUME":
			interface.getObject('Pause').set_label('Pause')
			interface.getObject('Pause').disconnect(interface.resumeSig)
			interface.pauseSig = interface.getObject('Pause').connect('clicked', InterfaceHandler().connectServer, "PAUSE")
		print "Received a %s signal." % (data)

class MainInterface:
	def getObject(self, data):
		return self.builder.get_object(data)

	def setSpecialCalls(self):
		self.getObject('Prev').connect('clicked', InterfaceHandler().connectServer, "PREV")
		self.pauseSig = self.getObject('Pause').connect('clicked', InterfaceHandler().connectServer, "PAUSE")
		self.getObject('Stop').connect('clicked', InterfaceHandler().connectServer, "STOP")
		self.getObject('Next').connect('clicked', InterfaceHandler().connectServer, "NEXT")

	def showTime(self):
		self.getObject('timeLabel').set_text("%d:%02d/%d:%02d"%(self.nowTimeMin, self.nowTimeSec, self.totTimeMin, self.totTimeSec))

	def setTime(self):
		self.nowTimeSec += 1
		if self.nowTimeSec == 60:
			self.nowTimeSec = 1
			self.nowTimeMin += 1
		tmp = (self.nowTimeMin * 60.0 + self.nowTimeSec) / (self.totTimeMin * 60.0 + self.totTimeSec) * 100.0
		self.getObject('scale').set_value(tmp)
		self.showTime()
		return True

	def setSpecialWidget(self):
		self.showTime()
		self.getObject('scale').set_sensitive(False)
		self.getObject('Stop').set_sensitive(False)
		GObject.timeout_add(950, self.setTime)

	def __init__(self):
		# analyze the XML file
		self.builder = Gtk.Builder()
		self.builder.add_from_file('interface.glade')

		self.nowTimeSec = 0
		self.nowTimeMin = 0
		self.totTimeSec = 28
		self.totTimeMin = 3

		self.setSpecialCalls()
		self.setSpecialWidget()
		self.builder.connect_signals(InterfaceHandler())

		self.window = self.getObject('MainWindow')
		self.window.show_all()

def run():
	Gtk.main()

if __name__ == "__main__":
	playList = PlayList()
	Socket = _Socket()
	interface = MainInterface()
	run()

