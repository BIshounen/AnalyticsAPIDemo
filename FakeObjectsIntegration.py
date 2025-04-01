import time
from threading import Thread
from collections import defaultdict
import uuid

import cv2

import json

from ultralytics import YOLO

import rest_utils
from AnalyticsAPIIntegration import AnalyticsAPIIntegration
from config import server_url

from coordinates_tranform import get_pixel_to_coordinates

import queue

RESIZE = 300
yolo = YOLO('yolo11n.pt')


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

    self.settings = {
      "figure": None,
      'coords_1_lat': 39.110999999999997,
      'coords_1_long': -100.487779,
      'coords_2_lat': 39.110999999999997,
      'coords_2_long': -100.487779,
      'coords_3_lat': 39.110999999999997,
      'coords_3_long': -100.487779,
      'time_correction': 0,
      'filter_duration': 0
    }

    self.cap = None
    self.q = queue.Queue()
    self.current_time = 0

  def start(self):
    self.thread.start()

  def set_settings(self, values):
    new_values = {}
    try:
      positions = json.loads(values['coordinates_position'])
      new_values['coordinates_position'] = {}
      new_values['coordinates_position']['figure'] = positions['figure']
      new_values['coords_1_lat'] = float(values['coords_1_lat'])
      new_values['coords_1_long'] = float(values['coords_1_long'])
      new_values['coords_2_lat'] = float(values['coords_2_lat'])
      new_values['coords_2_long'] = float(values['coords_2_long'])
      new_values['coords_3_lat'] = float(values['coords_3_lat'])
      new_values['coords_3_long'] = float(values['coords_3_long'])
    except KeyError:
      return

    filter_duration = json.loads(values['filter_duration'])
    time_correction = json.loads(values['time_correction'])

    new_values['filter_duration'] = filter_duration
    new_values['time_correction'] = time_correction

    self.settings = new_values

  def cap_reader(self):

    video = rest_utils.get_rtsp_link(server_url=server_url,
                                     credentials=self.credentials,
                                     device_id=self.agent_id)

    self.cap = cv2.VideoCapture(video)

    while self.running:
      success, frame = self.cap.read()
      current_time = int(time.time()*1000) + self.settings['time_correction']
      print(self.settings['time_correction'])

      if success:
        if not self.q.empty():
          try:
            self.q.get_nowait()  # discard previous (unprocessed) frame
          except queue.Empty:
            pass
        self.q.put((success, frame, current_time))

  def send_object(self):


    read_thread = Thread(target=self.cap_reader)
    read_thread.daemon = True
    read_thread.start()

    track_guids = defaultdict(lambda: uuid.uuid4())
    objects_buffer = {}


    while self.running:

      success, frames, current_time = self.q.get()
      if not success:
        continue

      objects = []
      if success:
        results = yolo.track(frames, persist=True, device='mps', tracker="bytetrack.yaml", iou=0.2, conf=0.5)
        boxes = results[0].boxes.xywhn.cpu()

        if results[0].boxes.id is None:
          continue

        track_ids = results[0].boxes.id.int().cpu().tolist()
        name_ids = results[0].boxes.cls.cpu().tolist()

        for box, track_id, name_id in zip(boxes, track_ids, name_ids):
          x, y, w, h = box
          track_guid = track_guids[track_id]

          lat = None
          lon = None

          if 'coordinates_position' in self.settings and self.settings['coordinates_position']['figure'] is not None:
            known_pixels = [
              {"pixel": (self.settings['coordinates_position']['figure']['points'][0][0],
                         self.settings['coordinates_position']['figure']['points'][0][1]),
               "lat_lon": (self.settings['coords_1_lat'], self.settings['coords_1_long'])},
              {"pixel": (self.settings['coordinates_position']['figure']['points'][1][0],
                         self.settings['coordinates_position']['figure']['points'][1][1]),
               "lat_lon": (self.settings['coords_2_lat'], self.settings['coords_2_long'])},
              {"pixel": (self.settings['coordinates_position']['figure']['points'][2][0],
                         self.settings['coordinates_position']['figure']['points'][2][1]),
               "lat_lon": (self.settings['coords_3_lat'], self.settings['coords_3_long'])}
            ]

            lat, lon = get_pixel_to_coordinates(known_points=known_pixels, pixel=(x + w/2, y + h/2))
            lat = round(float(lat), 3)
            lon = round(float(lon), 3)

          detected_object = {
              "typeId": "analytics.api.stub.object.vehicle",
              "trackId": str(track_guid),
              "boundingBox": f"{float(x - w/2)},{float(y - h/2)},{float(w)}x{float(h)}",
              "attributes": [
                {"name":"nx.sys.color", "value": "White"},
                {"name": "TrackID", "value": str(track_guid)},
                {"name": "Type", "value": str(results[0].names[int(name_id)])},
                {"name": "Latitude", "value": str(lat)},
                {"name": "Longitude", "value": str(lon)}
              ]
            }

          if track_guid not in objects_buffer:
            objects_buffer[track_guid] = {'metadata': [(current_time, detected_object)],
                                          'first_occurrence': current_time, 'best_shot_sent': False}
          else:
            if current_time - objects_buffer[track_guid]['first_occurrence'] > self.settings['filter_duration']:
              for obj in objects_buffer[track_guid]['metadata']:

                object_data = {
                  "id": self.engine_id,
                  "deviceId": self.agent_id,
                  "timestampMs": obj[0],
                  "durationMs": 1,
                  "objects": [obj[1]]
                }

                self.json_rpc_client.send_object(object_data=object_data)


              objects.append(detected_object)
              if not objects_buffer[track_guid]['best_shot_sent']:
                best_shot = {
                  "id": self.engine_id,
                  "deviceId": self.agent_id,
                  "trackId": str(track_guid),
                  "timestampUs": current_time,
                  "boundingBox": f"{float(x - w/2)},{float(y - h/2)},{float(w)}x{float(h)}",
                }
                self.json_rpc_client.send_best_shot(best_shot=best_shot)

                title = {
                  "id": self.engine_id,
                  "deviceId": self.agent_id,
                  "trackId": str(track_guid),
                  "timestampMs": current_time,
                  "boundingBox": f"{float(x)},{float(y)},{float(w)}x{float(h)}",
                  "imageUrl": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/2017_Washington_License_Plate.jpg/1600px-2017_Washington_License_Plate.jpg",
                  "text": "AZM9590"
                }
                self.json_rpc_client.send_title_image(title_image=title)

            else:
              objects_buffer[track_guid]['metadata'].append((current_time, detected_object))


        object_data = {
          "id": self.engine_id,
          "deviceId": self.agent_id,
          "timestampMs": current_time,
          "durationMs": 1,
          "objects": objects
        }

        # annotated_frame = results[0].plot()
        # cv2.imwrite(f'test_{current_time}.png', annotated_frame)
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
    device_agent_id = device_parameters['parameters']['id'].strip('{}')
    engine_id = device_parameters['target']['engineId'].strip('{}')
    if device_agent_id not in self.device_agents:
      self.device_agents[device_agent_id] = DeviceAgent(agent_id=device_agent_id,
                                                        json_rpc_client=self.JSONRPC,
                                                        engine_id=engine_id,
                                                        duration=10,
                                                        credentials=self.credentials)
      self.device_agents[device_agent_id].start()

  def on_device_agent_deletion(self, device_id):
    self.device_agents[device_id].stop()

  def on_agent_active_settings_change(self, parameters, device_id):
    self.device_agents[device_id].set_settings(parameters['settingsValues'])
    return {
      'settingsValues': parameters['settingsValues'],
      'settingsModel': self.engine_manifest['deviceAgentSettingsModel']
    }

  def on_agent_settings_update(self, parameters, device_id):
    if device_id in self.device_agents:
      self.device_agents[device_id].set_settings(parameters['settingsValues'])
      return {
        'settingsValues': self.device_agents[device_id].settings,
        'settingsModel': self.engine_manifest['deviceAgentSettingsModel']
      }
    else:
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
    value_to_save = parameters.get('params', {}).get('parameter', None)
    if value_to_save is not None:
      return {
        'settingsValues': {'settingsValues': {'saved_param': value_to_save}},
        'settingsModel': self.integration_manifest['engineSettingsModel']
      }

    else:
      return {
        'settingsValues': parameters['settingsValues'],
        'settingsModel': self.integration_manifest['engineSettingsModel']
      }

  def get_integration_engine_side_settings(self, parameters):
    return {'value_to_save': '123'}
