from collections import deque

import threading
import time
import vlc

class VlcHandler():
	def __init__(self, config):
		self.config = config
		self.is_playing = False

		parameters = [
			# '--alsa-audio-device=mono'
			# '--file-logging'
			# '--logfile=vlc-log.txt'
		]

		#if self.config['device']:
		#	parameters.append('--aout=' + self.config['device'])

		#if self.config['output_device']:
		#	parameters.append('--alsa-audio-device=' + self.config['output_device'])

		self.vlc = vlc.Instance(*parameters)
		self.player = self.vlc.media_player_new()

	def play(self, *args, **kwargs):
		thread = threading.Thread(target=self._play, args=args, kwargs=kwargs)
		thread.start()

	def stop(self):
		self.player.stop()

	def _play(self, audio):
		media = self.vlc.media_new(audio)
		media.get_mrl()

		self.player.set_media(media)
		self.player.audio_set_volume(100)

		self.event_manager = media.event_manager()
		self.event_manager.event_attach(vlc.EventType.MediaStateChanged, self._callback, media)

		self.player.play()

		#self.event_manager.event_detach(vlc.EventType.MediaStateChanged)
		#self.player.stop()

	def _callback(self, event, media):
		# print('vlc state={}', media.get_state())

		if media.get_state() == vlc.State.Ended:
			self.config['callback']()