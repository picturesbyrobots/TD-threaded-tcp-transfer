import selectors
import sys
import json
import struct
import io


class Transfer :
	def __init__(self, selector, sock, addr, request):
		self.sock = sock
		self.selector = selector
		self.addr = addr
		self.request = request
		self.request_queued = False
		self._outbytes = None
		self.recv_buffer = b""
		self.content_header_len = None
		self.content_header = None
		self.response_data = None


	def set_events_mask(self, mode) :
		if mode == "r" :
			events = selectors.EVENT_READ
		elif mode == "w" :
			events = selectors.EVENT_WRITE
		elif mode == "rw" :
			events = selectors.EVENT_READ | selectors.EVENT_WRITE
		else :
			raise ValueError("Invalid events mode: {}".format(mode))

		self.selector.modify(self.sock, events, data = self)


	"""pack the header and bytes into one request"""
	def pack(self, *, payload, content_type, content_encoding, file_name) :
		content_descriptor = {
		"byteorder" : sys.byteorder,
		"content-type": content_type,
		"content-encoding":content_encoding,
		"file_name": file_name,
		"content-length": len(payload)
		}
		cdb = json.dumps(content_descriptor,ensure_ascii=False).encode('utf-8')

		#encode the length of the content header as a subheader
		subheader = struct.pack(">H",len(cdb))
		trans_bytes = subheader + cdb + payload
		return trans_bytes

	"""create a transfer request."""

	def queue_request(self) : 
		content = self.request["content"]
		content_type = self.request["type"]
		content_encoding = self.request["encoding"]
		file_name = self.request["file_name"]

		q = {
		"payload" : content,
		"content_type": content_type,
		"content_encoding": content_encoding,
		"file_name" : file_name
		}

		packed = self.pack(**q)
		self._outbytes = packed
		self.request_queued = True


	def readbytes(self) :
		try :
			data = self.sock.recv(524288)
		except BlockingIOError :
			pass
		else :
			if data :
				self.recv_buffer += data
			else :
				raise RuntimeError("Transfer aborted. Peer Closed")


	def process_data(self) :
		content_len = self.content_header["content-length"] 
		if not len(self.recv_buffer) >= content_len :
			return

		data = self.recv_buffer[:content_len]
		self.recv_buffer = self.recv_buffer[content_len:]
		wrapper = io.TextIOWrapper(io.BytesIO(data), encoding = "utf-8", newline ="")
		self.response_data = json.load(wrapper)
		wrapper.close()
		print("response data : {}".format(self.response_data))


	def get_content_header_len(self) : 
		clen = 2
		if len(self.recv_buffer) >= clen :
			self.content_header_len = struct.unpack(
				">H", self.recv_buffer[:clen])[0]
			self.recv_buffer = self.recv_buffer[clen:]
		pass

	def get_content_header(self) :
		cdh_len = self.content_header_len
		#if we have enough bytes from the content header
		if len(self.recv_buffer) >= cdh_len :
		#pull bytes from buffer equal to the content header len
			json_bytes = self.recv_buffer[:cdh_len]
		#wrap it in a byte buffer and load it into json
			json_wrapper = io.TextIOWrapper(io.BytesIO(json_bytes), encoding = "utf-8", newline="")
			json_obj = json.load(json_wrapper)


		#pull the bytes from the transfer buffer
			self.recv_buffer = self.recv_buffer[cdh_len:]
			self.content_header = json_obj
			json_wrapper.close()
			print('got a json obj : {}'.format(json_obj))



	def read(self) :
		#get some bytes from the socket
		self.readbytes()

		#if we don't have the length of the content header get it
		if self.content_header_len is None :
			self.get_content_header_len()

		#if we do have content header length but not a content header parse it
		if self.content_header_len is not None :
			if self.content_header is None :
				self.get_content_header()

		#if we have a content header but no data
		if self.content_header :
			if self.response_data is None :
				self.process_data()






	"""internal writer for writing bytes to the send buffer"""
	def _write(self):
		if self._outbytes :
			print('sending to {} on {}'.format(self.addr[0], self.addr[1]))
			try :
				sent = self.sock.send(self._outbytes)
			except BlockingIOError :
				pass
			else :
				self._outbytes = self._outbytes[sent:]


	"""main driver for a write engine. makes a request if there isn't one qeued. sends a
	request on a buffer. closes the request if there is no more left to send"""

	def write(self) :
	# we don't have a request. make one
		if not self.request_queued  :
			self.queue_request()

	# call our internal write function
		self._write()

	#bytes sent. closing the connection
		if self.request_queued :
			if not self._outbytes :
				print('file sent. waiting for a response')
				self.set_events_mask('r')




	"""main driver for the Transfer client. if write or read based on event selector"""

	def process(self,mask):
		if mask & selectors.EVENT_READ :
			self.read()
		if mask & selectors.EVENT_WRITE :
			self.write()


	def close(self) :
		print('closing a connection to : {}'.format(self.addr))
		try :
			self.selector.unregister(self.sock)
		except Exception as e :
			print('got an error closing a selector')

		try :
			self.sock.close()
		except OSError as e :
			print('cause an os error closing the socket')
		finally :
			self.sock = None




