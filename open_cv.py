import cv2
import rest_utils
import config

auth = rest_utils.create_auth(config.server_url,
                              {"username": "nx.analytics_api_fake_objects",
                               "password": "YTk2NDk2OTktZDdiOS00MDU2LTkzMDEtMTYzZWQ0YmQ0ZTUw"},
                              method='GET'
                              )
haar_cascade = 'cars.xml'
video = 'https://172.19.7.98:7001/rest/v4/devices/0e190059-71db-5fe0-d3c8-62658e232818/media.mp4?auth={auth}'.format(auth=auth)

cap = cv2.VideoCapture(video)
car_cascade = cv2.CascadeClassifier(haar_cascade)

while True:
  # reads frames from a video
  ret, frames = cap.read()

  # convert to gray scale of each frames
  gray = cv2.cvtColor(frames, cv2.COLOR_BGR2GRAY)

  # Detects cars of different sizes in the input image
  cars = car_cascade.detectMultiScale(gray, 1.1, 1)

  # To draw a rectangle in each car
  for (x, y, w, h) in cars:
    cv2.rectangle(frames, (x, y), (x + w, y + h), (0, 0, 255), 2)

  # Display frames in a window
  cv2.imshow('video', frames)

  # Wait for Esc key to stop
  if cv2.waitKey(33) == 27:
    break

# De-allocate any associated memory usage
cv2.destroyAllWindows()
