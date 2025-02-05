import config
import json
from FakeObjectsIntegration import FakeObjectsIntegration

INTEGRATION_MANIFEST_PATH = "manifests/integration_manifest.json"
ENGINE_MANIFEST_PATH = "manifests/engine_manifest.json"
AGENT_MANIFEST_PATH = "manifests/agent_manifest.json"
CREDENTIALS_PATH = ".credentials_"

if __name__ == "__main__":
  with (open(INTEGRATION_MANIFEST_PATH, 'r') as f_i,
        open(ENGINE_MANIFEST_PATH, 'r') as f_e,
        open(AGENT_MANIFEST_PATH, 'r') as f_a):
    integration_manifest = json.load(f_i)
    engine_manifest = json.load(f_e)
    agent_manifest = json.load(f_a)


  integration = FakeObjectsIntegration(server_url=config.server_url,
                                        integration_manifest=integration_manifest,
                                        engine_manifest=engine_manifest,
                                        credentials_path=CREDENTIALS_PATH,
                                       device_agent_manifest=agent_manifest)

  integration.run()
