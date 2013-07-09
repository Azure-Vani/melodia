#!/usr/bin/env python2
# -*- encoding: utf-8 -*-

import socket
import time
import sys
import os
from playlist import PlayList
from interface import Interface
from gi.repository import GObject
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
		l = len(self.evt)
		for i in range(0, l):
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


if __name__ == "__main__":
	controller = MainController()

