import os

import pkg_resources


def activate_egg(eggpath):
    """Activate a Scrapy egg file. This is meant to be used from egg runners
    to activate a Scrapy egg file. Don't use it from other code as it may
    leave unwanted side effects.
    """
    distributions = pkg_resources.find_distributions(eggpath)
    if isinstance(distributions, tuple):
        raise ValueError("Unknown or corrupt egg")
    try:
        d = next(distributions)
    except StopIteration:
        raise ValueError("Unknown or corrupt egg")
    d.activate()
    settings_module = d.get_entry_info('scrapy', 'settings').module_name
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', settings_module)
