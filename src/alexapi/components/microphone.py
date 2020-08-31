from component import Component


import os
import tempfile
import threading
import time
import uuid


import alsaaudio
import webrtcvad

from pocketsphinx import get_model_path
from pocketsphinx.pocketsphinx import Decoder

import alexapi.pubsub as events

# constants
VAD_SAMPLERATE       = 16000
VAD_FRAME_MS         = 30
VAD_PERIOD = (VAD_SAMPLERATE / 1000) * VAD_FRAME_MS

VAD_THROWAWAY_FRAMES = 10
VAD_SILENCE_TIMEOUT  = 1000

MAX_RECORDING_LENGTH = 8

TMP_PATH = os.path.join(tempfile.mkdtemp(prefix='AlexaPi-Microphone-'), '')



class Microphone(Component):
	def __init__(self, config=None):
		Component.__init__(self, config)
		self.decoders = None

		events.register("detection_requested", self.detection_requested)
		events.register("capture_requested", self.capture_requested)



	def detection_requested(self, type, *args, **kwargs):
		thread = threading.Thread(target=self.detect, args=args, kwargs=kwargs)
		thread.start()



	def capture_requested(self, type, *args, **kwargs):
		thread = threading.Thread(target=self.capture, args=args, kwargs=kwargs)
		thread.start()



	def detect(self):
		# create decoders on the fly
		if not self.decoders:
			self.decoders = []

			for id, phrase in self.config['triggers'].iteritems():
				config = Decoder.default_config()

				# set recognition model to US
				config.set_string('-hmm', os.path.join(get_model_path(), 'en-us'))
				config.set_string('-dict', os.path.join(get_model_path(), 'cmudict-en-us.dict'))

				# specify recognition key phrase
				config.set_string('-keyphrase', phrase)
				config.set_float('-kws_threshold', 1e-5)

				# hide the VERY verbose logging information
				# if not self.config['debug']:
				config.set_string('-logfn', '/dev/null')

				decoder = Decoder(config)
				decoder.id = id

				self.decoders.append(decoder)

		events.fire('detection_started')

		# start decoding
		for decoder in self.decoders:
			decoder.start_utt()

		pcm = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self.config['device'])
		pcm.setchannels(1)
		pcm.setrate(16000)
		pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
		pcm.setperiodsize(1024)

		phrase = None
		triggered = False
		while not triggered:
			_, buffer = pcm.read()

			for decoder in self.decoders:
				decoder.process_raw(buffer, False, False)
				triggered = decoder.hyp() is not None

				if triggered:
					phrase = decoder.id
					break

		pcm.close()
		pcm = None

		for decoder in self.decoders:
			decoder.end_utt()

		events.fire('detection_fullfilled', id=phrase)



	def capture(self, vad_throwaway_frames=VAD_THROWAWAY_FRAMES):
		audio = ""

		pcm = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self.config['device'])
		pcm.setchannels(1)
		pcm.setrate(VAD_SAMPLERATE)
		pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
		pcm.setperiodsize(VAD_PERIOD)

		vad = webrtcvad.Vad(2)

		silenceRun = 0
		numSilenceRuns = 0
		thresholdSilenceMet = False

		frames = 0
		start = time.time()

		events.fire('capture_started')

		# do not count first 10 frames when doing VAD
		while frames < vad_throwaway_frames:
			length, data = pcm.read()
			frames = frames + 1
			if length:
				audio += data

		# now do VAD
		while ((thresholdSilenceMet is False) and ((time.time() - start) < self.config['timeout'])):
			length, data = pcm.read()
			if length:
				audio += data

				if length == VAD_PERIOD:
					isSpeech = vad.is_speech(data, VAD_SAMPLERATE)

					if not isSpeech:
						silenceRun = silenceRun + 1
						# print "0"
					else:
						silenceRun = 0
						numSilenceRuns = numSilenceRuns + 1
						# print "1"

			# only count silence runs after the first one
			# (allow user to speak for total of max recording length if they haven't said anything yet)
			if (numSilenceRuns != 0) and ((silenceRun * VAD_FRAME_MS) > VAD_SILENCE_TIMEOUT):
				thresholdSilenceMet = True

		path = TMP_PATH + str(uuid.uuid4()) + '.wav'

		with open(path, 'w') as rf:
			rf.write(audio)

		pcm.close()

		events.fire('capture_fullfilled', audio=path)
