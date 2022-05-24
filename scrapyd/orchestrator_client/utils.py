from scrapyd.config import Config

ORCHESTRATOR_URL = Config().get('orchestrator_url')
INSTANCE_ID = Config().get('instance_id')
USER = Config().get('orchestrator_user')
PASSWORD = Config().get('orchestrator_password')
