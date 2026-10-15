import urllib.request

# The image has neither curl nor wget, so the check is the interpreter it does ship with.
urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3)
