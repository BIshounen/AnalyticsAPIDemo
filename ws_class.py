import asyncio
import urllib.parse
from websockets.asyncio.client import connect

WS_PATH = "/jsonrpc"


def _concat_url(server_url, path):
    initial_url = urllib.parse.urlparse(server_url)
    result = str(urllib.parse.urlunparse(initial_url._replace(path=path, scheme='ws')))
    return result

def ws_address(server_url):
  return _concat_url(server_url=server_url, path=WS_PATH)

def 