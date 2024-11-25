import json

from ws_class import WSClass
METHOD_CREATE_SESSION = "rest.v3.login.sessions.create"


def create_message(method, payload, request_id=None):
  message = {
    'jsonrpc': "2.0",
    'method': method,
    'params': payload,
    'id': request_id
  }

  return message

def create_login_session(username, password):
  return create_message(method=METHOD_CREATE_SESSION, payload={'username': username,
                                                               'password':password,
                                                               'setSession': True})

class JSONRPCClient:

  def __init__(self, server_url, on_message_callback):
    self.on_message_callback = on_message_callback
    self.ws_connect = WSClass(server_url=server_url, on_message=self.on_message)

  def on_message(self, message):
    jsn = json.loads(message)
    if 'jsonrpc' in jsn:
      self.on_message_callback(jsn.get('method', ''), jsn.get('params',''))
    else:
      print('Unknown message')

  def send(self, method, payload):
    message = {"method": method,
               "params": payload,
               "jsonrpc": "2.0"
               }
    self.ws_connect.send(json.dumps(message))

  def authorize(self, credentials):
    payload = {
      'username': credentials['user'],
      'password': credentials['password'],
      'setSession': True
    }
    self.send(method=METHOD_CREATE_SESSION, payload=payload)
