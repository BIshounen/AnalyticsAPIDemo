import time
import uuid
import imutils
from threading import Thread
import tensorflow as tf

import cv2

import rest_utils
from AnalyticsAPIIntegration import AnalyticsAPIIntegration
from config import server_url

from centroid_tracker import CentroidTracker

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

    video = rest_utils.get_stream_link(server_url=server_url,
                                       credentials=self.credentials,
                                       device_id=self.agent_id,
                                       video_format='mp4',
                                       stream='primary')

    cap = cv2.VideoCapture(video)

    with tf.io.gfile.GFile('frozen_inference_graph.pb', 'rb') as f:
      graph_def = tf.compat.v1.GraphDef()
      graph_def.ParseFromString(f.read())

    tracker = CentroidTracker(max_disappeared=5)

    while self.running:
      current_time =  int(time.time()*1000000)
      with tf.compat.v1.Session() as sess:
        # Restore session
        sess.graph.as_default()
        tf.import_graph_def(graph_def, name='')

        ret, frames = cap.read()
        if not ret:
          continue
        (frame_h, frame_w) = frames.shape[:2]

        objects = []

        rows = frames.shape[0]
        cols = frames.shape[1]
        inp = cv2.resize(frames, (RESIZE, RESIZE))
        inp = inp[:, :, [2, 1, 0]]  # BGR2RGB

        out = sess.run([sess.graph.get_tensor_by_name('num_detections:0'),
                        sess.graph.get_tensor_by_name('detection_scores:0'),
                        sess.graph.get_tensor_by_name('detection_boxes:0'),
                        sess.graph.get_tensor_by_name('detection_classes:0')],
                       feed_dict={'image_tensor:0': inp.reshape(1, inp.shape[0], inp.shape[1], 3)})

        num_detections = int(out[0][0])

        detections = []

        for i in range(num_detections):
          class_id = int(out[3][0][i])
          if class_id not in [2, 3, 4, 6]:
            continue
          score = float(out[1][0][i])
          bbox = [float(v) for v in out[2][0][i]]
          if score > 0.3:
            x = bbox[1] * cols
            y = bbox[0] * rows
            right = bbox[3] * cols
            bottom = bbox[2] * rows
            w = right - x
            h = bottom - y

            detections.append((int(x), int(y), int(w), int(h)))

        tracks = tracker.update(detections)

        for (object_id, centroid) in tracks.items():

          detected_object = {
              "typeId": "analytics.api.stub.object.type",
              "trackId": object_id,
              "boundingBox": {
                "x": (centroid[0] - 15)/frame_w,
                "y": (centroid[1] - 15)/frame_h,
                "width": 30/frame_w,
                "height": 30/frame_h
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
