import json
from enum import verify

import requests
import urllib.parse

REGISTER_PATH = "/rest/v4/analytics/integrations/*/requests"
LOGIN_PATH = "/rest/v4/login/sessions"
ENGINES_PATH = "/rest/v4/analytics/engines"
DEVICE_AGENTS_PATH = "/rest/v4/analytics/engines/{engine_id}/deviceAgents"


def _concat_url(server_url, path):
    initial_url = urllib.parse.urlparse(server_url)
    print(initial_url)
    result = urllib.parse.urlunparse(initial_url._replace(path=path, scheme='https'))
    print(result)
    return result


def register_integration(server_url, integration_manifest, engine_manifest):
    params = {"integrationManifest": integration_manifest,
              "engineManifest": engine_manifest,
              "pinCode": "9876"}
    result = requests.post(_concat_url(server_url=server_url, path=REGISTER_PATH), json=params, verify=False)
    if result.status_code == 200:
        creds = {"user" : result.json()['user'], "password": result.json()['password']}
        return creds
    else:
        raise RuntimeError(result.status_code, result.text)


def get_device_agents(server_url: str, credentials: dict, integration_id: str) -> list:
    token = authorize(server_url, credentials)
    print('received auth token: ', token)
    parameters = 'integrationId="{integration_id}"'.format(integration_id=integration_id)

    header = {'Authorization': 'Bearer ' + token}
    result = requests.request(method='GET',
                              params=parameters,
                              url=_concat_url(server_url=server_url, path=ENGINES_PATH),
                              verify=False,
                              headers=header)
    if result.status_code != 200:
        raise RuntimeError('Unable to get engine id')

    engine_id = result.json()[0]['id']
    print('engine id: ', engine_id)

    result = requests.request(method='GET',
                              url=_concat_url(server_url=server_url,
                                              path=DEVICE_AGENTS_PATH.format(engine_id=engine_id)),
                              verify=False,
                              headers=header)
    if result.status_code != 200:
        raise RuntimeError('Unable to get device agents')

    device_agents = result.json()
    return device_agents


def authorize(server_url, credentials: dict):
    params = {
        "username": credentials['username'],
        "password": credentials['password']
    }

    result = requests.request(method='POST', url=_concat_url(server_url=server_url,path=LOGIN_PATH),
                              json=params,
                              verify=False)

    if result.status_code == 200:
        return result.json()['token']
    else:
        raise RuntimeError('Unable to authorize')
