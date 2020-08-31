from component import Component

import importlib
import os

import alexapi.pubsub as events

class Synthetizer(Component):
	def __init__(self, config=None):
		Component.__init__(self, config)

		handler = self.config['handler']
		imports = importlib.import_module('alexapi.playback.' + handler + 'handler', package=None)
		Handler = getattr(imports, handler.capitalize() + 'Handler')

		self.config['callback'] = self._callback

		self.handler = Handler(config)
		self.volume  = self.config['volume']

		events.register('speech_requested', self.play)
		events.register('volume_changed', self.volume)

	def play(self, type, *args, **kwargs):
		#print('audio={}'.format(kwargs['audio']))
		self.handler.play(audio=kwargs['audio'])

	def stop(self, type, *args, **kwargs):
		self.handler.stop()

	def volume(self, type, *args, **kwargs):
		#print('volume={}'.format(kwargs['value']))
		self.handler.volume(kwargs['value'])

	def _callback(self):
		events.fire('speech_fullfilled')