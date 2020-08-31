def mrl_fix(url):
  if ('#' in url) and url.startswith('file://'):
    new_url = url.replace('#', '.hashMark.')
    os.rename(url.replace('file://', ''), new_url.replace('file://', ''))
    url = new_url

  return url