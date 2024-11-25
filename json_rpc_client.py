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
    self.current_id = 0

  def on_message(self, message):
    jsn = json.loads(message)
    if 'jsonrpc' in jsn:
      if 'error' in jsn:
        self.on_message_callback(method='error', message=jsn['error'].get('message', ''))
      else:
        self.on_message_callback(method=jsn.get('method', ''), message=jsn.get('result',''), message_id=jsn.get('id',''))
    else:
      print('Unknown message')

  def send(self, method, payload):
    message = {"method": method,
               "params": payload,
               "jsonrpc": "2.0",
               'id': self.current_id
               }
    self.ws_connect.send(json.dumps(message))
    self.current_id += 1

  def authorize(self, credentials):
    payload = {
      'username': credentials['user'],
      'password': credentials['password'],
      'setSession': True
    }
    self.send(method=METHOD_CREATE_SESSION, payload=payload)
