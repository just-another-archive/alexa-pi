import requests
import threading

def mrl_fix(url):
  if ('#' in url) and url.startswith('file://'):
    new_url = url.replace('#', '.hashMark.')
    os.rename(url.replace('file://', ''), new_url.replace('file://', ''))
    url = new_url

  return url

def check_network():
	try:
		requests.get('https://api.amazon.com/auth/o2/token')
		return True
	except:
		return False

def setTimeout(call, delay=0., *args, **kwargs):
	timer = threading.Timer(delay, call, args=args, kwargs=kwargs)
	timer.start()