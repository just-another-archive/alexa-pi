from component import Component

import email
import json
import os
import tempfile
import time
import sys
import requests

from memcache import Client
from transitions import Machine

from alexapi.utils import check_network
from alexapi.utils import mrl_fix

import alexapi.pubsub as events

# constants
SERVERS  = ["127.0.0.1:11211"]
MEMCACHE = Client(SERVERS, debug=1)

TMP_PATH = os.path.join(tempfile.mkdtemp(prefix='AlexaPi-AVS-'), '')
RES_PATH = os.path.join(os.path.realpath(__file__).rstrip(os.path.basename(__file__)), '../../resources', '')



class AVS(Component):
	def __init__(self, config):
		Component.__init__(self,config)

		events.register('boot_requested', self.boot)
		events.register('greetings_requested', self.greet)
		events.register('detection_fullfilled', self.capture)
		events.register('capture_fullfilled', self.process)

	def boot(self, type, *args, **kwargs):
#		sys.stdout.write("Trying to reach Amazon...")
#		while not check_network():
#			sys.stdout.write(".")

#		print("")
#		print("Connection OK")

		if not self._get_token():
			sys.exit()

		events.fire('greetings_requested')
		events.fire('detection_requested')

	def greet(self, type, *args, **kwargs):
		events.fire('speech_requested', audio=RES_PATH + 'hello.mp3')

	def capture(self, type, *args, **kwargs):
		if kwargs['id'] != self.config['trigger']:
			return

		if not self.config['silent']:
			events.fire('speech_requested', audio=RES_PATH + 'alexayes.mp3')

		events.fire('capture_requested')

	def process(self, type, *args, **kwargs):
		# create request
		url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
		headers = {'Authorization': 'Bearer %s' % self._get_token()}
		payload = {
			"messageHeader": {
				"deviceContext": [
					{
						"name": "playbackState",
						"namespace": "AudioPlayer",
						"payload": {
							"streamId": "",
							"offsetInMilliseconds": "0",
							"playerActivity": "IDLE"
						}
					}
				]
			},
			"messageBody": {
				"profile": "alexa-close-talk",
				"locale": "en-us",
				"format": "audio/L16; rate=16000; channels=1"
			}
		}

		with open(kwargs['audio']) as audio:
			files = [
				('file', ('request', json.dumps(payload), 'application/json; charset=UTF-8')),
				('file', ('audio', audio, 'audio/L16; rate=16000; channels=1'))
			]

			# send request
			response = requests.post(url, headers=headers, files=files)

		# cleanup right after use
		os.remove(kwargs['audio'])

		print(response)

		if response.status_code == 204:
			events.fire('detection_requested')
			return

		if response.status_code != 200:
			events.fire('error_report_requested', response=response)
			return

		wrapper = "Content-Type: " + response.headers['content-type'] + '\r\n\r\n' + response.content
		message = email.message_from_string(wrapper)

		for payload in message.get_payload():
			content_type  = payload.get_content_type()
			response_body = payload.get_payload()

			if content_type == "audio/mpeg":
				filename = TMP_PATH + payload.get('Content-ID').strip("<>") + ".mp3"
				with open(filename, 'wb') as audio:
					audio.write(payload.get_payload())
			else:
				if content_type == "application/json":
					data = json.loads(response_body)

				elif self.config['debug']:
					print('-- Unknown data returned:')
					print(json.dumps(data))

		# process audio items first
#		if 'audioItem' in data['messageBody']:
#			self.player.play_playlist(data['messageBody'])
#			pass

		# for lisibility
		directives = data['messageBody']['directives']

		if not directives or len(directives) == 0 :
			events.fire('detection_requested')
			return

		wishes = []

		for directive in directives:
			# speaker control such as volume or mute
			if directive['namespace'] == "Speaker":
				if directive['name'] == 'SetVolume':
					wishes.append({ 'type': 'volume', 'value': int(directive['payload']['volume']), 'relative': directive['payload']['adjustmentType'] == 'relative' })

				elif directive['name'] == 'SetMute':
					pass

			# if need of a new capture phase
			elif directive['namespace'] == 'SpeechRecognizer' and directive['name'] == 'listen':
				events.fire('capture_requested', vad_throwaway_frames=directive['payload']['timeoutIntervalInMillis'] / 116)

			# play speech
			elif directive['namespace'] == 'SpeechSynthesizer':
				if directive['name'] == 'speak':
					wishes.append({ 'type': 'speech', 'value': mrl_fix("file://" + TMP_PATH + directive['payload']['audioContent'].lstrip("cid:") + ".mp3") })

			# play music
			elif directive['namespace'] == 'AudioPlayer':
				if directive['name'] == 'play':
					pass

		for wish in wishes:
			if wish['type'] == 'speech':
				events.fire('speech_requested', audio=wish['value'])

		time.sleep(.1)
		events.fire('detection_requested')

	def _get_token(self):
		token = MEMCACHE.get("access_token")
		refresh = self.config['refresh_token']

		if token:
			return token

		elif refresh:
			url = "https://api.amazon.com/auth/o2/token"
			payload = {
				"client_id": self.config['Client_ID'],
				"client_secret": self.config['Client_Secret'],
				"refresh_token": refresh,
				"grant_type": "refresh_token"
			}

			response = requests.post(url, data=payload)
			resp = json.loads(response.text)

			MEMCACHE.set("access_token", resp['access_token'], 3570)
			return resp['access_token']

		else:
			return False
