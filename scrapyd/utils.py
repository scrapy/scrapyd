import os
from urllib.parse import urlsplit

from scrapy.utils.misc import load_object


def initialize_component(config, setting, default, *args):
    path = config.get(setting, default)
    cls = load_object(path)
    return cls(config, *args)


def job_log_url(job):
    return f"/logs/{job.project}/{job.spider}/{job.job}.log"


def job_items_url(job):
    return f"/items/{job.project}/{job.spider}/{job.job}.jl"


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
    the scrapy.cfg [settings] section
    """

    # The poller and scheduler use this function (via get_spider_queues), and they aren't initialized with the
    # application. So, we need to re-initialize this component here.
    eggstorage = initialize_component(config, "eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")
    projects = eggstorage.list_projects()
    projects.extend(project for project, _ in config.items("settings", default=[]))
    return projects
