import requests
import urllib.parse

REGISTER_PATH = "/rest/v4/analytics/integrations/*/requests"


def _concat_url(server_url, path):
    initial_url = urllib.parse.urlparse(server_url)
    print(initial_url)
    result = urllib.parse.urlunparse(initial_url._replace(path=path, scheme='http'))
    print(result)
    return result


def register_integration(server_url, integration_manifest, engine_manifest):
    params = {"integrationManifest": integration_manifest,
              "engineManifest": engine_manifest,
              "pinCode": "9876"}
    result = requests.post(_concat_url(server_url=server_url, path=REGISTER_PATH), json=params)
    if result.status_code == 200:
        creds = {"user" : result.json()['user'], "password": result.json()['password']}
        return creds
    else:
        raise RuntimeError(result.status_code, result.text)
