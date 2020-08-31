__events__ = {}
__events__['*'] = []

def register(type, handler):
	global __events__

	if not hasattr(__events__, type):
		__events__[type] = []

	__events__[type].append(handler)

def fire(type, *args, **kwargs):
	global __events__

	for handler in __events__['*']:
		handler(type, *args, **kwargs)

	if not type in __events__:
		return

	for handler in __events__[type]:
		handler(type, *args, **kwargs)