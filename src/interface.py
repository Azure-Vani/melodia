#!/usr/bin/python2
# -*- encoding: utf-8 -*-

import socket
import time
import sys
import os
from playlist import PlayList
from gi.repository import GObject
from gi.repository import Gtk
socket_addr = '/tmp/melodia-socket'

class _Song:
	def __init__(self, info):
		self.totalTime = info["time"]
		self.artist = info["artist"]
		self.album = info["album"]

class _Socket:
	def __init__(self):
		self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		try:
			self.sock.connect(socket_addr)
		except socket.error:
			os.system('melodia-daemon &')
			self.sock.connect(socket_addr)
	def __del__(self):
		self.sock.close()
	def send(self, data):
		self.sock.send(data)
	def recv(self):
		return self.sock.recv(4096)
	def nonblocking(self):
		self.sock.setblocking(0)

class InterfaceHandler:
	def closeAll(self, *res):
		interface.quit()
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
			interface.paused = True
			interface.sock.send('PAUSE')
		if data == "RESUME":
			interface.getObject('Pause').set_label('Pause')
			interface.getObject('Pause').disconnect(interface.resumeSig)
			interface.pauseSig = interface.getObject('Pause').connect('clicked', InterfaceHandler().connectServer, "PAUSE")
			interface.paused = False
			interface.sock.send('RESUME')
		if data == "NEXT":
			interface.start()
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
		self.getObject('timeLabel').set_text("%d:%02d/%d:%02d" % (self.nowTime / 60, self.nowTime % 60, self.totalTime / 60, self.totalTime % 60))
		if self.totalTime: self.getObject('scale').set_value(self.nowTime * 100.0 / self.totalTime)
		else: self.getObject('scale').set_value(0)

	def setTime(self):
		try:
			info = self.sock.recv().split('\0')[:-1]
			for msg in info:
				if msg == 'QUIT':
					self.start()
				elif msg == 'BUFFERING':
					self.buffering = True
				elif msg == 'RESUME':
					self.buffering = False
				else:
					self.nowTime = int(msg)
			self.showTime()
		except: pass
		return True

	def start(self):
		try: del self.sock
		except: pass

		self.nowTime = 0
		(addr, size) = self.playlist.getNext()
		self.paused = self.buffering = False

		self.sock = _Socket()
		self.sock.send(addr)
		self.sock.recv()
		self.sock.send(str(size))
		info = self.sock.recv()
		self.totalTime = int(info.split('\1')[0])
		self.sock.send('START')
		self.sock.nonblocking()

	def quit(self):
		try: del self.sock
		except: pass
		try: self.playlist.quit()
		except: pass

	def setSpecialWidget(self):
		self.showTime()
		GObject.timeout_add(100, self.setTime)

	def __init__(self):
		# analyze the XML file
		self.builder = Gtk.Builder()
		self.builder.add_from_file('interface.glade')

		self.nowTime = self.totalTime = 0
		self.paused = self.buffering = False

		self.setSpecialCalls()
		self.setSpecialWidget()
		self.builder.connect_signals(InterfaceHandler())

		self.playlist = PlayList()
		self.start()

		self.window = self.getObject('MainWindow')
		self.window.show_all()

def run():
	Gtk.main()

if __name__ == "__main__":
	interface = MainInterface()
	run()

