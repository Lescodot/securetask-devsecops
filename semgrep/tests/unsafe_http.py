# This file intentionally contains insecure HTTP requests for Semgrep testing.

import requests
import httpx
import urllib.request

requests.get("http://example.com")

httpx.get("http://example.com")

urllib.request.urlopen("http://example.com")
