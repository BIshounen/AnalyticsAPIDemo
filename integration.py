import json
import os
import rest_utils
from json_rpc_client import JSONRPCClient


class Integration:

  def __init__(self, server_url, integration_manifest, engine_manifest, device_agent_manifest, credentials_path):
    self.server_url = server_url
    self.integration_manifest = integration_manifest
    self.engine_manifest = engine_manifest
    self.device_agent_manifest = device_agent_manifest
    self.credentials_path = credentials_path

    if not self.check_registered():
        self.register()

    with open(credentials_path, 'r') as f:
      self.credentials = json.load(f)

    self.json_rpc_client = JSONRPCClient(server_url=server_url, on_message_callback=self.on_message)
    self.json_rpc_client.authorize(self.credentials)

  def on_message(self, method, message):
    print(message)

  def check_registered(self):
    return os.path.isfile(self.credentials_path)

  def register(self):
    creds = rest_utils.register_integration(integration_manifest=self.integration_manifest,
                                            engine_manifest=self.engine_manifest,
                                            server_url=self.server_url)
    with open(self.credentials_path, 'w') as f:
      json.dump(creds, f)
