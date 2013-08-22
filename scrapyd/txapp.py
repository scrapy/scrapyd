# this file is used to start scrapyd with twistd -y
from scrapyd import get_application
application = get_application()
