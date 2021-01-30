import threading
import time
import socket
import sys
import base64
import libtransserver
import selectors
import traceback



class ThreadedTransSocketServer(threading.Thread) :
	def __init__(self, port = None, file_params = None, serverQ = None) :
		super(ThreadedTransSocketServer, self).__init__()
		self.stoprequest = threading.Event()
		self.socket = None
		self.selector = None
		self.serverQ = serverQ
		
		self.port = port
		self.file_params = file_params

	def accept_transfer(self,sock) :
		try :
			connection, address = sock.accept()
			print('starting a transfer from : {}'.format(address))

			#set the transfer to not block
			connection.setblocking(False)

			#create a new transfer object. expects the selector, connection, address of the client, and some descriptors about the transfer
			
			transfer = libtransserver.Transfer(self.selector,connection, address, self.file_params, self.serverQ)


			#register the transfer with selector
			self.selector.register(connection, selectors.EVENT_READ, data = transfer)

			#if the job que is empty put a 0 in to track file transfers
			if self.serverQ.empty() :
				self.serverQ.put(0)
			

		except OSError as e :
			if hasattr(e, 'winerror') and e.winerror == 10038 :
				print('has descriptors')
				pass
	



	def run(self) :
		try :
			#declare a new selector
			self.selector = selectors.DefaultSelector()
			#declare a new socket
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			#avoid some binding errors if address is already in use
			self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

			server_address =('0.0.0.0', self.port) 
			print('starting a server on : {}'.format(server_address))

			self.socket.bind(server_address)
			self.socket.listen(5)

			#non binding
			self.socket.setblocking(False)

			#register with our selector to accept multiple connections

			self.selector.register(self.socket, selectors.EVENT_READ, data=None)
		except Exception as e :
			print('encountered an exception while setting up the server exception : {}'.format(traceback.format_exc()))
			raise



		while not self.stoprequest.isSet() :
			""" selector will sometimes throw a win error on thread closuer. see python bug:
			"""

			try :
				events = self.selector.select(timeout=None) 
			except OSError as e :
				if hasattr(e, 'winerror') and e.winerror == 10038 :
					print('has descriptors')
					pass
			for key,mask in events :
				if key.data is None :
					self.accept_transfer(key.fileobj)
				else :
					transfer = key.data
					try :
						transfer.process(mask)
					except Exception :
						print('encountered an exception while processing a transfer from : {} \n exception : {}'.format(transfer.addr, traceback.format_exc()))
						transfer.close()





	def join(self, timeout=None) :
		print('stopping image socket server')
		#TODO. we might want to consider storing all open transfers in storage and then closing them on a join call.
		try :
			if self.socket :
				self.socket.close()
			if self.selector :
				self.selector.close()
			self.stoprequest.set()
			super(ThreadedTransSocketServer, self).join(timeout)
		except TypeError as e :
			pass







