import time
import uuid
import imutils
from threading import Thread

import cv2

import rest_utils
from AnalyticsAPIIntegration import AnalyticsAPIIntegration
from config import server_url

RESIZE = 300


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

    haar_cascade = 'cars.xml'

    video = rest_utils.get_stream_link(server_url=server_url,
                                       credentials=self.credentials,
                                       device_id=self.agent_id,
                                       video_format='mp4',
                                       stream='primary')

    cap = cv2.VideoCapture(video)
    car_cascade = cv2.CascadeClassifier(haar_cascade)

    trackers = {}

    while self.running:
      current_time =  int(time.time()*1000000)

      ret, frames = cap.read()
      gray = cv2.cvtColor(frames, cv2.COLOR_BGR2GRAY)
      gray = imutils.resize(gray, width=RESIZE)
      (frame_h, frame_w) = gray.shape[:2]
      cars = car_cascade.detectMultiScale(gray, 1.1, 1)


      objects = []

      for key, tracker in trackers.items():
        (success, bbox) = tracker['tracker'].update(gray)
        if success:
          tracker['bbox'] = bbox
        else:
          trackers[key].pop()

      for (x, y, w, h) in cars:

        tracker_id = None

        for key, tracker in trackers.items():
          if (x, y, w, h) == tracker['bbox']:
            tracker_id = key
            break

        if tracker_id is None:
          tracker = cv2.TrackerMIL.create()
          tracker.init(gray, (x, y, w, h))
          tracker_id = str(uuid.uuid4())
          trackers[tracker_id] = {'bbox': (x, y, w, h), 'tracker': tracker}


        detected_object = {
            "typeId": "analytics.api.stub.object.type",
            "trackId": tracker_id,
            "boundingBox": {
              "x": x/frame_w,
              "y": y/frame_h,
              "width": w/frame_w,
              "height": h/frame_h
            }
          }
        objects.append(detected_object)

        object_data = {
          "id": self.engine_id,
          "deviceId": self.agent_id,
          "timestampUs": current_time,
          "durationUs": 1000000,# 1000000 * self.frequency + 5000000,
          "objects": objects
        }

        self.json_rpc_client.send_object(device_agent_id=self.agent_id, object_data=object_data,
                                         engine_id=self.engine_id)


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
