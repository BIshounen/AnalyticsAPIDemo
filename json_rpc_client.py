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