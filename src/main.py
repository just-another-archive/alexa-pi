import optparse
import signal
import yaml
import sys

import alexapi.config

from alexapi.components.avs import AVS
from alexapi.components.microphone import Microphone
from alexapi.components.synthetizer import Synthetizer

import alexapi.pubsub as events

def cleanup(signal, frame):
	sys.exit(0)

if __name__ == "__main__":
	# interrupt
	for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM):
		signal.signal(sig, cleanup)

	# config
	with open(alexapi.config.filename, 'r') as stream:
		config = yaml.load(stream)

	# arguments
	parser = optparse.OptionParser()
	parser.add_option('-s', '--silent',
			dest="silent",
			action="store_true",
			default=False,
			help="start without saying hello")
	parser.add_option('-d', '--debug',
			dest="debug",
			action="store_true",
			default=False,
			help="display debug messages")

	cmdopts, cmdargs = parser.parse_args()
	config['debug']  = True # cmdopts.debug
	config['silent'] = cmdopts.silent

	# debug logger
	def log(type, *args, **kwargs):
		print('> {} {}'.format(type, kwargs))

	# wiring logger to pubsub
	events.register('*', log)

	# base components
	avs = AVS(config['avs'])
	microphone = Microphone(config['microphone'])
	synthetizer = Synthetizer(config['synthetizer'])

	# third party components


	# Ignition
	events.fire('boot_requested')
