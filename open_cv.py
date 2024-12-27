import cv2
import rest_utils
import config
import tensorflow as tf

auth = rest_utils.create_auth(config.server_url,
                              {"username": "nx.analytics_api_fake_objects",
                               "password": "YTk2NDk2OTktZDdiOS00MDU2LTkzMDEtMTYzZWQ0YmQ0ZTUw"},
                              method='GET'
                              )
haar_cascade = 'cars.xml'
video = 'https://172.19.7.98:7001/rest/v4/devices/d786ddaa-89bd-0ae4-602f-fcc0af3d6f43/media.mp4?auth={auth}'.format(auth=auth)

cap = cv2.VideoCapture(video)

with tf.io.gfile.GFile('frozen_inference_graph.pb', 'rb') as f:
      graph_def = tf.compat.v1.GraphDef()
      graph_def.ParseFromString(f.read())

while True:
  # reads frames from a video
  ret, frames = cap.read()

  if not ret:
    continue
  (frame_h, frame_w) = frames.shape[:2]

  with tf.compat.v1.Session() as sess:
    # Restore session
    sess.graph.as_default()
    tf.import_graph_def(graph_def, name='')

    rows = frames.shape[0]
    cols = frames.shape[1]
    inp = cv2.resize(frames, (300, 300))
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

      cv2.rectangle(frames, (int(x), int(y)), (int(right), int(bottom)), (125, 255, 51), thickness=2)

      detections.append((int(x), int(y), int(w), int(h)))

  # Display frames in a window
  cv2.imshow('video', frames)

  # Wait for Esc key to stop
  if cv2.waitKey(33) == 27:
    break

# De-allocate any associated memory usage
cv2.destroyAllWindows()
