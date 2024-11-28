import urllib.parse
import json
import uuid
import asyncio
from crypt import methods
from threading import Thread

from websocket import create_connection

WS_PATH = "/jsonrpc"

METHOD_CREATE_SESSION = "rest.v3.login.sessions.create"
METHOD_SUBSCRIBE_USERS = "rest.v3.users.subscribe"
METHOD_UPDATE_USERS = "rest.v3.users.update"
METHOD_SUBSCRIBE_ANALYTICS = 'rest.v4.analytics.subscribe'
METHOD_CREATE_DEVICE_AGENT = 'rest.v4.analytics.engines.deviceAgents.create'
METHOD_CREATE_DEVICE_AGENT_MANIFEST = 'rest.v4.analytics.engines.deviceAgents.manifest.create'

def _concat_url(server_url, path):
  initial_url = urllib.parse.urlparse(server_url)
  result = str(urllib.parse.urlunparse(initial_url._replace(path=path, scheme='ws')))
  return result


class RequestAwaitable:

  def __init__(self):
    self.respond = None

  def __await__(self):
    if self.respond is None:
      yield

    # if self.respond is None:
    #   raise RuntimeError("Await wasn't used with future")

    return self.respond



class NxJSONRPC:

  def __init__(self, server_url: str):

    self.requests_queue: dict[uuid.UUID, RequestAwaitable] = dict()
    self.server_url = server_url
    self.ws = create_connection(_concat_url(server_url=server_url, path=WS_PATH))
    self.listen_thread = Thread(target=self.listen)
    self.listen_thread.start()

  def on_ws_message(self, raw_message):
    message = json.loads(raw_message)
    if 'id' in message:
      if 'result' in message:
        self.parse_response(message)
      else:
        self.parse_request(message)
    else:
      self.parse_notification(message)

  def parse_response(self, message: dict):
    if message['id'] in self.requests_queue:
      self.requests_queue[message['id']].respond = message['result']

  def parse_request(self, message: dict):
    pass

  def parse_notification(self, message: dict):
    pass

  def listen(self):
    while True:
      print('listening')
      raw_message = self.ws.recv()
      print("received:")
      print(raw_message)
      self.on_ws_message(raw_message)


  @staticmethod
  def compose_request(message: str|dict|list, method: str, message_id: uuid.UUID):
    message_dict = {
      'id': str(message_id),
      'params': message,
      'method': method
    }

    return json.dumps(message_dict)

  async def make_request(self, message: str|dict|list, method: str):
    message_id = uuid.uuid4()
    message_string = self.compose_request(message=message, method=method, message_id=message_id)
    request = RequestAwaitable()
    self.requests_queue[message_id] = request
    self.send_message(message_string=message_string)
    await request

  def send_message(self, message_string):
    self.ws.send(message_string)

  def notify(self, message):
    pass

  def respond(self, message, message_id):
    pass

  async def authorize(self, credentials: dict):
    await self.make_request(method=METHOD_CREATE_SESSION, message=credentials)
