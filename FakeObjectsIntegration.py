from typing import Hashable

from AnalyticsAPIIntegration import AnalyticsAPIIntegration

class FakeObjectsIntegration(AnalyticsAPIIntegration):

  def __init__(self,
               server_url: str,
               integration_manifest: str,
               engine_manifest: str,
               credentials_path: str,
               device_agent_manifest: str):

    super().__init__(server_url=server_url,
                   integration_manifest=integration_manifest,
                   engine_manifest=engine_manifest,
                   credentials_path=credentials_path)

    self.device_agent_manifest = device_agent_manifest

  def get_device_agent_manifest(self, device_agent_id: Hashable) -> str:
    return self.device_agent_manifest