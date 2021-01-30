
import threading
import queue
import time
from pathlib import Path
import td



class ImageTransServerController :
	def __init__(self, ownerComp) :
		self.ServerThread = None
		self.ServerQ = None
		self.ownerComp = ownerComp

		pass
	def GetTargetDir(self) :
		target_dir_val = self.ownerComp.par.Targetdir.val

		if '/' in target_dir_val or '\\' in target_dir_val :
			target_dir = Path(target_dir_val)
		else :
			project_folder = Path(td.project.folder)
			target_dir = Path(project_folder / target_dir_val)

		return target_dir.resolve()


	def StartServer(self) :
		port = me.parent().par.Port.val
		target_dir = self.GetTargetDir()
		self.ServerQ = queue.Queue()
		self.ServerQ.put(0)
		params = {
		"targetDir" :target_dir
		}
		self.ServerThread = mod.threaded_filetrans_serverapp.ThreadedTransSocketServer(port,params,self.ServerQ)
		self.ServerThread.start()

	def ResetReceivedFileCount(self) :
		try :
			if self.ServerQ.empty() :
				self.ServerQ.put(0)
			else:
				old_count = self.ServerQ.get(timeout = .3) 
				self.ServerQ.put(0)
		except AttributeError as e :
			print('no queue active')

	def StopServer(self) :
		# if self.ServerQ :
		# 	while not self.ServerQ.empty() :
		# 		try :
		# 			self.ServerQ.get(timeout = .3)
		# 		except Empty:

		# 			continue

		# 	self.ServerQ.task_done()
		# time.sleep(.3)
		# try :
		# 	if self.ServerQ :
		# 		self.ServerQ.join()
		# 	self.ServerThread.join()
		# except AttributeError as e:
		# 	print('no server active')
		try :
			self.ServerThread.join()
		except AttributeError as e:
			print('no server active')
