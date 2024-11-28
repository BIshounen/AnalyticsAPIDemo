import abc
import asyncio
import os
from typing import Hashable
import rest_utils
import json

from AnalyticsAPIInterface import AnalyticsAPIInterface
from NxJSONRPC import NxJSONRPC


class AnalyticsAPIIntegration(AnalyticsAPIInterface):

  def __init__(self, server_url: str, integration_manifest: str, engine_manifest: str, credentials_path: str):
    self.server_url = server_url
    self.credentials = dict()
    self.integration_manifest = integration_manifest
    self.engine_manifest = engine_manifest
    self.credentials_path = credentials_path

    self.register()

    self.JSONRPC = None

  def register(self):
    if not os.path.isfile(self.credentials_path):
      creds = rest_utils.register_integration(integration_manifest=self.integration_manifest,
                                              engine_manifest=self.engine_manifest,
                                              server_url=self.server_url)
      with open(self.credentials_path, 'w') as f:
        json.dump(creds, f)
    with open(self.credentials_path, 'r') as f:
      temp_credentials = json.load(f)
      self.credentials = {'username': temp_credentials['user'], 'password': temp_credentials['password']}


  def set_parameters(self, parameters: dict):
    pass

  @abc.abstractmethod
  def get_device_agent_manifest(self, device_agent_id: Hashable) -> str:
    raise NotImplemented

  async def main(self):

    self.JSONRPC = NxJSONRPC(server_url=self.server_url)
    await self.JSONRPC.authorize(credentials=self.credentials)

  def run(self):
    asyncio.run(self.main())
