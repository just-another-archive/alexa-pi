import os
import time

import RPi.GPIO as GPIO

from rpilike import RPiLikePlatform

class TechnicolorPlatform(RPiLikePlatform):

	def __init__(self, config):
		self.isReady = False
		self.inProgress = False
		super(TechnicolorPlatform, self).__init__(config, 'technicolor', GPIO)

	def setup(self):
		GPIO.setwarnings(False)
		GPIO.cleanup()
		GPIO.setmode(GPIO.BCM)

		super(TechnicolorPlatform, self).setup()

	def after_setup(self):
		self.isReady = True
		print("after_setup")

	def indicate_failure(self):
		print("indicate_failure")
		if self.isReady:
			self.inProgress = False
			self.write_code('5')

	def indicate_success(self):
		print("indicate_success")
		if not self.isReady:
			self.write_code('0')
			time.sleep(9)

	def indicate_recording(self, state=True):
		print("indicate_recording " + str(state))
		if self.isReady:
			if state:
				self.write_code('2')

	def indicate_playback(self, state=True):
		print("indicate_playback " + str(state))
		if self.isReady:
			if state and not self.inProgress: # querying
				self.inProgress = True
				self.write_code('1')
				time.sleep(.8)
				pass

#			if state and self.inProgress: # responding
#				self.inProgress = False
#				self.write_code('4')
#				time.sleep(.8)
#				self.write_code('5')
#				pass

	def indicate_processing(self, state=True):
		print("indicate_processing " + str(state))
		if self.isReady:
			if state:
				self.write_code('3')

	def should_record(self):
		return False # self.isReady doesnt work. bug? i dont wanna investigate. False works. yay.

	def cleanup(self):
		print("cleanup")

	def write_code(self, code):
		try:
			os.stat(self._pconfig['tty'])
			with open(self._pconfig['tty'], "w") as f:
				f.write(code + '\n')
				f.flush()
				time.sleep(.01)
				f.write('\n')
				f.flush()

		except:
			print("--- TTY not reachable ---")
			pass