import os
from urllib.parse import urlsplit

from scrapy.utils.misc import load_object


def get_spider_queues(config):
    """Return a dict of Spider Queues keyed by project name"""
    spiderqueue_path = config.get("spiderqueue", "scrapyd.spiderqueue.SqliteSpiderQueue")
    spiderqueue_cls = load_object(spiderqueue_path)
    return {project: spiderqueue_cls(config, project) for project in get_project_list(config)}


# The database argument is "jobs" (in SqliteJobStorage) or a project (in SqliteSpiderQueue) from get_spider_queues(),
# which gets projects from get_project_list(), which gets projects from egg storage. We check for directory traversal
# in egg storage, instead.
def sqlite_connection_string(config, database):
    dbs_dir = config.get("dbs_dir", "dbs")
    if dbs_dir == ":memory:" or (urlsplit(dbs_dir).scheme and not os.path.splitdrive(dbs_dir)[0]):
        return dbs_dir
    if not os.path.exists(dbs_dir):
        os.makedirs(dbs_dir)
    return os.path.join(dbs_dir, f"{database}.db")


def get_project_list(config):
    """Get list of projects by inspecting the eggs storage and the ones defined in
    the scrapyd.conf [settings] section
    """
    eggstorage_path = config.get("eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")
    eggstorage_cls = load_object(eggstorage_path)
    eggstorage = eggstorage_cls(config)

    projects = eggstorage.list_projects()
    projects.extend(x[0] for x in config.items("settings", default=[]))
    return projects


def native_stringify_dict(dct_or_tuples, encoding="utf-8", *, keys_only=True):
    """Return a (new) dict with unicode keys (and values when "keys_only" is
    False) of the given dict converted to strings. `dct_or_tuples` can be a
    dict or a list of tuples, like any dict constructor supports.
    """
    d = {}
    for k, v in dct_or_tuples.items():
        key = to_native_str(k, encoding)
        if keys_only:
            value = v
        elif isinstance(v, dict):
            value = native_stringify_dict(v, encoding=encoding, keys_only=keys_only)
        elif isinstance(v, list):
            value = [to_native_str(e, encoding) for e in v]
        else:
            value = to_native_str(v, encoding)
        d[key] = value
    return d


def to_native_str(text, encoding="utf-8", errors="strict"):
    if isinstance(text, str):
        return text
    return text.decode(encoding, errors)
