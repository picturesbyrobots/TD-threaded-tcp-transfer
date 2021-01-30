
import selectors
import sys
import json
import struct
import io
import base64
import os


class Transfer :
	def __init__(self,selector, sock, addr, file_params, outQ) :
		self.sock = sock
		self.selector = selector
		self.addr = addr
		self.content_header_len = None
		self.content_header = None

		self.trans_buffer = b"" 
		self.send_buffer = b""
		self.file_data = None
		self.trans_success = False
		self.response_created = False
		self.file_params = file_params
		self.outQ = outQ



	def readbytes(self) :
		try :
			data = self.sock.recv(524288)
		except BlockingIOError :
			pass
		else :
			if data :
				self.trans_buffer += data
			else :
				raise RuntimeError("Transfer aborted. Peer Closed")


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


	def get_content_header(self) :
		cdh_len = self.content_header_len
		#if we have enough bytes from the content header
		if len(self.trans_buffer) >= cdh_len :
		#pull bytes from buffer equal to the content header len
			json_bytes = self.trans_buffer[:cdh_len]
		#wrap it in a byte buffer and load it into json
			json_wrapper = io.TextIOWrapper(io.BytesIO(json_bytes), encoding = "utf-8", newline="")
			json_obj = json.load(json_wrapper)


		#pull the bytes from the transfer buffer
			self.trans_buffer = self.trans_buffer[cdh_len:]
			self.content_header = json_obj
			json_wrapper.close()
			print('got a json obj : {}'.format(json_obj))




	def process_data(self) :
		content_len = self.content_header["content-length"] 
		if not len(self.trans_buffer) >= content_len :
			return
		#pull the rest of the data from the buffer

		#empty the buffer
		data = self.trans_buffer[:content_len] 
		self.trans_buffer = self.trans_buffer[content_len:] 

		#files are encoded as base64 strings. decode them
		decode = base64.decodestring(data)

		#pull the filename from the json header
		file_name = self.content_header["file_name"]

		#if there's a target directory add it to the path
		if self.file_params:
			print(self.file_params["targetDir"])
			file_name = os.path.join(self.file_params["targetDir"], file_name)

		# 	file_name = os.path.join(self.params["targetDir"], file_name)

		with open(file_name, 'wb') as res:
			print('writing to a file')
			res.write(decode)
			self.trans_success = True
			if not self.outQ.empty() :
				num_files = self.outQ.get(timeout = .3)
				self.outQ.put(num_files + 1)
		self.set_events_mask("w")

		



	def pack_message(self, *, payload, content_type, content_encoding) :
		json_header = {
		"byteorder" :sys.byteorder,
		"content-type" : content_type,
		"content-encoding": content_encoding,
		"content-length" : len(payload)
		}
		h_bytes = json.dumps(json_header, ensure_ascii=False).encode(content_encoding)
		mhdr = struct.pack(">H", len(h_bytes))
		message = mhdr + h_bytes + payload
		return message

	def create_response(self) :
		content = {"success" : self.trans_success} 
		content_encoding = "utf-8"
		json_encode = json.dumps(content, ensure_ascii=False).encode(content_encoding)
		response = {
		"payload" : json_encode,
		"content_type" : "text/json",
		"content_encoding" :content_encoding
		}
		message = self.pack_message(**response)
		self.response_created = True
		self.send_buffer += message

	def write_response(self) :
		if self.send_buffer :
			try :
				sent = self.sock.send(self.send_buffer)
			except BlockingIOError :
				pass
			else :
				self.send_buffer = self.send_buffer[sent:]
				if sent and not self.send_buffer :
					self.close()

	def get_content_header_len(self) : 
		clen = 2
		if len(self.trans_buffer) >= clen :
			self.content_header_len = struct.unpack(
				">H", self.trans_buffer[:clen])[0]
			self.trans_buffer = self.trans_buffer[clen:]
		pass

	def write(self) :
		if self.trans_success:
			if not self.response_created :
				print('sending a response')
				self.create_response()

		self.write_response()

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
			if self.file_data is None :
				self.process_data()





	def process(self, mask) :
		if mask & selectors.EVENT_READ :
			self.read()
		if mask & selectors.EVENT_WRITE:
			self.write()

	def close(self) :
		print("closing a connection to : {}".format(self.addr))
		try :
			self.selector.unregister(self.sock) 
		except Exception as e :
			print("encountered an error while unregistering a selector {} \n error: {}".format(self.addr, e))
		try :
			self.sock.close()
		except OSError as e :
			print('error while closing a socket for {} \n e: {}'
				.format(self.addr, e))
		finally :
			self.sock = None

