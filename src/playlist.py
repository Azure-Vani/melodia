import asynchttplib, re, socket

class EventedHTTPConnection:
	def __init__(self, evt, host, port = 80):
		self.host = host
		self.port = port
		self.evt = evt

	def handle_request(self, stage, callback):
		if stage == 'request':
			try:
				self.conn.request()
			except socket.error:
				self.evt.append((self.handle_request, ('request', callback)))
			else:
				self.evt.append((self.handle_request, ('getresponse', callback)))
		else:
			try:
				res = self.conn.getresponse()
			except socket.error:
				self.evt.append((self.handle_request, ('getresponse', callback)))
			else:
				callback[0](*(callback[1] + (res,)))

	def handle_get_content(self, callback):
		try:
			self.buf += self.res.read(8192)
		except socket.error: pass

		if (len(self.buf) < self.size):
			self.evt.append((self.handle_get_content, (callback,)))
		else:
			callback[0](*(callback[1] + (self.res.getheaders(), self.buf)))

	def get_content(self, callback, res):
		self.res = res
		self.size = int(res.getheader('content-length'))
		self.buf = ''

		self.evt.append((self.handle_get_content, (callback,)))

	def request(self, method, url, body = None, headers = {}, callback = None):
		self.conn = asynchttplib.AsyncHTTPConnection(self.host, self.port)
		try:
			self.conn.request(method, url, body, headers)
		except socket.error:
			self.evt.append((self.handle_request, ('request', callback)))
		else:
			self.evt.append((self.handle_request, ('getresponse', callback)))

class PlayList:
	def __init__(self):
		self.playlist = []

	def handle_getSong(self):
		try:
			msg = self.res.read(20000)
			start = self.sizeread < 20000 and self.sizeread + len(msg) >= 20000
			self.buf += msg
			self.sizeread += len(msg)
			if len(self.buf) >= 20000:
				self.fp.write(self.buf)
				self.fp.flush()
				self.buf = ''
			if start: self.startfunc[0](*(self.startfunc[1] + ('/tmp/song.mp3', self.size)))
		except socket.error as e:
			pass

		if self.sizeread < self.size:
			self.evt.append((self.handle_getSong, ()))
		else:
			self.fp.write(self.buf)
			self.fp.flush()

	def getSong(self, res):
		self.res = res
		self.size = int(res.getheader('content-length'))
		self.buf = ''
		self.sizeread = 0

		self.evt.append((self.handle_getSong, ()))

	def getPlayList(self, headers = None, res = None):
		if res:
			res = re.sub(r':false', ':False', res)
			tmp = eval(res)
			self.playlist = tmp['song']
		self.song = self.playlist.pop(0)
		self.fp = open('/tmp/song.mp3', 'w')
		self.song['url'] = re.sub(r'\\/', '/', self.song['url'])
		host, url = re.match(r'http://([^/]*)(.*)', self.song['url']).groups()
		self.conn = EventedHTTPConnection(self.evt, host)
		self.conn.request('GET', url, callback = (self.getSong, ()))
	
	def getNext(self, evt, startfunc):
		self.evt = evt
		self.startfunc = startfunc
		try:
			if self.proc.is_alive(): self.proc.terminate()
			else: self.proc.join()
		except: pass
		try: self.fp.close()
		except: pass
		if not self.playlist:
			self.conn = EventedHTTPConnection(evt, 'douban.fm')
			self.conn.request('GET', '/j/mine/playlist', callback = (self.conn.get_content, ((self.getPlayList, ()),)))
		else:
			self.getPlayList(None)

	def quit(self):
		try:
			if self.proc.is_alive(): self.proc.terminate()
			else: self.proc.join()
		except: pass
