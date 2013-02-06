from scrapy.utils.misc import load_object
from .config import Config

version_info = (0, 17, 0)
__version__ = "0.17.0"


def get_application(config=None):
    if config is None:
        config = Config()
    apppath = config.get('application', 'scrapyd.app.application')
    appfunc = load_object(apppath)
    return appfunc(config)
