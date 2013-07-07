#!/usr/bin/env python2
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
		self.builder.add_from_file('interface.glade')

	def getObject(self, data):
		return self.builder.get_object(data)

	def start(self):
		self.window = self.getObject('MainWindow')
		self.window.show_all()

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

class MainController:
	def connectServer(self, widget, data):
		self.interface.actionHandler(data)
		if data == "PAUSE":
			if self.paused:
				self.paused = False
				self.sock.send('RESUME')
			else:
				self.paused = True
				self.sock.send('PAUSE')
		if data == "NEXT":
			self.switch()
		print "Received a %s signal." % (data)

	def eventLoop(self):
		if self.evt:
			func = self.evt.pop(0)
			func[0](*func[1])

		if self.started:
			try:
				info = self.sock.recv().split('\0')[:-1]
				for msg in info:
					if msg == 'QUIT':
						self.switch()
					elif msg == 'BUFFERING':
						self.buffering = True
					elif msg == 'RESUME':
						self.buffering = False
					else:
						self.nowTime = int(msg)
				self.interface.showTime(self.nowTime, self.totalTime)
			except: pass

		return True

	def switch(self):
		if self.started:
			try: del self.sock
			except: pass

			self.nowTime = self.totalTime = 0
			self.started = False
		self.evt = []
		self.playlist.getNext(self.evt, (self.start, ()))

	def start(self, addr, size):
		self.paused = self.buffering = False
		self.started = True

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

	def __init__(self):
		self.interface = Interface()

		self.nowTime = self.totalTime = 0
		self.paused = self.buffering = False

		self.playlist = PlayList()
		self.started = False
		self.evt = []

		self.interface.setSpecialCalls(self.connectServer, self.quit)
		GObject.timeout_add(10, self.eventLoop)
		self.switch()
		self.interface.start()


def run():
	Gtk.main()

if __name__ == "__main__":
	controller = MainController()
	run()

