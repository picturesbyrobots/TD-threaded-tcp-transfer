import threading
import socket
import selectors
import traceback
import base64
import libtransclient
import queue
import time


class ThreadedTransSocketClient(threading.Thread) :
	def __init__(self, port, server_addr, inQ, cEvent) :
		super(ThreadedTransSocketClient, self).__init__()
		self.stoprequest = threading.Event()
		self.socket = None
		self.selector = None
		self.port = port
		self.server_addr = server_addr
		self.inQ = inQ
		self.cEvent = cEvent
		self.jobs = {}

	def create_transfer_request(self, file, file_name) :
		#open the file and read the bytes
		with open(file, 'rb') as img :
			image_read = img.read()
		#encode the file as base64
			image_64_encode = base64.encodestring(image_read)
			return dict(
				type='file',
				encoding='base64',
				file_name=file_name,
				content = bytes(image_64_encode)
				)


	def start_connection(self, host, port, request) :
		address = (host, port)
		#create a new socket for this connection
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		#set non blocking
		sock.setblocking(False)
		#connect!
		sock.connect_ex(address)

		#client should register read and write events to be able to write the request
		events = selectors.EVENT_READ | selectors.EVENT_WRITE

		#create a new transfer object
		transfer = libtransclient.Transfer(self.selector, sock,address, request)

		#register our transfer with the selector
		self.selector.register(sock,events,data = transfer)


	def run(self) :
		print('starting a client connection')
		try:
			self.selector = selectors.DefaultSelector()
		except Exception as e :
			print('encountered an exception while setting up the client exception : {}'.format(traceback.format_exc()))
			raise

		while not self.stoprequest.isSet() :
			try :
				jDataIn = self.inQ.get(timeout = .3)
				try :
					job_id = jDataIn["jobId"]
					jDataIn.pop("jobId")
					self.jobs[job_id] = jDataIn
					request = self.create_transfer_request(jDataIn["fileName"], jDataIn["targetName"])
					self.start_connection(self.server_addr, self.port, request)

				except KeyError as e :
					print('encoutered a key error while adding a job : {}'.format(traceback.format_exc()))
				finally:
					self.inQ.task_done()

			except queue.Empty as e :
				pass

			if len(self.jobs) :
				events = self.selector.select(timeout = None)
				for key,mask in events :
					transfer = key.data
					try :
						transfer.process(mask)
						if transfer.response_data :
							response = transfer.response_data
							print(response)
							transfer.close()
							self.jobs = {}
							self.cEvent.set()

					except Exception :
						print('encountered an exception while processing a transfer from : {} \n exception : {}'
							.format(transfer.addr, traceback.format_exc()))
						transfer.close()
			time.sleep(.1)


	def join(self, timeout=None) :
		print('stopping image socket client')
		#TODO. we might want to consider storing all open transfers in storage and then closing them on a join call.

		if self.selector :
			self.selector.close()
		self.stoprequest.set()
		super(ThreadedTransSocketClient, self).join(timeout)






