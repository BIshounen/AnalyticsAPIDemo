import os
import rest_utils


def check_registered():
    os.path.isfile("credentials.py")


class Integration:

  def __init__(self, server_url):
    self.server_url = server_url
    if not check_registered():
        self.register()

  def register(self):

