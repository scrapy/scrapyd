from scrapyd.config import Config

config = Config()

ORCHESTRATOR_URL = config.get('orchestrator_url')
INSTANCE_ID = config.get('instance_id')
USER = config.get('orchestrator_user')
PASSWORD = config.get('orchestrator_password')
