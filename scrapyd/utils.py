import os.path

from scrapy.utils.misc import load_object
from twisted.python import filepath

from scrapyd.exceptions import DirectoryTraversalError


def initialize_component(config, setting, default, *args):
    path = config.get(setting, default)
    cls = load_object(path)
    return cls(config, *args)


def local_items(items_dir, parsed):
    return items_dir and parsed.scheme.lower() in ("", "file", os.path.splitdrive(items_dir)[0].rstrip(":").lower())


def get_file_path(directory, project, spider, job):
    # https://docs.twisted.org/en/stable/api/twisted.python.filepath.FilePath.html
    try:
        return filepath.FilePath(directory).child(project).child(spider).child(job)
    except filepath.InsecurePath as e:
        raise DirectoryTraversalError(os.path.join(project, spider, job)) from e


def get_spider_queues(config):
    """Return a dict of Spider Queues keyed by project name"""
    spiderqueue_cls = load_object(config.get("spiderqueue", "scrapyd.spiderqueue.SqliteSpiderQueue"))
    return {project: spiderqueue_cls(config, project) for project in get_project_list(config)}


def get_project_list(config):
    """Get list of projects by inspecting the eggs storage and the ones defined in
    the scrapy.cfg [settings] section
    """

    # The poller and scheduler use this function (via get_spider_queues), and they aren't initialized with the
    # application. So, we need to re-initialize this component here.
    eggstorage = initialize_component(config, "eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")
    return eggstorage.list_projects() + [project for project, _ in config.items("settings", default=[])]
