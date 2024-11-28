import json
import os
from threading import Thread

import rest_utils
from json_rpc_client import JSONRPCClient
import time


class Integration:

  def __init__(self, server_url,
               integration_manifest,
               engine_manifest,
               device_agent_manifest,
               credentials_path,
               auth_refresh=600):
    self.server_url = server_url
    self.integration_manifest = integration_manifest
    self.engine_manifest = engine_manifest
    self.device_agent_manifest = device_agent_manifest
    self.credentials_path = credentials_path
    self.auth_refresh = auth_refresh
    self.is_approved = False
    self.integration_id = None

    if not self.check_registered():
        self.register()

    with open(credentials_path, 'r') as f:
      self.credentials = json.load(f)

    self.json_rpc_client = JSONRPCClient(server_url=server_url, integration=self)
    self.json_rpc_client.authorize(self.credentials)
    auth_tread = Thread(target=self.auth)
    auth_tread.start()

    self.json_rpc_client.subscribe_to_users(self.credentials['user'])


  @staticmethod
  def print_message(message, method=None):
    print(message, method)

  def check_registered(self):
    return os.path.isfile(self.credentials_path)

  def register(self):
    creds = rest_utils.register_integration(integration_manifest=self.integration_manifest,
                                            engine_manifest=self.engine_manifest,
                                            server_url=self.server_url)
    with open(self.credentials_path, 'w') as f:
      json.dump(creds, f)

  def auth(self):
    while True:
      time.sleep(self.auth_refresh)
      self.json_rpc_client.authorize(self.credentials)

  def set_parameters(self, parameters):
    self.is_approved = parameters.get('parameters', {}).get('integrationRequestData').get('isApproved', False)
    self.integration_id = parameters.get('parameters', {}).get('integrationRequestData').get('integrationId', None)

    if self.is_approved:
      self.json_rpc_client.subscribe_to_analytics()

  def start_sending(self):
    pass