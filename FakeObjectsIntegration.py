import time
import uuid
from threading import Thread

from AnalyticsAPIIntegration import AnalyticsAPIIntegration


class DeviceAgent:

  def __init__(self, engine_id, agent_id, json_rpc_client, duration):
    self.shift = 0
    self.json_rpc_client = json_rpc_client
    self.engine_id = engine_id
    self.agent_id = agent_id
    self.frequency = 1
    self.duration = duration
    self.running = True
    self.thread = Thread(target=self.send_object)

  def start(self):
    self.thread.start()

  def send_object(self):
    current_time = 0
    track_id = str(uuid.uuid4())

    while self.running:
      if current_time >= self.duration:
        current_time = 0
        track_id = str(uuid.uuid4())

      object_data = {
        "id": self.engine_id,
        "deviceId": self.agent_id,
        "timestampUs": int(time.time())*1000,
        "durationUs": current_time,
        "objects": [
          {
            "typeId": "analytics.api.stub.object.type",
            "trackId": track_id,
            "boundingBox": {
              "x": 0.3720000000000003,
              "y": 0.33,
              "width": 0.2,
              "height": 0.33
            }
          }
        ]
      }
      self.json_rpc_client.send_object(device_agent_id=self.agent_id, object_data=object_data, engine_id=self.engine_id)
      current_time += self.frequency
      time.sleep(self.frequency)

  def stop(self):
    self.running = False


class FakeObjectsIntegration(AnalyticsAPIIntegration):

  def __init__(self,
               server_url: str,
               integration_manifest: dict,
               engine_manifest: dict,
               credentials_path: str,
               device_agent_manifest: dict):

    super().__init__(server_url=server_url,
                   integration_manifest=integration_manifest,
                   engine_manifest=engine_manifest,
                   credentials_path=credentials_path)

    self.device_agents = {}

    self.device_agent_manifest = device_agent_manifest

  def get_device_agent_manifest(self, device_parameters: dict) -> dict:
    return self.device_agent_manifest

  def on_device_agent_created(self, device_parameters):
    device_agent_id = device_parameters['parameters']['id']
    engine_id = device_parameters['target']['engineId']
    self.device_agents[device_agent_id] = DeviceAgent(agent_id=device_agent_id,
                                                      json_rpc_client=self.JSONRPC,
                                                      engine_id=engine_id,
                                                      duration=10)
    self.device_agents[device_agent_id].start()

  def on_device_agent_deletion(self, device_id):
    self.device_agents[device_id].stop()

  def on_agent_active_settings_change(self, parameters):

    return {
      'settingsValues': parameters['settingsValues'],
      'settingsModel': self.engine_manifest['deviceAgentSettingsModel']
    }

  def on_agent_settings_update(self, parameters):

    return {
      'settingsValues': parameters['settingsValues'],
      'settingsModel': self.engine_manifest['deviceAgentSettingsModel']
    }

  def on_engine_settings_update(self, parameters):

    return {
      'settingsValues': parameters['settingsValues'],
      'settingsModel': self.integration_manifest['engineSettingsModel']
    }

  def on_engine_active_settings_change(self, parameters):

    return {
      'settingsValues': parameters['settingsValues'],
      'settingsModel': self.integration_manifest['engineSettingsModel']
    }
