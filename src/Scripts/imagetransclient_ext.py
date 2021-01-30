
import threading
import queue
import random
import traceback
import json

class ImageTransClientController:
	def __init__(self) :
		self.ClientThread = None
		self.ClientQ = None
		self.CompleteEvent = None
		self.WasSet = False
		pass

	def StartClient(self, port = None, server_addr = None) :
		if not server_addr :
			print('need a server address')
			return

		if port :
			self.ClientQ = queue.Queue()
			self.CompleteEvent = threading.Event()
			self.ClientThread = mod.threaded_filetrans_clientapp.ThreadedTransSocketClient(port, server_addr, self.ClientQ, self.CompleteEvent)
			self.ClientThread.start()
		else:
			print('need a port')

	def QueueJob(self,file_name = None, target_name = None) :
		if not self.ClientThread.is_alive() :
			self.StartClient()

		if file_name :
			letters = 'abcdef'
			numbers = '01234567'
			all_chars = letters+numbers
			job_id = ''.join(random.choice(all_chars) for i in range(5))
			if not target_name :
				target_name = file_name

			jData = {
			"jobId" : job_id,
			"fileName" : file_name,
			"targetName" : target_name
			}
			op('buffer').appendRow([json.dumps(jData)])
			if op('buffer').numRows == 1 :
				self.AddToQ()

		else:
			print('please supply a File name to transfer')

	def AddToQ(self) :
		if op('buffer').numRows :
			op('time_out').par.start.pulse()
			jData = json.loads(op('buffer')[0,0].val)
			self.CompleteEvent.clear()
			self.ClientQ.put(jData)

	def StopClient(self) :

		try :
			self.ClientQ.join()
			self.ClientThread.join()
		except AttributeError as e :
			pass
