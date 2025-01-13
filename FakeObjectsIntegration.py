import time
from threading import Thread
from collections import defaultdict
import uuid

import cv2

from ultralytics import YOLO

import rest_utils
from AnalyticsAPIIntegration import AnalyticsAPIIntegration
from config import server_url


RESIZE = 300
yolo = YOLO('yolov8m.pt')


class DeviceAgent:

  def __init__(self, engine_id, agent_id, json_rpc_client, duration, credentials):
    self.shift = 0
    self.json_rpc_client = json_rpc_client
    self.engine_id = engine_id
    self.agent_id = agent_id
    self.frequency = 3
    self.duration = duration
    self.running = True
    self.thread = Thread(target=self.send_object)
    self.credentials = credentials

  def start(self):
    self.thread.start()

  def send_object(self):

    video = rest_utils.get_rtsp_link(server_url=server_url,
                                     credentials=self.credentials,
                                     device_id=self.agent_id)

    cap = cv2.VideoCapture(video)


    track_guids = defaultdict(lambda: uuid.uuid4())
    start_time = 0.0

    while self.running:

      success, frames = cap.read()
      pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
      if pos_msec == 0:
        start_time = time.time()*1000000
      success = cap.grab()
      current_time = time.time()*1000000
      if not success:
        continue
      cap.retrieve(frames)
      print(pos_msec)
      print(current_time)
      print(time.time()*1000000)
      objects = []
      if success:
        results = yolo.track(frames, persist=True, device='mps')
        boxes = results[0].boxes.xywhn.cpu()

        if results[0].boxes.id is None:
          continue

        track_ids = results[0].boxes.id.int().cpu().tolist()
        name_ids = results[0].boxes.cls.cpu().tolist()

        for box, track_id, name_id in zip(boxes, track_ids, name_ids):
          x, y, w, h = box
          track_guid = track_guids[track_id]

          detected_object = {
              "typeId": "analytics.api.stub.object.type",
              "trackId": str(track_guid),
              "boundingBox": {
                "x": float(x),
                "y": float(y),
                "width": float(w),
                "height": float(h)
              },
            "attributes": [
              {"name":"nx.sys.color", "value": "White"},
              {"name": "track_id", "value": str(track_guid)},
              {"name": "object_type", "value": str(results[0].names[int(name_id)])}
            ]
            }

          objects.append(detected_object)
        #
        # if track_id not in sent_tracks:
        #   best_shot = {
        #     "id": self.engine_id,
        #     "deviceId": self.agent_id,
        #     "trackId": track_id,
        #     "timestampUs": current_time,
        #     "boundingBox": {
        #       "x": float(x/frame_w),
        #       "y": float(y/frame_h),
        #       "width": w/frame_w,
        #       "height": h/frame_h
        #     },
        #   }
        #
        #   self.json_rpc_client.send_best_shot(best_shot=best_shot)
        #   sent_tracks.append(track_id)

        object_data = {
          "id": self.engine_id,
          "deviceId": self.agent_id,
          "timestampUs": int(current_time),
          "durationUs": 100000,
          "objects": objects
        }

        # annotated_frame = results[0].plot()
        # cv2.imwrite('test.png', annotated_frame)
        self.json_rpc_client.send_object(object_data=object_data)


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
    print(cv2.__version__)

  def get_device_agent_manifest(self, device_parameters: dict) -> dict:
    return self.device_agent_manifest

  def on_device_agent_created(self, device_parameters):
    device_agent_id = device_parameters['parameters']['id']
    engine_id = device_parameters['target']['engineId']
    self.device_agents[device_agent_id] = DeviceAgent(agent_id=device_agent_id,
                                                      json_rpc_client=self.JSONRPC,
                                                      engine_id=engine_id,
                                                      duration=10,
                                                      credentials=self.credentials)
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
