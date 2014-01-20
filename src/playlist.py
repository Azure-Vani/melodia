import httplib, re, socket, json

class PlayList:
	def __init__(self):
		self.playlist = []

	def getNext(self):
		if not self.playlist:
			conn = httplib.HTTPConnection('douban.fm')
			conn.request('GET', '/j/mine/playlist')
			res = json.loads(conn.getresponse().read())
			self.playlist = res['song']
		return self.playlist.pop(0)['url']

	def quit(self):
		pass
