import socket, httplib, StringIO

class AsyncSocketFileObject:
	def __init__(self, sock):
		self._sock = sock
		self._buffer = ''

	def read(self, amt):
		if amt <= len(self._buffer):
			msg = self._buffer[: amt]
			self._buffer = self._buffer[amt: ]
		else:
			try:
				msg = self._buffer + self._sock.recv(amt - len(self._buffer))
			except socket.error as e:
				if self._buffer: msg = self._buffer
				else: raise
			self._buffer = ''
		return msg

	def readline(self, amt = -1):
		p = self._buffer.find('\n')+1

		if amt != -1 and len(self._buffer) >= amt:
			if p == 0 or p > amt: p = amt
			msg = self._buffer[: p]
			self._buffer = self._buffer[p: ]
			return msg

		if p == 0:
			if amt == -1: amt = 8192
			try:
				self._buffer += self._sock.recv(amt - len(self._buffer))
			except socket.error: pass
			p = self._buffer.find('\n')+1

		if p == 0:
			raise socket.error(11, 'Resource temporarily unavailable')
		if amt != -1 and p > amt: p = amt
		msg = self._buffer[: p]
		self._buffer = self._buffer[p: ]

		return msg

	def close(self):
		self._sock.close()
		self._buffer = ''

class AsyncHTTPResponse(httplib.HTTPResponse):
	# TODO: only supports an HTTP response with Content-Length specified

	def __init__(self, sock, debuglevel=0, strict=0, method=None, buffering=False):
		httplib.HTTPResponse.__init__(self, sock, debuglevel, strict, method, buffering)
		self._sock_fp = AsyncSocketFileObject(sock)
		self._buf = ''
	
	def begin(self):
		# Fully read the headers and make the result into a StringIO
		# to cheat the function in the parent class
		while True:
			line = self._sock_fp.readline()
			self._buf += line
			if line == '\r\n': break
		
		self.fp = StringIO.StringIO(self._buf)
		httplib.HTTPResponse.begin(self)
		self.fp = self._sock_fp

class AsyncHTTPConnection(httplib.HTTPConnection):
	# FIXME: not fully functional
	
	response_class = AsyncHTTPResponse

	def connect(self):
		# TODO: IPv6 support
		if not self.sock:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.setblocking(0)

		self.connected = 0
		self.sock.connect((self.host, self.port))
		self.connected = 1

	def send(self, data):
		if not self.sock or not self.connected:
			if self.auto_open:
				self.connect()
			else:
				raise httplib.NotConnected()

		return self.sock.send(data)

	def _send_output(self, message_body=None):
		if self._buffer:
			self._buffer.extend(("", ""))
			msg = "\r\n".join(self._buffer)
			if message_body != None:
				msg += message_body
			self._buffer = []
		else:
			msg = self._body_buffer + message_body

		res = self.send(msg)
		self._body_buffer = msg[res: ]
	
	def request(self, method=None, url=None, body=None, headers={}):
		if method == None:
			method = self._method
			url = self._url
			body = self._body
			headers = self._headers
		else:
			self._method = method
			self._url = url
			self._body = body
			self._headers = headers
			self._request_progress = False

		if self._request_progress:
			try:
				self.endheaders(None)
				self._request_progress = False
			except socket.error:
				self._HTTPConnection__state = httplib._CS_IDLE
				raise
		else:
			try:
				self._send_request(method, url, body, headers)
				self._request_progress = False
			except socket.error:
				self._HTTPConnection__state = httplib._CS_IDLE
				raise

	def getresponse(self, buffering=False):
		# XXX: Horrible
		
		if self._HTTPConnection__response and self._HTTPConnection__response.isclosed():
			self._HTTPConnection__response = None

		if self._HTTPConnection__state != httplib._CS_REQ_SENT or self._HTTPConnection__response and self._response_begin:
			raise httplib.ResponseNotReady()
	
		if self._HTTPConnection__response == None:
			args = (self.sock,)
			kwds = {"strict":self.strict, "method":self._method}
			if self.debuglevel > 0:
				args += (self.debuglevel,)
			if buffering:
				kwds["buffering"] = True
			response = self._HTTPConnection__response = self.response_class(*args, **kwds)
			self._response_begin = False
		else:
			response = self._HTTPConnection__response

		response.begin()
		self._response_begin = True
		self._HTTPConnection__state = httplib._CS_IDLE

		if response.will_close:
			self._HTTPConnection__response = None
			#self.close()

		return response
