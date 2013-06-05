import cookielib, urllib2, re, threading
class PlayList:
	def __init__(self):
		self.opener = urllib2.build_opener()
		self.playlist = []

	def getSong(self):
		fp = self.fp
		while self.cursize < self.size:
			tmp = self.res.read(100000)
			if fp != self.fp: return
			self.fp.write(tmp)
			self.cursize += len(tmp)
		self.fp.flush()
	
	def getNext(self):
		try:
			if self.thread.is_alive(): self.thread.join(0)
		except: pass
		try: self.fp.close()
		except: pass
		if not self.playlist:
			res = self.opener.open('http://douban.fm/j/mine/playlist').read()
			res = re.sub(r':false', ':False', res)
			tmp = eval(res)
			self.playlist = tmp['song']
		self.song = self.playlist.pop(0)
		self.fp = open('/tmp/song.mp3', 'w')
		self.song['url'] = re.sub(r'\\/', '/', self.song['url'])
		self.res = self.opener.open(self.song['url'])
		self.size = int(self.res.headers['content-length'])
		tmp = self.res.read(100000)
		self.cursize = len(tmp)
		self.fp.write(tmp)
		self.thread = threading.Thread(None, self.getSong, 'getsong', ())
		self.thread.start()
		return ('/tmp/song.mp3', self.size)

